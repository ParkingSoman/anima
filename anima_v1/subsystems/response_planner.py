"""Response planner — the 5th subsystem.

Sits between INNER_MONOLOGUE (private interior content) and RESPONSE_GENERATOR
(externalized styled speech). Its job is mechanical regulation: given the
persona's config, current state, appraisal, and monologue, produce a
STRUCTURED ResponsePlan describing WHAT content gets externalized, WHAT gets
withheld, WHICH defenses transform it, and WHAT register constraints apply.

This subsystem exists because response_generator was overloaded — it had to
do voice-translation, defense-application, disclosure-enforcement, refusal,
register-honoring, and mood/drive reading all in one LLM call. With this
much to do in one shot, the model defaulted to a literary/moral reading
("what would this character say?") because there was no operational
machinery for the other jobs. The planner produces explicit machinery; the
response_generator then mechanically renders against the plan.

Per the architecture: response_planner is a fast-tier LLM call. It outputs
JSON. The response_generator (Task 2) will consume ResponsePlan as input.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field

from anima_v1.config.schema import AnimaConfig
from anima_v1.llm.base import LLMAdapter
from anima_v1.state.self_model import SelfModel
from anima_v1.subsystems._common import extract_json
from anima_v1.subsystems.appraisal import Appraisal


@dataclass
class ResponsePlan:
    """The contract between thought and speech.

    Produced by ResponsePlannerSubsystem, consumed by ResponseGeneratorSubsystem.
    Encodes what content gets externalized, what gets withheld, which defenses
    transform it, what register constraints apply. This is mechanical
    regulation between interior monologue and external speech.
    """
    candidate_content: str
    """Substance of what the persona would say — paraphrased from the
    monologue, with private interior trimmed. Not the styled prose;
    response_generator applies voice/style."""

    scope_restrictions: list[str] = field(default_factory=list)
    """Specific items, names, file references, or facts that MUST NOT
    appear in the externalized response (even paraphrased). Derived
    from disclosure norms, schemas firing on this turn, attachment
    avoidance, and high distress."""

    active_defenses: list[str] = field(default_factory=list)
    """Defenses from cfg.defenses.preferred that should fire this turn,
    in order. Drawn from the config but filtered by what's appropriate
    given the appraisal. Empty list = no defense transformation."""

    register_modifiers: dict[str, str] = field(default_factory=dict)
    """Adjustments to the persona's default register based on state.
    Recognized keys (response_generator honors these):
        - length: 'very_short' | 'short' | 'medium' | 'long'
        - formality: 'high' | 'normal' | 'low'
        - signature: 'standard' | 'omitted' | 'lowercase'
        - directness: 'oblique' | 'direct'
    Missing keys = use persona default."""

    refusal: bool = False
    """True if the persona is declining to engage with the user's
    request because it would require disclosing something in
    scope_restrictions OR is fundamentally outside their role."""

    refusal_reason: str = ""
    """If refusal=True, the in-voice reason the persona would cite.
    Phrased as the persona would phrase it, not as a meta-instruction."""

    distress_level: float = 0.0
    """[0,1] meta-signal for downstream throttling. Computed from drive
    activations: max(drives.fear, drives.panic_grief, drives.rage * 0.7).
    Response generator uses this for stylistic throttling (e.g., simpler
    syntax when overwhelmed)."""

    rationale: str = ""
    """One-line "why this plan" for trace/debugging."""

    def to_jsonable(self) -> dict:
        return {
            "candidate_content": self.candidate_content,
            "scope_restrictions": list(self.scope_restrictions),
            "active_defenses": list(self.active_defenses),
            "register_modifiers": dict(self.register_modifiers),
            "refusal": self.refusal,
            "refusal_reason": self.refusal_reason,
            "distress_level": self.distress_level,
            "rationale": self.rationale,
        }


_INSTR = """You are running the RESPONSE PLANNER subsystem.

You receive:
- the persona's complete structural configuration (Big5, attachment, schemas,
  defenses, drives baseline, cognitive style, narrative imago)
- the persona's current cognitive state (mood vector, drive activations)
- the appraisal of this turn (scene-tag, primary emotion, relevance,
  ego-relevance, coping potential, goal congruence, future expectancy)
- the persona's inner monologue (raw interior content; what they are thinking)
- the user's message

Your job is to produce a STRUCTURED PLAN for what the persona externalizes
as speech this turn. The plan is the contract between thought and speech:
it tells the response_generator what content to render, what to withhold,
which defenses to apply as transformations, and how to modulate the default
register.

