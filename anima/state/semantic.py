"""Semantic memory store (§5.1 of the master plan).

Claims the Anima believes to be true about the world / the user / itself, each
tagged with a confidence and a list of supporting episodic-event ids. The
retrieval subsystem (E2) reads these; the consolidation process (E3) writes
them out of episodic patterns.

No knowledge graph, no embeddings — just claim strings + confidence. Phase 2
keeps it small on purpose.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class SemanticFact:
    id: str
    ts: str                                          # ISO-8601 UTC; when this claim was authored
    claim: str                                       # "The user works in real estate"
    confidence: float                                # [0, 1]
    sources: list[str] = field(default_factory=list)  # episodic event ids

    def to_jsonable(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "ts": self.ts,
            "claim": self.claim,
            "confidence": self.confidence,
            "sources": list(self.sources),
        }

    @classmethod
    def from_jsonable(cls, data: dict[str, Any]) -> "SemanticFact":
        return cls(
            id=str(data["id"]),
            ts=str(data["ts"]),
            claim=str(data["claim"]),
            confidence=float(data.get("confidence", 0.0)),
            sources=list(data.get("sources", [])),
        )


@dataclass
class SemanticStore:
    facts: list[SemanticFact] = field(default_factory=list)
    _by_id: dict[str, SemanticFact] = field(default_factory=dict, repr=False)

    def append(self, fact: SemanticFact) -> None:
        if fact.id in self._by_id:
            raise ValueError(f"duplicate semantic fact id: {fact.id}")
        self.facts.append(fact)
        self._by_id[fact.id] = fact

    def get(self, fact_id: str) -> SemanticFact | None:
        return self._by_id.get(fact_id)

    def list_all(self) -> list[SemanticFact]:
        return list(self.facts)

    def filter_by(
        self,
        min_confidence: float | None = None,
        topic_keywords: list[str] | None = None,
    ) -> list[SemanticFact]:
        """AND semantics. Empty criteria returns everything."""
        kw_lower = [k.lower() for k in (topic_keywords or [])]
        results: list[SemanticFact] = []
        for f in self.facts:
            if min_confidence is not None and f.confidence < min_confidence:
                continue
            if kw_lower:
                hay = f.claim.lower()
                if not all(k in hay for k in kw_lower):
                    continue
            results.append(f)
        return results

    def to_jsonable(self) -> dict[str, Any]:
        return {"facts": [f.to_jsonable() for f in self.facts]}

    @classmethod
    def from_jsonable(cls, data: dict[str, Any]) -> "SemanticStore":
        store = cls()
        for fd in data.get("facts", []):
            store.append(SemanticFact.from_jsonable(fd))
        return store
