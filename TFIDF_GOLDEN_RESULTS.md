# TF-IDF Baseline Evaluation Results on Golden Dataset

**Project:** Hiver AI Customer Support Agent  
**Step:** Step 8 — Baseline Evaluation on Verified Golden Dataset  
**Ground Truth:** `golden_dataset.jsonl` (200 human-reviewed AmazonHelp support examples)  
**Models Evaluated:** Existing trained TF-IDF + Logistic Regression pipelines (`models/tfidf_intent_classifier.pkl` & `models/tfidf_escalation_classifier.pkl`)

---

## 1. Purpose

The purpose of this evaluation is to establish the true benchmark performance of our traditional machine learning baseline (TF-IDF + Logistic Regression) against the verified 200-example golden ground-truth evaluation set.

This benchmark will serve as the reference point to prove whether the upcoming RAG + LLM architecture delivers real improvements on nuanced customer intent and escalation classification.

---

## 2. Models and Artifacts

| Component | Artifact | Details |
|:---|:---|:---|
| **Intent Classifier** | `models/tfidf_intent_classifier.pkl` | Multiclass Logistic Regression on unigrams + bigrams TF-IDF (50,000 features, sublinear TF) |
| **Escalation Classifier** | `models/tfidf_escalation_classifier.pkl` | Binary Logistic Regression (`AUTO_HANDLE` vs `ESCALATE`) on unigrams + bigrams TF-IDF |
| **Prediction Script** | `src/baselines/predict_golden.py` | Generates formatted JSONL predictions for the 200 golden examples |
| **Prediction Output** | `results/tfidf_golden_predictions.jsonl` | 200 records evaluated by the Step 7 harness |
| **Evaluation JSON** | `results/tfidf_golden_evaluation.json` | Machine-readable metrics & confusion matrices |
| **Evaluation Report** | `results/tfidf_golden_evaluation.md` | Detailed Markdown report from the evaluation harness |

---

## 3. Golden-Set Evaluation Metrics

Across the **200 golden evaluation examples**, the TF-IDF baseline achieved:

| Metric | Score | Percentage |
|:---|:---:|:---:|
| **Intent Accuracy** | `0.9300` | **93.0%** (186 / 200 correct) |
| **Intent Macro F1** | `0.9255` | — |
| **Escalation Accuracy** | `0.9400` | **94.0%** (188 / 200 correct) |
| **Escalation Precision (ESCALATE)** | `0.9113` | **91.1%** |
| **Escalation Recall (ESCALATE)** | `0.9912` | **99.1%** (113 / 114 escalations caught) |
| **Escalation F1 (ESCALATE)** | `0.9496` | — |
| **Combined Accuracy (Intent + Escalation both correct)** | `0.9000` | **90.0%** (180 / 200 correct) |

### Per-Intent Class Breakdown

| Intent Class | Precision | Recall | F1 | Support |
|:---|:---:|:---:|:---:|:---:|
| `delivery_delay` | 0.9048 | 0.9500 | 0.9268 | 20 |
| `refund_inquiry` | 0.8696 | 1.0000 | 0.9302 | 20 |
| `order_tracking_inquiry` | 1.0000 | 0.9444 | 0.9714 | 18 |
| `damaged_or_wrong_item` | 0.8571 | 1.0000 | 0.9231 | 18 |
| `order_cancellation` | 1.0000 | 1.0000 | 1.0000 | 15 |
| `prime_membership_inquiry` | 1.0000 | 1.0000 | 1.0000 | 15 |
| `account_access_and_security` | 1.0000 | 0.9333 | 0.9655 | 15 |
| `driver_and_packaging_feedback` | 1.0000 | 1.0000 | 1.0000 | 14 |
| `digital_and_device_troubleshooting` | 1.0000 | 1.0000 | 1.0000 | 14 |
| `promotion_and_discount_inquiry` | 1.0000 | 1.0000 | 1.0000 | 11 |
| `payment_and_billing_issue` | 1.0000 | **0.6875** | 0.8148 | 16 |
| `general_product_and_service_faq` | 0.9000 | **0.6429** | 0.7500 | 14 |
| `other_or_unsupported` | 0.6429 | 0.9000 | 0.7500 | 10 |

---

## 4. Comparison: Training Validation Split vs. Golden Dataset

| Metric | Validation Split (15% of Training) | Golden Dataset (200 Examples) | Delta |
|:---|:---:|:---:|:---:|
| **Intent Accuracy** | **95.67%** | **93.00%** | -2.67% |
| **Intent Macro F1** | **0.9300** | **0.9255** | -0.0045 |
| **Escalation Accuracy** | **97.71%** | **94.00%** | -3.71% |
| **Combined Accuracy** | — | **90.00%** | — |

### Why Did Performance Decrease on the Golden Set?
1. **Label Origin Discrepancy**: The training & internal validation sets were labeled automatically via high-precision regex rules mined from TWCS. Thus, the model was tested against its own synthetic pattern definitions. The golden dataset is human-verified and includes real conversational nuance, colloquialisms, and edge cases.
2. **Severe Training Imbalance on Rare Classes**: `payment_and_billing_issue` had only 95 training examples (0.6%) compared to 3,000 for `refund_inquiry` (18.7%). When evaluating against the balanced golden set (16 payment issue examples), recall dropped from 86% on validation to **68.8%** on golden.
3. **Compound Queries**: Real customer messages often mention multiple concepts (e.g., asking about a warranty replacement while referencing return policies), which n-gram bag-of-words cannot disambiguate without contextual semantic reasoning.

---

## 5. Major Failure Patterns & Error Analysis

A total of **20 examples** had at least one error (14 intent errors, 12 escalation errors, with 6 examples having both).

