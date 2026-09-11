"""
tests/test_evaluation.py

Unit tests for src/evaluation/evaluate.py.

Run with:
    python -m pytest tests/test_evaluation.py -v
or:
    python tests/test_evaluation.py

Tests cover:
  - Perfect predictions (all correct)
  - Completely wrong intent predictions
  - Escalation prediction errors
  - Missing prediction (golden ID absent from predictions)
  - Duplicate prediction ID
  - Unexpected prediction ID (not in golden)
  - Invalid intent value
  - Invalid escalation decision value
  - Combined correctness calculation
  - Accuracy / F1 computed correctly on known fixtures
  - Confusion matrix values
  - JSON serialisation round-trip
  - CLI returns exit-code 0 on valid input, 1 on invalid input
"""
import sys
import os
import json
import tempfile
import unittest

# Allow imports from src/
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from evaluation.evaluate import (
    VALID_INTENTS,
    VALID_DECISIONS,
    GoldenRecord,
    PredictionRecord,
    EvaluationResult,
    load_golden,
    load_predictions,
    validate_predictions,
    evaluate,
    ValidationError,
    build_markdown_report,
    main as eval_main,
)

# ─── Fixture helpers ──────────────────────────────────────────────────────────

def _make_golden(n: int = 5) -> list[GoldenRecord]:
    """Create n synthetic golden records cycling through intents."""
    intents = [
        "delivery_delay",
        "refund_inquiry",
        "order_tracking_inquiry",
        "damaged_or_wrong_item",
        "payment_and_billing_issue",
        "other_or_unsupported",
    ]
    decisions = ["ESCALATE", "ESCALATE", "AUTO_HANDLE", "ESCALATE", "ESCALATE", "ESCALATE"]
    records = []
    for i in range(n):
        idx = i % len(intents)
        records.append(GoldenRecord(
            id=f"golden_{i+1:03d}",
            customer_message=f"Sample message {i+1}",
            intent=intents[idx],
            escalation_decision=decisions[idx],
            source_tweet_id=str(1000 + i),
        ))
    return records


def _perfect_preds(golden: list[GoldenRecord]) -> list[PredictionRecord]:
    """Predictions that exactly match every golden label."""
    return [
        PredictionRecord(
            id=r.id,
            predicted_intent=r.intent,
            predicted_escalation_decision=r.escalation_decision,
        )
        for r in golden
    ]


def _write_jsonl(records: list[dict], path: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec) + "\n")


def _golden_to_jsonl_dicts(golden: list[GoldenRecord]) -> list[dict]:
    return [
        {
            "id": r.id,
            "customer_message": r.customer_message,
            "intent": r.intent,
            "escalation_decision": r.escalation_decision,
            "escalation_reason": "test",
            "source_tweet_id": r.source_tweet_id,
        }
        for r in golden
    ]


def _pred_to_jsonl_dicts(preds: list[PredictionRecord]) -> list[dict]:
    return [
        {
            "id": p.id,
            "predicted_intent": p.predicted_intent,
            "predicted_escalation_decision": p.predicted_escalation_decision,
        }
        for p in preds
    ]


# ─── Validation tests ─────────────────────────────────────────────────────────

class TestValidatePredictions(unittest.TestCase):

    def setUp(self):
        self.golden = _make_golden(6)
        self.perfect = _perfect_preds(self.golden)

    def test_perfect_predictions_pass_validation(self):
        """No exception should be raised for a perfect, valid prediction set."""
        validate_predictions(self.golden, self.perfect)  # must not raise

    def test_missing_prediction_raises(self):
        """Removing one prediction should cause a ValidationError."""
        preds = self.perfect[:-1]  # drop last
        with self.assertRaises(ValidationError) as ctx:
            validate_predictions(self.golden, preds)
        self.assertIn("no prediction", str(ctx.exception).lower())

    def test_duplicate_prediction_id_raises(self):
        """Duplicating a prediction ID should cause ValidationError."""
        preds = self.perfect + [self.perfect[0]]  # add duplicate
        with self.assertRaises(ValidationError) as ctx:
            validate_predictions(self.golden, preds)
        self.assertIn("duplicate", str(ctx.exception).lower())

    def test_unexpected_prediction_id_raises(self):
        """A prediction for a non-existent golden ID should raise."""
        preds = list(self.perfect)
        # Replace last prediction with a wrong ID
        preds[-1] = PredictionRecord(
            id="golden_999",
            predicted_intent=preds[-1].predicted_intent,
            predicted_escalation_decision=preds[-1].predicted_escalation_decision,
        )
        with self.assertRaises(ValidationError) as ctx:
            validate_predictions(self.golden, preds)
        self.assertIn("unexpected", str(ctx.exception).lower())

    def test_invalid_intent_raises(self):
        preds = list(self.perfect)
        preds[0] = PredictionRecord(
            id=preds[0].id,
            predicted_intent="not_a_real_intent",
            predicted_escalation_decision=preds[0].predicted_escalation_decision,
        )
        with self.assertRaises(ValidationError) as ctx:
            validate_predictions(self.golden, preds)
        self.assertIn("invalid intent", str(ctx.exception).lower())

    def test_invalid_escalation_raises(self):
        preds = list(self.perfect)
        preds[0] = PredictionRecord(
            id=preds[0].id,
            predicted_intent=preds[0].predicted_intent,
            predicted_escalation_decision="MAYBE",
        )
        with self.assertRaises(ValidationError) as ctx:
            validate_predictions(self.golden, preds)
        self.assertIn("invalid escalation", str(ctx.exception).lower())


