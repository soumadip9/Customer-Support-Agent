"""
src/llm/ollama_client.py

Reusable client for local Ollama models with structured JSON output enforcement,
strict schema validation, and persistent file-based caching.
"""

from __future__ import annotations

import hashlib
import json
import os
import urllib.error
import urllib.request
from typing import Any

VALID_INTENTS: frozenset[str] = frozenset({
    "delivery_delay",
    "order_tracking_inquiry",
    "order_cancellation",
    "refund_inquiry",
    "damaged_or_wrong_item",
    "payment_and_billing_issue",
    "prime_membership_inquiry",
    "account_access_and_security",
    "digital_and_device_troubleshooting",
    "promotion_and_discount_inquiry",
    "driver_and_packaging_feedback",
    "general_product_and_service_faq",
    "other_or_unsupported",
})

VALID_DECISIONS: frozenset[str] = frozenset({"AUTO_HANDLE", "ESCALATE"})
REQUIRED_KEYS: frozenset[str] = frozenset({
    "intent",
    "escalation_decision",
    "escalation_reason",
    "draft_response",
})

DEFAULT_CACHE_PATH = r"c:\CustomerSupport\data\ollama_cache.jsonl"


class LLMValidationError(Exception):
    """Raised when model output fails structural schema or taxonomy validation."""
    pass


class OllamaConnectionError(Exception):
    """Raised when connection to local Ollama server fails."""
    pass


def validate_structured_output(data: Any) -> dict[str, str]:
    """
    Strictly validates parsed JSON against the required response schema.

    Schema:
    {
        "intent": str (one of 13 taxonomy labels),
        "escalation_decision": str ("AUTO_HANDLE" or "ESCALATE"),
        "escalation_reason": str (non-empty),
        "draft_response": str (non-empty)
    }
    """
    if not isinstance(data, dict):
        raise LLMValidationError(f"Expected a JSON object, got {type(data).__name__}: {data!r}")

    missing = REQUIRED_KEYS - set(data.keys())
    if missing:
        raise LLMValidationError(f"Missing required keys in LLM output: {sorted(missing)}")

    intent = str(data["intent"]).strip()
    escalation_decision = str(data["escalation_decision"]).strip()
    escalation_reason = str(data["escalation_reason"]).strip()
    draft_response = str(data["draft_response"]).strip()

    if intent not in VALID_INTENTS:
        raise LLMValidationError(
            f"Invalid intent '{intent}'. Must be one of: {sorted(VALID_INTENTS)}"
        )

    if escalation_decision not in VALID_DECISIONS:
        raise LLMValidationError(
            f"Invalid escalation_decision '{escalation_decision}'. Must be 'AUTO_HANDLE' or 'ESCALATE'."
        )

    if not escalation_reason:
        raise LLMValidationError("escalation_reason must be a non-empty string.")

    if not draft_response:
        raise LLMValidationError("draft_response must be a non-empty string.")

    return {
        "intent": intent,
        "escalation_decision": escalation_decision,
        "escalation_reason": escalation_reason,
        "draft_response": draft_response,
    }


class OllamaClient:
    """
    Client for interacting with local Ollama instance with caching and JSON validation.
    """

    def __init__(
        self,
        model: str = "llama3.2:3b",
        base_url: str = "http://127.0.0.1:11434",
        timeout: int = 60,
        cache_path: str = DEFAULT_CACHE_PATH,
        use_cache: bool = True,
    ):
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.cache_path = cache_path
        self.use_cache = use_cache
        self._cache: dict[str, dict[str, str]] = {}
        if self.use_cache:
            self._load_cache()

    def _compute_cache_key(self, prompt: str, system_prompt: str) -> str:
        content = f"{self.model}:::{system_prompt}:::{prompt}"
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def _load_cache(self) -> None:
        if os.path.exists(self.cache_path):
            with open(self.cache_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            item = json.loads(line)
                            key = item.get("key")
                            val = item.get("value")
                            if key and val:
                                self._cache[key] = val
                        except json.JSONDecodeError:
                            continue

    def _save_cache_entry(self, key: str, value: dict[str, str]) -> None:
        self._cache[key] = value
        os.makedirs(os.path.dirname(self.cache_path), exist_ok=True)
        with open(self.cache_path, "a", encoding="utf-8") as f:
            f.write(json.dumps({"key": key, "value": value}, ensure_ascii=False) + "\n")

    def generate(self, prompt: str, system_prompt: str = "") -> dict[str, str]:
        """
        Sends prompt to Ollama, enforces structured JSON output, validates schema,
        and manages caching.
        """
        cache_key = self._compute_cache_key(prompt, system_prompt)

        if self.use_cache and cache_key in self._cache:
            return self._cache[cache_key]

        endpoint = f"{self.base_url}/api/generate"
        payload = {
            "model": self.model,
            "prompt": prompt,
            "system": system_prompt,
            "format": "json",
            "stream": False,
            "options": {
                "temperature": 0.0,  # Zero temperature for deterministic classification
            },
        }

        req = urllib.request.Request(
            endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                resp_data = json.loads(resp.read().decode("utf-8"))
        except urllib.error.URLError as e:
            raise OllamaConnectionError(
                f"Failed to connect to Ollama at {endpoint}: {e}. Ensure 'ollama serve' is running."
            ) from e
        except Exception as e:
            raise OllamaConnectionError(f"Unexpected error calling Ollama: {e}") from e

        raw_response = resp_data.get("response", "")
        if not raw_response:
            raise LLMValidationError("Empty response received from Ollama model.")

        try:
            parsed_json = json.loads(raw_response)
        except json.JSONDecodeError as e:
            raise LLMValidationError(
                f"Failed to parse JSON from model output: {e}\nRaw output: {raw_response!r}"
            ) from e

        validated = validate_structured_output(parsed_json)

        if self.use_cache:
            self._save_cache_entry(cache_key, validated)

        return validated
