"""Pydantic config schema for an Anima.

Each layer is documented with the mechanisms (M1-M6 from the plan) it routes to.
Layers that route only to M6 (expression) are decoration and excluded.

  M1  perception/appraisal bias
  M2  memory encoding/retrieval/distortion
  M3  prediction about the user
  M4  goal/drive activation
  M5  defense / suppression
  M6  expression / register
"""

from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field


def _u(): return Field(..., ge=0.0, le=1.0)
def _u_def(d): return Field(d, ge=0.0, le=1.0)


class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


# ---------- Big 5 traits (BFI-2 aligned). Routes to M1, M2, M4, M5, M6.

class Big5(_Frozen):
    openness: float = _u()
    conscientiousness: float = _u()
    extraversion: float = _u()
    agreeableness: float = _u()
    neuroticism: float = _u()

    def as_dict(self) -> dict:
        return {
            "openness": self.openness,
            "conscientiousness": self.conscientiousness,
            "extraversion": self.extraversion,
            "agreeableness": self.agreeableness,
            "neuroticism": self.neuroticism,
        }


# ---------- Attachment style (Bowlby / Bartholomew). Routes to M1, M3, M4.

class AttachmentStyle(str, Enum):
    SECURE = "secure"
    ANXIOUS = "anxious"        # preoccupied: low avoidance, high anxiety
    AVOIDANT = "avoidant"      # dismissive: high avoidance, low anxiety
    FEARFUL = "fearful"        # disorganized: high avoidance, high anxiety


class Attachment(_Frozen):
    style: AttachmentStyle = AttachmentStyle.SECURE
    anxiety: float = _u_def(0.3)        # ECR-R anxiety dimension
    avoidance: float = _u_def(0.3)      # ECR-R avoidance dimension
    iwm_of_self: str = "I am worthy of care."
    iwm_of_others: str = "Others are generally reliable."


# ---------- Schwartz values. Routes to M4.

class SchwartzValues(_Frozen):
    """Schwartz Theory of Basic Values. Each in [0,1]. The Anima generates goals
    weighted by these and resolves goal conflicts using their relative priority.
    """
    self_direction: float = _u_def(0.5)
    stimulation: float = _u_def(0.5)
    hedonism: float = _u_def(0.5)
    achievement: float = _u_def(0.5)
    power: float = _u_def(0.5)
    security: float = _u_def(0.5)
    conformity: float = _u_def(0.5)
    tradition: float = _u_def(0.5)
    benevolence: float = _u_def(0.5)
    universalism: float = _u_def(0.5)

    def top_k(self, k: int = 3) -> list[tuple[str, float]]:
        items = list(self.model_dump().items())
        items.sort(key=lambda kv: kv[1], reverse=True)
        return items[:k]


# ---------- Panksepp primary affective systems. Routes to M4.

class PankseppDrives(_Frozen):
    """Baseline activations for Panksepp's 7 primary-affect systems. Runtime
    state holds the *current* activations; this is the trait-level baseline.
    """
    seeking: float = _u_def(0.5)   # curiosity / appetitive motivation
    rage: float = _u_def(0.3)
    fear: float = _u_def(0.3)
    lust: float = _u_def(0.3)
    care: float = _u_def(0.5)
    panic_grief: float = _u_def(0.3)  # separation distress
    play: float = _u_def(0.5)


# ---------- Cognitive style. Routes to M1, M3.

class CognitiveStyle(_Frozen):
    need_for_closure: float = _u_def(0.5)
    intuitive_vs_analytic: float = _u_def(0.5)  # 0=fully analytic, 1=fully intuitive
    openness_to_ambiguity: float = _u_def(0.5)


# ---------- Demographics. Routes to M1, M3, M6.

class Demographics(_Frozen):
    age: int = Field(30, ge=0, le=120)
    gender: str = "unspecified"
    role: str = ""              # "high-school teacher", "trauma therapist", ...
    culture: str = ""           # "American urban", "rural Japanese", ...
    era: str = "contemporary"
    language_register: str = "neutral conversational"


# ---------- Biography. Routes to M1, M2, M3, M4 (seeds long-term memory).

class Biography(_Frozen):
    name: str
    one_line: str = ""           # "a 47-year-old grieving widow processing her husband's recent death"
    family_of_origin: str = ""
    formative_events: list[str] = Field(default_factory=list)
    current_life_situation: str = ""
    ongoing_relationships: list[str] = Field(default_factory=list)
    ongoing_life_projects: list[str] = Field(default_factory=list)
    recent_emotional_events: list[str] = Field(default_factory=list)


# ---------- Optional layers (slot in at later phases)

class YoungSchema(str, Enum):
    ABANDONMENT = "abandonment"
    MISTRUST = "mistrust_abuse"
    EMOTIONAL_DEPRIVATION = "emotional_deprivation"
    DEFECTIVENESS = "defectiveness_shame"
    SOCIAL_ISOLATION = "social_isolation"
    DEPENDENCE = "dependence_incompetence"
    VULNERABILITY = "vulnerability_to_harm"
    ENMESHMENT = "enmeshment"
    FAILURE = "failure"
    ENTITLEMENT = "entitlement"
    INSUFFICIENT_SELFCONTROL = "insufficient_self_control"
    SUBJUGATION = "subjugation"
    SELF_SACRIFICE = "self_sacrifice"
    APPROVAL_SEEKING = "approval_seeking"
    NEGATIVITY_PESSIMISM = "negativity_pessimism"
    EMOTIONAL_INHIBITION = "emotional_inhibition"
    UNRELENTING_STANDARDS = "unrelenting_standards"
    PUNITIVENESS = "punitiveness"


class DefenseMaturity(str, Enum):
    PSYCHOTIC = "psychotic"
    IMMATURE = "immature"
    NEUROTIC = "neurotic"
    MATURE = "mature"


class Defenses(_Frozen):
    maturity: DefenseMaturity = DefenseMaturity.NEUROTIC
    preferred: list[str] = Field(default_factory=list)  # e.g. ["humor", "intellectualization"]


class Narrative(_Frozen):
    agency_vs_communion: float = _u_def(0.5)  # 0=communion, 1=agency
    redemption_themes: float = _u_def(0.5)
    contamination_themes: float = _u_def(0.3)
    current_imago: str = ""                   # "the wounded healer", "the rebel", ...


# ---------- The top-level configuration.

class AnimaConfig(_Frozen):
    name: str
    big5: Big5
    schwartz: SchwartzValues
    attachment: Attachment
    biography: Biography
    drives: PankseppDrives = PankseppDrives()
    cognitive_style: CognitiveStyle = CognitiveStyle()
    demographics: Demographics = Demographics()
    schemas: list[YoungSchema] = Field(default_factory=list)
    defenses: Defenses = Defenses()
    narrative: Narrative = Narrative()
    notes: str = ""


def load_config(path: str | Path) -> AnimaConfig:
    raw = yaml.safe_load(Path(path).read_text())
    return AnimaConfig(**raw)
