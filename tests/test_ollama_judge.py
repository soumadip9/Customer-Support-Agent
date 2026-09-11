"""
tests/test_ollama_judge.py

Comprehensive tests for Step 17 & 18 Local Ollama LLM-as-a-Judge Evaluation:
- Exactly 50 examples selected
- All 13 intents represented
- Selected IDs are unique
- Ollama output scores strictly 1-5
- Malformed output is rejected
- Human review sample contains exactly 50 rows
- Unpopulated review CSV causes agreement analysis to refuse to run
- Populated review CSV runs agreement analysis successfully
- Judge prompt contains NO gold labels or answer keys
- Cache prevents duplicate Ollama calls
- Ollama connection failure is handled safely
- Quadratic weighted Cohen's Kappa computes correctly on test pairs
"""

import csv
import json
import pytest
from pathlib import Path

from src.evaluation.ollama_judge import (
    OllamaJudgeResult,
    OllamaJudgeEvaluator,
    OllamaJudgeValidationError,
    OllamaJudgeConnectionError,
    validate_ollama_judge_output,
    build_judge_prompt,
)
from src.evaluation.run_ollama_judge import (
    select_stratified_sample,
    load_jsonl,
    run_ollama_evaluation,
)
from src.evaluation.judge_agreement import (
    analyze_agreement,
    compute_quadratic_weighted_kappa,
    HumanScoresNotPopulatedError,
)


class TestStratifiedSampling:
    def test_stratified_sample_exactly_50_items(self):
        records = load_jsonl(Path("results/hybrid_v2_golden_predictions.jsonl"))
        sample = select_stratified_sample(records, n_samples=50, seed=42)
        assert len(sample) == 50

    def test_stratified_sample_all_13_intents_represented(self):
        records = load_jsonl(Path("results/hybrid_v2_golden_predictions.jsonl"))
        sample = select_stratified_sample(records, n_samples=50, seed=42)
        intents = {r["predicted_intent"] for r in sample}
        assert len(intents) == 13

    def test_stratified_sample_unique_ids(self):
        records = load_jsonl(Path("results/hybrid_v2_golden_predictions.jsonl"))
        sample = select_stratified_sample(records, n_samples=50, seed=42)
        ids = [r["id"] for r in sample]
        assert len(ids) == len(set(ids)) == 50


class TestJudgePromptIntegrity:
    def test_prompt_excludes_gold_labels(self):
        customer_msg = "My package has not arrived yet."
        pred_intent = "delivery_delay"
        pred_esc = "ESCALATE"
        draft = "We apologize for the delay. Please share your order ID."

        prompt = build_judge_prompt(
            customer_message=customer_msg,
            predicted_intent=pred_intent,
            predicted_escalation_decision=pred_esc,
            draft_response=draft,
        )

        assert customer_msg in prompt
        assert pred_intent in prompt
        assert pred_esc in prompt
        assert draft in prompt

        # Verify NO gold keys or answer labels
        assert "gold_intent" not in prompt
        assert "gold_escalation" not in prompt
        assert "human_label" not in prompt
        assert "ground_truth" not in prompt


class TestOllamaJudgeSchemaValidation:
    def test_valid_output_parsing(self):
        data = {
            "relevance_score": 5,
            "relevance_reasoning": "Direct match.",
            "escalation_actionability_score": 4,
            "escalation_reasoning": "Clear steps.",
            "empathy_tone_score": 5,
            "empathy_reasoning": "Very polite.",
            "policy_compliance_score": 5,
            "policy_reasoning": "Safe.",
            "clarity_score": 4,
            "clarity_reasoning": "Concise.",
            "overall_score": 4.6,
            "strengths": ["Polite", "Relevant"],
            "weaknesses": [],
        }
        res = validate_ollama_judge_output(data)
        assert isinstance(res, OllamaJudgeResult)
        assert res.relevance_score == 5
        assert res.overall_score == 4.6

    def test_missing_fields_raises_validation_error(self):
        data = {
            "relevance_score": 5,
            # missing rest
        }
        with pytest.raises(OllamaJudgeValidationError, match="Missing required key"):
            validate_ollama_judge_output(data)

    def test_score_outside_bounds_raises_validation_error(self):
        data = {
            "relevance_score": 6,  # invalid score > 5
            "relevance_reasoning": "Too high",
            "escalation_actionability_score": 4,
            "escalation_reasoning": "Clear steps.",
            "empathy_tone_score": 5,
            "empathy_reasoning": "Very polite.",
            "policy_compliance_score": 5,
            "policy_reasoning": "Safe.",
            "clarity_score": 4,
            "clarity_reasoning": "Concise.",
            "overall_score": 4.8,
            "strengths": [],
            "weaknesses": [],
        }
        with pytest.raises(OllamaJudgeValidationError, match="between 1 and 5"):
            validate_ollama_judge_output(data)


