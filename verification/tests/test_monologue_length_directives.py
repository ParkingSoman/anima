"""Unit tests for the monologue length-directive ablation probe.

The probe lives at :mod:`verification.probes.monologue_length_directives`.
These tests verify, for each cell:

  - the subclass can be instantiated and called;
  - the resulting system prompt contains the exact directive substring (for
    ``short`` and ``long``), or contains NO length guidance at all (for
    ``variable``);
  - the cell-specific ``max_tokens`` budget is forwarded to the adapter.

The :class:`anima_v1.llm.fake_adapter.FakeAdapter` is used as the LLM mock —
no network, no API key needed. We drive the subsystem directly with a minimal
view bundle so the test does not depend on the rest of the Phase 1 cognitive
core.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from anima_v1.config import load_config
from anima_v1.llm.fake_adapter import FakeAdapter
from anima_v1.state.self_model import SelfModel
from verification.probes.monologue_length_directives import (
    LONG_DIRECTIVE,
    SHORT_DIRECTIVE,
    LengthControlledInnerMonologue,
    MonologueCell,
)


_PRESETS_DIR = (
    Path(__file__).resolve().parents[2] / "anima_v1" / "config" / "presets"
)
_JAMIE = _PRESETS_DIR / "jamie.yaml"


def _run_cell(cell: MonologueCell):
    """Instantiate the cell-controlled subsystem, drive one ``run()`` call
    with a minimal view bundle, and return ``(monologue, fake_adapter, system_prompt)``.

    The system prompt is fished out of the adapter's recorded calls — that's
    where any length directive (or absence thereof) lives.
    """
    cfg = load_config(_JAMIE)
    fake = FakeAdapter()
    subsys = LengthControlledInnerMonologue(fake, cell=cell)
    monologue = subsys.run(
        cfg=cfg,
        self_model=SelfModel.from_config(cfg),
        mood_view="--- mood view ---\nneutral\n--- end mood ---",
        drive_view="--- drive view ---\nneutral\n--- end drive ---",
        perception_view="--- perception view ---\nneutral\n--- end perception ---",
        appraisal_view="--- appraisal view ---\nneutral\n--- end appraisal ---",
        relational_summary="",
        recent_monologue_summary="",
        user_msg="hey what's up",
    )
    # Find the inner-monologue call on the adapter. There should be exactly
    # one — we only invoked the subsystem once and FakeAdapter records every
    # generate() call.
    matching = [
        c for c in fake.calls if "INNER MONOLOGUE subsystem" in c["system"]
    ]
    assert len(matching) == 1, (
        f"expected exactly one INNER MONOLOGUE call; got {len(matching)}"
    )
    return monologue, fake, matching[0]


@pytest.mark.parametrize("cell", ["variable", "short", "long"])
def test_cell_instantiates_and_runs(cell):
    """Each of the three cells must instantiate without error and produce a
    :class:`Monologue` whose ``text`` is non-empty."""
    monologue, _fake, _call = _run_cell(cell)
    assert monologue.text, f"cell {cell!r} produced empty monologue text"
    assert monologue.summary, f"cell {cell!r} produced empty summary"


def test_short_prompt_contains_exact_directive():
    """The ``short`` cell's system prompt must contain the literal
    '1–2 sentences' substring (en-dash, the project's house style)."""
    _m, _fake, call = _run_cell("short")
    system = call["system"]
    assert "1–2 sentences" in system, (
        f"expected '1–2 sentences' in short prompt; got: {system[:600]!r}"
    )
    # And the full directive verbatim, for paranoia.
    assert SHORT_DIRECTIVE in system, (
        f"expected full SHORT_DIRECTIVE in short prompt; got: {system[:600]!r}"
    )


def test_long_prompt_contains_exact_directive():
    """The ``long`` cell's system prompt must contain the literal
    '8–12 sentences' substring (en-dash, the project's house style)."""
    _m, _fake, call = _run_cell("long")
    system = call["system"]
    assert "8–12 sentences" in system, (
        f"expected '8–12 sentences' in long prompt; got: {system[:600]!r}"
    )
    assert LONG_DIRECTIVE in system, (
        f"expected full LONG_DIRECTIVE in long prompt; got: {system[:600]!r}"
    )


def test_variable_prompt_has_no_length_guidance():
    """The ``variable`` cell must produce a system prompt that contains NO
    length directive at all — neither the 'Length:' phrasing of the short/long
    cells nor the 'LENGTH BUDGET' phrasing of the parent template."""
    _m, _fake, call = _run_cell("variable")
    system = call["system"]
    assert "Length:" not in system, (
        f"variable cell leaked a 'Length:' directive; got: {system[:600]!r}"
    )
    assert "LENGTH BUDGET" not in system, (
        f"variable cell leaked a 'LENGTH BUDGET' directive; "
        f"got: {system[:600]!r}"
    )
    # Sanity: the rest of the inner-monologue scaffold IS still present.
    assert "INNER MONOLOGUE subsystem" in system, (
        "variable cell stripped too much — INNER MONOLOGUE header missing"
    )


@pytest.mark.parametrize(
    "cell,expected_tokens",
    [("variable", 1500), ("short", 120), ("long", 720)],
)
def test_max_tokens_per_cell(cell, expected_tokens):
    """Each cell forwards its configured ``max_tokens`` budget to the adapter."""
    _m, _fake, call = _run_cell(cell)
    assert call["max_tokens"] == expected_tokens, (
        f"cell {cell!r}: expected max_tokens={expected_tokens}, "
        f"got {call['max_tokens']}"
    )


def test_unknown_cell_rejected():
    """Constructing with a bogus cell must raise immediately, not silently
    fall back to a default."""
    fake = FakeAdapter()
    with pytest.raises(ValueError):
        LengthControlledInnerMonologue(fake, cell="medium")  # type: ignore[arg-type]
