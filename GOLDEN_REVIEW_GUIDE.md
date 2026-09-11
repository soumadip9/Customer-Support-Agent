# Golden Dataset Human Review Guide

This guide outlines the instructions for manually annotating and reviewing the 200 customer support messages in [`golden_review.csv`](file:///c:/CustomerSupport/golden_review.csv) to produce the official ground truth evaluation set.

---

## 1. Core Principles for Human Reviewers

1. **Read Every Message Thoroughly:** Carefully evaluate each `customer_message` independently.
2. **Proposed Labels are Suggestions Only:** The `proposed_intent`, `proposed_escalation_decision`, and `proposed_escalation_reason` columns are algorithmic suggestions derived from initial pattern matching. **They do NOT represent ground truth.**
3. **Independent Decision-Making:** You must independently decide:
   - `human_intent`: The single best-fitting intent from the 13 supported categories.
   - `human_escalation_decision`: Either `AUTO_HANDLE` or `ESCALATE`.
   - `human_escalation_reason`: A concise explanation for why escalation is required (mandatory when decision is `ESCALATE`).
   - `review_notes`: Optional notes explaining difficult edge cases or multi-intent nuances.
4. **Use Only Valid Taxonomy Labels:** Do not invent new labels or alter intent spellings.
5. **Embrace `other_or_unsupported`:** Do **not** force ambiguous, conversational, sarcastic, or non-English messages into specific fulfillment intents. If a message is out of scope or unclear, assign `other_or_unsupported` and `ESCALATE`.

---

## 2. Supported Intent Taxonomy (13 Categories)

| Intent Name | Summary Definition | Default Policy | Default Policy Rationale |
| :--- | :--- | :--- | :--- |
| **`delivery_delay`** | Order/package missed scheduled delivery date, is overdue, or shows running late. | `ESCALATE` | Requires checking carrier backend transit systems, rescheduling appointments, or carrier search. |
| **`order_tracking_inquiry`** | Inquiries on parcel location, carrier name, tracking links, or dispatch schedules within normal SLA. | `AUTO_HANDLE` | Safe to provide self-serve tracking link (`https://www.amazon.com/your-orders`) or carrier info without account mutation. |
| **`order_cancellation`** | Request to cancel order, halt shipment, stop accidental duplicate order, or dispute cancellation. | `ESCALATE` | Mutates database order lifecycle and requires checking physical warehouse/carrier dispatch status. |
| **`refund_inquiry`** | Status of pending refund, uncredited return refund, return fees, or money back disputes. | `ESCALATE` | Financial transaction inquiry requiring access to bank payment ledger and refund authorization. |
| **`damaged_or_wrong_item`** | Received item broken, smashed, opened, missing contents, defective, or incorrect product/size. | `ESCALATE` | Requires inspecting damage claims, generating return labels, or authorizing replacement orders. |
| **`payment_and_billing_issue`** | Financial anomalies: duplicate charges, declined card with deduction, unauthorized charge, gift card error. | `ESCALATE` | High-risk financial dispute requiring sensitive customer banking verification. |
| **`prime_membership_inquiry`** | Prime benefits, Household family sharing, student trial terms, or turning off subscription auto-renewal. | `AUTO_HANDLE` | Safe to provide informational links to Prime settings and published program guidelines. |
| **`account_access_and_security`** | 2FA/OTP failures, locked account, password reset, account closure, or suspected account compromise. | `ESCALATE` | Critical security risk requiring strict identity authentication to prevent unauthorized account access. |
| **`digital_and_device_troubleshooting`** | Technical troubleshooting for Kindle, Echo, Fire TV, or digital apps (Prime Video app error, Audible). | `AUTO_HANDLE` | Safe to provide standard technical troubleshooting steps (power cycle, cache clear, app reinstallation). |
| **`promotion_and_discount_inquiry`** | Promotional voucher codes, coupon errors at checkout, Black Friday/Prime Day deal rules, price matching. | `AUTO_HANDLE` | Safe to provide published promotional rules, qualifying item criteria, and price-matching terms. |
| **`driver_and_packaging_feedback`** | Feedback on courier conduct (parking, drop-off behavior) or excessive/poor cardboard packaging without damage. | `AUTO_HANDLE` | Safe to acknowledge feedback empathetically and provide official carrier/packaging feedback submission forms. |
| **`general_product_and_service_faq`** | Public product catalog specifications, stock restock dates, Amazon Trade-In, warranty terms, holiday return window. | `AUTO_HANDLE` | Informational knowledge base retrieval with zero privacy or financial risk. |
| **`other_or_unsupported`** | Non-English messages, conversational chatter ('done', 'thanks'), sarcasm, or ambiguous long-tail queries. | `ESCALATE` | Safe conservative routing to human agents or multilingual support teams. |

---

## 3. Critical Boundary & Disambiguation Rules

When reviewing challenging borderline cases, apply these concrete disambiguation rules:

1. **`order_tracking_inquiry` vs `delivery_delay`:**
   - If the customer explicitly reports a missed deadline (*"late"*, *"overdue"*, *"was supposed to arrive yesterday"*, *"sitting at courier for days"*), classify as `delivery_delay` (`ESCALATE`).
   - If the package is in normal transit and the customer simply requests live tracking links, carrier name, or estimated ETA without claiming a missed deadline, classify as `order_tracking_inquiry` (`AUTO_HANDLE`).

2. **`refund_inquiry` vs `order_cancellation`:**
   - If the primary action is to *stop or abort an active unshipped order*, classify as `order_cancellation` (`ESCALATE`).
   - If the order was *already cancelled, returned, or received* and the customer is inquiring about the *timeline or deposit of funds*, classify as `refund_inquiry` (`ESCALATE`).

3. **`payment_and_billing_issue` vs `prime_membership_inquiry`:**
   - If the customer is disputing an *unauthorized bank/card deduction or duplicate charge* (e.g. unexpected £79 Prime debit), classify as `payment_and_billing_issue` (`ESCALATE`).
   - If the customer is asking about *Prime membership features, sharing, or how to turn off auto-renewal*, classify as `prime_membership_inquiry` (`AUTO_HANDLE`).

4. **`damaged_or_wrong_item` vs `driver_and_packaging_feedback`:**
   - If the *merchandise inside is broken, missing, defective, or incorrect* requiring replacement/refund, classify as `damaged_or_wrong_item` (`ESCALATE`).
   - If the product itself is intact but the customer is commenting on driver conduct (parking across driveway, throwing box) or excessive cardboard waste, classify as `driver_and_packaging_feedback` (`AUTO_HANDLE`).

5. **`digital_and_device_troubleshooting` vs `general_product_and_service_faq`:**
   - If the customer is experiencing an active *technical bug, frozen device, red light error, or app crash*, classify as `digital_and_device_troubleshooting` (`AUTO_HANDLE`).
   - If the customer is asking *general pre-purchase specifications, warranty terms, or trade-in rules*, classify as `general_product_and_service_faq` (`AUTO_HANDLE`).

---

## 4. How to Finalize After Review

Once you have filled in the `human_*` columns for all 200 rows in `golden_review.csv`, run:

```bash
python finalize_golden_dataset.py
```

The script will validate your inputs, ensure strict schema compliance, and generate the authoritative `golden_dataset.jsonl` from your human annotations.
