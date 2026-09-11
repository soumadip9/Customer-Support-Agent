"""
src/evaluation/run_ollama_judge.py

Execution runner for Step 17: Local Ollama LLM-as-a-Judge Response Quality Evaluation.
Selects 50 stratified examples from results/hybrid_v2_golden_predictions.jsonl,
runs Ollama (llama3.2:3b) evaluation with persistent caching, and produces:
- results/ollama_judge_evaluation.jsonl
- results/ollama_judge_summary.json
- results/ollama_judge_report.md
- data/human_response_review.csv (with human_* fields intentionally empty)
"""

from __future__ import annotations

import csv
import json
import random
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List

# Ensure project root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from src.evaluation.ollama_judge import (
    OllamaJudgeEvaluator,
    OllamaJudgeResult,
    OllamaJudgeConnectionError,
    OllamaJudgeValidationError,
)


def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    records = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def select_stratified_sample(
    records: List[Dict[str, Any]],
    n_samples: int = 50,
    seed: int = 42,
) -> List[Dict[str, Any]]:
    """
    Selects exactly n_samples using reproducible stratified sampling
    covering all unique predicted intents as evenly as possible.
    """
    by_intent = defaultdict(list)
    for r in records:
        by_intent[r["predicted_intent"]].append(r)

    intents = sorted(by_intent.keys())
    n_intents = len(intents)
    if n_intents == 0:
        raise ValueError("No records found to sample.")

    base_per_intent = n_samples // n_intents
    remainder = n_samples % n_intents

    rng = random.Random(seed)
    shuffled_groups = {k: list(v) for k, v in by_intent.items()}
    for k in shuffled_groups:
        rng.shuffle(shuffled_groups[k])

    selected = []
    for i, intent in enumerate(intents):
        count = base_per_intent + (1 if i < remainder else 0)
        selected.extend(shuffled_groups[intent][:count])

    # Sort selected items deterministically by ID
    selected.sort(key=lambda x: x["id"])
    return selected


