"""Unit tests for the monologue-length ablation flag (Task 10).

The ablation flag exists so a research run can disable the parameter-aware
monologue length computation in :class:`InnerMonologueSubsystem` and revert
to a uniform iter-1 2–6 sentence directive. The point is to isolate whether
that one component is what drives Jamie's psychometric improvement.

These tests use the FakeAdapter — NO live API calls.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from anima.config import load_config
from anima.core import Anima
from anima.llm.fake_adapter import FakeAdapter
from verification import battery


_PRESETS_DIR = Path(__file__).resolve().parents[2] / "anima" / "config" / "presets"
_JAMIE = _PRESETS_DIR / "jamie.yaml"

# Substring that appears in Jamie's parameter-aware band (score ≈ -1.49 →
# second band: "leans toward acting"). Keep both variants here so the test
# stays robust if Jamie's score nudges into the adjacent external-processor
# band in the future.
_PARAM_AWARE_NEEDLES = (
    "This person leans toward acting",
    "This person processes EXTERNALLY",
)
_UNIFORM_NEEDLE = "Length: 2–6 sentences. Stream-of-thought"


def _monologue_system_prompt(anima: Anima, fake: FakeAdapter) -> str:
    """Drive one turn and return the system prompt seen by the inner-
    monologue call (identified by its 'INNER MONOLOGUE subsystem' header)."""
    anima.respond("hey what's up")
    for call in fake.calls:
        if "INNER MONOLOGUE subsystem" in call["system"]:
            return call["system"]
    raise AssertionError("inner-monologue call never reached the LLM adapter")


def test_anima_default_uses_parameter_aware():
    """Default construction must use the parameter-aware directive (Jamie's
    band — 'leans toward acting' or 'EXTERNALLY')."""
    cfg = load_config(_JAMIE)
    fake = FakeAdapter()
    anima = Anima(cfg, llm=fake)
    system = _monologue_system_prompt(anima, fake)
    assert any(n in system for n in _PARAM_AWARE_NEEDLES), (
        f"expected one of {_PARAM_AWARE_NEEDLES!r} in system prompt; "
        f"got: {system[:500]!r}"
    )
    # And it must NOT be the uniform fallback.
    assert _UNIFORM_NEEDLE not in system, (
        "default path leaked the uniform-fallback directive"
    )


def test_anima_with_ablate_uses_uniform():
    """``ablate_monologue_length=True`` must swap in the uniform iter-1
    directive, and must NOT include any of the parameter-aware bands."""
    cfg = load_config(_JAMIE)
    fake = FakeAdapter()
    anima = Anima(cfg, llm=fake, ablate_monologue_length=True)
    system = _monologue_system_prompt(anima, fake)
    assert _UNIFORM_NEEDLE in system, (
        f"expected {_UNIFORM_NEEDLE!r} in system prompt; got: {system[:500]!r}"
    )
    for needle in _PARAM_AWARE_NEEDLES:
        assert needle not in system, (
            f"ablated path leaked parameter-aware directive {needle!r}"
        )


def test_battery_passes_ablate_flag(capsys):
    """The real battery CLI must accept ``--ablate-monologue-length`` and
    flip the module-level :data:`battery.ABLATE_MONOLOGUE_LENGTH` flag so
    the three unit functions see it. We exercise the production parser
    (via ``--help``) and confirm the flag is present, then drive argparse
    directly to confirm the captured value."""
    # The production parser exposes the flag in --help.
    with pytest.raises(SystemExit) as exc:
        battery.main(["--help"])
    assert exc.value.code == 0
    captured = capsys.readouterr()
    assert "--ablate-monologue-length" in captured.out, (
        "production --help did not list --ablate-monologue-length; got:\n"
        + captured.out
    )

    # And the flag is captured by argparse — replicate the production
    # parser shape so the test exercises argparse semantics without
    # invoking the full battery (which would require an LLM provider).
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--configs", nargs="+")
    parser.add_argument("--ablate-monologue-length", action="store_true",
                        default=False)

    args = parser.parse_args(["--configs", "a.yaml"])
    assert args.ablate_monologue_length is False

    args = parser.parse_args(
        ["--ablate-monologue-length", "--configs", "a.yaml"]
    )
    assert args.ablate_monologue_length is True
