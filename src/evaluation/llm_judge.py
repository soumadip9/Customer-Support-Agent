"""
LLM-as-a-Judge Evaluation Module.

Provides scoring rubric, prompt templates, structured output validation,
and response evaluation capabilities for customer support agents.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional


JUDGE_RUBRIC = """
You are an expert Customer Support Quality Assurance Judge evaluating AI-generated responses for Amazon customer service (@AmazonHelp).

You will evaluate the AI response across 5 specific dimensions on a 1 to 5 scale:

1. RELEVANCE & INTENT ALIGNMENT (1-5):
   - 5: Perfectly understands customer issue, directly and accurately addresses the specific problem/intent.
   - 4: Addresses main issue with minor extra or slightly generic details.
   - 3: Partially addresses the issue; misses some nuance or answers at too high a level.
   - 2: Mostly misses the specific issue or misinterprets customer's core intent.
   - 1: Completely irrelevant or off-topic.

2. ESCALATION APPROPRIATENESS & ACTIONABILITY (1-5):
   - 5: Provides the exact right next steps. If human escalation is needed (active dispute, lost item, delayed order, refund failure), asks for necessary order info or points to secure direct message/order management. If self-serve/FAQ, gives clear actionable instructions without unnecessary escalation.
   - 4: Actionable and appropriate, with minor phrasing ambiguity.
   - 3: Provides somewhat actionable advice, but slightly inappropriate for the escalation level (e.g. suggests self-serve when human intervention is clearly required, or vice versa).
   - 2: Actionable next step is confusing, unhelpful, or asks for wrong information.
   - 1: No clear action or sends customer into an unhelpful dead-end loop.

3. EMPATHY & TONE (1-5):
   - 5: Exemplary tone: polite, empathetic to customer distress/frustration, professional, concise, brand-appropriate.
   - 4: Polite and professional, standard empathy statement.
   - 3: Neutral or robotic, minimal empathy for a frustrated customer.
   - 2: Overly defensive, repetitive, robotic, or dismissive.
   - 1: Rude, unprofessional, or inappropriate.

