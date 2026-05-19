"""LLM-call capture wrapper — record every model output for the trace.

Why: every subsystem (perception, appraisal, inner_monologue, response_generator,
memory_retrieval, user_prediction) reads ``LLMResponse.text`` and discards the
rest. The discarded ``LLMResponse.raw_message`` may contain DeepSeek's
``reasoning`` chain-of-thought, ``tool_calls``, ``annotations``, ``refusal``,
``function_call``, ``audio``, etc. — material the user explicitly wants to
preserve ("everything the model does is cool stuff!").

Design: rather than thread a capture argument through every subsystem we wrap
the LLM adapter ONCE at :class:`anima.core.Anima` construction time. Every
``self.llm.generate(...)`` call from any subsystem then passes through the
wrapper transparently. The wrapper's ``__getattr__`` forwards any non-capture
attribute (``retry_cfg``, ``fast_model``, ``name``, ``model``, ...) to the
inner adapter so existing call sites that read those continue to work.

Per-turn lifecycle (driven by :class:`anima.core.Anima`):
  * at the START of each ``respond()``, ``reset()`` clears the buffer
  * during the turn, every subsystem call appends a :class:`CapturedLLMCall`
  * at the END of the turn (success OR partial-trace failure), the Anima
    snapshots the buffer onto the :class:`TurnTrace`'s ``llm_calls`` field

Captured fields per call:
  * tier            — "fast" or "strong" (which model bucket was used)
  * system_prompt_chars — length of the system prompt (cheaper than dumping it)
  * user_message_preview — last user-role message, truncated to ~200 chars
  * response        — the full :class:`LLMResponse` including ``raw_message``
  * elapsed_ms      — wall-clock duration of the call (None if timing failed)
  * timestamp       — ISO-8601 UTC timestamp at call site
"""

from __future__ import annotations

import datetime as _dt
import time
from dataclasses import dataclass, field
from typing import Any

from anima.llm.base import LLMAdapter, LLMResponse, Tier


@dataclass
class CapturedLLMCall:
    """One LLM call's full trace.

    ``response`` carries the entire :class:`LLMResponse` so downstream
    consumers (transcript writer, JSON sidecar) can inspect ``.text``,
    ``.usage``, ``.finish_reason``, and ``.raw_message`` (the full provider
    message dict — see :class:`anima.llm.base.LLMResponse` docs for the
    fields that may be populated).
    """
    tier: str
    system_prompt_chars: int
    user_message_preview: str
    response: LLMResponse
    elapsed_ms: int | None = None
    timestamp: str = ""


class CapturingLLMAdapter:
    """Wraps an :class:`LLMAdapter` and records every call.

    The wrapper duck-types as the underlying adapter:
      * exposes ``generate(...)`` with the same signature
      * forwards ALL other attribute access to the inner adapter via
        ``__getattr__`` so call sites that read e.g. ``adapter.retry_cfg``
        or ``adapter.fast_model`` continue to work

    The capture buffer (``self.calls``) is reset at the start of each turn
    by :class:`anima.core.Anima` and snapshotted into the ``TurnTrace`` at
    the end of the turn.
    """

    def __init__(self, inner: LLMAdapter):
        self.inner = inner
        self.calls: list[CapturedLLMCall] = []

    def __getattr__(self, name: str) -> Any:
        # __getattr__ runs only when normal lookup fails, so ``inner``,
        # ``calls``, ``generate``, ``reset`` resolve normally on the
        # wrapper. Everything else falls through to the inner adapter —
        # this is how ``retry_cfg``, ``name``, ``model``, ``fast_model``
        # etc. remain readable through the wrapper without explicit
        # forwarding props.
        return getattr(self.inner, name)

    def generate(
        self,
        *,
        tier: Tier,
        system: str,
        messages: list[dict],
        **kwargs: Any,
    ) -> LLMResponse:
        t0 = time.monotonic()
        resp = self.inner.generate(
            tier=tier, system=system, messages=messages, **kwargs,
        )
        elapsed_ms: int | None
        try:
            elapsed_ms = int((time.monotonic() - t0) * 1000)
        except Exception:  # noqa: BLE001 — clock failures must not break capture
            elapsed_ms = None

        # Last user-message preview. ``messages`` is an OpenAI-style list of
        # ``{"role": ..., "content": str}`` dicts; we only look at the most
        # recent entry because that's what the subsystem actually asked the
        # model on this call. Defensive against non-dict shapes.
        user_preview = ""
        if messages:
            last = messages[-1]
            if isinstance(last, dict):
                content = last.get("content", "")
                if not isinstance(content, str):
                    content = str(content)
            else:
                content = str(last)
            user_preview = content[:200]

        self.calls.append(CapturedLLMCall(
            tier=str(tier),
            system_prompt_chars=len(system) if isinstance(system, str) else 0,
            user_message_preview=user_preview,
            response=resp,
            elapsed_ms=elapsed_ms,
            timestamp=_dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
        ))
        return resp

    def reset(self) -> None:
        """Drop all captured calls. Called at the start of each turn."""
        self.calls = []


__all__ = ["CapturedLLMCall", "CapturingLLMAdapter"]
