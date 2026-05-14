"""Episodic memory store (§5.1 of the master plan).

A flat list of events the Anima has lived through. Each event carries its own
affect tag, snapshotted at encode time — the affect of *being there*, not the
affect of recalling later. The retrieval subsystem (E2) reads from this; the
decay / affect-congruence logic (E4) writes the access bookkeeping. This file
is data-structures only: append, get, list, filter, mark, and JSON I/O.

One Python process, in-memory list. No DB, no index. Phase 2 is small.
"""

from __future__ import annotations

import datetime
import math
from dataclasses import dataclass, field
from typing import Any

from anima.state.mood import MoodVector


# Decay constants (E4). Tunable; module-level for ease of experimentation.
# importance_decayed = importance * exp(-age_days / time_constant) * retrieval_boost
# time_constant=30d => half-life ~21d. retrieval_boost rewards repeated recall
# (Hebbian: "what fires together wires together"), bounded so it stays sane.
_DECAY_TIME_CONSTANT_DAYS = 30.0
_RETRIEVAL_BOOST_PER_HIT = 0.1
_MAX_RETRIEVAL_BOOST = 1.5
# Below this decayed importance, the retrieval ranker excludes the event from
# its candidate pool. Set at the retrieval layer, NOT applied to the store.
_RETRIEVAL_THRESHOLD = 0.05


