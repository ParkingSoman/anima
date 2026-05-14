"""Integration tests: the full turn loop with the user_prediction subsystem
wired in (E3).

Properties under test:
  - After turn 1, no surprise (no prior prediction); after turn 2, one
    surprise record; after turn 3, two records.
  - TurnTrace.prediction is populated on every turn.
  - TurnTrace.surprise_from_last_turn is empty on turn 1, non-empty on
    turn 2+.
  - On turn 2 the appraisal subsystem sees the prediction-violation block in
    its system prompt — verified by inspecting fake-adapter call history.
"""

from __future__ import annotations

from pathlib import Path

from anima.config import load_config
from anima.core import Anima
from anima.llm.fake_adapter import FakeAdapter


PRESET = Path(__file__).resolve().parents[2] / "anima" / "config" / "presets" / "marcus.yaml"


def test_surprise_history_grows_after_first_turn():
    cfg = load_config(PRESET)
    fake = FakeAdapter()
    a = Anima(cfg, llm=fake)

    # Turn 1: no prior prediction → no surprise recorded
    a.respond("hi")
    assert len(a._user_relation.surprise_history) == 0
    assert len(a._user_relation.predicted_intents) == 1

    # Turn 2: now there's a prior prediction → exactly one surprise recorded
    a.respond("tell me about yourself")
    assert len(a._user_relation.surprise_history) == 1
    assert len(a._user_relation.predicted_intents) == 2

    # Turn 3: two surprise records total
    a.respond("do you ever feel lonely")
    assert len(a._user_relation.surprise_history) == 2
    assert len(a._user_relation.predicted_intents) == 3


def test_trace_prediction_and_surprise_fields_populated():
    cfg = load_config(PRESET)
    fake = FakeAdapter()
    a = Anima(cfg, llm=fake)

    _, t1 = a.respond("hi")
    _, t2 = a.respond("how are you really")
    _, t3 = a.respond("nothing")

    # Predictions present on every turn.
    for t in (t1, t2, t3):
        assert t.prediction, "prediction missing from trace"
        assert "next_intent_label" in t.prediction
        assert "content_hint" in t.prediction
        assert "confidence" in t.prediction
        assert "rationale" in t.prediction
        # The fake adapter returns ask_question deterministically.
        assert t.prediction["next_intent_label"] == "ask_question"

    # Surprise: empty on turn 1, populated on turn 2+.
    assert t1.surprise_from_last_turn == {}
    assert t2.surprise_from_last_turn, "expected surprise on turn 2"
    assert "surprise_score" in t2.surprise_from_last_turn
    assert 0.0 <= t2.surprise_from_last_turn["surprise_score"] <= 1.0
    assert t3.surprise_from_last_turn, "expected surprise on turn 3"


def test_appraisal_prompt_on_turn_two_sees_surprise_block():
    """The prediction-violation signal must reach the appraisal subsystem on
    turns where a surprise was computed."""
    cfg = load_config(PRESET)
    fake = FakeAdapter()
    a = Anima(cfg, llm=fake)

    # Snapshot calls so we can isolate per-turn slices.
    a.respond("hi")
    n_calls_after_turn1 = len(fake.calls)
    a.respond("tell me more about your weekend")

    turn2_calls = fake.calls[n_calls_after_turn1:]
    # Find the APPRAISAL call from turn 2.
    appraisal_calls_t2 = [c for c in turn2_calls
                          if "APPRAISAL subsystem" in c["system"]]
    assert len(appraisal_calls_t2) == 1, (
        f"expected exactly one appraisal call on turn 2, got {len(appraisal_calls_t2)}"
    )
    sys_prompt = appraisal_calls_t2[0]["system"]
    assert "--- prediction-violation signal from prior turn ---" in sys_prompt, (
        "surprise block not threaded into appraisal prompt on turn 2"
    )
    assert "Surprise level:" in sys_prompt


def test_appraisal_prompt_on_turn_one_does_not_see_surprise_block():
    """On turn 1 there's no prior prediction, so the surprise block must be
    absent — backwards compatibility with pre-E3 prompts."""
    cfg = load_config(PRESET)
    fake = FakeAdapter()
    a = Anima(cfg, llm=fake)
    a.respond("hi")

    appraisal_calls = [c for c in fake.calls
                       if "APPRAISAL subsystem" in c["system"]]
    assert len(appraisal_calls) == 1
    sys_prompt = appraisal_calls[0]["system"]
    assert "prediction-violation signal" not in sys_prompt


def test_prediction_view_threaded_into_monologue_and_response():
    """Downstream subsystems (monologue, response) should see the theory-of-mind
    block in their system prompts."""
    cfg = load_config(PRESET)
    fake = FakeAdapter()
    a = Anima(cfg, llm=fake)
    a.respond("hi")

    tom_marker = "--- theory of mind ---"
    found_in_mono = False
    found_in_resp = False
    for call in fake.calls:
        sys = call["system"]
        if "INNER MONOLOGUE subsystem" in sys and tom_marker in sys:
            found_in_mono = True
        if "RESPONSE GENERATION subsystem" in sys and tom_marker in sys:
            found_in_resp = True
    assert found_in_mono, "theory-of-mind block missing from monologue prompt"
    assert found_in_resp, "theory-of-mind block missing from response prompt"


def test_user_prediction_llm_call_is_fast_tier_one_per_turn():
    """Master plan §10: prediction is ONE fast-tier call per turn."""
    cfg = load_config(PRESET)
    fake = FakeAdapter()
    a = Anima(cfg, llm=fake)
    a.respond("hi")

    prediction_calls = [c for c in fake.calls
                        if "USER PREDICTION subsystem" in c["system"]]
    assert len(prediction_calls) == 1, (
        f"expected 1 user-prediction call, got {len(prediction_calls)}"
    )
    assert prediction_calls[0]["tier"] == "fast"
