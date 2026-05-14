from __future__ import annotations

import os
from typing import Literal

from anthropic import Anthropic

from anima_v1.llm.base import LLMResponse, Tier


class AnthropicAdapter:
    name = "anthropic"

    def __init__(
        self,
        *,
        fast_model: str = "claude-haiku-4-5-20251001",
        strong_model: str = "claude-opus-4-7",
        api_key: str | None = None,
    ) -> None:
        self.fast_model = fast_model
        self.strong_model = strong_model
        self.client = Anthropic(api_key=api_key or os.environ.get("ANTHROPIC_API_KEY"))

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
        system_blocks = [{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}]
        resp = self.client.messages.create(
            model=self._model_for(tier),
            system=system_blocks,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
            stop_sequences=stop or [],
        )
        text = "".join(b.text for b in resp.content if getattr(b, "type", None) == "text")
        usage = {
            "input_tokens": resp.usage.input_tokens,
            "output_tokens": resp.usage.output_tokens,
            "cache_read_tokens": getattr(resp.usage, "cache_read_input_tokens", 0) or 0,
            "cache_create_tokens": getattr(resp.usage, "cache_creation_input_tokens", 0) or 0,
        }
        return LLMResponse(text=text, usage=usage, raw={"id": resp.id, "stop_reason": resp.stop_reason})
