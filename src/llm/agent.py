"""
src/llm/agent.py

End-to-end RAG Customer Support Agent combining SemanticRetriever (Step 9)
with a local Ollama LLM (Step 10).
"""

from __future__ import annotations

import json
from typing import Any

from src.llm.ollama_client import (
    OllamaClient,
    VALID_INTENTS,
    VALID_DECISIONS,
)
from src.retrieval.search import SemanticRetriever

SYSTEM_PROMPT = """You are an expert Amazon Customer Support AI Assistant.
Your task is to analyze an incoming customer support message, determine its exact intent from the official 13-category taxonomy, decide whether it should be handled automatically or escalated to a human agent, explain your reasoning, and write a professional, helpful customer response.

### OFFICIAL 13-CATEGORY INTENT TAXONOMY:
1. delivery_delay: Package missed promised delivery date, is running late, or overdue. (Default: ESCALATE)
2. order_tracking_inquiry: Inquiring about current tracking status, courier name, or transit ETA within normal delivery timeline. (Default: AUTO_HANDLE)
3. order_cancellation: Requesting to cancel an order, stop shipment, or dispute an unexpected cancellation. (Default: ESCALATE)
4. refund_inquiry: Asking for a refund status on returned/cancelled items, or inquiring when refund will credit to bank. (Default: ESCALATE)
5. damaged_or_wrong_item: Reporting broken, defective, crushed, missing items, or wrong product/size received. (Default: ESCALATE)
6. payment_and_billing_issue: Duplicate credit card charges, unauthorized transactions, or payment failure with money debited. (Default: ESCALATE)
7. prime_membership_inquiry: Inquiring about Prime benefits, membership fee rules, Household sharing, or student plans. (Default: AUTO_HANDLE)
8. account_access_and_security: Locked account, 2FA/OTP code not received, password reset issues, or compromised login. (Default: ESCALATE)
9. digital_and_device_troubleshooting: Kindle, Alexa, Echo, Fire TV, or Amazon app errors, settings, or setup problems. (Default: AUTO_HANDLE)
10. promotion_and_discount_inquiry: Promo codes, coupons, promotional discounts, or sale pricing inquiries. (Default: AUTO_HANDLE)
11. driver_and_packaging_feedback: Feedback on delivery carrier conduct or packaging size/materials where item itself is intact. (Default: AUTO_HANDLE)
12. general_product_and_service_faq: Policy questions on trade-in program, warranty coverage, or catalog stock availability. (Default: AUTO_HANDLE)
13. other_or_unsupported: Non-English messages, greetings without support context, or ambiguous conversational fragments. (Default: ESCALATE)

### ESCALATION RULES:
- ESCALATE: Any issue involving financial transactions/debits, account security/credentials, replacement/return approvals, or severe delivery failures requiring agent investigation.
- AUTO_HANDLE: General informational FAQs, self-serve links (e.g. tracking page, Prime settings, Trade-in page), and routine feedback acknowledgment.

### OUTPUT FORMAT:
You must respond with valid JSON ONLY matching this exact schema:
{
  "intent": "<exact_intent_name_from_taxonomy>",
  "escalation_decision": "<AUTO_HANDLE or ESCALATE>",
  "escalation_reason": "<concise explanation of why this intent and escalation decision was chosen>",
  "draft_response": "<polite, professional customer service response addressing customer's issue>"
}"""


def build_user_prompt(customer_message: str, retrieved_examples: list[dict]) -> str:
    """
    Constructs the prompt containing retrieved reference interactions and the current customer query.
    """
    prompt_lines = [
        "### HISTORICAL REFERENCE CONVERSATIONS (FOR CONTEXT ONLY):",
        "Note: Use these historical interactions to understand support conventions. Do NOT copy customer names, specific order IDs, or tracking numbers from them.",
        "",
    ]

    if retrieved_examples:
        for i, ex in enumerate(retrieved_examples, 1):
            prompt_lines.append(f"--- Example {i} (Similarity: {ex.get('similarity_score', 0.0):.4f}) ---")
            prompt_lines.append(f"Historical Customer: {ex.get('customer_message', '')}")
            resp = ex.get('historical_response', '').strip()
            if resp:
                prompt_lines.append(f"Historical Support Response: {resp}")
            prompt_lines.append("")
    else:
        prompt_lines.append("(No historical examples provided)")
        prompt_lines.append("")

    prompt_lines.extend([
        "### CURRENT INCOMING CUSTOMER MESSAGE TO CLASSIFY AND RESOLVE:",
        f"\"{customer_message}\"",
        "",
        "Analyze the incoming message, select the exact intent, decide ESCALATE vs AUTO_HANDLE, and provide a draft response in JSON format.",
    ])

    return "\n".join(prompt_lines)


class SupportAgent:
    """
    RAG-powered support agent combining semantic retrieval with an Ollama LLM.
    """

    def __init__(
        self,
        retriever: SemanticRetriever | None = None,
        llm_client: OllamaClient | None = None,
        default_top_k: int = 3,
    ):
        self.retriever = retriever if retriever is not None else SemanticRetriever()
        self.llm_client = llm_client if llm_client is not None else OllamaClient()
        self.default_top_k = default_top_k

    def process_message(
        self,
        customer_message: str,
        top_k: int | None = None,
    ) -> dict[str, Any]:
        """
        Full RAG pipeline:
        1. Retrieve top-K similar historical interactions.
        2. Build prompt with reference examples.
        3. Call Ollama for structured intent, escalation, and draft response.
        4. Return enriched structured dictionary.
        """
        k = top_k if top_k is not None else self.default_top_k

        # 1. Retrieve historical interactions
        retrieved = self.retriever.search(customer_message, top_k=k)

        # 2. Build prompt
        user_prompt = build_user_prompt(customer_message, retrieved)

        # 3. Call LLM with retry for small model intent hallucination
        llm_result = None
        last_error = None
        current_prompt = user_prompt

        for attempt in range(3):
            try:
                llm_result = self.llm_client.generate(
                    prompt=current_prompt,
                    system_prompt=SYSTEM_PROMPT,
                )
                break
            except Exception as e:
                last_error = e
                # Retry with an explicit reminder of the 13 valid intent labels
                current_prompt = (
                    f"{user_prompt}\n\nIMPORTANT: Your previous output had error: {e}. "
                    f"You MUST use ONLY one of these exact 13 intent strings: {sorted(VALID_INTENTS)}"
                )

        if llm_result is None:
            # Fallback to other_or_unsupported / ESCALATE if model persistently fails taxonomy
            llm_result = {
                "intent": "other_or_unsupported",
                "escalation_decision": "ESCALATE",
                "escalation_reason": f"LLM generation failed validation: {last_error}",
                "draft_response": "Thank you for reaching out to Amazon Support. A customer service representative will assist you with this request shortly.",
            }

        # 4. Enrich result
        return {
            "customer_message": customer_message,
            "intent": llm_result["intent"],
            "escalation_decision": llm_result["escalation_decision"],
            "escalation_reason": llm_result["escalation_reason"],
            "draft_response": llm_result["draft_response"],
            "retrieved_examples": retrieved,
            "model": self.llm_client.model,
        }
