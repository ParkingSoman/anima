"""Perception: interpret the user's message through the Anima's current state.

Routes to M1 (perception/appraisal bias). The same input becomes a different
*perception* depending on traits, schemas, self-model, and the existing
relational schema for this user.
"""

from __future__ import annotations

from dataclasses import dataclass

from anima_v1.llm.base import LLMAdapter
from anima_v1.state.self_model import SelfModel
from anima_v1.subsystems._common import extract_json


@dataclass
class Perception:
    literal_content: str
    perceived_intent: str
    perceived_valence: float           # -1 = hostile, 0 = neutral, +1 = warm
    perceived_demands: list[str]
    salient_features: list[str]        # what the Anima notices in the message


_INSTR = """You are running the PERCEPTION subsystem of a cognitive architecture
that simulates a specific person. You are NOT the person. You are an internal
module that determines what THIS PERSON, given who they are, would notice and
interpret in an incoming message from a conversation partner.

Output a single JSON object with these keys:
  literal_content:    one-sentence factual paraphrase of what was actually said
  perceived_intent:   one-sentence rendering of what this person reads the partner as wanting/doing
  perceived_valence:  number in [-1, 1] for how warm/hostile this person reads the message
  perceived_demands:  list of strings — what this person feels is being asked of them (may be empty)
  salient_features:   list of strings — specific words, tones, or implications this person notices,
                      filtered through their schemas, attachment style, and current preoccupations.
                      A more anxious person notices rejection cues; an avoidant one notices intrusion;
                      a person in grief notices anything that touches on loss.

Return ONLY the JSON. No prose around it.
"""


class PerceptionSubsystem:
    def __init__(self, llm: LLMAdapter):
        self.llm = llm

    def run(self, *, user_msg: str, self_model: SelfModel, mood_view: str,
            relational_summary: str) -> Perception:
        system = (
            _INSTR + "\n\n"
            + self_model.render() + "\n\n"
            + mood_view + "\n\n"
            + "--- existing relational sense of this partner ---\n"
            + (relational_summary or "no prior interactions")
            + "\n--- end relational ---"
        )
        msgs = [{"role": "user", "content": f"Partner just said:\n\n{user_msg}"}]
        resp = self.llm.generate(tier="fast", system=system, messages=msgs, max_tokens=8000, temperature=0.4)
        data = extract_json(resp.text) or {}
        return Perception(
            literal_content=str(data.get("literal_content", user_msg))[:1000],
            perceived_intent=str(data.get("perceived_intent", "unclear"))[:500],
            perceived_valence=float(data.get("perceived_valence", 0.0)),
            perceived_demands=list(data.get("perceived_demands", []))[:8],
            salient_features=list(data.get("salient_features", []))[:8],
        )

    def render(self, p: Perception) -> str:
        demands = "; ".join(p.perceived_demands) if p.perceived_demands else "—"
        salient = "; ".join(p.salient_features) if p.salient_features else "—"
        return (
            f"--- perception ---\n"
            f"what was said (paraphrase): {p.literal_content}\n"
            f"what I read them as doing: {p.perceived_intent}\n"
            f"warmth I read: {p.perceived_valence:+.2f}\n"
            f"what I feel being asked of me: {demands}\n"
            f"what I noticed: {salient}\n"
            f"--- end perception ---"
        )
