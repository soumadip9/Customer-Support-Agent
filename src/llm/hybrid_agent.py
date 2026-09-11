"""
src/llm/hybrid_agent.py

Step 15: Context-Aware Hybrid Customer Support Agent.

Marries the high-accuracy TF-IDF intent classifier (93.0% intent accuracy)
with dense FAISS semantic retrieval, local Ollama response generation, and a
3-level Context-Aware Escalation Layer:

Level 1: Deterministic Hard Safety Overrides (Account takeover, fraud, legal threats, human agent requests)
Level 2: Intent Policy Priors (7 Escalation intents vs 6 Automation intents)
Level 3: Context & Inquiry Complexity Assessment (Informational FAQ vs Active Customer-Specific Dispute)
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from typing import Any

# Ensure src/ is on sys.path for unpickling models saved as baselines.*
SRC_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from src.baselines.tfidf_logreg import TfidfIntentClassifier
from src.llm.ollama_client import (
    OllamaClient,
    VALID_DECISIONS,
    VALID_INTENTS,
)
from src.retrieval.search import SemanticRetriever

DEFAULT_INTENT_MODEL_PATH = r"c:\CustomerSupport\models\tfidf_intent_classifier.pkl"
DEFAULT_INDEX_PATH = r"c:\CustomerSupport\models\retrieval\faiss_index.bin"
DEFAULT_METADATA_PATH = r"c:\CustomerSupport\models\retrieval\corpus_metadata.jsonl"

# Taxonomy Intent Metadata & Policy Specifications
INTENT_DEFINITIONS: dict[str, dict[str, str]] = {
    "delivery_delay": {
        "definition": "Package missed promised delivery date, is running late, or overdue.",
        "default_escalation": "ESCALATE",
        "rationale": "Requires checking carrier status, courier investigation, or issuing concession/compensation.",
    },
    "order_tracking_inquiry": {
        "definition": "Inquiring about current tracking status, courier name, or transit ETA within normal delivery timeline.",
        "default_escalation": "AUTO_HANDLE",
        "rationale": "Safe for automated tracking lookup link and carrier guidance without human intervention.",
    },
    "order_cancellation": {
        "definition": "Requesting to cancel an order, stop shipment, or dispute an unexpected cancellation.",
        "default_escalation": "ESCALATE",
        "rationale": "Mutates order lifecycle and requires backend fulfillment intervention.",
    },
    "refund_inquiry": {
        "definition": "Asking for a refund status on returned/cancelled items, or inquiring when refund will credit to bank.",
        "default_escalation": "ESCALATE",
        "rationale": "Financial transaction inquiry requiring payment ledger and refund authorization.",
    },
    "damaged_or_wrong_item": {
        "definition": "Reporting broken, defective, crushed, missing items, or wrong product/size received.",
        "default_escalation": "ESCALATE",
        "rationale": "Requires return label generation, replacement authorization, or damage claim processing.",
    },
    "payment_and_billing_issue": {
        "definition": "Duplicate credit card charges, unauthorized transactions, or payment failure with money debited.",
        "default_escalation": "ESCALATE",
        "rationale": "High-risk financial dispute requiring sensitive account and payment ledger access.",
    },
    "prime_membership_inquiry": {
        "definition": "Inquiring about Prime benefits, membership fee rules, Household sharing, or student plans.",
        "default_escalation": "AUTO_HANDLE",
        "rationale": "Informational inquiry resolvable with self-service Prime settings links.",
    },
    "account_access_and_security": {
        "definition": "Locked account, 2FA/OTP code not received, password reset issues, or compromised login.",
        "default_escalation": "ESCALATE",
        "rationale": "Critical security issue requiring strict identity authentication and agent oversight.",
    },
    "digital_and_device_troubleshooting": {
        "definition": "Kindle, Alexa, Echo, Fire TV, or Amazon app errors, settings, or setup problems.",
        "default_escalation": "AUTO_HANDLE",
        "rationale": "Technical troubleshooting steps and device restart/settings guidance are automated.",
    },
    "promotion_and_discount_inquiry": {
        "definition": "Promo codes, coupons, promotional discounts, or sale pricing inquiries.",
        "default_escalation": "AUTO_HANDLE",
        "rationale": "Self-service promo terms, checkout voucher field instructions, and discount rules.",
    },
    "driver_and_packaging_feedback": {
        "definition": "Feedback on delivery carrier conduct or packaging size/materials where item itself is intact.",
        "default_escalation": "AUTO_HANDLE",
        "rationale": "Safe for automated logging and carrier/packaging feedback form routing.",
    },
    "general_product_and_service_faq": {
        "definition": "Policy questions on trade-in program, warranty coverage, or catalog stock availability.",
        "default_escalation": "AUTO_HANDLE",
        "rationale": "Public FAQ documentation and catalog policy guidance.",
    },
    "other_or_unsupported": {
        "definition": "Non-English messages, greetings without support context, or ambiguous conversational fragments.",
        "default_escalation": "ESCALATE",
        "rationale": "Unclear or unsupported customer intent requiring human agent triage.",
    },
}

DEFAULT_ESCALATE_INTENTS: frozenset[str] = frozenset({
    "delivery_delay",
    "order_cancellation",
    "refund_inquiry",
    "damaged_or_wrong_item",
    "payment_and_billing_issue",
    "account_access_and_security",
    "other_or_unsupported",
})

DEFAULT_AUTOHANDLE_INTENTS: frozenset[str] = frozenset({
    "order_tracking_inquiry",
    "prime_membership_inquiry",
    "digital_and_device_troubleshooting",
    "promotion_and_discount_inquiry",
    "driver_and_packaging_feedback",
    "general_product_and_service_faq",
})

# ==============================================================================
# LEVEL 1: HARD SAFETY OVERRIDES (Contextual Multi-Word Patterns)
# ==============================================================================
HARD_SAFETY_PATTERNS = [
    # Explicit demand to speak with a human/agent/representative
    (
        re.compile(
            r"\b(speak|talk|transfer|connect|pass|switch)\b.{1,30}\b(to|with)\b.{1,20}\b(human|agent|representative|supervisor|manager|real person|someone)\b|"
            r"\b(need|want|give me)\b.{1,15}\b(a |an )?(human|agent|representative|supervisor|manager|real person)\b|"
            r"\b(human|agent|representative|supervisor)\s+(please|now|immediately)\b",
            re.IGNORECASE,
        ),
        "Explicit customer request to speak with a human agent.",
    ),
    # Account compromise, hacking, or unauthorized login
    (
        re.compile(
            r"\b(account\s+(is\s+|was\s+|has been\s+)?(hacked|compromised|breached|taken over|unauthorized login))\b|"
            r"\b(someone\s+(else\s+)?(logged\s+in\s+to|logged\s+into|accessed|hacked|using)\s+my\s+account)\b|"
            r"\b(unauthorized\s+(access|login|password change|email change))\b",
            re.IGNORECASE,
        ),
        "High-risk account compromise or unauthorized security event.",
    ),
    # Explicit unauthorized or fraudulent transaction
    (
        re.compile(
            r"\b(unauthorized|fraudulent|unrecognized)\s+(charge|payment|transaction|fee|debit)\b|"
            r"\b(don't|dont|do not|cannot|cant)\s+recognize\s+(this|the|a|any)?\s*(charge|payment|transaction|fee|debit)\b|"
            r"\b(card|credit card|debit card)\s+(was\s+|is\s+)?(stolen|cloned|compromised|fraud)\b|"
            r"\b(did not authorize|never made this (purchase|order|charge))\b",
            re.IGNORECASE,
        ),
        "Financial fraud or unauthorized payment dispute requiring immediate ledger investigation.",
    ),
    # Legal threats, regulatory action, or severe physical safety violations
    (
        re.compile(
            r"\b(legal action|contact(ing)?\s+(my\s+)?lawyer|attorney|taking you to court|police report|trading standards|better business bureau)\b|"
            r"\b(driver\s+(threatened|assaulted|hit|trespassed|damaged my))\b",
            re.IGNORECASE,
        ),
        "Severe legal or physical safety escalation requiring immediate supervisor review.",
    ),
    # Direct theft report requiring claims filing
    (
        re.compile(
            r"\b(my\s+package\s+(was|got)\s+stolen\b|stolen\s+package\b|package\s+was\s+stolen\b)",
            re.IGNORECASE,
        ),
        "Stolen package claim requiring courier carrier investigation.",
    ),
]

# ==============================================================================
# LEVEL 3: CONTEXT & INQUIRY COMPLEXITY PATTERNS
# ==============================================================================
# Patterns that signify an informational / procedural inquiry (safe to automate)
INFORMATIONAL_PATTERNS = [
    re.compile(r"^(how (do i|can i|to|does)|what (is|are) (the|your)|where (can i|do i|is)|when (will|does|can))\b", re.IGNORECASE),
    re.compile(r"\b(how long (do|does|will)\b.*\b(take|last|arrive))\b", re.IGNORECASE),
    re.compile(r"\b(is it possible to|can (i|you|we) (trade|price match|cancel|return|use|share|exchange))\b", re.IGNORECASE),
    re.compile(r"\b(how do i deal with (the )?warranty|requirements for (trade-in|prime|return)|policy on)\b", re.IGNORECASE),
    re.compile(r"\b(do you (accept|have|offer|ship to)|what are (the|my) (options|rules|terms))\b", re.IGNORECASE),
]

# Patterns that signify an active, unresolved customer dispute / transaction issue (requires escalation)
ACTIVE_DISPUTE_PATTERNS = [
    re.compile(r"\b(not (arrived|received|delivered|credited|refunded)|never (arrived|came|received))\b", re.IGNORECASE),
    re.compile(r"\b(still (waiting|haven't|havent|pending|not received))\b", re.IGNORECASE),
    re.compile(r"\b(\d+\s+(days|weeks|hours)\s+(late|overdue|ago))\b", re.IGNORECASE),
    re.compile(r"\b(charged twice|double charged|money deducted|deducted twice|payment failed but money)\b", re.IGNORECASE),
    re.compile(r"\b(broken|shattered|crushed|smashed|damaged|wrong item|missing (item|items|parts))\b", re.IGNORECASE),
    re.compile(r"\b(cancel (my|this|the)\s+order\b|please cancel order\b)", re.IGNORECASE),
]


def assess_contextual_escalation(
    intent: str,
    customer_message: str,
    llm_reason: str = "",
) -> tuple[str, str]:
    """
    3-Level Context-Aware Escalation Assessment Engine.
    
    Level 1: Hard safety overrides (deterministic safety rules).
    Level 2: Intent policy baseline prior.
    Level 3: Contextual inquiry complexity (Informational FAQ vs Active Dispute).
    """
    clean_msg = customer_message.strip()

    # --------------------------------------------------------------------------
    # LEVEL 1: HARD SAFETY OVERRIDES
    # --------------------------------------------------------------------------
    for pattern, reason in HARD_SAFETY_PATTERNS:
        if pattern.search(clean_msg):
            return "ESCALATE", f"Hard safety override: {reason}"

    # --------------------------------------------------------------------------
    # LEVEL 3: CONTEXTUAL COMPLEXITY EVALUATION
    # --------------------------------------------------------------------------
    is_informational = any(p.search(clean_msg) for p in INFORMATIONAL_PATTERNS)
    is_active_dispute = any(p.search(clean_msg) for p in ACTIVE_DISPUTE_PATTERNS)

    # If the inquiry is clearly a general procedural/FAQ inquiry without an active dispute,
    # it is safe to AUTO_HANDLE even under nominal escalation intents (e.g. warranty questions,
    # "how long do refunds take?", general cancellation policy, trade-in requirements).
    if is_informational and not is_active_dispute:
        return (
            "AUTO_HANDLE",
            f"Contextual assessment: Informational inquiry regarding {intent} resolvable with self-service documentation.",
        )

    # --------------------------------------------------------------------------
    # LEVEL 2: INTENT POLICY PRIORS
    # --------------------------------------------------------------------------
    if intent in DEFAULT_ESCALATE_INTENTS:
        meta = INTENT_DEFINITIONS.get(intent, {})
        base_reason = meta.get("rationale", "Intent requires human agent oversight per taxonomy policy.")
        return "ESCALATE", base_reason

    # For AUTO_HANDLE intents (tracking, Prime, device troubleshooting, promo, feedback, FAQ):
    # Default to AUTO_HANDLE unless active dispute or explicit risk is identified
    meta = INTENT_DEFINITIONS.get(intent, {})
    base_reason = meta.get("rationale", f"Standard {intent} inquiry suitable for automated resolution.")
    return "AUTO_HANDLE", base_reason


def build_hybrid_prompt(
    customer_message: str,
    classified_intent: str,
    retrieved_examples: list[dict],
) -> tuple[str, str]:
    """
    Constructs the system and user prompts for Ollama, locking the classified intent
    and providing intent context and retrieved historical interactions.
    """
    intent_meta = INTENT_DEFINITIONS.get(classified_intent, {
        "definition": "Customer support inquiry.",
        "default_escalation": "ESCALATE",
        "rationale": "Support assistance required.",
    })

    system_prompt = f"""You are an expert Amazon Customer Support AI Assistant.
