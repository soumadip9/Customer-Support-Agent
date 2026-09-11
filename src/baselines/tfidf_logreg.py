"""
src/baselines/tfidf_logreg.py

TF-IDF + Logistic Regression baseline classifiers.

Two independent pipelines are trained:
  1. IntentClassifier:     customer_message → intent label
  2. EscalationClassifier: customer_message → AUTO_HANDLE / ESCALATE

Feature: only customer_message text (no metadata, no tweet IDs).
"""
import json
import pickle
import os
import random
import numpy as np
from collections import Counter

from sklearn.pipeline import Pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import classification_report, accuracy_score


SEED = 42
VALID_INTENTS = {
    "delivery_delay", "order_tracking_inquiry", "order_cancellation",
    "refund_inquiry", "damaged_or_wrong_item", "payment_and_billing_issue",
    "prime_membership_inquiry", "account_access_and_security",
    "driver_and_packaging_feedback", "general_product_and_service_faq",
    "digital_and_device_troubleshooting", "promotion_and_discount_inquiry",
    "other_or_unsupported",
}
VALID_DECISIONS = {"AUTO_HANDLE", "ESCALATE"}

# TF-IDF hyperparameters
TFIDF_PARAMS = {
    "ngram_range": (1, 2),      # unigrams + bigrams
    "max_features": 50_000,
    "sublinear_tf": True,       # log(1+tf) scaling
    "min_df": 2,                # ignore terms seen in <2 docs
    "strip_accents": "unicode",
    "analyzer": "word",
}

# Logistic Regression hyperparameters
LR_PARAMS = {
    "C": 1.0,
    "max_iter": 1000,
    "random_state": SEED,
    "class_weight": "balanced",  # compensate for label imbalance
    "solver": "lbfgs",
}

# Escalation classifier has binary output — simpler LR params
LR_BINARY_PARAMS = {
    "C": 1.0,
    "max_iter": 1000,
    "random_state": SEED,
    "class_weight": "balanced",
    "solver": "lbfgs",
}


class TfidfIntentClassifier:
    """
    TF-IDF + Logistic Regression intent classifier.

    Input : raw customer_message string(s)
    Output: intent label string(s) from VALID_INTENTS
    """

    def __init__(self):
        self.pipeline: Pipeline | None = None
        self.classes_: list[str] = []
        self.train_size: int = 0
        self.val_size: int = 0
        self.val_report: str = ""

    def fit(self, texts: list[str], labels: list[str], val_fraction: float = 0.15) -> "TfidfIntentClassifier":
        """
        Train on texts/labels with an internal validation hold-out.

        Parameters
        ----------
        texts : list[str]
            Raw customer messages (training set, not golden set).
        labels : list[str]
            Intent labels corresponding to each text.
        val_fraction : float
            Fraction of data to hold out for internal validation reporting.
        """
        if len(texts) != len(labels):
            raise ValueError("texts and labels must have the same length.")
        if not texts:
            raise ValueError("Training set is empty.")

        X_train, X_val, y_train, y_val = train_test_split(
            texts, labels, test_size=val_fraction, random_state=SEED, stratify=labels
        )
        self.train_size = len(X_train)
        self.val_size = len(X_val)

        self.pipeline = Pipeline([
            ("tfidf", TfidfVectorizer(**TFIDF_PARAMS)),
            ("clf", LogisticRegression(**LR_PARAMS)),
        ])
        self.pipeline.fit(X_train, y_train)
        self.classes_ = list(self.pipeline.classes_)

        val_preds = self.pipeline.predict(X_val)
        val_acc = accuracy_score(y_val, val_preds)
        self.val_report = (
            f"Validation accuracy: {val_acc:.4f}\n"
            + classification_report(y_val, val_preds, zero_division=0)
        )
        print(f"[TfidfIntentClassifier] train={self.train_size:,}  val={self.val_size:,}  val_acc={val_acc:.4f}")
        return self

    def predict(self, texts: list[str]) -> list[str]:
        """Predict intent labels for a list of messages."""
        self._check_fitted()
        # Handle empty strings safely
        safe_texts = [t if (t and t.strip()) else "unknown" for t in texts]
        return list(self.pipeline.predict(safe_texts))

    def predict_proba(self, texts: list[str]) -> np.ndarray:
        """Return class probabilities (shape: n_samples × n_classes)."""
        self._check_fitted()
        safe_texts = [t if (t and t.strip()) else "unknown" for t in texts]
        return self.pipeline.predict_proba(safe_texts)

    def _check_fitted(self):
        if self.pipeline is None:
            raise RuntimeError("TfidfIntentClassifier must be fit() before predict().")

    def save(self, path: str) -> None:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            pickle.dump(self, f)
        print(f"[TfidfIntentClassifier] Saved to {path}")

    @staticmethod
    def load(path: str) -> "TfidfIntentClassifier":
        with open(path, "rb") as f:
            return pickle.load(f)


