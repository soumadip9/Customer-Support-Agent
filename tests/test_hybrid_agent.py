"""
tests/test_hybrid_agent.py

Unit and integration tests for HybridSupportAgent (Step 13 & Step 15).
Verifies:
- Intent classification locking (TF-IDF authoritativeness)
- 3-Level Context-Aware Escalation Layer:
  * Level 1: Hard Safety Overrides (human request, fraud, takeover, legal)
  * Level 2: Intent Policy Priors
  * Level 3: Contextual Complexity Assessment (Informational vs Active Dispute)
- Contextual policy cases (e.g. benign use of 'person' or 'police')
- Prompt construction and intent conditioning
- Schema compliance and fallback handling
- Integration with real TF-IDF model and FAISS retriever
"""

import json
import os
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

# Ensure src/ is on sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from src.baselines.tfidf_logreg import TfidfIntentClassifier
from src.llm.hybrid_agent import (
    DEFAULT_AUTOHANDLE_INTENTS,
    DEFAULT_ESCALATE_INTENTS,
    INTENT_DEFINITIONS,
    HybridSupportAgent,
    assess_contextual_escalation,
    build_hybrid_prompt,
)
from src.llm.ollama_client import (
    VALID_DECISIONS,
    VALID_INTENTS,
    OllamaClient,
)
from src.retrieval.search import SemanticRetriever


