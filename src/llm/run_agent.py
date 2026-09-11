"""
src/llm/run_agent.py

CLI tool to run the full RAG Support Agent on an arbitrary customer support message.

Usage:
  python -m src.llm.run_agent --message "My package is three days late"
  python -m src.llm.run_agent --message "I was charged twice for order 123" --top-k 3
"""

from __future__ import annotations

import argparse
import json
import os
import sys

# Ensure src/ is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.llm.agent import SupportAgent
from src.llm.ollama_client import OllamaClient
from src.retrieval.search import SemanticRetriever


def parse_args():
    parser = argparse.ArgumentParser(
        description="Run RAG Customer Support Agent (SemanticRetriever + Ollama LLM)"
    )
    parser.add_argument(
        "--message", "-m",
        required=True,
        help="Incoming customer support message to classify and draft response for.",
    )
    parser.add_argument(
        "--top-k", "-k",
        type=int,
        default=3,
        help="Number of historical interactions to retrieve for context (default: 3).",
    )
    parser.add_argument(
        "--model",
        default="llama3.2:3b",
        help="Ollama model name (default: llama3.2:3b).",
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Disable response caching.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output result as raw JSON.",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    # Initialize components
    retriever = SemanticRetriever()
    llm_client = OllamaClient(
        model=args.model,
        use_cache=not args.no_cache,
    )
    agent = SupportAgent(
        retriever=retriever,
        llm_client=llm_client,
        default_top_k=args.top_k,
    )

    result = agent.process_message(args.message, top_k=args.top_k)

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return

    print("\n" + "=" * 75)
    print("CUSTOMER INCOMING MESSAGE:")
    print(f"\"{result['customer_message']}\"")
    print("=" * 75)

    print(f"\n--- Top-{len(result['retrieved_examples'])} Retrieved Historical Interactions (Context) ---")
    for i, ex in enumerate(result['retrieved_examples'], 1):
        print(f"[{i}] Similarity: {ex['similarity_score']:.4f} | Source Tweet: {ex['source_id']}")
        print(f"    Customer: {ex['customer_message']}")
        resp = ex['historical_response'] if ex['historical_response'] else "(No direct response)"
        print(f"    Response: {resp}")
        print("-" * 75)

    print(f"\n--- Structured Agent Decision (Model: {result['model']}) ---")
    print(f"Intent Classified   : {result['intent']}")
    print(f"Escalation Decision : {result['escalation_decision']}")
    print(f"Escalation Reason   : {result['escalation_reason']}")
    print(f"\n--- Draft Support Response ---")
    print(result['draft_response'])
    print("=" * 75 + "\n")


if __name__ == "__main__":
    main()
