# Step 14: Golden Dataset Evaluation — Hybrid Support Agent

## Executive Summary

In Step 14, the **Hybrid Support Agent** (`HybridSupportAgent`) developed in Step 13 was evaluated against all **200 human-verified examples** in `golden_dataset.jsonl` using the standard Step 7 evaluation harness (`src/evaluation/evaluate.py`).

The Hybrid Support Agent successfully resolves the critical degradation observed in the unconstrained RAG + Ollama system (Step 11/12), elevating performance beyond both the naive LLM and the pure TF-IDF baseline.

---

## 1. Comprehensive System Comparison

| System | Intent Accuracy | Intent Macro F1 | Escalation Accuracy | Escalation F1 | Combined Accuracy (Both Correct) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **1. Majority Baseline** | 10.00% (0.1000) | 0.0140 | 57.00% (0.5700) | 0.7261 | 10.00% (0.1000) |
| **2. TF-IDF Baseline** | 93.00% (0.9300) | 0.9255 | 94.00% (0.9400) | 0.9496 | 90.00% (0.9000) |
| **3. RAG + Ollama (`llama3.2:3b`)** | 42.50% (0.4250) | 0.4251 | 68.00% (0.6800) | 0.7480 | 40.50% (0.4050) |
| **4. Hybrid Support Agent** | **93.00% (0.9300)** | **0.9255** | **95.00% (0.9500)** | **0.9576** | **91.50% (0.9150)** |

---

## 2. Quantitative Performance Deltas

### A. Hybrid vs. TF-IDF Baseline
- **Intent Accuracy**: `93.00%` vs `93.00%` (**0.0% difference**) — Preserved authoritative classification.
- **Intent Macro F1**: `0.9255` vs `0.9255` (**0.0% difference**).
- **Escalation Accuracy**: `95.00%` vs `94.00%` (**+1.00% improvement**, 2 fewer escalation errors).
- **Escalation F1**: `0.9576` vs `0.9496` (**+0.0080 improvement**).
- **Combined Accuracy**: `91.50%` vs `90.00%` (**+1.50% improvement**, 3 additional examples with both intent & escalation correct).

### B. Hybrid vs. Naive RAG + Ollama (`llama3.2:3b`)
- **Intent Accuracy**: `93.00%` vs `42.50%` (**+50.50% absolute improvement** / **+118.8% relative gain**).
- **Intent Macro F1**: `0.9255` vs `0.4251` (**+0.5004 improvement**).
- **Escalation Accuracy**: `95.00%` vs `68.00%` (**+27.00% absolute improvement**).
- **Escalation F1**: `0.9576` vs `0.7480` (**+0.2096 improvement**).
- **Combined Accuracy**: `91.50%` vs `40.50%` (**+51.00% absolute improvement** / **+125.9% relative gain**).

### C. Error Counts on 200 Golden Examples
- **Intent Errors**: 14 errors / 200 (7.0% error rate)
- **Escalation Errors**: 10 errors / 200 (5.0% error rate)
- **Combined Errors**: 17 errors / 200 (8.5% error rate)

---

## 3. Per-Class Intent Breakdown & Recall

| Intent Category | Golden Support | TF-IDF Recall | RAG+Ollama Recall | **Hybrid Agent Recall** | **Hybrid Precision** | **Hybrid F1** |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `order_tracking_inquiry` | 18 | 94.44% | 0.00% | **94.44%** | 100.00% | **0.9714** |
| `prime_membership_inquiry` | 15 | 100.00% | 26.67% | **100.00%** | 100.00% | **1.0000** |
| `digital_and_device_troubleshooting` | 14 | 100.00% | 21.43% | **100.00%** | 100.00% | **1.0000** |
| `driver_and_packaging_feedback` | 14 | 100.00% | 21.43% | **100.00%** | 100.00% | **1.0000** |
| `promotion_and_discount_inquiry` | 11 | 100.00% | 18.18% | **100.00%** | 100.00% | **1.0000** |
| `order_cancellation` | 15 | 100.00% | 73.33% | **100.00%** | 100.00% | **1.0000** |
| `damaged_or_wrong_item` | 18 | 100.00% | 66.67% | **100.00%** | 85.71% | **0.9231** |
| `refund_inquiry` | 20 | 100.00% | 25.00% | **100.00%** | 86.96% | **0.9302** |
| `delivery_delay` | 20 | 95.00% | 65.00% | **95.00%** | 90.48% | **0.9268** |
| `account_access_and_security` | 15 | 93.33% | 73.33% | **93.33%** | 100.00% | **0.9655** |
| `other_or_unsupported` | 10 | 90.00% | 20.00% | **90.00%** | 64.29% | **0.7500** |
| `payment_and_billing_issue` | 16 | 68.75% | 43.75% | **68.75%** | 100.00% | **0.8148** |
| `general_product_and_service_faq` | 14 | 64.29% | 50.00% | **64.29%** | 90.00% | **0.7500** |

---

## 4. Verification of Step 12 Failure Modes

