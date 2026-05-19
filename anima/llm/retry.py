"""LLM adapter retry policy — stdlib only.

The user's machine occasionally drops connections, the provider occasionally
returns 5xx / 429, and structured-output paths occasionally see a malformed
JSON we can't recover from in-band. Layered retry is the cheapest insurance
that one such glitch does not crash a turn or a session.

This module is small on purpose: a single dataclass for the policy, and a
single helper that takes a no-arg callable and a policy. Adapters wrap their
provider call site with ``_retry_call(lambda: self._raw(...), self.retry_cfg)``.

Production retry policy (binding):
    Every real adapter (``AnthropicAdapter``, ``OpenAIAdapter``,
    ``OpenRouterAdapter``) instantiates ``RetryConfig()`` by default, which is
    ``max_attempts=3`` — i.e. **the initial attempt plus 2 retries** before
    the call is allowed to raise. ``Anima.respond`` then catches the raised
    exception per subsystem and substitutes a structurally-valid fallback,
    so every subsystem (perception, memory_retrieval, appraisal,
    user_prediction, inner_monologue, response_generator, self_monitor) gets
    at least 2 retries before any fallback fires. The response_generator goes
    further and uses a per-call ``RetryConfig(max_attempts=5)`` (4 retries),
    since its failure is the only one that costs the user a reply.

Asymmetry — the FakeAdapter:
    The :class:`anima.llm.fake_adapter.FakeAdapter` deliberately defaults to
    ``RetryConfig(max_attempts=1)`` (no retry). This is the right default for
    deterministic unit tests — tests that exercise retry paths use
    ``FlakyFakeAdapter`` and pass an explicit ``RetryConfig`` so the retry
    layer participates. If you run the real CLI against ``--provider fake``
    for a smoke test, you'll see the asymmetry: a single transient glitch in
    the canned routing logic falls through immediately. That is intentional;
    do NOT raise the FakeAdapter default without updating the test suites
    that rely on no-retry semantics.

Retry classification (see ``_is_retryable``):
    Retry on:
      - ``ConnectionError``, ``TimeoutError``
      - ``OSError`` with ``errno`` in {EPIPE, ECONNRESET, ETIMEDOUT}
      - any exception whose class name contains "RateLimit" (anthropic /
        openai variants) — checked via ``type(exc).__name__`` so this module
        does not import the provider packages
      - any exception with ``status_code`` attribute where the code is 429
        or in the 5xx range (covers ``anthropic.APIStatusError`` family,
        ``openai.APIError`` family, and ``urllib3.HTTPError`` shapes)

    Do NOT retry on:
      - ``TypeError``, ``AttributeError``, ``ValueError``, ``KeyError``,
        ``NameError`` (programmer errors — retry won't help)
      - any 4xx other than 429 (auth, bad request — retry won't help)

The classifier is conservative: when in doubt, we retry. The bound is
``max_attempts`` so the worst case is a known, finite delay.

Empty-content retry (Fix 1):
    Exception-based retry alone is insufficient. DeepSeek (and any provider)
    can return a successful HTTP response whose ``LLMResponse.text`` is the
    empty string or whitespace-only. Treating that as success silently
    half-blinds the architecture (subsystems fall back to defaults; the
    response generator runs on biography alone, which leaks heavily-defended
    content).

    The retry layer therefore also supports a per-call ``is_valid``
    predicate. After a successful ``fn()`` call, if the predicate returns
    False, the layer raises an internal sentinel exception (caught by the
    very same loop) and retries. When the retry budget is exhausted by
    empty responses, a public :class:`EmptyResponseAfterRetries` is raised
    so subsystem-level handlers can distinguish "model glitched and
    produced nothing" from "model produced something we couldn't parse".

    Asymmetry: by default, ``RetryConfig.retry_on_empty`` is True and the
    default predicate ``lambda r: bool(r.text and r.text.strip())`` fires.
    Passing ``is_valid`` explicitly overrides the default. Passing
    ``retry_on_empty=False`` disables the check entirely (used by
    memory_retrieval, whose call site may legitimately produce an empty
    structured output that the JSON parser is happy to interpret as
    "no items").

    The empty-retry budget is NOT compounded with the exception-retry
    budget — both count against the single ``max_attempts``. So with
    ``max_attempts=3`` and one timeout + one empty + one success, the
    third attempt returns the value. With three empties in a row, the
    call raises ``EmptyResponseAfterRetries``.
"""