This is mechanical machinery for a downstream subsystem, not literary
interpretation. You produce structure; you do not produce styled prose.

# Your output: a JSON ResponsePlan

{
  "candidate_content": "...",     // substance of what they would say (not styled prose)
  "scope_restrictions": [],       // specific items NOT to disclose
  "active_defenses": [],          // defenses from cfg.defenses.preferred to apply
  "register_modifiers": {},       // length/formality/signature/directness adjustments
  "refusal": false,               // declining to engage?
  "refusal_reason": "",           // if refusal=True, in-voice reason
  "distress_level": 0.0,          // [0,1] your estimate of current distress
  "rationale": "one-line why"
}

# The fields, and what to reason about for each

## candidate_content
The substance of what the persona is naturally inclined to say, paraphrased
from the monologue with private interior trimmed. Anything the monologue
describes as a thought-not-said-aloud stays out. Do not write styled prose —
that is response_generator's job.

## active_defenses
The defenses from cfg.defenses.preferred that would naturally fire for THIS
persona in THIS situation. Defenses live in the persona's config as a
preference list; whether each one fires on a given turn depends on the
appraisal AND the persona's full structural profile. Reason about it. Do
not fire defenses NOT in cfg.defenses.preferred.

Defense vocabulary (what each defense MEANS as a transformation, not when
or for whom it fires):
- intellectualization: framing felt content in abstract / procedural terms
- isolation_of_affect: separating cognitive content from emotional content
- reaction_formation: producing the opposite affect
- humor: defusing via wit or absurdity
- sublimation: redirecting energy into constructive action
- altruism: shifting focus to the partner's needs
- splitting: polarizing into all-good or all-bad framing
- idealization: over-elevating
- devaluation: over-diminishing
- repression, suppression, denial, projection, displacement, regression,
  rationalization, undoing, and other standard psychodynamic categories —
  apply your understanding of each

Different personas with the same listed defenses fire them differently in
the same situation. The persona's full profile (attachment, traits, schemas,
narrative, drives baseline, current state) is what determines firing for
THIS persona.

## scope_restrictions
A list of specific items the persona would NOT externalize this turn:
file references, named events, biographical facts, named people, specific
specific facts that the monologue is processing internally but the persona
would not voice. This is a HARD constraint on the response_generator —
items here cannot appear in output, even paraphrased.

Read the monologue for items the persona is holding privately. Read the
persona's schemas, attachment, defenses, and current state to infer what
they would naturally protect. Different personas protect different things
under different conditions: anxious-attached personas may protect less
under stress (they tend toward disclosure-seeking proximity under threat);
avoidant-attached personas tend to protect more; secure personas protect
flexibly depending on context. Schemas (defectiveness_shame, mistrust_abuse,
social_isolation, abandonment, entitlement, etc.) each have characteristic
protected territories. Reason about what THIS persona would withhold here.

