"""Unit tests for the memory_retrieval subsystem (E2, Phase 2).

Covers:
  - Empty-store and k=0 short-circuits (no LLM call)
  - Top-k selection by combined ranker score
  - Mood-congruence: positive mood prefers positive-affect events
  - mark_retrieved is called for every returned id
  - Schema-relevance boosts events whose content contains an active schema string
  - render() formats the empty and non-empty blocks correctly
"""

from __future__ import annotations

import datetime as dt

import pytest

from anima.config import load_config
from anima.llm import make_adapter
from anima.state.episodic import (
    _RETRIEVAL_THRESHOLD,
    AffectTag,
    EpisodicEvent,
    EpisodicStore,
)
from anima.state.mood import MoodVector
from anima.state.self_model import SelfModel
from anima.subsystems.memory_retrieval import MemoryRetrieval, RetrievedMemory
from anima.subsystems.perception import Perception


PRESET = "anima/config/presets/marcus.yaml"


def _percept(salient: list[str] | None = None,
             demands: list[str] | None = None) -> Perception:
    return Perception(
        literal_content="the partner spoke",
        perceived_intent="they want to talk",
        perceived_valence=0.0,
        perceived_demands=list(demands or []),
        salient_features=list(salient or []),
    )


def _episode(eid: str, *, ts: str = "2026-05-01T10:00:00Z",
             summary: str = "an ordinary moment",
             full: str = "user: hi\nself: hi back",
             participants: list[str] | None = None,
             valence: float = 0.0, arousal: float = 0.0, dominance: float = 0.0,
             importance: float = 0.5) -> EpisodicEvent:
    return EpisodicEvent(
        id=eid,
        ts=ts,
        content_summary=summary,
        full_content=full,
        participants=list(participants or ["user", "self"]),
        affect_tag=AffectTag(valence=valence, arousal=arousal, dominance=dominance),
        importance=importance,
    )


def _self_model() -> SelfModel:
    cfg = load_config(PRESET)
    return SelfModel.from_config(cfg)


def test_empty_store_returns_empty_list_and_no_llm_call():
    llm = make_adapter("fake")
    mr = MemoryRetrieval(llm)
    out = mr.run(
        perception=_percept(),
        perception_view="--- perception ---\n--- end perception ---",
        self_model=_self_model(),
        mood=MoodVector(),
        active_schemas=[],
        episodic_store=EpisodicStore(),
        k=3,
    )
    assert out == []
    assert llm.calls == [], "no LLM call should be made on empty store"


def test_k_zero_returns_empty():
    llm = make_adapter("fake")
    store = EpisodicStore()
    store.append(_episode("ev-1"))
    mr = MemoryRetrieval(llm)
    out = mr.run(
        perception=_percept(),
        perception_view="",
        self_model=_self_model(),
        mood=MoodVector(),
        active_schemas=[],
        episodic_store=store,
        k=0,
    )
    assert out == []
    assert llm.calls == []


def test_render_empty():
    mr = MemoryRetrieval(make_adapter("fake"))
    block = mr.render([])
    assert "no relevant memories surface right now" in block
    assert block.startswith("--- memories surfacing ---")
    assert block.endswith("--- end memories ---")


def test_top_k_returns_three_highest_scored():
    """5 events with different attributes; top-3 should reflect ranker priority."""
    llm = make_adapter("fake")
    store = EpisodicStore()
    # Build five events varying in importance, recency, affect.
    store.append(_episode("ev-low", ts="2026-04-01T10:00:00Z",
                          importance=0.1, valence=-0.5))
    store.append(_episode("ev-mid", ts="2026-04-15T10:00:00Z",
                          importance=0.4, valence=0.1))
    store.append(_episode("ev-high-imp", ts="2026-05-01T10:00:00Z",
                          importance=0.95, valence=0.6))
    store.append(_episode("ev-recent", ts="2026-05-13T10:00:00Z",
                          importance=0.7, valence=0.4))
    store.append(_episode("ev-newest", ts="2026-05-14T10:00:00Z",
                          importance=0.6, valence=0.5))

    mr = MemoryRetrieval(llm)
    out = mr.run(
        perception=_percept(),
        perception_view="",
        self_model=_self_model(),
        mood=MoodVector(valence=0.5, arousal=0.0, dominance=0.0),
        active_schemas=[],
        episodic_store=store,
        k=3,
    )
    assert len(out) == 3
    ids = {rm.event.id for rm in out}
    # ev-low (oldest + lowest importance + negative valence under positive mood)
    # should NOT be in the top-3.
    assert "ev-low" not in ids
    # Scores should be in descending order.
    scores = [rm.score for rm in out]
    assert scores == sorted(scores, reverse=True)


