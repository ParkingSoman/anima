from anima_v1.llm.base import LLMAdapter, LLMResponse, Tier
from anima_v1.llm.anthropic_adapter import AnthropicAdapter
from anima_v1.llm.openai_adapter import OpenAIAdapter
from anima_v1.llm.openrouter_adapter import OpenRouterAdapter
from anima_v1.llm.fake_adapter import FakeAdapter

__all__ = [
    "LLMAdapter",
    "LLMResponse",
    "Tier",
    "AnthropicAdapter",
    "OpenAIAdapter",
    "OpenRouterAdapter",
    "FakeAdapter",
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
