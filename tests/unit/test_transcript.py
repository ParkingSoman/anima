"""Unit tests for :class:`anima.transcript.TranscriptWriter` (E7).

We construct a small Anima with the deterministic ``FakeAdapter``, run
2-3 turns through it, then assert that the writer produced both files
with the expected structure and content. No network calls.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from anima.config import load_config
from anima.core import Anima
from anima.llm import make_adapter
from anima.transcript import TranscriptWriter


REPO_ROOT = Path(__file__).resolve().parents[2]
PRESET = REPO_ROOT / "anima" / "config" / "presets" / "marcus.yaml"


@pytest.fixture
def anima_and_writer(tmp_path: Path):
    cfg = load_config(PRESET)
    anima = Anima(cfg, llm=make_adapter("fake"))
    anima.set_session_id("s-test")
    writer = TranscriptWriter(
        persona_name="marcus",
        session_id="s-test",
        config_path=PRESET,
        provider="fake",
        output_dir=tmp_path / "transcripts",
    )
    writer.write_header(anima)
    return anima, writer, tmp_path


def _run_turns(anima: Anima, writer: TranscriptWriter, n: int) -> list[str]:
    """Drive n turns through the Anima and tee each into the writer."""
    inputs = [
        "hello",
        "how are you feeling today",
        "tell me about your weekend",
    ][:n]
    for i, msg in enumerate(inputs, start=1):
        reply, trace = anima.respond(msg)
        writer.write_turn(i, msg, reply, trace)
    return inputs


def test_files_are_created_in_output_dir(anima_and_writer):
    anima, writer, tmp_path = anima_and_writer
    _run_turns(anima, writer, 2)

    transcripts_dir = tmp_path / "transcripts"
    assert transcripts_dir.is_dir()
    assert writer.md_path.is_file()
    assert writer.json_path.is_file()
    # Paths are under the requested output_dir.
    assert writer.md_path.parent == transcripts_dir
    assert writer.json_path.parent == transcripts_dir
    # Filenames include persona and session_id.
    assert "marcus" in writer.md_path.name
    assert "s-test" in writer.md_path.name


def test_markdown_contains_turn_headings_and_monologue(anima_and_writer):
    anima, writer, _ = anima_and_writer
    _run_turns(anima, writer, 2)

    md = writer.md_path.read_text(encoding="utf-8")
    assert "### Turn 1" in md
    assert "### Turn 2" in md
    # FakeAdapter monologue text appears verbatim in the trace block.
    assert "Something tilts in my chest" in md
    # User msg + reply appear in the dialogue block.
    assert "hello" in md
    assert "how are you feeling today" in md


def test_json_shape_and_lengths(anima_and_writer):
    anima, writer, _ = anima_and_writer
    _run_turns(anima, writer, 3)

    data = json.loads(writer.json_path.read_text(encoding="utf-8"))
    assert set(data.keys()) >= {"meta", "turns", "state_trajectory"}
    assert len(data["turns"]) == 3
    assert len(data["state_trajectory"]) == 3

    # Each turn carries the TurnTrace.to_jsonable() shape.
    for t in data["turns"]:
        for key in (
            "user_msg", "perception", "appraisal", "monologue",
            "mood_before", "mood_after", "drives_before", "drives_after",
            "response", "retrieved", "usage",
            "surprise_from_last_turn", "prediction",
        ):
            assert key in t, f"missing key {key!r} in turn jsonable"

    # State-trajectory entries carry mood/drives only (not the full trace).
    for s in data["state_trajectory"]:
        assert set(s.keys()) == {"turn", "mood_after", "drives_after"}

    # Meta is populated by write_header.
    meta = data["meta"]
    assert meta["session_id"] == "s-test"
    assert meta["provider"] == "fake"


def test_finalize_adds_summary_and_finalized_at(anima_and_writer):
    anima, writer, _ = anima_and_writer
    _run_turns(anima, writer, 2)
    writer.finalize(anima)

    md = writer.md_path.read_text(encoding="utf-8")
    assert "## State trajectory summary" in md
    assert "total turns" in md
    assert "Final state snapshot" in md

    data = json.loads(writer.json_path.read_text(encoding="utf-8"))
    assert "finalized_at" in data
    assert isinstance(data["finalized_at"], str) and data["finalized_at"]


def test_write_turn_after_finalize_still_appends(anima_and_writer):
    """Picking the 'append' semantics: post-finalize writes must not crash."""
    anima, writer, _ = anima_and_writer
    _run_turns(anima, writer, 2)
    writer.finalize(anima)

    # One more turn after finalize.
    reply, trace = anima.respond("one more thing")
    writer.write_turn(3, "one more thing", reply, trace)

    data = json.loads(writer.json_path.read_text(encoding="utf-8"))
    assert len(data["turns"]) == 3
    assert len(data["state_trajectory"]) == 3
    # finalized_at remains from the earlier finalize call (we don't clear it).
    assert "finalized_at" in data
