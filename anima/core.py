"""Anima — the top-level orchestrator.

Phase 1 MVP turn loop:
    perception → appraisal → inner_monologue → response_generator
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from anima.config import AnimaConfig, load_config
from anima.llm.base import LLMAdapter
from anima.llm import make_adapter
from anima.persistence.store import AnimaStore, AnimaStoreSnapshot
from anima.state.drives import DriveState
from anima.state.episodic import EpisodicStore
from anima.state.mood import MoodVector
from anima.state.relations import PredictedIntent, RelationsStore
from anima.state.self_model import SelfModel
from anima.state.semantic import SemanticStore
from anima.subsystems.appraisal import AppraisalSubsystem
from anima.subsystems.inner_monologue import InnerMonologueSubsystem
from anima.subsystems.memory_retrieval import MemoryRetrieval
from anima.subsystems.perception import PerceptionSubsystem
from anima.subsystems.response_generator import ResponseGeneratorSubsystem
from anima.subsystems.user_prediction import UserPredictionSubsystem, _now_ts


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
        }


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

    @classmethod
    def from_config_path(cls, path: str | Path, llm: LLMAdapter | None = None,
                         *, ablate_monologue_length: bool = False) -> "Anima":
        return cls(load_config(path), llm=llm,
                   ablate_monologue_length=ablate_monologue_length)

    # ---------- the turn loop

    def respond(self, user_msg: str) -> tuple[str, TurnTrace]:
        mood_view = self.mood.render()
        drive_view = self.drives.render()
        mood_before = {"valence": self.mood.valence, "arousal": self.mood.arousal,
                       "dominance": self.mood.dominance,
                       "discrete": dict(self.mood.discrete)}
        drives_before = dict(self.drives.activations)

        # 1. perception
        perception = self._perception.run(
            user_msg=user_msg, self_model=self.self_model,
            mood_view=mood_view, relational_summary=self.relational_summary,
        )
        perception_view = self._perception.render(perception)

        # 2. memory retrieval (Phase 2). Reconstructive recall — see
        # anima/subsystems/memory_retrieval.py. retrieval_view is appended to
        # every downstream subsystem prompt so appraisal/monologue/response
        # all read against the same surfaced memories.
        retrieved = self._memory.run(
            perception=perception, perception_view=perception_view,
            self_model=self.self_model, mood=self.mood,
            active_schemas=[s.value for s in self.cfg.schemas],
            episodic_store=self.episodic_store,
            k=3,
        )
        retrieval_view = self._memory.render(retrieved)

        # 3a. surprise from last turn's prediction (master plan §10 / §11.10).
        # On turn 1 this is None (no prior prediction exists). After turn 1, we
        # compare what we predicted the user would do against what they
        # actually did — feed the prediction-error into appraisal.
        last_prediction = self._user_relation.last_prediction()
        surprise = self._user_prediction.compute_surprise(
            last_prediction=last_prediction, perception=perception,
        )
        if surprise is not None:
            self._user_relation.record_surprise(surprise)

        # 3. appraisal (now reads the surprise signal when present)
        appraisal = self._appraisal.run(
            cfg=self.cfg, self_model=self.self_model, mood_view=mood_view,
            drive_view=drive_view, perception=perception, perception_view=perception_view,
            retrieval_view=retrieval_view, surprise=surprise,
        )
        self._appraisal.apply(appraisal=appraisal, mood=self.mood, drives=self.drives)
        appraisal_view = self._appraisal.render(appraisal)

        # 4. user prediction (this turn's guess at next turn's user move).
        # Recorded on the relational schema so the NEXT turn's surprise
        # computation has something to compare against.
        prediction = self._user_prediction.predict(
            perception=perception, perception_view=perception_view,
            self_model=self.self_model, appraisal_view=appraisal_view,
            relational_schema=self._user_relation,
        )
        self._user_relation.record_prediction(PredictedIntent(
            ts=_now_ts(),
            perceived_input_summary=perception.literal_content[:200],
            next_intent_label=prediction.next_intent_label,
            content_hint=prediction.content_hint,
            confidence=prediction.confidence,
        ))
        prediction_view = self._user_prediction.render(prediction, surprise)

        # 5. inner monologue (re-render mood/drives so they reflect appraisal updates)
        post_mood_view = self.mood.render()
        post_drive_view = self.drives.render()
        monologue = self._monologue.run(
            cfg=self.cfg, self_model=self.self_model,
            mood_view=post_mood_view, drive_view=post_drive_view,
            perception_view=perception_view, appraisal_view=appraisal_view,
            relational_summary=self.relational_summary,
            recent_monologue_summary=self.recent_monologue_summary,
            user_msg=user_msg,
            ablate=self.ablate_monologue_length,
            retrieval_view=retrieval_view,
            prediction_view=prediction_view,
        )
        monologue_view = self._monologue.render(monologue)

        # 9. response
        response = self._response.run(
            cfg=self.cfg, self_model=self.self_model, mood_view=post_mood_view,
            perception_view=perception_view, appraisal_view=appraisal_view,
            monologue_view=monologue_view, user_msg=user_msg,
            conversation_history=self.conversation_history,
            retrieval_view=retrieval_view,
            prediction_view=prediction_view,
        )

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
        )
        self.traces.append(trace)

        # E5: autosave countdown. We tick AFTER the trace is appended so a
        # crash mid-turn doesn't leave a half-recorded turn on disk.
        if self._store is not None:
            self._turns_since_save += 1
            if self._turns_since_save >= self._autosave_every:
                self._autosave()

        return response.text, trace

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
