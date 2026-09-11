"""
src/baselines/majority_baseline.py

Majority-class baseline classifier.

For intent:     predict the single most frequent intent in training data.
For escalation: predict the single most frequent escalation decision.

This is the simplest possible baseline — a sanity check that any
real classifier must outperform.
"""
import json
import pickle
import os
from collections import Counter


VALID_INTENTS = {
    "delivery_delay", "order_tracking_inquiry", "order_cancellation",
    "refund_inquiry", "damaged_or_wrong_item", "payment_and_billing_issue",
    "prime_membership_inquiry", "account_access_and_security",
    "driver_and_packaging_feedback", "general_product_and_service_faq",
    "digital_and_device_troubleshooting", "promotion_and_discount_inquiry",
    "other_or_unsupported",
}
VALID_DECISIONS = {"AUTO_HANDLE", "ESCALATE"}


class MajorityClassifier:
    """
    Predicts the majority class from training data regardless of input.

    Attributes
    ----------
    majority_intent : str
        The most frequent intent label seen during fit().
    majority_escalation : str
        The most frequent escalation decision seen during fit().
    intent_counts : Counter
        Full training intent distribution.
    escalation_counts : Counter
        Full training escalation distribution.
    """

    def __init__(self):
        self.majority_intent: str | None = None
        self.majority_escalation: str | None = None
        self.intent_counts: Counter = Counter()
        self.escalation_counts: Counter = Counter()

    def fit(self, records: list[dict]) -> "MajorityClassifier":
        """
        Fit on a list of training records.

        Parameters
        ----------
        records : list[dict]
            Each dict must have keys 'intent' and 'escalation_decision'.
        """
        if not records:
            raise ValueError("Cannot fit on an empty training set.")

        for rec in records:
            intent = rec.get("intent", "")
            escalation = rec.get("escalation_decision", "")
            if intent in VALID_INTENTS:
                self.intent_counts[intent] += 1
            if escalation in VALID_DECISIONS:
                self.escalation_counts[escalation] += 1

        if not self.intent_counts:
            raise ValueError("No valid intent labels found in training data.")
        if not self.escalation_counts:
            raise ValueError("No valid escalation labels found in training data.")

        self.majority_intent = self.intent_counts.most_common(1)[0][0]
        self.majority_escalation = self.escalation_counts.most_common(1)[0][0]
        return self

    def predict_intent(self, messages: list[str]) -> list[str]:
        """Return majority intent for every message."""
        self._check_fitted()
        return [self.majority_intent] * len(messages)

    def predict_escalation(self, messages: list[str]) -> list[str]:
        """Return majority escalation decision for every message."""
        self._check_fitted()
        return [self.majority_escalation] * len(messages)

    def _check_fitted(self):
        if self.majority_intent is None:
            raise RuntimeError("MajorityClassifier must be fit() before predict().")

    def save(self, path: str) -> None:
        """Pickle the fitted classifier to path."""
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            pickle.dump(self, f)
        print(f"[MajorityClassifier] Saved to {path}")

    @staticmethod
    def load(path: str) -> "MajorityClassifier":
        """Load a pickled MajorityClassifier."""
        with open(path, "rb") as f:
            clf = pickle.load(f)
        return clf

    def report(self) -> str:
        lines = [
            "=== MajorityClassifier Report ===",
            f"Majority intent    : {self.majority_intent}",
            f"Majority escalation: {self.majority_escalation}",
            "",
            "Training intent distribution:",
        ]
        for intent, cnt in self.intent_counts.most_common():
            total = sum(self.intent_counts.values())
            lines.append(f"  {intent:<40s}: {cnt:>6,} ({cnt / total * 100:5.1f}%)")
        lines.append("\nTraining escalation distribution:")
        for dec, cnt in self.escalation_counts.most_common():
            total = sum(self.escalation_counts.values())
            lines.append(f"  {dec:<15s}: {cnt:>6,} ({cnt / total * 100:5.1f}%)")
        return "\n".join(lines)


def load_training_data(jsonl_path: str) -> list[dict]:
    records = []
    with open(jsonl_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


if __name__ == "__main__":
    import sys

    train_path = r"c:\CustomerSupport\data\training_data.jsonl"
    save_path = r"c:\CustomerSupport\models\majority_classifier.pkl"

    print(f"Loading training data from {train_path}...")
    records = load_training_data(train_path)
    print(f"  Loaded {len(records):,} training records.")

    clf = MajorityClassifier()
    clf.fit(records)
    print(clf.report())
    clf.save(save_path)
    print(f"\n[Done] MajorityClassifier saved to {save_path}")
