"""Unit tests for Fix 1 — empty-content retry in :mod:`anima.llm.retry`.

Covers:
  - FlakyFakeAdapter-style helper that returns empty text N times then
    valid text: retry should succeed on attempt N+1.
  - Always-empty: retry exhausts and raises EmptyResponseAfterRetries.
  - Mixed (one exception, one empty, one success): all share the same
    max_attempts budget.
  - retry_on_empty=False disables the check.
  - Explicit is_valid predicate overrides the default.
  - End-to-end: forcing 3 empty inner_monologue calls inside
    Anima.respond() lands the EmptyResponseAfterRetries record in
    trace.subsystem_errors with the right error_type and message.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from anima.config import load_config
from anima.core import Anima
from anima.llm import (
    EmptyResponseAfterRetries,
    EmptyTextFakeAdapter,
    FakeAdapter,
    FlakyFakeAdapter,
    RetryConfig,
)
from anima.llm.base import LLMResponse
from anima.llm.retry import _retry_call


REPO_ROOT = Path(__file__).resolve().parents[2]
PRESET = REPO_ROOT / "anima" / "config" / "presets" / "marcus.yaml"


# ---------- _retry_call directly: empty-content semantics


def test_empty_then_valid_succeeds_within_budget():
    """N=2 empty responses, then a valid one, with max_attempts=3 → success."""
    calls = {"n": 0}

    def fn():
        calls["n"] += 1
        if calls["n"] < 3:
            return LLMResponse(text="", usage={}, raw={})
        return LLMResponse(text="finally", usage={}, raw={})

    cfg = RetryConfig(max_attempts=3, base_delay=0.0, jitter=0.0)
    out = _retry_call(fn, cfg, sleep=lambda _d: None)
    assert out.text == "finally"
    assert calls["n"] == 3


def test_always_empty_exhausts_and_raises_empty_response_after_retries():
    """fn() returns empty on every call → after max_attempts, raises."""
    calls = {"n": 0}

    def fn():
        calls["n"] += 1
        return LLMResponse(text="", usage={}, raw={})

    cfg = RetryConfig(max_attempts=3, base_delay=0.0, jitter=0.0)
    with pytest.raises(EmptyResponseAfterRetries) as exc_info:
        _retry_call(fn, cfg, sleep=lambda _d: None)
    assert exc_info.value.attempts == 3
    assert "empty" in str(exc_info.value).lower()
    assert calls["n"] == 3, "should have called fn() exactly max_attempts times"


def test_whitespace_only_is_treated_as_empty():
    """Tabs/newlines/spaces — all forms of whitespace-only — should retry."""
    cfg = RetryConfig(max_attempts=2, base_delay=0.0, jitter=0.0)
    for variant in ("   ", "\n\n", "\t", " \n \t "):
        calls = {"n": 0}

        def fn(v=variant):
            calls["n"] += 1
            return LLMResponse(text=v, usage={}, raw={})

        with pytest.raises(EmptyResponseAfterRetries):
            _retry_call(fn, cfg, sleep=lambda _d: None)
        assert calls["n"] == 2


def test_mixed_exception_and_empty_share_budget():
    """1 exception + 1 empty + 1 success with max_attempts=3 → succeeds.

    The empty-retry budget is NOT compounded with exception retry — they
    share the same max_attempts budget.
    """
    calls = {"n": 0}

    def fn():
        calls["n"] += 1
        if calls["n"] == 1:
            raise ConnectionError("simulated drop")
        if calls["n"] == 2:
            return LLMResponse(text="", usage={}, raw={})
        return LLMResponse(text="hello", usage={}, raw={})

    cfg = RetryConfig(max_attempts=3, base_delay=0.0, jitter=0.0)
    out = _retry_call(fn, cfg, sleep=lambda _d: None)
    assert out.text == "hello"
    assert calls["n"] == 3


def test_mixed_two_exceptions_then_empty_at_budget_end_raises_empty():
    """2 exceptions + 1 empty with max_attempts=3 → all budget used; the
    last attempt was empty, so we should see EmptyResponseAfterRetries."""
    calls = {"n": 0}

    def fn():
        calls["n"] += 1
        if calls["n"] < 3:
            raise ConnectionError("drop")
        return LLMResponse(text="", usage={}, raw={})

    cfg = RetryConfig(max_attempts=3, base_delay=0.0, jitter=0.0)
    with pytest.raises(EmptyResponseAfterRetries):
        _retry_call(fn, cfg, sleep=lambda _d: None)
    assert calls["n"] == 3


def test_retry_on_empty_false_disables_check():
    """retry_on_empty=False → empty text comes through as a normal return."""
    cfg = RetryConfig(max_attempts=3, base_delay=0.0, jitter=0.0,
                      retry_on_empty=False)
    out = _retry_call(
        lambda: LLMResponse(text="", usage={}, raw={}),
        cfg,
        sleep=lambda _d: None,
    )
    assert out.text == ""


def test_explicit_is_valid_overrides_default():
    """Passing is_valid=lambda r: ... lets callers customize the check.

    Here we make every response 'valid' regardless of text — so even empty
    text is accepted without retry.
    """
    cfg = RetryConfig(max_attempts=3, base_delay=0.0, jitter=0.0)
    out = _retry_call(
        lambda: LLMResponse(text="", usage={}, raw={}),
        cfg,
        sleep=lambda _d: None,
        is_valid=lambda _r: True,
    )
    assert out.text == ""


def test_explicit_is_valid_can_be_stricter_than_default():
    """A caller can demand more than non-empty text — e.g. that the text
    parses to a non-trivial JSON object."""
    import json

    cfg = RetryConfig(max_attempts=2, base_delay=0.0, jitter=0.0)

    def stricter(r):
        try:
            obj = json.loads(r.text)
            return isinstance(obj, dict) and bool(obj)
        except Exception:
            return False

    # "{}" passes default is_valid (text is non-empty) but fails stricter.
    with pytest.raises(EmptyResponseAfterRetries):
        _retry_call(
            lambda: LLMResponse(text="{}", usage={}, raw={}),
            cfg,
            sleep=lambda _d: None,
            is_valid=stricter,
        )


def test_max_attempts_one_skips_empty_check_entirely():
    """FakeAdapter ships with max_attempts=1 by default and tests that wire
    deterministic empty fixtures expect that to come through. We honor
    that asymmetry: max_attempts=1 → no empty-content retry."""
    cfg = RetryConfig(max_attempts=1)
    out = _retry_call(
        lambda: LLMResponse(text="", usage={}, raw={}),
        cfg,
        sleep=lambda _d: None,
    )
    assert out.text == ""


# ---------- through EmptyTextFakeAdapter (end-to-end at the adapter layer)


def test_empty_text_fake_adapter_retries_to_success():
    """EmptyTextFakeAdapter returns empty for N calls, then canned content."""
    adapter = EmptyTextFakeAdapter(
        empty_first_n=2,
        retry_cfg=RetryConfig(max_attempts=3, base_delay=0.0, jitter=0.0),
        monologue_text="real monologue at last",
    )
    resp = adapter.generate(
        tier="strong",
        system="INNER MONOLOGUE subsystem",
        messages=[{"role": "user", "content": "x"}],
    )
    assert resp.text == "real monologue at last"
    assert adapter._empties_emitted == 2


def test_empty_text_fake_adapter_exhausts_budget():
    """EmptyTextFakeAdapter with empty_first_n >= max_attempts → raises."""
    adapter = EmptyTextFakeAdapter(
        empty_first_n=10,
        retry_cfg=RetryConfig(max_attempts=3, base_delay=0.0, jitter=0.0),
    )
    with pytest.raises(EmptyResponseAfterRetries):
        adapter.generate(
            tier="strong",
            system="INNER MONOLOGUE subsystem",
            messages=[{"role": "user", "content": "x"}],
        )


def test_fake_adapter_does_not_retry_empty_by_default():
    """FakeAdapter default config (max_attempts=1) does not retry empty."""
    adapter = FakeAdapter(monologue_text="")
    # Direct call via the same path the monologue subsystem uses.
    resp = adapter.generate(
        tier="strong",
        system="INNER MONOLOGUE subsystem",
        messages=[{"role": "user", "content": "x"}],
    )
    assert resp.text == ""


# ---------- end-to-end: forced empty subsystem call lands a tagged
# EmptyResponseAfterRetries record in Anima.respond()'s subsystem_errors


def _build_anima_with_empty_monologue() -> Anima:
    """Build an Anima whose inner_monologue LLM call returns empty 3 times.

    Strategy: swap the adapter for an EmptyTextFakeAdapter wired with
    ``empty_first_n=100`` so even the heaviest retry budget exhausts; pass
    ``retry_cfg=RetryConfig(max_attempts=3)`` so the inner_monologue's
    default adapter retry runs 3 attempts. The monologue subsystem doesn't
    pass a per-call retry override, so it inherits the adapter's default.
    """
    adapter = EmptyTextFakeAdapter(
        empty_first_n=100,  # effectively always-empty
        retry_cfg=RetryConfig(max_attempts=3, base_delay=0.0, jitter=0.0),
    )
    return Anima(load_config(PRESET), llm=adapter)


def test_anima_respond_records_empty_response_after_retries_for_inner_monologue():
    """End-to-end: a subsystem whose LLM returns 3 empties lands an
    EmptyResponseAfterRetries entry in trace.subsystem_errors."""
    anima = _build_anima_with_empty_monologue()
    # The response_generator uses a max_attempts=5 override; since this
    # adapter always returns empty for ALL subsystem calls (perception,
    # appraisal, monologue, response_generator), response_generator will
    # also exhaust. So Anima.respond() will raise ResponseGenerationFailed.
    # We collect the partial trace via anima.traces[-1] which is appended
    # before the raise.
    from anima.subsystems.errors import ResponseGenerationFailed

    with pytest.raises(ResponseGenerationFailed):
        anima.respond("hi")
    partial = anima.traces[-1]
    # The trace should carry an EmptyResponseAfterRetries error for at
    # least one subsystem.
    err_types = {e["error_type"] for e in partial.subsystem_errors}
    assert "EmptyResponseAfterRetries" in err_types
    # The message should match the canonical wording.
    empty_errs = [e for e in partial.subsystem_errors
                  if e["error_type"] == "EmptyResponseAfterRetries"]
    assert empty_errs
    for e in empty_errs:
        assert "empty" in e["message"].lower()
        # attempts should be the budget used (3 for normal subsystems,
        # 5 for response_generator).
        assert e["attempts"] in (3, 5), (
            f"unexpected attempts on {e['subsystem']}: {e['attempts']}"
        )


def test_anima_respond_inner_monologue_only_empty_falls_back_cleanly(monkeypatch):
    """Isolate the inner_monologue subsystem: only IT returns empty (3x);
    every other subsystem is the normal FakeAdapter. The turn should
    succeed (response_generator runs normally), and the trace should
    record exactly one EmptyResponseAfterRetries entry tagged
    ``inner_monologue``.
    """
    from anima.llm.fake_adapter import FakeAdapter
    from anima.llm.base import LLMResponse

    adapter = FakeAdapter()
    anima = Anima(load_config(PRESET), llm=adapter)

    # Patch the monologue subsystem's .run to invoke the adapter through a
    # wrapper that ALWAYS returns empty, with max_attempts=3 retries. We
    # do this by replacing the subsystem's llm with a dedicated empty
    # adapter just for that one call site.
    empty_adapter = EmptyTextFakeAdapter(
        empty_first_n=100,
        retry_cfg=RetryConfig(max_attempts=3, base_delay=0.0, jitter=0.0),
    )
    anima._monologue.llm = empty_adapter

    reply, trace = anima.respond("hi")
    # Reply still produced because every other subsystem worked.
    assert isinstance(reply, str) and reply
    err_types_by_sub = {
        e["subsystem"]: e["error_type"] for e in trace.subsystem_errors
    }
    assert err_types_by_sub.get("inner_monologue") == "EmptyResponseAfterRetries"
    # The monologue text should be the structurally-valid fallback (empty).
    assert trace.monologue == ""
