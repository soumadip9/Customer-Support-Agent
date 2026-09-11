# Deep Error Analysis: RAG + Ollama (LLaMA-3.2:3B) on Golden Evaluation Set

**Project:** Hiver AI Customer Support Agent  
**Step:** Step 12 — In-Depth Diagnostic Error Analysis  
**Ground Truth:** `golden_dataset.jsonl` (200 human-verified examples, 13 intent classes)  
**System Analyzed:** `src/llm/agent.py` (`llama3.2:3b` + Top-3 `all-MiniLM-L6-v2` FAISS context)  
**Baseline Reference:** `src/baselines/tfidf_logreg.py` (TF-IDF + Logistic Regression)

---

## 1. Executive Summary

On the 200 human-verified golden evaluation examples:
- **Total Intent Errors**: **115 / 200** (42.5% Intent Accuracy)
- **Total Escalation Errors**: **64 / 200** (68.0% Escalation Accuracy)
- **Total Examples with Any Error**: **119 / 200** (40.5% Combined Accuracy)
- **Comparison to TF-IDF**: TF-IDF achieved **93.0% intent accuracy** and **90.0% combined accuracy** on the exact same dataset.
- **Error Overlap**:
  - **Fixed by RAG**: 9 examples (where TF-IDF failed due to vocabulary/imbalance gaps, but RAG succeeded).
  - **Introduced by RAG**: 108 examples (where TF-IDF succeeded, but RAG failed).
  - **Shared Errors**: 11 examples (both systems failed).

```
                            ┌────────────────────────────────────────┐
                            │    Golden Dataset (200 Examples)       │
                            └───────────────────┬────────────────────┘
                                                │
                     ┌──────────────────────────┴──────────────────────────┐
                     ▼                                                     ▼
        ┌─────────────────────────┐                           ┌─────────────────────────┐
        │     TF-IDF Baseline     │                           │   RAG + LLaMA-3.2:3B    │
        │ Intent Acc:   93.0%     │                           │ Intent Acc:   42.5%     │
        │ Esc Acc:      94.0%     │                           │ Esc Acc:      68.0%     │
        │ Combined Acc: 90.0%     │                           │ Combined Acc: 40.5%     │
        └─────────────────────────┘                           └─────────────────────────┘
```

---

## 2. Top 5 Systemic Failure Modes

| # | Failure Mode | Count | % of 200 | Primary Root Cause Category |
|:---|:---|:---:|:---:|:---|
| **1** | **`order_cancellation` Attractor Bias** | 27 | 13.5% | **C. LLM Reasoning & B. Prompt Framing** |
| **2** | **Total `order_tracking_inquiry` Collapse** | 18 | 9.0% | **D. Taxonomy Ambiguity & C. LLM Reasoning** |
| **3** | **False Escalations on `AUTO_HANDLE` Cases** | 45 | 22.5% | **E. Escalation Policy & C. LLM Reasoning** |
| **4** | **`driver_and_packaging_feedback` → `delivery_delay`** | 7 | 3.5% | **A. Retrieval Distraction & C. LLM Reasoning** |
| **5** | **`digital_and_device_troubleshooting` → `prime_membership_inquiry`** | 5 | 2.5% | **A. Retrieval Distraction & D. Entity Overlap** |

---

## 3. In-Depth Failure Mode Investigation

### Failure Mode 1: `order_cancellation` Attractor Bias (27 Examples, 13.5%)
- **Symptom**: Whenever a customer expressed dissatisfaction, requested a refund, or reported a duplicate payment, the LLM predicted `order_cancellation` instead of the root intent.
  - **10 `refund_inquiry` examples** misclassified as `order_cancellation`
  - **5 `payment_and_billing_issue` examples** misclassified as `order_cancellation`
  - **5 `prime_membership_inquiry` examples** misclassified as `order_cancellation`
  - **3 `promotion_and_discount_inquiry` examples** misclassified as `order_cancellation`
- **Representative Case (`golden_056`)**:
  - *Customer:* `"yes i did, but amazonuk is not doing the refund process. if they do it. i will get it"`
  - *Gold:* `refund_inquiry` (`ESCALATE`)
  - *Predicted:* `order_cancellation` (`ESCALATE`)
  - *LLM Reason:* `"Customer is requesting a refund, but the issue is with the refund process not being initiated by Amazon UK, which suggests a potential problem with the order cancellation process..."`
- **Root Cause**: **C. LLM Reasoning & B. Prompt Framing**. Compact 3B models conflate the *action desired* (stopping the transaction/cancellation) with the *inquiry category* (asking where the refund money is).

---

### Failure Mode 2: Complete `order_tracking_inquiry` Collapse (18 Examples, 9.0%, 0.0% Recall)
- **Symptom**: All 18 ground-truth tracking inquiries were misclassified into other buckets: `other_or_unsupported` (5), `delivery_delay` (4), `driver_and_packaging_feedback` (4), `order_cancellation` (3), `damaged_or_wrong_item` (1), `general_product_and_service_faq` (1).
- **Representative Case (`golden_027`)**:
  - *Customer:* `"@AmazonHelp was told by a representative that my package would be delivered today by 8PM. Still hasn't arrived. Can you check?"`
  - *Gold:* `order_tracking_inquiry` (`AUTO_HANDLE`)
  - *Predicted:* `delivery_delay` (`ESCALATE`)
  - *LLM Reason:* `"The customer is reporting a delayed delivery, as their package has not arrived by the promised time (8 PM today)..."`
