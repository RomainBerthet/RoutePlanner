"""Provider abstraction for large language models.

The connector is intentionally provider-neutral: the same two methods work
across Anthropic, OpenAI and any OpenAI-compatible server (vLLM, LM Studio,
Ollama, ...). Provider SDKs are imported lazily inside each implementation so
the base install stays light — a user only needs the SDK for the backend they
actually use.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict


class ILLMProvider(ABC):
    """Minimal chat surface used by the travel-intelligence service."""

    @abstractmethod
    def complete_json(
        self,
        system: str,
        user: str,
        schema: Dict[str, Any],
        max_tokens: int = 4096,
    ) -> Dict[str, Any]:
        """Return a JSON object constrained to ``schema``.

        Implementations must return a parsed ``dict`` (never a raw string) and
        should use the provider's structured-output feature when available.
        """

    @abstractmethod
    def complete_text(self, system: str, user: str, max_tokens: int = 2048) -> str:
        """Return free-form text."""
