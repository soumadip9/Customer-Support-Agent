# Semantic Retrieval Component

**Project:** Hiver AI Customer Support Agent  
**Module:** `src/retrieval/`  
**Embedding Model:** `sentence-transformers/all-MiniLM-L6-v2` (384-dimensional dense vectors)  
**Vector Index:** Persistent FAISS `IndexFlatIP` (Cosine Similarity via L2-normalized embeddings)

---

## 1. Why Semantic Retrieval is Added

Traditional keyword and n-gram models (such as TF-IDF) struggle when customers use:
- **Synonyms & paraphrasing** (*"where is my parcel"* vs. *"where is my shipment"* vs. *"hasn't arrived"*)
- **Complex conversational descriptions** (*"driver tossed my package over the fence"* vs. *"driver conduct"*)
- **Negation & contextual framing** (*"wasn't asking for a price match"*)

Dense semantic retrieval maps both customer queries and historical support interactions into a shared continuous embedding space. This allows the AI agent to:
1. Retrieve the **top-K most semantically similar historical customer interactions**.
2. Surface real historical agent responses and domain context to guide downstream classification and response generation.
3. Overcome vocabulary mismatch and surface domain-specific resolution patterns.

---

## 2. Embedding Model Specification

| Property | Value |
|:---|:---|
| **Model Name** | `sentence-transformers/all-MiniLM-L6-v2` |
| **Parameters** | 22.7 Million (lightweight, runs fast on CPU) |
| **Vector Dimension** | 384 dimensions |
| **Max Sequence Length** | 256 tokens |
| **Similarity Metric** | Cosine Similarity via L2-normalized vectors and FAISS `IndexFlatIP` |
| **Execution** | Local execution via PyTorch / HuggingFace Transformers (no external API calls) |

---

## 3. Retrieval Corpus & Ground-Truth Leakage Prevention

### Corpus Source
The historical support corpus is built directly from real `@AmazonHelp` conversations in the TWCS dataset (`archive (4).zip` → `twcs.csv`). Each indexed interaction contains:
- `source_id`: Source tweet ID of the customer message
- `customer_message`: Real inbound customer query
- `historical_response`: Real outbound support response from the `@AmazonHelp` agent

### Strict Leakage Prevention Rule
> [!IMPORTANT]
> The **200 golden evaluation examples** (`golden_dataset.jsonl`) are **strictly excluded** from the retrieval corpus.  
> Before any record is added to `data/retrieval_corpus.jsonl`, its `tweet_id` is cross-referenced against all 200 golden `source_tweet_id`s.  
> This exclusion is continuously verified by `tests/test_retrieval.py::TestGoldenDatasetNotLeaked`.

---

## 4. Architecture & Storage

```
c:\CustomerSupport\
├── data\
│   └── retrieval_corpus.jsonl          # 15,000 extracted customer support Q&A pairs
├── models\
│   └── retrieval\
│       ├── faiss_index.bin             # Persistent FAISS IndexFlatIP binary (22.5 MB)
│       └── corpus_metadata.jsonl       # Metadata mapping vector ID (0..N-1) -> record
└── src\
    └── retrieval\
        ├── __init__.py                 # Module export (SemanticRetriever)
        ├── build_corpus.py             # TWCS extraction pipeline with golden filter
        ├── build_index.py              # Embedding generation & FAISS builder CLI
        └── search.py                   # Semantic search engine & interactive CLI
```

---

## 5. How to Build and Query the Index

### Step A — Extract Corpus from TWCS
```bash
python src/retrieval/build_corpus.py
```

### Step B — Build the FAISS Vector Index
```bash
python -m src.retrieval.build_index --corpus data/retrieval_corpus.jsonl --output-dir models/retrieval/
```

### Step C — Query the Retrieval Component (CLI)

```bash
# Basic top-5 search:
python -m src.retrieval.search --query "my package is several days late" --top-k 5

# Output as raw JSON:
python -m src.retrieval.search --query "money deducted twice for single order" --top-k 3 --json
```

### Step D — Programmatic Usage

```python
from src.retrieval.search import SemanticRetriever

retriever = SemanticRetriever()
results = retriever.search("I need a refund for damaged item", top_k=5)

for r in results:
    print(f"Similarity: {r['similarity_score']:.4f}")
    print(f"Customer:   {r['customer_message']}")
    print(f"Response:   {r['historical_response']}")
```

---

## 6. What Top-K Means

In semantic retrieval, **Top-$K$** represents the number of nearest neighbors retrieved in embedding space, ordered by descending cosine similarity ($[-1.0, 1.0]$):
- **$K=1$ to $K=3$**: Ideal for few-shot prompt augmentation in downstream LLM generation.
- **$K=5$ to $K=10$**: Ideal for intent context voting, historical policy lookup, and FAQ candidate retrieval.

---

## 7. Testing

Run all retrieval unit tests:

```bash
python -m pytest tests/test_retrieval.py -v
```

Verified test coverage:
1. `test_search_returns_top_k`: Returns requested number of items.
2. `test_search_result_fields`: All items have `similarity_score`, `source_id`, `customer_message`, `historical_response`.
3. `test_similarity_scores_ordered_descending`: Monotonically decreasing similarity scores.
4. `test_empty_query_returns_empty_list`: Safe handling of empty queries.
5. `test_metadata_mismatch_raises`: Enforces 1:1 parity between FAISS vectors and metadata rows.
6. `test_no_golden_leakage_in_corpus`: Verifies 0% golden set overlap.
