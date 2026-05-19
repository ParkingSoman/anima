from __future__ import annotations

import os
from typing import Any, Callable

from openai import OpenAI

from anima.llm.base import LLMResponse, Tier
from anima.llm.retry import RetryConfig, _retry_call


class OpenAIAdapter:
    name = "openai"

    def __init__(
        self,
        *,
        fast_model: str = "gpt-4.1-mini",
        strong_model: str = "gpt-4.1",
        api_key: str | None = None,
        retry_cfg: RetryConfig | None = None,
    ) -> None:
        self.fast_model = fast_model
        self.strong_model = strong_model
        self.client = OpenAI(api_key=api_key or os.environ.get("OPENAI_API_KEY"))
        self.retry_cfg = retry_cfg or RetryConfig()

    def _model_for(self, tier: Tier) -> str:
        return self.strong_model if tier == "strong" else self.fast_model

    def _raw_call(
        self,
        *,
        tier: Tier,
        system: str,
        messages: list[dict],
        max_tokens: int,
        temperature: float,
        stop: list[str] | None,
    ) -> LLMResponse:
        chat = [{"role": "system", "content": system}] + messages
        resp = self.client.chat.completions.create(
            model=self._model_for(tier),
            messages=chat,
            max_tokens=max_tokens,
            temperature=temperature,
            stop=stop,
        )
        text = resp.choices[0].message.content or ""
        usage = {
            "input_tokens": resp.usage.prompt_tokens,
            "output_tokens": resp.usage.completion_tokens,
            "cache_read_tokens": 0,
            "cache_create_tokens": 0,
        }
        return LLMResponse(text=text, usage=usage, raw={"id": resp.id})

    def generate(
        self,
        *,
        tier: Tier,
        system: str,
        messages: list[dict],
        max_tokens: int = 1024,
        temperature: float = 0.7,
        stop: list[str] | None = None,
        retry_cfg: RetryConfig | None = None,
        is_valid: Callable[[Any], bool] | None = None,
    ) -> LLMResponse:
        cfg = retry_cfg or self.retry_cfg
        return _retry_call(
            lambda: self._raw_call(
                tier=tier, system=system, messages=messages,
                max_tokens=max_tokens, temperature=temperature, stop=stop,
            ),
            cfg,
            is_valid=is_valid,
        )
