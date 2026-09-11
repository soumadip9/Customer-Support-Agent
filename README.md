# AI Customer Support Agent for E-Commerce (@AmazonHelp)

An end-to-end, production-grade Customer Support AI Agent built for the `@AmazonHelp` domain using the Kaggle Twitter Customer Support (TWCS) dataset. 

The system implements a **Context-Aware Hybrid Architecture** combining statistical TF-IDF classification, dense semantic retrieval (FAISS), local generative LLM drafting (`llama3.2:3b` via Ollama), and a 3-tier contextual escalation guardrail layer.

---

## Key Achievements

- **Intent Accuracy**: **93.00%** (13 mutually exclusive, collectively exhaustive intent categories)
- **Escalation Accuracy**: **97.50%** (Halved escalation errors from 10 to 5; $99.12\%$ safety recall with 0 critical safety misses)
- **Combined Accuracy**: **93.00%** (Both intent and escalation decision correct simultaneously)
- **Human Response Quality**: **4.43 / 5.00** across 50 independently reviewed customer interactions
- **Local Privacy & Reproducibility**: 100% local execution using Ollama with zero external API dependencies
- **Test Suite**: **137 / 137 tests passing (100% green)**

---

## 1. System Architecture

```
                              ┌─────────────────────────────┐
                              │  Customer Incoming Message  │
                              └──────────────┬──────────────┘
                                             │
                                             ▼
                              ┌─────────────────────────────┐
                              │ TF-IDF + Logistic Regression│
                              │     Authoritative Router    │
                              └──────────────┬──────────────┘
                                             │ Predicted Intent (93.0% Accuracy)
                                             ▼
                              ┌─────────────────────────────┐
                              │   FAISS Semantic Retrieval  │
                              │  (Top-3 Historical Pairs)   │
                              └──────────────┬──────────────┘
                                             │
                                             ▼
                              ┌─────────────────────────────┐
                              │  Local Ollama (llama3.2:3b) │
                              │   Response Draft Generator  │
                              └──────────────┬──────────────┘
                                             │ Draft Response + Candidate Reason
                                             ▼
                              ┌─────────────────────────────┐
                              │ 3-Tier Context-Aware        │
                              │ Escalation Guardrail Layer  │
                              └──────────────┬──────────────┘
                                             │ Final Intent, Escalation & Draft
                                             ▼
                              ┌─────────────────────────────┐
                              │  Customer Support Delivery  │
                              └─────────────────────────────┘
```

### Why a Hybrid Architecture?
In early experiments (Step 11), a naive end-to-end RAG + LLM approach achieved only **42.5% intent accuracy** due to severe cancellation attractor bias and label hallucinations. Decoupling the pipeline resolved this:
1. **Discriminative Router**: TF-IDF provides deterministic, sub-millisecond intent classification ($93.0\%$).
2. **Dense Retriever**: `all-MiniLM-L6-v2` + FAISS provides top-3 real `@AmazonHelp` conversation pairs for in-context grounding.
3. **Local Generative Drafter**: Local `llama3.2:3b` crafts empathetic, brand-appropriate response drafts.
4. **Context-Aware Escalation Layer**: 3-tier rules enforce hard safety overrides (theft/security), intent priors, and active dispute vs informational FAQ disambiguation.

---

## 2. Benchmark Comparison Across All Evaluated Models

All models were evaluated against the exact same 200 human-verified examples in `golden_dataset.jsonl`:

