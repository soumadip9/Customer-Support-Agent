"""
tests/test_retrieval.py

Unit tests for the semantic retrieval component (src/retrieval/).

Run with:
    python -m pytest tests/test_retrieval.py -v
"""

import json
import os
import sys
import tempfile
import unittest
import numpy as np
import faiss

# Ensure src/ is on sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from retrieval.search import SemanticRetriever

GOLDEN_PATH = r"c:\CustomerSupport\golden_dataset.jsonl"
CORPUS_PATH = r"c:\CustomerSupport\data\retrieval_corpus.jsonl"
INDEX_PATH = r"c:\CustomerSupport\models\retrieval\faiss_index.bin"
METADATA_PATH = r"c:\CustomerSupport\models\retrieval\corpus_metadata.jsonl"


class TestSyntheticRetriever(unittest.TestCase):
    """Fast isolated tests using a synthetic mini-index without loading the heavy model."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.dim = 4
        self.n_items = 5

        # Create dummy embeddings
        np.random.seed(42)
        raw_vecs = np.random.randn(self.n_items, self.dim).astype(np.float32)
        faiss.normalize_L2(raw_vecs)

        # Build index
        self.index = faiss.IndexFlatIP(self.dim)
        self.index.add(raw_vecs)
        self.test_index_path = os.path.join(self.tmpdir.name, "test_index.bin")
        faiss.write_index(self.index, self.test_index_path)

        # Build metadata
        self.test_metadata_path = os.path.join(self.tmpdir.name, "test_metadata.jsonl")
        self.records = [
            {
                "vector_id": i,
                "source_id": f"tweet_{i+100}",
                "customer_message": f"Customer message {i+1}",
                "historical_response": f"AmazonHelp response {i+1}",
            }
            for i in range(self.n_items)
        ]
        with open(self.test_metadata_path, "w", encoding="utf-8") as f:
            for r in self.records:
                f.write(json.dumps(r) + "\n")

        # Mock embedding model
        class MockModel:
            def encode(self, texts, **kwargs):
                vec = np.ones((len(texts), 4), dtype=np.float32)
                faiss.normalize_L2(vec)
                return vec

        self.retriever = SemanticRetriever(
            index_path=self.test_index_path,
            metadata_path=self.test_metadata_path,
            model_instance=MockModel(),
        )

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_search_returns_top_k(self):
        results = self.retriever.search("test query", top_k=3)
        self.assertEqual(len(results), 3)

    def test_search_returns_all_when_k_greater_than_total(self):
        results = self.retriever.search("test query", top_k=10)
        self.assertEqual(len(results), self.n_items)

    def test_search_result_fields(self):
        results = self.retriever.search("test query", top_k=2)
        for r in results:
            self.assertIn("similarity_score", r)
            self.assertIn("source_id", r)
            self.assertIn("customer_message", r)
            self.assertIn("historical_response", r)
            self.assertIsInstance(r["similarity_score"], float)

    def test_similarity_scores_ordered_descending(self):
        results = self.retriever.search("test query", top_k=4)
        scores = [r["similarity_score"] for r in results]
        self.assertEqual(scores, sorted(scores, reverse=True))

    def test_empty_query_returns_empty_list(self):
        self.assertEqual(self.retriever.search(""), [])
        self.assertEqual(self.retriever.search("   "), [])

    def test_metadata_mismatch_raises(self):
        bad_metadata_path = os.path.join(self.tmpdir.name, "bad_meta.jsonl")
        with open(bad_metadata_path, "w") as f:
            f.write(json.dumps({"vector_id": 0, "source_id": "1"}) + "\n")  # only 1 record, index has 5
        with self.assertRaises(ValueError):
            SemanticRetriever(
                index_path=self.test_index_path,
                metadata_path=bad_metadata_path,
                model_instance=self.retriever.model,
            )


class TestRealRetrievalIndex(unittest.TestCase):
    """Tests that run against the actual generated retrieval index and corpus."""

    @classmethod
    def setUpClass(cls):
        if not os.path.exists(INDEX_PATH) or not os.path.exists(METADATA_PATH):
            raise unittest.SkipTest("FAISS index or metadata not yet built.")
        cls.retriever = SemanticRetriever(
            index_path=INDEX_PATH,
            metadata_path=METADATA_PATH,
        )

    def test_index_loaded_successfully(self):
        self.assertGreater(self.retriever.ntotal, 0)
        self.assertEqual(self.retriever.dim, 384)

    def test_real_query_returns_relevant_results(self):
        results = self.retriever.search("where is my package delivery is late", top_k=5)
        self.assertEqual(len(results), 5)
        self.assertGreater(results[0]["similarity_score"], 0.3)
        for r in results:
            self.assertTrue(bool(r["source_id"]))
            self.assertTrue(bool(r["customer_message"]))

    def test_similarity_scores_ordered(self):
        results = self.retriever.search("refund my money", top_k=5)
        scores = [r["similarity_score"] for r in results]
        self.assertEqual(scores, sorted(scores, reverse=True))


class TestGoldenDatasetNotLeaked(unittest.TestCase):
    """Strict verification that 200 golden evaluation tweet IDs are NOT in the retrieval corpus."""

    def test_no_golden_leakage_in_corpus(self):
        if not os.path.exists(GOLDEN_PATH) or not os.path.exists(CORPUS_PATH):
            self.skipTest("Golden dataset or corpus not found.")

        golden_ids = set()
        with open(GOLDEN_PATH, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    rec = json.loads(line.strip())
                    golden_ids.add(str(rec["source_tweet_id"]))

        corpus_ids = set()
        with open(CORPUS_PATH, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    rec = json.loads(line.strip())
                    corpus_ids.add(str(rec.get("source_id", "")))

        overlap = golden_ids & corpus_ids
        self.assertEqual(
            len(overlap), 0,
            f"Leakage detected! Found {len(overlap)} golden tweet IDs in retrieval corpus: {list(overlap)[:5]}"
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
