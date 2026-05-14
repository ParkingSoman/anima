"""Unit tests for :mod:`anima.persistence.store` (E5).

Coverage:
  - fresh store: load() returns None when nothing is on disk
  - round-trip: save() then load() returns structurally-equal §5.1 + §5.2
  - atomic write: a stray .tmp sibling is invisible to load()
  - session transcripts: save with session_id writes a per-session file
  - prior sessions preserved: saving session B does not clobber session A
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from anima.persistence.store import AnimaStore, AnimaStoreSnapshot


def _sample_snapshot() -> AnimaStoreSnapshot:
    return AnimaStoreSnapshot(
        episodic_events=[
            {
                "id": "ev-1",
                "ts": "2026-05-14T15:23:01Z",
                "content_summary": "user mentioned cousin Sarah",
                "full_content": "user: my cousin sarah came over",
                "participants": ["user", "self"],
                "affect_tag": {"valence": 0.2, "arousal": 0.1, "dominance": 0.0, "discrete": {}},
                "importance": 0.5,
                "retrieval_count": 0,
                "links": [],
            }
        ],
        action_history=[{"user_msg": "hi", "response": "hello"}],
        self_model={
            "kernel": {
                "name": "Marcus",
                "one_line": "warm forty-something",
                "iwm_of_self": "secure",
                "iwm_of_others": "trustworthy",
                "role": "teacher",
                "age": 47,
                "culture": "mid-atlantic US",
                "formative_events": ["father's illness"],
                "family_of_origin": "small town",
            },
            "believed_traits": {"openness": 0.7},
            "believed_values": ["benevolence"],
            "current_concerns": ["the new term"],
            "current_hopes": [],
            "current_fears": [],
            "held_opinions": {},
            "ongoing_life_projects": ["the new term"],
            "provenance": [],
        },
        semantic_facts=[
            {"id": "f1", "ts": "2026-05-14T00:00:00Z", "claim": "user works in real estate",
             "confidence": 0.8, "sources": ["ev-1"]}
        ],
        relations={
            "user": {
                "name": "user",
                "attachment_quality_inferred": "warm",
                "beliefs_about_person": ["cares about family"],
                "predicted_intents": [],
                "surprise_history": [],
            }
        },
        mood={"valence": 0.2, "arousal": 0.0, "dominance": 0.1, "discrete": {}},
        drives={"activations": {"care": 0.6, "play": 0.3}},
        conversation_history=[
            {"role": "user", "content": "hi"},
            {"role": "assistant", "content": "hello"},
        ],
        current_session_id=None,
    )


def test_load_returns_none_when_no_state(tmp_path: Path):
    store = AnimaStore("fresh", root=tmp_path)
    assert store.load() is None


def test_save_then_load_roundtrip(tmp_path: Path):
    store = AnimaStore("alpha", root=tmp_path)
    snap = _sample_snapshot()
    store.save(snap)

    loaded = store.load()
    assert loaded is not None

    # §5.1 behavioral record
    assert loaded.episodic_events == snap.episodic_events
    assert loaded.action_history == snap.action_history

    # §5.2 interpreted state
    assert loaded.self_model == snap.self_model
    assert loaded.semantic_facts == snap.semantic_facts
    assert loaded.relations == snap.relations
    assert loaded.mood == snap.mood
    assert loaded.drives == snap.drives

    # session bookkeeping
    assert loaded.conversation_history == snap.conversation_history


def test_save_creates_two_separate_files(tmp_path: Path):
    """§5.1 and §5.2 must live in distinct files — researcher-auditability."""
    store = AnimaStore("beta", root=tmp_path)
    store.save(_sample_snapshot())

    assert store.behavioral_path.exists()
    assert store.interpreted_path.exists()

    # Behavioral file has §5.1 keys, NOT §5.2.
    with store.behavioral_path.open() as f:
        beh = json.load(f)
    assert "episodic_events" in beh
    assert "action_history" in beh
    assert "self_model" not in beh
    assert "mood" not in beh

    # Interpreted file has §5.2 keys, NOT §5.1.
    with store.interpreted_path.open() as f:
        interp = json.load(f)
    assert "self_model" in interp
    assert "mood" in interp
    assert "drives" in interp
    assert "episodic_events" not in interp


def test_atomic_write_ignores_stray_tmp(tmp_path: Path):
    """A leftover .tmp sibling (e.g. from a crash mid-write) must not be read
    as the canonical state. load() reads the replaced file, the tmp is junk."""
    store = AnimaStore("gamma", root=tmp_path)
    snap = _sample_snapshot()
    store.save(snap)

    # Inject a corrupt tmp sibling next to the interpreted file.
    bad_tmp = store.interpreted_path.parent / (store.interpreted_path.name + ".bogus.tmp")
    bad_tmp.write_text("{not valid json")

    loaded = store.load()
    assert loaded is not None
    # The canonical file (replaced via os.replace) is what got read.
    assert loaded.self_model == snap.self_model


def test_save_with_session_id_writes_transcript(tmp_path: Path):
    store = AnimaStore("delta", root=tmp_path)
    snap = _sample_snapshot()
    snap.conversation_history = [
        {"role": "user", "content": "monday msg"},
        {"role": "assistant", "content": "monday reply"},
    ]
    store.save(snap, session_id="session-monday")

    transcript_file = store.transcripts_dir / "session-monday.json"
    assert transcript_file.exists()
    payload = json.loads(transcript_file.read_text())
    assert payload["session_id"] == "session-monday"
    assert payload["messages"] == snap.conversation_history

    loaded = store.load()
    assert loaded is not None
    assert "session-monday" in loaded.transcripts_by_session
    assert loaded.transcripts_by_session["session-monday"] == snap.conversation_history


def test_saving_new_session_preserves_prior_sessions(tmp_path: Path):
    """Each session's transcript is its own file. Saving session B must not
    clobber session A's transcript — append-only behavioral-record semantics."""
    store = AnimaStore("epsilon", root=tmp_path)
    snap = _sample_snapshot()

    snap.conversation_history = [{"role": "user", "content": "monday"}]
    store.save(snap, session_id="session-A")

    snap.conversation_history = [{"role": "user", "content": "wednesday"}]
    store.save(snap, session_id="session-B")

    a_path = store.transcripts_dir / "session-A.json"
    b_path = store.transcripts_dir / "session-B.json"
    assert a_path.exists() and b_path.exists()

    a_payload = json.loads(a_path.read_text())
    b_payload = json.loads(b_path.read_text())
    assert a_payload["messages"] == [{"role": "user", "content": "monday"}]
    assert b_payload["messages"] == [{"role": "user", "content": "wednesday"}]

    loaded = store.load()
    assert loaded is not None
    assert set(loaded.transcripts_by_session) == {"session-A", "session-B"}


