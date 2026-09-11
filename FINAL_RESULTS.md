# Final Results: Quantitative Evaluation & Model Benchmarks

This document consolidates the measured, empirical benchmark results across all systems evaluated in the Hiver AI Customer Support project.

---

## 1. 200-Example Golden Benchmark Evaluation

All systems were evaluated blindly against the exact same 200 human-verified examples in `golden_dataset.jsonl` using the standard evaluation harness (`src/evaluation/evaluate.py`).

| System Architecture | Intent Accuracy | Intent Macro F1 | Escalation Accuracy | Escalation F1 | Combined Accuracy (Both Correct) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **1. Majority Baseline** | 10.00% (0.1000) | 0.0140 | 57.00% (0.5700) | 0.7261 | 10.00% (0.1000) |
| **2. TF-IDF Baseline** | 93.00% (0.9300) | 0.9255 | 94.00% (0.9400) | 0.9496 | 90.00% (0.9000) |
| **3. Naive RAG + Ollama (`llama3.2:3b`)** | 42.50% (0.4250) | 0.4251 | 68.00% (0.6800) | 0.7480 | 40.50% (0.4050) |
| **4. Hybrid v1 (Step 13)** | 93.00% (0.9300) | 0.9255 | 95.00% (0.9500) | 0.9576 | 91.50% (0.9150) |
| **5. Hybrid v2 (Context-Aware Escalation)** | **93.00% (0.9300)** | **0.9255** | **97.50% (0.9750)** | **0.9784** | **93.00% (0.9300)** |

### Key Milestones & Progression:
- **TF-IDF vs Majority**: $+83.0\%$ Intent Accuracy, $+37.0\%$ Escalation Accuracy.
- **Hybrid v1 vs Naive RAG**: $+50.5\%$ Intent Accuracy, $+27.0\%$ Escalation Accuracy, $+51.0\%$ Combined Accuracy.
- **Hybrid v2 vs Hybrid v1**: $+2.5\%$ Escalation Accuracy (errors cut in half from 10 to 5), $+1.5\%$ Combined Accuracy, $99.12\%$ safety escalation recall ($113/114$ true escalations caught, 0 critical incidents missed).

---

## 2. 50-Example Response-Quality Evaluation (Human vs. Ollama Judge)

Evaluated across 50 stratified customer interactions from `results/hybrid_v2_golden_predictions.jsonl` using the local `llama3.2:3b` model and independent human review.

### Summary Metrics:
- **Overall Mean Human Score**: **4.43 / 5.00**
- **Overall Mean Ollama Judge Score**: **4.44 / 5.00**
- **Difference between Means**: **+0.01**
- **Overall Exact Agreement**: **56.0%**
- **Overall Agreement within $\pm 1$**: **100.0%**
- **Overall Mean Absolute Difference (MAE)**: **0.11**
- **Overall Quadratic Weighted Cohen's $\kappa$**: **0.7934** (Strong Agreement)
- **Strongest Dimension**: **Policy Compliance & Safety** ($5.00/5$ Human, $4.98/5$ Ollama, $98\%$ exact match)
- **Weakest Dimension**: **Empathy & Tone** ($4.16/5$ Human, $4.26/5$ Ollama, $86\%$ exact match)

### Per-Dimension Agreement Breakdown:

| Evaluation Dimension | Mean Human Score | Mean Ollama Score | Exact Match (%) | Within $\pm 1$ (%) | MAE | Quadratic Weighted $\kappa$ |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Relevance** | 4.40 | 4.00 | 52.0% | 100.0% | 0.48 | 0.0000* |
| **Escalation Actionability** | 4.46 | 4.52 | 86.0% | 100.0% | 0.14 | 0.7209 |
| **Empathy & Tone** | 4.16 | 4.26 | 86.0% | 100.0% | 0.14 | 0.6641 |
| **Policy Compliance & Safety** | 5.00 | 4.98 | 98.0% | 100.0% | 0.02 | 0.0000* |
| **Clarity & Conciseness** | 4.14 | 4.42 | 64.0% | 100.0% | 0.36 | 0.1863 |
| **Overall Composite** | **4.43** | **4.44** | **56.0%** | **100.0%** | **0.11** | **0.7934** |

*\*Note on $\kappa = 0.0000$: When one evaluator assigns a single score to nearly all items (e.g. 5.0 on Policy Safety by Human, 4.0 on Relevance by Ollama), expected marginal chance agreement equals observed agreement, yielding $\kappa = 0.0$ despite $98\%$ and $100\%$ within $\pm 1$ agreement.*
