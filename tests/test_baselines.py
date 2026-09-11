"""
tests/test_baselines.py

Sanity-check unit tests for both baseline classifiers.

Run with:
    python tests/test_baselines.py
or:
    python -m pytest tests/test_baselines.py -v

Tests verify:
  - Models train successfully on minimal synthetic data
  - Predictions are valid taxonomy labels
  - Escalation predictions are AUTO_HANDLE or ESCALATE
  - Empty/invalid inputs are handled safely
  - Saved and loaded models produce identical predictions
  - MajorityClassifier always returns one constant label
  - TF-IDF classifiers produce one prediction per input
"""
import sys
import os
import json
import pickle
import tempfile
import unittest

# Allow imports from src/
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from baselines.majority_baseline import MajorityClassifier
from baselines.tfidf_logreg import TfidfIntentClassifier, TfidfEscalationClassifier

VALID_INTENTS = {
    "delivery_delay", "order_tracking_inquiry", "order_cancellation",
    "refund_inquiry", "damaged_or_wrong_item", "payment_and_billing_issue",
    "prime_membership_inquiry", "account_access_and_security",
    "driver_and_packaging_feedback", "general_product_and_service_faq",
    "digital_and_device_troubleshooting", "promotion_and_discount_inquiry",
    "other_or_unsupported",
}
VALID_DECISIONS = {"AUTO_HANDLE", "ESCALATE"}

# Minimal synthetic training fixture — 5 examples per intent
SYNTHETIC_RECORDS = []
_FIXTURES = [
    ("delivery_delay", "ESCALATE", [
        "my package hasn't arrived and it was supposed to be here yesterday",
        "where is my order it's late by two days",
        "my delivery is overdue, please investigate",
        "still waiting for my parcel, it's past the delivery date",
        "amazon says delayed but no reason given, very frustrated",
    ]),
    ("order_tracking_inquiry", "AUTO_HANDLE", [
        "which carrier is handling my delivery?",
        "can you give me the tracking number for my shipment?",
        "when will my order be dispatched?",
        "how do I track my parcel on AMZL?",
        "estimated delivery date for my order please",
    ]),
    ("order_cancellation", "ESCALATE", [
        "please cancel my order immediately",
        "I accidentally placed a duplicate order, cancel it",
        "why was my order cancelled without warning?",
        "I want to cancel my order before it ships",
        "the cancel button is greyed out on my order",
    ]),
    ("refund_inquiry", "ESCALATE", [
        "I need a refund for my returned item",
        "when will my refund appear in my bank account?",
        "refund not processed, it's been 10 days",
        "I returned the item two weeks ago and no refund yet",
        "please refund the delivery charge, the order was late",
    ]),
    ("damaged_or_wrong_item", "ESCALATE", [
        "I received a broken product, please replace it",
        "the item arrived smashed and unusable",
        "wrong item delivered, I ordered a blue jacket not a red one",
        "my package was opened and items were missing",
        "the glassware arrived completely shattered",
    ]),
    ("payment_and_billing_issue", "ESCALATE", [
        "I was charged twice for the same order",
        "payment failed but money was deducted from my account",
        "unauthorized charge on my credit card from Amazon",
        "gift card balance was not applied to my order",
        "double charged for the same item, please refund the duplicate",
    ]),
    ("prime_membership_inquiry", "AUTO_HANDLE", [
        "how do I turn off Prime auto renewal?",
        "how do I add my partner to Amazon Household?",
        "what are the benefits of Amazon Prime Student?",
        "why am I seeing a rental fee on Prime Video?",
        "can I pause my Prime membership while travelling?",
    ]),
    ("account_access_and_security", "ESCALATE", [
        "I cannot log in to my Amazon account",
        "I'm not receiving the 2-step verification code",
        "my account has been hacked, please help",
        "please close my Amazon account permanently",
        "password reset email never arrived",
    ]),
    ("driver_and_packaging_feedback", "AUTO_HANDLE", [
        "the delivery driver threw my parcel over the fence",
        "excessive cardboard packaging for a tiny USB cable",
        "delivery driver parked across my driveway for 30 minutes",
        "driver left the parcel in the rain without ringing the bell",
        "please stop using so much plastic in your packaging",
    ]),
    ("general_product_and_service_faq", "AUTO_HANDLE", [
        "when will the Echo Spot be back in stock?",
        "does my refurbished Amazon device come with a warranty?",
        "can I trade in my old Kindle for store credit?",
        "what is the holiday return deadline for November purchases?",
        "is this item eligible for international shipping?",
    ]),
    ("digital_and_device_troubleshooting", "AUTO_HANDLE", [
        "my Kindle screen is frozen and won't respond",
        "Alexa is showing a red light ring and is unresponsive",
        "Prime Video app keeps throwing error code 5004",
        "how do I reset my Echo Dot to factory settings?",
        "Fire TV keeps rebooting in a loop",
    ]),
    ("promotion_and_discount_inquiry", "AUTO_HANDLE", [
        "my promo code says invalid at checkout",
        "is this item eligible for the Black Friday discount?",
        "the coupon code BUT3GET30 is not working for books",
        "can I price match after buying if it drops in price?",
        "where do I enter the student voucher code on checkout?",
    ]),
    ("other_or_unsupported", "ESCALATE", [
        "ありがとうございます",
        "danke für die Info",
        "done",
        "ok thanks",
        "sadly yes",
    ]),
]

