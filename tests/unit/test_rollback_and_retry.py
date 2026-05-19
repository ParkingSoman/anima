"""Unit tests for /retry rollback + silence detection + error rendering.

Covers requirements A/B/C of the follow-up batch:
  A. retry policy is exposed in the transcript header.
  B. silence detection populates ``trace.silences`` per the per-subsystem rules
     and the transcript renders both the ``⚠️`` and ``🤐`` blocks distinctly.
  C. ``Anima.rollback_last_turn()`` restores all turn-modified state; ``/retry``
     in the CLI rolls back BEFORE re-calling ``respond()``, so the failed user
     message does not pollute the retry's context.
"""

from __future__ import annotations

import copy
import io
import json
from pathlib import Path

import pytest

from anima.config import load_config
from anima.core import Anima, TurnTrace
from anima.llm import make_adapter
from anima.llm.fake_adapter import EmptyTextFakeAdapter, FakeAdapter
from anima.llm.retry import RetryConfig
from anima.subsystems.errors import ResponseGenerationFailed
from anima.transcript import (
    TranscriptWriter,
    _format_silences_md,
    _format_subsystem_errors_md,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
PRESET = REPO_ROOT / "anima" / "config" / "presets" / "marcus.yaml"


def _build_anima() -> Anima:
    return Anima(load_config(PRESET), llm=make_adapter("fake"))


# ---------- Requirement C: Anima.rollback_last_turn()


def test_rollback_restores_conversation_history():
    anima = _build_anima()
    # Run one clean turn so there is something to roll back.
    anima.respond("hello there")
    assert any(
        m.get("content") == "hello there" for m in anima.conversation_history
    ), "the failed message should currently be in history (precondition)"
    rolled = anima.rollback_last_turn()
    assert rolled is True
    assert anima.conversation_history == [], (
        "rollback should remove the user+assistant entries the turn appended"
    )


def test_rollback_is_idempotent():
    """Calling rollback twice in a row should only roll back once."""
    anima = _build_anima()
    anima.respond("first")
    first_rollback = anima.rollback_last_turn()
    second_rollback = anima.rollback_last_turn()
    assert first_rollback is True
    assert second_rollback is False, (
        "the second call should be a no-op because the snapshot was consumed"
    )


def test_rollback_with_nothing_to_roll_back_returns_false():
    anima = _build_anima()
    assert anima.rollback_last_turn() is False


def test_rollback_restores_mood_and_drives():
    anima = _build_anima()
    mood_before = copy.deepcopy(anima.mood)
    drives_before = copy.deepcopy(anima.drives)
    anima.respond("hello")
    # Sanity check — the turn DID move something.
    mood_after_turn = copy.deepcopy(anima.mood)
    assert (
        mood_after_turn.valence != mood_before.valence
        or mood_after_turn.arousal != mood_before.arousal
        or dict(mood_after_turn.discrete) != dict(mood_before.discrete)
    ), "the canned fake-adapter appraisal should mutate mood somewhere"
    assert anima.rollback_last_turn() is True
    assert anima.mood.valence == pytest.approx(mood_before.valence)
    assert anima.mood.arousal == pytest.approx(mood_before.arousal)
    assert anima.mood.dominance == pytest.approx(mood_before.dominance)
    assert dict(anima.mood.discrete) == dict(mood_before.discrete)
    assert dict(anima.drives.activations) == dict(drives_before.activations)


def test_rollback_restores_traces_and_episodic_store():
    anima = _build_anima()
    n_traces_before = len(anima.traces)
    n_events_before = len(anima.episodic_store.events)
    anima.respond("hello")
    assert len(anima.traces) == n_traces_before + 1
    assert len(anima.episodic_store.events) == n_events_before + 1
    anima.rollback_last_turn()
    assert len(anima.traces) == n_traces_before
    assert len(anima.episodic_store.events) == n_events_before


def test_rollback_after_response_generator_failure(monkeypatch):
    """Even when response_generator fails (partial state mutated), the rollback
    target is the state BEFORE respond() was called with the failed message."""
    anima = _build_anima()
    # Capture baselines.
    history_before = list(anima.conversation_history)
    n_traces_before = len(anima.traces)
    n_events_before = len(anima.episodic_store.events)

    def _boom(**kwargs):
        raise ConnectionError("response generator down")

    monkeypatch.setattr(anima._response, "run", _boom)

    with pytest.raises(ResponseGenerationFailed):
        anima.respond("hello")
    # A partial trace was appended; rollback should drop it.
    assert len(anima.traces) == n_traces_before + 1

    assert anima.rollback_last_turn() is True
    assert list(anima.conversation_history) == history_before
    assert len(anima.traces) == n_traces_before
    assert len(anima.episodic_store.events) == n_events_before


def test_rollback_after_degraded_turn_with_fallbacks(monkeypatch):
    """A successful-but-degraded turn (perception failed → fallback) can also
    be rolled back; the rollback target is still the pre-respond() state."""
    anima = _build_anima()
    history_before = list(anima.conversation_history)
    n_traces_before = len(anima.traces)

    def _boom(**kwargs):
        raise ConnectionError("perception dropped")

    monkeypatch.setattr(anima._perception, "run", _boom)
    reply, trace = anima.respond("hi")
    assert reply, "the reply should still come back via fallbacks"
    # Pre-rollback: degraded turn left its mark.
    assert len(anima.traces) == n_traces_before + 1
    assert any("hi" in m.get("content", "") for m in anima.conversation_history)
    # Rollback drops everything.
    assert anima.rollback_last_turn() is True
    assert list(anima.conversation_history) == history_before
    assert len(anima.traces) == n_traces_before


def test_rollback_restores_user_relation_reference():
    """``_user_relation`` is a live reference into ``relations.schemas`` — the
    rollback must re-point it so subsequent record_prediction / record_surprise
    calls land on the rolled-back schema."""
    anima = _build_anima()
    anima.respond("hello")
    anima.rollback_last_turn()
    # Reference should resolve back through the restored RelationsStore.
    assert anima._user_relation is anima.relations.get_or_create("user")


# ---------- Requirement C: /retry integration in cmd_chat


def _run_cli(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, scripted_input: str) -> int:
    from anima.cli import main as cli_main

    monkeypatch.setattr("sys.stdin", io.StringIO(scripted_input))
    return cli_main([
        "chat",
        "--config", str(PRESET),
        "--provider", "fake",
        "--session-id", "s-rollbacktest",
        "--store-root", str(tmp_path / "store"),
        "--transcript-dir", str(tmp_path / "transcripts"),
    ])


def test_retry_does_not_leak_failed_message_into_context(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """After a failed turn, /retry should run respond() with conversation
    history that does NOT contain the failed message."""
    seen_histories: list[list[dict]] = []

    real_respond = Anima.respond
    state = {"fired": False}

    def flaky(self, msg):
        # Snapshot the conversation_history seen by respond() at call time.
        seen_histories.append(copy.deepcopy(self.conversation_history))
        if not state["fired"]:
            state["fired"] = True
            raise ResponseGenerationFailed(
                subsystem="response_generator",
                attempts=5,
                last_error=ConnectionError("simulated"),
            )
        return real_respond(self, msg)

    monkeypatch.setattr(Anima, "respond", flaky)

    rc = _run_cli(tmp_path, monkeypatch, "boom message\n/retry\n/quit\n")
    assert rc == 0
    # respond() was called twice.
    assert len(seen_histories) == 2
    # Neither call's conversation_history should contain 'boom message' as a
    # past entry — the FIRST call sees an empty history (fresh session), and
    # the SECOND call (after /retry triggers rollback) ALSO sees an empty
    # history. That's the load-bearing assertion: rollback removed the failed
    # turn's effect on history.
    for hist in seen_histories:
        assert all("boom message" not in m.get("content", "") for m in hist), (
            f"history should not contain 'boom message' on retry, got {hist}"
        )


def test_retry_marks_transcript_turn_as_retry_of(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """The retry turn's transcript entry should carry ``retry_of: N-1`` and
    the markdown header should read 'Turn N — retry of turn N-1'."""
    real_respond = Anima.respond
    state = {"fired": False}

    def flaky(self, msg):
        if not state["fired"]:
            state["fired"] = True
            raise ResponseGenerationFailed(
                subsystem="response_generator",
                attempts=5,
                last_error=ConnectionError("simulated"),
            )
        return real_respond(self, msg)

    monkeypatch.setattr(Anima, "respond", flaky)

    rc = _run_cli(tmp_path, monkeypatch, "first\n/retry\n/quit\n")
    assert rc == 0

    json_files = list((tmp_path / "transcripts").glob("*.json"))
    md_files = [m for m in (tmp_path / "transcripts").glob("*.md") if not m.stem.endswith("_neat")]
    assert json_files and md_files
    data = json.loads(json_files[0].read_text())
    md_text = md_files[0].read_text()

    turns = data["turns"]
    # Turn 1 = failed; Turn 2 = retry.
    assert turns[0]["status"] == "failed"
    assert turns[1]["status"] == "ok"
    assert turns[1].get("retry_of") == 1
    assert "Turn 2 — retry of turn 1" in md_text


# ---------- Requirement A: retry policy in transcript header


def test_transcript_header_records_retry_policy(tmp_path: Path):
    anima = _build_anima()
    writer = TranscriptWriter(
        persona_name="marcus",
        session_id="s-policy",
        config_path=PRESET,
        provider="fake",
        output_dir=tmp_path,
    )
    writer.write_header(anima)
    data = json.loads(writer.json_path.read_text())
    pol = data["meta"]["retry_policy"]
    # FakeAdapter defaults to max_attempts=1; the policy reflects the actual
    # adapter default. The point is that SOMETHING is recorded — for production
    # adapters this will be 3 attempts / 2 retries.
    assert "adapter_max_attempts" in pol
    assert pol["response_generator_max_attempts"] == 5
    assert pol["response_generator_retries"] == 4
    md = writer.md_path.read_text()
    assert "retry_policy" in md


# ---------- Requirement B: silence detection


def test_silence_inner_monologue_empty_string():
    """Empty monologue text from a successful call is silence."""
    adapter = FakeAdapter(monologue_text="")
    anima = Anima(load_config(PRESET), llm=adapter)
    _, trace = anima.respond("hi")
    sub_names = [s["subsystem"] for s in trace.silences]
    assert "inner_monologue" in sub_names


def test_silence_inner_monologue_whitespace_only():
    """Whitespace-only monologue is silence too."""
    adapter = FakeAdapter(monologue_text="   \n\t ")
    anima = Anima(load_config(PRESET), llm=adapter)
    _, trace = anima.respond("hi")
    sub_names = [s["subsystem"] for s in trace.silences]
    assert "inner_monologue" in sub_names


def test_silence_memory_retrieval_empty_list():
    """A fresh Anima has an empty episodic store; the retrieval call returns
    no memories → silence flagged."""
    anima = _build_anima()
    _, trace = anima.respond("hi")
    sub_names = [s["subsystem"] for s in trace.silences]
    assert "memory_retrieval" in sub_names


def test_silence_user_prediction_trivial_output(monkeypatch):
    """User prediction returning the unknown/0.0 trivial output is silence."""
    anima = _build_anima()
    from anima.subsystems.user_prediction import PredictionResult

    def _trivial(**kwargs):
        return PredictionResult(
            next_intent_label="unknown",
            content_hint="",
            confidence=0.0,
            rationale="model declined",
        )

    monkeypatch.setattr(anima._user_prediction, "predict", _trivial)
    _, trace = anima.respond("hi")
    sub_names = [s["subsystem"] for s in trace.silences]
    assert "user_prediction" in sub_names


def test_silence_response_generator_empty_reply():
    """Fix 1 (and iris-v1 follow-up) changed the contract for the
    response_generator's empty reply.

    Before Fix 1: an empty reply from a successful API call would pass
    through and surface as a ``silence`` (no retry).

    After Fix 1: the retry layer treats empty/whitespace-only text as a
    retryable failure. The response_generator uses
    ``RetryConfig(max_attempts=5)``.

    After the iris-v1 follow-up: the retry layer is now finish_reason
    aware. An empty response with finish_reason in {stop, end_turn,
    stop_sequence, None} is treated as a *genuine model silence* and
    NOT retried. Only empty responses with a non-stop finish_reason
    (length, content_filter, error, etc.) trigger retry. We use
    ``EmptyTextFakeAdapter`` here, which defaults the empty responses
    to ``finish_reason="length"`` — i.e. the cutoff path that SHOULD
    exhaust the budget and raise ``EmptyResponseAfterRetries``, which
    ``Anima.respond`` escalates to ``ResponseGenerationFailed``.
    """
    adapter = EmptyTextFakeAdapter(
        empty_first_n=100,  # effectively always-empty
        empty_finish_reason="length",
        retry_cfg=RetryConfig(max_attempts=5, base_delay=0.0, jitter=0.0),
        strong_text="",
    )
    anima = Anima(load_config(PRESET), llm=adapter)
    with pytest.raises(ResponseGenerationFailed) as exc_info:
        anima.respond("hi")
    # The wrapped exception is EmptyResponseAfterRetries; the partial trace
    # appended before the raise records the error with the right type.
    assert type(exc_info.value.last_error).__name__ == "EmptyResponseAfterRetries"
    # The finish_reason should be plumbed all the way out (iris-v1 fix).
    assert getattr(exc_info.value.last_error, "last_finish_reason", None) == "length"
    partial = anima.traces[-1]
    err_types = [e["error_type"] for e in partial.subsystem_errors]
    assert "EmptyResponseAfterRetries" in err_types


def test_silence_not_flagged_when_subsystem_errored(monkeypatch):
    """If a subsystem ERRORED (in subsystem_errors), it should NOT also be
    flagged as silence — those are distinct concepts."""
    anima = _build_anima()

    def _boom(**kwargs):
        raise ConnectionError("drop")

    monkeypatch.setattr(anima._monologue, "run", _boom)
    _, trace = anima.respond("hi")
    # inner_monologue is in errors (so it shouldn't also be in silences)
    err_subs = [e["subsystem"] for e in trace.subsystem_errors]
    sil_subs = [s["subsystem"] for s in trace.silences]
    assert "inner_monologue" in err_subs
    assert "inner_monologue" not in sil_subs


def test_silence_appraisal_never_flagged():
    """Appraisal always carries a scene_tag; per spec we do NOT flag it."""
    anima = _build_anima()
    _, trace = anima.respond("hi")
    sub_names = [s["subsystem"] for s in trace.silences]
    assert "appraisal" not in sub_names


def test_silence_perception_never_flagged():
    """Perception always returns structure; per spec we do NOT flag it."""
    anima = _build_anima()
    _, trace = anima.respond("hi")
    sub_names = [s["subsystem"] for s in trace.silences]
    assert "perception" not in sub_names


def test_silences_appear_in_trace_to_jsonable():
    anima = _build_anima()  # fresh store → memory_retrieval will be silent
    _, trace = anima.respond("hi")
    j = trace.to_jsonable()
    assert "silences" in j
    assert any(s["subsystem"] == "memory_retrieval" for s in j["silences"])


# ---------- Requirement B: transcript rendering


def test_transcript_renders_generation_errors_block(tmp_path: Path, monkeypatch):
    anima = _build_anima()

    def _boom(**kwargs):
        raise ConnectionError("simulated appraisal failure")

    monkeypatch.setattr(anima._appraisal, "run", _boom)
    reply, trace = anima.respond("hi")
    writer = TranscriptWriter(
        persona_name="marcus", session_id="s-errblock",
        config_path=PRESET, provider="fake", output_dir=tmp_path,
    )
    writer.write_header(anima)
    writer.write_turn(1, "hi", reply, trace)
    md = writer.md_path.read_text()
    assert "⚠️ **Generation errors this turn:**" in md
    assert "**appraisal** failed after" in md
    assert "error type: `ConnectionError`" in md
    assert "simulated appraisal failure" in md
    assert "attempts:" in md


def test_transcript_renders_silence_block(tmp_path: Path):
    """A fresh anima will have memory_retrieval silence."""
    anima = _build_anima()
    reply, trace = anima.respond("hi")
    writer = TranscriptWriter(
        persona_name="marcus", session_id="s-silenceblock",
        config_path=PRESET, provider="fake", output_dir=tmp_path,
    )
    writer.write_header(anima)
    writer.write_turn(1, "hi", reply, trace)
    md = writer.md_path.read_text()
    assert "🤐 **Model chose silence this turn:**" in md
    assert "**memory_retrieval**" in md


def test_transcript_json_includes_silences_and_retry_of(tmp_path: Path):
    anima = _build_anima()
    reply, trace = anima.respond("hi")
    writer = TranscriptWriter(
        persona_name="marcus", session_id="s-jsonsil",
        config_path=PRESET, provider="fake", output_dir=tmp_path,
    )
    writer.write_header(anima)
    writer.write_turn(1, "hi", reply, trace)
    data = json.loads(writer.json_path.read_text())
    t0 = data["turns"][0]
    assert "silences" in t0
    assert isinstance(t0["silences"], list)
    assert "retry_of" in t0
    assert t0["retry_of"] is None


def test_format_subsystem_errors_md_includes_full_message():
    """Direct unit test for the formatter — full exception message is printed."""
    md = _format_subsystem_errors_md([
        {
            "subsystem": "memory_retrieval",
            "error_type": "APIStatusError",
            "message": "upstream service unavailable (503)",
            "attempts": 3,
        }
    ])
    assert "**memory_retrieval**" in md
    assert "APIStatusError" in md
    assert "upstream service unavailable (503)" in md
    assert "attempts: 3" in md


def test_format_silences_md_renders_subsystem_and_detail():
    md = _format_silences_md([
        {"subsystem": "inner_monologue", "detail": "returned an empty string"},
    ])
    assert "🤐" in md
    assert "**inner_monologue**" in md
    assert "returned an empty string" in md


def test_format_empty_inputs_render_empty_string():
    assert _format_subsystem_errors_md([]) == ""
    assert _format_silences_md([]) == ""

