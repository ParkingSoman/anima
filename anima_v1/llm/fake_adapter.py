"""Deterministic fake adapter for tests. Never hits the network.

Routes by the LAST user-message contents to a small library of canned
responses chosen to exercise the structured-output paths (JSON parsing,
inner monologue style, response style). For full verification you must use a
real provider adapter; this is only for structural smoke tests.
"""

from __future__ import annotations

import re

from anima.llm.base import LLMResponse, Tier


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
                 ):
        self.strong_text = strong_text
        self.fast_text = fast_text
        self.monologue_text = monologue_text
        self.calls: list[dict] = []

    def generate(self, *, tier: Tier, system: str, messages: list[dict],
                 max_tokens: int = 1024, temperature: float = 0.7,
                 stop=None) -> LLMResponse:
        self.calls.append({"tier": tier, "system": system, "messages": messages,
                           "max_tokens": max_tokens, "temperature": temperature})

        # Route by subsystem fingerprint in the system prompt.
        if "PERCEPTION subsystem" in system:
            return LLMResponse(text=_PERCEPTION_JSON, usage={}, raw={})
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