def _clip(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def _parse_iso(ts: str) -> datetime.datetime:
    """Parse an ISO-8601 timestamp string, accepting trailing 'Z' as +00:00."""
    if ts.endswith("Z"):
        ts = ts[:-1] + "+00:00"
    return datetime.datetime.fromisoformat(ts)


@dataclass(frozen=True)
class AffectTag:
    """A frozen snapshot of affective state at the moment an event was encoded.

    Frozen rather than a reference to MoodVector because the live mood drifts;
    the *felt quality of that moment* should not drift with it.
    """
    valence: float = 0.0       # [-1, 1]
    arousal: float = 0.0       # [-1, 1]
    dominance: float = 0.0     # [-1, 1]
    discrete: dict[str, float] = field(default_factory=dict)  # emotion -> strength in [0,1]

    @classmethod
    def from_mood(cls, mv: MoodVector) -> "AffectTag":
        """Snapshot a MoodVector. The returned tag does not share state with mv."""
        return cls(
            valence=_clip(mv.valence, -1.0, 1.0),
            arousal=_clip(mv.arousal, -1.0, 1.0),
            dominance=_clip(mv.dominance, -1.0, 1.0),
            discrete=dict(mv.discrete),  # copy
        )

    def to_jsonable(self) -> dict[str, Any]:
        return {
            "valence": self.valence,
            "arousal": self.arousal,
            "dominance": self.dominance,
            "discrete": dict(self.discrete),
        }

    @classmethod
    def from_jsonable(cls, data: dict[str, Any]) -> "AffectTag":
        return cls(
            valence=float(data.get("valence", 0.0)),
            arousal=float(data.get("arousal", 0.0)),
            dominance=float(data.get("dominance", 0.0)),
            discrete=dict(data.get("discrete", {})),
        )


@dataclass
class EpisodicEvent:
    """One thing that happened in the Anima's life.

    Typically a turn pair (user msg + Anima reply), but the schema is general
    enough to hold compound events authored by consolidation (Phase 4).
    """
    id: str                                       # e.g. "ev-2026-05-14T15-23-01-abcd1234"
    ts: str                                       # ISO-8601 UTC
    content_summary: str                          # one-line gist
    full_content: str                             # the full text
    participants: list[str]                       # e.g. ["user", "self"]
    affect_tag: AffectTag                         # frozen at encode time
    importance: float                             # [0, 1]
    retrieval_count: int = 0
    links: list[str] = field(default_factory=list)  # ids of related events

    def importance_decayed(self, now: str | None = None) -> float:
        """Time- and retrieval-modulated importance for the retrieval ranker.

        Decay is exponential with time-constant `_DECAY_TIME_CONSTANT_DAYS`.
        Retrieval count provides a bounded Hebbian boost so memories that are
        recalled often resist decay. Result clamped to [0, 1] — high importance
        with high retrieval_count cannot exceed the original [0, 1] range.

        Args:
            now: ISO-8601 timestamp string. If None, uses current UTC time.
        """
        if now is None:
            now_dt = datetime.datetime.now(datetime.timezone.utc)
        else:
            now_dt = _parse_iso(now)
        then_dt = _parse_iso(self.ts)
        age_days = max(0.0, (now_dt - then_dt).total_seconds() / 86400.0)
        time_factor = math.exp(-age_days / _DECAY_TIME_CONSTANT_DAYS)
        retrieval_boost = min(
            _MAX_RETRIEVAL_BOOST,
            1.0 + _RETRIEVAL_BOOST_PER_HIT * max(0, self.retrieval_count),
        )
        return _clip(self.importance * time_factor * retrieval_boost, 0.0, 1.0)

    def to_jsonable(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "ts": self.ts,
            "content_summary": self.content_summary,
            "full_content": self.full_content,
            "participants": list(self.participants),
            "affect_tag": self.affect_tag.to_jsonable(),
            "importance": self.importance,
            "retrieval_count": self.retrieval_count,
            "links": list(self.links),
        }

    @classmethod
    def from_jsonable(cls, data: dict[str, Any]) -> "EpisodicEvent":
        return cls(
            id=str(data["id"]),
            ts=str(data["ts"]),
            content_summary=str(data["content_summary"]),
            full_content=str(data["full_content"]),
            participants=list(data.get("participants", [])),
            affect_tag=AffectTag.from_jsonable(data.get("affect_tag", {})),
            importance=float(data.get("importance", 0.0)),
            retrieval_count=int(data.get("retrieval_count", 0)),
            links=list(data.get("links", [])),
        )


@dataclass
class EpisodicStore:
    """Append-only list of EpisodicEvents with simple filtering.

    No decay, no affect-congruent retrieval — that's E4. No vector index —
    Phase 2 is small enough for linear scan.
    """
    events: list[EpisodicEvent] = field(default_factory=list)
    _by_id: dict[str, EpisodicEvent] = field(default_factory=dict, repr=False)

    def append(self, event: EpisodicEvent) -> None:
        if event.id in self._by_id:
            raise ValueError(f"duplicate episodic event id: {event.id}")
        self.events.append(event)
        self._by_id[event.id] = event

    def get(self, event_id: str) -> EpisodicEvent | None:
        return self._by_id.get(event_id)

    def list_recent(self, n: int = 10) -> list[EpisodicEvent]:
        """Most-recent first by ts (lexicographic on ISO-8601 strings is correct)."""
        return sorted(self.events, key=lambda e: e.ts, reverse=True)[:n]

    def filter_by(
        self,
        participants: list[str] | None = None,
        since: str | None = None,
        until: str | None = None,
        topic_keywords: list[str] | None = None,
    ) -> list[EpisodicEvent]:
        """Return events matching every supplied criterion (AND semantics).

        - participants: event must contain every listed participant
        - since / until: ISO-8601 lex-comparable bounds, inclusive
        - topic_keywords: event's summary OR full_content (lowercased) must
          contain every keyword (lowercased substring match)
        """
        results: list[EpisodicEvent] = []
        kw_lower = [k.lower() for k in (topic_keywords or [])]
        req_parts = set(participants or [])
        for e in self.events:
            if req_parts and not req_parts.issubset(set(e.participants)):
                continue
            if since is not None and e.ts < since:
                continue
            if until is not None and e.ts > until:
                continue
            if kw_lower:
                hay = (e.content_summary + " " + e.full_content).lower()
                if not all(k in hay for k in kw_lower):
                    continue
            results.append(e)
        return results

    def mark_retrieved(self, event_id: str) -> None:
        ev = self._by_id.get(event_id)
        if ev is None:
            raise KeyError(f"no episodic event with id {event_id}")
        ev.retrieval_count += 1

    def to_jsonable(self) -> dict[str, Any]:
        return {"events": [e.to_jsonable() for e in self.events]}

    @classmethod
    def from_jsonable(cls, data: dict[str, Any]) -> "EpisodicStore":
        store = cls()
        for ed in data.get("events", []):
            store.append(EpisodicEvent.from_jsonable(ed))
        return store
