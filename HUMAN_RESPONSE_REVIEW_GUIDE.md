# Human Response Review Guide: Customer Support Quality Assurance

This document defines the evaluation protocol and scoring rubric for human evaluators conducting independent quality reviews of AI-generated customer support responses for `@AmazonHelp`.

---

## 1. Important Instructions for Human Reviewers

> [!IMPORTANT]
> **Independent Review Requirement:**
> - Evaluate the **50 selected customer interactions** in `data/human_response_review.csv`.
> - Do **NOT** look at or use Ollama's scores (`ollama_*`) as guidance.
> - Form your own independent assessment based solely on the `customer_message` and the AI `draft_response`.
> - Fill all `human_*` columns with your ratings (integers 1–5 for dimensions, float for `human_overall_score`, optional notes in `human_notes`).

---

## 2. Multidimensional Scoring Rubric (1–5 Scale)

### A. Relevance & Intent Alignment (`human_relevance_score`)
- **5 (Exemplary)**: Directly and accurately addresses the customer's specific issue and intent.
- **4 (Good)**: Addresses the main issue with minor extra or slightly generic phrasing.
- **3 (Acceptable)**: Partially addresses the issue; misses important nuance or answers at too high a level.
- **2 (Deficient)**: Mostly misses the specific issue or misinterprets customer's core intent.
- **1 (Critical)**: Completely irrelevant, off-topic, or nonsensical.

---

### B. Escalation Appropriateness & Actionability (`human_escalation_actionability_score`)
- **5 (Exemplary)**: Exactly appropriate next steps for the customer's situation. If human investigation is needed (active delay, damaged item, payment failure, compromised account), requests order info or directs to private secure channel. If self-serve/FAQ, provides direct links/instructions.
- **4 (Good)**: Actionable and appropriate, with minor phrasing ambiguity.
- **3 (Acceptable)**: Somewhat actionable, but slightly inappropriate for the escalation level (e.g. suggests self-serve when human intervention is clearly required, or over-escalates a simple FAQ).
- **2 (Deficient)**: Actionable next step is confusing, unhelpful, or asks for wrong information.
- **1 (Critical)**: No useful next step, or sends customer into an unhelpful dead-end loop.

---

### C. Empathy & Customer Tone (`human_empathy_tone_score`)
- **5 (Exemplary)**: Polite, empathetic to customer distress/frustration, professional, concise, brand-appropriate (Amazon CS standard).
- **4 (Good)**: Polite and professional, standard courteous customer service phrasing.
- **3 (Acceptable)**: Neutral or robotic, minimal empathy for a frustrated customer.
- **2 (Deficient)**: Overly defensive, repetitive, robotic, or dismissive.
- **1 (Critical)**: Rude, unprofessional, or hostile.

---

### D. Factuality & Policy Safety (`human_policy_compliance_score`)
- **5 (Exemplary)**: Fully safe, factual, and compliant with Amazon policies. Never asks for private credentials (passwords, PINs, full payment info) over public social media, and makes no false guarantees.
- **4 (Good)**: Generally correct and safe with minor phrasing imprecision.
- **3 (Acceptable)**: Borderline policy guidance or promises an unverified turnaround time.
- **2 (Deficient)**: Serious unsupported guidance or makes unauthorized commitments.
- **1 (Critical)**: Major hallucination, fake tracking details, or unsafe data request.

---

### E. Conciseness & Clarity (`human_clarity_score`)
- **5 (Exemplary)**: Exceptionally clear, crisp, and concise (ideal for social/chat mobile interfaces, ~30–75 words).
- **4 (Good)**: Clear and readable, slightly wordy.
- **3 (Acceptable)**: Understandable but awkward phrasing or overly verbose (>90 words).
- **2 (Deficient)**: Hard to follow, confusing sentence structure, or overly cluttered.
- **1 (Critical)**: Incoherent or garbled.

---

### Overall Score Calculation (`human_overall_score`)
- Compute the arithmetic mean of your 5 dimensional scores rounded to 2 decimal places:
  $$\text{Overall Score} = \frac{\text{Relevance} + \text{Actionability} + \text{Empathy} + \text{Policy} + \text{Clarity}}{5}$$

---

## 3. CSV File Layout (`data/human_response_review.csv`)

| Column Name | Populated By | Value Type | Description |
| :--- | :---: | :---: | :--- |
| `review_id` | System | `rev_001` .. `rev_050` | Sequential review index |
| `source_id` | System | `golden_xxx` | Identifier in golden benchmark |
| `customer_message` | System | Text | Original customer inquiry |
| `draft_response` | System | Text | AI-generated draft response |
| `ollama_*_score` | System | 1–5 / Float | Ollama LLM Judge scores |
| `human_relevance_score` | **Human** | Integer (1–5) | Evaluator relevance score |
| `human_escalation_actionability_score` | **Human** | Integer (1–5) | Evaluator actionability score |
| `human_empathy_tone_score` | **Human** | Integer (1–5) | Evaluator empathy score |
| `human_policy_compliance_score` | **Human** | Integer (1–5) | Evaluator policy score |
| `human_clarity_score` | **Human** | Integer (1–5) | Evaluator clarity score |
| `human_overall_score` | **Human** | Float (1.0–5.0) | Evaluator mean composite score |
| `human_notes` | **Human** | Text (Optional) | Qualitative feedback or observations |
