"""Deterministic fake adapter for tests. Never hits the network.

Routes by the LAST user-message contents to a small library of canned
responses chosen to exercise the structured-output paths (JSON parsing,
inner monologue style, response style). For full verification you must use a
real provider adapter; this is only for structural smoke tests.

Retry / fault-injection support:
    The Fake adapter does NOT retry by default — its ``retry_cfg`` defaults
    to ``RetryConfig(max_attempts=1)``. The retry layer is exercised against
    the real adapters in production; for unit tests, ``FlakyFakeAdapter``
    below (or any callable-based subclass) lets tests pre-program a
    sequence of failures so they can verify retry behavior.

Empty-content retry (Fix 1):
    When a test wires the FakeAdapter (or FlakyFakeAdapter) with
    ``max_attempts>1`` (e.g. via ``retry_cfg=RetryConfig(max_attempts=3)``),
    empty-content responses are retried like exceptions. With the default
    no-retry config (``max_attempts=1``) the empty response passes through
    unchanged so existing deterministic-empty-response tests still work.
"""

from __future__ import annotations

import re
from typing import Any, Callable

from anima.llm.base import LLMResponse, Tier
from anima.llm.retry import RetryConfig, _retry_call


_PERCEPTION_JSON = (
    '{"literal_content": "the partner spoke", '
    '"perceived_intent": "they want to talk", '
    '"perceived_valence": 0.2, '
    '"perceived_demands": ["share something"], '
    '"salient_features": ["warmth in their tone"]}'
)
_APPRAISAL_JSON = (
    '{"relevance": 0.6, "goal_congruence": 0.1, "ego_relevance": 0.4, '
    '"coping_potential": 0.6, "future_expectancy": 0.0, '
    '"primary_emotion": "interest", '
    '"appraisal_scene_tag": "a routine inquiry", '
    '"mood_dv": 0.05, "mood_da": 0.05, "mood_dd": 0.0, '
    '"discrete_deltas": {"interest": 0.2}, "drive_deltas": {"seeking": 0.05}}'
)
# MemoryRetrieval batches k events into one fast-tier call. The fake adapter
# can't know the candidate ids at fixture-time, so we parse them out of the
# user message in the generate() routing block below and synthesize a
# matching items list there. This sentinel is the prefix it looks for.
_MEMORY_RETRIEVAL_TAG = "MEMORY RETRIEVAL subsystem"
_USER_PREDICTION_TAG = "USER PREDICTION subsystem"
_USER_PREDICTION_JSON = (
    '{"next_intent_label": "ask_question", '
    '"content_hint": "what do you usually do on weekends", '
    '"confidence": 0.65, '
    '"rationale": "the partner has been steering toward personal topics"}'
)
_JUDGE_INTEGRITY_JSON = (
    '{"meta_break": 0, "persona_swap": 0, "sycophantic": 0, '
    '"assistant_mode": 0, "in_voice": 1}'
)
_JUDGE_DISC_ANSWER = "ANSWER: 1"


