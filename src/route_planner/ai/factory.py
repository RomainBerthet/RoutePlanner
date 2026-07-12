"""Select an LLM provider by name."""

from __future__ import annotations

from typing import Any

from route_planner.ai.providers.anthropic_provider import AnthropicProvider
from route_planner.ai.providers.interface import ILLMProvider
from route_planner.ai.providers.openai_provider import OpenAIProvider, VLLMProvider

PROVIDERS = ("anthropic", "openai", "vllm")


class LLMFactory:
    @staticmethod
    def get_provider(name: str, **options: Any) -> ILLMProvider:
        name = (name or "anthropic").lower()
        if name == "anthropic":
            return AnthropicProvider(**options)
        if name == "openai":
            return OpenAIProvider(**options)
        if name == "vllm":
            return VLLMProvider(**options)
        raise ValueError(
            f"Provider IA inconnu : {name}. Choix possibles : {', '.join(PROVIDERS)}"
        )