# ─── Metric accuracy tests ────────────────────────────────────────────────────

class TestPerfectPredictions(unittest.TestCase):

    def setUp(self):
        self.golden = _make_golden(10)
        self.preds = _perfect_preds(self.golden)
        self.result = evaluate(self.golden, self.preds)

    def test_intent_accuracy_is_one(self):
        self.assertAlmostEqual(self.result.intent_accuracy, 1.0)

    def test_intent_macro_f1_is_one(self):
        self.assertAlmostEqual(self.result.intent_macro_f1, 1.0)

    def test_escalation_accuracy_is_one(self):
        self.assertAlmostEqual(self.result.escalation_accuracy, 1.0)

    def test_escalation_f1_is_one(self):
        self.assertAlmostEqual(self.result.escalation_f1, 1.0)

    def test_combined_accuracy_is_one(self):
        self.assertAlmostEqual(self.result.combined_accuracy, 1.0)

    def test_n_examples(self):
        self.assertEqual(self.result.n_examples, 10)


class TestAllWrongIntentPredictions(unittest.TestCase):
    """All intents predicted as 'other_or_unsupported' (always wrong if true != that)."""

    def setUp(self):
        # Build golden where no record has intent = other_or_unsupported
        self.golden = [
            GoldenRecord(id="golden_001", customer_message="msg", intent="delivery_delay",
                         escalation_decision="ESCALATE", source_tweet_id="1"),
            GoldenRecord(id="golden_002", customer_message="msg", intent="refund_inquiry",
                         escalation_decision="ESCALATE", source_tweet_id="2"),
            GoldenRecord(id="golden_003", customer_message="msg", intent="order_tracking_inquiry",
                         escalation_decision="AUTO_HANDLE", source_tweet_id="3"),
        ]
        # Predict wrong intent for all, but correct escalation
        self.preds = [
            PredictionRecord(id="golden_001", predicted_intent="other_or_unsupported",
                             predicted_escalation_decision="ESCALATE"),
            PredictionRecord(id="golden_002", predicted_intent="other_or_unsupported",
                             predicted_escalation_decision="ESCALATE"),
            PredictionRecord(id="golden_003", predicted_intent="other_or_unsupported",
                             predicted_escalation_decision="AUTO_HANDLE"),
        ]
        self.result = evaluate(self.golden, self.preds)

    def test_intent_accuracy_is_zero(self):
        self.assertAlmostEqual(self.result.intent_accuracy, 0.0)

    def test_combined_accuracy_is_zero(self):
        """Combined is zero because intents are all wrong."""
        self.assertAlmostEqual(self.result.combined_accuracy, 0.0)

    def test_escalation_accuracy_is_one(self):
        """Escalation was predicted correctly for all three."""
        self.assertAlmostEqual(self.result.escalation_accuracy, 1.0)


class TestEscalationErrors(unittest.TestCase):
    """All escalation predictions flipped, intents correct."""

    def setUp(self):
        self.golden = [
            GoldenRecord(id="golden_001", customer_message="m", intent="delivery_delay",
                         escalation_decision="ESCALATE", source_tweet_id="1"),
            GoldenRecord(id="golden_002", customer_message="m", intent="order_tracking_inquiry",
                         escalation_decision="AUTO_HANDLE", source_tweet_id="2"),
        ]
        # Flip escalation decisions
        self.preds = [
            PredictionRecord(id="golden_001", predicted_intent="delivery_delay",
                             predicted_escalation_decision="AUTO_HANDLE"),   # wrong
            PredictionRecord(id="golden_002", predicted_intent="order_tracking_inquiry",
                             predicted_escalation_decision="ESCALATE"),       # wrong
        ]
        self.result = evaluate(self.golden, self.preds)

    def test_intent_accuracy_is_one(self):
        self.assertAlmostEqual(self.result.intent_accuracy, 1.0)

    def test_escalation_accuracy_is_zero(self):
        self.assertAlmostEqual(self.result.escalation_accuracy, 0.0)

    def test_combined_accuracy_is_zero(self):
        self.assertAlmostEqual(self.result.combined_accuracy, 0.0)