def run_ollama_evaluation(
    predictions_path: Path = Path("results/hybrid_v2_golden_predictions.jsonl"),
    output_jsonl: Path = Path("results/ollama_judge_evaluation.jsonl"),
    output_summary_json: Path = Path("results/ollama_judge_summary.json"),
    output_report_md: Path = Path("results/ollama_judge_report.md"),
    output_human_csv: Path = Path("data/human_response_review.csv"),
    n_samples: int = 50,
    seed: int = 42,
) -> Dict[str, Any]:
    print(f"Loading predictions from: {predictions_path}")
    all_predictions = load_jsonl(predictions_path)
    if len(all_predictions) != 200:
        raise ValueError(f"Expected 200 predictions in {predictions_path}, got {len(all_predictions)}")

    # Stratified sample
    selected_samples = select_stratified_sample(all_predictions, n_samples=n_samples, seed=seed)
    print(f"Selected {len(selected_samples)} stratified examples across all intents.")

    # Initialize Ollama Judge Evaluator
    evaluator = OllamaJudgeEvaluator()
    print("Checking Ollama server connection...")
    if not evaluator.check_health():
        raise OllamaJudgeConnectionError(
            "Ollama server is unavailable or model 'llama3.2:3b' is not loaded at http://127.0.0.1:11434. "
            "Evaluation aborted to prevent data fabrication."
        )
    print("Ollama server is ONLINE and healthy.")

    judgments = []
    scores_by_dim = defaultdict(list)
    scores_by_intent = defaultdict(list)
    strengths_counts = defaultdict(int)
    weaknesses_counts = defaultdict(int)

    for idx, item in enumerate(selected_samples, 1):
        g_id = item["id"]
        customer_msg = item.get("customer_message")
        # If customer message was not in prediction file, read from golden dataset
        if not customer_msg:
            # Look up in golden dataset
            with open("golden_dataset.jsonl", "r", encoding="utf-8") as f:
                for line in f:
                    g_rec = json.loads(line)
                    if g_rec["id"] == g_id:
                        customer_msg = g_rec["customer_message"]
                        break

        pred_intent = item["predicted_intent"]
        pred_esc = item["predicted_escalation_decision"]
        draft_resp = item["draft_response"]

        print(f"[{idx}/{n_samples}] Judging {g_id} ({pred_intent})...", end=" ", flush=True)
        judge_res = evaluator.evaluate_response(
            customer_message=customer_msg,
            predicted_intent=pred_intent,
            predicted_escalation_decision=pred_esc,
            draft_response=draft_resp,
        )
        print(f"Score: {judge_res.overall_score} (Rel:{judge_res.relevance_score}, Esc:{judge_res.escalation_actionability_score})")

        judgments.append({
            "id": g_id,
            "customer_message": customer_msg,
            "predicted_intent": pred_intent,
            "predicted_escalation_decision": pred_esc,
            "draft_response": draft_resp,
            "ollama_judgment": judge_res.to_dict(),
        })

        scores_by_dim["relevance"].append(judge_res.relevance_score)
        scores_by_dim["escalation_actionability"].append(judge_res.escalation_actionability_score)
        scores_by_dim["empathy_tone"].append(judge_res.empathy_tone_score)
        scores_by_dim["policy_compliance"].append(judge_res.policy_compliance_score)
        scores_by_dim["clarity"].append(judge_res.clarity_score)
        scores_by_dim["overall"].append(judge_res.overall_score)
        scores_by_intent[pred_intent].append(judge_res.overall_score)

        for s in judge_res.strengths:
            strengths_counts[s] += 1
        for w in judge_res.weaknesses:
            weaknesses_counts[w] += 1

    # Aggregate metrics
    summary = {
        "model": evaluator.model,
        "sample_size": len(judgments),
        "intents_represented": len(scores_by_intent),
        "ollama_calls": evaluator.ollama_calls,
        "cache_hits": evaluator.cache_hits,
        "cache_misses": evaluator.cache_misses,
        "successful_judgments": evaluator.successful_judgments,
        "failed_judgments": evaluator.failed_judgments,
        "mean_scores": {
            "overall": round(sum(scores_by_dim["overall"]) / len(judgments), 2),
            "relevance": round(sum(scores_by_dim["relevance"]) / len(judgments), 2),
            "escalation_actionability": round(sum(scores_by_dim["escalation_actionability"]) / len(judgments), 2),
            "empathy_tone": round(sum(scores_by_dim["empathy_tone"]) / len(judgments), 2),
            "policy_compliance": round(sum(scores_by_dim["policy_compliance"]) / len(judgments), 2),
            "clarity": round(sum(scores_by_dim["clarity"]) / len(judgments), 2),
        },
        "score_distributions": {
            dim: {
                f"{star}_star": sum(1 for v in vals if v == star)
                for star in range(5, 0, -1)
            }
            for dim, vals in scores_by_dim.items() if dim != "overall"
        },
        "intent_average_scores": {
            intent: round(sum(vals) / len(vals), 2)
            for intent, vals in sorted(scores_by_intent.items())
        },
        "top_strengths": dict(sorted(strengths_counts.items(), key=lambda x: x[1], reverse=True)[:10]),
        "top_weaknesses": dict(sorted(weaknesses_counts.items(), key=lambda x: x[1], reverse=True)[:10]),
    }

    # Save output JSONL
    output_jsonl.parent.mkdir(parents=True, exist_ok=True)
    with open(output_jsonl, "w", encoding="utf-8") as f:
        for j in judgments:
            f.write(json.dumps(j, ensure_ascii=False) + "\n")
    print(f"Saved evaluations to: {output_jsonl}")

    # Save summary JSON
    with open(output_summary_json, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    print(f"Saved summary to: {output_summary_json}")

    # Save Markdown report
    md_report = generate_report_markdown(summary, judgments)
    with open(output_report_md, "w", encoding="utf-8") as f:
        f.write(md_report)
    print(f"Saved markdown report to: {output_report_md}")

    # Save Human Review CSV (with human fields strictly empty)
    output_human_csv.parent.mkdir(parents=True, exist_ok=True)
    csv_headers = [
        "review_id",
        "source_id",
        "customer_message",
        "draft_response",
        "ollama_relevance_score",
        "ollama_escalation_actionability_score",
        "ollama_empathy_tone_score",
        "ollama_policy_compliance_score",
        "ollama_clarity_score",
        "ollama_overall_score",
        "human_relevance_score",
        "human_escalation_actionability_score",
        "human_empathy_tone_score",
        "human_policy_compliance_score",
        "human_clarity_score",
        "human_overall_score",
        "human_notes",
    ]

    with open(output_human_csv, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=csv_headers)
        writer.writeheader()
        for idx, j in enumerate(judgments, 1):
            oj = j["ollama_judgment"]
            writer.writerow({
                "review_id": f"rev_{idx:03d}",
                "source_id": j["id"],
                "customer_message": j["customer_message"],
                "draft_response": j["draft_response"],
                "ollama_relevance_score": oj["relevance_score"],
                "ollama_escalation_actionability_score": oj["escalation_actionability_score"],
                "ollama_empathy_tone_score": oj["empathy_tone_score"],
                "ollama_policy_compliance_score": oj["policy_compliance_score"],
                "ollama_clarity_score": oj["clarity_score"],
                "ollama_overall_score": oj["overall_score"],
                # Human fields strictly empty:
                "human_relevance_score": "",
                "human_escalation_actionability_score": "",
                "human_empathy_tone_score": "",
                "human_policy_compliance_score": "",
                "human_clarity_score": "",
                "human_overall_score": "",
                "human_notes": "",
            })
    print(f"Saved human review CSV to: {output_human_csv}")

    return summary


def generate_report_markdown(summary: Dict[str, Any], judgments: List[Dict[str, Any]]) -> str:
    means = summary["mean_scores"]
    dists = summary["score_distributions"]

    md = f"""# Step 17: Local Ollama LLM-as-a-Judge Quality Evaluation Report

## 1. Executive Summary

A local **LLM-as-a-Judge evaluation** was performed using `{summary['model']}` running on a local Ollama instance (`http://127.0.0.1:11434`) with zero external API calls. Exactly **{summary['sample_size']} stratified examples** from the Final Hybrid Agent (`results/hybrid_v2_golden_predictions.jsonl`) were evaluated across all **{summary['intents_represented']} customer service intents**.

- **Model**: `{summary['model']}` (temperature=0.0)
- **Sample Size**: {summary['sample_size']} responses
- **Intents Represented**: {summary['intents_represented']} / 13
- **Ollama API Calls**: {summary['ollama_calls']} (Cache Hits: {summary['cache_hits']}, Cache Misses: {summary['cache_misses']})
- **Overall Response Quality Mean**: **{means['overall']} / 5.00**

---

## 2. Multidimensional Scoring Breakdown

| Dimension | Mean Score (1–5) | 5-Star | 4-Star | 3-Star | 2-Star | 1-Star |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Relevance & Intent Alignment** | **{means['relevance']}** | {dists['relevance']['5_star']} | {dists['relevance']['4_star']} | {dists['relevance']['3_star']} | {dists['relevance']['2_star']} | {dists['relevance']['1_star']} |
| **Escalation Actionability** | **{means['escalation_actionability']}** | {dists['escalation_actionability']['5_star']} | {dists['escalation_actionability']['4_star']} | {dists['escalation_actionability']['3_star']} | {dists['escalation_actionability']['2_star']} | {dists['escalation_actionability']['1_star']} |
| **Empathy & Tone** | **{means['empathy_tone']}** | {dists['empathy_tone']['5_star']} | {dists['empathy_tone']['4_star']} | {dists['empathy_tone']['3_star']} | {dists['empathy_tone']['2_star']} | {dists['empathy_tone']['1_star']} |
| **Policy Compliance & Safety** | **{means['policy_compliance']}** | {dists['policy_compliance']['5_star']} | {dists['policy_compliance']['4_star']} | {dists['policy_compliance']['3_star']} | {dists['policy_compliance']['2_star']} | {dists['policy_compliance']['1_star']} |
| **Clarity & Conciseness** | **{means['clarity']}** | {dists['clarity']['5_star']} | {dists['clarity']['4_star']} | {dists['clarity']['3_star']} | {dists['clarity']['2_star']} | {dists['clarity']['1_star']} |

---

## 3. Per-Intent Mean Scores

| Intent Category | Mean Judge Score (1–5) |
| :--- | :---: |
"""
    for intent, score in summary["intent_average_scores"].items():
        md += f"| `{intent}` | **{score}** |\n"

    md += f"""
---

## 4. Human Review Dataset

An unpopulated human review file has been generated at [`data/human_response_review.csv`](file:///c:/CustomerSupport/data/human_response_review.csv).
All `human_*` columns are strictly empty awaiting independent human ratings as guided by [`HUMAN_RESPONSE_REVIEW_GUIDE.md`](file:///c:/CustomerSupport/HUMAN_RESPONSE_REVIEW_GUIDE.md).
"""
    return md


if __name__ == "__main__":
    run_ollama_evaluation()
