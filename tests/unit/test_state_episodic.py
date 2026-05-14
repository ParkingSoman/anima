"""Unit tests for the episodic memory scaffolding. No LLM calls.

Covers construction, listing, filtering, retrieval bookkeeping, JSON
round-trip, the affect-snapshot independence property, and (E4) the
importance_decayed function.
"""

from __future__ import annotations

import datetime as dt
import math

import pytest

from anima.state.episodic import (
    _DECAY_TIME_CONSTANT_DAYS,
    _MAX_RETRIEVAL_BOOST,
    _RETRIEVAL_THRESHOLD,
    AffectTag,
    EpisodicEvent,
    EpisodicStore,
)
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


# -----------------------------------------------------------------------------
# E4: decay (importance_decayed)
# -----------------------------------------------------------------------------

_TS = "2026-05-14T12:00:00+00:00"


def _decay_event(*, importance: float = 0.5, retrieval_count: int = 0,
                 ts: str = _TS) -> EpisodicEvent:
    return EpisodicEvent(
        id="dec-1",
        ts=ts,
        content_summary="s",
        full_content="f",
        participants=["user", "self"],
        affect_tag=AffectTag(),
        importance=importance,
        retrieval_count=retrieval_count,
    )


def test_decay_zero_age_returns_importance():
    """When now == event.ts and retrieval_count=0, no decay, no boost."""
    ev = _decay_event(importance=0.7, retrieval_count=0)
    assert ev.importance_decayed(_TS) == pytest.approx(0.7, abs=1e-9)


def test_decay_one_time_constant_is_one_over_e():
    """After 30 days (one time constant), value is importance * exp(-1)."""
    base = dt.datetime.fromisoformat(_TS)
    later = (base + dt.timedelta(days=_DECAY_TIME_CONSTANT_DAYS)).isoformat()
    ev = _decay_event(importance=0.8, retrieval_count=0)
    decayed = ev.importance_decayed(later)
    expected = 0.8 * math.exp(-1.0)
    assert decayed == pytest.approx(expected, abs=1e-6)
    # Sanity: 0.8 * 0.3679 ≈ 0.294
    assert decayed == pytest.approx(0.294, abs=0.01)


def test_decay_after_one_year_is_near_zero():
    base = dt.datetime.fromisoformat(_TS)
    later = (base + dt.timedelta(days=365)).isoformat()
    ev = _decay_event(importance=1.0, retrieval_count=0)
    assert ev.importance_decayed(later) < 1e-4


def test_retrieval_boost_at_five_hits_is_cap_exactly():
    """1 + 0.1*5 = 1.5 — exactly at the cap."""
    ev = _decay_event(importance=0.4, retrieval_count=5)
    # At zero age, only boost applies: 0.4 * 1 * 1.5 = 0.6
    assert ev.importance_decayed(_TS) == pytest.approx(0.6, abs=1e-9)


def test_retrieval_boost_is_capped_at_max():
    """Boost saturates at _MAX_RETRIEVAL_BOOST no matter how many hits."""
    ev_capped = _decay_event(importance=0.4, retrieval_count=5)
    ev_huge = _decay_event(importance=0.4, retrieval_count=100)
    # Both should produce the same result — saturated at the cap.
    assert ev_huge.importance_decayed(_TS) == pytest.approx(
        ev_capped.importance_decayed(_TS), abs=1e-9
    )
    # And that cap is 0.4 * _MAX_RETRIEVAL_BOOST.
    assert ev_huge.importance_decayed(_TS) == pytest.approx(
        0.4 * _MAX_RETRIEVAL_BOOST, abs=1e-9
    )


def test_decay_result_clamped_to_unit_interval():
    """High importance + max retrieval boost still cannot exceed 1.0."""
    ev = _decay_event(importance=1.0, retrieval_count=100)
    # 1.0 * 1.0 * 1.5 = 1.5 → must clamp to 1.0.
    assert ev.importance_decayed(_TS) == pytest.approx(1.0, abs=1e-9)


def test_decay_default_now_uses_current_time():
    """now=None uses current UTC time; an old event has decayed importance < importance."""
    # Event from a year ago (relative to current UTC).
    a_year_ago = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=365)).isoformat(
        timespec="seconds"
    )
    ev = _decay_event(importance=0.9, ts=a_year_ago, retrieval_count=0)
    val = ev.importance_decayed()  # now=None
    assert 0.0 <= val < 0.9
    # And it's quite small after a year.
    assert val < 0.05


def test_decay_negative_age_does_not_amplify():
    """An event ts in the (slight) future shouldn't make decay > importance."""
    base = dt.datetime.fromisoformat(_TS)
    earlier_now = (base - dt.timedelta(days=1)).isoformat()
    ev = _decay_event(importance=0.7, retrieval_count=0)
    # age_days is clamped to >=0, so decay factor stays at 1.0.
    assert ev.importance_decayed(earlier_now) == pytest.approx(0.7, abs=1e-9)


def test_retrieval_threshold_constant_positive():
    """Threshold exists, is small and positive."""
    assert 0.0 < _RETRIEVAL_THRESHOLD < 0.5
