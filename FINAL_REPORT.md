# Hiver AI Customer Support Agent: Final Project Report

---

## 1. Problem Statement & System Objectives

Modern e-commerce customer support requires processing thousands of customer inquiries per hour with extreme precision, high empathy, policy safety, and fast turnaround. In public social media channels (such as `@AmazonHelp` on Twitter/X), an AI agent must handle three distinct responsibilities simultaneously:

1. **Intent Classification**: Accurately categorize the customer's request into a concrete operational bucket across a diverse 13-class taxonomy.
2. **Escalation Routing**: Correctly decide whether the query can be safely resolved automatically (`AUTO_HANDLE`) via public policy/self-serve guidance or requires human agent intervention (`ESCALATE`) for account access, order modifications, financial refunds, or carrier investigations.
3. **Draft Response Generation**: Produce polite, empathetic, policy-compliant, and brand-appropriate responses grounded in verified customer support knowledge.

A pure generative LLM often hallucinates non-existent policies, leaks private data, or suffers from attractor biases. Conversely, purely rule-based systems lack conversational warmth and contextual grounding. This project builds and evaluates a **Robust Hybrid AI Customer Support Architecture** combining statistical discriminative classifiers, dense semantic retrieval, local LLM generation, and multi-tiered contextual escalation guardrails.

---

## 2. Dataset, Conversation Reconstruction & Golden Evaluation Benchmark

### 2.1 Dataset Analysis & Conversation Graph
The system was trained and evaluated on the public Kaggle **Customer Support on Twitter (TWCS)** dataset:
- **Total Corpus**: 2,811,774 tweets across 108 brands.
- **`@AmazonHelp` Sub-Corpus**: 521,438 tweets (the largest single brand, representing ~18.5% of total volume).
- **Conversation Reconstruction**: By traversing the `in_reply_to_tweet_id` graph, multi-turn dialogue trees were reconstructed into customer-agent interaction pairs ($162,118$ single-turn, $41,202$ two-turn, and $18,432$ multi-turn conversations).

### 2.2 Intent Taxonomy Design
A comprehensive, mutually exclusive, collectively exhaustive 13-class taxonomy was established:
1. `delivery_delay`
2. `order_tracking_inquiry`
3. `order_cancellation`
4. `refund_inquiry`
5. `damaged_or_wrong_item`
6. `payment_and_billing_issue`
7. `prime_membership_inquiry`
8. `account_access_and_security`
9. `driver_and_packaging_feedback`
10. `general_product_and_service_faq`
11. `digital_and_device_troubleshooting`
12. `promotion_and_discount_inquiry`
13. `other_or_unsupported`

### 2.3 Golden Evaluation Benchmark Provenance
To ensure rigorous, leak-free benchmarking, a **200-example Golden Dataset** (`golden_dataset.jsonl`) was curated:
- **Provenance**: Candidate extraction from raw Twitter interactions $\rightarrow$ model-assisted boundary auditing $\rightarrow$ multi-stage human review $\rightarrow$ automated schema validation.
- **Integrity**: Exactly 200 unique records; all tweet IDs strictly held out from the retrieval corpus and baseline training sets (zero data leakage).

---

## 3. System Architecture: The Hybrid Pipeline

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
                                             │ Predicted Intent
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

### Architectural Rationale:
- **Discriminative Authority**: Intent classification is assigned to the trained TF-IDF model ($93.0\%$ accuracy), completely eliminating LLM label hallucination.
- **Contextual Grounding**: FAISS semantic retrieval provides 3 historical `@AmazonHelp` conversation pairs to ground the generative draft in real brand tone.
- **3-Tier Context-Aware Escalation Layer**:
  - *Tier 1 (Hard Safety Overrides)*: High-risk signals (account takeover, fraud, safety threats) force `ESCALATE` regardless of intent.
  - *Tier 2 (Intent Policy Priors)*: Maps operational classes to expected baseline policies.
  - *Tier 3 (Contextual Complexity Disambiguation)*: Distinguishes between active unresolved disputes (`ESCALATE`) vs general informational questions (`AUTO_HANDLE`).

---

## 4. Benchmark Progression & Comparative Results

All systems were evaluated on the exact same 200 golden benchmark interactions:

| System Architecture | Intent Accuracy | Intent Macro F1 | Escalation Accuracy | Escalation F1 | Combined Accuracy (Both Correct) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **1. Majority Baseline** | 10.00% (0.1000) | 0.0140 | 57.00% (0.5700) | 0.7261 | 10.00% (0.1000) |
| **2. TF-IDF Baseline** | 93.00% (0.9300) | 0.9255 | 94.00% (0.9400) | 0.9496 | 90.00% (0.9000) |
| **3. Naive RAG + Ollama (`llama3.2:3b`)** | 42.50% (0.4250) | 0.4251 | 68.00% (0.6800) | 0.7480 | 40.50% (0.4050) |
| **4. Hybrid Support Agent (v1)** | 93.00% (0.9300) | 0.9255 | 95.00% (0.9500) | 0.9576 | 91.50% (0.9150) |
| **5. Hybrid Support Agent (v2 Context-Aware)** | **93.00% (0.9300)** | **0.9255** | **97.50% (0.9750)** | **0.9784** | **93.00% (0.9300)** |

---

## 5. Evaluation Harness & Metrics

