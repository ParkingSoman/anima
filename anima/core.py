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
from anima.state.drives import DriveState
from anima.state.episodic import EpisodicStore
from anima.state.mood import MoodVector
from anima.state.self_model import SelfModel
from anima.subsystems.appraisal import AppraisalSubsystem
from anima.subsystems.inner_monologue import InnerMonologueSubsystem
from anima.subsystems.memory_retrieval import MemoryRetrieval
from anima.subsystems.perception import PerceptionSubsystem
from anima.subsystems.response_generator import ResponseGeneratorSubsystem


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


class Anima:
    def __init__(self, cfg: AnimaConfig, llm: LLMAdapter | None = None,
                 *, ablate_monologue_length: bool = False):
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

        # Phase-2 episodic store. Empty at construction; E6 self-monitor will
        # populate it from each turn's encoding pass.
        self.episodic_store = EpisodicStore()

        self.traces: list[TurnTrace] = []

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

        # 3. appraisal
        appraisal = self._appraisal.run(
            cfg=self.cfg, self_model=self.self_model, mood_view=mood_view,
            drive_view=drive_view, perception=perception, perception_view=perception_view,
            retrieval_view=retrieval_view,
        )
        self._appraisal.apply(appraisal=appraisal, mood=self.mood, drives=self.drives)
        appraisal_view = self._appraisal.render(appraisal)

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
        )
        monologue_view = self._monologue.render(monologue)

        # 9. response
        response = self._response.run(
            cfg=self.cfg, self_model=self.self_model, mood_view=post_mood_view,
            perception_view=perception_view, appraisal_view=appraisal_view,
            monologue_view=monologue_view, user_msg=user_msg,
            conversation_history=self.conversation_history,
            retrieval_view=retrieval_view,
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
        )
        self.traces.append(trace)
        return response.text, trace

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
