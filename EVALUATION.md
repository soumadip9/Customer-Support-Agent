# Evaluation Harness

**Project:** Hiver AI Customer Support Agent  
**Evaluation Dataset:** `golden_dataset.jsonl` — 200 human-reviewed examples across 13 intent classes.

---

## Overview

This document describes the evaluation harness used to compare any classifier or agent against the verified golden dataset. The harness measures:

1. **Intent classification performance** — how well the system identifies customer intent.
2. **Escalation decision performance** — how well the system decides between AUTO_HANDLE and ESCALATE.
3. **Combined correctness** — the percentage of examples where BOTH predictions are correct simultaneously.

> [!IMPORTANT]
> The 200-example golden dataset (`golden_dataset.jsonl`) is the **only ground truth** for final evaluation.  
> **It must never be used for training or hyperparameter tuning.**

---

## Ground Truth Dataset

| Property | Value |
|:---|:---|
| File | `golden_dataset.jsonl` |
| Format | JSONL — one JSON record per line |
| Size | 200 examples |
| Intent classes | 13 (see taxonomy below) |
| Fields | `id`, `customer_message`, `intent`, `escalation_decision`, `escalation_reason`, `source_tweet_id` |

**Intent class distribution in the golden set:**

| Intent | Count |
|:---|:---:|
| `delivery_delay` | 20 |
| `refund_inquiry` | 20 |
| `order_tracking_inquiry` | 18 |
| `damaged_or_wrong_item` | 18 |
| `payment_and_billing_issue` | 16 |
| `order_cancellation` | 15 |
| `prime_membership_inquiry` | 15 |
| `account_access_and_security` | 15 |
| `driver_and_packaging_feedback` | 14 |
| `general_product_and_service_faq` | 14 |
| `digital_and_device_troubleshooting` | 14 |
| `promotion_and_discount_inquiry` | 11 |
| `other_or_unsupported` | 10 |

---

## Predictions File Format

The evaluator expects a **JSONL file** (one JSON object per line) with exactly these fields:

```json
{"id": "golden_001", "predicted_intent": "delivery_delay", "predicted_escalation_decision": "ESCALATE"}
{"id": "golden_002", "predicted_intent": "refund_inquiry", "predicted_escalation_decision": "ESCALATE"}
...
```

| Field | Type | Constraint |
|:---|:---|:---|
| `id` | string | Must match a golden `id` exactly (`golden_001` to `golden_200`) |
| `predicted_intent` | string | Must be one of the 13 valid taxonomy labels |
| `predicted_escalation_decision` | string | Must be `AUTO_HANDLE` or `ESCALATE` |

**Validation enforced:**
- Every golden ID must have exactly one prediction.
- No duplicate prediction IDs are allowed.
- No IDs not present in the golden set.
- Invalid intent or escalation values cause a hard failure with a descriptive error message.

---

## Metrics Computed

### A. Intent Classification

| Metric | Definition |
|:---|:---|
| **Accuracy** | `correct_intent_predictions / total` |
| **Macro F1** | Average F1 across all 13 classes, weighted equally (not by support) |
| **Per-intent Precision** | `TP / (TP + FP)` for each intent class |
| **Per-intent Recall** | `TP / (TP + FN)` for each intent class |
| **Per-intent F1** | `2 * P * R / (P + R)` for each intent class |
| **Confusion matrix** | 13×13 count matrix (true label → predicted label) |

> [!NOTE]
> Macro F1 is used (not weighted F1) because the golden set is roughly balanced by design. Macro F1 penalizes poor performance on minority classes equally — important for catching silent failures on rare-but-critical intents like `payment_and_billing_issue` (16 examples).

### B. Escalation Decision

| Metric | Definition |
|:---|:---|
| **Accuracy** | `correct_escalation_predictions / total` |
| **Precision** | Positive class = `ESCALATE`: `TP / (TP + FP)` |
| **Recall** | `TP / (TP + FN)` where positive = `ESCALATE` |
| **F1** | Harmonic mean of precision and recall |
| **Confusion matrix** | 2×2: AUTO_HANDLE/ESCALATE × AUTO_HANDLE/ESCALATE |

> [!IMPORTANT]
> Recall on `ESCALATE` is the most safety-critical metric. A system that routes a genuine security issue or unauthorized charge to AUTO_HANDLE (false negative for ESCALATE) causes real customer harm. In production, a threshold on escalation recall should be established before deployment.

### C. Combined Correctness

```
combined_accuracy = (examples where BOTH intent AND escalation are correct) / total
```

This is the most meaningful end-to-end metric: the system must get the full prediction right to be useful.

---

## How to Run the Evaluator

### Prerequisites
The evaluator requires no special dependencies beyond the standard library.

### Basic Usage

```bash
# From the project root (c:\CustomerSupport):
python -m src.evaluation.evaluate \
    --golden golden_dataset.jsonl \
    --predictions results/my_predictions.jsonl
```

### Full Options