from __future__ import annotations

import errno as _errno
import random
import time
from dataclasses import dataclass
from typing import Any, Callable, TypeVar

T = TypeVar("T")


# OSError errno values that suggest a transient network condition. We use
# the numeric errno because errno names differ across platforms.
_TRANSIENT_ERRNO = {
    _errno.EPIPE,
    _errno.ECONNRESET,
    _errno.ETIMEDOUT,
    # ECONNABORTED is on the same axis on macOS/Linux; including it is harmless.
    getattr(_errno, "ECONNABORTED", -1),
}


@dataclass
class RetryConfig:
    """Adapter-level retry policy.

    Defaults: 3 attempts, exponential backoff with jitter. Sleeps between
    attempt N and N+1 are ``base_delay * 2**N + random(0, jitter * 2**N)``,
    so with defaults: ~1s, ~2s, ~4s (plus up to ~0.3, ~0.6, ~1.2 jitter).

    Tests pass ``RetryConfig(max_attempts=1)`` to disable retry entirely.

    Parameters
    ----------
    max_attempts:
        Total attempts (initial + retries). Empty-content retries count
        against the same budget as exception retries.
    base_delay, jitter:
        Backoff timing knobs. Tests typically set both to 0 to skip sleeps.
    retry_on_empty:
        When True (default), a successful call whose result fails the
        default-or-supplied ``is_valid`` predicate is treated as a
        retryable failure. When False, empty responses are never retried;
        whatever the provider returned passes through unchanged. Use False
        for subsystems where an empty response is semantically valid
        (e.g. memory retrieval producing an empty items list).
    """

    max_attempts: int = 3
    base_delay: float = 1.0
    jitter: float = 0.3
    retry_on_empty: bool = True


# Substrings of exception class names that we always treat as retryable. We
# match by name rather than by isinstance so this module does not import
# anthropic / openai (callers may install only one of them).
_RETRYABLE_CLASS_HINTS = (
    "RateLimit",
    "Timeout",
    "ServiceUnavailable",
    "InternalServerError",
    "BadGateway",
    "GatewayTimeout",
)

# Class names that should NEVER retry even if they happen to expose a
# status_code attribute or share a name fragment.
_NON_RETRYABLE_TYPES = (
    TypeError,
    AttributeError,
    ValueError,
    KeyError,
    NameError,
    NotImplementedError,
)


class EmptyResponseAfterRetries(Exception):
    """The LLM returned empty/whitespace-only content on every retry attempt.

    Raised by :func:`_retry_call` when ``retry_on_empty=True`` (or an
    explicit ``is_valid`` is passed) and every attempt's result fails the
    validity predicate. Distinguishes "provider glitched and returned
    nothing" from generic transport errors so subsystem-level handlers in
    :mod:`anima.core` can attach a clearly-labeled SubsystemError to the
    turn trace.

    Exposes ``attempts`` for transcript bookkeeping. The provider's last
    (empty) result is intentionally NOT carried because it has no
    information content — by definition it was empty.
    """

    def __init__(self, attempts: int, last_finish_reason: str | None = None):
        self.attempts = int(attempts)
        # The provider's last-seen finish_reason — propagated up so error
        # messages, transcripts, and operator-facing CLI prints can show
        # *why* the model kept returning empty. ``length`` is the common
        # one for DeepSeek-flash on long persona prompts; surfacing it lets
        # the operator immediately see "raise max_tokens / switch model"
        # rather than guessing.
        self.last_finish_reason = last_finish_reason
        if last_finish_reason is not None:
            msg = (
                f"LLM returned empty/whitespace-only text on all "
                f"{int(attempts)} retry attempts "
                f"(last finish_reason={last_finish_reason!r})"
            )
        else:
            msg = (
                f"LLM returned empty/whitespace-only text on all "
                f"{int(attempts)} retry attempts"
            )
        super().__init__(msg)