class TestCombinedAccuracyPartial(unittest.TestCase):
    """Exactly half of both intent and escalation correct."""

    def setUp(self):
        self.golden = [
            GoldenRecord(id="golden_001", customer_message="m", intent="delivery_delay",
                         escalation_decision="ESCALATE", source_tweet_id="1"),
            GoldenRecord(id="golden_002", customer_message="m", intent="refund_inquiry",
                         escalation_decision="ESCALATE", source_tweet_id="2"),
        ]
        self.preds = [
            # First: both correct
            PredictionRecord(id="golden_001", predicted_intent="delivery_delay",
                             predicted_escalation_decision="ESCALATE"),
            # Second: intent wrong, escalation correct
            PredictionRecord(id="golden_002", predicted_intent="order_cancellation",
                             predicted_escalation_decision="ESCALATE"),
        ]
        self.result = evaluate(self.golden, self.preds)

    def test_intent_accuracy_is_half(self):
        self.assertAlmostEqual(self.result.intent_accuracy, 0.5)

    def test_escalation_accuracy_is_one(self):
        self.assertAlmostEqual(self.result.escalation_accuracy, 1.0)

    def test_combined_accuracy_is_half(self):
        # Only golden_001 has BOTH correct
        self.assertAlmostEqual(self.result.combined_accuracy, 0.5)


class TestConfusionMatrix(unittest.TestCase):

    def setUp(self):
        self.golden = [
            GoldenRecord(id="golden_001", customer_message="m", intent="delivery_delay",
                         escalation_decision="ESCALATE", source_tweet_id="1"),
            GoldenRecord(id="golden_002", customer_message="m", intent="delivery_delay",
                         escalation_decision="ESCALATE", source_tweet_id="2"),
            GoldenRecord(id="golden_003", customer_message="m", intent="refund_inquiry",
                         escalation_decision="ESCALATE", source_tweet_id="3"),
        ]
        self.preds = [
            # First: correct
            PredictionRecord(id="golden_001", predicted_intent="delivery_delay",
                             predicted_escalation_decision="ESCALATE"),
            # Second: confused as refund_inquiry
            PredictionRecord(id="golden_002", predicted_intent="refund_inquiry",
                             predicted_escalation_decision="ESCALATE"),
            # Third: correct
            PredictionRecord(id="golden_003", predicted_intent="refund_inquiry",
                             predicted_escalation_decision="ESCALATE"),
        ]
        self.result = evaluate(self.golden, self.preds)

    def test_delivery_delay_tp(self):
        """True=delivery_delay, Pred=delivery_delay → count 1."""
        self.assertEqual(
            self.result.intent_confusion_matrix["delivery_delay"]["delivery_delay"], 1
        )

    def test_delivery_delay_confused_as_refund(self):
        """True=delivery_delay, Pred=refund_inquiry → count 1."""
        self.assertEqual(
            self.result.intent_confusion_matrix["delivery_delay"]["refund_inquiry"], 1
        )

    def test_refund_tp(self):
        """True=refund_inquiry, Pred=refund_inquiry → count 1."""
        self.assertEqual(
            self.result.intent_confusion_matrix["refund_inquiry"]["refund_inquiry"], 1
        )


# ─── Per-class metric sanity tests ────────────────────────────────────────────