def test_save_overwrites_full_behavioral_record(tmp_path: Path):
    """Caller is responsible for load-then-mutate-then-save semantics. The
    save() writes the FULL current behavioral record, so adding to the
    snapshot and saving again must reflect the new state on disk."""
    store = AnimaStore("zeta", root=tmp_path)
    snap = _sample_snapshot()
    store.save(snap)

    loaded = store.load()
    assert loaded is not None
    loaded.episodic_events.append({
        "id": "ev-2",
        "ts": "2026-05-14T16:00:00Z",
        "content_summary": "next",
        "full_content": "user: another turn",
        "participants": ["user", "self"],
        "affect_tag": {"valence": 0.0, "arousal": 0.0, "dominance": 0.0, "discrete": {}},
        "importance": 0.3,
        "retrieval_count": 0,
        "links": [],
    })
    store.save(loaded)

    reloaded = store.load()
    assert reloaded is not None
    assert len(reloaded.episodic_events) == 2
    assert reloaded.episodic_events[1]["id"] == "ev-2"


def test_root_path_is_per_anima_namespaced(tmp_path: Path):
    """Two Animas with different names share the same root but get their own
    subdirectories — no cross-contamination."""
    a = AnimaStore("marcus", root=tmp_path)
    b = AnimaStore("elena", root=tmp_path)
    a.save(_sample_snapshot())
    assert a.dir.exists()
    assert b.load() is None
    assert not b.dir.exists() or not (b.dir / "interpreted.json").exists()
