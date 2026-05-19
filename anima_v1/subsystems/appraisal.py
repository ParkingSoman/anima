"""Appraisal: Lazarus-style cognitive appraisal. The place where parameter
INTERACTION happens — the appraisal prompt receives the FULL configuration
plus current state and produces a joint appraisal, not a sum of independent
contributions.

Routes to M1, and writes mood/drive perturbations consumed by the rest of
the loop.
"""

from __future__ import annotations

from dataclasses import dataclass

from anima_v1.config.schema import AnimaConfig
from anima_v1.llm.base import LLMAdapter
from anima_v1.state.drives import DriveState
from anima_v1.state.mood import MoodVector
from anima_v1.state.self_model import SelfModel
from anima_v1.subsystems._common import extract_json
from anima_v1.subsystems.perception import Perception


@dataclass
class Appraisal:
    relevance: float           # how much this matters to me, [0,1]
    goal_congruence: float     # -1 thwarts, +1 facilitates my goals
    ego_relevance: float       # how much my sense of self is at stake, [0,1]
    coping_potential: float    # how well I think I can handle this, [0,1]
    future_expectancy: float   # do I expect this to get better or worse, [-1,1]
    primary_emotion: str       # one word: fear/anger/sadness/shame/guilt/joy/...
    appraisal_scene_tag: str   # 2–4 word concrete scene-tag; NOT a first-person sentence
    mood_dv: float = 0.0
    mood_da: float = 0.0
    mood_dd: float = 0.0
    discrete_deltas: dict = None
    drive_deltas: dict = None

    def __post_init__(self):
        if self.discrete_deltas is None:
            self.discrete_deltas = {}
        if self.drive_deltas is None:
            self.drive_deltas = {}


_INSTR = """You are the APPRAISAL subsystem of a cognitive architecture.

Given a person's full configuration (traits, attachment, values, schemas,
biography), their CURRENT self-model and mood, and their just-formed
PERCEPTION of an incoming message, do a Lazarus-style cognitive appraisal:
what does this MEAN for this person, given who they are?

This appraisal is where personality INTERACTIONS show up: e.g., a high-N +
secure-attachment person reads a perceived rejection differently than a
high-N + anxious-attachment person, who reads it differently than a high-N +
avoidant person. The appraisal must reflect the JOINT effect of the
configuration, not a sum of independent effects.

Output a single JSON object with these keys:
  relevance:           [0,1] how much this matters to this person
  goal_congruence:     [-1,1] does it facilitate (+) or thwart (-) their current goals
  ego_relevance:       [0,1] does it touch their sense of self
  coping_potential:    [0,1] can they handle what's coming
  future_expectancy:   [-1,1] do they expect things to get better (+) or worse (-)
  primary_emotion:     one word (fear|anger|sadness|shame|guilt|disgust|joy|interest|tenderness|love|contempt|pride|hope|surprise|neutral)
  appraisal_scene_tag: A 2–4 word concrete scene-tag describing how this moment registers
                       to this person. NOT a first-person sentence.
                       Examples of good tags:
                         "a tactical question",
                         "a small kindness",
                         "a hollow compliment",
                         "a procedural ask",
                         "an unwelcome topic".
                       Examples of BAD tags (do not produce these): full sentences, paragraphs,
                       anything starting with "I", anything explaining the appraisal.
  mood_dv:             change to valence in [-0.6, +0.6] (negative = darker)
  mood_da:             change to arousal in [-0.6, +0.6] (negative = calmer)
  mood_dd:             change to dominance in [-0.6, +0.6]
  discrete_deltas:     dict of {emotion_name: [0,1] delta}. Add only emotions that are activated.
  drive_deltas:        dict of {drive_name: [-0.4, +0.4] delta} for any of: seeking, rage, fear, lust, care, panic_grief, play.

Return ONLY the JSON. No prose around it.
"""


