"""Unit tests for OpenRouterAdapter. No network calls are made; we only verify
construction, model routing per tier, and factory wiring through make_adapter.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from anima.llm import OpenRouterAdapter, make_adapter


@pytest.fixture(autouse=True)
def _openrouter_key(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key-not-real")


def test_make_adapter_returns_openrouter_instance():
    adapter = make_adapter("openrouter")
    assert isinstance(adapter, OpenRouterAdapter)
    assert adapter.name == "openrouter"


def test_default_models_route_to_deepseek_v4_flash():
    adapter = OpenRouterAdapter()
    assert adapter._model_for("fast") == "deepseek/deepseek-v4-flash"
    assert adapter._model_for("strong") == "deepseek/deepseek-v4-flash"


def test_override_fast_and_strong_models():
    adapter = OpenRouterAdapter(fast_model="X", strong_model="Y")
    assert adapter._model_for("fast") == "X"
    assert adapter._model_for("strong") == "Y"
    assert adapter.fast_model == "X"
    assert adapter.strong_model == "Y"


def test_make_adapter_propagates_kwargs():
    adapter = make_adapter("openrouter", fast_model="Z")
    assert isinstance(adapter, OpenRouterAdapter)
    assert adapter.fast_model == "Z"
    assert adapter._model_for("fast") == "Z"
    # strong remains default
    assert adapter._model_for("strong") == "deepseek/deepseek-v4-flash"


def test_default_headers_construction():
    # Case 1: default app_name="anima", no referer → only X-Title is set.
    with patch("anima.llm.openrouter_adapter.OpenAI") as MockOpenAI:
        OpenRouterAdapter()
        kwargs = MockOpenAI.call_args.kwargs
        headers = kwargs["default_headers"]
        assert headers == {"X-Title": "anima"}
        assert "HTTP-Referer" not in headers

    # Case 2: explicit referer and app_name → both headers present.
    with patch("anima.llm.openrouter_adapter.OpenAI") as MockOpenAI:
        OpenRouterAdapter(referer="https://example.com", app_name="myproject")
        kwargs = MockOpenAI.call_args.kwargs
        headers = kwargs["default_headers"]
        assert headers == {
            "HTTP-Referer": "https://example.com",
            "X-Title": "myproject",
        }

    # Case 3: both None → default_headers is None (no headers dict at all).
    with patch("anima.llm.openrouter_adapter.OpenAI") as MockOpenAI:
        OpenRouterAdapter(referer=None, app_name=None)
        kwargs = MockOpenAI.call_args.kwargs
        assert kwargs["default_headers"] is None


def test_timeout_and_retries_are_passed_to_openai_client():
    # Case 1: defaults → timeout=60.0, max_retries=2.
    with patch("anima.llm.openrouter_adapter.OpenAI") as MockOpenAI:
        OpenRouterAdapter()
        kwargs = MockOpenAI.call_args.kwargs
        assert kwargs["timeout"] == 60.0
        assert kwargs["max_retries"] == 2

    # Case 2: explicit overrides propagate to the OpenAI(...) call.
    with patch("anima.llm.openrouter_adapter.OpenAI") as MockOpenAI:
        OpenRouterAdapter(timeout=10.0, max_retries=0)
        kwargs = MockOpenAI.call_args.kwargs
        assert kwargs["timeout"] == 10.0
        assert kwargs["max_retries"] == 0