class TestContextAwareEscalationLayer(unittest.TestCase):
    """Test 3-level context-aware escalation rules and edge cases."""

    # 1. Level 1: Hard Safety Overrides
    def test_explicit_human_agent_requests_always_escalate(self):
        human_queries = [
            "Please connect me to a human agent.",
            "I want to speak with a representative immediately.",
            "Transfer me to a supervisor right now.",
            "Can I talk to a real person please?",
            "Give me a human representative.",
        ]
        for q in human_queries:
            dec, reason = assess_contextual_escalation(
                intent="order_tracking_inquiry",
                customer_message=q,
            )
            self.assertEqual(dec, "ESCALATE", f"Query '{q}' should trigger hard human escalation.")
            self.assertIn("human", reason.lower())

    def test_account_compromise_always_escalates(self):
        compromise_queries = [
            "My account has been hacked and someone changed my password.",
            "Suspicious unauthorized login from unknown device on my account.",
            "Someone else logged into my account and placed orders.",
        ]
        for q in compromise_queries:
            dec, reason = assess_contextual_escalation(
                intent="account_access_and_security",
                customer_message=q,
            )
            self.assertEqual(dec, "ESCALATE", f"Query '{q}' should trigger hard safety escalation.")
            self.assertIn("compromise", reason.lower())

    def test_unauthorized_payment_fraud_always_escalates(self):
        fraud_queries = [
            "I don't recognize this charge on my statement.",
            "Unauthorized charge of $89 on my credit card.",
            "My credit card was stolen and used on Amazon.",
        ]
        for q in fraud_queries:
            dec, reason = assess_contextual_escalation(
                intent="payment_and_billing_issue",
                customer_message=q,
            )
            self.assertEqual(dec, "ESCALATE", f"Query '{q}' should trigger hard financial escalation.")
            self.assertIn("fraud", reason.lower())

    def test_direct_theft_claims_escalate(self):
        theft_queries = [
            "My package was stolen from my porch.",
            "Stolen package claim for order #123.",
        ]
        for q in theft_queries:
            dec, reason = assess_contextual_escalation(
                intent="delivery_delay",
                customer_message=q,
            )
            self.assertEqual(dec, "ESCALATE", f"Query '{q}' should escalate.")

    # 2. Benign Words Must NOT Trigger False Escalation
    def test_benign_use_of_person_does_not_escalate_autohandle(self):
        benign_person_queries = [
            ("driver_and_packaging_feedback", "The delivery person was very helpful and polite."),
            ("order_tracking_inquiry", "Please arrange courier person to collect the package."),
            ("general_product_and_service_faq", "Is there a limit on how many items one person can buy?"),
        ]
        for intent, q in benign_person_queries:
            dec, reason = assess_contextual_escalation(
                intent=intent,
                customer_message=q,
            )
            self.assertEqual(dec, "AUTO_HANDLE", f"Query '{q}' should NOT escalate merely because 'person' appears.")

    def test_benign_mention_of_police_or_venting_does_not_escalate(self):
        q = "You could ask the other Amazon Delivery driver who was there (and then slinked away when I called the police). I didn't get his name. You should require IDs."
        dec, reason = assess_contextual_escalation(
            intent="driver_and_packaging_feedback",
            customer_message=q,
        )
        self.assertEqual(dec, "AUTO_HANDLE", f"Driver feedback '{q}' should remain AUTO_HANDLE.")

    # 3. Informational vs Active Customer-Specific Cases
    def test_informational_refund_inquiry_autohandles(self):
        q = "How long does a refund normally take to appear in my account?"
        dec, reason = assess_contextual_escalation(
            intent="refund_inquiry",
            customer_message=q,
        )
        self.assertEqual(dec, "AUTO_HANDLE", f"Informational query '{q}' should AUTO_HANDLE.")
        self.assertIn("informational", reason.lower())

    def test_active_unresolved_refund_dispute_escalates(self):
        q = "My refund has not arrived after 30 days and the item was returned weeks ago."
        dec, reason = assess_contextual_escalation(
            intent="refund_inquiry",
            customer_message=q,
        )
        self.assertEqual(dec, "ESCALATE", f"Active refund dispute '{q}' must ESCALATE.")

    def test_informational_cancellation_question_autohandles(self):
        q = "How can I cancel an order on the website before it dispatches?"
        dec, reason = assess_contextual_escalation(
            intent="order_cancellation",
            customer_message=q,
        )
        self.assertEqual(dec, "AUTO_HANDLE", f"Informational cancellation question '{q}' should AUTO_HANDLE.")

    def test_active_order_cancellation_request_escalates(self):
        q = "Please cancel my order 402-8821901-1120491 immediately before it ships tomorrow."
        dec, reason = assess_contextual_escalation(
            intent="order_cancellation",
            customer_message=q,
        )
        self.assertEqual(dec, "ESCALATE", f"Active cancellation request '{q}' must ESCALATE.")

    def test_informational_warranty_and_tradein_faq_autohandle(self):
        test_queries = [
            ("damaged_or_wrong_item", "How do I deal with the warranty on an Amazon Basics item?"),
            ("other_or_unsupported", "I do not see anything that specifies the requirements for Trade-in... please advise."),
            ("payment_and_billing_issue", "Do you accept Visa and Mastercard debit cards at checkout?"),
        ]
        for intent, q in test_queries:
            dec, reason = assess_contextual_escalation(
                intent=intent,
                customer_message=q,
            )
            self.assertEqual(dec, "AUTO_HANDLE", f"Informational query '{q}' under {intent} should AUTO_HANDLE.")

    def test_standard_autohandle_intents_remain_autohandle(self):
        standard_cases = [
            ("order_tracking_inquiry", "Where can I track my package? The courier is AMZL."),
            ("prime_membership_inquiry", "How do I share my Prime benefits with family via Amazon Household?"),
            ("digital_and_device_troubleshooting", "My Kindle screen is frozen and won't restart."),
            ("promotion_and_discount_inquiry", "Where do I enter the promo code on the checkout page?"),
            ("general_product_and_service_faq", "When will the Echo Spot be back in stock in the UK store?"),
        ]
        for intent, q in standard_cases:
            dec, reason = assess_contextual_escalation(
                intent=intent,
                customer_message=q,
            )
            self.assertEqual(dec, "AUTO_HANDLE", f"Standard query '{q}' should AUTO_HANDLE.")

    def test_active_delivery_delay_escalates(self):
        q = "My package was supposed to be delivered yesterday and is 3 days overdue."
        dec, reason = assess_contextual_escalation(
            intent="delivery_delay",
            customer_message=q,
        )
        self.assertEqual(dec, "ESCALATE", f"Overdue delivery '{q}' must ESCALATE.")


