# Golden Evaluation Dataset Documentation

**Dataset File:** `golden_dataset.jsonl`
**Source Dataset:** Real AmazonHelp Twitter Customer Support Data (`twcs.csv` in `archive (4).zip`)
**Total Records:** 200 curated examples
**Schema Specification:** `id`, `customer_message`, `intent`, `escalation_decision`, `escalation_reason`, `source_tweet_id`

---

## 1. Purpose
The Golden Evaluation Dataset serves as the human-curated ground truth benchmark for rigorously and objectively evaluating the future AI customer support agent.
It establishes authoritative labels for:
1. **Intent Classification Accuracy & Macro-F1:** Testing whether the system can correctly recognize customer intent across 12 distinct support categories and 1 catch-all category.
2. **Conservative Escalation Policy & Safety:** Verifying that high-risk financial, security, and complex fulfillment issues are deterministically escalated, while safe informational FAQs are resolved automatically without dangerous hallucinations or actions.

---

## 2. Dataset Size
- **Total Number of Examples:** **200**
- **Format:** JSON Lines (`.jsonl`), one JSON object per row, UTF-8 encoded.
- **Provenance:** 100% extracted from genuine customer inbound messages in the TWCS dataset, each retaining its verified `source_tweet_id`.

---

## 3. Intent Distribution

The 200 curated examples span the 12 supported primary intents plus the `other_or_unsupported` safety category:

| Intent Name | Example Count | Percentage | Default Policy |
| :--- | :--- | :--- | :--- |
| **`delivery_delay`** | 20 | 10.0% | `ESCALATE` |
| **`refund_inquiry`** | 20 | 10.0% | `ESCALATE` |
| **`order_tracking_inquiry`** | 18 | 9.0% | `AUTO_HANDLE` |
| **`damaged_or_wrong_item`** | 18 | 9.0% | `ESCALATE` |
| **`payment_and_billing_issue`** | 16 | 8.0% | `ESCALATE` |
| **`order_cancellation`** | 15 | 7.5% | `ESCALATE` |
| **`prime_membership_inquiry`** | 15 | 7.5% | `AUTO_HANDLE` |
| **`account_access_and_security`** | 15 | 7.5% | `ESCALATE` |
| **`driver_and_packaging_feedback`** | 14 | 7.0% | `AUTO_HANDLE` |
| **`general_product_and_service_faq`** | 14 | 7.0% | `AUTO_HANDLE` |
| **`digital_and_device_troubleshooting`** | 14 | 7.0% | `AUTO_HANDLE` |
| **`promotion_and_discount_inquiry`** | 11 | 5.5% | `AUTO_HANDLE` |
| **`other_or_unsupported`** | 10 | 5.0% | `ESCALATE` |
| **Total** | **200** | **100.0%** | - |

---

## 4. Escalation Distribution

| Escalation Decision | Count | Percentage | Rationale |
| :--- | :--- | :--- | :--- |
| **`ESCALATE`** | 114 | 57.0% | Financial disputes, returns/refunds, security/credentials, damaged items, overdue delivery investigations, and ambiguous queries. |
| **`AUTO_HANDLE`** | 86 | 43.0% | Safe self-serve tracking links, policy FAQs, device reboot guides, discount voucher terms, and driver feedback logging. |

---

## 5. Selection Methodology
1. **Candidate Pool Extraction:** Inbound messages directed to `@AmazonHelp` were mined and stratified across candidate patterns.
2. **Context & Quality Filtering:** Messages with fewer than 4 words or unhelpful fragments were filtered out, ensuring all selected examples provide sufficient conversational context for a human or LLM to determine intent.
3. **Boundary & Multi-Intent Inclusion:** Challenging borderline examples that test model disambiguation boundaries (e.g. tracking vs delay, refund vs cancellation) were intentionally curated.
4. **Noise & Multilingual Inclusion:** `other_or_unsupported` includes both genuine social noise and real non-English queries (Japanese/Spanish/German/French) to test conservative escalation behavior on out-of-domain inputs.
5. **Deduplication:** Strict deduplication on normalized text and unique tweet IDs to guarantee zero redundant samples.

