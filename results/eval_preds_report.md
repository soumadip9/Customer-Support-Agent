# Evaluation Report

| Field | Value |
|:---|:---|
| Ground truth | `C:\Users\prasa\AppData\Local\Temp\tmpi22s5q0h\golden.jsonl` |
| Predictions | `C:\Users\prasa\AppData\Local\Temp\tmpi22s5q0h\preds.jsonl` |
| Model / system | `unknown` |
| Examples evaluated | 6 |

---

## Summary

| Metric | Value |
|:---|:---|
| Intent accuracy | **1.0000** (100.0%) |
| Intent macro F1 | **1.0000** |
| Escalation accuracy | **1.0000** (100.0%) |
| Escalation precision (ESCALATE) | 1.0000 |
| Escalation recall (ESCALATE) | 1.0000 |
| Escalation F1 (ESCALATE) | 1.0000 |
| Combined accuracy (intent + esc both correct) | **1.0000** (100.0%) |

---

## Per-Intent Metrics

| Intent | Precision | Recall | F1 | Support |
|:---|:---:|:---:|:---:|:---:|
| `account_access_and_security` | 0.0000 | 0.0000 | 0.0000 | 0 |
| `damaged_or_wrong_item` | 1.0000 | 1.0000 | 1.0000 | 1 |
| `delivery_delay` | 1.0000 | 1.0000 | 1.0000 | 1 |
| `digital_and_device_troubleshooting` | 0.0000 | 0.0000 | 0.0000 | 0 |
| `driver_and_packaging_feedback` | 0.0000 | 0.0000 | 0.0000 | 0 |
| `general_product_and_service_faq` | 0.0000 | 0.0000 | 0.0000 | 0 |
| `order_cancellation` | 0.0000 | 0.0000 | 0.0000 | 0 |
| `order_tracking_inquiry` | 1.0000 | 1.0000 | 1.0000 | 1 |
| `other_or_unsupported` | 1.0000 | 1.0000 | 1.0000 | 1 |
| `payment_and_billing_issue` | 1.0000 | 1.0000 | 1.0000 | 1 |
| `prime_membership_inquiry` | 0.0000 | 0.0000 | 0.0000 | 0 |
| `promotion_and_discount_inquiry` | 0.0000 | 0.0000 | 0.0000 | 0 |
| `refund_inquiry` | 1.0000 | 1.0000 | 1.0000 | 1 |

---

## Intent Confusion Matrix

Rows = true label · Columns = predicted label

| True \ Pred | AAS | DWI | DD | DDT | DPF | FAQ | OC | OTI | OTH | PBI | PM | PDI | RI |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| `AAS` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `DWI` | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `DD` | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `DDT` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `DPF` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `FAQ` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `OC` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `OTI` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 |
| `OTH` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 |
| `PBI` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 |
| `PM` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `PDI` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `RI` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 |

**Abbreviation key:** `DD`=delivery_delay, `OTI`=order_tracking_inquiry, `OC`=order_cancellation, `RI`=refund_inquiry, `DWI`=damaged_or_wrong_item, `PBI`=payment_and_billing_issue, `PM`=prime_membership_inquiry, `AAS`=account_access_and_security, `DPF`=driver_and_packaging_feedback, `FAQ`=general_product_and_service_faq, `DDT`=digital_and_device_troubleshooting, `PDI`=promotion_and_discount_inquiry, `OTH`=other_or_unsupported

---

## Escalation Confusion Matrix

| True \ Pred | AUTO_HANDLE | ESCALATE |
|:---|:---:|:---:|
| AUTO_HANDLE | 1 | 0 |
| ESCALATE | 0 | 5 |