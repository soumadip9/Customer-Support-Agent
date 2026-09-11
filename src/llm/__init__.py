"""
src/llm/__init__.py
"""
from .agent import SupportAgent, SYSTEM_PROMPT, build_user_prompt
from .ollama_client import (
    OllamaClient,
    LLMValidationError,
    OllamaConnectionError,
    VALID_INTENTS,
    VALID_DECISIONS,
    validate_structured_output,
)

__all__ = [
    "SupportAgent",
    "SYSTEM_PROMPT",
    "build_user_prompt",
    "OllamaClient",
    "LLMValidationError",
    "OllamaConnectionError",
    "VALID_INTENTS",
    "VALID_DECISIONS",
    "validate_structured_output",
]
