"""
src/baselines/train_baselines.py

CLI entry point to train both baseline classifiers and save them.

Usage:
    python src/baselines/train_baselines.py [--train-data PATH] [--models-dir PATH]
"""
import argparse
import sys
import os

# Allow running from project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from baselines.majority_baseline import MajorityClassifier, load_training_data as load_for_majority
from baselines.tfidf_logreg import (
    TfidfIntentClassifier,
    TfidfEscalationClassifier,
    load_training_data as load_for_tfidf,
)


def parse_args():
    parser = argparse.ArgumentParser(description="Train baseline classifiers for the Hiver AI Support Agent.")
    parser.add_argument(
        "--train-data",
        default=r"c:\CustomerSupport\data\training_data.jsonl",
        help="Path to training_data.jsonl",
    )
    parser.add_argument(
        "--models-dir",
        default=r"c:\CustomerSupport\models",
        help="Directory to save trained model files.",
    )
    parser.add_argument(
        "--skip-majority",
        action="store_true",
        help="Skip training the majority-class baseline.",
    )
    parser.add_argument(
        "--skip-tfidf",
        action="store_true",
        help="Skip training the TF-IDF baseline.",
    )
    return parser.parse_args()


def train_majority(train_path: str, models_dir: str) -> None:
    print("=" * 60)
    print("BASELINE 1: MajorityClassifier")
    print("=" * 60)
    records = load_for_majority(train_path)
    print(f"  Loaded {len(records):,} training records.")

    clf = MajorityClassifier()
    clf.fit(records)
    print(clf.report())

    save_path = os.path.join(models_dir, "majority_classifier.pkl")
    clf.save(save_path)


def train_tfidf(train_path: str, models_dir: str) -> None:
    print("\n" + "=" * 60)
    print("BASELINE 2: TF-IDF + Logistic Regression")
    print("=" * 60)
    texts, intents, escalations = load_for_tfidf(train_path)
    print(f"  Loaded {len(texts):,} valid records.")

    print("\n[Intent Classifier]")
    intent_clf = TfidfIntentClassifier()
    intent_clf.fit(texts, intents)
    print("\nInternal Validation Report:")
    print(intent_clf.val_report)
    intent_clf.save(os.path.join(models_dir, "tfidf_intent_classifier.pkl"))

    print("\n[Escalation Classifier]")
    esc_clf = TfidfEscalationClassifier()
    esc_clf.fit(texts, escalations)
    print("\nInternal Validation Report:")
    print(esc_clf.val_report)
    esc_clf.save(os.path.join(models_dir, "tfidf_escalation_classifier.pkl"))


def main():
    args = parse_args()

    if not os.path.exists(args.train_data):
        print(f"ERROR: Training data not found at {args.train_data}")
        print("Run: python src/baselines/build_training_data.py")
        sys.exit(1)

    os.makedirs(args.models_dir, exist_ok=True)

    if not args.skip_majority:
        train_majority(args.train_data, args.models_dir)

    if not args.skip_tfidf:
        train_tfidf(args.train_data, args.models_dir)

    print("\n" + "=" * 60)
    print("All baselines trained and saved successfully.")
    print(f"Model files are in: {args.models_dir}")
    print("=" * 60)


if __name__ == "__main__":
    main()
