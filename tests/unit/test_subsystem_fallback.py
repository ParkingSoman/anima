"""Unit tests for subsystem-level retry + fallback in Anima.respond().

Strategy:
  - Build a real Anima with the FakeAdapter (so the turn loop runs cleanly).
  - Monkeypatch a single subsystem's ``.run()`` (or ``.predict()``) to raise.
  - Verify ``respond()`` does NOT raise; the trace records the failure; the
    fallback value was used.

For the response_generator case (the only fatal one):
  - Patch the response generator to always fail.
  - Verify ``ResponseGenerationFailed`` is raised.
  - Verify a partial TurnTrace was still appended to ``anima.traces``.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from anima.config import load_config
from anima.core import Anima
from anima.llm import make_adapter
from anima.subsystems.errors import ResponseGenerationFailed


REPO_ROOT = Path(__file__).resolve().parents[2]
PRESET = REPO_ROOT / "anima" / "config" / "presets" / "marcus.yaml"


def _build_anima() -> Anima:
    cfg = load_config(PRESET)
    return Anima(cfg, llm=make_adapter("fake"))


# ---------- per-subsystem fallbacks


def test_perception_failure_falls_back_and_trace_records_error(monkeypatch):
    anima = _build_anima()

    def _boom(**kwargs):
        raise ConnectionError("simulated perception drop")

    monkeypatch.setattr(anima._perception, "run", _boom)

    reply, trace = anima.respond("hi")
    # Reply still produced via fallback chain.
    assert isinstance(reply, str) and reply
    # Error recorded.
    subs = [e["subsystem"] for e in trace.subsystem_errors]
    assert "perception" in subs
    # Fallback structure: perception used user_msg as literal content.
    assert trace.perception["perceived_intent"] == "unknown"
    assert trace.perception["literal_content"] == "hi"


def test_memory_retrieval_failure_falls_back_to_empty_list(monkeypatch):
    anima = _build_anima()

    def _boom(**kwargs):
        raise ConnectionError("simulated retrieval drop")

    monkeypatch.setattr(anima._memory, "run", _boom)

    reply, trace = anima.respond("hi")
    assert reply
    subs = [e["subsystem"] for e in trace.subsystem_errors]
    assert "memory_retrieval" in subs
    assert trace.retrieved == []


def test_appraisal_failure_falls_back_to_neutral(monkeypatch):
    anima = _build_anima()

    def _boom(**kwargs):
        raise ConnectionError("simulated appraisal drop")

    monkeypatch.setattr(anima._appraisal, "run", _boom)

    reply, trace = anima.respond("hi")
    assert reply
    subs = [e["subsystem"] for e in trace.subsystem_errors]
    assert "appraisal" in subs
    # Neutral fallback structure.
    assert trace.appraisal["primary_emotion"] == "neutral"
    assert trace.appraisal["appraisal_scene_tag"] == "unclassified"


def test_user_prediction_failure_falls_back_to_unknown(monkeypatch):
    anima = _build_anima()

    def _boom(**kwargs):
        raise ConnectionError("simulated prediction drop")

    monkeypatch.setattr(anima._user_prediction, "predict", _boom)

    reply, trace = anima.respond("hi")
    assert reply
    subs = [e["subsystem"] for e in trace.subsystem_errors]
    assert "user_prediction" in subs
    assert trace.prediction["next_intent_label"] == "unknown"
    assert trace.prediction["confidence"] == 0.0


def test_inner_monologue_failure_falls_back_to_empty(monkeypatch):
    anima = _build_anima()

    def _boom(**kwargs):
        raise ConnectionError("simulated monologue drop")

    monkeypatch.setattr(anima._monologue, "run", _boom)

    reply, trace = anima.respond("hi")
    assert reply
    subs = [e["subsystem"] for e in trace.subsystem_errors]
    assert "inner_monologue" in subs
    # Empty monologue is the spec'd fallback. The response generator handles
    # the empty inner-trace block without crashing — that's the load-bearing
    # property tested here.
    assert trace.monologue == ""


# ---------- response_generator: fatal


def test_response_generator_failure_raises_and_appends_partial_trace(monkeypatch):
    """Even though we cannot ship a reply, the failed turn must be in
    ``anima.traces`` so the transcript captures it."""
    anima = _build_anima()

    def _boom(**kwargs):
        raise ConnectionError("simulated response generator down")

    monkeypatch.setattr(anima._response, "run", _boom)

    n_before = len(anima.traces)
    with pytest.raises(ResponseGenerationFailed) as exc:
        anima.respond("hello world")

    assert exc.value.subsystem == "response_generator"
    assert exc.value.attempts == 5

    # A partial trace was appended even on failure.
    assert len(anima.traces) == n_before + 1
    partial = anima.traces[-1]
    assert partial.response == "[generation failed after 5 attempts]"
    assert partial.user_msg == "hello world"
    # The failure is captured in subsystem_errors.
    subs = [e["subsystem"] for e in partial.subsystem_errors]
    assert "response_generator" in subs


# ---------- multiple subsystems failing in one turn


def test_multiple_subsystem_failures_collected_in_one_trace(monkeypatch):
    anima = _build_anima()

    def _boom(**kwargs):
        raise ConnectionError("drop")

    monkeypatch.setattr(anima._perception, "run", _boom)
    monkeypatch.setattr(anima._appraisal, "run", _boom)

    reply, trace = anima.respond("hi")
    assert reply
    subs = {e["subsystem"] for e in trace.subsystem_errors}
    assert {"perception", "appraisal"} <= subs


# ---------- successful turn has no errors


def test_clean_turn_records_no_subsystem_errors():
    anima = _build_anima()
    reply, trace = anima.respond("hi")
    assert reply
    assert trace.subsystem_errors == []


# ---------- to_jsonable includes subsystem_errors


def test_trace_to_jsonable_includes_subsystem_errors(monkeypatch):
    anima = _build_anima()

    def _boom(**kwargs):
        raise ConnectionError("drop")

    monkeypatch.setattr(anima._perception, "run", _boom)
    _, trace = anima.respond("hi")
    j = trace.to_jsonable()
    assert "subsystem_errors" in j
    assert j["subsystem_errors"]
    assert j["subsystem_errors"][0]["subsystem"] == "perception"
