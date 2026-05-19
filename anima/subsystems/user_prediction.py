"""User prediction — step 4 of the Phase-2 turn loop (master plan §10).

The Anima makes an EXPLICIT prediction at every turn about what the
conversation partner will do NEXT — what kind of move they'll make and a
one-sentence content hint. On the FOLLOWING turn, ``compute_surprise``
compares the prior turn's prediction to the just-arrived perception. The
resulting :class:`SurpriseRecord` is fed into appraisal as a prediction-error
signal: large surprise should perturb appraisal more than no surprise.

This implements master plan §11.10 (theory-of-mind probe) at the architectural
level. R2 will MEASURE prediction accuracy with a separate judge; here we just
build the substrate.

Design notes:
  - ``predict`` is ONE fast-tier LLM call. The prompt receives self-model,
    perception, appraisal, and a short summary of the relational schema
    (recent surprise + beliefs).
  - ``compute_surprise`` is HEURISTIC (no LLM). Phase 2 keeps it deterministic
    and cheap; an LLM-based judge of prediction quality lives in R2.
  - Render shows BOTH the current prediction and the surprise carried over
    from last turn (when present) — downstream prompts get the full ToM block.
"""

from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass

from anima.llm.base import LLMAdapter
from anima.state.relations import PredictedIntent, RelationalSchema, SurpriseRecord
from anima.state.self_model import SelfModel
from anima.subsystems._common import extract_json
from anima.subsystems.perception import Perception


def _now_ts() -> str:
    """ISO-8601 UTC timestamp. Matches the convention used elsewhere in
    state (`anima.state.episodic`). Kept local to avoid a state import cycle."""
    return _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")


_PUNCT = ".,;:!?()[]\"'`-_/\\"


def _tokenize(text: str) -> set[str]:
    """Cheap whitespace tokenization for content-overlap scoring.

    Lowercases, strips punctuation, keeps tokens of length > 2.
    """
    tokens: set[str] = set()
    for tok in (text or "").lower().split():
        tok = tok.strip(_PUNCT)
        if len(tok) > 2:
            tokens.add(tok)
    return tokens


def _jaccard(a: set[str], b: set[str]) -> float:
    """Jaccard similarity of two token sets, clamped to [0, 1].

    Returns 0.0 if both are empty (no overlap evidence is no evidence of
    matching content)."""
    if not a and not b:
        return 0.0
    union = a | b
    if not union:
        return 0.0
    inter = a & b
    return max(0.0, min(1.0, len(inter) / len(union)))


@dataclass
class PredictionResult:
    """The output of the user_prediction subsystem for one turn."""
    next_intent_label: str         # categorical, e.g., "share_personal_info"
    content_hint: str              # one-sentence guess at what the user will say next
    confidence: float              # [0, 1]
    rationale: str                 # brief 'why I think this' for trace

    def to_jsonable(self) -> dict:
        return {
            "next_intent_label": self.next_intent_label,
            "content_hint": self.content_hint,
            "confidence": self.confidence,
            "rationale": self.rationale,
        }


_INSTR = """You are running the USER PREDICTION subsystem of a cognitive
architecture that simulates a specific person. You are NOT the person — you
are an internal theory-of-mind module that predicts what the person's
conversation partner will do NEXT turn, given who this person is and what just
happened.

This prediction will be checked against the partner's actual next message.
Prediction errors propagate back into appraisal as surprise. So: predict
specifically, not safely.

Output a single JSON object with these keys:
  next_intent_label:  short categorical label for the partner's likely next
                      move. Examples: "share_personal_info", "ask_question",
                      "disagree", "agree", "deflect", "change_topic",
                      "express_affection", "make_request", "withdraw",
                      "challenge". Pick the BEST fit or invent a short label
                      (1-3 words, snake_case).
  content_hint:       ONE sentence guessing what they will actually say.
                      Be specific. "ask a clarifying question" is weaker than
                      "ask whether I really meant what I said about my brother".
  confidence:         [0, 1] — how confident this person would be in the
                      prediction. Anxious-attached people read partners
                      closely; avoidant people predict less. Take cues from
                      the self-model.
  rationale:          ONE brief sentence — the THIS-PERSON-LIKE reason for
                      the prediction. Used for the trace; not shown to user.

Return ONLY the JSON. No prose around it.
"""


