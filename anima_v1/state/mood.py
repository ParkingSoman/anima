"""Mood vector. Soft state. Decays toward a trait-determined baseline.

Dimensions: valence (negative↔positive), arousal (calm↔excited), dominance
(submissive↔dominant), plus discrete emotions tracked for nuance.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from anima.config.schema import Big5


def _clip(x: float, lo: float = -1.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


@dataclass
class MoodVector:
    valence: float = 0.0      # -1 negative, +1 positive
    arousal: float = 0.0      # -1 calm, +1 excited
    dominance: float = 0.0    # -1 submissive, +1 dominant
    discrete: dict[str, float] = field(default_factory=dict)  # joy, fear, sadness, anger, shame, ...

    @classmethod
    def baseline_for(cls, big5: Big5) -> "MoodVector":
        # rough psych-grounded mapping: extraversion → positive valence; neuroticism
        # → negative valence and arousal toward fear/sadness; conscientiousness
        # → dominance.
        valence = 0.4 * (big5.extraversion - 0.5) - 0.6 * (big5.neuroticism - 0.5)
        arousal = 0.3 * (big5.neuroticism - 0.5) + 0.2 * (big5.extraversion - 0.5)
        dominance = 0.4 * (big5.conscientiousness - 0.5) - 0.2 * (big5.neuroticism - 0.5)
        return cls(
            valence=_clip(valence),
            arousal=_clip(arousal),
            dominance=_clip(dominance),
            discrete={},
        )

    def perturb(self, dv: float = 0.0, da: float = 0.0, dd: float = 0.0,
                discrete_deltas: dict[str, float] | None = None) -> None:
        self.valence = _clip(self.valence + dv)
        self.arousal = _clip(self.arousal + da)
        self.dominance = _clip(self.dominance + dd)
        if discrete_deltas:
            for k, v in discrete_deltas.items():
                self.discrete[k] = _clip(self.discrete.get(k, 0.0) + v, 0.0, 1.0)

    def decay_toward(self, baseline: "MoodVector", rate: float = 0.15) -> None:
        self.valence += rate * (baseline.valence - self.valence)
        self.arousal += rate * (baseline.arousal - self.arousal)
        self.dominance += rate * (baseline.dominance - self.dominance)
        # Discrete emotions decay toward 0
        for k in list(self.discrete.keys()):
            self.discrete[k] = max(0.0, self.discrete[k] - rate)
            if self.discrete[k] < 0.02:
                del self.discrete[k]

    def render(self) -> str:
        labels = []
        if self.valence > 0.3: labels.append("a generally positive cast")
        elif self.valence < -0.3: labels.append("a heaviness in the chest")
        if self.arousal > 0.3: labels.append("keyed-up")
        elif self.arousal < -0.3: labels.append("tired and slow")
        if self.dominance > 0.3: labels.append("steady, on solid ground")
        elif self.dominance < -0.3: labels.append("a bit at the mercy of things")
        for k, v in sorted(self.discrete.items(), key=lambda kv: -kv[1]):
            if v > 0.3:
                labels.append(f"a strand of {k} ({v:.2f})")
        gist = "; ".join(labels) if labels else "fairly neutral, nothing particular"
        return (
            f"--- mood right now ---\n"
            f"valence={self.valence:+.2f}, arousal={self.arousal:+.2f}, dominance={self.dominance:+.2f}\n"
            f"phenomenology: {gist}\n"
            f"--- end mood ---"
        )
