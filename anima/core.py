"""Anima — the top-level orchestrator.

Phase 1 MVP turn loop:
    perception → appraisal → inner_monologue → response_generator
"""

from __future__ import annotations

import copy
import datetime as _dt
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, TypeVar

from anima.config import AnimaConfig, load_config
from anima.llm.base import LLMAdapter
from anima.llm import make_adapter
from anima.llm.retry import RetryConfig, EmptyResponseAfterRetries
from anima.persistence.store import AnimaStore, AnimaStoreSnapshot
from anima.state.drives import DriveState
from anima.state.episodic import AffectTag, EpisodicEvent, EpisodicStore
from anima.state.mood import MoodVector
from anima.state.relations import PredictedIntent, RelationsStore
from anima.state.self_model import SelfModel
from anima.state.semantic import SemanticStore
from anima.subsystems.appraisal import Appraisal, AppraisalSubsystem
from anima.subsystems.errors import ResponseGenerationFailed, SubsystemError
from anima.subsystems.inner_monologue import InnerMonologueSubsystem, Monologue
from anima.subsystems.memory_retrieval import MemoryRetrieval
from anima.subsystems.perception import Perception, PerceptionSubsystem
from anima.subsystems.response_generator import (
    GeneratedResponse,
    ResponseGeneratorSubsystem,
)
from anima.subsystems.user_prediction import (
    PredictionResult,
    UserPredictionSubsystem,
    _now_ts,
)


T = TypeVar("T")


@dataclass
class TurnTrace:
    user_msg: str
    perception: dict
    appraisal: dict
    monologue: str
    mood_before: dict
    mood_after: dict
    drives_before: dict
    drives_after: dict
    response: str
    retrieved: list[dict] = field(default_factory=list)
    usage: dict = field(default_factory=dict)
    # E3: theory-of-mind trace fields.
    surprise_from_last_turn: dict = field(default_factory=dict)  # serialized SurpriseRecord or {}
    prediction: dict = field(default_factory=dict)               # serialized PredictionResult
    # E8: per-turn subsystem error records. Populated when a subsystem's LLM
    # call fails after all retries and the turn falls back to a structurally-
    # valid default. Empty on a clean turn.
    subsystem_errors: list[dict] = field(default_factory=list)
    # F1: per-turn "model chose silence" records. Populated when a subsystem's
    # LLM call SUCCEEDED but the output was empty in a subsystem-specific way
    # (empty monologue, empty response, unknown user prediction, etc.). This is
    # NOT an error — it's the model declining to produce content — and is
    # surfaced separately in the transcript from generation errors.
    silences: list[dict] = field(default_factory=list)
    # F2: when this turn is the result of /retry on a prior failed/degraded
    # turn, this points to that prior turn's index (1-based) in the transcript.
    # None on a normal turn.
    retry_of: int | None = None

    def to_jsonable(self) -> dict[str, Any]:
        """Serialize one turn for the §5.1 action-history record (append-only).

        All nested fields are already plain dicts/strings here (constructed
        from subsystem ``.to_jsonable()`` calls upstream), so this is a thin
        copy. Round-tripping is not required — the behavioral record is
        researcher-facing audit data, not read back by the Anima at runtime.
        """
        return {
            "user_msg": self.user_msg,
            "perception": dict(self.perception),
            "appraisal": dict(self.appraisal),
            "monologue": self.monologue,
            "mood_before": dict(self.mood_before),
            "mood_after": dict(self.mood_after),
            "drives_before": dict(self.drives_before),
            "drives_after": dict(self.drives_after),
            "response": self.response,
            "retrieved": [dict(r) for r in self.retrieved],
            "usage": dict(self.usage),
            "surprise_from_last_turn": dict(self.surprise_from_last_turn),
            "prediction": dict(self.prediction),
            "subsystem_errors": [dict(e) for e in self.subsystem_errors],
            "silences": [dict(s) for s in self.silences],
            "retry_of": self.retry_of,
        }