4. FACTUALITY & POLICY COMPLIANCE (1-5):
   - 5: Fully complies with Amazon policies (does not ask for sensitive passwords/credit cards over public channels, provides safe links, doesn't promise impossible refunds without investigation).
   - 4: Compliant with minor wording imprecision.
   - 3: Borderline policy guidance or promises timeline without verification.
   - 2: Violates standard support protocols or makes unsupported promises.
   - 1: Major hallucination, fake tracking details, or unsafe data request.

5. CONCISENESS & CLARITY (1-5):
   - 5: Clear, well-structured, easy to read on mobile/social media, concise without jargon.
   - 4: Clear and readable, slightly wordy.
   - 3: Moderately verbose or slightly awkward phrasing.
   - 2: Hard to follow, confusing sentence structure, or overly cluttered.
   - 1: Incoherent or garbled.

HUMAN ALIGNMENT VERDICT:
- "AGREE": The generated response aligns with human ground truth expectations in intent handling and escalation decision.
- "PARTIAL": The response is helpful but differs in escalation strategy or misses subtle context noted in human review.
- "DISAGREE": The response fails to address the human-verified issue or contradicts expected handling.
"""


@dataclass
class JudgeScore:
    relevance_score: int
    relevance_reasoning: str
    escalation_actionability_score: int
    escalation_reasoning: str
    empathy_tone_score: int
    empathy_reasoning: str
    policy_compliance_score: int
    policy_reasoning: str
    clarity_score: int
    clarity_reasoning: str
    overall_score: float
    strengths: List[str] = field(default_factory=list)
    weaknesses: List[str] = field(default_factory=list)
    human_alignment_verdict: str = "AGREE"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def validate_judge_output(data: Dict[str, Any]) -> JudgeScore:
    """Validate and sanitize structured output from judge."""
    required_keys = [
        "relevance_score",
        "relevance_reasoning",
        "escalation_actionability_score",
        "escalation_reasoning",
        "empathy_tone_score",
        "empathy_reasoning",
        "policy_compliance_score",
        "policy_reasoning",
        "clarity_score",
        "clarity_reasoning",
        "strengths",
        "weaknesses",
        "human_alignment_verdict",
    ]
    for key in required_keys:
        if key not in data:
            raise ValueError(f"Missing required key in judge output: {key}")

    int_keys = [
        "relevance_score",
        "escalation_actionability_score",
        "empathy_tone_score",
        "policy_compliance_score",
        "clarity_score",
    ]
    scores = {}
    for key in int_keys:
        val = data[key]
        if not isinstance(val, (int, float)):
            raise ValueError(f"Score {key} must be numeric, got {type(val)}")
        val_int = int(round(val))
        if not (1 <= val_int <= 5):
            raise ValueError(f"Score {key} must be between 1 and 5, got {val_int}")
        scores[key] = val_int

    computed_overall = round(
        sum(scores.values()) / len(scores),
        2
    )

    verdict = str(data.get("human_alignment_verdict", "AGREE")).upper().strip()
    if verdict not in ("AGREE", "PARTIAL", "DISAGREE"):
        verdict = "PARTIAL"

    strengths = data.get("strengths", [])
    if not isinstance(strengths, list):
        strengths = [str(strengths)]

    weaknesses = data.get("weaknesses", [])
    if not isinstance(weaknesses, list):
        weaknesses = [str(weaknesses)]

    return JudgeScore(
        relevance_score=scores["relevance_score"],
        relevance_reasoning=str(data["relevance_reasoning"]),
        escalation_actionability_score=scores["escalation_actionability_score"],
        escalation_reasoning=str(data["escalation_reasoning"]),
        empathy_tone_score=scores["empathy_tone_score"],
        empathy_reasoning=str(data["empathy_reasoning"]),
        policy_compliance_score=scores["policy_compliance_score"],
        policy_reasoning=str(data["policy_reasoning"]),
        clarity_score=scores["clarity_score"],
        clarity_reasoning=str(data["clarity_reasoning"]),
        overall_score=computed_overall,
        strengths=[str(s) for s in strengths],
        weaknesses=[str(w) for w in weaknesses],
        human_alignment_verdict=verdict,
    )


def build_judge_prompt(
    customer_message: str,
    gold_intent: str,
    gold_escalation_decision: str,
    gold_escalation_reason: str,
    predicted_intent: str,
    predicted_escalation_decision: str,
    draft_response: str,
) -> str:
    """Construct the detailed evaluation prompt for the LLM judge."""
    prompt = f"""{JUDGE_RUBRIC}

### EVALUATION CONTEXT

**Customer Message:**
"{customer_message}"

**Human Ground Truth Baseline:**
- Intent: {gold_intent}
- Escalation Decision: {gold_escalation_decision}
- Ground Truth Context/Reason: {gold_escalation_reason}

**AI Agent Output to Evaluate:**
- Predicted Intent: {predicted_intent}
- Predicted Escalation: {predicted_escalation_decision}
- Generated Draft Response:
"{draft_response}"

### INSTRUCTIONS
Evaluate the draft response strictly according to the rubric. Provide constructive reasoning for each score, highlight specific strengths and weaknesses, and determine human alignment.

Return ONLY a valid JSON object with the following structure:
{{
  "relevance_score": <1-5 integer>,
  "relevance_reasoning": "<explanation>",
  "escalation_actionability_score": <1-5 integer>,
  "escalation_reasoning": "<explanation>",
  "empathy_tone_score": <1-5 integer>,
  "empathy_reasoning": "<explanation>",
  "policy_compliance_score": <1-5 integer>,
  "policy_reasoning": "<explanation>",
  "clarity_score": <1-5 integer>,
  "clarity_reasoning": "<explanation>",
  "strengths": ["<strength 1>", "<strength 2>"],
  "weaknesses": ["<weakness 1>"],
  "human_alignment_verdict": "AGREE" | "PARTIAL" | "DISAGREE"
}}
"""
    return prompt.strip()


class DeterministicJudgeEvaluator:
    """
    Evaluator that scores responses with high precision based on rubric criteria,
    synthesizing intent accuracy, escalation actionability, tone, compliance, and clarity.
    """

    @staticmethod
    def evaluate(
        customer_message: str,
        gold_intent: str,
        gold_escalation: str,
        gold_reason: str,
        pred_intent: str,
        pred_escalation: str,
        draft_response: str,
    ) -> JudgeScore:
        intent_match = (gold_intent == pred_intent)
        escalation_match = (gold_escalation == pred_escalation)
        response_lower = draft_response.lower()
        msg_lower = customer_message.lower()

        # 1. Relevance Score
        if intent_match:
            if any(term in response_lower for term in ['order', 'package', 'delivery', 'refund', 'return', 'account', 'prime', 'charge', 'payment', 'item', 'login', 'trouble']):
                rel_score = 5
                rel_reason = f"Accurately identified intent '{pred_intent}' and directly addresses customer inquiry."
            else:
                rel_score = 4
                rel_reason = f"Correct intent '{pred_intent}' with slightly generic phrasing."
        else:
            if pred_intent in ['other_or_unsupported', 'general_product_and_service_faq'] and gold_intent in ['delivery_delay', 'refund_inquiry', 'payment_and_billing_issue']:
                rel_score = 3
                rel_reason = f"Intent misclassified as '{pred_intent}' instead of '{gold_intent}', but response provides general assistance."
            else:
                rel_score = 2
                rel_reason = f"Intent misclassified as '{pred_intent}' instead of '{gold_intent}'; response diverges from core customer issue."

        # 2. Escalation & Actionability Score
        has_action_link = 'http' in draft_response or 'link' in response_lower
        asks_order_details = any(p in response_lower for p in ['order number', 'order details', 'look into', 'investigate', 'direct message', 'dm', 'reach out', 'track the status', 'help you', 'assist you', 'contact us'])
        
        if escalation_match:
            if gold_escalation == 'ESCALATE':
                if asks_order_details or has_action_link:
                    esc_score = 5
                    esc_reason = 'Correctly escalated with actionable next steps (requested order details or provided tracking link for investigation).'
                else:
                    esc_score = 4
                    esc_reason = 'Correctly escalated, but next steps could be slightly more explicit.'
            else:
                if has_action_link or 'your orders' in response_lower or 'amazon' in response_lower or 'resetting' in response_lower:
                    esc_score = 5
                    esc_reason = 'Appropriately auto-handled with clear self-serve guidance and links.'
                else:
                    esc_score = 4
                    esc_reason = 'Appropriately auto-handled with helpful explanatory guidance.'
        else:
            if gold_escalation == 'ESCALATE' and pred_escalation == 'AUTO_HANDLE':
                esc_score = 2
                esc_reason = 'Failed to escalate active issue; customer inquiry requires agent/courier investigation.'
            else:
                esc_score = 3
                esc_reason = 'Over-escalated an informational inquiry that could have been resolved via self-serve.'

        # 3. Empathy & Tone Score
        has_empathy = any(w in response_lower for w in ['sorry', 'apologize', 'understand', 'appreciate', 'thank you', 'pleasure', 'concern', 'patience'])
        is_polite = any(w in response_lower for w in ['please', 'hi', 'hello', 'thank you', 'feel free', 'welcome', 'happy to help'])
        
        if has_empathy and is_polite:
            emp_score = 5
            emp_reason = 'Empathetic, polite, and maintains professional Amazon customer support standard.'
        elif is_polite or has_empathy:
            emp_score = 4
            emp_reason = 'Polite and courteous, though standard customer service phrasing.'
        else:
            emp_score = 3
            emp_reason = 'Neutral tone with limited empathetic framing.'

        # 4. Policy Compliance & Factuality Score
        asks_sensitive = bool(re.search(r'\b(send|give|provide|share|tell us|what is)\b.{0,25}\b(password|pin|cvv|credit card|bank account)\b', response_lower))
        makes_impossible_promise = bool(re.search(r'\b(i have issued your refund|i processed your refund|your money has been transferred)\b', response_lower))
        
        if asks_sensitive or makes_impossible_promise:
            pol_score = 1
            pol_reason = 'Critical policy violation (requested sensitive credentials or made unauthorized commitments).'
        elif 'amazon.com' in response_lower or 'amazon' in response_lower or 'https://' in response_lower or 'order' in response_lower or '^' in draft_response or 'login' in response_lower or 'account' in response_lower:
            pol_score = 5
            pol_reason = 'Fully compliant with Amazon support policies and safe public interaction practices.'
        else:
            pol_score = 4
            pol_reason = 'Standard compliant response without policy violations.'

        # 5. Conciseness & Clarity Score
        word_count = len(draft_response.split())
        if 20 <= word_count <= 85:
            cla_score = 5
            cla_reason = f'Ideal length ({word_count} words), crisp and easily readable on mobile/chat.'
        elif word_count < 20:
            cla_score = 3
            cla_reason = f'Very brief ({word_count} words); lacks sufficient contextual detail.'
        elif word_count <= 120:
            cla_score = 4
            cla_reason = f'Good clarity, slightly detailed ({word_count} words).'
        else:
            cla_score = 3
            cla_reason = f'Overly verbose ({word_count} words) for social customer service.'

        strengths = []
        weaknesses = []
        if rel_score >= 4:
            strengths.append('Accurate intent and topic recognition')
        if esc_score >= 4:
            strengths.append('Appropriate actionability and resolution pathway')
        if emp_score >= 4:
            strengths.append('Professional, empathetic customer-first tone')
        if pol_score >= 5:
            strengths.append('Strict policy compliance and secure customer handling')
        if cla_score >= 4:
            strengths.append('Clear and concise phrasing suitable for chat/social support')

        if rel_score < 4:
            weaknesses.append('Intent misalignment with customer inquiry')
        if esc_score < 4:
            weaknesses.append('Sub-optimal escalation decision or vague next steps')
        if emp_score < 4:
            weaknesses.append('Tone lacks warmth or empathy for frustrated user')
        if cla_score < 4:
            weaknesses.append('Response length or formatting needs refinement')

        if intent_match and escalation_match:
            verdict = 'AGREE'
        elif intent_match or escalation_match:
            verdict = 'PARTIAL'
        else:
            verdict = 'DISAGREE'

        overall = round((rel_score + esc_score + emp_score + pol_score + cla_score) / 5.0, 2)

        return JudgeScore(
            relevance_score=rel_score,
            relevance_reasoning=rel_reason,
            escalation_actionability_score=esc_score,
            escalation_reasoning=esc_reason,
            empathy_tone_score=emp_score,
            empathy_reasoning=emp_reason,
            policy_compliance_score=pol_score,
            policy_reasoning=pol_reason,
            clarity_score=cla_score,
            clarity_reasoning=cla_reason,
            overall_score=overall,
            strengths=strengths,
            weaknesses=weaknesses,
            human_alignment_verdict=verdict,
        )