# Internal sentinel — never escapes the module. Used to bounce control back
# to the retry loop when a successful call returns an empty result. Kept
# distinct from :class:`EmptyResponseAfterRetries` so the public exception
# only surfaces when the retry budget is fully exhausted.
class _EmptyResponseRetry(Exception):
    pass


_NO_TEXT_ATTR = object()


# OpenAI/OpenRouter and Anthropic finish_reason values that mean "the
# model emitted an end-of-turn deliberately". When .text is empty AND
# finish_reason is in this set, we trust the model: it chose to be
# silent, and a retry would just spam the provider with no upside.
#
# Why include None: many code paths (older adapters, synthetic test
# fixtures, providers that don't expose the field) leave finish_reason
# unset. Treating None as "non-stop" would retry every empty response
# from those paths and re-introduce the iris-v1 bug we're fixing. The
# safer default is "unknown → assume genuine"; explicit non-stop reasons
# (length / content_filter / error / etc.) are the only triggers.
_STOP_FINISH_REASONS = frozenset({
    "stop",            # OpenAI / OpenRouter
    "end_turn",        # Anthropic
    "stop_sequence",   # OpenAI alt / Anthropic alt
    None,              # unknown / unset → treat as genuine
})


def _default_is_valid(result: Any) -> bool:
    """Default validity predicate for LLM responses.

    Returns True when the result represents a legitimate model output
    that the retry layer should accept (and the caller can consume).

    Decision matrix:
        * No ``text`` attribute → pass through (this predicate is for
          LLMResponse-shaped outputs; generic callables in unit tests
          shouldn't trip the empty-content check).
        * ``text`` is non-empty after strip → valid, regardless of
          finish_reason.
        * ``text`` is empty/whitespace AND finish_reason is in
          ``_STOP_FINISH_REASONS`` → valid (model genuinely chose
          silence; do NOT retry).
        * ``text`` is empty/whitespace AND finish_reason is any
          explicit non-stop value (``length``, ``content_filter``,
          ``error``, ``tool_calls``, etc.) → invalid (cutoff / refusal
          / error; retry).
        * ``text`` is non-string (None, bytes, etc.) → invalid; the
          retry layer or caller will see it as a malformed result.

    The asymmetry on None for finish_reason is deliberate: many
    LLMResponse construction sites in the codebase predate the field
    and don't populate it. We do NOT want those paths to start retrying
    silence; only EXPLICIT non-stop reasons trigger retry.
    """
    text = getattr(result, "text", _NO_TEXT_ATTR)
    if text is _NO_TEXT_ATTR:
        return True
    if not isinstance(text, str):
        # Defensive: if some provider returns text=None or a bytes blob,
        # treat anything non-string as invalid.
        return False
    if text.strip():
        return True
    # text is empty/whitespace — decide based on finish_reason.
    finish_reason = getattr(result, "finish_reason", None)
    return finish_reason in _STOP_FINISH_REASONS


def _is_retryable(exc: BaseException) -> bool:
    """Decide whether an exception should trigger a retry.

    Conservative: if a network-ish exception type slips through, we retry it.
    The hard ``_NON_RETRYABLE_TYPES`` list takes precedence over everything.
    """
    if isinstance(exc, _NON_RETRYABLE_TYPES):
        return False

    # OSError with transient errno → retry. Includes ConnectionError /
    # TimeoutError which inherit from OSError.
    if isinstance(exc, (ConnectionError, TimeoutError)):
        return True
    if isinstance(exc, OSError):
        if exc.errno in _TRANSIENT_ERRNO:
            return True

    # HTTP-style status_code attribute. 429 and 5xx are retryable; other
    # 4xx are not (auth, bad request, etc.).
    status_code = getattr(exc, "status_code", None)
    if isinstance(status_code, int):
        if status_code == 429:
            return True
        if 500 <= status_code < 600:
            return True
        if 400 <= status_code < 500:
            return False

    # Provider-library class-name hints (anthropic.RateLimitError,
    # openai.RateLimitError, etc.).
    name = type(exc).__name__
    for hint in _RETRYABLE_CLASS_HINTS:
        if hint in name:
            return True

    return False