class TestHybridPromptBuilder(unittest.TestCase):
    """Test prompt construction and intent conditioning."""

    def test_prompt_includes_intent_and_definition(self):
        retrieved = [
            {
                "similarity_score": 0.88,
                "source_id": "1001",
                "customer_message": "Where is my item?",
                "historical_response": "Check tracking at amazon.com/orders",
            }
        ]
        sys_prompt, user_prompt = build_hybrid_prompt(
            customer_message="Can I track my parcel?",
            classified_intent="order_tracking_inquiry",
            retrieved_examples=retrieved,
        )

        self.assertIn("order_tracking_inquiry", sys_prompt)
        self.assertIn("AUTO_HANDLE", sys_prompt)
        self.assertIn("Where is my item?", user_prompt)
        self.assertIn("Check tracking at amazon.com/orders", user_prompt)
        self.assertIn("Can I track my parcel?", user_prompt)

    def test_prompt_handles_empty_retrieved_examples(self):
        sys_prompt, user_prompt = build_hybrid_prompt(
            customer_message="Help with Kindle",
            classified_intent="digital_and_device_troubleshooting",
            retrieved_examples=[],
        )
        self.assertIn("No historical examples provided", user_prompt)
        self.assertIn("digital_and_device_troubleshooting", sys_prompt)


class TestHybridSupportAgent(unittest.TestCase):
    """Unit tests with mocked subsystems."""

    def setUp(self):
        self.mock_classifier = MagicMock(spec=TfidfIntentClassifier)
        self.mock_retriever = MagicMock(spec=SemanticRetriever)
        self.mock_llm = MagicMock(spec=OllamaClient)
        self.mock_llm.model = "mock-llama3.2:3b"

    def test_hybrid_agent_happy_path_active_dispute(self):
        self.mock_classifier.predict.return_value = ["refund_inquiry"]
        self.mock_retriever.search.return_value = [
            {
                "similarity_score": 0.92,
                "source_id": "555",
                "customer_message": "Where is my refund for order #123?",
                "historical_response": "Refunds take 3-5 business days to appear.",
            }
        ]
        self.mock_llm.generate.return_value = {
            "intent": "refund_inquiry",
            "escalation_decision": "ESCALATE",
            "escalation_reason": "Customer is inquiring about status of uncredited refund.",
            "draft_response": "I understand you are checking on your refund status. Let me review your transaction history.",
        }

        agent = HybridSupportAgent(
            intent_classifier=self.mock_classifier,
            retriever=self.mock_retriever,
            llm_client=self.mock_llm,
        )

        result = agent.process_message("My refund has not arrived after 3 weeks, order 123-4567890-1234567.")

        self.assertEqual(result["intent"], "refund_inquiry")
        self.assertEqual(result["escalation_decision"], "ESCALATE")
        self.assertEqual(result["intent_source"], "tfidf_classifier")
        self.assertEqual(result["model"], "mock-llama3.2:3b")
        self.assertIn("refund", result["draft_response"].lower())

    def test_hybrid_agent_informational_refund_autohandles(self):
        self.mock_classifier.predict.return_value = ["refund_inquiry"]
        self.mock_retriever.search.return_value = []
        self.mock_llm.generate.return_value = {
            "intent": "refund_inquiry",
            "escalation_decision": "AUTO_HANDLE",
            "escalation_reason": "Informational refund policy question.",
            "draft_response": "Standard refunds are processed within 3-5 business days once received.",
        }

        agent = HybridSupportAgent(
            intent_classifier=self.mock_classifier,
            retriever=self.mock_retriever,
            llm_client=self.mock_llm,
        )

        result = agent.process_message("How long does a refund normally take?")

        self.assertEqual(result["intent"], "refund_inquiry")
        self.assertEqual(result["escalation_decision"], "AUTO_HANDLE")

    def test_hybrid_agent_enforces_tfidf_intent_over_llm_hallucination(self):
        self.mock_classifier.predict.return_value = ["delivery_delay"]
        self.mock_retriever.search.return_value = []
        self.mock_llm.generate.return_value = {
            "intent": "order_cancellation",  # LLM hallucinates different intent
            "escalation_decision": "ESCALATE",
            "escalation_reason": "Delivery issue.",
            "draft_response": "Apologies for the delivery delay.",
        }

        agent = HybridSupportAgent(
            intent_classifier=self.mock_classifier,
            retriever=self.mock_retriever,
            llm_client=self.mock_llm,
        )

        result = agent.process_message("My parcel is 3 days late")

        # Hybrid agent authoritatively preserves the TF-IDF intent
        self.assertEqual(result["intent"], "delivery_delay")
        self.assertEqual(result["escalation_decision"], "ESCALATE")

    def test_hybrid_agent_graceful_fallback_on_llm_failure(self):
        self.mock_classifier.predict.return_value = ["prime_membership_inquiry"]
        self.mock_retriever.search.return_value = []
        self.mock_llm.generate.side_effect = RuntimeError("Ollama connection failed")

        agent = HybridSupportAgent(
            intent_classifier=self.mock_classifier,
            retriever=self.mock_retriever,
            llm_client=self.mock_llm,
        )

        result = agent.process_message("How do I share my Prime with household?")

        self.assertEqual(result["intent"], "prime_membership_inquiry")
        self.assertEqual(result["escalation_decision"], "AUTO_HANDLE")
        self.assertTrue(len(result["draft_response"]) > 0)

    def test_all_thirteen_intents_produce_valid_schema(self):
        self.mock_retriever.search.return_value = []
        for intent in VALID_INTENTS:
            self.mock_classifier.predict.return_value = [intent]
            default_esc = INTENT_DEFINITIONS[intent]["default_escalation"]
            self.mock_llm.generate.return_value = {
                "intent": intent,
                "escalation_decision": default_esc,
                "escalation_reason": "Standard reasoning for intent.",
                "draft_response": f"Support response for {intent}.",
            }

            agent = HybridSupportAgent(
                intent_classifier=self.mock_classifier,
                retriever=self.mock_retriever,
                llm_client=self.mock_llm,
            )

            res = agent.process_message("Where is my package?")
            self.assertEqual(res["intent"], intent)
            self.assertIn(res["escalation_decision"], VALID_DECISIONS)
            self.assertTrue(bool(res["escalation_reason"]))
            self.assertTrue(bool(res["draft_response"]))


