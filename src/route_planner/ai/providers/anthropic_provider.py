"""Anthropic backend built on the official ``anthropic`` SDK.

Defaults follow Anthropic's current guidance: model ``claude-opus-4-8`` with
adaptive thinking, and structured outputs (``output_config.format``) for the
JSON planning calls so responses are guaranteed to parse.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict

from route_planner.ai.providers.interface import ILLMProvider

DEFAULT_MODEL = "claude-opus-4-8"


class AnthropicProvider(ILLMProvider):
    def __init__(
        self,
        model: str | None = None,
        api_key: str | None = None,
        effort: str = "medium",
        client=None,
    ):
        self.model = model or os.getenv("ANTHROPIC_MODEL") or DEFAULT_MODEL
        self.effort = effort
        self._api_key = api_key
        self._client = client

    @property
    def client(self):
        if self._client is None:
            try:
                import anthropic
            except ImportError as exc:  # pragma: no cover - exercised via message
                raise RuntimeError(
                    "Le provider Anthropic requiert le paquet 'anthropic' "
                    "(pip install anthropic)."
                ) from exc
            kwargs = {"api_key": self._api_key} if self._api_key else {}
            self._client = anthropic.Anthropic(**kwargs)
        return self._client

    def complete_json(
        self,
        system: str,
        user: str,
        schema: Dict[str, Any],
        max_tokens: int = 4096,
    ) -> Dict[str, Any]:
        response = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            system=system,
            thinking={"type": "adaptive"},
            output_config={
                "effort": self.effort,
                "format": {"type": "json_schema", "schema": schema},
            },
            messages=[{"role": "user", "content": user}],
        )
        return json.loads(self._first_text(response))

    def complete_text(self, system: str, user: str, max_tokens: int = 2048) -> str:
        response = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            system=system,
            thinking={"type": "adaptive"},
            output_config={"effort": self.effort},
            messages=[{"role": "user", "content": user}],
        )
        return self._first_text(response)

    @staticmethod
    def _first_text(response) -> str:
        for block in response.content:
            if getattr(block, "type", None) == "text":
                return block.text
        raise ValueError("Reponse Anthropic sans bloc texte")
