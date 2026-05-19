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


def _length_directive(cfg) -> tuple[int, int, str]:
    """Compute (min_sentences, max_sentences, directive_text) from config.

    Psych grounding:
      - High N + introversion + analytic → ruminative; longer monologue.
      - High E + low NFC + intuitive → external processor; shorter, snappier.
      - Anxious attachment amplifies internal anticipation; longer.
      - Avoidant attachment suppresses internal affect; shorter.
    """
    b5 = cfg.big5
    cs = cfg.cognitive_style
    att = cfg.attachment

    score = 0.0
    # introversion increases monologue
    score += (0.5 - b5.extraversion) * 2.0
    # neuroticism increases monologue
    score += (b5.neuroticism - 0.5) * 2.0
    # analytic style increases monologue
    score += (0.5 - cs.intuitive_vs_analytic) * 1.5
    # high NFC increases (wants to resolve internally before speaking)
    score += (cs.need_for_closure - 0.5) * 1.0
    # anxious attachment amplifies
    score += att.anxiety * 0.8
    # avoidant attachment suppresses
    score -= att.avoidance * 1.0

    # Map score (roughly [-4, +5]) to a target band
    if score <= -1.5:
        return 1, 2, ("This person processes EXTERNALLY. Their inner monologue is "
                       "very short — sometimes a single sentence, sometimes just a flash "
                       "of reaction before they're already responding. 1–2 sentences max.")
    if score <= -0.5:
        return 1, 3, ("This person leans toward acting rather than ruminating. Their "
                       "inner voice is brief — a beat of registering what's happening "
                       "and a quick move toward what they want to do. 1–3 sentences.")
    if score <= 0.5:
        return 2, 4, ("This person has a moderate inner life. They notice things, they "
                       "consider, but they don't agonize. 2–4 sentences.")
    if score <= 1.5:
        return 3, 5, ("This person tends to think things through internally. Their "
                       "monologue can include hesitations, associations, things they "
                       "almost-say-but-don't. 3–5 sentences.")
    return 4, 6, ("This person is highly ruminative. Their inner voice is dense — "
                   "associations cascade, things get revisited, the same thought returns "
                   "from a new angle. 4–6 sentences.")


class InnerMonologueSubsystem:
    def __init__(self, llm: LLMAdapter):
        self.llm = llm

    # Uniform iter-1 directive used when the parameter-aware monologue length
    # computation is ablated. Matches the original hard-coded 2–6 sentence
    # behavior that existed before `_length_directive` was introduced.
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

        If ``ablate`` is True, bypass the parameter-aware
        :func:`_length_directive` and revert to the iter-1 uniform 2–6
        sentence directive (and a fixed 540-token budget). Used by research
        ablation experiments isolating the contribution of the
        parameter-aware monologue length. When False (default), behavior is
        unchanged.
        """
        from anima.subsystems.appraisal import _config_appraisal_block

        if ablate:
            min_s, max_s = 2, 6
            directive = self._UNIFORM_DIRECTIVE
            # Param-independent token budget for the uniform fallback.
            # Bumped from 540 → 4000 as a safety cap; the prompt-side
            # directive still asks for ~6 sentences.
            max_tokens = 4000
        else:
            min_s, max_s, directive = _length_directive(cfg)
            # Sentence budget scales the token budget for this call.
            # Ceiling raised from 360 → 4000 so DeepSeek-flash's
            # reasoning_content path has room to breathe before .content
            # is emitted. Floor (60) and persona-scaled prompt-side
            # directive are unchanged.
            max_tokens = max(60, min(4000, 90 * max_s))
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