class TestCachingAndConnectionHandling:
    def test_caching_prevents_duplicate_calls(self, tmp_path):
        cache_file = tmp_path / "test_cache.jsonl"
        evaluator = OllamaJudgeEvaluator(cache_path=str(cache_file))

        key = evaluator._compute_cache_key(
            customer_message="test query",
            predicted_intent="delivery_delay",
            predicted_escalation_decision="ESCALATE",
            draft_response="test draft",
        )
        sample_result = {
            "relevance_score": 5,
            "relevance_reasoning": "Good",
            "escalation_actionability_score": 5,
            "escalation_reasoning": "Good",
            "empathy_tone_score": 5,
            "empathy_reasoning": "Good",
            "policy_compliance_score": 5,
            "policy_reasoning": "Good",
            "clarity_score": 5,
            "clarity_reasoning": "Good",
            "overall_score": 5.0,
            "strengths": ["All good"],
            "weaknesses": [],
        }
        evaluator._save_cache_entry(key, sample_result)

        res = evaluator.evaluate_response(
            customer_message="test query",
            predicted_intent="delivery_delay",
            predicted_escalation_decision="ESCALATE",
            draft_response="test draft",
        )
        assert res.overall_score == 5.0
        assert evaluator.cache_hits == 1
        assert evaluator.ollama_calls == 0

    def test_connection_failure_raises_cleanly(self):
        evaluator = OllamaJudgeEvaluator(base_url="http://127.0.0.1:59999", cache_path=None)
        with pytest.raises(OllamaJudgeConnectionError):
            evaluator.evaluate_response(
                customer_message="test query",
                predicted_intent="delivery_delay",
                predicted_escalation_decision="ESCALATE",
                draft_response="test draft",
            )


class TestHumanReviewFileAndAgreement:
    def test_unpopulated_csv_raises_error(self, tmp_path):
        csv_file = tmp_path / "test_unpopulated.csv"
        headers = [
            "review_id", "source_id", "customer_message", "draft_response",
            "ollama_relevance_score", "ollama_escalation_actionability_score",
            "ollama_empathy_tone_score", "ollama_policy_compliance_score",
            "ollama_clarity_score", "ollama_overall_score",
            "human_relevance_score", "human_escalation_actionability_score",
            "human_empathy_tone_score", "human_policy_compliance_score",
            "human_clarity_score", "human_overall_score", "human_notes",
        ]
        with open(csv_file, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            for i in range(50):
                writer.writerow({
                    "review_id": f"rev_{i+1:03d}",
                    "source_id": f"golden_{i+1:03d}",
                    "customer_message": f"Query {i+1}",
                    "draft_response": f"Draft {i+1}",
                    "ollama_relevance_score": 5,
                    "ollama_escalation_actionability_score": 5,
                    "ollama_empathy_tone_score": 5,
                    "ollama_policy_compliance_score": 5,
                    "ollama_clarity_score": 5,
                    "ollama_overall_score": 5.0,
                    "human_relevance_score": "",
                    "human_escalation_actionability_score": "",
                    "human_empathy_tone_score": "",
                    "human_policy_compliance_score": "",
                    "human_clarity_score": "",
                    "human_overall_score": "",
                    "human_notes": "",
                })

        with pytest.raises(HumanScoresNotPopulatedError):
            analyze_agreement(csv_file)

    def test_populated_real_csv_runs_successfully(self):
        # Test against real data/human_response_review.csv
        summary = analyze_agreement(Path("data/human_response_review.csv"))
        assert summary["sample_size"] == 50
        assert "dimensional_agreement" in summary
        assert summary["mean_scores"]["mean_ollama_score"] > 0
        assert summary["mean_scores"]["mean_human_score"] > 0

    def test_quadratic_weighted_kappa_calculation(self):
        rater1 = [5, 4, 3, 2, 1]
        rater2 = [5, 4, 3, 2, 1]
        kappa_perfect = compute_quadratic_weighted_kappa(rater1, rater2)
        assert kappa_perfect == 1.0

        rater3 = [5, 4, 3, 2, 2]
        kappa_close = compute_quadratic_weighted_kappa(rater1, rater3)
        assert kappa_close > 0.8