| System Architecture | Intent Accuracy | Intent Macro F1 | Escalation Accuracy | Escalation F1 | Combined Accuracy (Both Correct) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **1. Majority Baseline** | 10.00% (0.1000) | 0.0140 | 57.00% (0.5700) | 0.7261 | 10.00% (0.1000) |
| **2. TF-IDF Baseline** | 93.00% (0.9300) | 0.9255 | 94.00% (0.9400) | 0.9496 | 90.00% (0.9000) |
| **3. Naive RAG + Ollama (`llama3.2:3b`)** | 42.50% (0.4250) | 0.4251 | 68.00% (0.6800) | 0.7480 | 40.50% (0.4050) |
| **4. Hybrid Support Agent (v1)** | 93.00% (0.9300) | 0.9255 | 95.00% (0.9500) | 0.9576 | 91.50% (0.9150) |
| **5. Hybrid Support Agent (v2 Context-Aware)** | **93.00% (0.9300)** | **0.9255** | **97.50% (0.9750)** | **0.9784** | **93.00% (0.9300)** |

---

## 3. Response Quality Study (Human vs. Local Ollama Judge)

A stratified sample of 50 customer interactions covering all 13 intents was evaluated across 5 quality dimensions (1–5 scale) by an **Independent Human Reviewer** and the **Local Ollama LLM Judge (`llama3.2:3b`)**:

| Dimension | Human Mean (1–5) | Ollama Mean (1–5) | Exact Match (%) | Within $\pm 1$ (%) | MAE | Quadratic Weighted Cohen's $\kappa$ |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Relevance & Intent** | 4.40 | 4.00 | 52.0% | 100.0% | 0.48 | 0.0000* |
| **Escalation Actionability** | 4.46 | 4.52 | 86.0% | 100.0% | 0.14 | 0.7209 |
| **Empathy & Tone** | 4.16 | 4.26 | 86.0% | 100.0% | 0.14 | 0.6641 |
| **Policy Compliance & Safety** | 5.00 | 4.98 | 98.0% | 100.0% | 0.02 | 0.0000* |
| **Clarity & Conciseness** | 4.14 | 4.42 | 64.0% | 100.0% | 0.36 | 0.1863 |
| **Overall Composite** | **4.43** | **4.44** | **56.0%** | **100.0%** | **0.11** | **0.7934** |

*\*Note: Quadratic Weighted Cohen's $\kappa = 0.7934$ indicates strong overall inter-rater reliability. Perfect agreement and zero variance on Policy Safety mathematically yields $\kappa = 0.0$ despite $98\%$ exact agreement.*

---

## 4. Repository Structure

```
Customer-Support-Agent/
├── data/
│   ├── human_response_review.csv        # 50-sample human-reviewed evaluation dataset
│   ├── ollama_cache.jsonl               # Persistent inference cache for Ollama
│   ├── ollama_judge_cache.jsonl         # Persistent cache for LLM-as-a-judge
│   ├── retrieval_corpus.jsonl           # 15,000 clean historical interactions
│   └── training_data.jsonl              # Baseline training set
├── models/
│   ├── majority_classifier.pkl          # Majority baseline model
│   ├── tfidf_intent_classifier.pkl      # Trained TF-IDF intent model
│   ├── tfidf_escalation_classifier.pkl  # Trained TF-IDF escalation model
│   └── retrieval/
│       ├── faiss_index.bin              # FAISS IndexFlatIP (384-dim embeddings)
│       └── corpus_metadata.jsonl        # Retrieval metadata lookup
├── results/
│   ├── hybrid_v2_golden_predictions.jsonl # Complete predictions on 200 golden examples
│   ├── hybrid_v2_golden_evaluation.json   # Evaluation metrics JSON
│   ├── ollama_judge_evaluation.jsonl      # 50-item Ollama judge predictions
│   ├── judge_agreement.json               # Human vs Ollama agreement metrics
│   └── judge_agreement_report.md          # Agreement analysis markdown report
├── src/
│   ├── baselines/                       # Baseline training and inference scripts
│   ├── evaluation/                      # Evaluation harness, LLM judge, agreement
│   ├── llm/                             # Hybrid agent and Ollama client
│   └── retrieval/                       # Embedding search and FAISS indexer
├── tests/                               # 137 unit and integration tests
├── golden_dataset.jsonl                 # 200 human-verified golden benchmark
├── FINAL_AUDIT.md                       # Comprehensive compliance audit matrix
├── FINAL_REPORT.md                      # Complete ~6-page technical report
├── FINAL_RESULTS.md                     # Consolidated benchmark results
├── DECISION_LOG.md                      # Chronological architectural decision log
└── README.md                            # Project overview & documentation
```