class TestHybridAgentIntegrationWithRealModels(unittest.TestCase):
    """Integration test loading real TF-IDF classifier and FAISS index with mock LLM."""

    @classmethod
    def setUpClass(cls):
        intent_model_path = r"c:\CustomerSupport\models\tfidf_intent_classifier.pkl"
        index_path = r"c:\CustomerSupport\models\retrieval\faiss_index.bin"
        metadata_path = r"c:\CustomerSupport\models\retrieval\corpus_metadata.jsonl"

        if not (os.path.exists(intent_model_path) and os.path.exists(index_path) and os.path.exists(metadata_path)):
            raise unittest.SkipTest("Models or indexes not found.")

        cls.intent_clf = TfidfIntentClassifier.load(intent_model_path)
        cls.retriever = SemanticRetriever(index_path=index_path, metadata_path=metadata_path)

    def test_real_pipeline_tracking_query(self):
        mock_llm = MagicMock()
        mock_llm.model = "llama3.2:3b"
        mock_llm.generate.return_value = {
            "intent": "order_tracking_inquiry",
            "escalation_decision": "AUTO_HANDLE",
            "escalation_reason": "Tracking inquiry within normal dispatch timeframe.",
            "draft_response": "You can track your parcel anytime in the Your Orders section.",
        }

        agent = HybridSupportAgent(
            intent_classifier=self.intent_clf,
            retriever=self.retriever,
            llm_client=mock_llm,
        )

        result = agent.process_message("Where can I track the carrier AMZL for my package?")

        self.assertEqual(result["intent"], "order_tracking_inquiry")
        self.assertEqual(result["escalation_decision"], "AUTO_HANDLE")
        self.assertGreater(len(result["retrieved_examples"]), 0)

    def test_real_pipeline_late_delivery_query(self):
        mock_llm = MagicMock()
        mock_llm.model = "llama3.2:3b"
        mock_llm.generate.return_value = {
            "intent": "delivery_delay",
            "escalation_decision": "ESCALATE",
            "escalation_reason": "Package is 4 days late past guaranteed delivery date.",
            "draft_response": "We apologize for the delivery delay. A representative is looking into your package.",
        }

        agent = HybridSupportAgent(
            intent_classifier=self.intent_clf,
            retriever=self.retriever,
            llm_client=mock_llm,
        )

        result = agent.process_message("My package was supposed to arrive 4 days ago and is still not here!")

        self.assertEqual(result["intent"], "delivery_delay")
        self.assertEqual(result["escalation_decision"], "ESCALATE")
        self.assertGreater(len(result["retrieved_examples"]), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
