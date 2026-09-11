"""
src/llm/evaluate_hybrid_golden.py

Step 14: Generates predictions for all 200 golden evaluation examples using the
HybridSupportAgent (Step 13).

Outputs:
  results/hybrid_golden_predictions.jsonl

Schema per line:
  {
    "id": "golden_001",
    "predicted_intent": "...",
    "predicted_escalation_decision": "...",
    "escalation_reason": "...",
    "draft_response": "..."
  }
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from collections import Counter

# Ensure src/ is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.llm.hybrid_agent import HybridSupportAgent
from src.llm.ollama_client import (
    VALID_DECISIONS,
    VALID_INTENTS,
)

DEFAULT_GOLDEN_PATH = r"c:\CustomerSupport\golden_dataset.jsonl"
DEFAULT_OUTPUT_PATH = r"c:\CustomerSupport\results\hybrid_golden_predictions.jsonl"
DEFAULT_MODEL = "llama3.2:3b"
DEFAULT_TOP_K = 3


def generate_hybrid_golden_predictions(
    golden_path: str = DEFAULT_GOLDEN_PATH,
    output_path: str = DEFAULT_OUTPUT_PATH,
    model_name: str = DEFAULT_MODEL,
    top_k: int = DEFAULT_TOP_K,
    use_cache: bool = True,
) -> int:
    t0 = time.time()

    # 1. Load golden dataset
    if not os.path.exists(golden_path):
        raise FileNotFoundError(f"Golden dataset not found: {golden_path}")

    golden_records = []
    with open(golden_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                golden_records.append(json.loads(line))

    n_records = len(golden_records)
    print(f"[evaluate_hybrid_golden] Loaded {n_records} golden records from {golden_path}")
    if n_records != 200:
        print(f"WARNING: Expected 200 golden records, found {n_records}.")

    # 2. Initialize Hybrid Support Agent
    print(f"[evaluate_hybrid_golden] Initializing HybridSupportAgent (model: {model_name}, top_k: {top_k})...")
    agent = HybridSupportAgent(
        default_top_k=top_k,
    )

    # 3. Generate predictions for each golden example
    print(f"[evaluate_hybrid_golden] Starting prediction loop over {n_records} examples...")
    predictions = []
    seen_ids = set()

    for idx, rec in enumerate(golden_records, 1):
        gid = rec["id"]
        customer_message = rec["customer_message"]

        # IMPORTANT: Gold labels (rec['intent'], rec['escalation_decision']) are NEVER passed to the agent
        result = agent.process_message(customer_message, top_k=top_k)

        p_intent = result["intent"]
        p_esc = result["escalation_decision"]
        esc_reason = result["escalation_reason"]
        draft_resp = result["draft_response"]

        # Validation assertions
        if p_intent not in VALID_INTENTS:
            raise ValueError(f"Invalid intent produced for {gid}: {p_intent}")
        if p_esc not in VALID_DECISIONS:
            raise ValueError(f"Invalid escalation produced for {gid}: {p_esc}")
        if gid in seen_ids:
            raise ValueError(f"Duplicate golden ID encountered: {gid}")
        seen_ids.add(gid)

        pred_entry = {
            "id": gid,
            "predicted_intent": p_intent,
            "predicted_escalation_decision": p_esc,
            "escalation_reason": esc_reason,
            "draft_response": draft_resp,
        }
        predictions.append(pred_entry)

        if idx % 20 == 0 or idx == n_records:
            elapsed = time.time() - t0
            print(f"  Processed {idx}/{n_records} examples ({idx/n_records*100:.1f}%) in {elapsed:.1f}s...")

    # 4. Save to JSONL
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        for p in predictions:
            f.write(json.dumps(p, ensure_ascii=False) + "\n")

    total_time = time.time() - t0
    print(f"\n[evaluate_hybrid_golden] Successfully saved {len(predictions)} predictions to: {output_path}")
    print(f"[evaluate_hybrid_golden] Total execution time: {total_time:.2f}s ({total_time/n_records:.2f}s per example)")

    # 5. Quick distribution check
    intent_counts = Counter(p["predicted_intent"] for p in predictions)
    esc_counts = Counter(p["predicted_escalation_decision"] for p in predictions)
    print("\nPredicted Intent Distribution:")
    for intent, count in intent_counts.most_common():
        print(f"  {intent:<38s}: {count:>3d}")
    print("\nPredicted Escalation Distribution:")
    for dec, count in esc_counts.most_common():
        print(f"  {dec:<15s}: {count:>3d}")

    return len(predictions)


def parse_args():
    parser = argparse.ArgumentParser(description="Generate Hybrid Support Agent predictions for golden evaluation dataset.")
    parser.add_argument("--golden", default=DEFAULT_GOLDEN_PATH, help="Path to golden_dataset.jsonl")
    parser.add_argument("--output", default=DEFAULT_OUTPUT_PATH, help="Path to write hybrid_golden_predictions.jsonl")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Ollama model name (default: llama3.2:3b)")
    parser.add_argument("--top-k", type=int, default=DEFAULT_TOP_K, help="Retrieval top-k (default: 3)")
    parser.add_argument("--no-cache", action="store_true", help="Bypass LLM response cache")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    generate_hybrid_golden_predictions(
        golden_path=args.golden,
        output_path=args.output,
        model_name=args.model,
        top_k=args.top_k,
        use_cache=not args.no_cache,
    )
