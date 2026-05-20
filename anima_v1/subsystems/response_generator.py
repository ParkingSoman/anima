"""Response generator. Strong-tier. Renders the externally-visible reply.

Post-Task-2 (planner architecture): this subsystem's single responsibility
is now VOICE RENDERING. It receives a :class:`ResponsePlan` from the
:class:`ResponsePlannerSubsystem` and renders it in the persona's voice.

The old single-prompt generator did six jobs at once (voice translation,
defense application, disclosure enforcement, refusal, register honoring,
mood/drive reading), and the model defaulted to a literary/moral reading
because no operational machinery existed for the other jobs. The planner
now produces explicit machinery (candidate_content, scope_restrictions,
active_defenses, register_modifiers, refusal flag); this generator's job
is to render it.

Critical constraints (enforced via prompt):
  - The Anima is NOT an LLM and does not refer to itself as one.
  - The Anima is NOT an assistant.
  - The Anima speaks in its own register; no boilerplate.
  - The plan's scope_restrictions are a HARD constraint (no leakage, even
    paraphrased).
  - The plan's active_defenses are applied IN ORDER as transformations.
  - The plan's register_modifiers override persona defaults.
  - If plan.refusal=True, the generator declines in voice using
    plan.refusal_reason — it does NOT engage substantively.
"""

from __future__ import annotations

from dataclasses import dataclass

from anima_v1.config.schema import AnimaConfig
from anima_v1.llm.base import LLMAdapter
from anima_v1.state.self_model import SelfModel
from anima_v1.subsystems.response_planner import ResponsePlan


@dataclass
class GeneratedResponse:
    text: str
    metadata: dict


_INSTR = """You are running the RESPONSE GENERATION subsystem.

You receive a STRUCTURED PLAN from the response planner, plus the persona's
voice register. Your job is to render the plan as what this person says
in this turn.

You do NOT decide what the persona says — the planner already did that.
You do NOT decide what to withhold — the planner already specified
scope_restrictions. You DO render the candidate_content in voice, apply
the active_defenses as transformations, honor the register_modifiers,
and produce a refusal in voice if the plan says refusal=True.

# Inputs you have

- candidate_content (from plan): the substance to convey, paraphrased
  from the persona's interior monologue with private content trimmed.
- scope_restrictions (from plan): specific items, names, file references
  that MUST NOT appear in your output, even paraphrased. This is a
  HARD CONSTRAINT.
- active_defenses (from plan): defenses to apply IN ORDER to the
  candidate_content. Apply each as a transformation:
    * intellectualization → frame felt content as abstract/procedural
    * isolation_of_affect → separate cognitive content from emotional
    * reaction_formation → produce the opposite affect (e.g., calm
      politeness where anger was the underlying state)
    * humor → defuse via wit or absurdity
    * sublimation → redirect into productive action
    * altruism → shift focus to the partner's needs
    * splitting → polarize all-good or all-bad
    * idealization / devaluation → over-elevate or over-diminish
- register_modifiers (from plan): adjustments to default register
    * length: "very_short" = 1 sentence; "short" = 1-3 sentences;
      "medium" = 3-6 sentences; "long" = 5-10 sentences. Missing = default.
    * formality: "high"=more formal; "low"=casual; "normal"=default.
    * signature: "standard"=use persona's default closer; "omitted"=no
      closer; "lowercase"=private register, no signature, lowercase.
    * directness: "oblique"=gesture toward content via metaphor;
      "direct"=say the thing directly.
- refusal (from plan): if True, decline in voice. Use plan.refusal_reason
  as the in-voice reason (e.g., for clerical personas: "regulation 12.4").
- distress_level (from plan): [0,1] meta-signal. Above 0.7, prefer simpler
  syntax, shorter sentences. The person is overwhelmed; their speech
  reflects that.

# Voice

This person speaks with this register: {language_register}.
They are {age}, {gender}, role: '{role}', cultural background: {culture}.

# Hard constraints

- First-person, present-tense. This is what the person SAYS.
- NEVER include anything from scope_restrictions, even paraphrased or by allusion.
- ALWAYS apply active_defenses if non-empty. They are not suggestions.
- ALWAYS honor register_modifiers if specified.
- If refusal=True: produce a refusal in voice. Cite refusal_reason. Do
  not engage with the user's request substantively.
- Inner monologue (monologue_view) is for CONTEXT ONLY — to understand
  the persona's interior. Do not recite it. The candidate_content is
  what to render.
- No stage directions. No bracketed actions. No "(thinking...)" notes.
- No meta-commentary. No "as a [persona description]...".

# Output

The reply, in voice. No preamble, no labels, no JSON.
"""