def test_mood_congruence_flips_top_rank_with_mood():
    """The mood ranker contributes to top-rank selection: swapping mood
    valence flips which event surfaces first. This is the load-bearing
    property — the ranker isn't decoration."""
    llm = make_adapter("fake")
    store = EpisodicStore()
    store.append(_episode("ev-positive", ts="2026-05-01T10:00:00Z",
                          importance=0.5, valence=0.8))
    store.append(_episode("ev-negative", ts="2026-05-01T10:00:00Z",
                          importance=0.5, valence=-0.8))

    mr = MemoryRetrieval(llm)

    out_pos = mr.run(
        perception=_percept(), perception_view="",
        self_model=_self_model(),
        mood=MoodVector(valence=0.9, arousal=0.0, dominance=0.0),
        active_schemas=[], episodic_store=store, k=2,
    )
    out_neg = mr.run(
        perception=_percept(), perception_view="",
        self_model=_self_model(),
        mood=MoodVector(valence=-0.9, arousal=0.0, dominance=0.0),
        active_schemas=[], episodic_store=store, k=2,
    )

    # Both moods retrieve both events (since k=2 and only 2 events exist)
    assert len(out_pos) == 2 and len(out_neg) == 2
    # Top-1 under positive mood must be the positive-affect event.
    assert out_pos[0].event.id == "ev-positive"
    # Top-1 under negative mood must be the negative-affect event.
    assert out_neg[0].event.id == "ev-negative"
    # Therefore the top ranks FLIPPED — the ranker uses mood, not just first-event.
    assert out_pos[0].event.id != out_neg[0].event.id
    # And within each condition, top-1 outscores top-2.
    assert out_pos[0].score > out_pos[1].score
    assert out_neg[0].score > out_neg[1].score


def test_mark_retrieved_increments_count_for_each_returned():
    llm = make_adapter("fake")
    store = EpisodicStore()
    store.append(_episode("ev-a", ts="2026-05-01T10:00:00Z", importance=0.7))
    store.append(_episode("ev-b", ts="2026-05-02T10:00:00Z", importance=0.6))
    store.append(_episode("ev-c", ts="2026-05-03T10:00:00Z", importance=0.5))

    mr = MemoryRetrieval(llm)
    out = mr.run(
        perception=_percept(),
        perception_view="",
        self_model=_self_model(),
        mood=MoodVector(),
        active_schemas=[],
        episodic_store=store,
        k=3,
    )
    assert len(out) == 3
    for rm in out:
        assert store.get(rm.event.id).retrieval_count == 1, (
            f"{rm.event.id} not marked retrieved"
        )


def test_schema_relevance_boosts_matching_event():
    """An event whose content contains an active-schema substring outscores an
    otherwise-identical event without it."""
    llm = make_adapter("fake")
    store = EpisodicStore()
    # Same timestamp, importance, affect; only difference is schema substring.
    store.append(_episode(
        "ev-with-schema",
        ts="2026-05-01T10:00:00Z",
        importance=0.5, valence=0.0,
        summary="thought about abandonment and family",
        full="user: family stuff\nself: I felt abandonment in that moment",
    ))
    store.append(_episode(
        "ev-without",
        ts="2026-05-01T10:00:00Z",
        importance=0.5, valence=0.0,
        summary="thought about the weather",
        full="user: it's sunny\nself: yeah",
    ))

    mr = MemoryRetrieval(llm)
    out = mr.run(
        perception=_percept(),
        perception_view="",
        self_model=_self_model(),
        mood=MoodVector(),
        active_schemas=["abandonment"],
        episodic_store=store,
        k=2,
    )
    assert out[0].event.id == "ev-with-schema"
    assert out[0].score > out[1].score


def test_render_nonempty_includes_framing_and_reason():
    """Smoke test the render() output structure on real retrieved data."""
    llm = make_adapter("fake")
    store = EpisodicStore()
    store.append(_episode("ev-1", summary="the cat knocked over the vase"))

    mr = MemoryRetrieval(llm)
    out = mr.run(
        perception=_percept(),
        perception_view="",
        self_model=_self_model(),
        mood=MoodVector(),
        active_schemas=[],
        episodic_store=store,
        k=3,
    )
    block = mr.render(out)
    assert "--- memories surfacing ---" in block
    assert "--- end memories ---" in block
    assert "the cat knocked over the vase" in block
    # Framing + reason rendered for the one retrieved memory.
    assert "how I recall it now:" in block
    assert "why it surfaced:" in block


def test_one_llm_call_per_turn_regardless_of_k():
    """The LLM call for retrieval_reason+framing is batched — one call total."""
    llm = make_adapter("fake")
    store = EpisodicStore()
    for i in range(5):
        store.append(_episode(f"ev-{i}", ts=f"2026-05-{i+1:02d}T10:00:00Z"))

    mr = MemoryRetrieval(llm)
    mr.run(
        perception=_percept(),
        perception_view="",
        self_model=_self_model(),
        mood=MoodVector(),
        active_schemas=[],
        episodic_store=store,
        k=3,
    )
    assert len(llm.calls) == 1, f"expected 1 LLM call, got {len(llm.calls)}"
    assert llm.calls[0]["tier"] == "fast"


def test_retrieved_memory_dataclass_shape():
    """Quick structural check on RetrievedMemory."""
    rm = RetrievedMemory(
        event=_episode("ev-x"),
        score=0.5,
        retrieval_reason="r",
        reconstructed_framing="f",
    )
    assert rm.event.id == "ev-x"
    assert rm.score == pytest.approx(0.5)
    assert rm.retrieval_reason == "r"
    assert rm.reconstructed_framing == "f"


