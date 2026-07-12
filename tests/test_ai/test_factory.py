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
