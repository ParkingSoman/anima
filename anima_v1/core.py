"""Anima — the top-level orchestrator.

Phase 1 MVP turn loop:
    perception → appraisal → inner_monologue → response_generator
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from anima_v1.config import AnimaConfig, load_config
from anima_v1.llm.base import LLMAdapter
from anima_v1.llm import make_adapter
from anima_v1.state.drives import DriveState
from anima_v1.state.mood import MoodVector
from anima_v1.state.self_model import SelfModel
from anima_v1.subsystems.appraisal import AppraisalSubsystem
from anima_v1.subsystems.inner_monologue import InnerMonologueSubsystem
from anima_v1.subsystems.perception import PerceptionSubsystem
from anima_v1.subsystems.response_generator import ResponseGeneratorSubsystem

# Feature plumbing: capture every LLM call's full output (including DeepSeek
# ``reasoning`` chain-of-thought, tool_calls, refusals, etc.) so the trace +
# transcript preserve "everything the model does". The CapturingLLMAdapter
# lives in the head ``anima.llm`` package because v1's LLMResponse pre-dates
# the ``raw_message`` field — but the wrapper itself is provider-agnostic and
# forwards via __getattr__, so v1 works fine wrapping a v1 adapter (the
# captured ``response`` will just lack a raw_message — still useful for
# elapsed_ms / text / usage). When the smoke uses a head ``anima.llm``
# adapter against a v1 Anima (as the iteration's smoke test does), the
# raw_message is populated normally.
from anima.llm.capture import CapturingLLMAdapter


def _snapshot_llm_calls(capture: CapturingLLMAdapter | None) -> list[dict]:
    """Serialize captured LLM calls into JSON-able dicts (mirrors head).

    v1's :class:`LLMResponse` does not carry ``raw_message`` or
    ``finish_reason`` natively, but the smoke test wires a head-style
    ``anima.llm`` adapter into v1's Anima, in which case both fields
    are populated by the adapter. We use ``getattr`` with ``None``
    defaults so v1-native adapters (without those fields) still
    serialize cleanly.
    """
    if capture is None:
        return []
    out: list[dict] = []
    for c in capture.calls:
        resp = c.response
        usage = dict(resp.usage) if isinstance(resp.usage, dict) else {}
        out.append({
            "tier": c.tier,
            "system_prompt_chars": c.system_prompt_chars,
            "user_message_preview": c.user_message_preview,
            "elapsed_ms": c.elapsed_ms,
            "timestamp": c.timestamp,
            "response": {
                "text": resp.text,
                "usage": usage,
                "finish_reason": getattr(resp, "finish_reason", None),
                "raw_message": getattr(resp, "raw_message", None),
            },
        })
    return out


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
    usage: dict = field(default_factory=dict)
    # Feature plumbing (matches head ``anima.core.TurnTrace``): captured
    # LLM-call outputs for THIS turn. Each entry is a JSON-able dict with
    # ``tier`` / ``system_prompt_chars`` / ``user_message_preview`` /
    # ``elapsed_ms`` / ``timestamp`` / ``response`` (where ``response``
    # carries ``text`` / ``usage`` / ``finish_reason`` / ``raw_message``).
    # The ``raw_message`` is where DeepSeek's chain-of-thought lives.
    llm_calls: list[dict] = field(default_factory=list)


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
        # Wrap the supplied adapter so every subsystem's ``self.llm.generate(...)``
        # call is recorded. Same plumbing as head's ``anima.core.Anima`` — see
        # the head module for the design rationale. ``__getattr__`` forwarding
        # in CapturingLLMAdapter keeps existing reads of ``adapter.name`` /
        # ``adapter.model`` / etc. transparent.
        _inner_llm = llm or make_adapter("anthropic")
        self._llm_capture: CapturingLLMAdapter = CapturingLLMAdapter(_inner_llm)
        self.llm = self._llm_capture
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

        self.traces: list[TurnTrace] = []

    @classmethod
    def from_config_path(cls, path: str | Path, llm: LLMAdapter | None = None,
                         *, ablate_monologue_length: bool = False) -> "Anima":
        return cls(load_config(path), llm=llm,
                   ablate_monologue_length=ablate_monologue_length)

    # ---------- the turn loop

    def respond(self, user_msg: str) -> tuple[str, TurnTrace]:
        # Capture: clear the LLM-call buffer so this turn's snapshot only
        # contains calls made during this turn.
        self._llm_capture.reset()
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

        # 3. appraisal (memory triggering deferred to phase 2)
        appraisal = self._appraisal.run(
            cfg=self.cfg, self_model=self.self_model, mood_view=mood_view,
            drive_view=drive_view, perception=perception, perception_view=perception_view,
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
        )
        monologue_view = self._monologue.render(monologue)

        # 9. response
        response = self._response.run(
            cfg=self.cfg, self_model=self.self_model, mood_view=post_mood_view,
            perception_view=perception_view, appraisal_view=appraisal_view,
            monologue_view=monologue_view, user_msg=user_msg,
            conversation_history=self.conversation_history,
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
            usage=response.metadata.get("usage", {}),
            llm_calls=_snapshot_llm_calls(self._llm_capture),
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
