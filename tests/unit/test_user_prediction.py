"""Unit tests for the user_prediction subsystem (E3, Phase 2).

Covers:
  - compute_surprise short-circuits when last_prediction is None
  - matching intent + high content overlap → surprise near 0
  - mismatched intent + low content overlap → surprise near 1
  - boundary: empty content_hint, empty perception literal_content
  - predict returns a PredictionResult on the deterministic fake adapter
  - predict falls back to "unclear" on malformed JSON
  - render shows prediction; with surprise, also shows surprise reason
"""

from __future__ import annotations

from anima.config import load_config
from anima.llm import make_adapter
from anima.llm.base import LLMResponse
from anima.state.relations import PredictedIntent, RelationalSchema, SurpriseRecord
from anima.state.self_model import SelfModel
from anima.subsystems.perception import Perception
from anima.subsystems.user_prediction import (
    PredictionResult,
    UserPredictionSubsystem,
)


PRESET = "anima/config/presets/marcus.yaml"


def _self_model() -> SelfModel:
    cfg = load_config(PRESET)
    return SelfModel.from_config(cfg)


def _perception(*, intent: str = "they want to talk",
                content: str = "the partner spoke") -> Perception:
    return Perception(
        literal_content=content,
        perceived_intent=intent,
        perceived_valence=0.0,
        perceived_demands=[],
        salient_features=[],
    )


def _prediction(*, label: str = "ask_question",
                hint: str = "they will ask about my weekend",
                conf: float = 0.6) -> PredictedIntent:
    return PredictedIntent(
        ts="2026-05-14T00:00:00+00:00",
        perceived_input_summary="something earlier",
        next_intent_label=label,
        content_hint=hint,
        confidence=conf,
    )


# ---------- compute_surprise


def test_compute_surprise_none_when_no_prior_prediction():
    """Turn 1 of a conversation: no prediction to score, return None."""
    ups = UserPredictionSubsystem(make_adapter("fake"))
    out = ups.compute_surprise(last_prediction=None, perception=_perception())
    assert out is None


def test_compute_surprise_low_when_intent_matches_and_content_overlaps():
    """High content overlap + label substring in actual intent → score near 0."""
    ups = UserPredictionSubsystem(make_adapter("fake"))
    # The label "ask_question" appears as the substring "ask_question" in
    # perceived_intent. (We accept the literal token; compute_surprise does
    # substring containment lowercased.)
    pred = _prediction(
        label="ask_question",
        hint="will probably ask about my weekend and family plans",
    )
    perc = _perception(
        intent="they are about to ask_question style move",
        content="ask about weekend family plans please",
    )
    s = ups.compute_surprise(last_prediction=pred, perception=perc)
    assert s is not None
    # intent_mismatch = 0 (label is in intent string)
    # overlap is high (about, weekend, family, plans all overlap)
    assert s.surprise_score < 0.3, f"expected low surprise, got {s.surprise_score:.2f}"
    assert s.predicted_intent is pred
    assert s.reason


def test_compute_surprise_normalizes_snake_case_label_against_natural_intent():
    """Predicted label 'ask_question' should match perceived intent
    'ask question about preferences' after snake_case normalization,
    yielding intent_mismatch=0. With identical content this gives
    surprise approximately 0 (not approximately 0.5 as the pre-fix
    heuristic produced)."""
    ups = UserPredictionSubsystem(make_adapter("fake"))
    pred = _prediction(
        label="ask_question",
        hint="what do you like to read",
    )
    perc = _perception(
        intent="ask question about preferences",
        content="what do you like to read",
    )
    sr = ups.compute_surprise(last_prediction=pred, perception=perc)
    assert sr is not None
    # intent_mismatch should be 0 after snake_case normalization, and
    # content_overlap should be 1.0 (identical token sets), so
    # surprise = 0.5 * 0 + 0.5 * (1 - 1) = 0.
    assert sr.surprise_score < 0.1, (
        f"expected near-zero surprise after snake_case normalization, "
        f"got {sr.surprise_score:.3f}"
    )


def test_compute_surprise_high_when_intent_mismatched_and_no_overlap():
    """Wrong intent label + no shared content tokens → score near 1."""
    ups = UserPredictionSubsystem(make_adapter("fake"))
    pred = _prediction(
        label="ask_question",
        hint="they will probably ask about my weekend",
    )
    perc = _perception(
        intent="they are expressing frustration about traffic",
        content="totally unrelated complaint regarding rush hour congestion downtown",
    )
    s = ups.compute_surprise(last_prediction=pred, perception=perc)
    assert s is not None
    assert s.surprise_score > 0.7, f"expected high surprise, got {s.surprise_score:.2f}"


def test_compute_surprise_handles_empty_content_hint_and_literal():
    """Empty strings shouldn't crash; surprise should land at a sensible default."""
    ups = UserPredictionSubsystem(make_adapter("fake"))
    pred = _prediction(label="", hint="")
    perc = _perception(intent="", content="")
    s = ups.compute_surprise(last_prediction=pred, perception=perc)
    assert s is not None
    # Empty label → intent_mismatch=0. Empty content_hint and literal → overlap=0.
    # So surprise = 0.5 * 0 + 0.5 * (1 - 0) = 0.5.
    assert 0.0 <= s.surprise_score <= 1.0
    assert s.surprise_score == 0.5


