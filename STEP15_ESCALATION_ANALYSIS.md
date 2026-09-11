# Step 15: Deep Root-Cause Analysis of Escalation Errors

## 1. Context & Motivation

In Step 14, the Hybrid Support Agent achieved **95.0% escalation accuracy** and **91.5% combined accuracy** on the 200-example golden dataset. While this substantially outperformed both the naive RAG agent (68.0% escalation accuracy) and the TF-IDF baseline (94.0%), an in-depth audit of the **10 escalation errors** revealed two distinct systemic issues in the Step 13 escalation layer:

1. **Overly Broad Keyword Risk Scans**: Isolated single-word regex matches (`person`, `police`, `stolen`) fired on benign phrases (e.g., "arrange person to pick up", "driver was there when I called the police", "package stolen yesterday... driver left at wrong house").
2. **Rigid Intent-to-Escalation Mapping**: Defaulting all instances of 7 intents to `ESCALATE` caused informational policy and warranty questions (e.g., "How do I deal with warranty on Amazon Basics?", "What specifies the requirements for Trade-in?") to be rigidly escalated when misrouted to `other_or_unsupported` or `damaged_or_wrong_item`.

---

## 2. Granular Audit of the 10 Step 14 Escalation Errors

| Example ID | Customer Message | Gold Intent | Predicted Intent | Gold Escalation | Step 14 Pred | Root Cause Group | Detailed Root Cause |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **`golden_005`** | *"Hi is there a way to confirm that I make sure my pre-order of WWII gets here on time? Last year was day late."* | `delivery_delay` | `general_product_and_service_faq` | `ESCALATE` | `AUTO_HANDLE` | **Group B: Intent Misclassification** | TF-IDF misclassified query as FAQ $\rightarrow$ Step 13 guardrail rigidly defaulted FAQ to `AUTO_HANDLE`. |
| **`golden_031`** | *"Now I have suffer in self returning product and also not sure that courier charges will be given by Amazon or not. Please arrange person to"* | `order_tracking_inquiry` | `order_tracking_inquiry` | `AUTO_HANDLE` | `ESCALATE` | **Group A: Overly Broad Trigger** | Isolated regex match on word `"person"` triggered human agent override, even though customer meant "arrange courier person for pickup". |
| **`golden_038`** | *"Its very headache so please pick up from your hand. I dont pick up any charges for courier so please arrange from u."* | `order_tracking_inquiry` | `other_or_unsupported` | `AUTO_HANDLE` | `ESCALATE` | **Group C: Rigid Intent Mapping** | TF-IDF predicted `other_or_unsupported` $\rightarrow$ Step 13 guardrail unconditionally forced `ESCALATE` without assessing inquiry context. |
| **`golden_138`** | *"You could ask the other Amazon Delivery driver who was there (and then slinked away when I called the police). I didn't get his name. You should require IDs"* | `driver_and_packaging_feedback` | `driver_and_packaging_feedback` | `AUTO_HANDLE` | `ESCALATE` | **Group A: Overly Broad Trigger** | Isolated regex match on `"police"` triggered high-risk override on general delivery feedback. |
| **`golden_148`** | *"Amazon delivery is the worst!Had a package stolen yesterday..I'm thinking the delivery driver left it at the wrong house..AGAIN!"* | `driver_and_packaging_feedback` | `driver_and_packaging_feedback` | `AUTO_HANDLE` | `ESCALATE` | **Group A: Overly Broad Trigger** | Isolated regex match on `"stolen"` triggered high-risk override on carrier conduct feedback venting. |
| **`golden_156`** | *"While ordering mobile phone I have also ordered a servify accident warranty on 1 year but I am unable to register. Please give a concern!!"* | `general_product_and_service_faq` | `other_or_unsupported` | `AUTO_HANDLE` | `ESCALATE` | **Group C: Rigid Intent Mapping** | TF-IDF predicted `other_or_unsupported` $\rightarrow$ unconditionally forced `ESCALATE`. |
| **`golden_158`** | *"Less than the current price of the item even the unofficial sellers are selling the product on 3rd e website with warranty on purchase"* | `general_product_and_service_faq` | `damaged_or_wrong_item` | `AUTO_HANDLE` | `ESCALATE` | **Group C: Rigid Intent Mapping** | TF-IDF predicted `damaged_or_wrong_item` due to word "warranty" $\rightarrow$ unconditionally forced `ESCALATE`. |
| **`golden_159`** | *"I just reviewed info from that link... I do not see anything that specifies the requirements for Trade-in... am I missing - please advise."* | `general_product_and_service_faq` | `other_or_unsupported` | `AUTO_HANDLE` | `ESCALATE` | **Group C: Rigid Intent Mapping** | Informational Trade-in inquiry misrouted to `other_or_unsupported` $\rightarrow$ unconditionally forced `ESCALATE`. |
| **`golden_161`** | *"How do I deal with the warranty on an Amazon Basics item? The one I'm having a problem with you guys discontinued and don't make anymore. It's a large item."* | `general_product_and_service_faq` | `damaged_or_wrong_item` | `AUTO_HANDLE` | `ESCALATE` | **Group C: Rigid Intent Mapping** | General warranty FAQ misrouted to `damaged_or_wrong_item` $\rightarrow$ unconditionally forced `ESCALATE`. |
| **`golden_164`** | *"I would like it replaced not refunded. But the sale is over, and doesn’t look like you have it in stock at the site. What are my other options?"* | `general_product_and_service_faq` | `other_or_unsupported` | `AUTO_HANDLE` | `ESCALATE` | **Group C: Rigid Intent Mapping** | General catalog replacement policy inquiry misrouted to `other_or_unsupported` $\rightarrow$ unconditionally forced `ESCALATE`. |

---

## 3. Summary of Root Cause Distribution

1. **Group A: Overly Broad Isolated Keyword Triggers (3 cases: 30%)**:
   - Single-word matching without surrounding syntactic context caused false escalations on benign courier pickup requests (`person`) and venting remarks (`police`, `stolen`).
2. **Group C: Rigid Intent-to-Escalation Mapping on Informational Queries (6 cases: 60%)**:
   - Step 13 treated the predicted intent as an absolute deterministic mandate (`intent in DEFAULT_ESCALATE_INTENTS -> ESCALATE`). When benign informational questions (warranty terms, trade-in requirements, out-of-stock options) were slightly misclassified into `other_or_unsupported` or `damaged_or_wrong_item`, they were blindly escalated.
3. **Group B: Intent Classification Inversion (1 case: 10%)**:
   - `delivery_delay` query misclassified as FAQ defaulted to `AUTO_HANDLE`.

---

## 4. Architectural Requirements for Step 15 Context-Aware Escalation

To systematically resolve these failure modes without compromising safety or overengineering:
1. **Level 1 — Contextual Hard Safety Overrides**:
   - Replace single-word regexes with **contextual multi-word patterns** (e.g. `speak to a human`, `talk to an agent`, `unauthorized charge`, `account was hacked`, `legal action`).
2. **Level 2 — Intent as Policy Prior (not unconditional hardcode)**:
   - Use intent as a prior baseline, while recognizing that informational questions (e.g. "how do I...", "what is the policy...", "requirements for...") can be safely auto-handled.
3. **Level 3 — Context / Complexity Assessment**:
   - Distinguish active unresolved disputes / transaction issues (needing human intervention) from general inquiries (resolvable via documentation / self-service links).
