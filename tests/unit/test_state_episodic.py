"""Unit tests for the episodic memory scaffolding. No LLM calls.

Covers construction, listing, filtering, retrieval bookkeeping, JSON
round-trip, and the affect-snapshot independence property.
"""

from __future__ import annotations

import pytest

from anima.state.episodic import AffectTag, EpisodicEvent, EpisodicStore
from anima.state.mood import MoodVector


def _make_event(
    eid: str = "ev-1",
    ts: str = "2026-05-14T15:23:01Z",
    summary: str = "user mentioned their cousin Sarah",
    full: str = "user: my cousin sarah came over\nself: oh, that's lovely",
    participants: list[str] | None = None,
    valence: float = 0.2,
    importance: float = 0.5,
) -> EpisodicEvent:
    return EpisodicEvent(
        id=eid,
        ts=ts,
        content_summary=summary,
        full_content=full,
        participants=list(participants or ["user", "self"]),
        affect_tag=AffectTag(valence=valence, arousal=0.1, dominance=0.0, discrete={"joy": 0.4}),
        importance=importance,
    )


def test_store_empty():
    store = EpisodicStore()
    assert store.list_recent() == []
    assert store.get("nope") is None
    assert store.filter_by() == []


def test_append_and_get():
    store = EpisodicStore()
    ev = _make_event()
    store.append(ev)
    assert store.get("ev-1") is ev
    assert store.list_recent(10) == [ev]


def test_append_duplicate_id_rejected():
    store = EpisodicStore()
    store.append(_make_event(eid="ev-1"))
    with pytest.raises(ValueError):
        store.append(_make_event(eid="ev-1"))


def test_list_recent_orders_newest_first_and_limits():
    store = EpisodicStore()
    store.append(_make_event(eid="ev-a", ts="2026-05-14T10:00:00Z"))
    store.append(_make_event(eid="ev-b", ts="2026-05-14T12:00:00Z"))
    store.append(_make_event(eid="ev-c", ts="2026-05-14T11:00:00Z"))
    recent = store.list_recent(2)
    assert [e.id for e in recent] == ["ev-b", "ev-c"]


def test_filter_by_participants():
    store = EpisodicStore()
    store.append(_make_event(eid="ev-a", participants=["user", "self"]))
    store.append(_make_event(eid="ev-b", participants=["user", "self", "Sarah"]))
    only_sarah = store.filter_by(participants=["Sarah"])
    assert [e.id for e in only_sarah] == ["ev-b"]
    # user+self matches both (subset semantics)
    both = store.filter_by(participants=["user", "self"])
    assert {e.id for e in both} == {"ev-a", "ev-b"}


def test_filter_by_time_window():
    store = EpisodicStore()
    store.append(_make_event(eid="ev-a", ts="2026-05-14T10:00:00Z"))
    store.append(_make_event(eid="ev-b", ts="2026-05-14T12:00:00Z"))
    store.append(_make_event(eid="ev-c", ts="2026-05-14T14:00:00Z"))
    mid = store.filter_by(since="2026-05-14T11:00:00Z", until="2026-05-14T13:00:00Z")
    assert [e.id for e in mid] == ["ev-b"]


def test_filter_by_keywords_AND_and_case_insensitive():
    store = EpisodicStore()
    store.append(_make_event(
        eid="ev-a",
        summary="user mentioned their cousin SARAH",
        full="user: my cousin came by\nself: that's lovely",
    ))
    store.append(_make_event(
        eid="ev-b",
        summary="user mentioned the weather",
        full="user: it's raining\nself: yeah",
    ))
    hit = store.filter_by(topic_keywords=["sarah", "COUSIN"])
    assert [e.id for e in hit] == ["ev-a"]
    # Match crosses summary + full_content fields: keyword can come from either.
    miss = store.filter_by(topic_keywords=["sarah", "weather"])
    assert miss == []


def test_mark_retrieved_increments():
    store = EpisodicStore()
    store.append(_make_event(eid="ev-1"))
    assert store.get("ev-1").retrieval_count == 0
    store.mark_retrieved("ev-1")
    store.mark_retrieved("ev-1")
    assert store.get("ev-1").retrieval_count == 2


def test_mark_retrieved_unknown_id_raises():
    store = EpisodicStore()
    with pytest.raises(KeyError):
        store.mark_retrieved("nope")


def test_json_roundtrip():
    store = EpisodicStore()
    store.append(_make_event(eid="ev-a", ts="2026-05-14T10:00:00Z"))
    store.append(_make_event(eid="ev-b", ts="2026-05-14T12:00:00Z", valence=-0.3))
    store.mark_retrieved("ev-a")
    data = store.to_jsonable()
    restored = EpisodicStore.from_jsonable(data)
    assert restored.to_jsonable() == data
    assert restored.get("ev-a").retrieval_count == 1
    assert restored.get("ev-b").affect_tag.valence == pytest.approx(-0.3)


def test_affect_tag_from_mood_snapshots_and_is_independent():
    mv = MoodVector(valence=0.4, arousal=-0.2, dominance=0.1, discrete={"joy": 0.5})
    tag = AffectTag.from_mood(mv)
    # mutate the live mood; the tag should not move
    mv.valence = -0.9
    mv.discrete["joy"] = 0.0
    mv.discrete["fear"] = 0.7
    assert tag.valence == pytest.approx(0.4)
    assert tag.arousal == pytest.approx(-0.2)
    assert tag.dominance == pytest.approx(0.1)
    assert tag.discrete == {"joy": 0.5}


def test_affect_tag_frozen():
    tag = AffectTag(valence=0.0, arousal=0.0, dominance=0.0)
    with pytest.raises(Exception):
        tag.valence = 0.5  # frozen dataclass: should raise FrozenInstanceError
