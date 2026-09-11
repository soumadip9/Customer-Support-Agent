"""
Tests for LLM-as-a-Judge Evaluation Module.
"""

import pytest
from pathlib import Path
from src.evaluation.llm_judge import (
    JudgeScore,
    validate_judge_output,
    build_judge_prompt,
    DeterministicJudgeEvaluator,
)
from src.evaluation.run_claude_judge import run_evaluation, load_jsonl


class TestJudgeOutputValidation:
    def test_valid_judge_output(self):
        sample = {
            "relevance_score": 5,
            "relevance_reasoning": "Direct match.",
            "escalation_actionability_score": 5,
            "escalation_reasoning": "Clear action steps.",
            "empathy_tone_score": 4,
            "empathy_reasoning": "Polite tone.",
            "policy_compliance_score": 5,
            "policy_reasoning": "Safe and compliant.",
            "clarity_score": 5,
            "clarity_reasoning": "Crisp.",
            "strengths": ["Clear", "Accurate"],
            "weaknesses": [],
            "human_alignment_verdict": "AGREE",
        }
        res = validate_judge_output(sample)
        assert isinstance(res, JudgeScore)
        assert res.relevance_score == 5
        assert res.overall_score == 4.8
        assert res.human_alignment_verdict == "AGREE"

    def test_missing_required_key_raises(self):
        sample = {
            "relevance_score": 5,
            # missing rest
        }
        with pytest.raises(ValueError, match="Missing required key"):
            validate_judge_output(sample)

    def test_out_of_bounds_score_raises(self):
        sample = {
            "relevance_score": 6,  # invalid
            "relevance_reasoning": "Too high.",
            "escalation_actionability_score": 5,
            "escalation_reasoning": "Clear action steps.",
            "empathy_tone_score": 4,
            "empathy_reasoning": "Polite tone.",
            "policy_compliance_score": 5,
            "policy_reasoning": "Safe and compliant.",
            "clarity_score": 5,
            "clarity_reasoning": "Crisp.",
            "strengths": [],
            "weaknesses": [],
            "human_alignment_verdict": "AGREE",
        }
        with pytest.raises(ValueError, match="must be between 1 and 5"):
            validate_judge_output(sample)


class TestJudgePromptBuilder:
    def test_prompt_contains_all_context(self):
        prompt = build_judge_prompt(
            customer_message="Where is my package?",
            gold_intent="delivery_delay",
            gold_escalation_decision="ESCALATE",
            gold_escalation_reason="Active missing package.",
            predicted_intent="delivery_delay",
            predicted_escalation_decision="ESCALATE",
            draft_response="We are sorry for the delay! Please send your order ID.",
        )
        assert "Where is my package?" in prompt
        assert "delivery_delay" in prompt
        assert "ESCALATE" in prompt
        assert "We are sorry for the delay!" in prompt
        assert "RELEVANCE & INTENT ALIGNMENT" in prompt


class TestDeterministicEvaluator:
    def test_perfect_alignment_evaluation(self):
        score = DeterministicJudgeEvaluator.evaluate(
            customer_message="My package has not arrived.",
            gold_intent="delivery_delay",
            gold_escalation="ESCALATE",
            gold_reason="Late shipment.",
            pred_intent="delivery_delay",
            pred_escalation="ESCALATE",
            draft_response="I apologize for the delay with your delivery! Please share your order number so we can investigate.",
        )
        assert score.relevance_score == 5
        assert score.escalation_actionability_score == 5
        assert score.empathy_tone_score == 5
        assert score.policy_compliance_score == 5
        assert score.overall_score >= 4.5
        assert score.human_alignment_verdict == "AGREE"

    def test_misclassified_intent_evaluation(self):
        score = DeterministicJudgeEvaluator.evaluate(
            customer_message="Money deducted but order not placed.",
            gold_intent="payment_and_billing_issue",
            gold_escalation="ESCALATE",
            gold_reason="Payment deduction error.",
            pred_intent="other_or_unsupported",
            pred_escalation="AUTO_HANDLE",
            draft_response="Please check our website for details.",
        )
        assert score.relevance_score <= 3
        assert score.escalation_actionability_score <= 3
        assert score.human_alignment_verdict == "DISAGREE"


class TestEndToEndEvaluation:
    def test_run_evaluation_creates_valid_artifacts(self, tmp_path):
        out_jsonl = tmp_path / "judge_eval.jsonl"
        out_summary = tmp_path / "judge_summary.json"
        out_report = tmp_path / "judge_report.md"

        summary = run_evaluation(
            golden_path=Path("golden_dataset.jsonl"),
            predictions_path=Path("results/hybrid_v2_golden_predictions.jsonl"),
            output_jsonl=out_jsonl,
            output_summary_json=out_summary,
            output_report_md=out_report,
        )

        assert summary["n_evaluated"] == 200
        assert 1.0 <= summary["mean_scores"]["overall_quality"] <= 5.0
        assert out_jsonl.exists()
        assert out_summary.exists()
        assert out_report.exists()

        records = load_jsonl(out_jsonl)
        assert len(records) == 200
        assert records[0]["id"] == "golden_001"
        assert "judge_evaluation" in records[0]
