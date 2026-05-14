"""Autobiographical narrative — STUB.

Phase 5 work. Phase 2 leaves this minimal so the §5.1/§5.2 boundary is
established (episodic + semantic + relational vs. narrative-level integration)
but consolidation into a life-story is deferred to Phase 5.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class AutobiographicalNarrative:
    themes: list[str] = field(default_factory=list)
    imago: str = ""                  # McAdams: the current self-as-character image
    recent_events_gist: str = ""     # one paragraph; updated by consolidation (Phase 4+)

    def render(self) -> str:
        themes_str = "; ".join(self.themes) if self.themes else "—"
        imago_str = self.imago or "—"
        gist_str = self.recent_events_gist or "—"
        return (
            f"--- autobiographical narrative ---\n"
            f"themes: {themes_str}\n"
            f"imago: {imago_str}\n"
            f"recent gist: {gist_str}\n"
            f"--- end narrative ---"
        )

    def to_jsonable(self) -> dict[str, Any]:
        return {
            "themes": list(self.themes),
            "imago": self.imago,
            "recent_events_gist": self.recent_events_gist,
        }

    @classmethod
    def from_jsonable(cls, data: dict[str, Any]) -> "AutobiographicalNarrative":
        return cls(
            themes=list(data.get("themes", [])),
            imago=str(data.get("imago", "")),
            recent_events_gist=str(data.get("recent_events_gist", "")),
        )
