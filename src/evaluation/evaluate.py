"""
src/evaluation/evaluate.py

Reusable evaluation harness for the Hiver AI Customer Support Agent.

Compares predicted intent + escalation labels against the verified
200-example golden evaluation dataset.

Usage
-----
# From project root:
python -m src.evaluation.evaluate \
    --golden golden_dataset.jsonl \
    --predictions <prediction_file.jsonl> \
    --output results/eval_output.json \
    [--report results/eval_report.md]

Prediction file format (JSONL, one record per line):
    {"id": "golden_001", "predicted_intent": "delivery_delay", "predicted_escalation_decision": "ESCALATE"}

The "id" field must match the "id" field in golden_dataset.jsonl
(i.e. "golden_001" through "golden_200").
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from typing import NamedTuple

# ─── Taxonomy constants ────────────────────────────────────────────────────────

VALID_INTENTS: frozenset[str] = frozenset({
    "delivery_delay",
    "order_tracking_inquiry",
    "order_cancellation",
    "refund_inquiry",
    "damaged_or_wrong_item",
    "payment_and_billing_issue",
    "prime_membership_inquiry",
    "account_access_and_security",
    "driver_and_packaging_feedback",
    "general_product_and_service_faq",
    "digital_and_device_troubleshooting",
    "promotion_and_discount_inquiry",
    "other_or_unsupported",
})

VALID_DECISIONS: frozenset[str] = frozenset({"AUTO_HANDLE", "ESCALATE"})

# ─── Data structures ──────────────────────────────────────────────────────────


class GoldenRecord(NamedTuple):
    id: str
    customer_message: str
    intent: str
    escalation_decision: str
    source_tweet_id: str


class PredictionRecord(NamedTuple):
    id: str
    predicted_intent: str
    predicted_escalation_decision: str


class EvaluationResult(NamedTuple):
    """All computed evaluation metrics in a single container."""
    n_examples: int

    # Intent
    intent_accuracy: float
    intent_macro_f1: float
    intent_per_class: dict[str, dict[str, float]]   # intent → {precision, recall, f1, support}
    intent_confusion_matrix: dict[str, dict[str, int]]  # true → pred → count

    # Escalation
    escalation_accuracy: float
    escalation_precision: float
    escalation_recall: float
    escalation_f1: float
    escalation_confusion_matrix: dict[str, dict[str, int]]

    # Combined
    combined_accuracy: float  # both intent AND escalation correct

    def to_dict(self) -> dict:
        return {
            "n_examples": self.n_examples,
            "intent": {
                "accuracy": round(self.intent_accuracy, 4),
                "macro_f1": round(self.intent_macro_f1, 4),
                "per_class": {
                    k: {m: round(v, 4) for m, v in metrics.items()}
                    for k, metrics in self.intent_per_class.items()
                },
                "confusion_matrix": self.intent_confusion_matrix,
            },
            "escalation": {
                "accuracy": round(self.escalation_accuracy, 4),
                "precision": round(self.escalation_precision, 4),
                "recall": round(self.escalation_recall, 4),
                "f1": round(self.escalation_f1, 4),
                "confusion_matrix": self.escalation_confusion_matrix,
            },
            "combined": {
                "accuracy": round(self.combined_accuracy, 4),
            },
        }


# ─── File I/O ─────────────────────────────────────────────────────────────────

def load_golden(path: str) -> list[GoldenRecord]:
    """Load and validate the golden dataset JSONL."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"Golden dataset not found: {path}")

    records: list[GoldenRecord] = []
    required_keys = {"id", "customer_message", "intent", "escalation_decision", "source_tweet_id"}

    with open(path, "r", encoding="utf-8") as f:
        for lineno, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError as e:
                raise ValueError(f"Golden dataset line {lineno}: invalid JSON — {e}") from e

            missing = required_keys - set(obj.keys())
            if missing:
                raise ValueError(f"Golden dataset line {lineno}: missing keys {missing}")

            records.append(GoldenRecord(
                id=str(obj["id"]),
                customer_message=str(obj["customer_message"]),
                intent=str(obj["intent"]),
                escalation_decision=str(obj["escalation_decision"]),
                source_tweet_id=str(obj["source_tweet_id"]),
            ))

    if not records:
        raise ValueError("Golden dataset is empty.")

    return records