def _config_appraisal_block(cfg: AnimaConfig) -> str:
    b5 = cfg.big5
    s = cfg.schwartz
    return (
        "--- this person's configuration (immutable; informs the appraisal) ---\n"
        f"Big5: O={b5.openness:.2f}, C={b5.conscientiousness:.2f}, E={b5.extraversion:.2f}, "
        f"A={b5.agreeableness:.2f}, N={b5.neuroticism:.2f}\n"
        f"Attachment: style={cfg.attachment.style.value}, "
        f"anxiety={cfg.attachment.anxiety:.2f}, avoidance={cfg.attachment.avoidance:.2f}\n"
        f"Schwartz top values: {', '.join(f'{k}={v:.2f}' for k, v in s.top_k(5))}\n"
        f"Drives (baseline): seek={cfg.drives.seeking:.2f}, care={cfg.drives.care:.2f}, "
        f"play={cfg.drives.play:.2f}, fear={cfg.drives.fear:.2f}, "
        f"panic_grief={cfg.drives.panic_grief:.2f}, rage={cfg.drives.rage:.2f}\n"
        f"Active schemas: {', '.join(s.value for s in cfg.schemas) or 'none salient'}\n"
        f"Defense maturity: {cfg.defenses.maturity.value}; preferred: "
        f"{', '.join(cfg.defenses.preferred) or '—'}\n"
        f"Narrative: agency_vs_communion={cfg.narrative.agency_vs_communion:.2f}, "
        f"redemption={cfg.narrative.redemption_themes:.2f}, "
        f"contamination={cfg.narrative.contamination_themes:.2f}, "
        f"imago='{cfg.narrative.current_imago}'\n"
        "--- end configuration ---"
    )


class AppraisalSubsystem:
    def __init__(self, llm: LLMAdapter):
        self.llm = llm

    def run(self, *, cfg: AnimaConfig, self_model: SelfModel,
            mood_view: str, drive_view: str, perception: Perception,
            perception_view: str) -> Appraisal:
        system = (
            _INSTR + "\n\n"
            + _config_appraisal_block(cfg) + "\n\n"
            + self_model.render() + "\n\n"
            + mood_view + "\n\n"
            + drive_view + "\n\n"
            + perception_view
        )
        msgs = [{"role": "user",
                 "content": "Appraise the situation. Return only the JSON object."}]
        resp = self.llm.generate(tier="fast", system=system, messages=msgs,
                                 max_tokens=4000, temperature=0.4)
        data = extract_json(resp.text) or {}
        return Appraisal(
            relevance=float(data.get("relevance", 0.5)),
            goal_congruence=float(data.get("goal_congruence", 0.0)),
            ego_relevance=float(data.get("ego_relevance", 0.3)),
            coping_potential=float(data.get("coping_potential", 0.5)),
            future_expectancy=float(data.get("future_expectancy", 0.0)),
            primary_emotion=str(data.get("primary_emotion", "neutral"))[:32],
            appraisal_scene_tag=str(data.get("appraisal_scene_tag", ""))[:80],
            mood_dv=float(data.get("mood_dv", 0.0)),
            mood_da=float(data.get("mood_da", 0.0)),
            mood_dd=float(data.get("mood_dd", 0.0)),
            discrete_deltas={k: float(v) for k, v in (data.get("discrete_deltas") or {}).items()},
            drive_deltas={k: float(v) for k, v in (data.get("drive_deltas") or {}).items()},
        )

    def apply(self, *, appraisal: Appraisal, mood: MoodVector, drives: DriveState) -> None:
        mood.perturb(dv=appraisal.mood_dv, da=appraisal.mood_da, dd=appraisal.mood_dd,
                     discrete_deltas=appraisal.discrete_deltas)
        drives.perturb(appraisal.drive_deltas)

    def render(self, a: Appraisal) -> str:
        return (
            f"--- appraisal ---\n"
            f"relevance: {a.relevance:.2f}; ego at stake: {a.ego_relevance:.2f}\n"
            f"goal congruence: {a.goal_congruence:+.2f}; coping potential: {a.coping_potential:.2f}\n"
            f"future expectancy: {a.future_expectancy:+.2f}\n"
            f"primary emotion: {a.primary_emotion}\n"
            f"how I read this moment (scene-tag): {a.appraisal_scene_tag}\n"
            f"--- end appraisal ---"
        )
