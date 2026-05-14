"""Relational schemas — the Anima's model of specific people (§5.2 / §6).

For each known person (typically just "user" in Phase 2) the Anima stores:
  - inferred attachment quality of the relationship
  - free-text beliefs about the person
  - predictions it has made about their next move
  - a history of how surprised it was when those predictions met reality

The surprise stream is the substrate for theory-of-mind learning (E6): a
running record of "what I expected vs what actually happened" that
consolidation can read to update beliefs.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class PredictedIntent:
    """One stored prediction the Anima made about the user's next move."""
    ts: str
    perceived_input_summary: str   # what the user just said (briefly)
    next_intent_label: str         # categorical, e.g. "share_personal_info", "disagree", "ask_question"
    content_hint: str              # free-text guess at what the user will say next
    confidence: float              # [0, 1]

    def to_jsonable(self) -> dict[str, Any]:
        return {
            "ts": self.ts,
            "perceived_input_summary": self.perceived_input_summary,
            "next_intent_label": self.next_intent_label,
            "content_hint": self.content_hint,
            "confidence": self.confidence,
        }

    @classmethod
    def from_jsonable(cls, data: dict[str, Any]) -> "PredictedIntent":
        return cls(
            ts=str(data["ts"]),
            perceived_input_summary=str(data["perceived_input_summary"]),
            next_intent_label=str(data["next_intent_label"]),
            content_hint=str(data["content_hint"]),
            confidence=float(data.get("confidence", 0.0)),
        )


@dataclass
class SurpriseRecord:
    """One observation: prediction vs actual outcome."""
    ts: str
    predicted_intent: PredictedIntent
    actual_user_msg_summary: str
    surprise_score: float          # [0, 1]; high = prediction wrong
    reason: str = ""               # judge's reasoning if available

    def to_jsonable(self) -> dict[str, Any]:
        return {
            "ts": self.ts,
            "predicted_intent": self.predicted_intent.to_jsonable(),
            "actual_user_msg_summary": self.actual_user_msg_summary,
            "surprise_score": self.surprise_score,
            "reason": self.reason,
        }

    @classmethod
    def from_jsonable(cls, data: dict[str, Any]) -> "SurpriseRecord":
        return cls(
            ts=str(data["ts"]),
            predicted_intent=PredictedIntent.from_jsonable(data["predicted_intent"]),
            actual_user_msg_summary=str(data["actual_user_msg_summary"]),
            surprise_score=float(data.get("surprise_score", 0.0)),
            reason=str(data.get("reason", "")),
        )


@dataclass
class RelationalSchema:
    """The Anima's evolving model of one known person (typically 'user')."""
    name: str                                                          # canonical name
    attachment_quality_inferred: str = "unknown"                       # "warm", "distant", "ambivalent", "unknown"
    beliefs_about_person: list[str] = field(default_factory=list)      # e.g. "they care about their cousin"
    predicted_intents: list[PredictedIntent] = field(default_factory=list)
    surprise_history: list[SurpriseRecord] = field(default_factory=list)

    def last_prediction(self) -> PredictedIntent | None:
        return self.predicted_intents[-1] if self.predicted_intents else None

    def record_prediction(self, p: PredictedIntent) -> None:
        self.predicted_intents.append(p)

    def record_surprise(self, s: SurpriseRecord) -> None:
        self.surprise_history.append(s)

    def render(self) -> str:
        """Short prompt-ready summary. Read by ToM-aware subsystems."""
        beliefs = "; ".join(self.beliefs_about_person) if self.beliefs_about_person else "—"
        last = self.last_prediction()
        last_str = (
            f"({last.next_intent_label}, conf {last.confidence:.2f}): {last.content_hint}"
            if last is not None else "—"
        )
        n_surp = len(self.surprise_history)
        recent_surp = self.surprise_history[-3:]
        if recent_surp:
            avg = sum(s.surprise_score for s in recent_surp) / len(recent_surp)
            surp_str = f"recent avg surprise (last {len(recent_surp)} of {n_surp}): {avg:.2f}"
        else:
            surp_str = "no surprise history yet"
        return (
            f"--- relation: {self.name} ---\n"
            f"inferred attachment quality of relationship: {self.attachment_quality_inferred}\n"
            f"what I currently believe about them: {beliefs}\n"
            f"my last prediction about them: {last_str}\n"
            f"{surp_str}\n"
            f"--- end relation ---"
        )

    def to_jsonable(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "attachment_quality_inferred": self.attachment_quality_inferred,
            "beliefs_about_person": list(self.beliefs_about_person),
            "predicted_intents": [p.to_jsonable() for p in self.predicted_intents],
            "surprise_history": [s.to_jsonable() for s in self.surprise_history],
        }

    @classmethod
    def from_jsonable(cls, data: dict[str, Any]) -> "RelationalSchema":
        return cls(
            name=str(data["name"]),
            attachment_quality_inferred=str(data.get("attachment_quality_inferred", "unknown")),
            beliefs_about_person=list(data.get("beliefs_about_person", [])),
            predicted_intents=[PredictedIntent.from_jsonable(p) for p in data.get("predicted_intents", [])],
            surprise_history=[SurpriseRecord.from_jsonable(s) for s in data.get("surprise_history", [])],
        )


@dataclass
class RelationsStore:
    """Mapping of name -> RelationalSchema. Phase 2 typically has one entry: 'user'."""
    schemas: dict[str, RelationalSchema] = field(default_factory=dict)

    def get_or_create(self, name: str) -> RelationalSchema:
        if name not in self.schemas:
            self.schemas[name] = RelationalSchema(name=name)
        return self.schemas[name]

    def get(self, name: str) -> RelationalSchema | None:
        return self.schemas.get(name)

    def to_jsonable(self) -> dict[str, Any]:
        return {"schemas": {n: s.to_jsonable() for n, s in self.schemas.items()}}

    @classmethod
    def from_jsonable(cls, data: dict[str, Any]) -> "RelationsStore":
        store = cls()
        for n, sd in data.get("schemas", {}).items():
            store.schemas[n] = RelationalSchema.from_jsonable(sd)
        return store
