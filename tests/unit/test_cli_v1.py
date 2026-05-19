"""Unit tests for Fix 2 — ``anima.cli chat --version v1``.

The v1 (frozen Phase-1) Anima has a smaller constructor signature, a
smaller TurnTrace, and lacks ``store``, ``set_session_id``, ``save``,
and ``rollback_last_turn``. The CLI must:

  1. Construct the v1 Anima without passing Phase-2-only kwargs.
  2. Disable persistence (``anima.save()`` is never called).
  3. Honor ``--blind`` and ``--transcript-dir``; write a transcript whose
     header records ``architecture: v1``.
  4. ``/retry`` should print a friendly v1-unavailable message instead
     of crashing.
  5. Head-mode (default) regression must remain byte-identical to the
     pre-Fix-2 behavior — verified by re-running a head smoke through
     the existing CLI.
"""

from __future__ import annotations

import io
import json
from pathlib import Path

import pytest

from anima.cli import main as cli_main


REPO_ROOT = Path(__file__).resolve().parents[2]
PRESET = REPO_ROOT / "anima" / "config" / "presets" / "marcus.yaml"


def _run_cli(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    scripted_input: str,
    *,
    version: str = "v1",
    extra_args: list[str] | None = None,
) -> int:
    """Drive a single chat session with scripted stdin under --version."""
    monkeypatch.setattr("sys.stdin", io.StringIO(scripted_input))
    args = [
        "chat",
        "--config", str(PRESET),
        "--provider", "fake",
        "--version", version,
        "--session-id", f"v1test-{version}",
        "--store-root", str(tmp_path / "store"),
        "--transcript-dir", str(tmp_path / "transcripts"),
    ]
    if extra_args:
        args.extend(extra_args)
    return cli_main(args)


# ---------- Smoke: v1 chat runs end-to-end


def test_v1_chat_smoke_completes_cleanly(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """A v1 chat session with one message + /quit must exit rc=0."""
    rc = _run_cli(tmp_path, monkeypatch, "hello\n/quit\n")
    assert rc == 0


def test_v1_transcript_header_records_architecture_v1(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """The transcript JSON meta block and markdown header must say
    ``architecture: v1`` so a reader can immediately tell which
    architecture produced the run."""
    rc = _run_cli(tmp_path, monkeypatch, "hello\n/quit\n")
    assert rc == 0
    json_files = list((tmp_path / "transcripts").glob("*.json"))
    md_files = list((tmp_path / "transcripts").glob("*.md"))
    assert json_files and md_files

    data = json.loads(json_files[0].read_text())
    assert data["meta"]["architecture"] == "v1"

    md = md_files[0].read_text()
    assert "architecture: v1" in md


def test_v1_transcript_omits_phase2_only_sections(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """v1's TurnTrace has no retrieved memories, prediction, or surprise.
    The transcript writer must OMIT those headings (not render placeholder
    "(none surfaced)" text) so v1 transcripts read clean."""
    rc = _run_cli(tmp_path, monkeypatch, "hello\n/quit\n")
    assert rc == 0
    md_files = list((tmp_path / "transcripts").glob("*.md"))
    assert md_files
    md = md_files[0].read_text()
    # These section headings exist in head mode but should NOT appear in
    # v1 transcripts. The empty (none surfaced) placeholder is the
    # specifically-banned form.
    assert "**Retrieved memories:**" not in md
    assert "**User prediction" not in md
    assert "Surprise (from prior turn)" not in md


def test_v1_retry_prints_unavailable_message(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
):
    """When the user types /retry in v1 mode AFTER a failed turn, the CLI
    must print a friendly v1-unavailable message and stay alive."""
    from anima_v1.core import Anima as AnimaV1

    real_respond = AnimaV1.respond
    state = {"fired": False}

    def flaky(self, msg):
        if not state["fired"]:
            state["fired"] = True
            # Raise a generic exception (v1 has no ResponseGenerationFailed
            # plumbing — the CLI's last-resort handler must still preserve
            # the message for /retry).
            raise RuntimeError("simulated v1 turn failure")
        return real_respond(self, msg)

    monkeypatch.setattr(AnimaV1, "respond", flaky)

    rc = _run_cli(tmp_path, monkeypatch, "boom\n/retry\n/quit\n")
    assert rc == 0
    out = capsys.readouterr().out
    # The friendly message should be printed at least once.
    assert "retry isn't available in --version v1" in out


def test_v1_save_is_not_called(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """v1 has no save(); the CLI must not call it. We assert by checking
    that the store directory is empty after the session ends (head mode
    would write a session JSON there)."""
    rc = _run_cli(tmp_path, monkeypatch, "hello\n/quit\n")
    assert rc == 0
    store_root = tmp_path / "store"
    # Either the store dir doesn't exist (no AnimaStore writes happened)
    # OR it exists but is empty / has no session files. We accept both —
    # the binding property is "no v1-incompatible save() call crashed and
    # no persistence data was written".
    if store_root.exists():
        # Walk anything under the store root and assert no .json files
        # were created (head would have at least one).
        found = list(store_root.rglob("*.json"))
        assert not found, f"v1 should not write store JSON, but found: {found}"


def test_v1_blind_mode_works(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
):
    """--blind under --version v1 should suppress /trace and /state output
    just like in head mode, and still write the transcript to disk."""
    rc = _run_cli(
        tmp_path, monkeypatch, "hi\n/trace\n/quit\n",
        extra_args=["--blind"],
    )
    assert rc == 0
    out = capsys.readouterr().out
    # /trace should be replaced by the hidden notice.
    assert "hidden in blind mode" in out
    # Transcript should still be on disk.
    md_files = list((tmp_path / "transcripts").glob("*.md"))
    assert md_files


def test_v1_state_command_works(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
):
    """/state should print v1's observe() output (mood/drives/etc.)
    without crashing on missing head-only fields."""
    rc = _run_cli(tmp_path, monkeypatch, "hi\n/state\n/quit\n")
    assert rc == 0
    out = capsys.readouterr().out
    # observe() returns name + mood + drives + concerns + traits.
    assert "mood" in out
    assert "drives" in out


def test_v1_banner_includes_architecture_note(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
):
    """The chat banner should announce v1 mode so users running v1 know
    cross-session memory et al. are disabled."""
    rc = _run_cli(tmp_path, monkeypatch, "/quit\n")
    assert rc == 0
    out = capsys.readouterr().out
    assert "v1 (Phase 1 frozen" in out or "running architecture: v1" in out


# ---------- head-mode regression: existing behavior unchanged


def test_head_mode_still_writes_session_store(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """Sanity: under --version head (the default), Anima.save() runs at
    finalize and the store dir holds at least one session JSON. This is
    the regression check that Fix 2's branching didn't break head."""
    rc = _run_cli(tmp_path, monkeypatch, "hello\n/quit\n", version="head")
    assert rc == 0
    store_root = tmp_path / "store"
    found = list(store_root.rglob("*.json"))
    assert found, (
        "head mode should write at least one persistence JSON via anima.save()"
    )


def test_head_mode_transcript_records_architecture_head(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """The architecture field also lands in head transcripts so the
    schema is uniform across modes."""
    rc = _run_cli(tmp_path, monkeypatch, "hello\n/quit\n", version="head")
    assert rc == 0
    json_files = list((tmp_path / "transcripts").glob("*.json"))
    assert json_files
    data = json.loads(json_files[0].read_text())
    assert data["meta"]["architecture"] == "head"
