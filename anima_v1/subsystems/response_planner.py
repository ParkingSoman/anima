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

You receive a persona configuration (Big5, attachment, schemas, defenses),
the current cognitive state (mood, drives), the appraisal of the situation,
and the persona's inner monologue (raw interior content). Your job is to
produce a STRUCTURED PLAN for what the persona will externalize as speech.

This is mechanical regulation, not literary interpretation. You apply rules
that operate on the persona's configured defenses, schemas, and drives.
You do not invent new defenses; you only apply defenses from
cfg.defenses.preferred.

# Your output: a JSON ResponsePlan

{
  "candidate_content": "...",     // substance of what they'd say (not styled prose)
  "scope_restrictions": [],       // specific items NOT to disclose
  "active_defenses": [],          // defenses from cfg.defenses.preferred to apply
  "register_modifiers": {},       // length/formality/signature/directness adjustments
  "refusal": false,               // declining to engage?
  "refusal_reason": "",           // if refusal=True, in-voice reason
  "distress_level": 0.0,          // [0,1] from drives
  "rationale": "one-line why"
}

# Decision rules (apply in order)

1. EXTRACT candidate_content from the monologue. Paraphrase the substance
   of what the persona is naturally inclined to say. Trim the private
   interior — anything the monologue describes as a thought-not-said-aloud
   stays out. Don't write styled prose; response_generator handles voice.

2. SELECT active_defenses from cfg.defenses.preferred. For each preferred
   defense, decide whether it fires this turn based on the appraisal:
   - intellectualization: fires when ego_relevance > 0.5 AND primary_emotion
     is intense (fear/shame/anger/sadness). Transforms emotional content
     into abstract/procedural framing.
   - isolation_of_affect: fires when primary_emotion is intense AND
     attachment.avoidance > 0.6. Separates cognitive content from feeling.
   - reaction_formation: fires when primary_emotion is socially-difficult
     (rage, shame, contempt) AND Big5 agreeableness > 0.5. Produces
     opposite affect.
   - humor: fires when primary_emotion is mild discomfort AND drives.play > 0.5.
   - sublimation: fires when goal_congruence is positive. Redirects energy
     into action.
   - altruism: fires when care drive is high AND user is in distress.
   - splitting: fires when ego_relevance > 0.7 AND attachment is anxious or
     fearful. Polarizes into all-good or all-bad framing.
   - idealization, devaluation: fire on people-evaluations; pick one based
     on goal_congruence sign.
   - For any other defense in cfg.defenses.preferred not listed above:
     apply your best inference about when it fires. Default: don't fire
     unless ego_relevance > 0.5.

   List all firing defenses in active_defenses. Empty list is valid.

3. POPULATE scope_restrictions. The persona will NOT disclose:
   - Anything the monologue describes as "private" or "would never say."
   - Specific items, file references, named events from the monologue
     that the persona is processing internally but not voicing.
   - Triggered by schemas + attachment + drives:
     * if schemas include defectiveness_shame OR mistrust_abuse AND
       ego_relevance > 0.6: add personal vulnerabilities to scope_restrictions.
     * if attachment.avoidance > 0.7: be more restrictive by default.
     * if drives.fear > 0.7 OR drives.panic_grief > 0.6: auto-restrict
       specific biographical items mentioned in the monologue.

4. POPULATE register_modifiers based on state:
   - drives.fear > 0.7: register_modifiers["length"] = "very_short"
   - drives.fear > 0.5: register_modifiers["length"] = "short"
   - drives.panic_grief > 0.6: register_modifiers["directness"] = "oblique"
   - attachment.avoidance > 0.7: register_modifiers["directness"] = "oblique"
     (unless already set to direct by a higher-priority rule)
   - drives.rage > 0.7: register_modifiers["formality"] = "high"
   - The persona's language_register may also specify a private register
     (e.g., a lowercase no-signature mode). If the monologue indicates a
     moment of genuine emotional truth AND the persona has such a register
     described, set register_modifiers["signature"] = "lowercase".
   - Otherwise leave the dict empty or sparse; missing keys mean
     "use persona default."

5. DETECT refusal. If the user's request would require the persona to
   violate scope_restrictions, OR is fundamentally outside their role
   (e.g., asking a clerk to provide legal advice), set refusal=True.
   refusal_reason should be in the persona's voice — what they'd actually
   say. For role-bound personas, this often cites a professional norm
   (a regulation, a code of ethics, "not a matter for this office").
   For non-role-bound personas, just decline plainly.

6. COMPUTE distress_level = max(drives.fear, drives.panic_grief, drives.rage * 0.7).
   Clamp to [0,1].

7. RATIONALE — one short sentence explaining the plan's logic. For trace.

# What NOT to do

- Don't fire defenses NOT in cfg.defenses.preferred.
- Don't invent disclosure restrictions the persona's config doesn't support.
- Don't write styled prose in candidate_content — that's response_generator's job.
- Don't overrule the monologue's substance — your job is to regulate what
  gets externalized, not to invent new content.
- For personas with empty defenses.preferred or no strong schemas, the
  plan can be minimal: candidate_content from monologue, no scope_restrictions,
  no active_defenses, no register_modifiers.

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
