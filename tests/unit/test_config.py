"""Unit tests for config loading and self-model construction. These do NOT
call the LLM and run in <1s. The point is to catch shape/structural mistakes
before any expensive battery run.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from anima.config import AnimaConfig, load_config
from anima.state.self_model import SelfModel
from anima.state.mood import MoodVector
from anima.state.drives import DriveState

PRESETS = list((Path(__file__).resolve().parents[2] / "anima" / "config" / "presets").glob("*.yaml"))


@pytest.mark.parametrize("path", PRESETS, ids=lambda p: p.stem)
def test_preset_loads(path):
    cfg = load_config(path)
    assert isinstance(cfg, AnimaConfig)
    assert cfg.biography.name
    assert 0.0 <= cfg.big5.neuroticism <= 1.0


@pytest.mark.parametrize("path", PRESETS, ids=lambda p: p.stem)
def test_self_model_from_config(path):
    cfg = load_config(path)
    sm = SelfModel.from_config(cfg)
    assert sm.kernel.name == cfg.biography.name
    rendered = sm.render()
    assert cfg.biography.name in rendered
    assert "self-model" in rendered.lower()


@pytest.mark.parametrize("path", PRESETS, ids=lambda p: p.stem)
def test_mood_baseline_in_range(path):
    cfg = load_config(path)
    mv = MoodVector.baseline_for(cfg.big5)
    assert -1.0 <= mv.valence <= 1.0
    assert -1.0 <= mv.arousal <= 1.0
    assert -1.0 <= mv.dominance <= 1.0


@pytest.mark.parametrize("path", PRESETS, ids=lambda p: p.stem)
def test_drive_state_from_baseline(path):
    cfg = load_config(path)
    ds = DriveState.from_baseline(cfg.drives)
    for k, v in ds.activations.items():
        assert 0.0 <= v <= 1.0, f"{k}={v} out of range"


def test_self_model_delta_lifecycle():
    cfg = load_config(PRESETS[0])
    sm = SelfModel.from_config(cfg)
    before = dict(sm.believed_traits)
    sm.propose_delta("believed_trait", "openness", 0.99, "user kept asking weird questions")
    # not committed yet — believed_traits unchanged
    assert sm.believed_traits == before
    sm.commit_delta(0)
    assert sm.believed_traits["openness"] == pytest.approx(0.99)