- **Root Cause**: **D. Taxonomy Boundary Ambiguity & C. LLM Reasoning**. On Twitter support data, customer messages asking *"where is my order today"* contain expressions of impatience. The 3B model cannot judge the temporal SLA boundary (whether the delivery window is still active vs. overdue) without explicit structured order metadata.

---

### Failure Mode 3: Over-Escalation on `AUTO_HANDLE` Topics (45 Examples, 22.5%)
- **Symptom**: Out of 86 ground-truth `AUTO_HANDLE` examples, the LLM escalated **45 examples to `ESCALATE`** (a **52.3% false alarm rate**).
- **Representative Case (`golden_188`)**:
  - *Customer:* `"I bought a mattress, it is not 150$ cheaper. I asked for a credit. It is still covered under the 100 night guarantee. They have told me I need to return it and repurchase it. I understand that you do not price match, but that is a lot of expense..."`
  - *Gold:* `promotion_and_discount_inquiry` (`AUTO_HANDLE`)
  - *Predicted:* `order_cancellation` (`ESCALATE`)
  - *LLM Reason:* `"The customer is requesting a credit or return/repurchase due to price difference, which involves financial transaction and policy investigation."`
- **Root Cause**: **E. Escalation Policy & C. LLM Reasoning**. The prompt defined `ESCALATE` as anything involving "financial transactions/debits or investigation". The model over-generalized this rule: mentioning dollars, credits, or return logistics triggered escalation even for routine policy inquiries.

---

### Failure Mode 4: `driver_and_packaging_feedback` → `delivery_delay` (7 Examples, 3.5%)
- **Symptom**: 7 feedback cases where the customer complained about delivery drivers (e.g. driver delivery attempts, wrong doorstep drops) were misclassified as late delivery.
- **Representative Case (`golden_141`)**:
  - *Customer:* `"A third pretend attempt by your delivery driver means I'm still without my order. No card left, no knock."`
  - *Gold:* `driver_and_packaging_feedback` (`AUTO_HANDLE`)
  - *Predicted:* `delivery_delay` (`ESCALATE`)
- **Root Cause**: **A. Retrieval Distraction & C. LLM Reasoning**. The semantic retriever matched these queries with general non-delivery and delay tickets because of high dense vector similarity on words like *"delivery"*, *"attempt"*, and *"without my order"*.

---

### Failure Mode 5: `digital_and_device_troubleshooting` → `prime_membership_inquiry` (5 Examples, 2.5%)
- **Symptom**: 5 / 14 digital device and streaming queries were misrouted to Prime membership.
- **Representative Case (`golden_172`)**:
  - *Customer:* `"Also when will Amazon prime music be available for Indian users of Alexa?"`
  - *Gold:* `digital_and_device_troubleshooting` (`AUTO_HANDLE`)
  - *Predicted:* `prime_membership_inquiry` (`AUTO_HANDLE`)
- **Root Cause**: **A. Retrieval Distraction & D. Entity Overlap**. Retrieved historical tweets for "Prime Music" contained Prime subscription FAQ links. The model anchored on the entity token "Prime" rather than the technical capability ("Alexa support").

---

## 4. Retrieval Context Diagnosis: Is Retrieval Helping or Misleading?

| Observation | Impact |
|:---|:---|
| **Stylistic Guidance (Positive)** | The retrieved historical `@AmazonHelp` agent responses helped the model generate highly realistic, polite customer draft responses matching Amazon's official tone. |
| **Semantic Pull / Topic Drift (Negative)** | The retrieval corpus contains unlabelled conversation pairs. When a customer query has overlapping keywords (e.g. *"cancel"*, *"refund"*, *"carrier"*), retrieval surfaces conversational pairs from adjacent intents. Because the 3B model has limited reasoning capacity, it frequently adopted the intent of the retrieved examples rather than the input query. |
| **Recommendation** | Unlabelled dense retrieval alone is insufficient for intent classification in small LLMs. Retrieval should either be **intent-partitioned** (retrieving exemplars conditioned on intent) or the classification stage should be decoupled from open-domain text retrieval. |

---

## 5. What RAG Fixed vs. What RAG Broke (Comparison to TF-IDF)

### A. The 9 Examples Fixed by RAG + Ollama