---

## 6. Quality Checks & Verification
The dataset was programmatically verified via [`validate_golden_dataset.py`](file:///c:/CustomerSupport/validate_golden_dataset.py) with the following verified guarantees:
- [x] **Provenance:** All 200 `source_tweet_id` verified against the raw `twcs.csv` dataset in `archive (4).zip`.
- [x] **Uniqueness:** Zero duplicate tweet IDs or duplicate record IDs.
- [x] **Schema Integrity:** Every record contains non-empty `id`, `customer_message`, `intent`, `escalation_decision`, `escalation_reason`, and `source_tweet_id`.
- [x] **Valid Intent Labels:** All 200 intent labels match the 13 defined taxonomy classes.
- [x] **Valid Escalation Labels:** All 200 escalation decisions are strictly `AUTO_HANDLE` or `ESCALATE` with explicit rationale.
- [x] **Zero Fabrication:** Zero rewritten, synthesized, or modified customer messages.

---

## 7. Representative Difficult / Borderline Examples
The golden dataset contains several subtle edge cases designed to stress-test intent classification and safety boundaries:

### Borderline Case 1: Tracking vs Delivery Delay (Missed Promised SLA)
- **Tweet ID:** `634`
- **Customer Message:** *"@115821 @AmazonHelp why is my order at my local courier for the last 6 days and still hasn’t been delivered to me?? Over 1 week late 😡"*
- **Golden Intent:** `delivery_delay`
- **Golden Escalation:** `ESCALATE`
- **Disambiguation Rationale:** Contains courier/tracking references, but the core issue is an overdue package past promised SLA, requiring carrier investigation rather than a standard self-serve tracking link.

### Borderline Case 2: Cancellation vs Refund Inquiry
- **Tweet ID:** `1730`
- **Customer Message:** *"@AmazonHelp I’ve cancelled my order and gone to Best Buy. Thank you."*
- **Golden Intent:** `order_cancellation`
- **Golden Escalation:** `ESCALATE`
- **Disambiguation Rationale:** Past-tense cancellation statement expressing customer churn and order termination.

### Borderline Case 3: Damaged Goods vs Driver Feedback
- **Tweet ID:** `632`
- **Customer Message:** *"@115830 my package was ‘accidentally’ opened.. 4 items missing worth £97. You need better delivery drivers!! https://t.co/f6SaVBSMqM"*
- **Golden Intent:** `damaged_or_wrong_item`
- **Golden Escalation:** `ESCALATE`
- **Disambiguation Rationale:** Blames delivery drivers, but the critical commercial issue is £97 of missing/stolen goods requiring claims resolution rather than routine driver feedback logging.

### Borderline Case 4: Payment Billing vs Prime Membership
- **Tweet ID:** `31205`
- **Customer Message:** *"@AmazonHelp I see a £79 charge on my credit card from Amazon that I did not authorize. Please investigate immediately."*
- **Golden Intent:** `payment_and_billing_issue`
- **Golden Escalation:** `ESCALATE`
- **Disambiguation Rationale:** The £79 charge corresponds to annual Amazon Prime renewal, but the customer is disputing an unauthorized credit card debit, making it a financial dispute rather than an informational Prime query.

### Borderline Case 5: Multilingual Out-of-Domain Query
- **Tweet ID:** `325`
- **Customer Message:** *"amazonプライムビデオ、再生エラーが多いです"*
- **Golden Intent:** `other_or_unsupported`
- **Golden Escalation:** `ESCALATE`
- **Disambiguation Rationale:** Japanese customer reporting Prime Video streaming playback errors. In an English-targeted support system, non-English messages must be conservatively escalated to multilingual agents.