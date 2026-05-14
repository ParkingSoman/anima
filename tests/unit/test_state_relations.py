"""Unit tests for the relational-schema scaffolding. No LLM calls."""

from __future__ import annotations

import pytest

from anima.state.relations import (
    PredictedIntent,
    RelationalSchema,
    RelationsStore,
    SurpriseRecord,
)


def _make_prediction(
    label: str = "share_personal_info",
    hint: str = "they'll mention their cousin again",
    conf: float = 0.6,
    ts: str = "2026-05-14T15:23:01Z",
) -> PredictedIntent:
    return PredictedIntent(
        ts=ts,
        perceived_input_summary="user opened with a story about family",
        next_intent_label=label,
        content_hint=hint,
        confidence=conf,
    )


def test_store_empty():
    store = RelationsStore()
    assert store.get("user") is None


def test_get_or_create_idempotent():
    store = RelationsStore()
    s1 = store.get_or_create("user")
    s2 = store.get_or_create("user")
    assert s1 is s2
    assert s1.name == "user"
    assert s1.attachment_quality_inferred == "unknown"


def test_record_prediction_and_last_prediction():
    schema = RelationalSchema(name="user")
    assert schema.last_prediction() is None
    p1 = _make_prediction(label="ask_question", ts="2026-05-14T10:00:00Z")
    p2 = _make_prediction(label="disagree", ts="2026-05-14T11:00:00Z")
    schema.record_prediction(p1)
    schema.record_prediction(p2)
    assert schema.last_prediction() is p2
    assert len(schema.predicted_intents) == 2


def test_record_surprise():
    schema = RelationalSchema(name="user")
    p = _make_prediction()
    s = SurpriseRecord(
        ts="2026-05-14T15:24:00Z",
        predicted_intent=p,
        actual_user_msg_summary="user actually changed the subject to work",
        surprise_score=0.8,
        reason="prediction was about family; actual was about work",
    )
    schema.record_surprise(s)
    assert schema.surprise_history == [s]


def test_render_smoke():
    schema = RelationalSchema(
        name="user",
        attachment_quality_inferred="warm",
        beliefs_about_person=["cares about cousin", "works in real estate"],
    )
    schema.record_prediction(_make_prediction(label="share_personal_info", conf=0.7))
    out = schema.render()
    assert "user" in out
    assert "warm" in out
    assert "cousin" in out
    assert "share_personal_info" in out
    # no history yet, should not crash
    assert "no surprise history" in out


def test_render_with_surprise_history_includes_avg():
    schema = RelationalSchema(name="user")
    p = _make_prediction()
    for score in (0.2, 0.4, 0.9):
        schema.record_surprise(SurpriseRecord(
            ts="2026-05-14T15:24:00Z",
            predicted_intent=p,
            actual_user_msg_summary="...",
            surprise_score=score,
            reason="",
        ))
    out = schema.render()
    assert "recent avg surprise" in out


def test_json_roundtrip_schema():
    schema = RelationalSchema(
        name="user",
        attachment_quality_inferred="ambivalent",
        beliefs_about_person=["cares about cousin"],
    )
    p = _make_prediction(label="disagree", conf=0.55)
    schema.record_prediction(p)
    schema.record_surprise(SurpriseRecord(
        ts="2026-05-14T15:24:00Z",
        predicted_intent=p,
        actual_user_msg_summary="changed subject",
        surprise_score=0.7,
        reason="off-topic shift",
    ))
    data = schema.to_jsonable()
    restored = RelationalSchema.from_jsonable(data)
    assert restored.to_jsonable() == data
    assert restored.name == "user"
    assert restored.attachment_quality_inferred == "ambivalent"
    assert restored.last_prediction().next_intent_label == "disagree"
    assert restored.surprise_history[0].surprise_score == pytest.approx(0.7)


def test_json_roundtrip_store_multiple_schemas():
    store = RelationsStore()
    store.get_or_create("user").beliefs_about_person.append("careful, slow to open up")
    store.get_or_create("Sarah").attachment_quality_inferred = "warm"
    data = store.to_jsonable()
    restored = RelationsStore.from_jsonable(data)
    assert restored.to_jsonable() == data
    assert restored.get("user").beliefs_about_person == ["careful, slow to open up"]
    assert restored.get("Sarah").attachment_quality_inferred == "warm"
