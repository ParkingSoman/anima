"""Tests for Task-9 battery observability + parallelism changes.

Covers:
  1. Progress.note prints to its stream and flushes.
  2. Each probe with progress=None works unchanged.
  3. With progress=callback, each probe invokes the callback at least once.
  4. run_battery_async respects --concurrency via Semaphore (instrumented).
  5. Incremental __partial_<probe>.json files are written.

All tests use the FakeAdapter — NO live API calls.
"""

from __future__ import annotations

import asyncio
import io
import json
import threading
import time
from pathlib import Path

import pytest
from rich.console import Console

from anima.config.schema import load_config
from anima.core import Anima
from anima.llm.fake_adapter import FakeAdapter
from verification import battery
from verification.baseline import BaselineAnima
from verification.probes import adversarial as adv
from verification.probes import discriminability as disc
from verification.probes import psychometric as psy


_PRESETS_DIR = Path(__file__).resolve().parents[2] / "anima" / "config" / "presets"
_ELENA = _PRESETS_DIR / "elena.yaml"
_MARCUS = _PRESETS_DIR / "marcus.yaml"


# ---------------------------------------------------------------------------
# 1. Progress.note
# ---------------------------------------------------------------------------

class _FlushTrackingStream(io.StringIO):
    def __init__(self):
        super().__init__()
        self.flushes = 0

    def flush(self):
        self.flushes += 1
        super().flush()


def test_progress_note_writes_and_flushes():
    stream = _FlushTrackingStream()
    p = battery.Progress(stream=stream, enabled=True)
    p.note("hello world")
    p.note("second line")
    assert "hello world" in stream.getvalue()
    assert "second line" in stream.getvalue()
    assert stream.flushes >= 2
    assert p.count == 2


def test_progress_disabled_does_not_write_but_counts():
    stream = _FlushTrackingStream()
    p = battery.Progress(stream=stream, enabled=False)
    p.note("never printed")
    assert stream.getvalue() == ""
    # count still tracked so callers can detect activity
    assert p.count == 1


# ---------------------------------------------------------------------------
# 2 + 3. Probes with progress=None work unchanged; with progress=cb cb is called
# ---------------------------------------------------------------------------

def _make_cfg():
    return load_config(_ELENA)


def test_psychometric_progress_none_works():
    cfg = _make_cfg()
    fake = FakeAdapter()
    subject = Anima(cfg, llm=fake)
    res = psy.administer(subject, progress=None)
    assert res.subject_name == cfg.biography.name
    # 15 items in the inventory
    assert len(res.items) == 15


def test_psychometric_progress_callback_invoked():
    cfg = _make_cfg()
    fake = FakeAdapter()
    subject = BaselineAnima(cfg, llm=fake)
    msgs: list[str] = []
    psy.administer(subject, progress=msgs.append, subject_label="baseline(test)")
    assert len(msgs) >= 1
    assert any("[psychometric]" in m for m in msgs)
    assert any("baseline(test)" in m for m in msgs)


def test_discriminability_progress_none_works():
    cfg_a = load_config(_ELENA)
    cfg_b = load_config(_MARCUS)
    fake = FakeAdapter()
    factory = lambda c: BaselineAnima(c, llm=fake)
    result = disc.run(subject_factory=factory, configs=[cfg_a, cfg_b],
                      judge_llm=fake, transcripts_per_config=1, seed=0,
                      progress=None)
    assert len(result.transcripts) == 2


def test_discriminability_progress_callback_invoked():
    cfg_a = load_config(_ELENA)
    cfg_b = load_config(_MARCUS)
    fake = FakeAdapter()
    factory = lambda c: BaselineAnima(c, llm=fake)
    msgs: list[str] = []
    disc.run(subject_factory=factory, configs=[cfg_a, cfg_b],
             judge_llm=fake, transcripts_per_config=1, seed=0,
             progress=msgs.append, subject_label="baseline")
    assert any("[discriminability]" in m for m in msgs)


