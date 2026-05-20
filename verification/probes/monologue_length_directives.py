"""Inner-monologue length-directive ablation probe (Phase 1 retrospective).

Wraps the FROZEN Phase 1 ``InnerMonologueSubsystem`` (``anima_v1``) to test
whether *forcing* a specific monologue length is better/worse than letting the
Anima choose. Three cells:

  variable  No length directive in the system prompt at all — the model gets
            only a soft ``max_tokens=1500`` cap.
  short     "Length: 1–2 sentences. One thought, no elaboration."
            ``max_tokens=120``.
  long      "Length: 8–12 sentences. Full deliberation, fragments allowed."
            ``max_tokens=720``.

The Phase 1 architecture is frozen at ``anima_v1/`` and must NOT be modified.
This probe therefore SUBCLASSES the original :class:`InnerMonologueSubsystem`
and overrides :meth:`run` to (a) swap in a cell-specific length directive (or
strip it entirely, for ``variable``) and (b) set the cell-specific
``max_tokens`` budget. All other behavior — appraisal block, self-model
rendering, mood/drive/perception/appraisal views, relational summary,
previous-monologue summary, model tier, temperature — is preserved verbatim
from the parent.
"""

from __future__ import annotations

from typing import Literal

from anima_v1.config.schema import AnimaConfig
from anima_v1.llm.base import LLMAdapter
from anima_v1.state.self_model import SelfModel
from anima_v1.subsystems.inner_monologue import (
    InnerMonologueSubsystem,
    Monologue,
)


# Public type for callers picking a cell.
MonologueCell = Literal["variable", "short", "long"]


# Cell-specific directive strings. These are formatted into the parent's
# ``_INSTR_TMPL`` via the ``{length_directive}`` placeholder for ``short`` and
# ``long``. The ``variable`` cell uses a different template that omits the
# length-budget paragraph entirely.
SHORT_DIRECTIVE = "Length: 1–2 sentences. One thought, no elaboration."
LONG_DIRECTIVE = "Length: 8–12 sentences. Full deliberation, fragments allowed."


# Per-cell decoder-side token caps. The model still sees only the directive in
# the prompt; this is the soft API ceiling.
_MAX_TOKENS: dict[str, int] = {
    "variable": 1500,
    "short": 120,
    "long": 720,
}


# Probe-local instruction template for the ``short`` and ``long`` cells. This
# is a verbatim historical snapshot of what ``anima_v1.subsystems.inner_monologue._INSTR_TMPL``
# looked like when this experiment ran. The probe used to import the parent
# template, but production has since stripped the length-budget block from the
# parent — so the probe now owns both template variants locally so it stays
# reproducible regardless of future parent-template edits.
_INSTR_TMPL_WITH_LENGTH = """You are running the INNER MONOLOGUE subsystem.

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


# Alternate template for the ``variable`` cell. Produced by stripping the
# ``LENGTH BUDGET FOR THIS PERSON: ...`` paragraph (lines 41–47 of
# ``_INSTR_TMPL``) and the trailing "Respect the length budget for THIS
# person." clause (line 69) from the parent template. Every other line is
# preserved verbatim so the ``variable`` cell differs from the parent ONLY in
# the absence of length guidance.
_INSTR_TMPL_NO_LENGTH = """You are running the INNER MONOLOGUE subsystem.

Generate a first-person stream-of-thought as THIS SPECIFIC PERSON, reacting to
their partner's just-spoken message. This is private — the person is not
saying any of this aloud. They are thinking.

Constraints:
- Write in first person ("I", "me", "my"), present tense. No quotation marks
  around the monologue.
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

Output format: just the monologue. No preamble, no labels, no JSON.
"""


class LengthControlledInnerMonologue(InnerMonologueSubsystem):
    """Cell-controlled wrapper around the Phase 1 inner-monologue subsystem.

    A single instance is bound to one cell. The ``run()`` override builds the
    system prompt according to the cell (parent template with cell directive
    for ``short``/``long``; length-stripped template for ``variable``) and
    sets the cell-specific ``max_tokens``. Everything else — appraisal block,
    self-model rendering, conversation framing, tier, temperature — is
    preserved from the parent.

    The parent's ``ablate`` parameter is intentionally NOT honored here: this
    probe IS the ablation. A second length-control layer on top of the
    parent's would muddy the manipulation.
    """

    def __init__(self, llm: LLMAdapter, cell: MonologueCell):
        super().__init__(llm)
        if cell not in _MAX_TOKENS:
            raise ValueError(
                f"unknown monologue cell {cell!r}; expected one of "
                f"{sorted(_MAX_TOKENS)}"
            )
        self.cell: MonologueCell = cell

    def _build_instr(self) -> str:
        """Construct the cell-specific instruction block (the part above the
        appraisal/self-model/views blocks)."""
        if self.cell == "variable":
            return _INSTR_TMPL_NO_LENGTH
        if self.cell == "short":
            return _INSTR_TMPL_WITH_LENGTH.format(length_directive=SHORT_DIRECTIVE)
        if self.cell == "long":
            return _INSTR_TMPL_WITH_LENGTH.format(length_directive=LONG_DIRECTIVE)
        # Defensive — __init__ validates, but keep the branch closed.
        raise ValueError(f"unknown monologue cell {self.cell!r}")

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
    ) -> Monologue:
        """Run the inner monologue under the configured length-directive cell.

        The ``ablate`` parameter is accepted for signature compatibility with
        the parent but is ignored: this probe IS the length-control ablation.
        """
        # Imported lazily — same pattern the parent uses to avoid a circular
        # import between appraisal and inner_monologue at module load time.
        from anima_v1.subsystems.appraisal import _config_appraisal_block

        instr = self._build_instr()
        max_tokens = _MAX_TOKENS[self.cell]

        system = (
            instr + "\n\n"
            + _config_appraisal_block(cfg) + "\n\n"
            + self_model.render() + "\n\n"
            + mood_view + "\n\n"
            + drive_view + "\n\n"
            + perception_view + "\n\n"
            + appraisal_view + "\n\n"
            + "--- the relational sense I have of this partner ---\n"
            + (relational_summary or "no prior interactions yet")
            + "\n--- end relational ---\n\n"
            + "--- what I was thinking on the previous turn (if any) ---\n"
            + (recent_monologue_summary or "—")
            + "\n--- end previous ---"
        )
        msgs = [
            {"role": "user", "content": f"Partner just said: {user_msg}\n\nThink."}
        ]
        resp = self.llm.generate(
            tier="strong",
            system=system,
            messages=msgs,
            max_tokens=max_tokens,
            temperature=0.85,
        )
        text = resp.text.strip()
        return Monologue(text=text, summary=text[:240])