class TfidfEscalationClassifier:
    """
    TF-IDF + Logistic Regression binary escalation classifier.

    Input : raw customer_message string(s)
    Output: 'AUTO_HANDLE' or 'ESCALATE'
    """

    def __init__(self):
        self.pipeline: Pipeline | None = None
        self.classes_: list[str] = []
        self.train_size: int = 0
        self.val_size: int = 0
        self.val_report: str = ""

    def fit(self, texts: list[str], labels: list[str], val_fraction: float = 0.15) -> "TfidfEscalationClassifier":
        if len(texts) != len(labels):
            raise ValueError("texts and labels must have the same length.")
        if not texts:
            raise ValueError("Training set is empty.")

        X_train, X_val, y_train, y_val = train_test_split(
            texts, labels, test_size=val_fraction, random_state=SEED, stratify=labels
        )
        self.train_size = len(X_train)
        self.val_size = len(X_val)

        lr_params = {k: v for k, v in LR_BINARY_PARAMS.items()}

        self.pipeline = Pipeline([
            ("tfidf", TfidfVectorizer(**TFIDF_PARAMS)),
            ("clf", LogisticRegression(**lr_params)),
        ])
        self.pipeline.fit(X_train, y_train)
        self.classes_ = list(self.pipeline.classes_)

        val_preds = self.pipeline.predict(X_val)
        val_acc = accuracy_score(y_val, val_preds)
        self.val_report = (
            f"Validation accuracy: {val_acc:.4f}\n"
            + classification_report(y_val, val_preds, zero_division=0)
        )
        print(f"[TfidfEscalationClassifier] train={self.train_size:,}  val={self.val_size:,}  val_acc={val_acc:.4f}")
        return self

    def predict(self, texts: list[str]) -> list[str]:
        self._check_fitted()
        safe_texts = [t if (t and t.strip()) else "unknown" for t in texts]
        return list(self.pipeline.predict(safe_texts))

    def predict_proba(self, texts: list[str]) -> np.ndarray:
        self._check_fitted()
        safe_texts = [t if (t and t.strip()) else "unknown" for t in texts]
        return self.pipeline.predict_proba(safe_texts)

    def _check_fitted(self):
        if self.pipeline is None:
            raise RuntimeError("TfidfEscalationClassifier must be fit() before predict().")

    def save(self, path: str) -> None:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            pickle.dump(self, f)
        print(f"[TfidfEscalationClassifier] Saved to {path}")

    @staticmethod
    def load(path: str) -> "TfidfEscalationClassifier":
        with open(path, "rb") as f:
            return pickle.load(f)


def load_training_data(jsonl_path: str) -> tuple[list[str], list[str], list[str]]:
    """Returns (texts, intent_labels, escalation_labels)."""
    texts, intents, escalations = [], [], []
    with open(jsonl_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            text = rec.get("customer_message", "").strip()
            intent = rec.get("intent", "")
            esc = rec.get("escalation_decision", "")
            if text and intent in VALID_INTENTS and esc in VALID_DECISIONS:
                texts.append(text)
                intents.append(intent)
                escalations.append(esc)
    return texts, intents, escalations


if __name__ == "__main__":
    train_path = r"c:\CustomerSupport\data\training_data.jsonl"
    intent_save = r"c:\CustomerSupport\models\tfidf_intent_classifier.pkl"
    esc_save = r"c:\CustomerSupport\models\tfidf_escalation_classifier.pkl"

    print(f"Loading training data from {train_path}...")
    texts, intents, escalations = load_training_data(train_path)
    print(f"  {len(texts):,} valid records loaded.")

    print("\n--- Training Intent Classifier ---")
    intent_clf = TfidfIntentClassifier()
    intent_clf.fit(texts, intents)
    print("\nValidation Report:")
    print(intent_clf.val_report)
    intent_clf.save(intent_save)

    print("\n--- Training Escalation Classifier ---")
    esc_clf = TfidfEscalationClassifier()
    esc_clf.fit(texts, escalations)
    print("\nValidation Report:")
    print(esc_clf.val_report)
    esc_clf.save(esc_save)

    print("\n[Done] Both TF-IDF classifiers saved.")