```bash
python -m src.evaluation.evaluate \
    --golden    golden_dataset.jsonl \
    --predictions results/my_predictions.jsonl \
    --output    results/eval_my_model.json \
    --report    results/eval_my_model_report.md \
    --model-name "my_model_v1" \
    [--quiet]
```

| Argument | Default | Description |
|:---|:---|:---|
| `--golden` | `golden_dataset.jsonl` | Path to ground-truth JSONL |
| `--predictions` | *(required)* | Path to model predictions JSONL |
| `--output` | `results/eval_<stem>.json` | Path for JSON metric output |
| `--report` | `results/eval_<stem>_report.md` | Path for Markdown report |
| `--model-name` | `unknown` | Label for the model in the report |
| `--quiet` | off | Suppress progress messages |

### Exit Codes
- `0` — Evaluation completed successfully.
- `1` — Validation error or file not found. Error details are printed to stderr.

---

## Output Files

### JSON Result (`results/eval_*.json`)

Machine-readable output containing all metrics:

```json
{
  "n_examples": 200,
  "intent": {
    "accuracy": 0.9500,
    "macro_f1": 0.9300,
    "per_class": {
      "delivery_delay": {"precision": 0.95, "recall": 0.90, "f1": 0.92, "support": 20},
      ...
    },
    "confusion_matrix": {
      "delivery_delay": {"delivery_delay": 18, "refund_inquiry": 2, ...},
      ...
    }
  },
  "escalation": {
    "accuracy": 0.9550,
    "precision": 0.9600,
    "recall": 0.9800,
    "f1": 0.9699,
    "confusion_matrix": {
      "AUTO_HANDLE": {"AUTO_HANDLE": 80, "ESCALATE": 6},
      "ESCALATE": {"AUTO_HANDLE": 3, "ESCALATE": 111}
    }
  },
  "combined": {
    "accuracy": 0.9100
  },
  "meta": {
    "golden_path": "golden_dataset.jsonl",
    "predictions_path": "results/my_predictions.jsonl",
    "model_name": "my_model_v1"
  }
}
```

### Markdown Report (`results/eval_*_report.md`)

Human-readable report with summary table, per-intent metrics table, intent confusion matrix (abbreviated), and escalation confusion matrix.

---

## Running Unit Tests

```bash
python -m pytest tests/test_evaluation.py -v
```

The test suite (44 tests) covers:
- Perfect predictions → all metrics = 1.0
- All-wrong intent predictions → intent accuracy = 0.0, combined = 0.0
- All-wrong escalation decisions → escalation accuracy = 0.0
- Partial correctness → combined = exactly fraction with both correct
- Confusion matrix cell values verified against hand-computed expectations
- Per-class precision/recall computed against hand-calculated TP/FP/FN
- Missing prediction ID → `ValidationError`
- Duplicate prediction ID → `ValidationError`
- Unexpected prediction ID → `ValidationError`
- Invalid intent value → `ValidationError`
- Invalid escalation value → `ValidationError`
- CLI exit code 0 on valid input, 1 on invalid input
- JSON output written and parseable
- Markdown report written and contains expected sections

---

## Smoke Test (CLI Machinery Verification)

> [!NOTE]
> This is **not** model performance. It only confirms the evaluation machinery works correctly on a known-answer synthetic prediction file.

The `results/smoke_predictions.jsonl` file has 200 predictions: 198 perfectly correct, with exactly 2 deliberate errors:
- **`golden_009`**: intent changed to `other_or_unsupported` (true: `delivery_delay`)
- **`golden_010`**: escalation flipped to `AUTO_HANDLE` (true: `ESCALATE`)

```bash
python -m src.evaluation.evaluate \
    --golden golden_dataset.jsonl \
    --predictions results/smoke_predictions.jsonl \
    --model-name "smoke_test_synthetic"
```

**Actual output (verified correct):**

```
============================================================
EVALUATION SUMMARY — smoke_test_synthetic
============================================================
  Examples          : 200
  Intent accuracy   : 0.9950  (99.5%)
  Intent macro F1   : 0.9944
  Escalation acc.   : 0.9950  (99.5%)
  Escalation F1     : 0.9956
  Combined accuracy : 0.9900  (99.0%)
============================================================
```

This matches the hand-computed expectation:
- Intent accuracy = 199/200 = 0.9950 ✅
- Escalation accuracy = 199/200 = 0.9950 ✅  
- Combined accuracy = 198/200 = 0.9900 ✅

---

## File Locations

| File | Description |
|:---|:---|
| [`src/evaluation/evaluate.py`](file:///c:/CustomerSupport/src/evaluation/evaluate.py) | Core evaluation module and CLI |
| [`tests/test_evaluation.py`](file:///c:/CustomerSupport/tests/test_evaluation.py) | 44-test unit test suite |
| `results/smoke_predictions.jsonl` | Synthetic predictions for smoke testing |
| `results/eval_smoke.json` | JSON output from smoke test run |
| `results/eval_smoke_report.md` | Markdown report from smoke test run |
