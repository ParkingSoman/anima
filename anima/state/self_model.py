"""The Anima's self-model.

This is what the Anima BELIEVES about itself. It is allowed to diverge from
the configuration and from the behavioral record (§5.2 of the plan). It is
the first-person representation that every subsystem reads when constructing
its prompt — that's the architectural commitment that makes the self
*inhabited* rather than *performed*.

Two regions:
  - kernel  : near-constant. Constitutional. Resists soft revision.
  - soft    : revisable by the offline self-integration process.

The kernel is what allows the Anima to *defend* its self-model under pressure
(adversarial probes, persona-replacement attempts, gaslighting). Defense
mechanisms fire on threats to the kernel.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from anima.config.schema import AnimaConfig


@dataclass
class SelfModelKernel:
    """Constitutional. Set at instantiation; not revised by single conversations.

    The self-model self-reports from these; behaviorally the Anima may or may not
    embody them. The gap between kernel beliefs and behavioral record is the
    self-deception signal that §11.6 probes.
    """
    name: str
    one_line: str
    iwm_of_self: str
    iwm_of_others: str
    role: str
    age: int
    culture: str
    formative_events: list[str] = field(default_factory=list)
    family_of_origin: str = ""

    def to_jsonable(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "one_line": self.one_line,
            "iwm_of_self": self.iwm_of_self,
            "iwm_of_others": self.iwm_of_others,
            "role": self.role,
            "age": self.age,
            "culture": self.culture,
            "formative_events": list(self.formative_events),
            "family_of_origin": self.family_of_origin,
        }

    @classmethod
    def from_jsonable(cls, data: dict[str, Any]) -> "SelfModelKernel":
        return cls(
            name=str(data["name"]),
            one_line=str(data.get("one_line", "")),
            iwm_of_self=str(data.get("iwm_of_self", "")),
            iwm_of_others=str(data.get("iwm_of_others", "")),
            role=str(data.get("role", "")),
            age=int(data.get("age", 0)),
            culture=str(data.get("culture", "")),
            formative_events=list(data.get("formative_events", [])),
            family_of_origin=str(data.get("family_of_origin", "")),
        )


@dataclass
class SelfModel:
    """The full self-representation. Read by every subsystem.

    The kernel is read-only at runtime. `soft` fields are written by the
    self-monitor subsystem (per turn, candidate deltas only) and committed by
    the offline self-integration process (across many sessions, dissonance-
    weighted).
    """
    kernel: SelfModelKernel

    # Soft self-representation. The Anima's CURRENT beliefs about itself, which
    # can drift from its actual trait/behavioral profile.
    believed_traits: dict[str, float] = field(default_factory=dict)        # "I think I am about a 0.7 on conscientiousness"
    believed_values: list[str] = field(default_factory=list)               # ranked, in the Anima's words
    current_concerns: list[str] = field(default_factory=list)              # what is on its mind
    current_hopes: list[str] = field(default_factory=list)
    current_fears: list[str] = field(default_factory=list)
    held_opinions: dict[str, str] = field(default_factory=dict)            # topic -> stance
    ongoing_life_projects: list[str] = field(default_factory=list)

    # Provenance: where the Anima got these beliefs about itself. For research.
    provenance: list[dict] = field(default_factory=list)

    @classmethod
    def from_config(cls, cfg: AnimaConfig) -> "SelfModel":
        """Seed the self-model from the config. CRUCIALLY, this is not the same
        as the config — the Anima sees these as 'who I think I am,' and over
        time, behavior + offline integration may move them.
        """
        kernel = SelfModelKernel(
            name=cfg.biography.name,
            one_line=cfg.biography.one_line,
            iwm_of_self=cfg.attachment.iwm_of_self,
            iwm_of_others=cfg.attachment.iwm_of_others,
            role=cfg.demographics.role,
            age=cfg.demographics.age,
            culture=cfg.demographics.culture,
            formative_events=list(cfg.biography.formative_events),
            family_of_origin=cfg.biography.family_of_origin,
        )

        return cls(
            kernel=kernel,
            believed_traits=cfg.big5.as_dict(),
            believed_values=[name for name, _ in cfg.schwartz.top_k(5)],
            current_concerns=list(cfg.biography.ongoing_life_projects),
            current_hopes=[],
            current_fears=[],
            held_opinions={},
            ongoing_life_projects=list(cfg.biography.ongoing_life_projects),
        )

    # ---------- rendering (the "I am" view consumed by subsystem prompts)

    def render(self) -> str:
        """Render the self-model as a first-person 'who I am, right now' block.
        Every subsystem prompt includes this. This is the architectural lever
        for §7 (self as read-input to every subsystem).
        """
        traits_str = ", ".join(f"{k}={v:.2f}" for k, v in self.believed_traits.items())
        values_str = ", ".join(self.believed_values[:5])
        concerns_str = "; ".join(self.current_concerns) if self.current_concerns else "—"
        hopes_str = "; ".join(self.current_hopes) if self.current_hopes else "—"
        fears_str = "; ".join(self.current_fears) if self.current_fears else "—"
        opinions_str = "\n  ".join(f"on {k}: {v}" for k, v in self.held_opinions.items()) or "—"

        return (
            f"--- WHO I AM (self-model) ---\n"
            f"I am {self.kernel.name}. {self.kernel.one_line}\n"
            f"My role: {self.kernel.role}. My age: {self.kernel.age}. "
            f"Cultural background: {self.kernel.culture}.\n"
            f"How I see myself: {self.kernel.iwm_of_self}\n"
            f"How I see others: {self.kernel.iwm_of_others}\n"
            f"Family of origin: {self.kernel.family_of_origin}\n"
            f"Events that shaped me:\n  - "
            + "\n  - ".join(self.kernel.formative_events)
            + "\n"
            f"My sense of my own traits: {traits_str}\n"
            f"What I value most: {values_str}\n"
            f"What I'm currently working on / preoccupied with: {concerns_str}\n"
            f"What I hope for: {hopes_str}\n"
            f"What I'm afraid of: {fears_str}\n"
            f"Opinions I currently hold:\n  {opinions_str}\n"
            f"--- end self-model ---"
        )

    # ---------- JSON I/O (E5 — cross-session persistence; §5.2 interpreted state)

    def to_jsonable(self) -> dict[str, Any]:
        return {
            "kernel": self.kernel.to_jsonable(),
            "believed_traits": dict(self.believed_traits),
            "believed_values": list(self.believed_values),
            "current_concerns": list(self.current_concerns),
            "current_hopes": list(self.current_hopes),
            "current_fears": list(self.current_fears),
            "held_opinions": dict(self.held_opinions),
            "ongoing_life_projects": list(self.ongoing_life_projects),
            "provenance": [dict(p) for p in self.provenance],
        }

    @classmethod
    def from_jsonable(cls, data: dict[str, Any]) -> "SelfModel":
        return cls(
            kernel=SelfModelKernel.from_jsonable(data["kernel"]),
            believed_traits=dict(data.get("believed_traits", {})),
            believed_values=list(data.get("believed_values", [])),
            current_concerns=list(data.get("current_concerns", [])),
            current_hopes=list(data.get("current_hopes", [])),
            current_fears=list(data.get("current_fears", [])),
            held_opinions=dict(data.get("held_opinions", {})),
            ongoing_life_projects=list(data.get("ongoing_life_projects", [])),
            provenance=[dict(p) for p in data.get("provenance", [])],
        )

    # ---------- candidate deltas (per turn, committed only if non-dissonant)

    def propose_delta(self, kind: str, key: str, value: Any, reason: str) -> None:
        """Self-monitor writes candidate deltas here. The offline self-integration
        process commits them (or rationalizes them, or triggers defenses).
        """
        self.provenance.append(
            {"kind": kind, "key": key, "value": value, "reason": reason, "committed": False}
        )

    def commit_delta(self, idx: int) -> None:
        """Mark a candidate delta as committed and apply it. Called by the
        offline self-integration process — NOT during the turn loop.
        """
        if idx < 0 or idx >= len(self.provenance):
            raise IndexError(f"delta index {idx} out of range")
        delta = self.provenance[idx]
        if delta["committed"]:
            return
        kind, key, value = delta["kind"], delta["key"], delta["value"]
        if kind == "believed_trait":
            self.believed_traits[key] = float(value)
        elif kind == "current_concern_add":
            if value not in self.current_concerns:
                self.current_concerns.append(str(value))
        elif kind == "current_concern_remove":
            self.current_concerns = [c for c in self.current_concerns if c != value]
        elif kind == "opinion":
            self.held_opinions[key] = str(value)
        elif kind == "hope_add":
            if value not in self.current_hopes:
                self.current_hopes.append(str(value))
        elif kind == "fear_add":
            if value not in self.current_fears:
                self.current_fears.append(str(value))
        else:
            raise ValueError(f"unknown delta kind: {kind}")
        delta["committed"] = True