def load_predictions(path: str) -> list[PredictionRecord]:
    """Load and validate the predictions JSONL."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"Predictions file not found: {path}")

    records: list[PredictionRecord] = []
    required_keys = {"id", "predicted_intent", "predicted_escalation_decision"}

    with open(path, "r", encoding="utf-8") as f:
        for lineno, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError as e:
                raise ValueError(f"Predictions line {lineno}: invalid JSON — {e}") from e

            missing = required_keys - set(obj.keys())
            if missing:
                raise ValueError(f"Predictions line {lineno}: missing keys {missing}")

            records.append(PredictionRecord(
                id=str(obj["id"]),
                predicted_intent=str(obj["predicted_intent"]),
                predicted_escalation_decision=str(obj["predicted_escalation_decision"]),
            ))

    if not records:
        raise ValueError("Predictions file is empty.")

    return records


# ─── Validation ───────────────────────────────────────────────────────────────

class ValidationError(Exception):
    """Raised when predictions file fails structural or schema validation."""
    pass


def validate_predictions(
    golden: list[GoldenRecord],
    predictions: list[PredictionRecord],
) -> None:
    """
    Validate that predictions align exactly with the golden set.

    Raises ValidationError with a descriptive message on any violation.
    """
    golden_ids = {r.id for r in golden}
    pred_ids = [r.id for r in predictions]

    # 1. Duplicate prediction IDs
    id_counts = Counter(pred_ids)
    duplicates = {pid: cnt for pid, cnt in id_counts.items() if cnt > 1}
    if duplicates:
        raise ValidationError(
            f"Duplicate prediction IDs found: {duplicates}"
        )

    pred_id_set = set(pred_ids)

    # 2. Unexpected predictions (pred IDs not in golden)
    unexpected = pred_id_set - golden_ids
    # 3. Missing predictions (golden IDs not in predictions)
    missing = golden_ids - pred_id_set

    errors = []
    if unexpected:
        errors.append(
            f"{len(unexpected)} unexpected prediction ID(s) not in golden set.\n"
            f"Unexpected IDs (up to 10): {sorted(unexpected)[:10]}"
        )
    if missing:
        errors.append(
            f"{len(missing)} golden example(s) have no prediction.\n"
            f"Missing IDs (up to 10): {sorted(missing)[:10]}"
        )
    if errors:
        raise ValidationError("\n".join(errors))

    # 4. Count mismatch (should be caught above, but sanity-check)
    if len(predictions) != len(golden):
        raise ValidationError(
            f"Count mismatch: golden has {len(golden)}, predictions has {len(predictions)}."
        )

    # 5. Invalid intent / escalation values
    bad_intents = []
    bad_decisions = []
    for pred in predictions:
        if pred.predicted_intent not in VALID_INTENTS:
            bad_intents.append((pred.id, pred.predicted_intent))
        if pred.predicted_escalation_decision not in VALID_DECISIONS:
            bad_decisions.append((pred.id, pred.predicted_escalation_decision))

    errors = []
    if bad_intents:
        errors.append(f"Invalid intent values (up to 5): {bad_intents[:5]}")
    if bad_decisions:
        errors.append(f"Invalid escalation decisions (up to 5): {bad_decisions[:5]}")
    if errors:
        raise ValidationError("\n".join(errors))


# ─── Metric helpers ───────────────────────────────────────────────────────────

def _precision_recall_f1(tp: int, fp: int, fn: int) -> tuple[float, float, float]:
    """Return (precision, recall, f1) safely — return 0.0 when denominator is 0."""
    p = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    r = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f = 2 * p * r / (p + r) if (p + r) > 0 else 0.0
    return p, r, f


def _compute_intent_metrics(
    true_labels: list[str],
    pred_labels: list[str],
    classes: list[str],
) -> tuple[float, float, dict[str, dict[str, float]], dict[str, dict[str, int]]]:
    """
    Return (accuracy, macro_f1, per_class_metrics, confusion_matrix).
    per_class_metrics: {intent: {precision, recall, f1, support}}
    confusion_matrix:  {true_intent: {pred_intent: count}}
    """
    n = len(true_labels)
    correct = sum(t == p for t, p in zip(true_labels, pred_labels))
    accuracy = correct / n if n > 0 else 0.0

    # Confusion matrix (true → pred → count)
    cm: dict[str, dict[str, int]] = {c: {c2: 0 for c2 in classes} for c in classes}
    for t, p in zip(true_labels, pred_labels):
        if t in cm and p in cm:
            cm[t][p] += 1

    # Per-class TP/FP/FN
    per_class: dict[str, dict[str, float]] = {}
    f1_sum = 0.0
    n_classes_with_support = 0
    for cls in classes:
        tp = sum(t == cls and p == cls for t, p in zip(true_labels, pred_labels))
        fp = sum(t != cls and p == cls for t, p in zip(true_labels, pred_labels))
        fn = sum(t == cls and p != cls for t, p in zip(true_labels, pred_labels))
        support = sum(t == cls for t in true_labels)
        p_val, r_val, f_val = _precision_recall_f1(tp, fp, fn)
        per_class[cls] = {
            "precision": round(p_val, 4),
            "recall": round(r_val, 4),
            "f1": round(f_val, 4),
            "support": support,
        }
        if support > 0:
            f1_sum += f_val
            n_classes_with_support += 1

    macro_f1 = f1_sum / n_classes_with_support if n_classes_with_support > 0 else 0.0

    return accuracy, macro_f1, per_class, cm


def _compute_escalation_metrics(
    true_labels: list[str],
    pred_labels: list[str],
) -> tuple[float, float, float, float, dict[str, dict[str, int]]]:
    """
    Return (accuracy, precision, recall, f1, confusion_matrix).
    Positive class = ESCALATE.
    """
    n = len(true_labels)
    correct = sum(t == p for t, p in zip(true_labels, pred_labels))
    accuracy = correct / n if n > 0 else 0.0

    classes = ["AUTO_HANDLE", "ESCALATE"]
    cm = {c: {c2: 0 for c2 in classes} for c in classes}
    for t, p in zip(true_labels, pred_labels):
        if t in cm and p in cm:
            cm[t][p] += 1

    # ESCALATE is the positive class
    tp = cm["ESCALATE"]["ESCALATE"]
    fp = cm["AUTO_HANDLE"]["ESCALATE"]
    fn = cm["ESCALATE"]["AUTO_HANDLE"]

    p_val, r_val, f_val = _precision_recall_f1(tp, fp, fn)
    return accuracy, p_val, r_val, f_val, cm


# ─── Core evaluation ──────────────────────────────────────────────────────────

def evaluate(
    golden: list[GoldenRecord],
    predictions: list[PredictionRecord],
) -> EvaluationResult:
    """
    Compute all evaluation metrics.

    Assumes predictions have already been validated against golden.
    """
    # Build lookup: golden id → record
    golden_by_id = {r.id: r for r in golden}
    pred_by_id = {p.id: p for p in predictions}

    # Align in golden order
    true_intents: list[str] = []
    pred_intents: list[str] = []
    true_esc: list[str] = []
    pred_esc: list[str] = []

    for gid in [r.id for r in golden]:
        g = golden_by_id[gid]
        p = pred_by_id[gid]
        true_intents.append(g.intent)
        pred_intents.append(p.predicted_intent)
        true_esc.append(g.escalation_decision)
        pred_esc.append(p.predicted_escalation_decision)

    # Sorted class list for reproducible output
    classes = sorted(VALID_INTENTS)

    intent_acc, intent_macro_f1, intent_per_class, intent_cm = _compute_intent_metrics(
        true_intents, pred_intents, classes
    )
    esc_acc, esc_prec, esc_rec, esc_f1, esc_cm = _compute_escalation_metrics(
        true_esc, pred_esc
    )

    # Combined: both intent AND escalation must be correct
    both_correct = sum(
        ti == pi and te == pe
        for ti, pi, te, pe in zip(true_intents, pred_intents, true_esc, pred_esc)
    )
    combined_acc = both_correct / len(golden) if golden else 0.0

    return EvaluationResult(
        n_examples=len(golden),
        intent_accuracy=intent_acc,
        intent_macro_f1=intent_macro_f1,
        intent_per_class=intent_per_class,
        intent_confusion_matrix=intent_cm,
        escalation_accuracy=esc_acc,
        escalation_precision=esc_prec,
        escalation_recall=esc_rec,
        escalation_f1=esc_f1,
        escalation_confusion_matrix=esc_cm,
        combined_accuracy=combined_acc,
    )


# ─── Human-readable report builder ────────────────────────────────────────────

def build_markdown_report(
    result: EvaluationResult,
    golden_path: str,
    predictions_path: str,
    model_name: str = "unknown",
) -> str:
    """Render a human-readable Markdown evaluation report."""
    lines = [
        f"# Evaluation Report",
        f"",
        f"| Field | Value |",
        f"|:---|:---|",
        f"| Ground truth | `{golden_path}` |",
        f"| Predictions | `{predictions_path}` |",
        f"| Model / system | `{model_name}` |",
        f"| Examples evaluated | {result.n_examples} |",
        f"",
        f"---",
        f"",
        f"## Summary",
        f"",
        f"| Metric | Value |",
        f"|:---|:---|",
        f"| Intent accuracy | **{result.intent_accuracy:.4f}** ({result.intent_accuracy * 100:.1f}%) |",
        f"| Intent macro F1 | **{result.intent_macro_f1:.4f}** |",
        f"| Escalation accuracy | **{result.escalation_accuracy:.4f}** ({result.escalation_accuracy * 100:.1f}%) |",
        f"| Escalation precision (ESCALATE) | {result.escalation_precision:.4f} |",
        f"| Escalation recall (ESCALATE) | {result.escalation_recall:.4f} |",
        f"| Escalation F1 (ESCALATE) | {result.escalation_f1:.4f} |",
        f"| Combined accuracy (intent + esc both correct) | **{result.combined_accuracy:.4f}** ({result.combined_accuracy * 100:.1f}%) |",
        f"",
        f"---",
        f"",
        f"## Per-Intent Metrics",
        f"",
        f"| Intent | Precision | Recall | F1 | Support |",
        f"|:---|:---:|:---:|:---:|:---:|",
    ]
    for intent in sorted(result.intent_per_class):
        m = result.intent_per_class[intent]
        lines.append(
            f"| `{intent}` | {m['precision']:.4f} | {m['recall']:.4f} | {m['f1']:.4f} | {m['support']} |"
        )

    lines += [
        f"",
        f"---",
        f"",
        f"## Intent Confusion Matrix",
        f"",
        f"Rows = true label · Columns = predicted label",
        f"",
    ]
    # Abbreviated header — sorted class list
    sorted_classes = sorted(VALID_INTENTS)
    abbrev = {
        "delivery_delay": "DD",
        "order_tracking_inquiry": "OTI",
        "order_cancellation": "OC",
        "refund_inquiry": "RI",
        "damaged_or_wrong_item": "DWI",
        "payment_and_billing_issue": "PBI",
        "prime_membership_inquiry": "PM",
        "account_access_and_security": "AAS",
        "driver_and_packaging_feedback": "DPF",
        "general_product_and_service_faq": "FAQ",
        "digital_and_device_troubleshooting": "DDT",
        "promotion_and_discount_inquiry": "PDI",
        "other_or_unsupported": "OTH",
    }
    header = "| True \\ Pred | " + " | ".join(abbrev[c] for c in sorted_classes) + " |"
    separator = "|:---|" + ":---:|" * len(sorted_classes)
    lines.append(header)
    lines.append(separator)
    for true_cls in sorted_classes:
        row_vals = [str(result.intent_confusion_matrix.get(true_cls, {}).get(pred_cls, 0))
                    for pred_cls in sorted_classes]
        lines.append(f"| `{abbrev[true_cls]}` | " + " | ".join(row_vals) + " |")

    lines += [
        f"",
        f"**Abbreviation key:** " + ", ".join(f"`{v}`={k}" for k, v in abbrev.items()),
        f"",
        f"---",
        f"",
        f"## Escalation Confusion Matrix",
        f"",
        f"| True \\ Pred | AUTO_HANDLE | ESCALATE |",
        f"|:---|:---:|:---:|",
    ]
    for tc in ["AUTO_HANDLE", "ESCALATE"]:
        ah = result.escalation_confusion_matrix.get(tc, {}).get("AUTO_HANDLE", 0)
        esc = result.escalation_confusion_matrix.get(tc, {}).get("ESCALATE", 0)
        lines.append(f"| {tc} | {ah} | {esc} |")

    return "\n".join(lines)


# ─── CLI ──────────────────────────────────────────────────────────────────────

def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Hiver AI Support Agent — Evaluation Harness",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m src.evaluation.evaluate \\
      --golden golden_dataset.jsonl \\
      --predictions results/my_predictions.jsonl

  python -m src.evaluation.evaluate \\
      --golden golden_dataset.jsonl \\
      --predictions results/my_predictions.jsonl \\
      --output results/eval_output.json \\
      --report results/eval_report.md \\
      --model-name "tfidf_baseline"
        """,
    )
    parser.add_argument(
        "--golden",
        default="golden_dataset.jsonl",
        help="Path to golden_dataset.jsonl (default: golden_dataset.jsonl)",
    )
    parser.add_argument(
        "--predictions",
        required=True,
        help="Path to JSONL predictions file. Each line: {id, predicted_intent, predicted_escalation_decision}",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="(Optional) Path to write JSON evaluation result. Default: results/eval_<predictions_stem>.json",
    )
    parser.add_argument(
        "--report",
        default=None,
        help="(Optional) Path to write Markdown report. Default: results/eval_<predictions_stem>_report.md",
    )
    parser.add_argument(
        "--model-name",
        default="unknown",
        help="Label for this model/system in the report (default: unknown)",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress progress messages (still prints summary).",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    # Derive default output paths if not specified
    pred_stem = os.path.splitext(os.path.basename(args.predictions))[0]
    output_path = args.output or os.path.join("results", f"eval_{pred_stem}.json")
    report_path = args.report or os.path.join("results", f"eval_{pred_stem}_report.md")

    if not args.quiet:
        print(f"[evaluate] Loading golden dataset: {args.golden}")
    try:
        golden = load_golden(args.golden)
    except (FileNotFoundError, ValueError) as e:
        print(f"ERROR loading golden dataset:\n  {e}", file=sys.stderr)
        return 1

    if not args.quiet:
        print(f"[evaluate] Loading predictions:    {args.predictions}")
    try:
        predictions = load_predictions(args.predictions)
    except (FileNotFoundError, ValueError) as e:
        print(f"ERROR loading predictions:\n  {e}", file=sys.stderr)
        return 1

    if not args.quiet:
        print(f"[evaluate] Validating predictions...")
    try:
        validate_predictions(golden, predictions)
    except ValidationError as e:
        print(f"VALIDATION ERROR:\n{e}", file=sys.stderr)
        return 1

    if not args.quiet:
        print(f"[evaluate] Computing metrics on {len(golden)} examples...")
    result = evaluate(golden, predictions)

    # Print summary to stdout
    print(f"\n{'='*60}")
    print(f"EVALUATION SUMMARY — {args.model_name}")
    print(f"{'='*60}")
    print(f"  Examples          : {result.n_examples}")
    print(f"  Intent accuracy   : {result.intent_accuracy:.4f}  ({result.intent_accuracy*100:.1f}%)")
    print(f"  Intent macro F1   : {result.intent_macro_f1:.4f}")
    print(f"  Escalation acc.   : {result.escalation_accuracy:.4f}  ({result.escalation_accuracy*100:.1f}%)")
    print(f"  Escalation F1     : {result.escalation_f1:.4f}")
    print(f"  Combined accuracy : {result.combined_accuracy:.4f}  ({result.combined_accuracy*100:.1f}%)")
    print(f"{'='*60}\n")

    # Write JSON result
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    result_dict = result.to_dict()
    result_dict["meta"] = {
        "golden_path": args.golden,
        "predictions_path": args.predictions,
        "model_name": args.model_name,
    }
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result_dict, f, indent=2)
    print(f"[evaluate] JSON result written to: {output_path}")

    # Write Markdown report
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    md = build_markdown_report(result, args.golden, args.predictions, args.model_name)
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(md)
    print(f"[evaluate] Markdown report written to: {report_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
