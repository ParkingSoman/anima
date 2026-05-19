from __future__ import annotations

import os
from typing import Any, Callable, Literal

from anthropic import Anthropic

from anima.llm.base import LLMResponse, Tier
from anima.llm.retry import RetryConfig, _retry_call


class AnthropicAdapter:
    name = "anthropic"

    def __init__(
        self,
        *,
        fast_model: str = "claude-haiku-4-5-20251001",
        strong_model: str = "claude-opus-4-7",
        api_key: str | None = None,
        retry_cfg: RetryConfig | None = None,
    ) -> None:
        self.fast_model = fast_model
        self.strong_model = strong_model
        self.client = Anthropic(api_key=api_key or os.environ.get("ANTHROPIC_API_KEY"))
        # Default retry policy: 3 attempts, exponential + jitter. Tunable
        # per-call via ``generate(retry_cfg=...)``.
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
        # Anthropic's analogue of OpenAI's finish_reason is `stop_reason`
        # (values: "end_turn", "stop_sequence", "max_tokens", "tool_use",
        # "pause_turn", "refusal"). We surface it on the cross-provider
        # LLMResponse.finish_reason so the retry layer can use one rule for
        # both providers. The original verbatim value is also kept in
        # ``raw["stop_reason"]`` for debugging.
        stop_reason = getattr(resp, "stop_reason", None)
        return LLMResponse(text=text, usage=usage,
                           raw={"id": resp.id, "stop_reason": stop_reason},
                           finish_reason=stop_reason)

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
