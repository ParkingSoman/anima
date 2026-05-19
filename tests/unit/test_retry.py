"""Unit tests for :mod:`anima.llm.retry`.

Covers:
  - retry succeeds on attempt N+1 when ``fail_first_n`` < max_attempts
  - retry exhausts at exactly ``max_attempts`` and re-raises the last exception
  - backoff timing is roughly correct (sleeps approximately match the formula,
    using a monkeypatched ``time.sleep`` to avoid real waits)
  - non-retryable exception types (TypeError) bypass retry entirely
  - HTTP 5xx (status_code attribute) is retried; HTTP 4xx (non-429) is not
"""

from __future__ import annotations

import errno

import pytest

from anima.llm import FakeAdapter, FlakyFakeAdapter, RetryConfig
from anima.llm.retry import _is_retryable, _retry_call


# ---------- _retry_call directly


def test_succeeds_on_attempt_n_plus_one():
    """Fail twice, succeed on third try with max_attempts=3."""
    calls = {"n": 0}

    def fn():
        calls["n"] += 1
        if calls["n"] < 3:
            raise ConnectionError("boom")
        return "ok"

    cfg = RetryConfig(max_attempts=3, base_delay=0.0, jitter=0.0)
    out = _retry_call(fn, cfg, sleep=lambda _d: None)
    assert out == "ok"
    assert calls["n"] == 3


def test_exhausts_at_max_attempts_and_reraises():
    """Always-failing fn raises after exactly max_attempts calls."""
    calls = {"n": 0}

    def fn():
        calls["n"] += 1
        raise ConnectionError("permanent")

    cfg = RetryConfig(max_attempts=3, base_delay=0.0, jitter=0.0)
    with pytest.raises(ConnectionError, match="permanent"):
        _retry_call(fn, cfg, sleep=lambda _d: None)
    assert calls["n"] == 3, "should have tried exactly max_attempts times"


def test_max_attempts_one_disables_retry():
    """RetryConfig(max_attempts=1) means a single attempt, no retry."""
    calls = {"n": 0}

    def fn():
        calls["n"] += 1
        raise ConnectionError("boom")

    with pytest.raises(ConnectionError):
        _retry_call(fn, RetryConfig(max_attempts=1), sleep=lambda _d: None)
    assert calls["n"] == 1


def test_backoff_timing_matches_formula():
    """Sleeps between attempts should follow base * 2^i with jitter band.

    With base_delay=1.0 and jitter=0.3, the three between-attempt sleeps for
    max_attempts=4 are in bands [1.0, 1.3], [2.0, 2.6], [4.0, 5.2]. We force
    jitter to 0 by monkeypatching ``rand`` so the test is deterministic.
    """
    sleeps: list[float] = []

    def fake_sleep(d: float) -> None:
        sleeps.append(d)

    calls = {"n": 0}

    def fn():
        calls["n"] += 1
        raise ConnectionError("boom")

    cfg = RetryConfig(max_attempts=4, base_delay=1.0, jitter=0.3)
    with pytest.raises(ConnectionError):
        _retry_call(fn, cfg, sleep=fake_sleep, rand=lambda: 0.0)
    # 4 attempts → 3 between-attempt sleeps.
    assert sleeps == [1.0, 2.0, 4.0]


def test_backoff_with_max_jitter():
    """With rand() returning 1.0, jitter adds its full band each time."""
    sleeps: list[float] = []
    cfg = RetryConfig(max_attempts=4, base_delay=1.0, jitter=0.3)

    def fn():
        raise ConnectionError()

    with pytest.raises(ConnectionError):
        _retry_call(fn, cfg, sleep=sleeps.append, rand=lambda: 1.0)
    # band = base * 2^i, jitter_band = jitter * 2^i, delay = band + rand * jitter_band.
    # i=0: 1.0 + 1.0 * 0.3 = 1.3
    # i=1: 2.0 + 1.0 * 0.6 = 2.6
    # i=2: 4.0 + 1.0 * 1.2 = 5.2
    assert sleeps == pytest.approx([1.3, 2.6, 5.2], rel=1e-9)


def test_non_retryable_exception_bypasses_retry():
    """TypeError is a programmer error — should not retry."""
    calls = {"n": 0}

    def fn():
        calls["n"] += 1
        raise TypeError("bad arg")

    cfg = RetryConfig(max_attempts=5, base_delay=0.0, jitter=0.0)
    with pytest.raises(TypeError):
        _retry_call(fn, cfg, sleep=lambda _d: None)
    assert calls["n"] == 1, "non-retryable should fire fn() exactly once"