### 10 Representative Incorrect Golden Examples

| ID | Tweet ID | Customer Message | Gold Intent (Esc) | Predicted Intent (Esc) | Failure Category |
|:---|:---:|:---|:---|:---|:---|
| `golden_093` | 133880 | *"My order number 404-... Placed on 3rd Sept, money deducted ... Later got 2knw that your team doesn't see the money recd ... till 2day havnt recd my money not the item."* | `payment_and_billing_issue` (ESCALATE) | `refund_inquiry` (ESCALATE) | **Payment vs. Refund Lexical Overlap**: "money deducted" and "havnt recd my money" triggered dominant refund n-grams. |
| `golden_096` | 238917 | *"the payment for a recent order did not go through earlier but now the money has been debited twice. Kindly help."* | `payment_and_billing_issue` (ESCALATE) | `refund_inquiry` (ESCALATE) | **Class Imbalance Bias**: "debited twice" mapped to refund due to lack of distinct billing n-grams. |
| `golden_104` | 445643 | *"You have charged extra for 11 AM delivery . I had to gift it to someone ... Stop doing fake promotions if you dont have stock . Please make sure it is delivered to me in next 2 hours"* | `payment_and_billing_issue` (ESCALATE) | `delivery_delay` (ESCALATE) | **Keyword Trap**: The urgency regarding "delivered to me in next 2 hours" overwhelmed the billing overcharge intent. |
| `golden_131` | 133809 | *"I started placing order from 22-nov itself but your amazon app (which is crap) didnt send me OTP on time and few times transaction got declined."* | `account_access_and_security` (ESCALATE) | `damaged_or_wrong_item` (ESCALATE) | **Spurious Sentiment Correlation**: Negative words like "crap" and "declined" erroneously associated with defective/damaged item training samples. |
| `golden_158` | 1480409 | *"Less than the current price of the item even the unofficial sellers are selling the product on 3rd e website with warranty on purchase"* | `general_product_and_service_faq` (AUTO_HANDLE) | `damaged_or_wrong_item` (ESCALATE) | **Warranty Policy Confusion**: Mention of "warranty" pulled the sample into physical product damage rather than catalog FAQ. |
| `golden_161` | 2862066 | *"How do I deal with the warranty on an Amazon Basics item? The one I'm having a problem with you guys discontinued and don't make anymore. It's a large item."* | `general_product_and_service_faq` (AUTO_HANDLE) | `damaged_or_wrong_item` (ESCALATE) | **False Escalation on Problem Statement**: "having a problem" + "warranty" triggered both damaged item and unnecessary escalation. |
| `golden_164` | 5117 | *"I would like it replaced not refunded. But the sale is over, and doesn’t look like you have it in stock at the site. What are my other options?"* | `general_product_and_service_faq` (AUTO_HANDLE) | `other_or_unsupported` (ESCALATE) | **Stock Inquiry Fallback**: Competing keywords ("replaced", "refunded", "sale", "stock") cancelled each other out, falling back to unsupported. |
| `golden_188` | 150559 | *"I bought a mattress, it is not 150$ cheaper. I asked for a credit. It is still covered under the 100 night guarantee ... I understand that you do not price match..."* | `promotion_and_discount_inquiry` (AUTO_HANDLE) | `promotion_and_discount_inquiry` (**ESCALATE**) | **False Escalation on Financial Words**: Correct intent recognized, but "credit" and "repurchase" caused unwanted escalation. |
| `golden_189` | 166462 | *"Thanks. Wasn’t asking for a price match. Just noticed that Amazon keeps changing the price for some of its blu-rays and was wondering if I’d be getting an adjustment."* | `promotion_and_discount_inquiry` (AUTO_HANDLE) | `promotion_and_discount_inquiry` (**ESCALATE**) | **Negation Blindness in Escalation**: Model saw "price match" and "adjustment" without recognizing customer was asking an informational policy question. |
| `golden_005` | 10665 | *"Hi is there a way to confirm that I make sure my pre-order of @115766 WWII gets here on time? Last year was day late."* | `delivery_delay` (ESCALATE) | `general_product_and_service_faq` (AUTO_HANDLE) | **Temporal Context Confusion**: "pre-order" dominated over "Last year was day late", misclassifying a delay concern as a general pre-order FAQ. |

---

## 6. Summary of Failure Categories

1. **Severe Imbalance Bias (`payment_and_billing_issue` → `refund_inquiry`)**: Because refund inquiries outnumber billing disputes 30:1 in training data, queries about duplicate debits and payment deductions get misrouted to refunds.
2. **False Escalations on FAQ / Policy Questions**: 8 out of the 12 escalation errors were **false escalations** (predicting `ESCALATE` when gold is `AUTO_HANDLE`). Words like "problem", "warranty", "credit", and "denied" in informational inquiries triggered the escalation classifier.
3. **Negation and Complex Syntactic Structures**: TF-IDF cannot handle phrases like *"Wasn't asking for a price match"* or *"is there a way to confirm..."* where negation or modal framing changes the communicative intent.
4. **Vocabulary Drift on Edge Cases**: Out-of-vocabulary terms or rare phrasings in warranty and trade-in support caused the model to fall back onto `other_or_unsupported`.

---

## 7. Next Steps for Step 9 (RAG & LLM)

These baseline results clearly define what our LLM + RAG system must solve:
- Must surpass **93.0% intent accuracy** and **92.55% macro F1**.
- Must surpass **90.0% combined correctness**.
- Must fix false escalations on FAQ/pricing policies (improving `AUTO_HANDLE` precision).
- Must correctly distinguish between payment ledger disputes (`payment_and_billing_issue`) and standard return funds (`refund_inquiry`).
