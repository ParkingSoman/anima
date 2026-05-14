"""Structural integration test of the MVP turn loop with the FakeAdapter.

Verifies that the full perception → appraisal → monologue → response sequence
executes and produces the expected trace fields. Does NOT validate quality —
that's the verification battery's job.
"""

from pathlib import Path

import pytest

from anima.config import load_config
from anima.core import Anima
from anima.llm.fake_adapter import FakeAdapter
from verification.baseline import BaselineAnima

PRESETS = list((Path(__file__).resolve().parents[2] / "anima" / "config" / "presets").glob("*.yaml"))


@pytest.mark.parametrize("path", PRESETS, ids=lambda p: p.stem)
def test_full_turn_loop_runs(path):
    cfg = load_config(path)
    fake = FakeAdapter()
    a = Anima(cfg, llm=fake)
    reply, trace = a.respond("How have you been?")

    # Reply is non-empty
    assert reply
    # Trace contains all the structured stages
    assert trace.user_msg == "How have you been?"
    assert "literal_content" in trace.perception
    assert "primary_emotion" in trace.appraisal
    assert trace.monologue                    # monologue is non-empty
    assert trace.response == reply
    # Mood and drive state must have advanced (or been re-rendered)
    assert "valence" in trace.mood_before and "valence" in trace.mood_after
    assert set(trace.drives_before.keys()) == set(trace.drives_after.keys())

    # Architecture must have made all four expected LLM calls
    # (perception fast, appraisal fast, monologue strong, response strong)
    tiers = [c["tier"] for c in fake.calls]
    assert tiers.count("fast") >= 2
    assert tiers.count("strong") >= 2


def test_self_model_is_consulted_by_every_subsystem():
    """Pillar 3 architectural commitment: self-model is read input to every
    subsystem. Verify by checking the rendered self-model block appears in
    the system prompt for each subsystem-stage call."""
    cfg = load_config(PRESETS[0])
    fake = FakeAdapter()
    a = Anima(cfg, llm=fake)
    a.respond("Tell me something.")

    needle = "WHO I AM (self-model)"
    subsystem_systems = [c["system"] for c in fake.calls
                         if any(tag in c["system"] for tag in
                                ["PERCEPTION subsystem", "APPRAISAL subsystem",
                                 "INNER MONOLOGUE subsystem", "RESPONSE GENERATION subsystem"])]
    assert subsystem_systems, "no subsystem calls observed"
    for sys_prompt in subsystem_systems:
        assert needle in sys_prompt, "self-model block missing from a subsystem prompt"


def test_baseline_also_runs():
    cfg = load_config(PRESETS[0])
    fake = FakeAdapter()
    b = BaselineAnima(cfg, llm=fake)
    reply, _ = b.respond("Hi.")
    assert reply

    # Baseline must NOT have any of the subsystem prompt fingerprints
    for call in fake.calls:
        for tag in ["PERCEPTION subsystem", "APPRAISAL subsystem",
                    "INNER MONOLOGUE subsystem", "RESPONSE GENERATION subsystem"]:
            assert tag not in call["system"], "baseline accidentally invoked subsystem"
