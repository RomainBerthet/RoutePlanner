"""OpenAI-compatible backend built on the official ``openai`` SDK.

Works with the OpenAI API and any OpenAI-compatible server (vLLM, LM Studio,
Ollama, ...) via a ``base_url`` override — that is why vLLM support is just a
thin subclass. JSON calls try native ``json_schema`` structured output and
gracefully fall back to ``json_object`` for servers that don't support it.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict

from route_planner.ai.providers.interface import ILLMProvider

DEFAULT_MODEL = "gpt-4o-mini"


class OpenAIProvider(ILLMProvider):
    def __init__(
        self,
        model: str | None = None,
        api_key: str | None = None,
        base_url: str | None = None,
        client=None,
    ):
        self.model = model or os.getenv("OPENAI_MODEL") or DEFAULT_MODEL
        self.base_url = base_url or os.getenv("OPENAI_BASE_URL")
        self._api_key = api_key
        self._client = client

    @property
    def client(self):
        if self._client is None:
            try:
                from openai import OpenAI
            except ImportError as exc:  # pragma: no cover - exercised via message
                raise RuntimeError(
                    "Le provider OpenAI/vLLM requiert le paquet 'openai' "
                    "(pip install openai)."
                ) from exc
            kwargs: Dict[str, Any] = {}
            if self._api_key:
                kwargs["api_key"] = self._api_key
            if self.base_url:
                kwargs["base_url"] = self.base_url
            self._client = OpenAI(**kwargs)
        return self._client

    def complete_json(
        self,
        system: str,
        user: str,
        schema: Dict[str, Any],
        max_tokens: int = 4096,
    ) -> Dict[str, Any]:
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                max_tokens=max_tokens,
                messages=messages,
                response_format={
                    "type": "json_schema",
                    "json_schema": {"name": "response", "schema": schema, "strict": False},
                },
            )
        except Exception:
            # Server without json_schema support: fall back to json_object and
            # embed the schema in the prompt as a hint.
            messages[1]["content"] = (
                f"{user}\n\nReponds uniquement en JSON respectant ce schema:\n"
                f"{json.dumps(schema)}"
            )
            response = self.client.chat.completions.create(
                model=self.model,
                max_tokens=max_tokens,
                messages=messages,
                response_format={"type": "json_object"},
            )
        return json.loads(response.choices[0].message.content)

    def complete_text(self, system: str, user: str, max_tokens: int = 2048) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            max_tokens=max_tokens,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        return response.choices[0].message.content


class VLLMProvider(OpenAIProvider):
    """OpenAI-compatible provider preconfigured for a local vLLM server."""

    def __init__(self, model: str | None = None, base_url: str | None = None, **kwargs):
        base_url = base_url or os.getenv("VLLM_URL") or "http://localhost:8000/v1"
        api_key = kwargs.pop("api_key", None) or os.getenv("VLLM_API_KEY") or "EMPTY"
        super().__init__(
            model=model or os.getenv("VLLM_MODEL"),
            api_key=api_key,
            base_url=base_url,
            **kwargs,
        )
