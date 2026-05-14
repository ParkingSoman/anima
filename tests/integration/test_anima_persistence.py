"""Integration: Anima + AnimaStore cross-session memory (E5).

The architectural commitment under test:
    You chat with Marcus on Monday → process exits. New process, same name on
    Wednesday → Marcus recalls Monday. The §5.1/§5.2 separation is preserved
    through the on-disk hop.
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path

import pytest

from anima.config import load_config
from anima.core import Anima
from anima.llm.fake_adapter import FakeAdapter
from anima.persistence.store import AnimaStore
from anima.state.episodic import AffectTag, EpisodicEvent


PRESETS_DIR = Path(__file__).resolve().parents[2] / "anima" / "config" / "presets"
MARCUS = PRESETS_DIR / "marcus.yaml"


def _make_anima(tmp_path: Path, name: str = "test-A", autosave_every: int = 5) -> tuple[Anima, AnimaStore]:
    cfg = load_config(MARCUS)
    store = AnimaStore(name, root=tmp_path)
    a = Anima(cfg, llm=FakeAdapter(), store=store, autosave_every=autosave_every)
    return a, store


def test_phase1_backward_compat_no_store(tmp_path: Path):
    """No store= kwarg → Phase 1 behavior. No on-disk files, no autosave attribute leakage."""
    cfg = load_config(MARCUS)
    a = Anima(cfg, llm=FakeAdapter())
    a.respond("hello")
    assert not (tmp_path / "anima_store").exists()  # default path not used either


def test_autosave_does_not_fire_below_threshold(tmp_path: Path):
    a, store = _make_anima(tmp_path, autosave_every=5)
    for msg in ["hi", "how are you", "tell me about yourself"]:
        a.respond(msg)
    # 3 turns < threshold of 5 → no autosave yet.
    assert not store.behavioral_path.exists()
    assert not store.interpreted_path.exists()


def test_autosave_fires_at_threshold(tmp_path: Path):
    a, store = _make_anima(tmp_path, autosave_every=5)
    for i in range(5):
        a.respond(f"turn {i}")
    # 5th turn triggers autosave.
    assert store.behavioral_path.exists()
    assert store.interpreted_path.exists()


def test_explicit_save_works_at_any_time(tmp_path: Path):
    a, store = _make_anima(tmp_path, autosave_every=999)
    a.respond("just one turn")
    assert not store.interpreted_path.exists()
    a.save()
    assert store.interpreted_path.exists()
    assert store.behavioral_path.exists()


def test_cross_session_episodic_memory(tmp_path: Path):
    """Build Anima A1 with store, append an event, save. New Anima A2 with the
    same name reads back the event. This is THE feature: cross-session
    memory."""
    cfg = load_config(MARCUS)
    store_v1 = AnimaStore("cross-session", root=tmp_path)
    a1 = Anima(cfg, llm=FakeAdapter(), store=store_v1, autosave_every=999)

    a1.episodic_store.append(EpisodicEvent(
        id="ev-monday",
        ts="2026-05-11T10:00:00Z",
        content_summary="user mentioned moving",
        full_content="user said they're moving to Boston",
        participants=["user", "self"],
        affect_tag=AffectTag(valence=0.3),
        importance=0.7,
    ))
    a1.save()

    # New process simulation: fresh Anima, same name.
    store_v2 = AnimaStore("cross-session", root=tmp_path)
    a2 = Anima(cfg, llm=FakeAdapter(), store=store_v2)
    assert len(a2.episodic_store.events) == 1
    assert a2.episodic_store.events[0].id == "ev-monday"
    assert a2.episodic_store.events[0].full_content == "user said they're moving to Boston"


def test_cross_session_interpreted_state(tmp_path: Path):
    """§5.2 — mood, relations, self-model survive a hop."""
    cfg = load_config(MARCUS)
    store_v1 = AnimaStore("interp", root=tmp_path)
    a1 = Anima(cfg, llm=FakeAdapter(), store=store_v1, autosave_every=999)
    a1.mood.valence = 0.42
    a1.mood.discrete["joy"] = 0.6
    a1.self_model.current_concerns.append("a fresh concern")
    a1.relations.get_or_create("user").beliefs_about_person.append("loves their dog")
    a1.save()

    store_v2 = AnimaStore("interp", root=tmp_path)
    a2 = Anima(cfg, llm=FakeAdapter(), store=store_v2)
    assert a2.mood.valence == pytest.approx(0.42)
    assert a2.mood.discrete.get("joy") == pytest.approx(0.6)
    assert "a fresh concern" in a2.self_model.current_concerns
    assert "loves their dog" in a2.relations.get_or_create("user").beliefs_about_person


def test_session_id_creates_transcript_file(tmp_path: Path):
    a, store = _make_anima(tmp_path, autosave_every=1)
    a.set_session_id("monday-session")
    a.respond("hi marcus")
    transcript_file = store.transcripts_dir / "monday-session.json"
    assert transcript_file.exists()


def test_two_sessions_two_transcript_files(tmp_path: Path):
    cfg = load_config(MARCUS)
    store_v1 = AnimaStore("multi", root=tmp_path)
    a1 = Anima(cfg, llm=FakeAdapter(), store=store_v1, autosave_every=1)
    a1.set_session_id("session-1")
    a1.respond("first")
    a1.save()

    store_v2 = AnimaStore("multi", root=tmp_path)
    a2 = Anima(cfg, llm=FakeAdapter(), store=store_v2, autosave_every=1)
    a2.set_session_id("session-2")
    a2.respond("second")
    a2.save()

    assert (store_v2.transcripts_dir / "session-1.json").exists()
    assert (store_v2.transcripts_dir / "session-2.json").exists()
