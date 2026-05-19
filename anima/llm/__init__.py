from anima.llm.base import LLMAdapter, LLMResponse, Tier
from anima.llm.retry import RetryConfig, _retry_call
from anima.llm.anthropic_adapter import AnthropicAdapter
from anima.llm.openai_adapter import OpenAIAdapter
from anima.llm.openrouter_adapter import OpenRouterAdapter
from anima.llm.fake_adapter import FakeAdapter, FlakyFakeAdapter

__all__ = [
    "LLMAdapter",
    "LLMResponse",
    "Tier",
    "RetryConfig",
    "AnthropicAdapter",
    "OpenAIAdapter",
    "OpenRouterAdapter",
    "FakeAdapter",
    "FlakyFakeAdapter",
]


def make_adapter(provider: str = "anthropic", **kwargs) -> LLMAdapter:
    provider = provider.lower()
    if provider == "anthropic":
        return AnthropicAdapter(**kwargs)
    if provider == "openai":
        return OpenAIAdapter(**kwargs)
    if provider == "openrouter":
        return OpenRouterAdapter(**kwargs)
    if provider == "fake":
        return FakeAdapter(**kwargs)
    raise ValueError(f"unknown provider: {provider}")
