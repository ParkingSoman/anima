"""Integration test: the full turn loop with memory retrieval wired in.

Two cases:
  - Empty episodic store: retrieval_view should be the "no memories" block,
    and TurnTrace.retrieved should be [].
  - Pre-populated store: retrieval_view should contain memory content, and
    TurnTrace.retrieved should hold {id, score, retrieval_reason,
    reconstructed_framing} entries.
"""

from __future__ import annotations

from pathlib import Path

from anima.config import load_config
from anima.core import Anima
from anima.llm.fake_adapter import FakeAdapter
from anima.state.episodic import AffectTag, EpisodicEvent


PRESET = Path(__file__).resolve().parents[2] / "anima" / "config" / "presets" / "marcus.yaml"


def _episode(eid: str, ts: str, summary: str,
             valence: float = 0.0, importance: float = 0.5) -> EpisodicEvent:
    return EpisodicEvent(
        id=eid,
        ts=ts,
        content_summary=summary,
        full_content=f"user: {summary}\nself: noted",
        participants=["user", "self"],
        affect_tag=AffectTag(valence=valence, arousal=0.0, dominance=0.0),
        importance=importance,
    )


def test_turn_runs_with_empty_store_and_records_no_memories():
    cfg = load_config(PRESET)
    fake = FakeAdapter()
    a = Anima(cfg, llm=fake)
    assert a.episodic_store.events == []

    reply, trace = a.respond("How have you been?")
    assert reply

    # No memories were available, so retrieved is empty.
    assert trace.retrieved == []

    # The "no memories" block should be visible in the downstream subsystem
    # prompts (appraisal, monologue, response) — that's the proof that the
    # retrieval_view threaded through.
    needle = "no relevant memories surface right now"
    saw_downstream_with_block = False
    for call in fake.calls:
        sys_prompt = call["system"]
        if any(tag in sys_prompt for tag in
               ["APPRAISAL subsystem", "INNER MONOLOGUE subsystem",
                "RESPONSE GENERATION subsystem"]):
            assert needle in sys_prompt, (
                f"retrieval_view not threaded into downstream prompt: "
                f"{sys_prompt[:200]}"
            )
            saw_downstream_with_block = True
    assert saw_downstream_with_block, "no downstream subsystem prompt observed"


def test_turn_with_populated_store_surfaces_memories():
    cfg = load_config(PRESET)
    fake = FakeAdapter()
    a = Anima(cfg, llm=fake)

    # Append three events directly to the store.
    a.episodic_store.append(_episode("ev-a", "2026-05-01T10:00:00Z",
                                     "a conversation about work",
                                     valence=0.2, importance=0.7))
    a.episodic_store.append(_episode("ev-b", "2026-05-05T10:00:00Z",
                                     "a quiet evening alone",
                                     valence=-0.1, importance=0.4))
    a.episodic_store.append(_episode("ev-c", "2026-05-10T10:00:00Z",
                                     "an argument with a sibling",
                                     valence=-0.5, importance=0.8))

    reply, trace = a.respond("How have you been?")
    assert reply

    # retrieved should contain entries with the expected shape.
    assert len(trace.retrieved) == 3
    for entry in trace.retrieved:
        assert set(entry.keys()) >= {"id", "score", "retrieval_reason",
                                      "reconstructed_framing"}
        assert isinstance(entry["score"], float)
        assert 0.0 <= entry["score"] <= 1.0
        assert entry["id"] in {"ev-a", "ev-b", "ev-c"}

    # retrieval_count was incremented on every retrieved id.
    for eid in {e["id"] for e in trace.retrieved}:
        assert a.episodic_store.get(eid).retrieval_count == 1

    # The retrieved content should have leaked into the downstream subsystem
    # prompts (summary text from at least one event present in each).
    summaries = {"a conversation about work", "a quiet evening alone",
                 "an argument with a sibling"}
    for call in fake.calls:
        sys_prompt = call["system"]
        if any(tag in sys_prompt for tag in
               ["APPRAISAL subsystem", "INNER MONOLOGUE subsystem",
                "RESPONSE GENERATION subsystem"]):
            assert any(s in sys_prompt for s in summaries), (
                "no episodic summary content found in downstream prompt"
            )


def test_existing_subsystem_tiers_still_balanced():
    """Sanity: the retrieval LLM call is fast-tier; existing tier counts
    (perception fast, appraisal fast, monologue strong, response strong) must
    still hold. With memory retrieval added we now expect >=3 fast calls."""
    cfg = load_config(PRESET)
    fake = FakeAdapter()
    a = Anima(cfg, llm=fake)
    # Populate so retrieval actually fires its LLM call.
    a.episodic_store.append(_episode("ev-a", "2026-05-01T10:00:00Z", "x"))

    a.respond("hi")
    tiers = [c["tier"] for c in fake.calls]
    assert tiers.count("fast") >= 3, f"expected >=3 fast calls, got {tiers}"
    assert tiers.count("strong") >= 2, f"expected >=2 strong calls, got {tiers}"
