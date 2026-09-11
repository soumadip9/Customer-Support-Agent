# Evaluation Report

| Field | Value |
|:---|:---|
| Ground truth | `golden_dataset.jsonl` |
| Predictions | `results/rag_ollama_golden_predictions.jsonl` |
| Model / system | `rag_ollama_llama3.2:3b` |
| Examples evaluated | 200 |

---

## Summary

| Metric | Value |
|:---|:---|
| Intent accuracy | **0.4250** (42.5%) |
| Intent macro F1 | **0.4251** |
| Escalation accuracy | **0.6800** (68.0%) |
| Escalation precision (ESCALATE) | 0.6786 |
| Escalation recall (ESCALATE) | 0.8333 |
| Escalation F1 (ESCALATE) | 0.7480 |
| Combined accuracy (intent + esc both correct) | **0.4050** (40.5%) |

---

## Per-Intent Metrics

| Intent | Precision | Recall | F1 | Support |
|:---|:---:|:---:|:---:|:---:|
| `account_access_and_security` | 0.9167 | 0.7333 | 0.8148 | 15 |
| `damaged_or_wrong_item` | 0.7500 | 0.6667 | 0.7059 | 18 |
| `delivery_delay` | 0.4062 | 0.6500 | 0.5000 | 20 |
| `digital_and_device_troubleshooting` | 1.0000 | 0.2143 | 0.3529 | 14 |
| `driver_and_packaging_feedback` | 0.2308 | 0.2143 | 0.2222 | 14 |
| `general_product_and_service_faq` | 0.4667 | 0.5000 | 0.4828 | 14 |
| `order_cancellation` | 0.2683 | 0.7333 | 0.3929 | 15 |
| `order_tracking_inquiry` | 0.0000 | 0.0000 | 0.0000 | 18 |
| `other_or_unsupported` | 0.0741 | 0.2000 | 0.1081 | 10 |
| `payment_and_billing_issue` | 0.7778 | 0.4375 | 0.5600 | 16 |
| `prime_membership_inquiry` | 0.4000 | 0.2667 | 0.3200 | 15 |
| `promotion_and_discount_inquiry` | 0.7000 | 0.6364 | 0.6667 | 11 |
| `refund_inquiry` | 1.0000 | 0.2500 | 0.4000 | 20 |

---

## Intent Confusion Matrix

Rows = true label · Columns = predicted label

| True \ Pred | AAS | DWI | DD | DDT | DPF | FAQ | OC | OTI | OTH | PBI | PM | PDI | RI |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| `AAS` | 11 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 2 | 1 | 0 | 0 | 0 |
| `DWI` | 0 | 12 | 2 | 0 | 0 | 0 | 1 | 0 | 3 | 0 | 0 | 0 | 0 |
| `DD` | 0 | 0 | 13 | 0 | 1 | 1 | 0 | 4 | 1 | 0 | 0 | 0 | 0 |
| `DDT` | 0 | 0 | 0 | 3 | 2 | 2 | 0 | 0 | 2 | 0 | 5 | 0 | 0 |
| `DPF` | 0 | 2 | 7 | 0 | 3 | 0 | 1 | 0 | 1 | 0 | 0 | 0 | 0 |
| `FAQ` | 0 | 1 | 0 | 0 | 0 | 7 | 1 | 1 | 2 | 0 | 0 | 2 | 0 |
| `OC` | 0 | 0 | 1 | 0 | 1 | 0 | 11 | 0 | 2 | 0 | 0 | 0 | 0 |
| `OTI` | 0 | 1 | 4 | 0 | 4 | 1 | 3 | 0 | 5 | 0 | 0 | 0 | 0 |
| `OTH` | 1 | 0 | 1 | 0 | 2 | 4 | 0 | 0 | 2 | 0 | 0 | 0 | 0 |
| `PBI` | 0 | 0 | 1 | 0 | 0 | 0 | 5 | 2 | 0 | 7 | 1 | 0 | 0 |
| `PM` | 0 | 0 | 2 | 0 | 0 | 0 | 5 | 0 | 3 | 0 | 4 | 1 | 0 |
| `PDI` | 0 | 0 | 0 | 0 | 0 | 0 | 3 | 0 | 1 | 0 | 0 | 7 | 0 |
| `RI` | 0 | 0 | 1 | 0 | 0 | 0 | 10 | 0 | 3 | 1 | 0 | 0 | 5 |

**Abbreviation key:** `DD`=delivery_delay, `OTI`=order_tracking_inquiry, `OC`=order_cancellation, `RI`=refund_inquiry, `DWI`=damaged_or_wrong_item, `PBI`=payment_and_billing_issue, `PM`=prime_membership_inquiry, `AAS`=account_access_and_security, `DPF`=driver_and_packaging_feedback, `FAQ`=general_product_and_service_faq, `DDT`=digital_and_device_troubleshooting, `PDI`=promotion_and_discount_inquiry, `OTH`=other_or_unsupported

---

## Escalation Confusion Matrix

| True \ Pred | AUTO_HANDLE | ESCALATE |
|:---|:---:|:---:|
| AUTO_HANDLE | 41 | 45 |
| ESCALATE | 19 | 95 |