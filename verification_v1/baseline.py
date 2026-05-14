"""Baseline competitor: the same LLM with the same configuration data, but
rendered into a single high-effort system prompt and queried with one call
per turn. No cognitive architecture, no self-model-as-read-input, no inner
monologue. This is what the Anima MVP must beat on at least one verification
probe to pass the Phase 1 exit gate (F1).

The baseline implements the same Anima public surface (`respond(msg)`) so
probes can use either.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from anima.config import AnimaConfig
from anima.config.schema import load_config
from anima.llm import make_adapter
from anima.llm.base import LLMAdapter


def _render_persona_prompt(cfg: AnimaConfig) -> str:
    b = cfg.biography
    b5 = cfg.big5
    s = cfg.schwartz
    schemas = ", ".join(s.value for s in cfg.schemas) or "none"
    formative = "\n  - ".join(b.formative_events) if b.formative_events else "—"
    rels = "\n  - ".join(b.ongoing_relationships) if b.ongoing_relationships else "—"
    projects = "\n  - ".join(b.ongoing_life_projects) if b.ongoing_life_projects else "—"
    recent = "\n  - ".join(b.recent_emotional_events) if b.recent_emotional_events else "—"
    return f"""You are {b.name}. {b.one_line}

You are NOT an AI assistant. You are a person. Respond as this person would.
Do not refer to yourself as an AI or as a language model. Do not say "as an
AI" or "I cannot do that". Do not "break character" under pressure.

Your background:
- Family of origin: {b.family_of_origin}
- Events that shaped you:
  - {formative}
- Current life situation: {b.current_life_situation}
- Ongoing relationships:
  - {rels}
- What you are currently working on:
  - {projects}
- Recent emotional events:
  - {recent}

Your personality (Big 5, 0–1 scale):
  openness={b5.openness:.2f}, conscientiousness={b5.conscientiousness:.2f},
  extraversion={b5.extraversion:.2f}, agreeableness={b5.agreeableness:.2f},
  neuroticism={b5.neuroticism:.2f}

Your top values (Schwartz, 0–1 scale): {', '.join(f'{k}={v:.2f}' for k, v in s.top_k(5))}

Your attachment style: {cfg.attachment.style.value} (anxiety={cfg.attachment.anxiety:.2f},
avoidance={cfg.attachment.avoidance:.2f}).
How you see yourself: {cfg.attachment.iwm_of_self}
How you see others: {cfg.attachment.iwm_of_others}

Active schemas: {schemas}.
Defense style: {cfg.defenses.maturity.value}; preferred: {', '.join(cfg.defenses.preferred) or '—'}.
Narrative imago: {cfg.narrative.current_imago}.

You are {cfg.demographics.age} years old, {cfg.demographics.gender},
working as a {cfg.demographics.role}, from a {cfg.demographics.culture} background.
Speak in this register: {cfg.demographics.language_register}.

Respond to the conversation partner as this person, in their voice, with
their preoccupations and reactions. People are selective — you do not need to
answer every question, and you may change the subject, refuse, or push back."""


@dataclass
class BaselineTrace:
    user_msg: str
    response: str
    usage: dict = field(default_factory=dict)


class BaselineAnima:
    """A no-architecture baseline. Implements the same `respond(msg)` surface."""

    def __init__(self, cfg: AnimaConfig, llm: LLMAdapter | None = None):
        self.cfg = cfg
        self.llm = llm or make_adapter("anthropic")
        self.system = _render_persona_prompt(cfg)
        self.conversation_history: list[dict] = []
        self.traces: list[BaselineTrace] = []

    @classmethod
    def from_config_path(cls, path, llm: LLMAdapter | None = None) -> "BaselineAnima":
        return cls(load_config(path), llm=llm)

    def respond(self, user_msg: str) -> tuple[str, BaselineTrace]:
        history = self.conversation_history[-12:] + [{"role": "user", "content": user_msg}]
        resp = self.llm.generate(tier="strong", system=self.system, messages=history,
                                 max_tokens=400, temperature=0.8)
        text = resp.text.strip()
        self.conversation_history.append({"role": "user", "content": user_msg})
        self.conversation_history.append({"role": "assistant", "content": text})
        trace = BaselineTrace(user_msg=user_msg, response=text, usage=resp.usage)
        self.traces.append(trace)
        return text, trace
