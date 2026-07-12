import pytest

from route_planner.ai.factory import LLMFactory
from route_planner.ai.providers import AnthropicProvider, OpenAIProvider, VLLMProvider


def test_factory_returns_requested_provider():
    assert isinstance(LLMFactory.get_provider("anthropic"), AnthropicProvider)
    assert isinstance(LLMFactory.get_provider("openai"), OpenAIProvider)
    assert isinstance(LLMFactory.get_provider("vllm"), VLLMProvider)


def test_factory_defaults_to_anthropic():
    assert isinstance(LLMFactory.get_provider(""), AnthropicProvider)


def test_factory_rejects_unknown_provider():
    with pytest.raises(ValueError):
        LLMFactory.get_provider("bogus")


def test_vllm_defaults_to_local_openai_endpoint():
    provider = LLMFactory.get_provider("vllm")
    assert provider.base_url.endswith("/v1")


def test_provider_options_are_forwarded():
    provider = LLMFactory.get_provider("openai", model="gpt-4o", base_url="http://x/v1")
    assert provider.model == "gpt-4o"
    assert provider.base_url == "http://x/v1"


def test_from_env_reads_ai_provider(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "vllm")
    monkeypatch.setenv("VLLM_MODEL", "Qwen/Qwen3.5-32B-Instruct")
    monkeypatch.setenv("VLLM_URL", "http://localhost:8000/v1")
    provider = LLMFactory.from_env()
    assert isinstance(provider, VLLMProvider)
    assert provider.model == "Qwen/Qwen3.5-32B-Instruct"
    assert provider.base_url == "http://localhost:8000/v1"


def test_from_env_defaults_to_anthropic(monkeypatch):
    monkeypatch.delenv("AI_PROVIDER", raising=False)
    assert isinstance(LLMFactory.from_env(), AnthropicProvider)