| ID | Customer Message | Gold Intent | TF-IDF (Failed) | RAG + Ollama (Correct) | Why RAG Succeeded |
|:---:|:---|:---:|:---:|:---:|:---|
| `golden_096` | *"payment did not go through earlier but now the money has been debited twice. Kindly help."* | `payment_and_billing_issue` | `refund_inquiry` | `payment_and_billing_issue` | **Semantic understanding of double debits** without requiring exact n-gram keywords. |
| `golden_097` | *"added Rs.1962 to paybalance, money deducted twice, been more than one hour money still not added."* | `payment_and_billing_issue` | `refund_inquiry` | `payment_and_billing_issue` | Understood **wallet balance recharge failure**. |
| `golden_102` | *"just bought a product, money deducted & now email comes saying I have product limit, cannot buy."* | `payment_and_billing_issue` | `other_or_unsupported` | `payment_and_billing_issue` | Parsed complex transactional state mismatch. |
| `golden_145` | *"seems like somewhat excessive packaging for 2 CDs..."* | `driver_and_packaging_feedback` | `ESCALATE` (Wrong) | `AUTO_HANDLE` (Correct) | Understood feedback nature without triggering unnecessary escalation. |
| `golden_152` | *"I don't understand, based on what will the trade-in accepted or not?"* | `general_product_and_service_faq` | `ESCALATE` (Wrong) | `AUTO_HANDLE` (Correct) | Recognized Trade-In program informational query. |
| `golden_156` | *"ordered a servify accident warranty on 1 year but I am unable to register."* | `general_product_and_service_faq` | `other_or_unsupported` | `general_product_and_service_faq` | Recognized third-party warranty policy question. |
| `golden_159` | *"reviewed info from that link... I do not see anything that specifies the requirements for Trade-in..."* | `general_product_and_service_faq` | `other_or_unsupported` | `general_product_and_service_faq` | Understood catalog policy link clarification. |
| `golden_161` | *"How do I deal with the warranty on an Amazon Basics item? Discontinued item."* | `general_product_and_service_faq` | `damaged_or_wrong_item` | `general_product_and_service_faq` | Distinguished warranty process FAQ from physical item damage report. |
| `golden_189` | *"Wasn't asking for a price match. Just noticed that Amazon keeps changing price..."* | `promotion_and_discount_inquiry` | `ESCALATE` (Wrong) | `AUTO_HANDLE` (Correct) | **Parsed negation syntax** (*"Wasn't asking"*). |

---

### B. The 108 Failures Introduced by RAG
1. **Loss of Discriminative Boundaries**: TF-IDF trained with logistic regression learned sharp discriminative weights across 50,000 features. In contrast, `llama3.2:3b` in zero-shot JSON mode lacks calibrated decision boundaries across 13 classes.
2. **Structural Fragility in JSON Generation**: The 3B model spent substantial parameter capacity maintaining strict JSON formatting, leaving fewer active attention heads for subtle semantic disambiguation.

---

## 6. Recommended High-Impact Architectural Improvements

> [!NOTE]
> These are architectural recommendations based on diagnostic data. No changes are implemented in this step.

### 1. Two-Stage Hybrid Architecture (Discriminative Routing + Generative Drafting)
- **Problem**: The small LLM struggles at 13-way multiclass classification (42.5%), while TF-IDF is highly accurate (93.0%).
- **Solution**: Use the calibrated **TF-IDF classifier as the primary intent router**, and pass the predicted intent + retrieved historical interactions to the LLM **solely for explanation and draft response generation**.

### 2. Intent-Conditioned Retrieval (Partitioned Exemplars)
- **Problem**: Raw open-domain semantic retrieval surfaces cross-intent noise (e.g. refund queries matching cancellation tweets).
- **Solution**: Filter or cluster retrieval candidates by intent class so that exemplars injected into the prompt are pure ground-truth demonstrations of the candidate intent.

### 3. Explicit Escalation Guardrails with Binary Rule Classifier
- **Problem**: High false-escalation rate (52.3%) because the LLM treats all expressions of sentiment as requiring human investigation.
- **Solution**: Enforce deterministic escalation policies based on verified intent (e.g., hardcoded `AUTO_HANDLE` for `order_tracking_inquiry`, `driver_and_packaging_feedback`, and `promotion_and_discount_inquiry` unless explicit security/theft keywords appear).

### 4. Upgrade LLM Backbone / Structured Classifier Head
- **Problem**: 3B local parameters are insufficient for concurrent 13-class zero-shot taxonomy reasoning + escalation triage + JSON formatting.
- **Solution**: Test an 8B model (e.g. `llama3.1:8b` or `qwen2.5:7b`) if local hardware permits, or use a fine-tuned cross-encoder / SetFit classification head.

---

## 7. Artifact Summary

| File | Type | Description |
|:---|:---|:---|
| [`STEP12_ERROR_ANALYSIS.md`](file:///c:/CustomerSupport/STEP12_ERROR_ANALYSIS.md) | New | Complete 200-example diagnostic breakdown, failure mode taxonomy, and architectural recommendations |
| `scratch/deep_error_breakdown.py` | Scratch | Diagnostic script clustering errors across all 200 examples |
| `scratch/examine_retrieval_impact.py` | Scratch | Diagnostic script analyzing retrieved context for failure modes |
| `scratch/error_breakdown.json` | Scratch | Machine-readable breakdown of failure mode IDs |

*No source code, models, golden datasets, or FAISS indices were modified.*