def _retry_call(
    fn: Callable[[], T],
    cfg: RetryConfig,
    *,
    sleep: Callable[[float], None] = time.sleep,
    rand: Callable[[], float] = random.random,
    is_valid: Callable[[Any], bool] | None = None,
) -> T:
    """Call ``fn()``, retrying on transient failures per ``cfg``.

    ``sleep`` and ``rand`` are injected so tests can verify the backoff
    timing without actually sleeping. ``rand`` returns a float in [0, 1)
    (matches ``random.random``); we multiply by the per-attempt jitter band.

    ``is_valid`` is an optional predicate run on each successful result.
    Resolution order:
        * explicit ``is_valid`` always wins (caller takes responsibility)
        * else if ``cfg.retry_on_empty`` is True, the default predicate
          ``_default_is_valid`` is used (text must be non-empty,
          non-whitespace)
        * else (``retry_on_empty=False`` and no explicit ``is_valid``) the
          validity check is skipped entirely

    Behavior:
        * exception → retry per ``_is_retryable`` until budget exhausted
        * empty response → raise sentinel, retry with same budget
        * exhausted budget with all-empty → raise
          :class:`EmptyResponseAfterRetries`
        * exhausted budget with mixed/exception → re-raise the last
          underlying exception

    The total attempt count is ``max_attempts``; empty + exception
    failures share that budget (no compounding).
    """
    # Resolve the validity predicate. Caller-supplied always wins; otherwise
    # honor the config's retry_on_empty toggle.
    #
    # Asymmetry: when ``max_attempts == 1`` (e.g. FakeAdapter's no-retry
    # default), we intentionally do NOT run the empty-content check, because
    # there's no retry to bounce to anyway — and triggering the empty path
    # would convert a one-shot empty response into a noisy
    # EmptyResponseAfterRetries that callers running deterministic empty
    # fixtures (e.g. silence-detection tests using FakeAdapter(text="")) do
    # not want. The retry layer is only useful when a budget exists.
    if is_valid is None:
        if cfg.retry_on_empty and cfg.max_attempts > 1:
            effective_is_valid: Callable[[Any], bool] | None = _default_is_valid
        else:
            effective_is_valid = None
    else:
        effective_is_valid = is_valid

    attempts = max(1, int(cfg.max_attempts))
    last_exc: BaseException | None = None
    empty_attempts = 0
    # Tracks the most recent finish_reason we observed on an empty
    # result, so EmptyResponseAfterRetries can surface it (helpful for
    # the operator: "all 5 attempts ended with finish_reason=length"
    # immediately suggests "max_tokens too low" instead of a guessing game).
    last_finish_reason: str | None = None
    for i in range(attempts):
        try:
            result = fn()
            # Success path — run the validity check before returning.
            if effective_is_valid is not None and not effective_is_valid(result):
                # Bounce to the retry loop via the internal sentinel.
                empty_attempts += 1
                # Capture finish_reason of this (invalid) empty response
                # before the sentinel raises and we lose the local.
                last_finish_reason = getattr(result, "finish_reason", None)
                raise _EmptyResponseRetry()
            return result
        except _EmptyResponseRetry:
            # Empty-response path. If this was the last attempt, escalate
            # to the public exception. Otherwise fall through to backoff.
            if i == attempts - 1:
                raise EmptyResponseAfterRetries(
                    attempts=attempts,
                    last_finish_reason=last_finish_reason,
                ) from None
            # Backoff before next attempt (shared formula with the
            # exception path below).
            band = cfg.base_delay * (2 ** i)
            jitter_band = cfg.jitter * (2 ** i)
            delay = band + rand() * jitter_band
            sleep(delay)
            continue
        except BaseException as exc:  # noqa: BLE001 — classified below
            last_exc = exc
            if not _is_retryable(exc):
                raise
            if i == attempts - 1:
                # Last attempt failed; bubble out.
                raise
            # Backoff before next attempt. Doubling band each round so a
            # truly-flaky upstream gets exponential breathing room.
            band = cfg.base_delay * (2 ** i)
            jitter_band = cfg.jitter * (2 ** i)
            delay = band + rand() * jitter_band
            sleep(delay)
    # Unreachable — the loop either returns or raises. The assertion is here
    # to satisfy type checkers and to make a logic bug loud if one ever lands.
    raise RuntimeError("retry loop exited without return or raise")  # pragma: no cover