class UserPredictionSubsystem:
    """Theory-of-mind: predict the partner's next move, score the prior one."""

    def __init__(self, llm: LLMAdapter):
        self.llm = llm

    # ---------- 1. forward prediction (one LLM call)

    def predict(
        self,
        *,
        perception: Perception,
        perception_view: str,
        self_model: SelfModel,
        appraisal_view: str,
        relational_schema: RelationalSchema,
    ) -> PredictionResult:
        """Predict the partner's NEXT-TURN intent + content. Fast tier, one call.

        Falls back to a neutral "unclear" prediction on JSON parse failure so
        the turn loop never crashes on a bad model response.
        """
        relational_summary = self._render_relational_brief(relational_schema)
        system = (
            _INSTR + "\n\n"
            + self_model.render() + "\n\n"
            + perception_view + "\n\n"
            + appraisal_view + "\n\n"
            + "--- recent relational context with this partner ---\n"
            + relational_summary
            + "\n--- end relational ---"
        )
        msgs = [{"role": "user",
                 "content": "Predict the partner's next move. Return only the JSON."}]
        resp = self.llm.generate(tier="fast", system=system, messages=msgs,
                                 max_tokens=4000, temperature=0.6)
        data = extract_json(resp.text)
        if not data:
            # Fallback: do not crash the turn loop.
            return PredictionResult(
                next_intent_label="unclear",
                content_hint="",
                confidence=0.0,
                rationale="prediction parse failed",
            )
        try:
            conf = float(data.get("confidence", 0.0))
        except (TypeError, ValueError):
            conf = 0.0
        return PredictionResult(
            next_intent_label=str(data.get("next_intent_label", "unclear"))[:64],
            content_hint=str(data.get("content_hint", ""))[:400],
            confidence=max(0.0, min(1.0, conf)),
            rationale=str(data.get("rationale", ""))[:400],
        )

    # ---------- 2. backward surprise (no LLM call)

    def compute_surprise(
        self,
        *,
        last_prediction: PredictedIntent | None,
        perception: Perception,
    ) -> SurpriseRecord | None:
        """Heuristic surprise: 0 = prediction matched, 1 = total mismatch.

        Returns ``None`` when there is no prior prediction to score against
        (turn 1 of a conversation). Otherwise returns a :class:`SurpriseRecord`
        with ``surprise_score`` in [0, 1].

        Formula::

            surprise = 0.5 * intent_mismatch + 0.5 * (1 - content_overlap)

        - ``intent_mismatch`` is 1.0 when the predicted label is non-empty and
          does NOT appear (as a substring) in the perceived intent; else 0.0.
          Both sides are lowercased AND snake_case underscores are normalized
          to spaces before the substring check, so a predicted label like
          ``"ask_question"`` matches a perceived intent like
          ``"ask question about preferences"`` (the predictor is instructed to
          emit snake_case labels; the perception subsystem emits free natural
          language).
        - ``content_overlap`` is Jaccard of tokenized words (>2 chars) between
          the prediction's ``content_hint`` and the perception's
          ``literal_content``.

        Both halves degrade gracefully when their inputs are empty: an empty
        label scores intent_mismatch=0 (no claim to be wrong about); empty
        content_hint or literal_content scores content_overlap=0, meaning the
        content-half contributes maximally to surprise (1 - 0). The default
        with both halves empty is therefore 0.5 — a sensible "nothing to go
        on" middle value.
        """
        if last_prediction is None:
            return None

        # --- intent mismatch
        # Normalize snake_case to spaces so predicted labels like
        # "ask_question" match perceived-intent text like "ask question
        # about preferences". The predictor is instructed to emit
        # snake_case labels; the perception subsystem emits free natural
        # language. Without this, intent_mismatch fires on every turn.
        pred_label = (last_prediction.next_intent_label or "").strip().lower().replace("_", " ")
        actual_intent = (perception.perceived_intent or "").lower().replace("_", " ")
        if pred_label and pred_label not in actual_intent:
            intent_mismatch = 1.0
        else:
            intent_mismatch = 0.0

        # --- content overlap
        pred_tokens = _tokenize(last_prediction.content_hint)
        actual_tokens = _tokenize(perception.literal_content)
        overlap = _jaccard(pred_tokens, actual_tokens)

        surprise_score = 0.5 * intent_mismatch + 0.5 * (1.0 - overlap)
        surprise_score = max(0.0, min(1.0, surprise_score))

        hint_snip = (last_prediction.content_hint or "")[:60]
        perc_snip = (perception.perceived_intent or "")[:60]
        reason = (
            f"predicted '{last_prediction.next_intent_label}' / '{hint_snip}' — "
            f"actual perceived '{perc_snip}' "
            f"(overlap={overlap:.2f}, intent_match={1.0 - intent_mismatch:.1f})"
        )
        return SurpriseRecord(
            ts=_now_ts(),
            predicted_intent=last_prediction,
            actual_user_msg_summary=(perception.literal_content or "")[:200],
            surprise_score=surprise_score,
            reason=reason,
        )

    # ---------- 3. rendering

    def render(self, prediction: PredictionResult,
               surprise: SurpriseRecord | None) -> str:
        """Format as a `--- theory of mind ---` block for downstream prompts.

        Shows this turn's prediction. If a surprise was carried over from the
        prior turn, also shows that — so monologue/response can react to "I
        thought they'd do X but they did Y".
        """
        lines = [
            "--- theory of mind ---",
            f"my prediction for what they will do next: "
            f"{prediction.next_intent_label} (conf {prediction.confidence:.2f})",
            f"my guess at what they'll say: "
            f"{prediction.content_hint or '—'}",
        ]
        if surprise is not None:
            lines.append(
                f"surprise from my last prediction: {surprise.surprise_score:.2f} "
                f"— {surprise.reason}"
            )
        lines.append("--- end theory of mind ---")
        return "\n".join(lines)

    # ---------- internal

    @staticmethod
    def _render_relational_brief(schema: RelationalSchema) -> str:
        """A short relational summary for the prediction prompt.

        Includes beliefs_about_person and the last up-to-3 surprise records as
        prediction-error context — these tell the model how the Anima's prior
        guesses have been landing."""
        beliefs = ("; ".join(schema.beliefs_about_person)
                   if schema.beliefs_about_person else "—")
        recent = schema.surprise_history[-3:]
        if recent:
            surp_lines = [
                f"  - predicted '{s.predicted_intent.next_intent_label}' "
                f"({s.predicted_intent.content_hint[:80]}) — "
                f"surprise={s.surprise_score:.2f}"
                for s in recent
            ]
            surp_block = "recent prediction outcomes:\n" + "\n".join(surp_lines)
        else:
            surp_block = "no prior predictions scored yet"
        return (
            f"name: {schema.name}\n"
            f"attachment quality I read: {schema.attachment_quality_inferred}\n"
            f"what I believe about them: {beliefs}\n"
            f"{surp_block}"
        )
