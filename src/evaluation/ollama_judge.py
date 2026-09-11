"""
src/evaluation/ollama_judge.py

Local Ollama LLM-as-a-Judge Evaluation Module.
Uses local llama3.2:3b to independently evaluate customer-support draft responses
against a strict 5-dimensional rubric with persistent caching, retries, and structured JSON validation.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


PROMPT_VERSION = "v1.0"
DEFAULT_OLLAMA_URL = "http://127.0.0.1:11434"
DEFAULT_MODEL = "llama3.2:3b"
DEFAULT_CACHE_PATH = r"c:\CustomerSupport\data\ollama_judge_cache.jsonl"


RUBRIC_TEXT = """
Score every dimension from 1 to 5:

A. RELEVANCE & INTENT ALIGNMENT:
1 = irrelevant / off-topic
2 = mostly misses the issue
3 = partially addresses the issue
4 = addresses the main issue with minor gaps
5 = directly and accurately addresses the customer's issue

B. ESCALATION / ACTIONABILITY:
1 = no useful next step
2 = confusing or inappropriate next step
3 = somewhat actionable but imperfect
4 = appropriate and actionable
5 = exactly appropriate next step for the customer's situation

C. EMPATHY / TONE:
1 = rude / inappropriate
2 = dismissive / robotic
3 = neutral
4 = polite / professional
5 = empathetic, professional, concise and brand-appropriate

D. FACTUALITY / POLICY SAFETY:
1 = major hallucination or unsafe request
2 = serious unsupported guidance
3 = borderline / imprecise
4 = generally correct and safe
5 = fully safe, factual and policy-appropriate

E. CLARITY / CONCISENESS:
1 = incoherent
2 = confusing
3 = understandable but awkward / verbose
4 = clear and readable
5 = exceptionally clear and concise

OVERALL:
Average of the five scores rounded to 2 decimal places.
"""


class OllamaJudgeError(Exception):
    """Base exception for Ollama Judge operations."""
    pass


class OllamaJudgeConnectionError(OllamaJudgeError):
    """Raised when connection to local Ollama server fails."""
    pass


class OllamaJudgeValidationError(OllamaJudgeError):
    """Raised when Ollama output fails structural schema or rubric validation."""
    pass


@dataclass
class OllamaJudgeResult:
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

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def validate_ollama_judge_output(data: Any) -> OllamaJudgeResult:
    """Validate and sanitize JSON output from Ollama Judge."""
    if not isinstance(data, dict):
        raise OllamaJudgeValidationError(f"Expected dict from judge, got {type(data)}")

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
    ]
    for key in required_keys:
        if key not in data:
            raise OllamaJudgeValidationError(f"Missing required key in judge output: {key}")

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
            raise OllamaJudgeValidationError(f"Score '{key}' must be numeric, got {type(val)}")
        val_int = int(round(val))
        if not (1 <= val_int <= 5):
            raise OllamaJudgeValidationError(f"Score '{key}' must be an integer between 1 and 5, got {val_int}")
        scores[key] = val_int

    computed_overall = round(sum(scores.values()) / 5.0, 2)

    strengths = data.get("strengths", [])
    if not isinstance(strengths, list):
        strengths = [str(strengths)]

    weaknesses = data.get("weaknesses", [])
    if not isinstance(weaknesses, list):
        weaknesses = [str(weaknesses)]

    return OllamaJudgeResult(
        relevance_score=scores["relevance_score"],
        relevance_reasoning=str(data.get("relevance_reasoning", "")).strip(),
        escalation_actionability_score=scores["escalation_actionability_score"],
        escalation_reasoning=str(data.get("escalation_reasoning", "")).strip(),
        empathy_tone_score=scores["empathy_tone_score"],
        empathy_reasoning=str(data.get("empathy_reasoning", "")).strip(),
        policy_compliance_score=scores["policy_compliance_score"],
        policy_reasoning=str(data.get("policy_reasoning", "")).strip(),
        clarity_score=scores["clarity_score"],
        clarity_reasoning=str(data.get("clarity_reasoning", "")).strip(),
        overall_score=computed_overall,
        strengths=[str(s).strip() for s in strengths if str(s).strip()],
        weaknesses=[str(w).strip() for w in weaknesses if str(w).strip()],
    )


def build_judge_prompt(
    customer_message: str,
    predicted_intent: str,
    predicted_escalation_decision: str,
    draft_response: str,
) -> str:
    """
    Construct the single-example evaluation prompt for the local LLM judge.
    Strictly excludes all gold labels, human notes, or reference answers.
    """
    prompt = f"""You are an expert Customer Support Quality Assurance Judge.
Evaluate the following AI-generated customer support draft response for Amazon Customer Service (@AmazonHelp).

[CUSTOMER MESSAGE]
"{customer_message}"

[CLASSIFIED INTENT]
{predicted_intent}

[ESCALATION DECISION]
{predicted_escalation_decision}

[GENERATED DRAFT RESPONSE]
"{draft_response}"

[RUBRIC]
{RUBRIC_TEXT}