| Step 12 Failure Mode in Naive RAG | Naive RAG Behavior | Hybrid Agent Status | Evidence |
| :--- | :--- | :--- | :--- |
| **1. `order_cancellation` Attractor Bias** | 41 false-positive cancellation predictions; precision collapsed to 26.83%. | **COMPLETELY RESOLVED** | Cancellation precision is **100.0%** (15/15), F1 is **1.0000**. Zero spurious cancellations. |
| **2. Total Tracking Collapse** | 0.0% recall on `order_tracking_inquiry` (18/18 misclassified as delays/cancellations). | **COMPLETELY RESOLVED** | Tracking recall is **94.44%** (17/18), Precision is **100.0%**, F1 is **0.9714**. |
| **3. Digital Device / FAQ Collapse** | 78.57% of digital troubleshooting queries misclassified as Prime or general questions. | **COMPLETELY RESOLVED** | Digital troubleshooting recall is **100.0%** (14/14), Precision is **100.0%**, F1 is **1.0000**. |
| **4. False Escalation Inflation** | Naive LLM escalated 68% of AUTO_HANDLE inquiries unnecessarily. | **COMPLETELY RESOLVED** | Escalation accuracy improved to **95.0%** (77/86 AUTO_HANDLE correctly routed). |
| **5. Hallucinated Non-Taxonomy Labels** | LLM repeatedly generated nonexistent intents (e.g. `prime_video_issue`). | **COMPLETELY RESOLVED** | 100% of predictions belong strictly to the 13 official taxonomy classes. |

---

## 5. Detailed Error Analysis of Hybrid Agent (17 Remaining Discrepancies)

### A. Top Remaining Intent Confusions (14 Total Intent Errors)
1. **`general_product_and_service_faq` $\rightarrow$ `other_or_unsupported` (3 cases: `golden_156`, `golden_159`, `golden_164`)**:
   - Short conversational policy questions lacking specific product keywords.
2. **`payment_and_billing_issue` $\rightarrow$ `refund_inquiry` (3 cases: `golden_093`, `golden_096`, `golden_097`)**:
   - Inquiries mentioning wallet balances, failed payments, and uncredited deductions that use refund-adjacent terminology ("money deducted twice", "payment did not go through").
3. **`general_product_and_service_faq` $\rightarrow$ `damaged_or_wrong_item` (2 cases: `golden_158`, `golden_161`)**:
   - Warranty and replacement questions on Amazon Basics items that contain words like "replaced" or "warranty".
4. **`delivery_delay` $\rightarrow$ `general_product_and_service_faq` (1 case: `golden_005`)**:
   - Pre-delivery question asking to confirm delivery timing before deadline has lapsed.
5. **`account_access_and_security` $\rightarrow$ `damaged_or_wrong_item` (1 case: `golden_131`)**:
   - Customer complaining about checkout app crash while looking for product.

### B. Remaining Escalation Confusions (10 Total Escalation Errors)
- **False Escalations (9 cases)**:
  - 4 cases where explicit risk override triggers correctly caught high-risk keywords in otherwise automated categories (e.g., `golden_031` with "person", `golden_138` with "police", `golden_148` with "stolen"). These false positives represent safety-biased defensive escalations.
  - 5 cases where the intent classifier routed to an ESCALATE intent (`other_or_unsupported` or `damaged_or_wrong_item`) on borderline FAQ messages.
- **Missed Escalation (1 case: `golden_005`)**:
  - `golden_005` was classified as `general_product_and_service_faq` $\rightarrow$ defaulted to `AUTO_HANDLE` instead of `ESCALATE`.

---

## 6. Regression & Integrity Verification

- [x] **Sample Count**: Exactly 200 predictions generated and evaluated.
- [x] **ID Integrity**: Exactly matches `golden_001` through `golden_200` with 0 missing, 0 duplicate, and 0 unexpected IDs.
- [x] **Label Validity**: All 200 predicted intents belong to the 13 valid classes; all 200 escalation decisions are `AUTO_HANDLE` or `ESCALATE`.
- [x] **No Label Leakage**: Ground truth labels (`intent`, `escalation_decision`) were completely shielded from runtime inference.
- [x] **Data & Model Immutability**: `golden_dataset.jsonl`, baseline model binaries (`.pkl`), and FAISS retrieval index were not modified.
- [x] **Full Test Suite**: 107/107 unit and integration tests passing.

---

## 7. Strategic Engineering Conclusion

The evaluation demonstrates that the **Hybrid Support Agent Architecture** represents the optimal engineering balance for enterprise customer support:

1. **Deterministic ML for Mission-Critical Routing**: The TF-IDF logistic regression pipeline provides robust, high-precision intent classification ($93.0\%$ accuracy) resistant to generative drift.
2. **Generative LLM for Customer-Facing Empathy & Drafting**: Local Ollama (`llama3.2:3b`) synthesizes clear, context-aware draft responses conditioned on the fixed intent and retrieved precedent without risking classification errors.
3. **Deterministic Guardrails for Operational Safety**: Taxonomy-driven escalation logic achieves $95.0\%$ escalation accuracy and eliminates dangerous false-automation of sensitive financial or account disputes.

The Hybrid Support Agent outperforms all standalone baselines and unconstrained RAG architectures, delivering a **$91.5\%$ combined accuracy**.
