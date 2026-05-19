from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Protocol

from anima.llm.retry import RetryConfig

Tier = Literal["fast", "strong"]


@dataclass
class LLMResponse:
    text: str
    usage: dict = field(default_factory=dict)
    raw: dict = field(default_factory=dict)
    # Why the call ended, as reported by the provider. Mirrors
    # OpenAI/OpenRouter ``choices[0].finish_reason`` and Anthropic
    # ``stop_reason``. Used by the retry layer (anima.llm.retry) to
    # decide whether an empty .text was a genuine "model chose to say
    # nothing" (e.g. ``stop``/``end_turn``) — which should NOT retry —
    # versus a cutoff/error (``length``/``content_filter``/``error``/etc.)
    # — which SHOULD retry. Defaults to None so adapters that don't yet
    # populate it pass type-checks; the retry layer treats None as
    # "unknown → assume genuine" so legacy code paths don't suddenly
    # start retrying.
    finish_reason: str | None = None
    # Fix (investigation): the full provider message object as a dict.
    # OpenAI/OpenRouter chat-completions ``choices[0].message`` may carry
    # extra fields beyond ``.content`` — notably DeepSeek's
    # ``reasoning_content`` (chain-of-thought text), ``tool_calls``,
    # ``function_call``, ``refusal``, ``annotations`` etc. When
    # ``.content`` arrives empty with ``finish_reason='length'`` we need
    # to inspect what the model actually produced. Adapters populate
    # this with ``message.model_dump()`` (pydantic v2) or an equivalent.
    # None means the adapter didn't capture it (e.g. FakeAdapter).
    raw_message: dict | None = None


class LLMAdapter(Protocol):
    """Provider-agnostic adapter. Implementations route 'fast' tier to a cheap fast
    model and 'strong' tier to the strongest available reasoning model. The cognitive
    core never touches a provider SDK directly.

    Implementations MUST:
      - accept a stable `system` for prompt caching;
      - support multi-message conversation (`messages` is OpenAI-style list of
        {"role": "user"|"assistant", "content": str});
      - return an LLMResponse with the assistant text in `.text`.
      - accept an optional ``retry_cfg`` per-call override (None means use the
        adapter's default policy).
    """

    name: str
    retry_cfg: RetryConfig

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
    ) -> LLMResponse:
        ...