class TestPerClassMetrics(unittest.TestCase):

    def setUp(self):
        """4 examples: 2 delivery_delay (both correct), 2 refund_inquiry (both wrong → predicted as delivery_delay)."""
        self.golden = [
            GoldenRecord(id="golden_001", customer_message="m", intent="delivery_delay",
                         escalation_decision="ESCALATE", source_tweet_id="1"),
            GoldenRecord(id="golden_002", customer_message="m", intent="delivery_delay",
                         escalation_decision="ESCALATE", source_tweet_id="2"),
            GoldenRecord(id="golden_003", customer_message="m", intent="refund_inquiry",
                         escalation_decision="ESCALATE", source_tweet_id="3"),
            GoldenRecord(id="golden_004", customer_message="m", intent="refund_inquiry",
                         escalation_decision="ESCALATE", source_tweet_id="4"),
        ]
        self.preds = [
            PredictionRecord(id="golden_001", predicted_intent="delivery_delay",
                             predicted_escalation_decision="ESCALATE"),
            PredictionRecord(id="golden_002", predicted_intent="delivery_delay",
                             predicted_escalation_decision="ESCALATE"),
            PredictionRecord(id="golden_003", predicted_intent="delivery_delay",  # wrong
                             predicted_escalation_decision="ESCALATE"),
            PredictionRecord(id="golden_004", predicted_intent="delivery_delay",  # wrong
                             predicted_escalation_decision="ESCALATE"),
        ]
        self.result = evaluate(self.golden, self.preds)

    def test_delivery_delay_precision(self):
        # TP=2, FP=2 → precision = 2/4 = 0.5
        self.assertAlmostEqual(
            self.result.intent_per_class["delivery_delay"]["precision"], 0.5
        )

    def test_delivery_delay_recall(self):
        # TP=2, FN=0 → recall = 2/2 = 1.0
        self.assertAlmostEqual(
            self.result.intent_per_class["delivery_delay"]["recall"], 1.0
        )

    def test_refund_inquiry_recall(self):
        # TP=0, FN=2 → recall = 0/2 = 0.0
        self.assertAlmostEqual(
            self.result.intent_per_class["refund_inquiry"]["recall"], 0.0
        )

    def test_refund_inquiry_precision(self):
        # TP=0, FP=0 → precision = 0 (safe zero)
        self.assertAlmostEqual(
            self.result.intent_per_class["refund_inquiry"]["precision"], 0.0
        )

    def test_support_counts(self):
        self.assertEqual(self.result.intent_per_class["delivery_delay"]["support"], 2)
        self.assertEqual(self.result.intent_per_class["refund_inquiry"]["support"], 2)


# ─── to_dict / JSON serialisation tests ──────────────────────────────────────

class TestToDict(unittest.TestCase):

    def setUp(self):
        golden = _make_golden(6)
        preds = _perfect_preds(golden)
        self.result = evaluate(golden, preds)

    def test_to_dict_has_required_keys(self):
        d = self.result.to_dict()
        self.assertIn("n_examples", d)
        self.assertIn("intent", d)
        self.assertIn("escalation", d)
        self.assertIn("combined", d)

    def test_to_dict_intent_has_metrics(self):
        d = self.result.to_dict()
        self.assertIn("accuracy", d["intent"])
        self.assertIn("macro_f1", d["intent"])
        self.assertIn("per_class", d["intent"])
        self.assertIn("confusion_matrix", d["intent"])

    def test_to_dict_escalation_has_metrics(self):
        d = self.result.to_dict()
        self.assertIn("accuracy", d["escalation"])
        self.assertIn("precision", d["escalation"])
        self.assertIn("recall", d["escalation"])
        self.assertIn("f1", d["escalation"])

    def test_json_serialisable(self):
        d = self.result.to_dict()
        serialised = json.dumps(d)   # must not raise
        self.assertIsInstance(serialised, str)


# ─── File I/O + CLI tests ─────────────────────────────────────────────────────

class TestFileIO(unittest.TestCase):

    def _write_files(self, golden_records, pred_records, tmpdir):
        golden_path = os.path.join(tmpdir, "golden.jsonl")
        pred_path = os.path.join(tmpdir, "preds.jsonl")
        _write_jsonl(_golden_to_jsonl_dicts(golden_records), golden_path)
        _write_jsonl(_pred_to_jsonl_dicts(pred_records), pred_path)
        return golden_path, pred_path

    def test_load_golden_roundtrip(self):
        golden = _make_golden(5)
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "golden.jsonl")
            _write_jsonl(_golden_to_jsonl_dicts(golden), path)
            loaded = load_golden(path)
        self.assertEqual(len(loaded), 5)
        self.assertEqual(loaded[0].id, "golden_001")

    def test_load_predictions_roundtrip(self):
        golden = _make_golden(5)
        preds = _perfect_preds(golden)
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "preds.jsonl")
            _write_jsonl(_pred_to_jsonl_dicts(preds), path)
            loaded = load_predictions(path)
        self.assertEqual(len(loaded), 5)

    def test_load_golden_missing_file_raises(self):
        with self.assertRaises(FileNotFoundError):
            load_golden("/nonexistent/path/golden.jsonl")

    def test_load_predictions_missing_file_raises(self):
        with self.assertRaises(FileNotFoundError):
            load_predictions("/nonexistent/path/preds.jsonl")


