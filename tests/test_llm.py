"""
tests/test_llm.py

Unit tests for Ollama client, validation, prompt construction, caching, and SupportAgent.
Uses mocking so tests run fast and offline without requiring a live Ollama server.
"""

import io
import json
import os
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

# Ensure src/ is on sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from src.llm.agent import SupportAgent, build_user_prompt
from src.llm.ollama_client import (
    LLMValidationError,
    OllamaClient,
    OllamaConnectionError,
    VALID_DECISIONS,
    VALID_INTENTS,
    validate_structured_output,
)


class TestStructuredOutputValidation(unittest.TestCase):

    def test_valid_output_passes(self):
        sample = {
            "intent": "delivery_delay",
            "escalation_decision": "ESCALATE",
            "escalation_reason": "Order missed promised SLA date.",
            "draft_response": "I apologize for the delay. We are tracking your parcel.",
        }
        res = validate_structured_output(sample)
        self.assertEqual(res["intent"], "delivery_delay")
        self.assertEqual(res["escalation_decision"], "ESCALATE")

    def test_invalid_type_raises(self):
        with self.assertRaises(LLMValidationError):
            validate_structured_output("not a dict")
        with self.assertRaises(LLMValidationError):
            validate_structured_output(["item1", "item2"])

    def test_missing_keys_raises(self):
        incomplete = {
            "intent": "delivery_delay",
            "escalation_decision": "ESCALATE",
            # missing escalation_reason and draft_response
        }
        with self.assertRaises(LLMValidationError) as ctx:
            validate_structured_output(incomplete)
        self.assertIn("missing", str(ctx.exception).lower())

    def test_invalid_intent_raises(self):
        bad_intent = {
            "intent": "totally_fabricated_intent",
            "escalation_decision": "ESCALATE",
            "escalation_reason": "reason",
            "draft_response": "response",
        }
        with self.assertRaises(LLMValidationError) as ctx:
            validate_structured_output(bad_intent)
        self.assertIn("invalid intent", str(ctx.exception).lower())

    def test_invalid_escalation_decision_raises(self):
        bad_esc = {
            "intent": "refund_inquiry",
            "escalation_decision": "HUMAN_AGENT_PLEASE",
            "escalation_reason": "reason",
            "draft_response": "response",
        }
        with self.assertRaises(LLMValidationError) as ctx:
            validate_structured_output(bad_esc)
        self.assertIn("invalid escalation_decision", str(ctx.exception).lower())

    def test_empty_escalation_reason_raises(self):
        empty_reason = {
            "intent": "delivery_delay",
            "escalation_decision": "ESCALATE",
            "escalation_reason": "   ",
            "draft_response": "response",
        }
        with self.assertRaises(LLMValidationError):
            validate_structured_output(empty_reason)

    def test_empty_draft_response_raises(self):
        empty_resp = {
            "intent": "delivery_delay",
            "escalation_decision": "ESCALATE",
            "escalation_reason": "valid reason",
            "draft_response": "",
        }
        with self.assertRaises(LLMValidationError):
            validate_structured_output(empty_resp)


class TestOllamaClient(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.cache_path = os.path.join(self.tmpdir.name, "test_cache.jsonl")

    def tearDown(self):
        self.tmpdir.cleanup()

    @patch("urllib.request.urlopen")
    def test_ollama_client_generate_success(self, mock_urlopen):
        mock_response_payload = {
            "response": json.dumps({
                "intent": "order_tracking_inquiry",
                "escalation_decision": "AUTO_HANDLE",
                "escalation_reason": "Standard status query.",
                "draft_response": "You can track your order via the Your Orders tab.",
            })
        }
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(mock_response_payload).encode("utf-8")
        mock_resp.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_resp

        client = OllamaClient(cache_path=self.cache_path, use_cache=True)
        res = client.generate("Where is my package?")

        self.assertEqual(res["intent"], "order_tracking_inquiry")
        self.assertEqual(res["escalation_decision"], "AUTO_HANDLE")
        self.assertEqual(mock_urlopen.call_count, 1)

    @patch("urllib.request.urlopen")
    def test_ollama_client_cache_hit_avoids_network(self, mock_urlopen):
        mock_response_payload = {
            "response": json.dumps({
                "intent": "order_cancellation",
                "escalation_decision": "ESCALATE",
                "escalation_reason": "Cancellation request.",
                "draft_response": "I will assist you in cancelling this order.",
            })
        }
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(mock_response_payload).encode("utf-8")
        mock_resp.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_resp

        client = OllamaClient(cache_path=self.cache_path, use_cache=True)

        # First call: hits mock network
        res1 = client.generate("Cancel order #123")
        self.assertEqual(mock_urlopen.call_count, 1)

        # Second call with same prompt: uses cache
        res2 = client.generate("Cancel order #123")
        self.assertEqual(mock_urlopen.call_count, 1)  # unchanged
        self.assertEqual(res1, res2)

    @patch("urllib.request.urlopen")
    def test_ollama_client_invalid_json_raises(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({"response": "Plain text, not JSON"}).encode("utf-8")
        mock_resp.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_resp

        client = OllamaClient(cache_path=self.cache_path, use_cache=False)
        with self.assertRaises(LLMValidationError):
            client.generate("some prompt")

    @patch("urllib.request.urlopen")
    def test_ollama_client_connection_error(self, mock_urlopen):
        import urllib.error
        mock_urlopen.side_effect = urllib.error.URLError("Connection refused")

        client = OllamaClient(cache_path=self.cache_path, use_cache=False)
        with self.assertRaises(OllamaConnectionError):
            client.generate("some prompt")


class TestPromptBuilder(unittest.TestCase):

    def test_prompt_includes_retrieved_examples_and_customer_message(self):
        retrieved = [
            {
                "similarity_score": 0.85,
                "source_id": "12345",
                "customer_message": "Where is my item?",
                "historical_response": "Track it here: https://amazon.com",
            }
        ]
        prompt = build_user_prompt("My package is late", retrieved)

        self.assertIn("Where is my item?", prompt)
        self.assertIn("Track it here: https://amazon.com", prompt)
        self.assertIn("My package is late", prompt)
        self.assertIn("0.8500", prompt)

    def test_prompt_handles_empty_retrieval(self):
        prompt = build_user_prompt("Hello", [])
        self.assertIn("Hello", prompt)
        self.assertIn("No historical examples provided", prompt)


class TestSupportAgent(unittest.TestCase):

    def test_support_agent_full_pipeline_mock(self):
        mock_retriever = MagicMock()
        mock_retriever.search.return_value = [
            {
                "similarity_score": 0.9,
                "source_id": "999",
                "customer_message": "My package was late",
                "historical_response": "We apologize.",
            }
        ]

        mock_llm = MagicMock()
        mock_llm.model = "mock-model"
        mock_llm.generate.return_value = {
            "intent": "delivery_delay",
            "escalation_decision": "ESCALATE",
            "escalation_reason": "Late package delivery complaint.",
            "draft_response": "We apologize for the delivery delay. Let me check your shipment.",
        }

        agent = SupportAgent(retriever=mock_retriever, llm_client=mock_llm)
        result = agent.process_message("My order is 2 days late")

        self.assertEqual(result["intent"], "delivery_delay")
        self.assertEqual(result["escalation_decision"], "ESCALATE")
        self.assertEqual(result["model"], "mock-model")
        self.assertEqual(len(result["retrieved_examples"]), 1)
        mock_retriever.search.assert_called_once_with("My order is 2 days late", top_k=3)
        mock_llm.generate.assert_called_once()


if __name__ == "__main__":
    unittest.main(verbosity=2)