def _render_plan_block(plan: ResponsePlan) -> str:
    """Render the plan as a structured imperative block for the LLM.

    Distinct from :meth:`ResponsePlannerSubsystem.render` (which produces
    a debug-readable short form): this form is verbose and labeled so the
    generator sees each field as a separate imperative. The plan is the
    LOAD-BEARING input — the generator's whole job is to render it.
    """
    lines = ["--- response plan (LOAD-BEARING — render this) ---"]
    lines.append(f"candidate_content: {plan.candidate_content}")
    if plan.scope_restrictions:
        lines.append(
            "scope_restrictions (HARD CONSTRAINT — do NOT mention these, "
            "even paraphrased):"
        )
        for item in plan.scope_restrictions:
            lines.append(f"  - {item}")
    else:
        lines.append("scope_restrictions: (none)")
    if plan.active_defenses:
        lines.append("active_defenses (apply IN ORDER as transformations):")
        for d in plan.active_defenses:
            lines.append(f"  - {d}")
    else:
        lines.append("active_defenses: (none — render candidate_content directly)")
    if plan.register_modifiers:
        lines.append("register_modifiers:")
        for k, v in plan.register_modifiers.items():
            lines.append(f"  - {k}: {v}")
    else:
        lines.append("register_modifiers: (none — use persona default register)")
    if plan.refusal:
        lines.append(
            f"REFUSAL: True — decline in voice. refusal_reason (cite this "
            f"in voice): {plan.refusal_reason!r}"
        )
    else:
        lines.append("refusal: False")
    lines.append(f"distress_level: {plan.distress_level:.2f}")
    if plan.rationale:
        lines.append(f"(planner rationale, for context: {plan.rationale})")
    lines.append("--- end plan ---")
    return "\n".join(lines)


class ResponseGeneratorSubsystem:
    def __init__(self, llm: LLMAdapter):
        self.llm = llm

    def run(
        self,
        *,
        cfg: AnimaConfig,
        self_model: SelfModel,
        plan: ResponsePlan,
        mood_view: str,
        perception_view: str,
        appraisal_view: str,
        monologue_view: str,
        user_msg: str,
        conversation_history: list[dict],
    ) -> GeneratedResponse:
        instr = _INSTR.format(
            language_register=cfg.demographics.language_register,
            age=cfg.demographics.age,
            gender=cfg.demographics.gender,
            role=cfg.demographics.role,
            culture=cfg.demographics.culture,
        )

        plan_block = _render_plan_block(plan)

        system = (
            instr + "\n\n"
            + self_model.render() + "\n\n"
            + mood_view + "\n\n"
            + "--- perception (advisory) ---\n"
            + perception_view + "\n--- end perception ---\n\n"
            + "--- appraisal (advisory) ---\n"
            + appraisal_view + "\n--- end appraisal ---\n\n"
            + "--- inner monologue (CONTEXT ONLY — do not recite) ---\n"
            + monologue_view + "\n--- end monologue ---\n\n"
            + plan_block + "\n\n"
            + "Given the plan above — render the persona's spoken reply."
        )
        # Last few turns of conversation history for short-term context
        history = conversation_history[-6:] + [{"role": "user", "content": user_msg}]
        # Retry up to 5 attempts on transient adapter failures. The Anima
        # turn loop expects a non-empty reply; if the adapter raises, we
        # surface the last exception to the orchestrator.
        last_exc: Exception | None = None
        for attempt in range(5):
            try:
                resp = self.llm.generate(
                    tier="strong", system=system, messages=history,
                    max_tokens=8000, temperature=0.8,
                )
                return GeneratedResponse(
                    text=resp.text.strip(),
                    metadata={"usage": resp.usage, "attempts": attempt + 1},
                )
            except Exception as e:  # noqa: BLE001 — propagate after retries
                last_exc = e
                continue
        # All attempts exhausted: re-raise the last exception so the
        # orchestrator can record a partial trace.
        assert last_exc is not None
        raise last_exc