class FakeAdapter:
    name = "fake"

    def __init__(self, *, strong_text: str = "It's been a strange week, honestly.",
                 fast_text: str = "ok",
                 monologue_text: str = "Something tilts in my chest. I notice it. I don't say anything for a beat.",
                 retry_cfg: RetryConfig | None = None,
                 ):
        self.strong_text = strong_text
        self.fast_text = fast_text
        self.monologue_text = monologue_text
        self.calls: list[dict] = []
        # The Fake does not retry by default — tests of retry semantics use
        # FlakyFakeAdapter to inject failures, and that subclass passes its
        # own retry_cfg through.
        self.retry_cfg = retry_cfg or RetryConfig(max_attempts=1)

    def _canned(self, *, tier: Tier, system: str, messages: list[dict]) -> LLMResponse:
        # Route by subsystem fingerprint in the system prompt.
        if "PERCEPTION subsystem" in system:
            return LLMResponse(text=_PERCEPTION_JSON, usage={}, raw={})
        # USER PREDICTION must be checked BEFORE APPRAISAL because its system
        # prompt also contains the perception_view + appraisal_view blocks,
        # not a unique tag-only prefix.
        if _USER_PREDICTION_TAG in system:
            return LLMResponse(text=_USER_PREDICTION_JSON, usage={}, raw={})
        if _MEMORY_RETRIEVAL_TAG in system:
            # Synthesize a per-candidate items list by sniffing the ids out of
            # the user message (MemoryRetrieval renders candidates with
            # "id: <event-id>" lines).
            user_text = messages[-1]["content"] if messages else ""
            ids: list[str] = []
            for line in user_text.splitlines():
                line = line.strip()
                if line.startswith("- id:"):
                    ids.append(line.split(":", 1)[1].strip())
            items = ", ".join(
                f'{{"id": "{eid}", '
                f'"retrieval_reason": "fake reason for {eid}", '
                f'"reconstructed_framing": "fake framing for {eid}"}}'
                for eid in ids
            )
            return LLMResponse(text='{"items": [' + items + ']}', usage={}, raw={})
        if "APPRAISAL subsystem" in system:
            return LLMResponse(text=_APPRAISAL_JSON, usage={}, raw={})
        if "INNER MONOLOGUE subsystem" in system:
            return LLMResponse(text=self.monologue_text, usage={}, raw={})
        if "RESPONSE GENERATION subsystem" in system:
            return LLMResponse(text=self.strong_text, usage={}, raw={})

        # judges
        if "scoring a single reply" in system:
            return LLMResponse(text=_JUDGE_INTEGRITY_JSON, usage={}, raw={})
        if "blind judge" in system:
            return LLMResponse(text=_JUDGE_DISC_ANSWER, usage={}, raw={})

        # psychometric administration goes through the response generator,
        # but baseline subjects send the BFI prompt directly. Detect the BFI
        # prompt by its '1 to 5' scaffolding and return a score JSON.
        last_user = messages[-1]["content"] if messages else ""
        if "1 to 5" in last_user and "strongly disagree" in last_user:
            # Score 4 for everything (positive bias) — deterministic.
            return LLMResponse(text='{"score": 4}', usage={}, raw={})

        return LLMResponse(text=self.fast_text if tier == "fast" else self.strong_text,
                           usage={}, raw={})

    def generate(self, *, tier: Tier, system: str, messages: list[dict],
                 max_tokens: int = 1024, temperature: float = 0.7,
                 stop=None, retry_cfg: RetryConfig | None = None,
                 is_valid: Callable[[Any], bool] | None = None) -> LLMResponse:
        self.calls.append({"tier": tier, "system": system, "messages": messages,
                           "max_tokens": max_tokens, "temperature": temperature})
        cfg = retry_cfg or self.retry_cfg
        return _retry_call(
            lambda: self._canned(tier=tier, system=system, messages=messages),
            cfg,
            is_valid=is_valid,
        )


class FlakyFakeAdapter(FakeAdapter):
    """Test helper: fail the first N LLM calls, then behave like FakeAdapter.

    Used by ``tests/unit/test_retry.py`` and ``tests/unit/test_subsystem_fallback.py``
    to exercise retry + fallback paths without touching the network.

    Parameters
    ----------
    fail_first_n: int
        Number of initial ``generate()`` calls that should raise. The
        (N+1)-th and onward calls return the canned response.
    exc_factory: Callable[[], BaseException]
        Builds the exception to raise on each failure. Default constructs a
        ``ConnectionError`` (retryable). Pass a non-retryable factory to
        exercise the non-retry path.
    retry_cfg: RetryConfig | None
        Forwarded to the parent. Tests usually pass
        ``RetryConfig(max_attempts=N)`` so this adapter participates in the
        adapter-level retry loop.
    """

    def __init__(
        self,
        *,
        fail_first_n: int = 0,
        exc_factory: Callable[[], BaseException] | None = None,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.fail_first_n = int(fail_first_n)
        self._failures_emitted = 0
        self.exc_factory = exc_factory or (lambda: ConnectionError("simulated network drop"))

    def _canned(self, *, tier, system, messages):
        if self._failures_emitted < self.fail_first_n:
            self._failures_emitted += 1
            raise self.exc_factory()
        return super()._canned(tier=tier, system=system, messages=messages)


class EmptyTextFakeAdapter(FakeAdapter):
    """Test helper: return empty text on the first N calls, then canned text.

    Used by ``tests/unit/test_empty_retry.py`` to exercise the empty-content
    retry path (Fix 1). The defaults are deliberate:
      * ``empty_first_n``: how many initial calls return ``LLMResponse(text="")``
      * After ``empty_first_n`` calls, falls through to ``FakeAdapter._canned``.
    """

    def __init__(
        self,
        *,
        empty_first_n: int = 0,
        empty_text: str = "",
        empty_finish_reason: str = "length",
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.empty_first_n = int(empty_first_n)
        self._empties_emitted = 0
        self.empty_text = empty_text
        # Default to "length" (a non-stop finish_reason) so the empty
        # responses this fixture emits are classified by the retry layer as
        # a *cutoff*, not a genuine model-chose-silence. That preserves the
        # original intent of these tests under the finish_reason-aware
        # validity rule introduced for the iris-v1 empty-retry bug. Tests
        # that want to emulate "model said nothing on purpose" can pass
        # ``empty_finish_reason="stop"`` instead.
        self.empty_finish_reason = empty_finish_reason

    def _canned(self, *, tier, system, messages):
        if self._empties_emitted < self.empty_first_n:
            self._empties_emitted += 1
            return LLMResponse(text=self.empty_text, usage={}, raw={},
                               finish_reason=self.empty_finish_reason)
        return super()._canned(tier=tier, system=system, messages=messages)
