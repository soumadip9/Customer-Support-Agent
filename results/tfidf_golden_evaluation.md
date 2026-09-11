# Evaluation Report

| Field | Value |
|:---|:---|
| Ground truth | `golden_dataset.jsonl` |
| Predictions | `results/tfidf_golden_predictions.jsonl` |
| Model / system | `tfidf_baseline` |
| Examples evaluated | 200 |

---

## Summary

| Metric | Value |
|:---|:---|
| Intent accuracy | **0.9300** (93.0%) |
| Intent macro F1 | **0.9255** |
| Escalation accuracy | **0.9400** (94.0%) |
| Escalation precision (ESCALATE) | 0.9113 |
| Escalation recall (ESCALATE) | 0.9912 |
| Escalation F1 (ESCALATE) | 0.9496 |
| Combined accuracy (intent + esc both correct) | **0.9000** (90.0%) |

---

## Per-Intent Metrics

| Intent | Precision | Recall | F1 | Support |
|:---|:---:|:---:|:---:|:---:|
| `account_access_and_security` | 1.0000 | 0.9333 | 0.9655 | 15 |
| `damaged_or_wrong_item` | 0.8571 | 1.0000 | 0.9231 | 18 |
| `delivery_delay` | 0.9048 | 0.9500 | 0.9268 | 20 |
| `digital_and_device_troubleshooting` | 1.0000 | 1.0000 | 1.0000 | 14 |
| `driver_and_packaging_feedback` | 1.0000 | 1.0000 | 1.0000 | 14 |
| `general_product_and_service_faq` | 0.9000 | 0.6429 | 0.7500 | 14 |
| `order_cancellation` | 1.0000 | 1.0000 | 1.0000 | 15 |
| `order_tracking_inquiry` | 1.0000 | 0.9444 | 0.9714 | 18 |
| `other_or_unsupported` | 0.6429 | 0.9000 | 0.7500 | 10 |
| `payment_and_billing_issue` | 1.0000 | 0.6875 | 0.8148 | 16 |
| `prime_membership_inquiry` | 1.0000 | 1.0000 | 1.0000 | 15 |
| `promotion_and_discount_inquiry` | 1.0000 | 1.0000 | 1.0000 | 11 |
| `refund_inquiry` | 0.8696 | 1.0000 | 0.9302 | 20 |

---

## Intent Confusion Matrix

Rows = true label · Columns = predicted label

| True \ Pred | AAS | DWI | DD | DDT | DPF | FAQ | OC | OTI | OTH | PBI | PM | PDI | RI |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| `AAS` | 14 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `DWI` | 0 | 18 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `DD` | 0 | 0 | 19 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `DDT` | 0 | 0 | 0 | 14 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `DPF` | 0 | 0 | 0 | 0 | 14 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `FAQ` | 0 | 2 | 0 | 0 | 0 | 9 | 0 | 0 | 3 | 0 | 0 | 0 | 0 |
| `OC` | 0 | 0 | 0 | 0 | 0 | 0 | 15 | 0 | 0 | 0 | 0 | 0 | 0 |
| `OTI` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 17 | 1 | 0 | 0 | 0 | 0 |
| `OTH` | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 9 | 0 | 0 | 0 | 0 |
| `PBI` | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 1 | 11 | 0 | 0 | 3 |
| `PM` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 15 | 0 | 0 |
| `PDI` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 11 | 0 |
| `RI` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 20 |

**Abbreviation key:** `DD`=delivery_delay, `OTI`=order_tracking_inquiry, `OC`=order_cancellation, `RI`=refund_inquiry, `DWI`=damaged_or_wrong_item, `PBI`=payment_and_billing_issue, `PM`=prime_membership_inquiry, `AAS`=account_access_and_security, `DPF`=driver_and_packaging_feedback, `FAQ`=general_product_and_service_faq, `DDT`=digital_and_device_troubleshooting, `PDI`=promotion_and_discount_inquiry, `OTH`=other_or_unsupported

---

## Escalation Confusion Matrix

| True \ Pred | AUTO_HANDLE | ESCALATE |
|:---|:---:|:---:|
| AUTO_HANDLE | 75 | 11 |
| ESCALATE | 1 | 113 |