Your task is to write a polite, professional, and empathetic customer support draft response and provide an explanation for the issue.

### INTENT SPECIFICATION (AUTHORITATIVE):
- Intent: {classified_intent}
- Definition: {intent_meta['definition']}
- Policy Escalation: {intent_meta['default_escalation']}

### RESPONSE GUIDELINES:
1. Maintain the standard Amazon customer service voice: empathetic, helpful, clear, and direct.
2. For AUTO_HANDLE inquiries (e.g. tracking lookup, FAQ, prime info, device troubleshooting, general warranty/policy info), provide concrete self-service steps and standard Amazon links (e.g., 'Your Orders', 'Prime Central', 'Manage Your Content and Devices').
3. For ESCALATE inquiries (e.g. active delivery delays, broken items, missing refunds, active cancellations, billing disputes), express empathy for the inconvenience, acknowledge the specifics of their issue, and explain that their case is being handled by support.
4. Do NOT invent fake order IDs, personal names, or non-Amazon URLs.

### REQUIRED OUTPUT FORMAT:
You must respond with valid JSON ONLY matching this schema:
{{
  "intent": "{classified_intent}",
  "escalation_decision": "{intent_meta['default_escalation']}",
  "escalation_reason": "<concise explanation of the customer issue and why it should be auto-handled or escalated>",
  "draft_response": "<polite, professional customer service response addressing customer's issue>"
}}"""

    prompt_lines = [
        "### HISTORICAL REFERENCE CONVERSATIONS (FOR STYLE AND CONTEXT ONLY):",
        "Note: Use these historical interactions to understand customer service phrasing. Do NOT copy names or order numbers from them.",
        "",
    ]

    if retrieved_examples:
        for i, ex in enumerate(retrieved_examples, 1):
            prompt_lines.append(f"--- Reference Example {i} (Similarity: {ex.get('similarity_score', 0.0):.4f}) ---")
            prompt_lines.append(f"Customer: {ex.get('customer_message', '')}")
            resp = ex.get('historical_response', '').strip()
            if resp:
                prompt_lines.append(f"Support Response: {resp}")
            prompt_lines.append("")
    else:
        prompt_lines.append("(No historical examples provided)")
        prompt_lines.append("")

    prompt_lines.extend([
        "### CURRENT INCOMING CUSTOMER MESSAGE:",
        f"\"{customer_message}\"",
        "",
        f"Classified Intent: {classified_intent}",
        "Generate the JSON output containing the draft response and explanation.",
    ])

    return system_prompt, "\n".join(prompt_lines)


class HybridSupportAgent:
    """
    Production-grade Hybrid Customer Support Agent.
    - Intent: TF-IDF Logistic Regression Classifier (authoritative, high-precision)
    - Retrieval: Dense FAISS Semantic Retriever (top-K historical interactions)
    - Response Generation: Local Ollama LLM (empathetic drafting conditioned on intent)
    - Escalation: 3-Level Context-Aware Escalation Layer (Hard Safety + Policy Prior + Context Complexity)
    """

    def __init__(
        self,
        intent_classifier: TfidfIntentClassifier | None = None,
        retriever: SemanticRetriever | None = None,
        llm_client: OllamaClient | None = None,
        default_top_k: int = 3,
        intent_model_path: str = DEFAULT_INTENT_MODEL_PATH,
    ):
        if intent_classifier is not None:
            self.intent_classifier = intent_classifier
        elif os.path.exists(intent_model_path):
            self.intent_classifier = TfidfIntentClassifier.load(intent_model_path)
        else:
            self.intent_classifier = None

        self.retriever = retriever if retriever is not None else SemanticRetriever()
        self.llm_client = llm_client if llm_client is not None else OllamaClient()
        self.default_top_k = default_top_k

    def process_message(
        self,
        customer_message: str,
        top_k: int | None = None,
    ) -> dict[str, Any]:
        """
        Processes an incoming customer message end-to-end:
        1. Classify intent via TF-IDF model (authoritative).
        2. Retrieve top-K similar historical conversations via FAISS.
        3. Draft customer response and reasoning via Ollama LLM.
        4. Apply 3-level context-aware escalation assessment.
        5. Return structured result compatible with evaluation harness.
        """
        k = top_k if top_k is not None else self.default_top_k

        # 1. Authoritative Intent Classification via TF-IDF
        if self.intent_classifier is not None:
            predicted_intent = self.intent_classifier.predict([customer_message])[0]
        else:
            predicted_intent = "other_or_unsupported"

        if predicted_intent not in VALID_INTENTS:
            predicted_intent = "other_or_unsupported"

        # 2. Semantic Retrieval
        retrieved = self.retriever.search(customer_message, top_k=k)

        # 3. Prompt Construction & Ollama Generation
        system_prompt, user_prompt = build_hybrid_prompt(
            customer_message=customer_message,
            classified_intent=predicted_intent,
            retrieved_examples=retrieved,
        )

        llm_result = None
        for attempt in range(2):
            try:
                raw_llm = self.llm_client.generate(
                    prompt=user_prompt,
                    system_prompt=system_prompt,
                )
                llm_result = raw_llm
                break
            except Exception:
                continue

        # Fallback response generation if LLM is unreachable
        if llm_result is None:
            default_esc = INTENT_DEFINITIONS.get(predicted_intent, {}).get("default_escalation", "ESCALATE")
            llm_result = {
                "intent": predicted_intent,
                "escalation_decision": default_esc,
                "escalation_reason": INTENT_DEFINITIONS.get(predicted_intent, {}).get("rationale", "Standard inquiry handling."),
                "draft_response": "Thank you for contacting Amazon Customer Support. We have received your inquiry and our team is assisting you.",
            }

        # 4. Context-Aware Escalation Layer (3 Levels)
        final_escalation, guardrail_reason = assess_contextual_escalation(
            intent=predicted_intent,
            customer_message=customer_message,
            llm_reason=llm_result.get("escalation_reason", ""),
        )

        # Combine LLM reasoning with guardrail reasoning for complete transparency
        llm_reason = llm_result.get("escalation_reason", "").strip()
        final_reason = f"{guardrail_reason} {llm_reason}".strip() if llm_reason else guardrail_reason

        return {
            "customer_message": customer_message,
            "intent": predicted_intent,
            "escalation_decision": final_escalation,
            "escalation_reason": final_reason,
            "draft_response": llm_result.get("draft_response", ""),
            "retrieved_examples": retrieved,
            "intent_source": "tfidf_classifier",
            "model": self.llm_client.model,
        }


def parse_args():
    parser = argparse.ArgumentParser(description="Run Hybrid Support Agent on a customer inquiry.")
    parser.add_argument("--message", "-m", required=True, help="Customer message to process.")
    parser.add_argument("--top-k", "-k", type=int, default=3, help="Number of historical examples to retrieve.")
    parser.add_argument("--json", action="store_true", help="Output raw JSON.")
    return parser.parse_args()


def main():
    args = parse_args()
    agent = HybridSupportAgent()
    result = agent.process_message(args.message, top_k=args.top_k)

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return

    print("\n" + "=" * 75)
    print("HYBRID SUPPORT AGENT INFERENCE RESULT")
    print("=" * 75)
    print(f"Customer Message: \"{result['customer_message']}\"")
    print(f"Intent (TF-IDF):  {result['intent']}")
    print(f"Escalation:       {result['escalation_decision']}")
    print(f"Reason:           {result['escalation_reason']}")
    print("-" * 75)
    print(f"Draft Response:\n{result['draft_response']}")
    print("-" * 75)
    print(f"Retrieved Context ({len(result['retrieved_examples'])} examples):")
    for i, ex in enumerate(result['retrieved_examples'], 1):
        print(f"  [{i}] Similarity: {ex['similarity_score']:.4f} | \"{ex['customer_message']}\"")
    print("=" * 75 + "\n")


if __name__ == "__main__":
    main()
