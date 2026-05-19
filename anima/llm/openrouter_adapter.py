"""OpenRouter LLM adapter.

Wraps OpenRouter's OpenAI-compatible Chat Completions API using the `openai`
client. Both `fast_model` and `strong_model` default to
`deepseek/deepseek-v4-flash` deliberately: DeepSeek V4 Flash is cheap enough to
serve both tiers, and callers can pass `strong_model="deepseek/deepseek-v4-pro"`
to upgrade the strong-tier (inner monologue + response generation) if needed.
`app_name` defaults to "anima" to attribute requests; `referer` defaults to
`None` because there is no meaningful project URL to advertise by default.
The `OPENROUTER_API_KEY` environment variable is required (unless `api_key` is
passed explicitly).

The adapter also pins explicit `timeout=60.0` and `max_retries=2` defaults on
the underlying `OpenAI` client. The SDK's out-of-the-box defaults (600s timeout
with 2 retries = up to ~30 minutes per call on a stuck socket) once let a
single request hang for 34 minutes during a battery run; making both values
explicit ensures we fail fast and surface upstream stalls.
"""

from __future__ import annotations

import os
from typing import Any, Callable

from openai import OpenAI

from anima.llm.base import LLMResponse, Tier
from anima.llm.retry import RetryConfig, _retry_call


class OpenRouterAdapter:
    name = "openrouter"

    def __init__(
        self,
        *,
        fast_model: str = "deepseek/deepseek-v4-flash",
        strong_model: str = "deepseek/deepseek-v4-flash",
        api_key: str | None = None,
        base_url: str = "https://openrouter.ai/api/v1",
        referer: str | None = None,
        app_name: str | None = "anima",
        timeout: float = 60.0,
        max_retries: int = 2,
        retry_cfg: RetryConfig | None = None,
    ) -> None:
        self.fast_model = fast_model
        self.strong_model = strong_model
        headers: dict[str, str] = {}
        if referer:
            headers["HTTP-Referer"] = referer
        if app_name:
            headers["X-Title"] = app_name
        self.client = OpenAI(
            # Subscript (not .get) is deliberate: fail fast with KeyError if the
            # env var is unset and no explicit api_key was provided.
            api_key=api_key or os.environ["OPENROUTER_API_KEY"],
            base_url=base_url,
            default_headers=headers or None,
            # Explicit timeout/retries: SDK defaults (600s x 3 attempts) can hang ~30 min on a stuck socket.
            timeout=timeout,
            max_retries=max_retries,
        )
        # Adapter-level retry sits ABOVE the SDK-level max_retries. The SDK
        # handles per-request retries on its own clock; the adapter retry is
        # a higher-level guard for cases the SDK gives up on (e.g. final 5xx).
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
        # Investigation: capture the full message dict BEFORE extracting
        # .content. DeepSeek's chat-completions response often carries
        # ``reasoning_content`` (separate from ``content``) — if we only
        # read .content we miss the model's actual thinking. Capture via
        # pydantic v2 ``model_dump`` with defensive fallbacks; never crash.
        msg_obj = resp.choices[0].message
        msg_dict: dict | None
        try:
            msg_dict = msg_obj.model_dump()
        except Exception:  # noqa: BLE001 — best-effort capture
            try:
                msg_dict = dict(msg_obj)
            except Exception:  # noqa: BLE001
                try:
                    msg_dict = {
                        k: getattr(msg_obj, k, None)
                        for k in ("role", "content", "reasoning_content",
                                  "tool_calls", "function_call",
                                  "refusal", "annotations")
                    }
                except Exception:  # noqa: BLE001
                    msg_dict = None
        text = (msg_dict.get("content") if isinstance(msg_dict, dict) else None) or ""
        # finish_reason is how OpenAI/OpenRouter signal *why* the call ended.
        # "stop" / "stop_sequence" = the model emitted an end-of-turn (legit
        # silence if text is also empty). "length" = max_tokens cap hit
        # mid-stream. "content_filter" = the safety layer redacted. "error"
        # = upstream blew up but the SDK still returned a (likely-empty)
        # message. The retry layer reads this off LLMResponse to decide
        # whether empty .text deserves a retry. Some provider responses may
        # omit it; we default to None and the retry layer treats that as
        # "unknown → assume genuine" so we don't over-retry.
        finish_reason = getattr(resp.choices[0], "finish_reason", None)
        usage = {
            "input_tokens": resp.usage.prompt_tokens,
            "output_tokens": resp.usage.completion_tokens,
            "cache_read_tokens": 0,
            "cache_create_tokens": 0,
        }
        return LLMResponse(text=text, usage=usage, raw={"id": resp.id},
                           finish_reason=finish_reason,
                           raw_message=msg_dict)

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