- **Harness Implementation**: [`src/evaluation/evaluate.py`](file:///c:/CustomerSupport/src/evaluation/evaluate.py) provides deterministic scoring.
- **Combined Correctness**: Demands that both intent and escalation decision match ground truth simultaneously ($93.00\%$ in Hybrid v2).
- **Safety Recall**: Out of 114 true escalation events in the golden set, Hybrid v2 correctly escalated **113 cases (99.12% recall)** with **zero critical safety misses**.

---

## 6. Response Quality Study: Independent Human vs. Local Ollama Judge

A stratified sample of 50 customer interactions covering all 13 intents was evaluated across 5 quality dimensions (1–5 scale) by both an **Independent Human Reviewer** and the **Local Ollama LLM Judge (`llama3.2:3b`)**:

| Dimension | Human Mean | Ollama Mean | Exact Match (%) | Within $\pm 1$ (%) | MAE | Quadratic Weighted $\kappa$ |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Relevance** | 4.40 | 4.00 | 52.0% | 100.0% | 0.48 | 0.0000* |
| **Escalation Actionability** | 4.46 | 4.52 | 86.0% | 100.0% | 0.14 | 0.7209 |
| **Empathy & Tone** | 4.16 | 4.26 | 86.0% | 100.0% | 0.14 | 0.6641 |
| **Policy Compliance & Safety** | 5.00 | 4.98 | 98.0% | 100.0% | 0.02 | 0.0000* |
| **Clarity & Conciseness** | 4.14 | 4.42 | 64.0% | 100.0% | 0.36 | 0.1863 |
| **Overall Composite** | **4.43** | **4.44** | **56.0%** | **100.0%** | **0.11** | **0.7934** |

### Key Takeaways:
- **Strong Global Calibration**: Mean difference between human and LLM judge is only **$+0.01$**.
- **Consensus**: $100\%$ of all score pairs fell within $\pm 1$ point band; quadratic weighted $\kappa = 0.7934$ reflects strong overall agreement.

---

## 7. Final Top 5 Failure Modes & Mitigations

Analysis of all remaining errors on the 200-example golden set:

1. **`payment_and_billing_issue` $\rightarrow$ `refund_inquiry` (3 cases / 1.5%)**:
   - *Example*: *"added Rs.1962 to paybalance, money deducted twice, but balance not updated"* (`golden_097`).
   - *Root Cause*: Lexical overlap between failed checkout charges and refund terminology.
   - *Mitigation*: Incorporate payment gateway/wallet-specific bigram features into TF-IDF vectorizer.
2. **`general_product_and_service_faq` $\rightarrow$ `other_or_unsupported` (3 cases / 1.5%)**:
   - *Example*: Third-party Servify warranty registration query (`golden_156`).
   - *Root Cause*: Third-party partner terms lack standard retail product keywords.
   - *Mitigation*: Augment FAQ training data with partner warranty and trade-in catalog terms.
3. **`general_product_and_service_faq` $\rightarrow$ `damaged_or_wrong_item` (2 cases / 1.0%)**:
   - *Example*: Price matching and warranty inquiry (`golden_158`).
   - *Root Cause*: "Warranty" and "damaged" tokens trigger defect classifier features.
   - *Mitigation*: Disambiguate price-matching and catalog policy from physical defects.
4. **`order_tracking_inquiry` $\rightarrow$ `other_or_unsupported` (1 case / 0.5%)**:
   - *Example*: Non-standard colloquial delivery complaint (`golden_038`).
   - *Root Cause*: Colloquial grammar without explicit carrier tracking keywords.
   - *Mitigation*: Support slang and informal support text normalization during tokenization.
5. **`delivery_delay` $\rightarrow$ `general_product_and_service_faq` (1 case / 0.5%)**:
   - *Example*: Pre-order delivery date question referencing past year's delay (`golden_005`).
   - *Root Cause*: Ambiguity between hypothetical policy query vs active late shipment.
   - *Mitigation*: Temporal tense detection (past year reference vs active overdue order).

---

## 8. Limitations & Practical Caveats

1. **Benchmark Sample Size**: The golden evaluation benchmark contains 200 interactions, and the judge agreement study includes 50 interactions. While statistically robust for directional validation, production deployment across millions of tweets requires continual sample monitoring.
2. **Lexical Limits of TF-IDF**: While achieving $93.0\%$ accuracy, TF-IDF relies on n-gram co-occurrence and cannot handle highly convoluted syntactic sarcasm or obscure multilingual code-switching.
3. **Local Small LLM Constraints**: Running `llama3.2:3b` locally ensures complete data privacy and zero API costs, but smaller parameter models require strict structured formatting constraints to prevent prompt drift.
4. **Dense Retrieval Without Sparse Hybrid**: FAISS dense embeddings occasionally match on generic conversational phrasing rather than domain-specific order IDs; adding BM25 sparse hybrid retrieval would improve retrieval precision.

---

## 9. Key Engineering Decisions & Trade-Offs

- **Why Local Ollama?**: Complete data privacy, zero external API costs, local reproducibility, and deterministic output.
- **Why TF-IDF as Intent Authority?**: In Step 11, naive RAG LLM intent classification achieved only $42.5\%$ accuracy due to attractor bias. TF-IDF provides deterministic $93.0\%$ accuracy with sub-millisecond latency.
- **Why Context-Aware Escalation?**: Moving from naive keyword triggers to 3-tier contextual guardrails reduced escalation errors by $50\%$ (from 10 errors to 5), while maintaining $99.12\%$ safety recall.

---

## 10. Conclusion & Future Roadmap

The finalized **Context-Aware Hybrid Support Agent (v2)** successfully achieves **93.00% Intent Accuracy**, **97.50% Escalation Accuracy**, **93.00% Combined Accuracy**, and **4.43/5.00 Human Response Quality** with zero external API dependencies and full test coverage (**137/137 tests passing**). Future iterations will introduce hybrid BM25+FAISS reranking and multi-turn session state tracking.
