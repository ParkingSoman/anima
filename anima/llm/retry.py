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
    """

    max_attempts: int = 3
    base_delay: float = 1.0
    jitter: float = 0.3


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
) -> T:
    """Call ``fn()``, retrying on transient failures per ``cfg``.

    ``sleep`` and ``rand`` are injected so tests can verify the backoff
    timing without actually sleeping. ``rand`` returns a float in [0, 1)
    (matches ``random.random``); we multiply by the per-attempt jitter band.

    Raises the last exception unchanged when retries are exhausted.
    """
    attempts = max(1, int(cfg.max_attempts))
    last_exc: BaseException | None = None
    for i in range(attempts):
        try:
            return fn()
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
