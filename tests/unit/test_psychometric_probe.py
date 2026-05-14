"""Tests for the Item-B refactor of `verification.probes.psychometric`.

The probe administers BFI items as natural conversational questions. The
subject's user message NEVER contains a meta-format instruction (no JSON,
no "answer with only an integer"). A separate score-extractor LLM call
converts natural-language replies into 1–5 integers.

These tests cover:
  - The regex/JSON fast path short-circuits without an LLM call when the
    reply is already a clean score.
  - The LLM extractor handles hedged natural-language replies.
  - One retry of the extraction with a more permissive system prompt is
    performed before giving up.
  - On hard failure both extractor calls fail; the per-item record is
    marked "unparsed" and the effective score is the neutral midpoint 3.
  - The subject's prompt contains the conversational 1-to-5 scaffolding
    but no JSON or "exact format" instruction.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from anima.config.schema import load_config
from anima.llm.base import LLMResponse
from anima.llm.fake_adapter import FakeAdapter
from verification.baseline import BaselineAnima
from verification.probes import psychometric as psy
from verification.probes.psychometric import _extract_score


_PRESETS_DIR = Path(__file__).resolve().parents[2] / "anima" / "config" / "presets"
_ELENA = _PRESETS_DIR / "elena.yaml"


# ---------------------------------------------------------------------------
# Test double
# ---------------------------------------------------------------------------


class CountingLLM:
    """Minimal LLM stub: serves a queue of canned text responses in order and
    records each call. Used instead of `FakeAdapter` because the latter routes
    by system-prompt fingerprint, which makes it awkward to script per-call
    extractor responses."""

    name = "counting"

    def __init__(self, responses: list[str]):
        self.responses = list(responses)
        self.calls: list[dict] = []

    def generate(self, *, tier, system, messages,
                 max_tokens: int = 1024, temperature: float = 0.7,
                 stop=None) -> LLMResponse:
        self.calls.append({
            "tier": tier, "system": system, "messages": messages,
            "max_tokens": max_tokens, "temperature": temperature,
        })
        if not self.responses:
            raise AssertionError(
                f"CountingLLM exhausted; unexpected call #{len(self.calls)}"
            )
        return LLMResponse(text=self.responses.pop(0), usage={}, raw={})


# ---------------------------------------------------------------------------
# _extract_score — fast paths and LLM paths
# ---------------------------------------------------------------------------


def test_extract_score_json_fast_path_no_llm_call():
    llm = CountingLLM(responses=[])  # any call would AssertionError
    score, status = _extract_score('{"score": 4}', llm)
    assert score == 4
    assert status == "ok"
    assert llm.calls == []


def test_extract_score_bare_digit_fast_path_no_llm_call():
    llm = CountingLLM(responses=[])
    score, status = _extract_score("3", llm)
    assert score == 3
    assert status == "ok"
    assert llm.calls == []


def test_extract_score_bare_digit_with_trailing_punctuation_fast_path():
    llm = CountingLLM(responses=[])
    score, status = _extract_score("3.", llm)
    assert score == 3
    assert status == "ok"
    assert llm.calls == []


def test_extract_score_llm_path_when_no_clean_digit():
    """Hedged reply with no digit anywhere — extractor LLM is invoked."""
    llm = CountingLLM(responses=["4"])
    reply = "That's me, more than I'd care to admit, honestly."
    score, status = _extract_score(reply, llm)
    assert score == 4
    assert status == "ok"
    assert len(llm.calls) == 1
    # Subject's reply passed verbatim, fast tier, deterministic, tight budget.
    call = llm.calls[0]
    assert call["tier"] == "fast"
    assert call["temperature"] == 0.0
    assert call["max_tokens"] == 8
    assert call["messages"] == [{"role": "user", "content": reply}]


def test_extract_score_retry_path_when_first_unparsed():
    """First extractor call returns UNPARSED; the retry call returns the score."""
    llm = CountingLLM(responses=["UNPARSED", "3"])
    reply = "Hard to say — kind of in the middle, I suppose."
    score, status = _extract_score(reply, llm)
    assert score == 3
    assert status == "ok_extractor_retry"
    assert len(llm.calls) == 2
    # Retry uses a different (more permissive) system prompt.
    assert llm.calls[0]["system"] != llm.calls[1]["system"]


def test_extract_score_hard_failure_both_calls_unparsed():
    llm = CountingLLM(responses=["UNPARSED", "UNPARSED"])
    reply = "I'd rather not answer that one."
    score, status = _extract_score(reply, llm)
    assert score is None
    assert status == "unparsed"
    assert len(llm.calls) == 2


# ---------------------------------------------------------------------------
# administer — end-to-end with the new extractor plumbing
# ---------------------------------------------------------------------------


class ScriptedSubject:
    """A minimal subject standing in for Anima/BaselineAnima for unit testing
    `administer`. Exposes the small surface administer relies on: `.cfg`,
    `.respond`, `.llm`."""

    def __init__(self, cfg, replies: list[str], extractor_llm):
        self.cfg = cfg
        self._replies = list(replies)
        self.llm = extractor_llm  # used as the default extractor_llm
        self.calls: list[str] = []

    def respond(self, msg: str):
        self.calls.append(msg)
        if not self._replies:
            return "", None
        return self._replies.pop(0), None


def _make_subject_with_replies(replies: list[str], extractor_llm):
    cfg = load_config(_ELENA)
    return ScriptedSubject(cfg, replies, extractor_llm)


def test_administer_uses_subject_llm_as_default_extractor():
    """Hard-failure reply propagates: parse_status='unparsed', effective=3."""
    n_items = 15
    bad_reply = "I'd rather not answer that one."
    # 2 extractor calls per item (first + retry), both UNPARSED.
    extractor = CountingLLM(responses=["UNPARSED"] * (n_items * 2))
    subject = _make_subject_with_replies([bad_reply] * n_items, extractor)

    res = psy.administer(subject)
    assert len(res.items) == n_items
    for rec in res.items:
        assert rec["parse_status"] == "unparsed"
        assert rec["score_raw"] is None
        # neutral 3 with reverse-key applied where appropriate
        assert rec["score_effective"] == 3
        assert rec["raw_reply"] == bad_reply
    # All trait recovered_raw means should be 3.0 (neutral midpoint).
    for trait, mean in res.recovered_raw.items():
        assert mean == pytest.approx(3.0)


def test_administer_no_format_instruction_in_subject_prompt():
    """The subject's user message must NOT contain any meta-format instruction.

    The 1-to-5 scale itself is conversational scaffolding and may appear; what
    must not appear is anything telling the subject HOW to format its output
    (JSON, "exact format", "answer with only the integer", etc.)."""
    extractor = CountingLLM(responses=["4"] * 100)  # in case any are needed
    subject = _make_subject_with_replies(["4"] * 15, extractor)
    psy.administer(subject)

    assert len(subject.calls) == 15
    for prompt in subject.calls:
        lower = prompt.lower()
        assert "json" not in lower
        assert "exact format" not in lower
        assert "{" not in prompt  # no JSON skeleton leaked
        # The conversational scale phrasing is expected — assert it's present
        # so a future edit doesn't accidentally strip the researcher's framing.
        assert "1 to 5" in prompt
        assert "strongly disagree" in prompt
        assert "strongly agree" in prompt


def test_administer_clean_score_replies_skip_extractor():
    """If every reply is a clean digit, the extractor LLM is never called."""
    extractor = CountingLLM(responses=[])  # any call would raise
    subject = _make_subject_with_replies(["4"] * 15, extractor)
    res = psy.administer(subject)
    assert all(rec["parse_status"] == "ok" for rec in res.items)
    assert extractor.calls == []


def test_administer_explicit_extractor_llm_kwarg_used():
    """Passing extractor_llm= overrides the subject.llm default."""
    subject_llm = CountingLLM(responses=[])  # any call here would raise
    explicit = CountingLLM(responses=["3"] * 30)  # extractor responses
    subject = _make_subject_with_replies(
        ["Hmm, hard to say."] * 15, subject_llm
    )
    psy.administer(subject, extractor_llm=explicit)
    # Subject-attached LLM untouched; explicit extractor took every call.
    assert subject_llm.calls == []
    assert len(explicit.calls) == 15


# ---------------------------------------------------------------------------
# Integration with FakeAdapter (preserves existing battery-test behavior)
# ---------------------------------------------------------------------------


def test_administer_baseline_with_fake_adapter_uses_fast_path():
    """The FakeAdapter's BFI route returns '{"score": 4}', which the regex
    fast path handles WITHOUT an extractor LLM call. This is the smoke-test
    path used by the existing battery orchestration tests; it must keep
    working unchanged."""
    cfg = load_config(_ELENA)
    fake = FakeAdapter()
    subject = BaselineAnima(cfg, llm=fake)
    # Count adapter calls before vs after administer; only the subject's
    # response calls should occur, NOT additional extractor calls.
    before = len(fake.calls)
    res = psy.administer(subject)
    after = len(fake.calls)
    # 15 items × 1 subject call each. No extractor calls because the fast
    # path catches every reply.
    assert after - before == 15
    assert len(res.items) == 15
    assert all(rec["parse_status"] == "ok" for rec in res.items)
    assert all(rec["score_raw"] == 4 for rec in res.items)