def test_attribute_error_bypasses_retry():
    """AttributeError is also non-retryable."""
    calls = {"n": 0}

    def fn():
        calls["n"] += 1
        raise AttributeError("missing attr")

    with pytest.raises(AttributeError):
        _retry_call(fn, RetryConfig(max_attempts=5, base_delay=0.0),
                    sleep=lambda _d: None)
    assert calls["n"] == 1


# ---------- _is_retryable classification


class _HTTPError(Exception):
    """Plain stand-in for a provider HTTP error with a status_code attribute."""

    def __init__(self, status_code: int, message: str = ""):
        super().__init__(message)
        self.status_code = status_code


def test_http_429_is_retryable():
    assert _is_retryable(_HTTPError(429)) is True


def test_http_5xx_is_retryable():
    assert _is_retryable(_HTTPError(500)) is True
    assert _is_retryable(_HTTPError(502)) is True
    assert _is_retryable(_HTTPError(503)) is True


def test_http_4xx_non_429_is_not_retryable():
    assert _is_retryable(_HTTPError(401)) is False
    assert _is_retryable(_HTTPError(400)) is False
    assert _is_retryable(_HTTPError(404)) is False


def test_connection_and_timeout_errors_retryable():
    assert _is_retryable(ConnectionError("drop")) is True
    assert _is_retryable(TimeoutError("slow")) is True


def test_transient_oserrno_retryable():
    exc = OSError(errno.EPIPE, "broken pipe")
    assert _is_retryable(exc) is True
    exc = OSError(errno.ECONNRESET, "reset")
    assert _is_retryable(exc) is True


def test_class_name_hints_retryable():
    """Provider libraries surface RateLimit by class name; we match on that
    without importing the library."""

    class RateLimitError(Exception):  # mimics anthropic.RateLimitError shape
        pass

    assert _is_retryable(RateLimitError("slow down")) is True


def test_type_error_not_retryable_even_with_status_code():
    """The hard non-retryable list takes precedence over status_code hints."""
    exc = TypeError("bad arg")
    # Forcibly attach a status_code attribute that would normally trigger retry.
    exc.status_code = 503  # type: ignore[attr-defined]
    assert _is_retryable(exc) is False


# ---------- through the FlakyFakeAdapter (end-to-end)


def test_flaky_fake_adapter_recovers_within_max_attempts():
    """N=2 failures + 3 attempts → succeed on third try."""
    adapter = FlakyFakeAdapter(
        fail_first_n=2,
        retry_cfg=RetryConfig(max_attempts=3, base_delay=0.0, jitter=0.0),
    )
    # Use a tiny direct call that hits the default fallback branch.
    resp = adapter.generate(tier="fast", system="anything", messages=[
        {"role": "user", "content": "ping"}
    ])
    assert resp.text == "ok"
    assert adapter._failures_emitted == 2


def test_flaky_fake_adapter_exhausts_attempts():
    """fail_first_n > max_attempts → final ConnectionError bubbles out."""
    adapter = FlakyFakeAdapter(
        fail_first_n=5,
        retry_cfg=RetryConfig(max_attempts=3, base_delay=0.0, jitter=0.0),
    )
    with pytest.raises(ConnectionError):
        adapter.generate(tier="fast", system="anything", messages=[
            {"role": "user", "content": "ping"}
        ])


def test_fake_adapter_does_not_retry_by_default():
    """FakeAdapter's default retry_cfg is max_attempts=1 — no retry."""
    adapter = FakeAdapter()
    assert adapter.retry_cfg.max_attempts == 1


def test_per_call_retry_cfg_override():
    """generate(retry_cfg=...) overrides the adapter's default."""
    adapter = FlakyFakeAdapter(
        fail_first_n=2,
        retry_cfg=RetryConfig(max_attempts=1),  # adapter default would FAIL
    )
    # Per-call override gives us 3 attempts → success.
    resp = adapter.generate(
        tier="fast", system="anything", messages=[{"role": "user", "content": "ping"}],
        retry_cfg=RetryConfig(max_attempts=3, base_delay=0.0, jitter=0.0),
    )
    assert resp.text == "ok"