[INSTRUCTIONS]
Return ONLY a valid JSON object strictly matching this schema:
{{
  "relevance_score": <1-5 integer>,
  "relevance_reasoning": "<short explanation>",
  "escalation_actionability_score": <1-5 integer>,
  "escalation_reasoning": "<short explanation>",
  "empathy_tone_score": <1-5 integer>,
  "empathy_reasoning": "<short explanation>",
  "policy_compliance_score": <1-5 integer>,
  "policy_reasoning": "<short explanation>",
  "clarity_score": <1-5 integer>,
  "clarity_reasoning": "<short explanation>",
  "overall_score": <float average of the 5 scores, 1.00 to 5.00>,
  "strengths": ["<strength 1>", "<strength 2>"],
  "weaknesses": ["<weakness 1>"]
}}"""
    return prompt.strip()


class OllamaJudgeEvaluator:
    """
    Client for evaluating response quality using local Ollama model.
    Includes persistent caching, retry logic, metrics tracking, and schema validation.
    """

    def __init__(
        self,
        base_url: str = DEFAULT_OLLAMA_URL,
        model: str = DEFAULT_MODEL,
        cache_path: Optional[str] = DEFAULT_CACHE_PATH,
        temperature: float = 0.0,
        timeout: int = 120,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.cache_path = cache_path
        self.temperature = temperature
        self.timeout = timeout
        self._cache: Dict[str, Dict[str, Any]] = {}
        self.ollama_calls = 0
        self.cache_hits = 0
        self.cache_misses = 0
        self.successful_judgments = 0
        self.failed_judgments = 0

        if self.cache_path:
            self._load_cache()

    def _load_cache(self) -> None:
        if not self.cache_path or not os.path.exists(self.cache_path):
            return
        with open(self.cache_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    if "cache_key" in entry and "result" in entry:
                        self._cache[entry["cache_key"]] = entry["result"]
                except Exception:
                    continue

    def _save_cache_entry(self, key: str, result: Dict[str, Any]) -> None:
        if not self.cache_path:
            return
        os.makedirs(os.path.dirname(os.path.abspath(self.cache_path)), exist_ok=True)
        self._cache[key] = result
        with open(self.cache_path, "a", encoding="utf-8") as f:
            f.write(json.dumps({"cache_key": key, "result": result}, ensure_ascii=False) + "\n")

    def _compute_cache_key(
        self,
        customer_message: str,
        predicted_intent: str,
        predicted_escalation_decision: str,
        draft_response: str,
    ) -> str:
        payload = (
            f"model:{self.model}|prompt:{PROMPT_VERSION}|msg:{customer_message}|"
            f"intent:{predicted_intent}|esc:{predicted_escalation_decision}|resp:{draft_response}"
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def check_health(self) -> bool:
        """Verify Ollama server is reachable and model is available."""
        url = f"{self.base_url}/api/tags"
        try:
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                models = [m.get("name") for m in data.get("models", [])]
                if not any(self.model in m for m in models if m):
                    return False
                return True
        except Exception:
            return False

    def evaluate_response(
        self,
        customer_message: str,
        predicted_intent: str,
        predicted_escalation_decision: str,
        draft_response: str,
    ) -> OllamaJudgeResult:
        """Evaluate a single response using Ollama LLM judge with caching and retry."""
        cache_key = self._compute_cache_key(
            customer_message=customer_message,
            predicted_intent=predicted_intent,
            predicted_escalation_decision=predicted_escalation_decision,
            draft_response=draft_response,
        )

        if cache_key in self._cache:
            self.cache_hits += 1
            self.successful_judgments += 1
            return validate_ollama_judge_output(self._cache[cache_key])

        self.cache_misses += 1
        prompt = build_judge_prompt(
            customer_message=customer_message,
            predicted_intent=predicted_intent,
            predicted_escalation_decision=predicted_escalation_decision,
            draft_response=draft_response,
        )

        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "format": "json",
            "options": {
                "temperature": self.temperature,
                "seed": 42,
            },
        }

        url = f"{self.base_url}/api/generate"
        raw_response = ""
        last_error = None

        # Try up to 2 attempts with timeout
        for attempt in range(2):
            try:
                req = urllib.request.Request(
                    url,
                    data=json.dumps(payload).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    self.ollama_calls += 1
                    body = json.loads(resp.read().decode("utf-8"))
                    raw_response = body.get("response", "")
                    break
            except Exception as e:
                last_error = e
                time.sleep(1)

        if not raw_response:
            self.failed_judgments += 1
            raise OllamaJudgeConnectionError(f"Failed to communicate with Ollama at {url}: {last_error}")

        try:
            parsed_data = json.loads(raw_response)
        except json.JSONDecodeError as e:
            self.failed_judgments += 1
            raise OllamaJudgeValidationError(f"Ollama returned invalid JSON: {raw_response[:200]}") from e

        try:
            result = validate_ollama_judge_output(parsed_data)
        except OllamaJudgeValidationError:
            self.failed_judgments += 1
            raise

        self._save_cache_entry(cache_key, result.to_dict())
        self.successful_judgments += 1
        return result
