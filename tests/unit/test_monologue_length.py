"""Unit test: the monologue length-budget tiering should produce different
ranges for the three preset configs in the expected direction.

Expected ranking by rumination tendency:
  Jamie (high E, low NFC, intuitive, secure)  →  SHORTEST
  Marcus (analytic, high NFC, avoidant)       →  MEDIUM-ish
  Elena (high N, analytic-ish, anxious)       →  LONGEST
"""

from pathlib import Path

import pytest

from anima.config import load_config
from anima.subsystems.inner_monologue import _length_directive


PRESET_DIR = Path(__file__).resolve().parents[2] / "anima" / "config" / "presets"


def _band(cfg):
    lo, hi, _ = _length_directive(cfg)
    return lo, hi


def test_jamie_short():
    cfg = load_config(PRESET_DIR / "jamie.yaml")
    lo, hi = _band(cfg)
    assert hi <= 4, f"Jamie should ruminate little; got {lo}-{hi}"


def test_elena_long():
    cfg = load_config(PRESET_DIR / "elena.yaml")
    lo, hi = _band(cfg)
    assert lo >= 2 and hi >= 4, f"Elena should ruminate; got {lo}-{hi}"


def test_ordering():
    j = _band(load_config(PRESET_DIR / "jamie.yaml"))
    m = _band(load_config(PRESET_DIR / "marcus.yaml"))
    e = _band(load_config(PRESET_DIR / "elena.yaml"))
    # Jamie's upper bound <= Marcus's upper bound <= Elena's upper bound
    assert j[1] <= m[1] <= e[1], f"expected Jamie≤Marcus≤Elena upper bounds; got {j[1]}, {m[1]}, {e[1]}"
