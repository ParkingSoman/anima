"""Unit tests for the semantic memory scaffolding. No LLM calls."""

from __future__ import annotations

import pytest

from anima.state.semantic import SemanticFact, SemanticStore


def _make_fact(
    fid: str = "f-1",
    ts: str = "2026-05-14T15:23:01Z",
    claim: str = "The user works in real estate",
    confidence: float = 0.8,
    sources: list[str] | None = None,
) -> SemanticFact:
    return SemanticFact(
        id=fid,
        ts=ts,
        claim=claim,
        confidence=confidence,
        sources=list(sources or ["ev-1"]),
    )


def test_store_empty():
    store = SemanticStore()
    assert store.list_all() == []
    assert store.get("nope") is None
    assert store.filter_by() == []


def test_append_and_get():
    store = SemanticStore()
    f = _make_fact()
    store.append(f)
    assert store.get("f-1") is f
    assert store.list_all() == [f]


def test_append_duplicate_id_rejected():
    store = SemanticStore()
    store.append(_make_fact(fid="f-1"))
    with pytest.raises(ValueError):
        store.append(_make_fact(fid="f-1"))


def test_filter_by_min_confidence():
    store = SemanticStore()
    store.append(_make_fact(fid="f-a", confidence=0.4))
    store.append(_make_fact(fid="f-b", confidence=0.9))
    high = store.filter_by(min_confidence=0.8)
    assert [f.id for f in high] == ["f-b"]


def test_filter_by_keywords_AND_and_case_insensitive():
    store = SemanticStore()
    store.append(_make_fact(fid="f-a", claim="The user works in Real Estate"))
    store.append(_make_fact(fid="f-b", claim="The user has a cousin named Sarah"))
    hit = store.filter_by(topic_keywords=["real", "ESTATE"])
    assert [f.id for f in hit] == ["f-a"]
    miss = store.filter_by(topic_keywords=["real", "sarah"])
    assert miss == []


def test_filter_combined_criteria():
    store = SemanticStore()
    store.append(_make_fact(fid="f-a", claim="user likes coffee", confidence=0.3))
    store.append(_make_fact(fid="f-b", claim="user likes coffee", confidence=0.95))
    store.append(_make_fact(fid="f-c", claim="user dislikes tea", confidence=0.95))
    hits = store.filter_by(min_confidence=0.8, topic_keywords=["coffee"])
    assert [f.id for f in hits] == ["f-b"]


def test_json_roundtrip():
    store = SemanticStore()
    store.append(_make_fact(fid="f-a", confidence=0.4, sources=["ev-1", "ev-2"]))
    store.append(_make_fact(fid="f-b", confidence=0.9, claim="user lives in Brooklyn"))
    data = store.to_jsonable()
    restored = SemanticStore.from_jsonable(data)
    assert restored.to_jsonable() == data
    assert restored.get("f-a").sources == ["ev-1", "ev-2"]
    assert restored.get("f-b").confidence == pytest.approx(0.9)
