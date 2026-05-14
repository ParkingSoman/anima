"""Smoke tests for the baseline renderer. No LLM calls."""

from pathlib import Path

from anima.config.schema import load_config
from verification.baseline import _render_persona_prompt

PRESETS = list((Path(__file__).resolve().parents[2] / "anima" / "config" / "presets").glob("*.yaml"))


def test_baseline_prompt_contains_essentials():
    cfg = load_config(PRESETS[0])
    prompt = _render_persona_prompt(cfg)
    assert cfg.biography.name in prompt
    assert "openness" in prompt
    assert cfg.attachment.style.value in prompt
    assert cfg.demographics.role in prompt
    # The "not an AI" disclaimer must be present — this is the fair comparison.
    assert "NOT an AI" in prompt or "not an AI" in prompt
