"""
src/baselines/predict_golden.py

Generates predictions for the 200 golden evaluation examples using the existing
trained TF-IDF baseline models.

Outputs:
  results/tfidf_golden_predictions.jsonl

Schema:
  {"id": "golden_001", "predicted_intent": "...", "predicted_escalation_decision": "..."}
"""

import json
import os
import sys

# Ensure src/ is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from baselines.tfidf_logreg import TfidfIntentClassifier, TfidfEscalationClassifier


def generate_predictions(
    golden_path: str = r"c:\CustomerSupport\golden_dataset.jsonl",
    intent_model_path: str = r"c:\CustomerSupport\models\tfidf_intent_classifier.pkl",
    escalation_model_path: str = r"c:\CustomerSupport\models\tfidf_escalation_classifier.pkl",
    output_path: str = r"c:\CustomerSupport\results\tfidf_golden_predictions.jsonl",
) -> int:
    # 1. Check files
    if not os.path.exists(golden_path):
        raise FileNotFoundError(f"Golden dataset not found: {golden_path}")
    if not os.path.exists(intent_model_path):
        raise FileNotFoundError(f"Intent model not found: {intent_model_path}")
    if not os.path.exists(escalation_model_path):
        raise FileNotFoundError(f"Escalation model not found: {escalation_model_path}")

    # 2. Load golden examples (ONLY id and customer_message are used)
    golden_records = []
    with open(golden_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                golden_records.append(json.loads(line))

    print(f"Loaded {len(golden_records)} golden records from {golden_path}")

    # Extract messages and ids
    ids = [r["id"] for r in golden_records]
    messages = [r["customer_message"] for r in golden_records]

    # 3. Load existing trained models
    print(f"Loading intent classifier from {intent_model_path}...")
    intent_clf = TfidfIntentClassifier.load(intent_model_path)

    print(f"Loading escalation classifier from {escalation_model_path}...")
    esc_clf = TfidfEscalationClassifier.load(escalation_model_path)

    # 4. Predict
    print("Generating predictions...")
    predicted_intents = intent_clf.predict(messages)
    predicted_escalations = esc_clf.predict(messages)

    # 5. Format and save predictions
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    predictions = []
    with open(output_path, "w", encoding="utf-8") as f:
        for gid, p_intent, p_esc in zip(ids, predicted_intents, predicted_escalations):
            pred_obj = {
                "id": gid,
                "predicted_intent": p_intent,
                "predicted_escalation_decision": p_esc,
            }
            predictions.append(pred_obj)
            f.write(json.dumps(pred_obj, ensure_ascii=False) + "\n")

    print(f"Successfully wrote {len(predictions)} predictions to {output_path}")
    return len(predictions)


if __name__ == "__main__":
    generate_predictions()