# E8: fallback values used when a subsystem's LLM call fails after retries.
# Each must be structurally valid for downstream consumers (no None traps).
def _fallback_perception(user_msg: str) -> Perception:
    return Perception(
        literal_content=user_msg[:1000],
        perceived_intent="unknown",
        perceived_valence=0.0,
        perceived_demands=[],
        salient_features=[],
    )


def _fallback_appraisal() -> Appraisal:
    return Appraisal(
        relevance=0.5,
        goal_congruence=0.0,
        ego_relevance=0.5,
        coping_potential=0.5,
        future_expectancy=0.0,
        primary_emotion="neutral",
        appraisal_scene_tag="unclassified",
        mood_dv=0.0,
        mood_da=0.0,
        mood_dd=0.0,
        discrete_deltas={},
        drive_deltas={},
    )


def _fallback_prediction() -> PredictionResult:
    return PredictionResult(
        next_intent_label="unknown",
        content_hint="",
        confidence=0.0,
        rationale="user prediction failed; using neutral fallback",
    )


def _fallback_monologue() -> Monologue:
    # Empty monologue. The response generator's prompt tolerates this — it
    # treats the (empty) "private thoughts" block as a non-signal and still
    # produces a reply on the appraisal + perception + register hint.
    return Monologue(text="", summary="")