class TestCLI(unittest.TestCase):

    def test_cli_perfect_predictions_exit_0(self):
        golden = _make_golden(6)
        preds = _perfect_preds(golden)
        with tempfile.TemporaryDirectory() as tmpdir:
            golden_path, pred_path = self._write_files(golden, preds, tmpdir)
            output_path = os.path.join(tmpdir, "out.json")
            report_path = os.path.join(tmpdir, "report.md")
            rc = eval_main([
                "--golden", golden_path,
                "--predictions", pred_path,
                "--output", output_path,
                "--report", report_path,
                "--model-name", "test_model",
                "--quiet",
            ])
        self.assertEqual(rc, 0)

    def test_cli_writes_json_output(self):
        golden = _make_golden(6)
        preds = _perfect_preds(golden)
        with tempfile.TemporaryDirectory() as tmpdir:
            golden_path, pred_path = self._write_files(golden, preds, tmpdir)
            output_path = os.path.join(tmpdir, "out.json")
            eval_main([
                "--golden", golden_path,
                "--predictions", pred_path,
                "--output", output_path,
                "--quiet",
            ])
            self.assertTrue(os.path.exists(output_path))
            with open(output_path) as f:
                data = json.load(f)
            self.assertIn("n_examples", data)
            self.assertEqual(data["n_examples"], 6)

    def test_cli_writes_markdown_report(self):
        golden = _make_golden(6)
        preds = _perfect_preds(golden)
        with tempfile.TemporaryDirectory() as tmpdir:
            golden_path, pred_path = self._write_files(golden, preds, tmpdir)
            report_path = os.path.join(tmpdir, "report.md")
            eval_main([
                "--golden", golden_path,
                "--predictions", pred_path,
                "--output", os.path.join(tmpdir, "out.json"),
                "--report", report_path,
                "--quiet",
            ])
            self.assertTrue(os.path.exists(report_path))
            content = open(report_path).read()
            self.assertIn("# Evaluation Report", content)

    def test_cli_invalid_predictions_exit_1(self):
        golden = _make_golden(6)
        preds = _perfect_preds(golden)
        # Introduce invalid intent
        bad_preds = list(preds)
        bad_preds[0] = PredictionRecord(
            id=bad_preds[0].id,
            predicted_intent="COMPLETELY_WRONG",
            predicted_escalation_decision=bad_preds[0].predicted_escalation_decision,
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            golden_path, pred_path = self._write_files(golden, bad_preds, tmpdir)
            rc = eval_main([
                "--golden", golden_path,
                "--predictions", pred_path,
                "--output", os.path.join(tmpdir, "out.json"),
                "--quiet",
            ])
        self.assertEqual(rc, 1)

    def test_cli_missing_predictions_file_exit_1(self):
        golden = _make_golden(3)
        with tempfile.TemporaryDirectory() as tmpdir:
            golden_path = os.path.join(tmpdir, "golden.jsonl")
            _write_jsonl(_golden_to_jsonl_dicts(golden), golden_path)
            rc = eval_main([
                "--golden", golden_path,
                "--predictions", "/nonexistent/preds.jsonl",
                "--output", os.path.join(tmpdir, "out.json"),
                "--quiet",
            ])
        self.assertEqual(rc, 1)

    def _write_files(self, golden_records, pred_records, tmpdir):
        golden_path = os.path.join(tmpdir, "golden.jsonl")
        pred_path = os.path.join(tmpdir, "preds.jsonl")
        _write_jsonl(_golden_to_jsonl_dicts(golden_records), golden_path)
        _write_jsonl(_pred_to_jsonl_dicts(pred_records), pred_path)
        return golden_path, pred_path


# ─── Markdown report sanity test ─────────────────────────────────────────────

class TestMarkdownReport(unittest.TestCase):

    def test_report_contains_all_sections(self):
        golden = _make_golden(6)
        preds = _perfect_preds(golden)
        result = evaluate(golden, preds)
        md = build_markdown_report(result, "golden.jsonl", "preds.jsonl", "test_model")
        self.assertIn("# Evaluation Report", md)
        self.assertIn("## Summary", md)
        self.assertIn("## Per-Intent Metrics", md)
        self.assertIn("## Intent Confusion Matrix", md)
        self.assertIn("## Escalation Confusion Matrix", md)

    def test_report_contains_accuracy_values(self):
        golden = _make_golden(6)
        preds = _perfect_preds(golden)
        result = evaluate(golden, preds)
        md = build_markdown_report(result, "golden.jsonl", "preds.jsonl", "test_model")
        # Perfect predictions → 100.0%
        self.assertIn("100.0%", md)


if __name__ == "__main__":
    unittest.main(verbosity=2)