for intent, esc, msgs in _FIXTURES:
    for msg in msgs:
        SYNTHETIC_RECORDS.append({
            "customer_message": msg,
            "intent": intent,
            "escalation_decision": esc,
        })


class TestMajorityClassifier(unittest.TestCase):

    def setUp(self):
        self.clf = MajorityClassifier()
        self.clf.fit(SYNTHETIC_RECORDS)

    def test_fits_without_error(self):
        self.assertIsNotNone(self.clf.majority_intent)
        self.assertIsNotNone(self.clf.majority_escalation)

    def test_majority_intent_is_valid(self):
        self.assertIn(self.clf.majority_intent, VALID_INTENTS)

    def test_majority_escalation_is_valid(self):
        self.assertIn(self.clf.majority_escalation, VALID_DECISIONS)

    def test_predict_intent_returns_valid_labels(self):
        msgs = ["any message", "another message", ""]
        preds = self.clf.predict_intent(msgs)
        self.assertEqual(len(preds), 3)
        for p in preds:
            self.assertIn(p, VALID_INTENTS, f"Invalid intent: {p}")

    def test_predict_intent_constant(self):
        """All predictions must be the same (majority) label."""
        msgs = ["message one", "message two", "message three"]
        preds = self.clf.predict_intent(msgs)
        self.assertEqual(len(set(preds)), 1, "Majority classifier must always predict the same label.")

    def test_predict_escalation_returns_valid(self):
        msgs = ["help me", "where is my order"]
        preds = self.clf.predict_escalation(msgs)
        for p in preds:
            self.assertIn(p, VALID_DECISIONS)

    def test_predict_escalation_constant(self):
        msgs = ["hello", "refund please", "cancel my order"]
        preds = self.clf.predict_escalation(msgs)
        self.assertEqual(len(set(preds)), 1)

    def test_predict_before_fit_raises(self):
        clf = MajorityClassifier()
        with self.assertRaises(RuntimeError):
            clf.predict_intent(["test"])

    def test_fit_empty_raises(self):
        clf = MajorityClassifier()
        with self.assertRaises(ValueError):
            clf.fit([])

    def test_save_and_load(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "majority.pkl")
            self.clf.save(path)
            loaded = MajorityClassifier.load(path)
            self.assertEqual(loaded.majority_intent, self.clf.majority_intent)
            self.assertEqual(loaded.majority_escalation, self.clf.majority_escalation)

    def test_report_contains_majority_label(self):
        report = self.clf.report()
        self.assertIn(self.clf.majority_intent, report)