class Anima:
    def __init__(self, cfg: AnimaConfig, llm: LLMAdapter | None = None,
                 *, ablate_monologue_length: bool = False,
                 store: AnimaStore | None = None,
                 autosave_every: int = 5):
        """Construct an Anima.

        Parameters
        ----------
        cfg: AnimaConfig
        llm: LLMAdapter, optional
        ablate_monologue_length: bool, default False
            If True, disable the parameter-aware monologue length
            computation in :class:`InnerMonologueSubsystem` and revert to a
            uniform 2–6 sentence directive (iter-1 behavior). The flag is
            stored on ``self`` and forwarded to ``_monologue.run`` per turn
            (the less-invasive plumbing — it keeps the subsystem stateless
            and avoids touching the shared constructor signature). Used by
            the research battery to isolate the causal contribution of the
            parameter-aware monologue. Default False — production behavior
            is byte-identical to before this kwarg existed.
        store: AnimaStore, optional
            Per-Anima JSON-on-disk persistence (E5). If supplied AND on-disk
            state exists for this Anima name, ``__init__`` hydrates §5.1 +
            §5.2 from the snapshot — wiring cross-session memory. If supplied
            but no on-disk state exists yet, the Anima starts fresh and will
            persist on autosave. If ``None`` (default), no persistence — the
            Phase 1 behavior.
        autosave_every: int, default 5
            Number of ``respond()`` calls between automatic saves. Only
            consulted when ``store`` is not None.
        """
        self.cfg = cfg
        self.llm = llm or make_adapter("anthropic")
        self.ablate_monologue_length = ablate_monologue_length
        self.self_model = SelfModel.from_config(cfg)
        self.mood = MoodVector.baseline_for(cfg.big5)
        self._mood_baseline = MoodVector.baseline_for(cfg.big5)
        self.drives = DriveState.from_baseline(cfg.drives)
        self.conversation_history: list[dict] = []
        self.recent_monologue_summary = ""
        self.relational_summary = ""

        self._perception = PerceptionSubsystem(self.llm)
        self._appraisal = AppraisalSubsystem(self.llm)
        self._monologue = InnerMonologueSubsystem(self.llm)
        self._response = ResponseGeneratorSubsystem(self.llm)
        self._memory = MemoryRetrieval(self.llm)
        self._user_prediction = UserPredictionSubsystem(self.llm)

        # Phase-2 episodic store. Empty at construction; E6 self-monitor will
        # populate it from each turn's encoding pass.
        self.episodic_store = EpisodicStore()

        # Phase-2 semantic store (§5.1). Empty at construction; consolidation
        # (Phase 4) writes here. Held on the Anima now so persistence (E5)
        # has a clear surface to load/save against.
        self.semantic_store = SemanticStore()

        # Phase-2 relational schemas (§5.2 / §6). Theory-of-mind state lives
        # here: predictions made about the user, surprise history, beliefs.
        self.relations = RelationsStore()
        self._user_relation = self.relations.get_or_create("user")

        self.traces: list[TurnTrace] = []

        # E5: per-Anima JSON persistence. Hydrate state from disk if a store
        # is provided and on-disk state exists. The §5.1/§5.2 separation is
        # preserved by reading the two regions back into their distinct stores.
        self._store = store
        self._autosave_every = max(1, int(autosave_every))
        self._turns_since_save = 0
        self._current_session_id: str | None = None

        if self._store is not None:
            snap = self._store.load()
            if snap is not None:
                self._hydrate_from_snapshot(snap)

        # F2: pre-turn snapshot for ``rollback_last_turn()``. Set at the start
        # of each ``respond()`` call (success or failure). ``None`` means
        # nothing-to-rollback (either no turn has been run yet, or the most
        # recent rollback already consumed the snapshot — idempotent).
        self._pre_turn_snapshot: dict[str, Any] | None = None

    @classmethod
    def from_config_path(cls, path: str | Path, llm: LLMAdapter | None = None,
                         *, ablate_monologue_length: bool = False) -> "Anima":
        return cls(load_config(path), llm=llm,
                   ablate_monologue_length=ablate_monologue_length)

    # ---------- the turn loop

    def respond(self, user_msg: str) -> tuple[str, TurnTrace]:
        # F2: snapshot all turn-modified state BEFORE the turn does anything,
        # so ``rollback_last_turn()`` can restore the pre-turn state if /retry
        # is invoked. Deep-copied so subsequent in-place mutations of mood /
        # drives / episodic_store / relations / traces do not leak into the
        # snapshot. The transcript writer is intentionally NOT snapshotted —
        # the transcript is the audit trail of what happened, not part of the
        # Anima's working state.
        self._pre_turn_snapshot = self._take_turn_snapshot()

        mood_view = self.mood.render()
        drive_view = self.drives.render()
        mood_before = {"valence": self.mood.valence, "arousal": self.mood.arousal,
                       "dominance": self.mood.dominance,
                       "discrete": dict(self.mood.discrete)}
        drives_before = dict(self.drives.activations)

        # E8: subsystem-error accumulator. Each safe-call below appends a
        # SubsystemError record on failure; the turn keeps going with a
        # structurally-valid fallback. The accumulator is attached to the
        # TurnTrace at the end so the transcript can surface what failed.
        errors: list[SubsystemError] = []
        # F1: silence accumulator. A subsystem call counts as "silence" when
        # it SUCCEEDED (so it's NOT in ``errors``) but its output is empty in
        # a subsystem-specific way. Populated after each subsystem call below.
        silences: list[dict] = []

        def _safe(subsystem: str, fn: Callable[[], T], fallback: T) -> T:
            """Run an LLM-backed subsystem call; on failure, log + fall back.

            The retry happens INSIDE the adapter (``RetryConfig`` default = 3
            attempts). By the time an exception reaches this helper, the
            adapter has already given up. We then build a SubsystemError
            record and return the fallback so the turn loop continues.

            Fix 1: when the adapter exhausts all attempts producing only
            empty/whitespace-only text, it raises
            :class:`EmptyResponseAfterRetries`. We surface that under the
            same SubsystemError shape so the operator can distinguish
            "model glitched and produced nothing" from "transport failed".
            The transcript renderer reads ``error_type ==
            'EmptyResponseAfterRetries'`` and uses a clearer wording.
            """
            try:
                return fn()
            except EmptyResponseAfterRetries as exc:
                # The exception carries its own attempts count; trust it
                # rather than re-deriving from the adapter's default config
                # (a per-call override may have used a different budget).
                errors.append(SubsystemError(
                    subsystem=subsystem,
                    error_type=type(exc).__name__,
                    message=str(exc)[:500],
                    attempts=int(getattr(exc, "attempts", 0) or 0),
                ))
                return fallback
            except Exception as exc:  # noqa: BLE001 — last-line defense per spec
                # The adapter's retry policy ran inside fn(); attempts reflects
                # the adapter default (or whatever override the subsystem used).
                attempts = getattr(self.llm, "retry_cfg", None)
                attempts_n = getattr(attempts, "max_attempts", 1) if attempts else 1
                errors.append(SubsystemError(
                    subsystem=subsystem,
                    error_type=type(exc).__name__,
                    message=str(exc)[:500],
                    attempts=attempts_n,
                ))
                return fallback

        # 1. perception
        perception = _safe(
            "perception",
            lambda: self._perception.run(
                user_msg=user_msg, self_model=self.self_model,
                mood_view=mood_view, relational_summary=self.relational_summary,
            ),
            _fallback_perception(user_msg),
        )
        perception_view = self._perception.render(perception)

        # 2. memory retrieval (Phase 2). Reconstructive recall — see
        # anima/subsystems/memory_retrieval.py. retrieval_view is appended to
        # every downstream subsystem prompt so appraisal/monologue/response
        # all read against the same surfaced memories.
        retrieved = _safe(
            "memory_retrieval",
            lambda: self._memory.run(
                perception=perception, perception_view=perception_view,
                self_model=self.self_model, mood=self.mood,
                active_schemas=[s.value for s in self.cfg.schemas],
                episodic_store=self.episodic_store,
                k=3,
            ),
            [],
        )
        retrieval_view = self._memory.render(retrieved)

        # F1: silence detection — memory_retrieval. If the call didn't error
        # (memory_retrieval not in errored set) and surfaced no memories,
        # that's the model declining to recall anything. We flag it as silence;
        # the trace section keeps its `(none surfaced)` rendering separately.
        _errored = {e.subsystem for e in errors}
        if "memory_retrieval" not in _errored and not retrieved:
            silences.append({
                "subsystem": "memory_retrieval",
                "detail": "surfaced 0 memories (LLM call succeeded; no memories matched the query)",
            })

        # 3a. surprise from last turn's prediction (master plan §10 / §11.10).
        # Pure-Python heuristic; no LLM call, so no retry needed.
        last_prediction = self._user_relation.last_prediction()
        surprise = self._user_prediction.compute_surprise(
            last_prediction=last_prediction, perception=perception,
        )
        if surprise is not None:
            self._user_relation.record_surprise(surprise)

        # 3. appraisal (now reads the surprise signal when present)
        appraisal = _safe(
            "appraisal",
            lambda: self._appraisal.run(
                cfg=self.cfg, self_model=self.self_model, mood_view=mood_view,
                drive_view=drive_view, perception=perception, perception_view=perception_view,
                retrieval_view=retrieval_view, surprise=surprise,
            ),
            _fallback_appraisal(),
        )
        # apply() is pure-Python state mutation; safe to call even on a fallback
        # appraisal (deltas are all zero).
        self._appraisal.apply(appraisal=appraisal, mood=self.mood, drives=self.drives)
        appraisal_view = self._appraisal.render(appraisal)

        # 4. user prediction (this turn's guess at next turn's user move).
        prediction = _safe(
            "user_prediction",
            lambda: self._user_prediction.predict(
                perception=perception, perception_view=perception_view,
                self_model=self.self_model, appraisal_view=appraisal_view,
                relational_schema=self._user_relation,
            ),
            _fallback_prediction(),
        )
        self._user_relation.record_prediction(PredictedIntent(
            ts=_now_ts(),
            perceived_input_summary=perception.literal_content[:200],
            next_intent_label=prediction.next_intent_label,
            content_hint=prediction.content_hint,
            confidence=prediction.confidence,
        ))
        prediction_view = self._user_prediction.render(prediction, surprise)

        # F1: silence detection — user_prediction. The trivial/floor output
        # (unknown intent, empty hint, zero confidence) means the model
        # declined to predict. We flag if it didn't error AND looks trivial.
        _errored = {e.subsystem for e in errors}
        if (
            "user_prediction" not in _errored
            and prediction.next_intent_label == "unknown"
            and prediction.content_hint == ""
            and prediction.confidence == 0.0
        ):
            silences.append({
                "subsystem": "user_prediction",
                "detail": (
                    "returned the trivial unknown/0.0 prediction "
                    "(LLM call succeeded; the model declined to make a prediction)"
                ),
            })

        # 5. inner monologue (re-render mood/drives so they reflect appraisal updates)
        post_mood_view = self.mood.render()
        post_drive_view = self.drives.render()
        monologue = _safe(
            "inner_monologue",
            lambda: self._monologue.run(
                cfg=self.cfg, self_model=self.self_model,
                mood_view=post_mood_view, drive_view=post_drive_view,
                perception_view=perception_view, appraisal_view=appraisal_view,
                relational_summary=self.relational_summary,
                recent_monologue_summary=self.recent_monologue_summary,
                user_msg=user_msg,
                ablate=self.ablate_monologue_length,
                retrieval_view=retrieval_view,
                prediction_view=prediction_view,
            ),
            _fallback_monologue(),
        )
        monologue_view = self._monologue.render(monologue)

        # F1: silence detection — inner_monologue. Empty / whitespace-only
        # text from a successful call is the model declining to think out loud.
        _errored = {e.subsystem for e in errors}
        if "inner_monologue" not in _errored and not monologue.text.strip():
            silences.append({
                "subsystem": "inner_monologue",
                "detail": "returned an empty string (LLM call succeeded; the model simply produced no content)",
            })

        # 6. response generation. THIS is the externally-visible subsystem;
        # heavier retry (5 attempts) is applied via per-call retry override.
        # If even 5 attempts fail we cannot synthesize a reply — we raise
        # ResponseGenerationFailed AFTER appending a partial TurnTrace so the
        # transcript records the failure.
        response_retry_cfg = RetryConfig(max_attempts=5)
        response: GeneratedResponse | None = None
        response_exc: BaseException | None = None
        try:
            response = self._response.run(
                cfg=self.cfg, self_model=self.self_model, mood_view=post_mood_view,
                perception_view=perception_view, appraisal_view=appraisal_view,
                monologue_view=monologue_view, user_msg=user_msg,
                conversation_history=self.conversation_history,
                retrieval_view=retrieval_view,
                prediction_view=prediction_view,
                retry_cfg=response_retry_cfg,
            )
        except Exception as exc:  # noqa: BLE001 — escalated below
            response_exc = exc
            # Fix 1: when the adapter exhausts attempts with all-empty
            # results, the exception carries its own ``attempts`` count.
            # Otherwise we fall back to the override budget (5) we set above.
            attempts_n = int(getattr(exc, "attempts", 0) or response_retry_cfg.max_attempts)
            errors.append(SubsystemError(
                subsystem="response_generator",
                error_type=type(exc).__name__,
                message=str(exc)[:500],
                attempts=attempts_n,
            ))

        if response_exc is not None:
            # Append a partial trace so the transcript captures the failed turn
            # even though no reply went out.
            partial = TurnTrace(
                user_msg=user_msg,
                perception=perception.__dict__,
                appraisal=appraisal.__dict__,
                monologue=monologue.text,
                mood_before=mood_before,
                mood_after={"valence": self.mood.valence, "arousal": self.mood.arousal,
                            "dominance": self.mood.dominance,
                            "discrete": dict(self.mood.discrete)},
                drives_before=drives_before,
                drives_after=dict(self.drives.activations),
                response="[generation failed after 5 attempts]",
                retrieved=[
                    {"id": rm.event.id, "score": rm.score,
                     "retrieval_reason": rm.retrieval_reason,
                     "reconstructed_framing": rm.reconstructed_framing}
                    for rm in retrieved
                ],
                usage={},
                surprise_from_last_turn=(surprise.to_jsonable() if surprise else {}),
                prediction=prediction.to_jsonable(),
                subsystem_errors=[e.to_jsonable() for e in errors],
                silences=list(silences),
            )
            self.traces.append(partial)
            raise ResponseGenerationFailed(
                subsystem="response_generator",
                attempts=response_retry_cfg.max_attempts,
                last_error=response_exc,
            )

        assert response is not None  # narrowed by the raise above

        # F1: silence detection — response_generator. The user-visible reply
        # being empty is the most surprising silence shape; we flag it loudly.
        if not response.text.strip():
            silences.append({
                "subsystem": "response_generator",
                "detail": "returned an empty reply (LLM call succeeded; the model chose to say nothing)",
            })

        # Bookkeeping
        self.conversation_history.append({"role": "user", "content": user_msg})
        self.conversation_history.append({"role": "assistant", "content": response.text})
        self.recent_monologue_summary = monologue.summary
        # Light mood-decay between turns (full decay-toward-baseline happens
        # offline in Phase 4+).
        self.mood.decay_toward(self._mood_baseline, rate=0.05)

        trace = TurnTrace(
            user_msg=user_msg,
            perception=perception.__dict__,
            appraisal=appraisal.__dict__,
            monologue=monologue.text,
            mood_before=mood_before,
            mood_after={"valence": self.mood.valence, "arousal": self.mood.arousal,
                        "dominance": self.mood.dominance,
                        "discrete": dict(self.mood.discrete)},
            drives_before=drives_before,
            drives_after=dict(self.drives.activations),
            response=response.text,
            retrieved=[
                {"id": rm.event.id, "score": rm.score,
                 "retrieval_reason": rm.retrieval_reason,
                 "reconstructed_framing": rm.reconstructed_framing}
                for rm in retrieved
            ],
            usage=response.metadata.get("usage", {}),
            surprise_from_last_turn=(surprise.to_jsonable() if surprise else {}),
            prediction=prediction.to_jsonable(),
            subsystem_errors=[e.to_jsonable() for e in errors],
            silences=list(silences),
        )
        self.traces.append(trace)

        # 10. self_monitor (E6). Encode this turn as an EpisodicEvent so the
        # retrieval subsystem has something to surface next turn. The Phase-2
        # importance score is a transparent linear blend of:
        #   (a) how much this turn mattered to the Anima (appraisal-derived),
        #   (b) how strong the felt experience was (mood-derived),
        #   (c) how much internal language it produced (monologue-length).
        # All operands clamped to [0,1]; weights sum to 1.0. ML-scored
        # importance is a later-phase upgrade — the heuristic is enough to
        # make cross-session memory functional today.
        # E8: self-monitor encoding is pure-Python state mutation. If
        # something raises here (e.g., affect_tag construction on weird
        # values), we log + continue — the response already went out, so
        # crashing now would be the worst possible time.
        try:
            importance = max(0.05, min(1.0,
                0.3 * abs(appraisal.ego_relevance)
                + 0.3 * abs(self.mood.valence)
                + 0.2 * min(1.0, len(monologue.text) / 600.0)
                + 0.2 * abs(appraisal.coping_potential)
            ))
            now_utc = _dt.datetime.now(_dt.timezone.utc)
            turn_num = len(self.episodic_store.events) + 1
            event_id = f"ev-{now_utc.strftime('%Y%m%dT%H%M%SZ')}-{turn_num}"
            ev = EpisodicEvent(
                id=event_id,
                ts=now_utc.isoformat(timespec="seconds"),
                content_summary=f"user: {user_msg[:80]}",
                full_content=f"user: {user_msg}\nself: {response.text}",
                participants=[self.cfg.biography.name.lower(), "user"],
                affect_tag=AffectTag.from_mood(self.mood),  # post-appraisal mood
                importance=importance,
                retrieval_count=0,
                links=[],
            )
            self.episodic_store.append(ev)
        except Exception as exc:  # noqa: BLE001 — defensive: don't crash post-reply
            trace.subsystem_errors.append(SubsystemError(
                subsystem="self_monitor",
                error_type=type(exc).__name__,
                message=str(exc)[:500],
                attempts=1,
            ).to_jsonable())

        # E5: autosave countdown. We tick AFTER the trace is appended so a
        # crash mid-turn doesn't leave a half-recorded turn on disk.
        if self._store is not None:
            self._turns_since_save += 1
            if self._turns_since_save >= self._autosave_every:
                self._autosave()

        return response.text, trace

    # ---------- F2 /retry support: pre-turn snapshot + rollback

    def _take_turn_snapshot(self) -> dict[str, Any]:
        """Deep-copy every piece of state ``respond()`` mutates.

        Targets (the union of what every code path inside ``respond()`` writes):
            * ``conversation_history`` — appended user + assistant messages
            * ``mood``                  — appraisal apply + decay_toward
            * ``drives``                — appraisal apply
            * ``recent_monologue_summary`` — set from monologue.summary
            * ``traces``                — partial OR full trace appended
            * ``episodic_store``        — self-monitor encoding appends an event
            * ``relations``             — record_prediction / record_surprise
              both mutate ``self._user_relation`` in-place
            * ``self_model``            — not mutated in respond() today, but
              snapshotted defensively (cheap; future-proofs against refactor)
            * ``_user_relation``        — re-pointed at the restored relations
              schema in ``rollback_last_turn()``
            * ``_turns_since_save``     — incremented for autosave bookkeeping

        Returns a dict the restore path consumes via ``rollback_last_turn()``.
        Deep copies are used uniformly — the perf hit is dwarfed by the LLM
        call that follows, and avoids subtle aliasing bugs around nested
        dataclasses (``DriveState.activations`` is a dict; ``MoodVector.discrete``
        is a dict; ``EpisodicStore._by_id`` is a derived dict).
        """
        return {
            "conversation_history": copy.deepcopy(self.conversation_history),
            "mood": copy.deepcopy(self.mood),
            "drives": copy.deepcopy(self.drives),
            "recent_monologue_summary": self.recent_monologue_summary,
            "traces": copy.deepcopy(self.traces),
            "episodic_store": copy.deepcopy(self.episodic_store),
            "relations": copy.deepcopy(self.relations),
            "self_model": copy.deepcopy(self.self_model),
            "_turns_since_save": self._turns_since_save,
        }

    def rollback_last_turn(self) -> bool:
        """Restore Anima state to immediately before the most recent ``respond()``.

        Used by the CLI ``/retry`` command to ensure that a failed (or
        degraded-with-fallbacks) turn does not pollute the context of the
        retry attempt. Specifically: the failed user message must not appear
        in ``conversation_history`` when the retry runs, and any mood / drive
        / episodic changes that the failed turn caused must be undone.

        Idempotent: calling twice rolls back at most once. After a successful
        rollback the snapshot slot is cleared, so a subsequent call returns
        ``False`` until the next ``respond()`` runs.

        The transcript is deliberately NOT rolled back — it is the audit
        trail; retries should appear as additional turns labeled
        ``retry_of: N-1`` in the JSON record and ``### Turn N — retry of
        turn N-1`` in the markdown.
        """
        if self._pre_turn_snapshot is None:
            return False
        snap = self._pre_turn_snapshot
        self.conversation_history = snap["conversation_history"]
        self.mood = snap["mood"]
        self.drives = snap["drives"]
        self.recent_monologue_summary = snap["recent_monologue_summary"]
        self.traces = snap["traces"]
        self.episodic_store = snap["episodic_store"]
        self.relations = snap["relations"]
        # ``_user_relation`` is a live reference into ``self.relations.schemas``;
        # re-resolve it against the restored RelationsStore so subsequent
        # ``record_prediction`` / ``record_surprise`` calls land on the
        # rolled-back schema, not the dropped one.
        self._user_relation = self.relations.get_or_create("user")
        self.self_model = snap["self_model"]
        self._turns_since_save = snap["_turns_since_save"]
        # Idempotency: consume the snapshot so the next call returns False
        # until ``respond()`` re-arms it.
        self._pre_turn_snapshot = None
        return True

    # ---------- E5 persistence

    def _hydrate_from_snapshot(self, snap: AnimaStoreSnapshot) -> None:
        """Restore §5.1 + §5.2 state from an on-disk snapshot.

        Each region is restored via its dedicated ``from_jsonable`` codec so
        the in-memory invariants (e.g. EpisodicStore's ``_by_id`` index) are
        rebuilt. If a sub-region is empty on disk (fresh field), the existing
        config-seeded default is kept — we only overwrite when we have data.
        """
        # §5.1 behavioral record.
        if snap.episodic_events:
            self.episodic_store = EpisodicStore.from_jsonable(
                {"events": snap.episodic_events}
            )
        # action_history is researcher-facing; not re-hydrated into TurnTraces
        # (we don't need to reconstruct the live trace objects across sessions
        # — they're an audit trail). Kept on snapshot for save round-trips.

        # §5.2 interpreted state.
        if snap.semantic_facts:
            self.semantic_store = SemanticStore.from_jsonable(
                {"facts": snap.semantic_facts}
            )
        if snap.relations:
            self.relations = RelationsStore.from_jsonable(
                {"schemas": snap.relations}
            )
            self._user_relation = self.relations.get_or_create("user")
        if snap.self_model:
            self.self_model = SelfModel.from_jsonable(snap.self_model)
        if snap.mood:
            self.mood = MoodVector.from_jsonable(snap.mood)
        if snap.drives:
            self.drives = DriveState.from_jsonable(snap.drives)

        # Session bookkeeping.
        if snap.conversation_history:
            self.conversation_history = list(snap.conversation_history)
        self._current_session_id = snap.current_session_id

    def _build_snapshot(self) -> AnimaStoreSnapshot:
        """Serialize current in-memory state into an :class:`AnimaStoreSnapshot`.

        Flat-list field shapes (e.g. ``episodic_events`` as ``list[dict]``)
        match the on-disk JSON — see :class:`AnimaStoreSnapshot` for the
        canonical schema.
        """
        return AnimaStoreSnapshot(
            episodic_events=[e.to_jsonable() for e in self.episodic_store.events],
            action_history=[t.to_jsonable() for t in self.traces],
            self_model=self.self_model.to_jsonable(),
            semantic_facts=[f.to_jsonable() for f in self.semantic_store.facts],
            relations={n: s.to_jsonable() for n, s in self.relations.schemas.items()},
            mood=self.mood.to_jsonable(),
            drives=self.drives.to_jsonable(),
            conversation_history=list(self.conversation_history),
            current_session_id=self._current_session_id,
        )

    def _autosave(self) -> None:
        """Internal: build a snapshot and write through the store.

        No-op if no store is attached. Resets the turn counter so the next
        autosave fires after another ``autosave_every`` turns.
        """
        if self._store is None:
            return
        snap = self._build_snapshot()
        self._store.save(snap, session_id=self._current_session_id)
        self._turns_since_save = 0

    def save(self) -> None:
        """Public: force a save right now, regardless of the autosave countdown.

        Use this at session end / before process exit / on user request to
        guarantee the §5.1 + §5.2 state is durable. No-op if no store is
        attached.
        """
        if self._store is None:
            return
        self._autosave()

    def set_session_id(self, session_id: str) -> None:
        """Mark the start of a new named session.

        The CLI (E6) calls this so per-session transcript files are kept
        separate — preserving the audit invariant that one session's
        conversation log is one JSON file.
        """
        self._current_session_id = session_id

    # ---------- module surface (lightweight for Phase 1; expanded later)

    def observe(self) -> dict[str, Any]:
        """Peek at internal state. For research/debugging."""
        return {
            "name": self.cfg.biography.name,
            "mood": {"valence": self.mood.valence, "arousal": self.mood.arousal,
                     "dominance": self.mood.dominance,
                     "discrete": dict(self.mood.discrete)},
            "drives": dict(self.drives.activations),
            "current_concerns": list(self.self_model.current_concerns),
            "believed_traits": dict(self.self_model.believed_traits),
        }
