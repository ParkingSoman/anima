"""Integration: E6 self_monitor — every turn encodes an EpisodicEvent.

This is the bridge from "the turn loop runs" to "memory accumulates from real
turns". Phase 2 closure: without this, the episodic store stays empty across
sessions and retrieval has nothing to surface.

The architectural commitment under test:
  - One ``respond()`` call → exactly one new EpisodicEvent.
  - The event's participants include both 'user' and the persona name (lowered).
  - The event's full_content carries BOTH sides of the turn (user: ... / self: ...).
  - The event's importance is in (0, 1].
  - Affect is snapshotted at encode-time (frozen — does not drift with later mood).
  - Two respond() calls produce two events with distinct ids.
  - Events survive an AnimaStore save/load round-trip (E5 ↔ E6 contract).
"""

from __future__ import annotations

from pathlib import Path

from anima.config import load_config
from anima.core import Anima
from anima.llm.fake_adapter import FakeAdapter
from anima.persistence.store import AnimaStore
from anima.state.episodic import AffectTag


PRESET = Path(__file__).resolve().parents[2] / "anima" / "config" / "presets" / "marcus.yaml"


def _make_anima() -> Anima:
    return Anima(load_config(PRESET), llm=FakeAdapter())


def test_respond_appends_exactly_one_event():
    a = _make_anima()
    assert len(a.episodic_store.events) == 0
    a.respond("hi marcus")
    assert len(a.episodic_store.events) == 1


def test_event_participants_include_user_and_persona():
    a = _make_anima()
    a.respond("hi there")
    ev = a.episodic_store.events[-1]
    persona = a.cfg.biography.name.lower()
    assert "user" in ev.participants
    assert persona in ev.participants


def test_event_full_content_carries_both_sides():
    a = _make_anima()
    a.respond("how are you")
    ev = a.episodic_store.events[-1]
    # The user side is the literal message; the self side is whatever the
    # response generator emitted. Both prefixed labels must be present so the
    # retrieval ranker can substring-match on either side.
    assert "user:" in ev.full_content
    assert "self:" in ev.full_content
    assert "how are you" in ev.full_content


def test_event_importance_in_valid_range():
    a = _make_anima()
    a.respond("anything")
    ev = a.episodic_store.events[-1]
    # The heuristic clamps to [0.05, 1.0]. We check the looser (0, 1] band so
    # the test doesn't pin the floor — only that the score is a valid
    # importance value.
    assert 0.0 < ev.importance <= 1.0


def test_two_calls_produce_distinct_event_ids():
    a = _make_anima()
    a.respond("turn one")
    a.respond("turn two")
    assert len(a.episodic_store.events) == 2
    ids = [e.id for e in a.episodic_store.events]
    assert ids[0] != ids[1]
    # IDs are turn-numbered so even two events in the same wall-second remain
    # unique. The second event's ordinal must reflect the second turn.
    assert ids[1].endswith("-2")


def test_event_affect_tag_is_frozen_at_encode_time():
    """The affect snapshot at encode time must not drift when the live mood
    drifts later. This is the architectural promise of AffectTag (see
    state/episodic.py)."""
    a = _make_anima()
    a.respond("first")
    ev = a.episodic_store.events[-1]
    affect_at_encode = AffectTag(
        valence=ev.affect_tag.valence,
        arousal=ev.affect_tag.arousal,
        dominance=ev.affect_tag.dominance,
        discrete=dict(ev.affect_tag.discrete),
    )
    # Mutate the live mood AFTER encoding.
    a.mood.valence = -0.99
    a.mood.discrete["sadness"] = 0.99
    # The stored affect_tag must NOT have moved.
    assert ev.affect_tag == affect_at_encode


def test_self_monitor_event_survives_save_load_cycle(tmp_path: Path):
    """E5 ↔ E6: events encoded by self_monitor persist through a process hop."""
    cfg = load_config(PRESET)
    store_v1 = AnimaStore("e6-roundtrip", root=tmp_path)
    a1 = Anima(cfg, llm=FakeAdapter(), store=store_v1, autosave_every=999)
    a1.respond("remember this")
    a1.save()
    encoded_id = a1.episodic_store.events[-1].id

    store_v2 = AnimaStore("e6-roundtrip", root=tmp_path)
    a2 = Anima(cfg, llm=FakeAdapter(), store=store_v2)
    assert len(a2.episodic_store.events) == 1
    assert a2.episodic_store.events[0].id == encoded_id
    assert "remember this" in a2.episodic_store.events[0].full_content
