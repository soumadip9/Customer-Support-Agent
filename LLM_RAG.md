# Local LLM + RAG Support Agent

**Project:** Hiver AI Customer Support Agent  
**Module:** `src/llm/`  
**LLM Model Used:** `llama3.2:3b` (via local Ollama server at `http://127.0.0.1:11434`)  
**Semantic Retriever:** `all-MiniLM-L6-v2` dense vectors + FAISS `IndexFlatIP` (15,000 interactions)

---

## 1. Architecture Overview

```
Incoming Customer Message
           │
           ▼
  SemanticRetriever (top_k=3)
           │
           ▼
Top-3 Historical AmazonHelp Context
           │
           ▼
  Prompt Builder (13 Intents + Escalation Rules)
           │
           ▼
  Local Cache Lookup (SHA-256 key)
           ├── [HIT]  ──► Return Cached JSON
           └── [MISS] ──► Call Ollama API (/api/generate, format='json')
                               │
                               ▼
                   Strict Schema Validation
                               │
                               ▼
                   Structured Response:
                   - intent
                   - escalation_decision
                   - escalation_reason
                   - draft_response
```

---

## 2. Ollama Model Specification

- **Model Name**: `llama3.2:3b` (Meta LLaMA 3.2, 3 Billion parameters, 2.0 GB local footprint)
- **Local Inference Server**: Ollama (`http://127.0.0.1:11434`)
- **Deterministic Settings**: `temperature: 0.0`, `format: "json"`
- **Zero API Dependency**: All embeddings and LLM calls execute 100% locally on the machine.

---

## 3. Retrieval Augmentation Specification

- **Retriever**: `src.retrieval.search.SemanticRetriever`
- **Default Top-$K$**: `3` historical conversation pairs
- **Context Injected**: Customer message text, historical `@AmazonHelp` agent reply, and similarity score.
- **Reference Guardrail**: The system prompt explicitly instructs the LLM that retrieved historical conversations are **references only** and must not lead to hallucinating order IDs, customer names, or copying stale links.

---

## 4. Structured Output Schema & Strict Validation

Every LLM generation must conform to this exact JSON schema:

```json
{
  "intent": "<exact_intent_from_13_taxonomy_labels>",
  "escalation_decision": "<AUTO_HANDLE | ESCALATE>",
  "escalation_reason": "<non-empty string explaining classification and escalation>",
  "draft_response": "<non-empty professional customer service response>"
}
```

### Validation Enforcement (`validate_structured_output`)
- **Intent**: Must be one of the exact 13 taxonomy labels (`delivery_delay`, `refund_inquiry`, `order_cancellation`, etc.).
- **Escalation Decision**: Must be `AUTO_HANDLE` or `ESCALATE`.
- **Escalation Reason & Draft Response**: Must be non-empty strings.
- **Error Handling**: Any failure in JSON syntax or schema raises `LLMValidationError` immediately without silent degradation.

---

## 5. Caching Mechanism

- **Cache File**: `data/ollama_cache.jsonl`
- **Key Generation**: SHA-256 hash of `(model + ":::" + system_prompt + ":::" + user_prompt)`
- **Behavior**: Avoids redundant LLM inferences on identical queries and ensures fast, reproducible runs.

---

## 6. How to Run the Agent CLI

```bash
# Basic run with default model (llama3.2:3b) and top_k=3:
python -m src.llm.run_agent --message "My package is three days late."

# Output raw JSON:
python -m src.llm.run_agent --message "I was charged twice for the same order." --json

# Customize top-K context:
python -m src.llm.run_agent --message "How can I cancel my order?" --top-k 5
```

---

## 7. Limitations

1. **Local Context Window**: While `llama3.2:3b` handles top-3 context comfortably, very large top-$K$ values ($K > 10$) increase local CPU prompt processing latency.
2. **Deterministic Output vs. Creativity**: Temperature is locked at `0.0` to guarantee consistent intent classification, which can make draft customer responses follow structured templates.
