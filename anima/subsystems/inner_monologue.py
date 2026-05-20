"""Inner monologue — the seat of the self.

This is the only subsystem that runs at STRONG tier on every turn. Its output
is private first-person stream-of-thought, NEVER shown to the user. It is the
input to defense filtering and response planning.

Per §7 of the plan: the self is inhabited rather than performed iff the
self-model influences outputs the system does not realize are self-expressive.
The inner monologue is FIRST-person, conditioned on self-model + appraisal +
mood + drives, and is generated without knowing what the response will be.

Convention: the monologue may include thoughts the person would NOT say. That
is the point. The defense and response-planning subsystems determine what gets
externalized.
"""

from __future__ import annotations

from dataclasses import dataclass

from anima.config.schema import AnimaConfig
from anima.llm.base import LLMAdapter
from anima.state.self_model import SelfModel


@dataclass
class Monologue:
    text: str
    summary: str = ""    # one-sentence gist for downstream prompts


_INSTR_TMPL = """You are running the INNER MONOLOGUE subsystem.

Generate a first-person stream-of-thought as THIS SPECIFIC PERSON, reacting to
their partner's just-spoken message. This is private — the person is not
saying any of this aloud. They are thinking.

Constraints:
- Write in first person ("I", "me", "my"), present tense. No quotation marks
  around the monologue.
- LENGTH BUDGET FOR THIS PERSON: {length_directive}
  Different people have different inner lives. Ruminative, neurotic,
  introverted, analytic people think more internally before acting.
  Extraverted, low-NFC, intuitive people process externally — their inner
  voice is often one sentence or a flash, and then they're already speaking.
  RESPECT THIS BUDGET. It is a feature of who this person is, not a default
  to be inflated.
- Stream-of-thought, not essay. Allow fragments. Allow contradictions. Allow
  self-interruption.
- The monologue should reflect WHO THIS PERSON IS at a level deeper than
  surface vocabulary. The traits, schemas, attachment style, current mood, and
  preoccupations should leak into what the person ATTENDS to, what associations
  surface, what they want to do, and what they almost-say-and-then-don't.
- A grieving person notices things that wouldn't catch a happy person. An
  anxious-attached person reads more rejection into ambiguity than an avoidant
  one. A playful, secure person might just notice their partner's mood and
  reach for the next move. Let those filters operate.
- Do NOT narrate yourself describing yourself. Do NOT begin with "As a person
  who..." This is the inside of a head, not a character sheet.
- Do NOT decide a response yet. That happens later. Just think.
- This monologue can include thoughts the person would never SAY. That is the
  point of having an inside.
- The appraisal block above contains a "scene-tag" — a 2-4 word handle for how
  this moment registers. The tag is NOT a sentence to extend or quote; it's a
  categorical label. Your job is to produce the actual first-person prose
  interior. Do not echo the tag.

Output format: just the monologue. No preamble, no labels, no JSON. Respect the
length budget for THIS person.
"""


class InnerMonologueSubsystem:
    def __init__(self, llm: LLMAdapter):
        self.llm = llm

    # Uniform monologue directive applied to every persona. Length-of-output
    # emerges from the persona's structural config (Big5, schemas, defenses), not
    # from prompt-side length prescription.
    _UNIFORM_DIRECTIVE = (
        "Length: 2–6 sentences. Stream-of-thought, not essay. Allow "
        "fragments. Allow contradictions. Allow self-interruption."
    )

    def run(
        self,
        *,
        cfg: AnimaConfig,
        self_model: SelfModel,
        mood_view: str,
        drive_view: str,
        perception_view: str,
        appraisal_view: str,
        relational_summary: str,
        recent_monologue_summary: str,
        user_msg: str,
        ablate: bool = False,
        retrieval_view: str = "",
        prediction_view: str = "",
    ) -> Monologue:
        """Run the inner monologue.

        The directive is the same for every persona (a uniform 2–6 sentence
        instruction). Length-of-output emerges from the persona's structural
        config (Big5, schemas, defenses) reacting to the situation, not from
        prompt-side length prescription. The ``ablate`` kwarg is retained
        for API compatibility but is now a no-op.
        """
        from anima.subsystems.appraisal import _config_appraisal_block

        # Single uniform monologue directive — same for every persona. The
        # prior persona-scaled length directive (introvert+analytic → longer;
        # extravert+intuitive → shorter) was removed: it conflated *instructed
        # sentence count* with *token budget* and produced mid-sentence cutoffs
        # for ruminative personas like Iris on DeepSeek-flash (where the
        # reasoning channel eats budget before .content emits). Length-of-
        # output now emerges from the structural config (Big5, schemas,
        # defenses) acting on a fixed directive, not from prompt-side
        # length prescription. The ``ablate`` parameter is retained as a no-op
        # for API compatibility with Anima.__init__'s ablate_monologue_length
        # plumbing; both branches now take the same path.
        directive = self._UNIFORM_DIRECTIVE
        max_tokens = 8000
        instr = _INSTR_TMPL.format(length_directive=directive)

        system = (
            instr + "\n\n"
            + _config_appraisal_block(cfg) + "\n\n"
            + self_model.render() + "\n\n"
            + mood_view + "\n\n"
            + drive_view + "\n\n"
            + perception_view
            + ("\n\n" + retrieval_view if retrieval_view else "")
            + ("\n\n" + prediction_view if prediction_view else "")
            + "\n\n"
            + appraisal_view + "\n\n"
            + "--- the relational sense I have of this partner ---\n"
            + (relational_summary or "no prior interactions yet")
            + "\n--- end relational ---\n\n"
            + "--- what I was thinking on the previous turn (if any) ---\n"
            + (recent_monologue_summary or "—")
            + "\n--- end previous ---"
        )
        msgs = [{"role": "user", "content": f"Partner just said: {user_msg}\n\nThink."}]
        resp = self.llm.generate(tier="strong", system=system, messages=msgs,
                                 max_tokens=max_tokens, temperature=0.85)
        text = resp.text.strip()
        return Monologue(text=text, summary=text[:240])

    def render(self, m: Monologue) -> str:
        return f"--- inner monologue (private) ---\n{m.text}\n--- end monologue ---"
