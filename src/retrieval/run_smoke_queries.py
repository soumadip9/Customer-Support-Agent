"""
run_smoke_queries.py

Executes a small set of representative customer support queries through
the semantic retrieval component to inspect retrieval quality and relevance.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import json
from src.retrieval.search import SemanticRetriever

queries = [
    "my package is several days late",
    "I need my refund",
    "my payment was charged twice",
    "how do I cancel an order that hasn't shipped yet",
]

def main():
    print("Initializing SemanticRetriever...")
    retriever = SemanticRetriever()

    for q in queries:
        print(f"\n{'='*75}")
        print(f"QUERY: \"{q}\"")
        print(f"{'='*75}")
        results = retriever.search(q, top_k=3)
        for i, r in enumerate(results, 1):
            print(f"[{i}] Similarity: {r['similarity_score']:.4f} | Source Tweet: {r['source_id']}")
            print(f"    Customer:  {r['customer_message']}")
            resp = r['historical_response'] if r['historical_response'] else "(No direct response)"
            print(f"    Response:  {resp}")
            print("-" * 75)

if __name__ == "__main__":
    main()
