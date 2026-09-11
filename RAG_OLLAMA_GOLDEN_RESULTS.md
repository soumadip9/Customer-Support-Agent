# RAG + Ollama (LLaMA-3.2:3B) Evaluation Results on Golden Dataset

**Project:** Hiver AI Customer Support Agent  
**Step:** Step 11 — RAG + Ollama Evaluation on Verified Golden Dataset  
**Evaluation Set:** `golden_dataset.jsonl` (200 human-verified examples across 13 intent classes)  
**System Evaluated:** RAG + Local Ollama Agent (`llama3.2:3b`, top-3 FAISS retrieval context)  
**Benchmark Reference:** TF-IDF Baseline (`models/tfidf_intent_classifier.pkl` & `models/tfidf_escalation_classifier.pkl`)

---

## 1. Head-to-Head Comparison: TF-IDF vs. RAG + Ollama (3B)

Both systems were evaluated against the exact same 200 human-verified golden examples using the Step 7 evaluation harness:

| Metric | TF-IDF Baseline | RAG + Ollama (`llama3.2:3b`) | Difference |
|:---|:---:|:---:|:---:|
| **Intent Accuracy** | **0.9300 (93.0%)** | `0.4250 (42.5%)` | **-50.5%** |
| **Intent Macro F1** | **0.9255** | `0.4251` | **-0.5004** |
| **Escalation Accuracy** | **0.9400 (94.0%)** | `0.6800 (68.0%)` | **-26.0%** |
| **Escalation Precision (ESCALATE)** | **0.9113 (91.1%)** | `0.6786 (67.9%)` | **-23.27%** |
| **Escalation Recall (ESCALATE)** | **0.9912 (99.1%)** | `0.8333 (83.3%)` | **-15.79%** |
| **Escalation F1 (ESCALATE)** | **0.9496** | `0.7480` | **-0.2016** |
| **Combined Accuracy (Both Correct)** | **0.9000 (90.0%)** | `0.4050 (40.5%)` | **-49.5%** |

---

## 2. Per-Class Intent Comparison

| Intent Class | Golden Support | TF-IDF Recall | RAG + Ollama Recall | TF-IDF F1 | RAG + Ollama F1 |
|:---|:---:|:---:|:---:|:---:|:---:|
| `delivery_delay` | 20 | **0.9500** | 0.6500 | **0.9268** | 0.5000 |
| `refund_inquiry` | 20 | **1.0000** | 0.2500 | **0.9302** | 0.4000 |
| `order_tracking_inquiry` | 18 | **0.9444** | **0.0000** | **0.9714** | **0.0000** |
| `damaged_or_wrong_item` | 18 | **1.0000** | 0.6667 | **0.9231** | 0.7059 |
| `order_cancellation` | 15 | **1.0000** | 0.7333 | **1.0000** | 0.3929 |
| `prime_membership_inquiry` | 15 | **1.0000** | 0.2667 | **1.0000** | 0.3200 |
| `account_access_and_security` | 15 | **0.9333** | 0.7333 | **0.9655** | 0.8148 |
| `driver_and_packaging_feedback` | 14 | **1.0000** | 0.2143 | **1.0000** | 0.2222 |
| `general_product_and_service_faq` | 14 | **0.6429** | 0.5000 | **0.7500** | 0.4828 |
| `digital_and_device_troubleshooting`| 14 | **1.0000** | 0.2143 | **1.0000** | 0.3529 |
| `payment_and_billing_issue` | 16 | **0.6875** | 0.4375 | **0.8148** | 0.5600 |
| `promotion_and_discount_inquiry` | 11 | **1.0000** | 0.6364 | **1.0000** | 0.6667 |
| `other_or_unsupported` | 10 | **0.9000** | 0.2000 | **0.7500** | 0.1081 |

---

## 3. Detailed Failure Analysis: Why Did RAG + LLaMA-3.2 (3B) Underperform?

Analysis of the 119 misclassified examples revealed clear systemic failure modes stemming from using a compact 3-Billion parameter local model on fine-grained support taxonomy boundaries:

### A. Severe `order_cancellation` Attractor Bias (41 Predicted vs 15 Ground Truth)
- The small 3B model treated `order_cancellation` as an umbrella catch-all for any customer desiring resolution on a problematic order:
  - **10 refund inquiries** misclassified as `order_cancellation` (e.g. *"I want a refund for the product"* → predicted cancellation).
  - **5 payment issue inquiries** misclassified as `order_cancellation` (e.g. *"money deducted twice"* → assumed cancellation needed).
  - **5 Prime membership inquiries** misclassified as `order_cancellation` (e.g. *"cancel my Prime subscription"* → routed to physical order cancellation).

### B. Total Collapse on `order_tracking_inquiry` (0.0% Recall, 0 / 18 Correct)
- The LLM failed to distinguish standard in-transit tracking queries from active delivery delays:
  - 4 tracking queries classified as `delivery_delay`
  - 4 classified as `driver_and_packaging_feedback`
  - 5 classified as `other_or_unsupported`
  - 3 classified as `order_cancellation`
- The model lacked the nuanced threshold logic that asking *"where is my package"* within the expected window is `order_tracking_inquiry` / `AUTO_HANDLE`, whereas complaining about an overdue package is `delivery_delay` / `ESCALATE`.

### C. Digital/Device Troubleshooting vs. Prime Ecosystem
- **5 / 14 digital device troubleshooting requests** (e.g., Kindle e-reader issues, Fire TV app loading errors, Prime Video streaming glitches) were misrouted to `prime_membership_inquiry` because of the presence of the word "Prime" or subscription services in the text.

### D. Over-Escalation (False Alarm Rate: 52.3%)
- The escalation classifier in Ollama predicted `ESCALATE` for **45 out of 86 AUTO_HANDLE examples** (precision on `AUTO_HANDLE`: 68.3%).
- The small model defaulted to `ESCALATE` whenever any customer expressiveness, frustration, or question occurred, defeating the purpose of automation on self-serve topics.

---

## 4. Leakage and Fairness Verification

| Check | Result | Verification Method |
|:---|:---:|:---|
| **No Golden Set Leakage in Retrieval** | **VERIFIED PASS** | 0 / 200 golden `source_tweet_id`s present in `retrieval_corpus.jsonl` (verified by `test_no_golden_leakage_in_corpus`) |
| **No Gold Labels Injected in Prompt** | **VERIFIED PASS** | `build_user_prompt()` takes only `customer_message` + retrieved reference pairs; `intent` and `escalation_decision` fields never exposed |
| **No Retraining or Golden Tuning** | **VERIFIED PASS** | `llama3.2:3b` executed via zero-shot/few-shot in-context inference without parameter updates |
| **Unchanged Retrieval Index** | **VERIFIED PASS** | `models/retrieval/faiss_index.bin` hash unchanged |
| **Unchanged Ollama Model** | **VERIFIED PASS** | Model `llama3.2:3b` used as-is |

---

## 5. Artifacts and Results Files

- Predictions File: [`results/rag_ollama_golden_predictions.jsonl`](file:///c:/CustomerSupport/results/rag_ollama_golden_predictions.jsonl)
- Evaluation JSON: [`results/rag_ollama_golden_evaluation.json`](file:///c:/CustomerSupport/results/rag_ollama_golden_evaluation.json)
- Evaluation Markdown Report: [`results/rag_ollama_golden_evaluation.md`](file:///c:/CustomerSupport/results/rag_ollama_golden_evaluation.md)
- Evaluation Script: [`src/llm/evaluate_golden.py`](file:///c:/CustomerSupport/src/llm/evaluate_golden.py)
