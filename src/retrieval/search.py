"""
src/retrieval/search.py

Semantic retrieval search module and CLI for finding similar historical
AmazonHelp customer support interactions.

Usage:
  python -m src.retrieval.search --query "my package is several days late" --top-k 5
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer

DEFAULT_INDEX_PATH = r"c:\CustomerSupport\models\retrieval\faiss_index.bin"
DEFAULT_METADATA_PATH = r"c:\CustomerSupport\models\retrieval\corpus_metadata.jsonl"
DEFAULT_MODEL_NAME = "all-MiniLM-L6-v2"


class SemanticRetriever:
    """
    Retrieves historically similar customer messages and agent responses
    using dense embeddings and FAISS cosine similarity search.
    """

    def __init__(
        self,
        index_path: str = DEFAULT_INDEX_PATH,
        metadata_path: str = DEFAULT_METADATA_PATH,
        model_name: str = DEFAULT_MODEL_NAME,
        model_instance: SentenceTransformer | None = None,
    ):
        self.index_path = index_path
        self.metadata_path = metadata_path
        self.model_name = model_name

        if not os.path.exists(index_path):
            raise FileNotFoundError(f"FAISS index not found: {index_path}. Build it first with build_index.py.")
        if not os.path.exists(metadata_path):
            raise FileNotFoundError(f"Metadata file not found: {metadata_path}.")

        # 1. Load FAISS index
        self.index = faiss.read_index(index_path)
        self.dim = self.index.d
        self.ntotal = self.index.ntotal

        # 2. Load metadata list mapping vector_id -> record
        self.metadata: list[dict] = []
        with open(metadata_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    self.metadata.append(json.loads(line))

        if len(self.metadata) != self.ntotal:
            raise ValueError(
                f"Metadata count ({len(self.metadata)}) does not match FAISS index count ({self.ntotal})."
            )

        # 3. Load embedding model
        if model_instance is not None:
            self.model = model_instance
        else:
            self.model = SentenceTransformer(model_name)

    def search(self, query: str, top_k: int = 5) -> list[dict]:
        """
        Retrieve the top-K most similar historical interactions for a query text.

        Returns a list of dictionaries, ordered by descending similarity score:
        [
            {
                "similarity_score": float,
                "source_id": str,
                "customer_message": str,
                "historical_response": str,
            },
            ...
        ]
        """
        if not query or not query.strip():
            return []

        top_k = min(max(1, top_k), self.ntotal)

        # 1. Encode query
        query_emb = self.model.encode(
            [query],
            convert_to_numpy=True,
            normalize_embeddings=True,  # Normalized for cosine similarity
        )
        query_emb = np.ascontiguousarray(query_emb, dtype=np.float32)

        # 2. Search FAISS index
        scores, indices = self.index.search(query_emb, top_k)

        # 3. Assemble results
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < 0 or idx >= len(self.metadata):
                continue
            meta = self.metadata[idx]
            results.append({
                "similarity_score": round(float(score), 4),
                "source_id": meta.get("source_id", ""),
                "customer_message": meta.get("customer_message", ""),
                "historical_response": meta.get("historical_response", ""),
            })

        return results


def parse_args():
    parser = argparse.ArgumentParser(description="Search historically similar AmazonHelp customer support messages.")
    parser.add_argument("--query", "-q", required=True, help="Customer query message to retrieve similar examples for.")
    parser.add_argument("--top-k", "-k", type=int, default=5, help="Number of similar examples to retrieve.")
    parser.add_argument("--index-path", default=DEFAULT_INDEX_PATH, help="Path to FAISS index file.")
    parser.add_argument("--metadata-path", default=DEFAULT_METADATA_PATH, help="Path to corpus metadata file.")
    parser.add_argument("--json", action="store_true", help="Output results as raw JSON.")
    return parser.parse_args()


def main():
    args = parse_args()
    retriever = SemanticRetriever(
        index_path=args.index_path,
        metadata_path=args.metadata_path,
    )
    results = retriever.search(args.query, top_k=args.top_k)

    if args.json:
        print(json.dumps(results, indent=2, ensure_ascii=False))
        return

    print(f"\n{'='*70}")
    print(f"QUERY: \"{args.query}\"")
    print(f"Top-{len(results)} Retrieved Similar Historical Interactions:")
    print(f"{'='*70}\n")

    for i, r in enumerate(results, 1):
        print(f"[{i}] Similarity: {r['similarity_score']:.4f} | Source Tweet ID: {r['source_id']}")
        print(f"    Customer:  {r['customer_message']}")
        resp = r['historical_response'] if r['historical_response'] else "(No direct outbound response in corpus)"
        print(f"    Response:  {resp}")
        print("-" * 70)


if __name__ == "__main__":
    main()