---

## 5. Quickstart & Installation

### Prerequisites
- Python 3.10+ (tested on Python 3.14)
- [Ollama](https://ollama.com/) installed and running locally

### 1. Clone the Repository
```bash
git clone https://github.com/soumadip9/Customer-Support-Agent.git
cd Customer-Support-Agent
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
# or install core packages:
pip install scikit-learn sentence-transformers faiss-cpu pytest
```

### 3. Setup Local Ollama
Pull and start the local 3B model:
```bash
ollama pull llama3.2:3b
ollama serve
```

---

## 6. How to Run the Agent

### Interactive / Single Query Inference
```python
from src.llm.hybrid_agent import HybridSupportAgent

agent = HybridSupportAgent()

result = agent.process_query("@AmazonHelp Where is my package? It was supposed to arrive yesterday!")
print(f"Predicted Intent: {result['intent']}")
print(f"Escalation Decision: {result['escalation_decision']}")
print(f"Escalation Reason: {result['escalation_reason']}")
print(f"Draft Response: {result['draft_response']}")
```

---

## 7. How to Run Tests & Reproduce Benchmarks

### Run the Complete Test Suite
```bash
pytest tests/ -v
# 137 passed in ~57s
```

### Reproduce Golden Set Evaluation
```bash
python -m src.evaluation.evaluate --golden golden_dataset.jsonl --predictions results/hybrid_v2_golden_predictions.jsonl --output-json results/reproduced_evaluation.json --output-md results/reproduced_evaluation.md
```

### Reproduce Human vs. Ollama Agreement Analysis
```bash
python -m src.evaluation.judge_agreement
```

---

## 8. Remaining Failure Modes & Mitigations

Analysis of all 14 intent and 5 escalation errors remaining in the 200-example golden set:
1. **`payment_and_billing_issue` $\rightarrow$ `refund_inquiry` (3 cases / 1.5%)**: Inquiries involving wallet deductions contain refund-adjacent terms. *Mitigation*: Add payment gateway bigrams to vectorizer.
2. **`general_product_and_service_faq` $\rightarrow$ `other_or_unsupported` (3 cases / 1.5%)**: Third-party warranty registration lacks product keywords. *Mitigation*: Augment FAQ training data with partner service catalogs.
3. **`general_product_and_service_faq` $\rightarrow$ `damaged_or_wrong_item` (2 cases / 1.0%)**: Price matching questions mentioning warranty trigger defect tokens. *Mitigation*: Disambiguate price matching from physical defects.
4. **`order_tracking_inquiry` $\rightarrow$ `other_or_unsupported` (1 case / 0.5%)**: Highly colloquial delivery complaint syntax. *Mitigation*: Support slang text normalization.
5. **`delivery_delay` $\rightarrow$ `general_product_and_service_faq` (1 case / 0.5%)**: Pre-order question referencing previous year's delay. *Mitigation*: Temporal tense detection.

---

## 9. Limitations & Practical Caveats

- **Golden Set Size**: 200 human-verified examples provide strong statistical signal, but full production deployment requires continuous sampling and drift monitoring.
- **TF-IDF Lexical Dependency**: While highly accurate ($93.0\%$), TF-IDF cannot parse complex sarcasm or multilingual code-switching.
- **Dense-Only Retrieval**: Incorporating hybrid BM25 + FAISS reranking would further improve retrieval precision on short tracking codes.

---

## License & Attribution
Built as part of the Hiver AI/SDE Customer Support Engineering Assignment using the open Kaggle Customer Support on Twitter (TWCS) dataset.
