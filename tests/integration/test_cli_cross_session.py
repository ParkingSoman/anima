"""Integration: E6 CLI wiring — --session-id + AnimaStore.

We exercise the chat command's flag plumbing (argparse parses the new flags,
help string includes them) and the LOAD-BEARING property the CLI promises:
two Anima processes sharing a (--store-root, persona) pair share episodic
events. The CLI's persistence-on-exit and resume-via-session-id are tested
at the Anima+Store layer (test_anima_persistence already covers cross-session
state at that layer; test_self_monitor covers self-monitor events surviving
the hop). Here we focus on the CLI surface itself.
"""

from __future__ import annotations

import io
from pathlib import Path

import pytest

from anima.cli import main as cli_main
from anima.config import load_config
from anima.core import Anima
from anima.llm.fake_adapter import FakeAdapter
from anima.persistence.store import AnimaStore


PRESET = Path(__file__).resolve().parents[2] / "anima" / "config" / "presets" / "marcus.yaml"


def test_chat_help_advertises_new_flags(capsys: pytest.CaptureFixture[str]):
    """The --session-id, --store-root, --version flags must show in --help so
    operators can discover them."""
    with pytest.raises(SystemExit) as exc:
        cli_main(["chat", "--help"])
    assert exc.value.code == 0
    out = capsys.readouterr().out
    assert "--session-id" in out
    assert "--store-root" in out
    assert "--version" in out


def test_chat_loop_persists_with_session_id(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    """Drive the chat REPL with a scripted stdin, asserting that the store
    files appear under --store-root and that the named session's transcript
    is on disk after a clean /quit."""
    # Rich reads from stdin via console.input; redirecting stdin is enough.
    scripted = io.StringIO("hi\nare you well\n/quit\n")
    monkeypatch.setattr("sys.stdin", scripted)

    rc = cli_main([
        "chat",
        "--config", str(PRESET),
        "--provider", "fake",
        "--session-id", "s1",
        "--store-root", str(tmp_path),
    ])
    assert rc == 0

    persona = "marcus"
    behavioral = tmp_path / persona / "behavioral_record.json"
    interpreted = tmp_path / persona / "interpreted.json"
    transcript = tmp_path / persona / "transcripts" / "s1.json"
    assert behavioral.exists(), "behavioral_record.json should be written on save"
    assert interpreted.exists(), "interpreted.json should be written on save"
    assert transcript.exists(), "named session transcript should be on disk"


def test_chat_session_resumes_episodic_memory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    """Session 1 writes events via the CLI; a fresh process at the same
    --store-root + persona sees them. This is the cross-session demo. We
    verify it at the Anima+Store layer for session 2 because driving the
    interactive REPL is unnecessary to prove the load-bearing property."""
    scripted = io.StringIO("I love sailing\n/quit\n")
    monkeypatch.setattr("sys.stdin", scripted)

    rc = cli_main([
        "chat",
        "--config", str(PRESET),
        "--provider", "fake",
        "--session-id", "s1",
        "--store-root", str(tmp_path),
    ])
    assert rc == 0

    # Session 2: same store name, fresh Anima. The episodic_store should be
    # hydrated from disk with at least one event from session 1.
    cfg = load_config(PRESET)
    store2 = AnimaStore("marcus", root=tmp_path)
    a2 = Anima(cfg, llm=FakeAdapter(), store=store2)
    assert len(a2.episodic_store.events) >= 1
    full = a2.episodic_store.events[0].full_content
    assert "sailing" in full
