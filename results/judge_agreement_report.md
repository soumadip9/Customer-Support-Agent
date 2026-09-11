# Step 18: Human Review & Ollama LLM Judge Agreement Analysis

## 1. Executive Overview

This report provides the comparative agreement analysis between the **Local Ollama LLM Judge (`llama3.2:3b`)** and an **Independent Human Reviewer** across **50 stratified customer support responses** from `@AmazonHelp` (`data/human_response_review.csv`).

### Core Evaluation Parameters:
- **LLM Judge**: Local Ollama `llama3.2:3b` (temperature=0.0, deterministic structured JSON)
- **Human Evaluator**: Independent human rating according to [`HUMAN_RESPONSE_REVIEW_GUIDE.md`](file:///c:/CustomerSupport/HUMAN_RESPONSE_REVIEW_GUIDE.md)
- **Sample Size**: 50 interactions covering all 13 customer service intents
- **Overall Mean Ollama Score**: **4.44 / 5.00**
- **Overall Mean Human Score**: **4.43 / 5.00**
- **Difference between Means**: **+0.01**

> [!NOTE]
> **Important Limitation:**
> This agreement analysis is based on a 50-example stratified sample, not the full 200-example golden set. Findings represent this sample and should not be claimed as an exact representation of all 200 responses with certainty.

---

## 2. Quantitative Agreement Metrics

| Dimension | Exact Agreement (%) | Agreement within $\pm 1$ (%) | Mean Absolute Difference (MAE) | Quadratic Weighted Cohen's $\kappa$ | Mean Ollama Score | Mean Human Score |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Relevance** | **52.0%** | 100.0% | 0.48 | **0.0** | 4.0 | 4.4 |
| **Actionability** | **86.0%** | 100.0% | 0.14 | **0.7209** | 4.52 | 4.46 |
| **Empathy / Tone** | **86.0%** | 100.0% | 0.14 | **0.6641** | 4.26 | 4.16 |
| **Policy Safety** | **98.0%** | 100.0% | 0.02 | **0.0** | 4.98 | 5.0 |
| **Clarity** | **64.0%** | 100.0% | 0.36 | **0.1863** | 4.42 | 4.14 |
| **Overall Composite** | **56.0%** | 100.0% | 0.11 | **0.7934** | 4.44 | 4.43 |

---

## 3. Qualitative Agreement & Disagreement Analysis

### Dimensions of Highest Agreement:
1. **Policy Safety (98.0% Exact Agreement, MAE: 0.02)**:
   - Both Ollama and Human evaluators recognized that the generated draft responses strictly complied with Amazon public communication policies (no credentials requested, safe navigation links provided).
2. **Escalation Actionability (86.0% Exact Agreement, 100.0% within $\pm 1$)**:
   - Strong alignment on when human escalation requires requesting order numbers vs providing direct self-serve FAQ links.

### Dimensions of Divergence:
1. **Relevance Nuance**:
   - Ollama rated relevance uniformly at `4.0` across responses where the customer's query had subtle sub-clauses, whereas the human evaluator awarded `5.0` for responses that addressed the customer's core intent with high contextual fidelity (e.g. `rev_016`, `rev_020`).
2. **Empathy & Tone**:
   - Ollama frequently gave 4 stars noting "polite but could be more empathetic", while human evaluators valued the concise, professional Amazon social media standard.

### Magnitude of Disagreements:
- **100% of disagreements were within $\pm 1$ score band**. Zero radical divergences ($\ge 2$ points difference).

---

## 4. Final Response-Quality Assessment (Human Reviewer Perspective)

- **Overall Mean Response Quality**: **4.43 / 5.00**
- **Strongest Dimension**: **Policy Compliance & Safety (5.0 / 5.00)**
- **Weakest Dimension**: **Empathy & Tone (4.16 / 5.00)**

### Representative High-Quality Responses (Score: 4.80–5.00):
- `rev_016` (`golden_074` - Damaged Item): Immediate apology, clear replacement pathway, order verification.
- `rev_020` (`golden_098` - Payment Issue): Clear banking deduction investigation guidance.
- `rev_030` (`golden_125` - Account Security): High-urgency security protocol, direct support phone number and reset flow.

### Representative Moderate Responses (Score: 3.80–4.20):
- `rev_008` (`golden_033` - Tracking vs Return Charges): Helpful tracking link, but partially sidesteps the customer's complaint about return fee burden.
- `rev_038` (`golden_156` - 3rd-Party Warranty): Gives generic support link rather than direct Servify partner warranty registration route.
