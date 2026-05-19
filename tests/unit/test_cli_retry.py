"""Unit tests for CLI-level error handling + /retry.

The chat REPL must:
  - survive a ``ResponseGenerationFailed`` (does not crash the loop)
  - survive an unexpected exception (last-resort catch)
  - preserve the user's failed message and resend it on /retry
  - record the failed turn in the transcript
  - clear the last-failed message after a successful turn (so /retry on a
    clean session prints "nothing to retry")
"""

from __future__ import annotations

import io
from pathlib import Path

import pytest

from anima.cli import main as cli_main
from anima.subsystems.errors import ResponseGenerationFailed


PRESET = Path(__file__).resolve().parents[2] / "anima" / "config" / "presets" / "marcus.yaml"


def _run_cli(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, scripted_input: str) -> int:
    """Drive a single chat session with scripted stdin."""
    monkeypatch.setattr("sys.stdin", io.StringIO(scripted_input))
    return cli_main([
        "chat",
        "--config", str(PRESET),
        "--provider", "fake",
        "--session-id", "s-retrytest",
        "--store-root", str(tmp_path / "store"),
        "--transcript-dir", str(tmp_path / "transcripts"),
    ])


def test_chat_loop_survives_response_generation_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    """Patch Anima.respond to raise once, then succeed. Loop must NOT crash."""
    from anima.core import Anima

    real_respond = Anima.respond
    state = {"fired": False}

    def flaky(self, msg):
        if not state["fired"]:
            state["fired"] = True
            raise ResponseGenerationFailed(
                subsystem="response_generator",
                attempts=5,
                last_error=ConnectionError("simulated downstream drop"),
            )
        return real_respond(self, msg)

    monkeypatch.setattr(Anima, "respond", flaky)

    # First message fails, second succeeds, then quit. The loop must run all
    # three inputs without raising.
    rc = _run_cli(tmp_path, monkeypatch, "first\nsecond\n/quit\n")
    assert rc == 0
    assert state["fired"], "the test setup should have fired the simulated failure"


def test_chat_loop_survives_unexpected_exception(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    """Patch Anima.respond to raise a NON-ResponseGenerationFailed exception
    once. The last-resort catch must keep the REPL alive."""
    from anima.core import Anima

    real_respond = Anima.respond
    state = {"fired": False}

    def flaky(self, msg):
        if not state["fired"]:
            state["fired"] = True
            raise RuntimeError("kaboom — entirely unexpected")
        return real_respond(self, msg)

    monkeypatch.setattr(Anima, "respond", flaky)

    rc = _run_cli(tmp_path, monkeypatch, "first\nsecond\n/quit\n")
    assert rc == 0
    assert state["fired"]


def test_retry_command_resends_last_failed_message(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
):
    """When the first turn fails, /retry must resend the same message.

    We verify by observing that ``Anima.respond`` is called with the original
    message text after the user types /retry.
    """
    from anima.core import Anima

    real_respond = Anima.respond
    state = {"fired": False, "msgs": []}

    def flaky(self, msg):
        state["msgs"].append(msg)
        if not state["fired"]:
            state["fired"] = True
            raise ResponseGenerationFailed(
                subsystem="response_generator",
                attempts=5,
                last_error=ConnectionError("simulated"),
            )
        return real_respond(self, msg)

    monkeypatch.setattr(Anima, "respond", flaky)

    # "hello there" fails → "/retry" should re-send "hello there" → /quit.
    rc = _run_cli(tmp_path, monkeypatch, "hello there\n/retry\n/quit\n")
    assert rc == 0
    # Both respond() calls saw the SAME message; the second call (after /retry)
    # came in with the preserved text.
    assert state["msgs"] == ["hello there", "hello there"]


def test_retry_without_prior_failure_prints_nothing_to_retry(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
):
    """/retry at the start of a session, with no failed message in scope, is
    a no-op with a friendly message."""
    rc = _run_cli(tmp_path, monkeypatch, "/retry\n/quit\n")
    assert rc == 0
    out = capsys.readouterr().out
    assert "nothing to retry" in out


def test_failed_turn_is_recorded_in_transcript(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    """The failed turn must be persisted to the per-session transcript so the
    user can see WHICH turn glitched after the fact."""
    from anima.core import Anima

    def always_fail(self, msg):
        raise ResponseGenerationFailed(
            subsystem="response_generator",
            attempts=5,
            last_error=ConnectionError("permanent drop"),
        )

    monkeypatch.setattr(Anima, "respond", always_fail)

    rc = _run_cli(tmp_path, monkeypatch, "hi\n/quit\n")
    assert rc == 0

    # Find the transcript JSON file (stamp suffix is dynamic).
    json_files = list((tmp_path / "transcripts").glob("*.json"))
    assert json_files, "transcript JSON should have been written"
    import json
    data = json.loads(json_files[0].read_text())
    turns = data["turns"]
    assert turns, "the failed turn should appear in turns[]"
    assert turns[0]["status"] == "failed"
    assert turns[0]["user_msg"] == "hi"


def test_successful_turn_clears_retry_target(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
):
    """After a failed-then-successful sequence, /retry should report 'nothing
    to retry' — the successful turn clears the failed-message slot."""
    from anima.core import Anima

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

    # boom → recovers on next msg → /retry should be a no-op.
    rc = _run_cli(tmp_path, monkeypatch, "first\nsecond\n/retry\n/quit\n")
    assert rc == 0
    out = capsys.readouterr().out
    assert "nothing to retry" in out