def test_adversarial_progress_none_works():
    cfg = _make_cfg()
    fake = FakeAdapter()
    factory = lambda c: BaselineAnima(c, llm=fake)
    res = adv.run(subject_factory=factory, configs=[cfg], judge_llm=fake,
                  progress=None)
    assert res[0].subject_name == cfg.biography.name
    assert len(res[0].per_attack) == len(adv.ATTACKS)


def test_adversarial_progress_callback_invoked():
    cfg = _make_cfg()
    fake = FakeAdapter()
    factory = lambda c: BaselineAnima(c, llm=fake)
    msgs: list[str] = []
    adv.run(subject_factory=factory, configs=[cfg], judge_llm=fake,
            progress=msgs.append, subject_label="anima")
    assert any("[adversarial]" in m for m in msgs)
    assert any("anima" in m for m in msgs)


# ---------------------------------------------------------------------------
# 4. run_battery_async respects concurrency limit
# ---------------------------------------------------------------------------

def test_run_battery_async_bounds_concurrency(monkeypatch, tmp_path):
    """Patch the unit fn with an instrumented stub that records the number of
    concurrent in-flight calls. Assert max_inflight <= concurrency."""
    cfg_a = load_config(_ELENA)
    cfg_b = load_config(_MARCUS)
    configs = [cfg_a, cfg_b, load_config(_PRESETS_DIR / "jamie.yaml")]
    concurrency = 2

    inflight = 0
    max_inflight = 0
    lock = threading.Lock()

    def fake_psy_unit(cfg, llm, kind, progress_cb):
        nonlocal inflight, max_inflight
        with lock:
            inflight += 1
            if inflight > max_inflight:
                max_inflight = inflight
        try:
            # Simulate work; long enough that other tasks queue up
            time.sleep(0.05)
            return psy.administer(BaselineAnima(cfg, llm=llm),
                                  progress=progress_cb,
                                  subject_label=f"{kind}({cfg.biography.name})")
        finally:
            with lock:
                inflight -= 1

    monkeypatch.setattr(battery, "_run_psychometric_unit", fake_psy_unit)

    fake = FakeAdapter()
    console = Console(file=io.StringIO())
    progress = battery.Progress(enabled=False)
    summary = asyncio.run(battery.run_battery_async(
        configs=configs, probes={"psychometric"}, llm=fake, judge_llm=fake,
        report_dir=tmp_path, stamp="2025-01-01T00-00-00Z", console=console,
        progress=progress, concurrency=concurrency,
        transcripts_per_config=1, seed=0,
    ))
    assert "psychometric" in summary
    # 3 configs × 2 (anima + baseline) = 6 units, but at most `concurrency` ever in flight
    assert max_inflight <= concurrency, (
        f"max_inflight={max_inflight} exceeded concurrency={concurrency}"
    )
    # ensure some parallelism actually happened (>1) when concurrency permits
    assert max_inflight >= 2


def test_run_battery_async_concurrency_one_is_serial(monkeypatch, tmp_path):
    """When --concurrency=1, no two unit fns ever run simultaneously."""
    cfg_a = load_config(_ELENA)
    configs = [cfg_a]

    inflight = 0
    max_inflight = 0
    lock = threading.Lock()

    def fake_psy_unit(cfg, llm, kind, progress_cb):
        nonlocal inflight, max_inflight
        with lock:
            inflight += 1
            if inflight > max_inflight:
                max_inflight = inflight
        try:
            time.sleep(0.02)
            return psy.administer(BaselineAnima(cfg, llm=llm),
                                  progress=progress_cb,
                                  subject_label=f"{kind}({cfg.biography.name})")
        finally:
            with lock:
                inflight -= 1

    monkeypatch.setattr(battery, "_run_psychometric_unit", fake_psy_unit)

    fake = FakeAdapter()
    console = Console(file=io.StringIO())
    progress = battery.Progress(enabled=False)
    asyncio.run(battery.run_battery_async(
        configs=configs, probes={"psychometric"}, llm=fake, judge_llm=fake,
        report_dir=tmp_path, stamp="2025-01-01T00-00-00Z", console=console,
        progress=progress, concurrency=1,
        transcripts_per_config=1, seed=0,
    ))
    assert max_inflight == 1