class TestTfidfIntentClassifier(unittest.TestCase):

    def setUp(self):
        texts = [r["customer_message"] for r in SYNTHETIC_RECORDS]
        labels = [r["intent"] for r in SYNTHETIC_RECORDS]
        self.clf = TfidfIntentClassifier()
        self.clf.fit(texts, labels, val_fraction=0.2)

    def test_fits_without_error(self):
        self.assertIsNotNone(self.clf.pipeline)
        self.assertGreater(len(self.clf.classes_), 0)

    def test_classes_are_valid_intents(self):
        for cls in self.clf.classes_:
            self.assertIn(cls, VALID_INTENTS, f"Unknown class: {cls}")

    def test_predict_single(self):
        preds = self.clf.predict(["my package is late and hasn't arrived"])
        self.assertEqual(len(preds), 1)
        self.assertIn(preds[0], VALID_INTENTS)

    def test_predict_batch(self):
        msgs = ["I need a refund", "my Kindle is broken", "cancel my order now"]
        preds = self.clf.predict(msgs)
        self.assertEqual(len(preds), len(msgs))
        for p in preds:
            self.assertIn(p, VALID_INTENTS)

    def test_predict_empty_string(self):
        """Empty strings must not crash the classifier."""
        preds = self.clf.predict(["", "  "])
        self.assertEqual(len(preds), 2)
        for p in preds:
            self.assertIn(p, VALID_INTENTS)

    def test_predict_proba_shape(self):
        msgs = ["refund my money", "track my order"]
        proba = self.clf.predict_proba(msgs)
        self.assertEqual(proba.shape[0], 2)
        self.assertEqual(proba.shape[1], len(self.clf.classes_))
        # Probabilities should sum to ~1
        for row in proba:
            self.assertAlmostEqual(float(row.sum()), 1.0, places=4)

    def test_predict_before_fit_raises(self):
        clf = TfidfIntentClassifier()
        with self.assertRaises(RuntimeError):
            clf.predict(["test"])

    def test_train_val_sizes(self):
        self.assertGreater(self.clf.train_size, 0)
        self.assertGreater(self.clf.val_size, 0)

    def test_save_and_load(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "tfidf_intent.pkl")
            self.clf.save(path)
            loaded = TfidfIntentClassifier.load(path)
            preds_original = self.clf.predict(["my order is overdue"])
            preds_loaded = loaded.predict(["my order is overdue"])
            self.assertEqual(preds_original, preds_loaded)


class TestTfidfEscalationClassifier(unittest.TestCase):

    def setUp(self):
        texts = [r["customer_message"] for r in SYNTHETIC_RECORDS]
        labels = [r["escalation_decision"] for r in SYNTHETIC_RECORDS]
        self.clf = TfidfEscalationClassifier()
        self.clf.fit(texts, labels, val_fraction=0.2)

    def test_fits_without_error(self):
        self.assertIsNotNone(self.clf.pipeline)

    def test_classes_are_valid(self):
        for cls in self.clf.classes_:
            self.assertIn(cls, VALID_DECISIONS)

    def test_predict_single(self):
        preds = self.clf.predict(["I need a refund for my broken item"])
        self.assertEqual(len(preds), 1)
        self.assertIn(preds[0], VALID_DECISIONS)

    def test_predict_batch_valid(self):
        msgs = ["help me track my order", "I want a refund", "account is hacked"]
        preds = self.clf.predict(msgs)
        self.assertEqual(len(preds), 3)
        for p in preds:
            self.assertIn(p, VALID_DECISIONS, f"Invalid decision: {p}")

    def test_predict_empty_string(self):
        preds = self.clf.predict([""])
        self.assertEqual(len(preds), 1)
        self.assertIn(preds[0], VALID_DECISIONS)

    def test_predict_proba_binary(self):
        proba = self.clf.predict_proba(["cancel my order"])
        self.assertEqual(proba.shape[1], 2)

    def test_save_and_load(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "tfidf_esc.pkl")
            self.clf.save(path)
            loaded = TfidfEscalationClassifier.load(path)
            preds_original = self.clf.predict(["my account was hacked"])
            preds_loaded = loaded.predict(["my account was hacked"])
            self.assertEqual(preds_original, preds_loaded)


class TestGoldenDatasetNotUsedInTraining(unittest.TestCase):
    """Verify the golden tweet IDs are not in the training data."""

    def test_golden_ids_excluded(self):
        golden_path = r"c:\CustomerSupport\golden_dataset.jsonl"
        train_path = r"c:\CustomerSupport\data\training_data.jsonl"

        if not os.path.exists(golden_path) or not os.path.exists(train_path):
            self.skipTest("Golden or training data not found — skipping provenance test.")

        golden_tids = set()
        with open(golden_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    rec = json.loads(line)
                    golden_tids.add(str(rec["source_tweet_id"]))

        train_tids = set()
        with open(train_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    rec = json.loads(line)
                    train_tids.add(str(rec.get("tweet_id", "")))

        overlap = golden_tids & train_tids
        self.assertEqual(
            len(overlap), 0,
            f"Found {len(overlap)} golden tweet IDs in training data: {list(overlap)[:5]}"
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
