"""Subsystem error records and the one fatal exception.

A turn that hits an LLM glitch should produce a response anyway — the
fallback values per subsystem keep the turn structurally valid even when
upstream content is missing. The only subsystem whose failure is fatal to
the turn is the response generator: it produces the externally-visible
reply, and there is no sensible fallback for "I have nothing to say".
"""

from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass, field
from typing import Any


def _iso_now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")


@dataclass
class SubsystemError:
    """One subsystem's LLM call failed after all retries.

    Attached to :class:`anima.core.TurnTrace.subsystem_errors`. Surfaced in
    the per-turn transcript (markdown warning block + JSON ``errors``
    entry) so the operator can see WHICH subsystem glitched on a given turn.
    """

    subsystem: str
    error_type: str
    message: str
    attempts: int
    timestamp: str = field(default_factory=_iso_now)
    # Investigation: the full provider message dict from the LAST failed
    # attempt. Only populated when the underlying exception was
    # :class:`anima.llm.retry.EmptyResponseAfterRetries` AND the adapter
    # captured a raw_message — i.e. .content arrived empty but the
    # provider may have produced reasoning_content / tool_calls / etc.
    # Stays None for ordinary exception failures (TimeoutError,
    # ConnectionError, programmer-error AttributeError, etc.) because
    # those don't have a successful response to inspect.
    raw_message: dict | None = None

    def to_jsonable(self) -> dict[str, Any]:
        return {
            "subsystem": self.subsystem,
            "error_type": self.error_type,
            "message": self.message,
            "attempts": self.attempts,
            "timestamp": self.timestamp,
            "raw_message": self.raw_message,
        }


class ResponseGenerationFailed(Exception):
    """Response generator failed after all retries — turn cannot produce a reply.

    The turn-level handler in :meth:`anima.core.Anima.respond` catches this
    AFTER appending a partial :class:`anima.core.TurnTrace` (with the failure
    captured in ``subsystem_errors``), so the transcript records the failed
    turn even though no reply was sent. The session-level handler in
    ``cmd_chat`` then prints a clear error, preserves the user's message for
    ``/retry``, and keeps the REPL alive.
    """

    def __init__(self, *, subsystem: str = "response_generator",
                 attempts: int = 0, last_error: BaseException | None = None):
        self.subsystem = subsystem
        self.attempts = attempts
        self.last_error = last_error
        err_name = type(last_error).__name__ if last_error is not None else "unknown"
        err_msg = str(last_error) if last_error is not None else ""
        super().__init__(
            f"{subsystem} failed after {attempts} attempts "
            f"({err_name}: {err_msg})"
        )
