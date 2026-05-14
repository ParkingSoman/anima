"""Drive state (Panksepp's 7 primary affective systems).

Activations rise with deprivation, fall with satisfying activity. They are
the scarcity backbone: drive levels gate goal salience.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from anima.config.schema import PankseppDrives


def _clip01(x: float) -> float:
    return max(0.0, min(1.0, x))


@dataclass
class DriveState:
    activations: dict[str, float] = field(default_factory=dict)

    @classmethod
    def from_baseline(cls, baseline: PankseppDrives) -> "DriveState":
        return cls(activations=baseline.model_dump())

    def perturb(self, deltas: dict[str, float]) -> None:
        for k, v in deltas.items():
            self.activations[k] = _clip01(self.activations.get(k, 0.0) + v)

    def decay_toward(self, baseline: PankseppDrives, rate: float = 0.1) -> None:
        base = baseline.model_dump()
        for k, v in base.items():
            cur = self.activations.get(k, v)
            self.activations[k] = _clip01(cur + rate * (v - cur))

    def to_jsonable(self) -> dict[str, Any]:
        return {"activations": dict(self.activations)}

    @classmethod
    def from_jsonable(cls, data: dict[str, Any]) -> "DriveState":
        return cls(activations=dict(data.get("activations", {})))

    def render(self) -> str:
        items = sorted(self.activations.items(), key=lambda kv: -kv[1])
        lines = [f"  {k}: {v:.2f}" for k, v in items]
        return "--- drive activations ---\n" + "\n".join(lines) + "\n--- end drives ---"
