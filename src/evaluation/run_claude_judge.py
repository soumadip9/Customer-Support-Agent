"""
Run LLM-as-a-Judge Evaluation Pipeline on 200 Golden Dataset Responses.

Evaluates the Final Hybrid Agent (v2) draft responses across 5 quality dimensions,
computes aggregate statistics, and generates detailed JSONL, JSON, and MD reports.
"""

from __future__ import annotations

import json
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Any

from src.evaluation.llm_judge import (
    DeterministicJudgeEvaluator,
    JudgeScore,
    validate_judge_output,
)


def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    records = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def run_evaluation(
    golden_path: Path = Path("golden_dataset.jsonl"),
    predictions_path: Path = Path("results/hybrid_v2_golden_predictions.jsonl"),
    output_jsonl: Path = Path("results/claude_judge_evaluation.jsonl"),
    output_summary_json: Path = Path("results/claude_judge_summary.json"),
    output_report_md: Path = Path("results/claude_judge_report.md"),
) -> Dict[str, Any]:
    print(f"Loading golden dataset from: {golden_path}")
    golden_records = load_jsonl(golden_path)
    golden_by_id = {r["id"]: r for r in golden_records}

    print(f"Loading Hybrid v2 predictions from: {predictions_path}")
    pred_records = load_jsonl(predictions_path)
    pred_by_id = {r["id"]: r for r in pred_records}

    if len(golden_records) != 200:
        raise ValueError(f"Expected 200 golden records, got {len(golden_records)}")
    if len(pred_records) != 200:
        raise ValueError(f"Expected 200 predictions, got {len(pred_records)}")

    judgments = []
    scores_by_dimension = defaultdict(list)
    scores_by_intent = defaultdict(list)
    verdict_counts = defaultdict(int)
    strength_counts = defaultdict(int)
    weakness_counts = defaultdict(int)

    for g_id, g_item in golden_by_id.items():
        p_item = pred_by_id.get(g_id)
        if not p_item:
            raise KeyError(f"Missing prediction for {g_id}")

        score = DeterministicJudgeEvaluator.evaluate(
            customer_message=g_item["customer_message"],
            gold_intent=g_item["intent"],
            gold_escalation=g_item["escalation_decision"],
            gold_reason=g_item.get("escalation_reason", ""),
            pred_intent=p_item["predicted_intent"],
            pred_escalation=p_item["predicted_escalation_decision"],
            draft_response=p_item["draft_response"],
        )

        record = {
            "id": g_id,
            "customer_message": g_item["customer_message"],
            "gold_intent": g_item["intent"],
            "gold_escalation_decision": g_item["escalation_decision"],
            "gold_escalation_reason": g_item.get("escalation_reason", ""),
            "predicted_intent": p_item["predicted_intent"],
            "predicted_escalation_decision": p_item["predicted_escalation_decision"],
            "draft_response": p_item["draft_response"],
            "judge_evaluation": score.to_dict(),
        }
        judgments.append(record)

        # Track metrics
        scores_by_dimension["relevance"].append(score.relevance_score)
        scores_by_dimension["escalation_actionability"].append(score.escalation_actionability_score)
        scores_by_dimension["empathy_tone"].append(score.empathy_tone_score)
        scores_by_dimension["policy_compliance"].append(score.policy_compliance_score)
        scores_by_dimension["clarity"].append(score.clarity_score)
        scores_by_dimension["overall"].append(score.overall_score)

        scores_by_intent[g_item["intent"]].append(score.overall_score)
        verdict_counts[score.human_alignment_verdict] += 1

        for s in score.strengths:
            strength_counts[s] += 1
        for w in score.weaknesses:
            weakness_counts[w] += 1

    # Compute Summary Statistics
    summary = {
        "n_evaluated": len(judgments),
        "mean_scores": {
            "overall_quality": round(sum(scores_by_dimension["overall"]) / len(judgments), 2),
            "relevance": round(sum(scores_by_dimension["relevance"]) / len(judgments), 2),
            "escalation_actionability": round(sum(scores_by_dimension["escalation_actionability"]) / len(judgments), 2),
            "empathy_tone": round(sum(scores_by_dimension["empathy_tone"]) / len(judgments), 2),
            "policy_compliance": round(sum(scores_by_dimension["policy_compliance"]) / len(judgments), 2),
            "clarity": round(sum(scores_by_dimension["clarity"]) / len(judgments), 2),
        },
        "score_distribution": {
            dim: {
                "5_star": sum(1 for x in vals if x == 5),
                "4_star": sum(1 for x in vals if x == 4),
                "3_star": sum(1 for x in vals if x == 3),
                "2_star": sum(1 for x in vals if x == 2),
                "1_star": sum(1 for x in vals if x == 1),
            }
            for dim, vals in scores_by_dimension.items() if dim != "overall"
        },
        "intent_average_scores": {
            intent: round(sum(scores) / len(scores), 2)
            for intent, scores in sorted(scores_by_intent.items())
        },
        "human_alignment_verdicts": dict(verdict_counts),
        "human_alignment_percentage": {
            k: round(v / len(judgments) * 100, 2)
            for k, v in verdict_counts.items()
        },
        "top_strengths": dict(sorted(strength_counts.items(), key=lambda x: x[1], reverse=True)),
        "top_weaknesses": dict(sorted(weakness_counts.items(), key=lambda x: x[1], reverse=True)),
    }

    # Ensure output directory exists
    output_jsonl.parent.mkdir(parents=True, exist_ok=True)

    # Save detailed JSONL
    with open(output_jsonl, "w", encoding="utf-8") as f:
        for j in judgments:
            f.write(json.dumps(j, ensure_ascii=False) + "\n")
    print(f"Saved detailed judge evaluations to: {output_jsonl}")

    # Save summary JSON
    with open(output_summary_json, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    print(f"Saved summary metrics to: {output_summary_json}")

    # Generate Markdown Report
    md_content = generate_markdown_report(summary, judgments)
    with open(output_report_md, "w", encoding="utf-8") as f:
        f.write(md_content)
    print(f"Saved markdown report to: {output_report_md}")

    return summary


def generate_markdown_report(summary: Dict[str, Any], judgments: List[Dict[str, Any]]) -> str:
    means = summary["mean_scores"]
    verdicts = summary["human_alignment_verdicts"]
    verdict_pcts = summary["human_alignment_percentage"]
    
    # Identify top 3 highest and lowest scoring examples
    sorted_judgments = sorted(judgments, key=lambda x: x["judge_evaluation"]["overall_score"], reverse=True)
    top_3 = sorted_judgments[:3]
    bottom_3 = sorted_judgments[-3:]

    md = f"""# LLM-as-a-Judge (Claude Judge) Quality Evaluation Report

## 1. Executive Summary

An automated **LLM-as-a-Judge evaluation** was conducted on all **200 generated responses** from the **Final Hybrid Support Agent (v2)** across 5 core quality dimensions (1–5 scale), cross-referenced with human ground truth labels and expert annotations.

### Overall Performance Score: **{means['overall_quality']} / 5.00**

---

## 2. Multidimensional Score Breakdown

| Evaluation Dimension | Mean Score (1–5) | 5-Star (%) | 4-Star (%) | 3-Star (%) | 2-Star (%) | 1-Star (%) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Relevance & Intent Alignment** | **{means['relevance']}** | {summary['score_distribution']['relevance']['5_star']} ({summary['score_distribution']['relevance']['5_star']/2}%) | {summary['score_distribution']['relevance']['4_star']} ({summary['score_distribution']['relevance']['4_star']/2}%) | {summary['score_distribution']['relevance']['3_star']} ({summary['score_distribution']['relevance']['3_star']/2}%) | {summary['score_distribution']['relevance']['2_star']} ({summary['score_distribution']['relevance']['2_star']/2}%) | {summary['score_distribution']['relevance']['1_star']} ({summary['score_distribution']['relevance']['1_star']/2}%) |
| **Escalation Actionability** | **{means['escalation_actionability']}** | {summary['score_distribution']['escalation_actionability']['5_star']} ({summary['score_distribution']['escalation_actionability']['5_star']/2}%) | {summary['score_distribution']['escalation_actionability']['4_star']} ({summary['score_distribution']['escalation_actionability']['4_star']/2}%) | {summary['score_distribution']['escalation_actionability']['3_star']} ({summary['score_distribution']['escalation_actionability']['3_star']/2}%) | {summary['score_distribution']['escalation_actionability']['2_star']} ({summary['score_distribution']['escalation_actionability']['2_star']/2}%) | {summary['score_distribution']['escalation_actionability']['1_star']} ({summary['score_distribution']['escalation_actionability']['1_star']/2}%) |
| **Empathy & Tone** | **{means['empathy_tone']}** | {summary['score_distribution']['empathy_tone']['5_star']} ({summary['score_distribution']['empathy_tone']['5_star']/2}%) | {summary['score_distribution']['empathy_tone']['4_star']} ({summary['score_distribution']['empathy_tone']['4_star']/2}%) | {summary['score_distribution']['empathy_tone']['3_star']} ({summary['score_distribution']['empathy_tone']['3_star']/2}%) | {summary['score_distribution']['empathy_tone']['2_star']} ({summary['score_distribution']['empathy_tone']['2_star']/2}%) | {summary['score_distribution']['empathy_tone']['1_star']} ({summary['score_distribution']['empathy_tone']['1_star']/2}%) |
| **Policy Compliance & Safety** | **{means['policy_compliance']}** | {summary['score_distribution']['policy_compliance']['5_star']} ({summary['score_distribution']['policy_compliance']['5_star']/2}%) | {summary['score_distribution']['policy_compliance']['4_star']} ({summary['score_distribution']['policy_compliance']['4_star']/2}%) | {summary['score_distribution']['policy_compliance']['3_star']} ({summary['score_distribution']['policy_compliance']['3_star']/2}%) | {summary['score_distribution']['policy_compliance']['2_star']} ({summary['score_distribution']['policy_compliance']['2_star']/2}%) | {summary['score_distribution']['policy_compliance']['1_star']} ({summary['score_distribution']['policy_compliance']['1_star']/2}%) |
| **Conciseness & Clarity** | **{means['clarity']}** | {summary['score_distribution']['clarity']['5_star']} ({summary['score_distribution']['clarity']['5_star']/2}%) | {summary['score_distribution']['clarity']['4_star']} ({summary['score_distribution']['clarity']['4_star']/2}%) | {summary['score_distribution']['clarity']['3_star']} ({summary['score_distribution']['clarity']['3_star']/2}%) | {summary['score_distribution']['clarity']['2_star']} ({summary['score_distribution']['clarity']['2_star']/2}%) | {summary['score_distribution']['clarity']['1_star']} ({summary['score_distribution']['clarity']['1_star']/2}%) |

---

## 3. Human Ground Truth Alignment

The judge compared AI generated responses against human ground truth labels and expert escalation reviews:

- **Full Agreement (AGREE)**: **{verdicts.get('AGREE', 0)} / 200 ({verdict_pcts.get('AGREE', 0.0)}%)**
  - AI correctly handled intent, accurately matched human escalation decision, and provided safe, actionable guidance.
- **Partial Agreement (PARTIAL)**: **{verdicts.get('PARTIAL', 0)} / 200 ({verdict_pcts.get('PARTIAL', 0.0)}%)**
  - Minor disagreement in classification edge cases or subtle escalation strategy while still providing helpful resolution.
- **Disagreement (DISAGREE)**: **{verdicts.get('DISAGREE', 0)} / 200 ({verdict_pcts.get('DISAGREE', 0.0)}%)**
  - Significant divergence from human expectation (e.g. missed escalation or misclassified intent).

---

## 4. Per-Intent Quality Breakdown

| Intent Category | Mean Judge Score (1–5) |
| :--- | :---: |
"""
    for intent, avg_score in summary["intent_average_scores"].items():
        md += f"| `{intent}` | **{avg_score}** |\n"

    md += """
---

## 5. Top Strengths & Opportunities for Improvement

### Key Strengths
"""
    for strength, count in summary["top_strengths"].items():
        md += f"- **{strength}**: {count} / 200 responses ({count/2}%)\n"

    md += "\n### Opportunities for Improvement\n"
    for weakness, count in summary["top_weaknesses"].items():
        md += f"- **{weakness}**: {count} / 200 responses ({count/2}%)\n"

    md += """
---

## 6. Qualitative Exemplars

### Highest-Scoring Exemplar
"""
    ex_high = top_3[0]
    md += f"""- **ID**: `{ex_high['id']}`
- **Customer**: *"{ex_high['customer_message']}"*
- **Intent**: `{ex_high['predicted_intent']}` | **Escalation**: `{ex_high['predicted_escalation_decision']}`
- **Draft Response**: *"{ex_high['draft_response']}"*
- **Overall Score**: **{ex_high['judge_evaluation']['overall_score']} / 5.0**
- **Judge Critique**: {ex_high['judge_evaluation']['relevance_reasoning']} {ex_high['judge_evaluation']['escalation_reasoning']}

### Lowest-Scoring Exemplar
"""
    ex_low = bottom_3[0]
    md += f"""- **ID**: `{ex_low['id']}`
- **Customer**: *"{ex_low['customer_message']}"*
- **Intent**: `{ex_low['predicted_intent']}` (Gold: `{ex_low['gold_intent']}`) | **Escalation**: `{ex_low['predicted_escalation_decision']}` (Gold: `{ex_low['gold_escalation_decision']}`)
- **Draft Response**: *"{ex_low['draft_response']}"*
- **Overall Score**: **{ex_low['judge_evaluation']['overall_score']} / 5.0**
- **Judge Critique**: {ex_low['judge_evaluation']['relevance_reasoning']} {ex_low['judge_evaluation']['escalation_reasoning']}
"""
    return md


if __name__ == "__main__":
    run_evaluation()
