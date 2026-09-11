"""
src/retrieval/build_index.py

Embeds the AmazonHelp historical customer retrieval corpus using SentenceTransformer
('all-MiniLM-L6-v2') and builds a persistent FAISS IndexFlatIP (cosine similarity).

Outputs:
  - models/retrieval/faiss_index.bin       (FAISS index)
  - models/retrieval/corpus_metadata.jsonl (Metadata mapping vector ID -> record)
"""

import argparse
import json
import os
import time
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer

DEFAULT_CORPUS = r"c:\CustomerSupport\data\retrieval_corpus.jsonl"
DEFAULT_INDEX_DIR = r"c:\CustomerSupport\models\retrieval"
DEFAULT_MODEL_NAME = "all-MiniLM-L6-v2"
EMBEDDING_DIM = 384


def build_faiss_index(
    corpus_path: str = DEFAULT_CORPUS,
    output_dir: str = DEFAULT_INDEX_DIR,
    model_name: str = DEFAULT_MODEL_NAME,
    batch_size: int = 256,
) -> tuple[str, str, int]:
    t0 = time.time()
    
    if not os.path.exists(corpus_path):
        raise FileNotFoundError(f"Retrieval corpus not found: {corpus_path}")

    # 1. Load corpus
    print(f"[build_index] Loading corpus from: {corpus_path}")
    records = []
    with open(corpus_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))

    n_records = len(records)
    print(f"[build_index] Loaded {n_records:,} corpus records.")

    if n_records == 0:
        raise ValueError("Retrieval corpus is empty.")

    # 2. Extract customer messages for embedding
    texts = [r["customer_message"] for r in records]

    # 3. Load embedding model
    print(f"[build_index] Loading embedding model '{model_name}'...")
    model = SentenceTransformer(model_name)

    # 4. Encode texts in batches
    print(f"[build_index] Encoding {n_records:,} texts (batch_size={batch_size})...")
    embeddings = model.encode(
        texts,
        batch_size=batch_size,
        show_progress_bar=True,
        convert_to_numpy=True,
        normalize_embeddings=True,  # Normalize for cosine similarity via IndexFlatIP
    )
    embeddings = np.ascontiguousarray(embeddings, dtype=np.float32)

    # 5. Build FAISS IndexFlatIP
    print(f"[build_index] Building FAISS IndexFlatIP (dim={EMBEDDING_DIM})...")
    index = faiss.IndexFlatIP(EMBEDDING_DIM)
    index.add(embeddings)
    print(f"[build_index] Added {index.ntotal:,} vectors to index.")

    # 6. Save FAISS index and metadata
    os.makedirs(output_dir, exist_ok=True)
    index_path = os.path.join(output_dir, "faiss_index.bin")
    metadata_path = os.path.join(output_dir, "corpus_metadata.jsonl")

    faiss.write_index(index, index_path)
    print(f"[build_index] Saved FAISS index to: {index_path} ({os.path.getsize(index_path) / 1024:.1f} KB)")

    with open(metadata_path, "w", encoding="utf-8") as f:
        for i, rec in enumerate(records):
            meta_entry = {
                "vector_id": i,
                "source_id": rec.get("source_id", ""),
                "customer_message": rec.get("customer_message", ""),
                "historical_response": rec.get("historical_response", ""),
                "response_tweet_id": rec.get("response_tweet_id", ""),
            }
            f.write(json.dumps(meta_entry, ensure_ascii=False) + "\n")

    print(f"[build_index] Saved metadata to: {metadata_path}")
    elapsed = time.time() - t0
    print(f"[build_index] Indexing complete in {elapsed:.2f}s.")
    return index_path, metadata_path, index.ntotal


def parse_args():
    parser = argparse.ArgumentParser(description="Build FAISS semantic retrieval index for AmazonHelp support corpus.")
    parser.add_argument("--corpus", default=DEFAULT_CORPUS, help="Path to retrieval_corpus.jsonl")
    parser.add_argument("--output-dir", default=DEFAULT_INDEX_DIR, help="Directory to save FAISS index and metadata")
    parser.add_argument("--model-name", default=DEFAULT_MODEL_NAME, help="SentenceTransformer model name")
    parser.add_argument("--batch-size", type=int, default=256, help="Batch size for embedding generation")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    build_faiss_index(
        corpus_path=args.corpus,
        output_dir=args.output_dir,
        model_name=args.model_name,
        batch_size=args.batch_size,
    )
