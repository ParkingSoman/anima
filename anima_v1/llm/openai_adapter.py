from __future__ import annotations

import os

from openai import OpenAI

from anima_v1.llm.base import LLMResponse, Tier


class OpenAIAdapter:
    name = "openai"

    def __init__(
        self,
        *,
        fast_model: str = "gpt-4.1-mini",
        strong_model: str = "gpt-4.1",
        api_key: str | None = None,
    ) -> None:
        self.fast_model = fast_model
        self.strong_model = strong_model
        self.client = OpenAI(api_key=api_key or os.environ.get("OPENAI_API_KEY"))

    def _model_for(self, tier: Tier) -> str:
        return self.strong_model if tier == "strong" else self.fast_model

    def generate(
        self,
        *,
        tier: Tier,
        system: str,
        messages: list[dict],
        max_tokens: int = 1024,
        temperature: float = 0.7,
        stop: list[str] | None = None,
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