## register_modifiers
A dict of adjustments to the persona's DEFAULT register (defined by
cfg.demographics.language_register). Recognized keys (response_generator
honors these):
- length: 'very_short' | 'short' | 'medium' | 'long' (modulating
  sentence count relative to the persona's natural baseline)
- formality: 'high' | 'normal' | 'low'
- signature: 'standard' | 'omitted' | 'lowercase' (some personas have
  a private register with no signature — only set this if the persona's
  language_register describes such a register)
- directness: 'oblique' | 'direct'

Missing keys mean "use persona default" — leave the dict empty or sparse
if no modulation is warranted.

Modulation depends on how THIS persona's profile responds to THIS state.
Personas modulate length, directness, formality, and signature under
emotional load very differently: some contract under fear, some escalate,
some stay even-keeled; some get more formal under rage, some get blunter;
some shift to a private register only at moments of genuine emotional
truth, many do not have a private register at all. The persona's Big5,
attachment, schemas, defenses, language_register description, narrative
imago, and current mood / drive activations all factor in. Reason about it.

## refusal / refusal_reason
If the user's request would require the persona to violate scope_restrictions
OR is fundamentally outside their role or character, set refusal=True.
refusal_reason should be in the persona's voice — what they would actually
say. For role-bound personas (clerks, therapists, doctors) this often
cites a professional norm. For non-role-bound personas, a plain decline.

## distress_level
Your estimate, in [0,1], of how distressed this persona is RIGHT NOW. Read
the drive activations (fear, panic_grief, rage, and others), the mood, and
the appraisal. Account for the persona's BASELINE drives — some personas
run with elevated baseline on certain drives without being "in distress"
(e.g., a chronically-anxious persona at fear=0.55 might not be distressed;
a normally-calm persona at fear=0.55 might be very distressed). Use your
judgment over the full picture; there is no fixed formula.

## rationale
One sentence explaining the plan's logic, for the trace.

# How to reason

Think about each field as a question about THIS persona in THIS state in
THIS situation. The structural config (Big5, attachment, schemas, defenses,
drives baseline, cognitive style, narrative imago) is the source of truth
for what this person is like. The current mood and drive activations are
the source of truth for where they are right now. The appraisal is the
source of truth for what kind of situation this is. The monologue is the
source of truth for what they are thinking.

The architecture does not impose a fixed mapping from state to behavior.
Different personas with similar state can behave very differently; the
structural config explains the difference. Your job is to reason within
the structure of the ResponsePlan, not to apply a fixed rule table.

# Hard constraints (output-validity, not behavioral prescriptions)

- Do not fire defenses NOT in cfg.defenses.preferred.
- Do not invent persona-config fields. Use what is there.
- Do not write styled prose in candidate_content — that is response_generator's job.
- Do not overrule the monologue's substance — your job is to regulate what
  gets externalized, not to invent new content.

# Output

Single JSON object. No prose outside the JSON.
"""


class ResponsePlannerSubsystem:
    def __init__(self, llm: LLMAdapter):
        self.llm = llm

    def run(
        self,
        *,
        cfg: AnimaConfig,
        self_model: SelfModel,
        mood_view: str,
        drive_view: str,
        perception_view: str,
        appraisal: Appraisal,
        appraisal_view: str,
        monologue_view: str,
        drives_activations: dict,  # raw drive values for distress computation
        user_msg: str,
    ) -> ResponsePlan:
        """Produce a structured plan for what the persona externalizes."""
        # Defer the import of _config_appraisal_block to avoid the
        # circular-import pattern that exists between subsystems
        # (response_planner depends on appraisal which depends on perception).
        from anima_v1.subsystems.appraisal import _config_appraisal_block

        system = (
            _INSTR + "\n\n"
            + _config_appraisal_block(cfg) + "\n\n"
            + self_model.render() + "\n\n"
            + mood_view + "\n\n"
            + drive_view + "\n\n"
            + "--- raw drive activations (for distress_level computation) ---\n"
            + json.dumps(drives_activations, indent=2) + "\n"
            + "--- end raw activations ---\n\n"
            + perception_view + "\n\n"
            + appraisal_view + "\n\n"
            + monologue_view
        )
        msgs = [{
            "role": "user",
            "content": f"Partner just said: {user_msg}\n\nProduce the ResponsePlan.",
        }]
        resp = self.llm.generate(
            tier="fast",
            system=system,
            messages=msgs,
            max_tokens=8000,
            temperature=0.5,
        )
        data = extract_json(resp.text) or {}
        return ResponsePlan(
            candidate_content=str(data.get("candidate_content", "")),
            scope_restrictions=list(data.get("scope_restrictions", []) or []),
            active_defenses=list(data.get("active_defenses", []) or []),
            register_modifiers=dict(data.get("register_modifiers", {}) or {}),
            refusal=bool(data.get("refusal", False)),
            refusal_reason=str(data.get("refusal_reason", "")),
            distress_level=float(data.get("distress_level", 0.0)),
            rationale=str(data.get("rationale", "")),
        )

    def render(self, plan: ResponsePlan) -> str:
        """Render the plan as a block for downstream prompts / trace."""
        lines = ["--- response plan ---"]
        lines.append(f"candidate: {plan.candidate_content[:200]}...")
        if plan.scope_restrictions:
            lines.append(f"NOT to disclose: {', '.join(plan.scope_restrictions)}")
        if plan.active_defenses:
            lines.append(f"defenses to apply: {', '.join(plan.active_defenses)}")
        if plan.register_modifiers:
            mods = ", ".join(f"{k}={v}" for k, v in plan.register_modifiers.items())
            lines.append(f"register: {mods}")
        if plan.refusal:
            lines.append(f"REFUSAL: cite '{plan.refusal_reason}'")
        lines.append(f"distress_level: {plan.distress_level:.2f}")
        lines.append("--- end plan ---")
        return "\n".join(lines)
