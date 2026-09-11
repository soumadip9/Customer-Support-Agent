# Evaluation Report

| Field | Value |
|:---|:---|
| Ground truth | `golden_dataset.jsonl` |
| Predictions | `results/smoke_predictions.jsonl` |
| Model / system | `smoke_test_synthetic` |
| Examples evaluated | 200 |

---

## Summary

| Metric | Value |
|:---|:---|
| Intent accuracy | **0.9950** (99.5%) |
| Intent macro F1 | **0.9944** |
| Escalation accuracy | **0.9950** (99.5%) |
| Escalation precision (ESCALATE) | 1.0000 |
| Escalation recall (ESCALATE) | 0.9912 |
| Escalation F1 (ESCALATE) | 0.9956 |
| Combined accuracy (intent + esc both correct) | **0.9900** (99.0%) |

---

## Per-Intent Metrics

| Intent | Precision | Recall | F1 | Support |
|:---|:---:|:---:|:---:|:---:|
| `account_access_and_security` | 1.0000 | 1.0000 | 1.0000 | 15 |
| `damaged_or_wrong_item` | 1.0000 | 1.0000 | 1.0000 | 18 |
| `delivery_delay` | 1.0000 | 0.9500 | 0.9744 | 20 |
| `digital_and_device_troubleshooting` | 1.0000 | 1.0000 | 1.0000 | 14 |
| `driver_and_packaging_feedback` | 1.0000 | 1.0000 | 1.0000 | 14 |
| `general_product_and_service_faq` | 1.0000 | 1.0000 | 1.0000 | 14 |
| `order_cancellation` | 1.0000 | 1.0000 | 1.0000 | 15 |
| `order_tracking_inquiry` | 1.0000 | 1.0000 | 1.0000 | 18 |
| `other_or_unsupported` | 0.9091 | 1.0000 | 0.9524 | 10 |
| `payment_and_billing_issue` | 1.0000 | 1.0000 | 1.0000 | 16 |
| `prime_membership_inquiry` | 1.0000 | 1.0000 | 1.0000 | 15 |
| `promotion_and_discount_inquiry` | 1.0000 | 1.0000 | 1.0000 | 11 |
| `refund_inquiry` | 1.0000 | 1.0000 | 1.0000 | 20 |

---

## Intent Confusion Matrix

Rows = true label · Columns = predicted label

| True \ Pred | AAS | DWI | DD | DDT | DPF | FAQ | OC | OTI | OTH | PBI | PM | PDI | RI |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| `AAS` | 15 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `DWI` | 0 | 18 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `DD` | 0 | 0 | 19 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 |
| `DDT` | 0 | 0 | 0 | 14 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `DPF` | 0 | 0 | 0 | 0 | 14 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `FAQ` | 0 | 0 | 0 | 0 | 0 | 14 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `OC` | 0 | 0 | 0 | 0 | 0 | 0 | 15 | 0 | 0 | 0 | 0 | 0 | 0 |
| `OTI` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 18 | 0 | 0 | 0 | 0 | 0 |
| `OTH` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 10 | 0 | 0 | 0 | 0 |
| `PBI` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 16 | 0 | 0 | 0 |
| `PM` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 15 | 0 | 0 |
| `PDI` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 11 | 0 |
| `RI` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 20 |

**Abbreviation key:** `DD`=delivery_delay, `OTI`=order_tracking_inquiry, `OC`=order_cancellation, `RI`=refund_inquiry, `DWI`=damaged_or_wrong_item, `PBI`=payment_and_billing_issue, `PM`=prime_membership_inquiry, `AAS`=account_access_and_security, `DPF`=driver_and_packaging_feedback, `FAQ`=general_product_and_service_faq, `DDT`=digital_and_device_troubleshooting, `PDI`=promotion_and_discount_inquiry, `OTH`=other_or_unsupported

---

## Escalation Confusion Matrix

| True \ Pred | AUTO_HANDLE | ESCALATE |
|:---|:---:|:---:|
| AUTO_HANDLE | 86 | 0 |
| ESCALATE | 1 | 113 |