# -----------------------------------------------------------------------------
# E4: decay-based retrieval threshold (candidate-pool filter; store not pruned)
# -----------------------------------------------------------------------------


def _now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def test_below_threshold_event_excluded_at_retrieval_but_remains_in_store():
    """An event with importance below `_RETRIEVAL_THRESHOLD` at encode time is
    not surfaced — but the store itself is never pruned. The exclusion is a
    retrieval-time gate."""
    llm = make_adapter("fake")
    now = dt.datetime.now(dt.timezone.utc)
    # Event timestamped 'now' (so age=0, decay=1) but importance below threshold.
    fresh_ts = now.isoformat(timespec="seconds")
    store = EpisodicStore()
    store.append(_episode(
        "ev-dim",
        ts=fresh_ts,
        importance=0.04,  # below _RETRIEVAL_THRESHOLD=0.05
    ))

    mr = MemoryRetrieval(llm)
    out = mr.run(
        perception=_percept(),
        perception_view="",
        self_model=_self_model(),
        mood=MoodVector(),
        active_schemas=[],
        episodic_store=store,
        k=3,
    )
    # Nothing surfaced — and so no LLM call needed.
    assert out == []
    assert llm.calls == []
    # The store still has the event — exclusion is retrieval-time only.
    assert store.get("ev-dim") is not None
    assert store.get("ev-dim").importance == pytest.approx(0.04)
    assert len(store.list_recent(10)) == 1


def test_old_event_decayed_below_threshold_is_excluded():
    """An event with high importance but very old timestamp falls below the
    decay threshold and is excluded from retrieval."""
    llm = make_adapter("fake")
    now = dt.datetime.now(dt.timezone.utc)
    year_old = (now - dt.timedelta(days=365)).isoformat(timespec="seconds")
    store = EpisodicStore()
    store.append(_episode(
        "ev-ancient",
        ts=year_old,
        importance=0.9,  # high importance but 365 days old
    ))
    # Sanity: confirm precondition.
    assert store.get("ev-ancient").importance_decayed(_now_iso()) < _RETRIEVAL_THRESHOLD

    mr = MemoryRetrieval(llm)
    out = mr.run(
        perception=_percept(),
        perception_view="",
        self_model=_self_model(),
        mood=MoodVector(),
        active_schemas=[],
        episodic_store=store,
        k=3,
    )
    assert out == []
    assert llm.calls == []
    # Store still has it.
    assert store.get("ev-ancient") is not None


def test_above_threshold_event_with_retrieval_boost_is_included():
    """Sanity check: a moderate-importance event with retrieval_count=10
    (capped boost) is well above threshold and surfaces normally."""
    llm = make_adapter("fake")
    now = dt.datetime.now(dt.timezone.utc)
    fresh_ts = now.isoformat(timespec="seconds")
    store = EpisodicStore()
    ev = _episode("ev-loved", ts=fresh_ts, importance=0.5)
    store.append(ev)
    # Pre-bump retrieval count to 10 (capped boost = 1.5).
    for _ in range(10):
        store.mark_retrieved("ev-loved")
    assert store.get("ev-loved").retrieval_count == 10
    # Decayed importance: 0.5 * 1.0 * 1.5 = 0.75, well above threshold.
    assert store.get("ev-loved").importance_decayed(_now_iso()) >= _RETRIEVAL_THRESHOLD

    mr = MemoryRetrieval(llm)
    out = mr.run(
        perception=_percept(),
        perception_view="",
        self_model=_self_model(),
        mood=MoodVector(),
        active_schemas=[],
        episodic_store=store,
        k=3,
    )
    assert len(out) == 1
    assert out[0].event.id == "ev-loved"


def test_mixed_pool_only_surviving_events_surface():
    """With a mix of fresh-high-importance and old-low-importance events, only
    the survivors of the threshold filter make it into the retrieved list."""
    llm = make_adapter("fake")
    now = dt.datetime.now(dt.timezone.utc)
    fresh_ts = now.isoformat(timespec="seconds")
    old_ts = (now - dt.timedelta(days=365)).isoformat(timespec="seconds")
    store = EpisodicStore()
    store.append(_episode("ev-fresh-A", ts=fresh_ts, importance=0.6))
    store.append(_episode("ev-fresh-B", ts=fresh_ts, importance=0.5))
    store.append(_episode("ev-faded",   ts=old_ts,   importance=0.9))  # decays out
    store.append(_episode("ev-dim",     ts=fresh_ts, importance=0.02))  # below thresh

    mr = MemoryRetrieval(llm)
    out = mr.run(
        perception=_percept(),
        perception_view="",
        self_model=_self_model(),
        mood=MoodVector(),
        active_schemas=[],
        episodic_store=store,
        k=5,
    )
    ids = {rm.event.id for rm in out}
    assert ids == {"ev-fresh-A", "ev-fresh-B"}
    # The store still has all four events — gating is retrieval-time only.
    assert len(store.events) == 4
