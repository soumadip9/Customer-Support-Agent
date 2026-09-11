# Architectural Decision Log: Steps 1–18

This document records the chronological decisions, experimental results, failed approaches, and architectural evolution across all 18 engineering steps.

---

## Decision 1: Scope & Dataset Reconstruction (Steps 1–3)
- **Context**: The raw Kaggle TWCS dataset contains 2.8M tweets across 108 brands.
- **Decision**: Filter exclusively to `@AmazonHelp` (521,438 tweets) as the primary domain to ensure high conversational density and concrete operational semantics. Reconstruct multi-turn conversations by traversing the `in_reply_to_tweet_id` graph.
- **Outcome**: Produced clean 1-turn, 2-turn, and multi-turn conversation corpora.

---

## Decision 2: 13-Class Intent Taxonomy & Boundary Rules (Step 4)
- **Context**: Generic taxonomies fail to capture e-commerce operational workflows (e.g. distinguishing `delivery_delay` from `order_tracking_inquiry` or `damaged_or_wrong_item` from `driver_and_packaging_feedback`).
- **Decision**: Define 13 mutually exclusive, collectively exhaustive intent categories with explicit decision trees, boundary rules, and sample validations.
- **Outcome**: Established deterministic evaluation criteria across the entire project.

---

## Decision 3: 200-Example Golden Benchmark & Zero Leakage (Step 5)
- **Context**: Automated benchmarks on synthetic data hide real-world failure modes.
- **Decision**: Curate 200 real Twitter customer interactions from TWCS with multi-stage human and expert verification (`golden_dataset.jsonl`). Enforce strict hold-out: exclude all 200 golden tweet IDs from training sets and the FAISS retrieval corpus.
- **Outcome**: Created an uncompromised evaluation ground truth benchmark.

---

## Decision 4: Deterministic Evaluation Harness & Initial Baselines (Steps 6–8)
- **Context**: Establish baseline reference points for intent and escalation classification.
- **Approaches Tested**:
  1. *Majority Baseline*: Always predicted dominant class (`delivery_delay` and `ESCALATE`).
     - *Result*: 10.0% Intent Accuracy, 57.0% Escalation Accuracy, 10.0% Combined Accuracy.
  2. *TF-IDF + Logistic Regression*: Sublinear TF-IDF word & char n-grams with balanced class weighting.
     - *Result*: 93.0% Intent Accuracy, 94.0% Escalation Accuracy, 90.0% Combined Accuracy.
- **Decision**: Retain TF-IDF model as a fast, high-accuracy baseline.

---

## Decision 5: Semantic Retrieval Engine (Step 9)
- **Context**: Need to retrieve relevant historical AmazonHelp dialogue pairs to ground response generation.
- **Decision**: Use `sentence-transformers/all-MiniLM-L6-v2` (384-dimensional embeddings) to index 15,000 clean customer-agent interactions in a FAISS `IndexFlatIP` index (`models/retrieval/faiss_index.bin`).
- **Outcome**: Sub-10ms top-3 semantic retrieval with 0.65–0.88 cosine similarity on customer support queries.

---

## Decision 6: The Naive RAG + Ollama Failure & Rejection (Steps 10–12)
- **Approach Tested**: Naive End-to-End LLM Agent (`SupportAgent` using local `llama3.2:3b` via Ollama). The LLM was given retrieved examples and asked to predict intent, escalation decision, escalation reason, and draft response in a single generation step.
- **Measured Result**:
  - *Intent Accuracy*: **42.50%** (Massive drop from TF-IDF 93.0%)
  - *Escalation Accuracy*: **68.00%** (Drop from TF-IDF 94.0%)
  - *Combined Accuracy*: **40.50%**
- **Deep Error Analysis (Step 12)**:
  1. *Cancellation Attractor Bias*: The 3B model over-indexed on the word "cancel", misclassifying 47 diverse queries into `order_cancellation`.
  2. *Tracking vs Delay Collapse*: Inability of the small generative model to distinguish between neutral tracking questions and delayed delivery complaints.
  3. *Label Hallucination*: Small LLMs frequently invent non-taxonomy label names when unconstrained.
- **Decision**: **REJECT naive end-to-end LLM for classification.**

---

## Decision 7: Hybrid Agent Architecture (Steps 13–14)
- **Decision**: Decouple discriminative routing from generative drafting:
  - Use the reliable **TF-IDF classifier** as the authoritative intent router ($93.0\%$ accuracy).
  - Use **FAISS** to retrieve top-3 examples relevant to the query.
  - Pass the **fixed intent** and retrieved examples to **Ollama** strictly to generate draft responses.
  - Use deterministic escalation rules.
- **Measured Result (Hybrid v1)**:
  - *Intent Accuracy*: **93.00%** ($+50.5\%$ over Naive RAG)
  - *Escalation Accuracy*: **95.00%** ($+27.0\%$ over Naive RAG)
  - *Combined Accuracy*: **91.50%** ($+51.0\%$ over Naive RAG)

---

## Decision 8: 3-Tier Context-Aware Escalation Layer (Steps 15–16)
- **Context**: Hybrid v1 had 10 escalation errors (9 false escalations triggered by naive isolated keywords like `police`, `person`, `stolen` or benign warranty/trade-in questions).
- **Decision**: Implement a 3-tier Context-Aware Escalation Architecture:
  - *Tier 1*: Hard Safety Overrides (account security breaches, theft, severe complaints $\rightarrow$ `ESCALATE`).
  - *Tier 2*: Intent Policy Priors (baseline policy mappings).
  - *Tier 3*: Contextual Complexity Disambiguation (regex distinction between active unresolved disputes vs informational FAQ questions).
- **Measured Result (Hybrid v2)**:
  - *Escalation Accuracy*: **97.50%** (Escalation errors halved from 10 to 5)
  - *Combined Accuracy*: **93.00%** (Highest benchmark achieved)
  - *Safety Recall*: **99.12%** ($113/114$ true escalations caught, 0 safety-critical misses)

---

## Decision 9: Local Ollama LLM-as-a-Judge & Independent Human Review (Steps 17–18)
- **Context**: Response quality cannot be evaluated purely by classification accuracy. Need a reproducible LLM-as-a-judge quality evaluation with zero external API dependencies, cross-validated against independent human ratings.
- **Decision**:
  - Sample 50 stratified interactions covering all 13 intents with fixed random seed (`seed=42`).
  - Run local Ollama `llama3.2:3b` as an independent quality judge scoring 5 dimensions (Relevance, Escalation Actionability, Empathy/Tone, Policy Safety, Clarity) on a 1–5 scale.
  - Conduct an independent human review without exposing Ollama scores (`data/human_response_review.csv`).
  - Run agreement analysis using Quadratic Weighted Cohen's Kappa.
- **Measured Result**:
  - *Human Mean Quality*: **4.43 / 5.00**
  - *Ollama Judge Mean Quality*: **4.44 / 5.00** (Delta: $+0.01$)
  - *Overall Agreement within $\pm 1$*: **100.0%** ($\text{MAE} = 0.11$, $\kappa = 0.7934$)
  - *Policy Compliance Agreement*: **98.0% exact match** ($\text{MAE} = 0.02$)