def test_compute_surprise_score_is_clamped_to_unit_interval():
    """Pathological inputs still yield a value in [0,1]."""
    ups = UserPredictionSubsystem(make_adapter("fake"))
    pred = _prediction(label="WEIRDLABEL_NEVER_PRESENT", hint="alpha bravo charlie")
    perc = _perception(intent="entirely orthogonal phrasing",
                       content="delta echo foxtrot")
    s = ups.compute_surprise(last_prediction=pred, perception=perc)
    assert s is not None
    assert 0.0 <= s.surprise_score <= 1.0


# ---------- predict


def test_predict_on_fake_adapter_returns_deterministic_result():
    """The fake adapter routes USER PREDICTION → fixed JSON; verify parsing."""
    ups = UserPredictionSubsystem(make_adapter("fake"))
    schema = RelationalSchema(name="user")  # empty schema
    result = ups.predict(
        perception=_perception(),
        perception_view="--- perception ---\n--- end perception ---",
        self_model=_self_model(),
        appraisal_view="--- appraisal ---\n--- end appraisal ---",
        relational_schema=schema,
    )
    assert isinstance(result, PredictionResult)
    assert result.next_intent_label == "ask_question"
    assert result.content_hint == "what do you usually do on weekends"
    assert 0.0 <= result.confidence <= 1.0
    assert result.confidence == 0.65
    assert result.rationale


class _BadJSONAdapter:
    """Adapter that always returns non-JSON garbage. Exercises the fallback."""
    name = "bad-json"

    def __init__(self):
        self.calls = []

    def generate(self, *, tier, system, messages, max_tokens=1024,
                 temperature=0.7, stop=None):
        self.calls.append({"tier": tier})
        return LLMResponse(text="totally not json, just prose ramble",
                           usage={}, raw={})


def test_predict_falls_back_to_unclear_on_malformed_json():
    """A non-JSON LLM response must not crash; return safe fallback."""
    ups = UserPredictionSubsystem(_BadJSONAdapter())
    schema = RelationalSchema(name="user")
    result = ups.predict(
        perception=_perception(),
        perception_view="",
        self_model=_self_model(),
        appraisal_view="",
        relational_schema=schema,
    )
    assert isinstance(result, PredictionResult)
    assert result.next_intent_label == "unclear"
    assert result.confidence == 0.0


def test_predict_with_populated_relational_schema_does_not_crash():
    """A non-empty schema (recent surprise + beliefs) renders into the prompt."""
    ups = UserPredictionSubsystem(make_adapter("fake"))
    schema = RelationalSchema(
        name="user",
        attachment_quality_inferred="ambivalent",
        beliefs_about_person=["they often deflect direct questions",
                              "they care about their sister"],
    )
    # Add a prior surprise record so the brief renderer hits its surprise branch.
    schema.record_prediction(_prediction(label="agree"))
    schema.record_surprise(SurpriseRecord(
        ts="2026-05-13T00:00:00+00:00",
        predicted_intent=_prediction(label="agree"),
        actual_user_msg_summary="they pushed back",
        surprise_score=0.8,
        reason="predicted agree; got pushback",
    ))
    result = ups.predict(
        perception=_perception(),
        perception_view="--- perception ---\n--- end perception ---",
        self_model=_self_model(),
        appraisal_view="--- appraisal ---\n--- end appraisal ---",
        relational_schema=schema,
    )
    assert isinstance(result, PredictionResult)
    assert result.next_intent_label == "ask_question"  # from fake adapter


# ---------- render


def test_render_without_surprise_shows_prediction_only():
    ups = UserPredictionSubsystem(make_adapter("fake"))
    pred = PredictionResult(
        next_intent_label="share_personal_info",
        content_hint="they will mention a tough week at work",
        confidence=0.55,
        rationale="they've been getting more personal",
    )
    block = ups.render(pred, surprise=None)
    assert "--- theory of mind ---" in block
    assert "--- end theory of mind ---" in block
    assert "share_personal_info" in block
    assert "0.55" in block
    assert "tough week at work" in block
    # No surprise section
    assert "surprise from my last prediction" not in block


def test_render_with_surprise_shows_both_prediction_and_surprise():
    ups = UserPredictionSubsystem(make_adapter("fake"))
    pred = PredictionResult(
        next_intent_label="ask_question",
        content_hint="they'll probe about my weekend",
        confidence=0.7,
        rationale="—",
    )
    surp = SurpriseRecord(
        ts="2026-05-14T00:00:00+00:00",
        predicted_intent=_prediction(label="agree"),
        actual_user_msg_summary="they disagreed",
        surprise_score=0.82,
        reason="predicted 'agree' / 'they will agree' — actual perceived 'they push back' (overlap=0.10, intent_match=0.0)",
    )
    block = ups.render(pred, surprise=surp)
    assert "ask_question" in block
    assert "surprise from my last prediction: 0.82" in block
    assert "intent_match=0.0" in block


def test_render_handles_empty_content_hint():
    """Falls back to a dash placeholder so the prompt is never blank."""
    ups = UserPredictionSubsystem(make_adapter("fake"))
    pred = PredictionResult(
        next_intent_label="unclear",
        content_hint="",
        confidence=0.0,
        rationale="—",
    )
    block = ups.render(pred, surprise=None)
    assert "unclear" in block
    # An empty content hint should show as the em-dash placeholder.
    assert "'—'" in block or ": —" in block