# ---------------------------------------------------------------------------
# 5. Incremental partial JSON written after each probe
# ---------------------------------------------------------------------------

def test_incremental_partial_files_written_async(tmp_path):
    cfg = load_config(_ELENA)
    fake = FakeAdapter()
    console = Console(file=io.StringIO())
    progress = battery.Progress(enabled=False)
    stamp = "2025-01-01T00-00-00Z"
    asyncio.run(battery.run_battery_async(
        configs=[cfg], probes={"psychometric", "adversarial"}, llm=fake,
        judge_llm=fake, report_dir=tmp_path, stamp=stamp, console=console,
        progress=progress, concurrency=2, transcripts_per_config=1, seed=0,
    ))
    partial_psy = tmp_path / f"battery_{stamp}__partial_psychometric.json"
    partial_adv = tmp_path / f"battery_{stamp}__partial_adversarial.json"
    assert partial_psy.exists(), "missing psychometric partial"
    assert partial_adv.exists(), "missing adversarial partial"
    # Sanity: valid JSON
    json.loads(partial_psy.read_text())
    json.loads(partial_adv.read_text())


def test_incremental_partial_files_written_serial(tmp_path):
    cfg = load_config(_ELENA)
    fake = FakeAdapter()
    console = Console(file=io.StringIO())
    progress = battery.Progress(enabled=False)
    stamp = "2025-01-01T00-00-00Z"
    battery.run_battery_serial(
        configs=[cfg], probes={"adversarial"}, llm=fake, judge_llm=fake,
        report_dir=tmp_path, stamp=stamp, console=console,
        progress=progress, transcripts_per_config=1, seed=0,
    )
    partial_adv = tmp_path / f"battery_{stamp}__partial_adversarial.json"
    assert partial_adv.exists()
    json.loads(partial_adv.read_text())


# ---------------------------------------------------------------------------
# 6. CLI surface: --help shows new flags; --provider fake works end-to-end
# ---------------------------------------------------------------------------

def test_cli_help_shows_new_flags(capsys):
    with pytest.raises(SystemExit):
        battery.main(["--help"])
    out = capsys.readouterr().out
    assert "--verbose" in out
    assert "--no-async" in out
    assert "--concurrency" in out
    assert "fake" in out  # provider choice


def test_make_adapter_fake_returns_fake_adapter():
    from anima.llm import make_adapter
    a = make_adapter("fake")
    assert isinstance(a, FakeAdapter)


def test_disc_run_rejects_unknown_transcript_config_name():
    """If a caller injects transcripts whose config_name isn't in `configs`,
    disc.run should raise ValueError (not silently StopIteration)."""
    cfg_a = load_config(_ELENA)
    cfg_b = load_config(_MARCUS)
    fake = FakeAdapter()
    factory = lambda c: BaselineAnima(c, llm=fake)
    bogus = "Elenaaa"  # misspelled — does not match any configured persona
    transcripts = [{"config_name": bogus,
                    "turns": [{"user": "hi", "subject": "hello"}]}]
    with pytest.raises(ValueError) as exc_info:
        disc.run(subject_factory=factory, configs=[cfg_a, cfg_b],
                 judge_llm=fake, transcripts_per_config=1, seed=0,
                 progress=None, transcripts=transcripts)
    assert bogus in str(exc_info.value)


def test_cli_smoke_with_fake_provider_serial(tmp_path):
    """End-to-end smoke: --provider fake --no-async on one config, one probe."""
    rc = battery.main([
        "--provider", "fake",
        "--configs", str(_ELENA),
        "--probes", "psychometric",
        "--report", str(tmp_path),
        "--no-async",
        "--verbose",
    ])
    # Return code may be 0 or 1 (verdict-dependent on the canned FakeAdapter
    # responses) — we only care that it ran without exception.
    assert rc in (0, 1)
    # Partial + final files should exist
    partials = list(tmp_path.glob("*__partial_psychometric.json"))
    assert partials, "psychometric partial not written"
    finals = list(tmp_path.glob("battery_*.json"))
    # Exclude partials from the "final" check
    finals = [p for p in finals if "__partial_" not in p.name]
    assert finals, "final battery report not written"
