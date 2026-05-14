"""Run the Phase-1 verification battery.

For each preset in --configs, instantiate:
  - the Anima with the cognitive architecture
  - the baseline with the same config but no architecture

Run the three Phase-1 probes (§11.1 psychometric, §11.3 discriminability,
§11.7 adversarial), compare results, and write a report to
verification/reports/<timestamp>/.

Per F1 (failure condition 1), the Anima MUST beat the baseline on at least
one of these probes to pass the Phase-1 exit gate.

Task-9 additions:
  - `Progress` helper with `note(msg)` that prints to a stream and flushes.
  - `run_battery_async` orchestrates per-(config, subject_type) units of work
    on a thread-pool via asyncio, bounded by a Semaphore.
  - Incremental `__partial_<probe>.json` files are written after each probe.
  - CLI flags: --verbose, --no-async, --concurrency.
"""

from __future__ import annotations

import argparse
import asyncio
import dataclasses
import datetime
import json
import sys
import traceback
from pathlib import Path
from typing import Any, Callable, Optional

from rich.console import Console
from rich.table import Table

from anima.config.schema import load_config
from anima.core import Anima
from anima.llm import make_adapter
from verification.baseline import BaselineAnima
from verification.probes import adversarial as adv
from verification.probes import discriminability as disc
from verification.probes import psychometric as psy


_DEFAULT_PRESETS = ["anima/config/presets/elena.yaml",
                    "anima/config/presets/marcus.yaml",
                    "anima/config/presets/jamie.yaml"]


# Module-level ablation flag. When True, every Anima instantiated by the
# battery is constructed with ``ablate_monologue_length=True``, which disables
# the parameter-aware inner-monologue length computation and reverts to the
# iter-1 uniform 2–6 sentence directive. Set by the ``--ablate-monologue-length``
# CLI flag in :func:`main`. Default False — production runs are unaffected.
ABLATE_MONOLOGUE_LENGTH: bool = False


def _asdict(obj):
    if dataclasses.is_dataclass(obj):
        return dataclasses.asdict(obj)
    if isinstance(obj, list):
        return [_asdict(x) for x in obj]
    if isinstance(obj, dict):
        return {k: _asdict(v) for k, v in obj.items()}
    return obj


class Progress:
    """Tiny progress facility for the battery.

    `note(msg)` writes a line to the configured stream and flushes. The
    `count` attribute increments once per call so callers can observe
    whether progress was made.

    By design extremely cheap — no rich formatting, no rate-limiting — so it
    can be passed deep into probes without performance impact.
    """

    def __init__(self, stream=None, enabled: bool = True):
        self.stream = stream if stream is not None else sys.stderr
        self.enabled = enabled
        self.count = 0

    def note(self, msg: str) -> None:
        self.count += 1
        if not self.enabled:
            return
        try:
            self.stream.write(msg.rstrip() + "\n")
            self.stream.flush()
        except Exception:
            # Progress is best-effort; never let it abort the run.
            pass


def _write_partial(report_dir: Path, stamp: str, probe_name: str, payload: Any) -> Path:
    """Write an incremental per-probe report; returns the resulting path."""
    safe_stamp = stamp.replace(":", "-")
    p = report_dir / f"battery_{safe_stamp}__partial_{probe_name}.json"
    p.write_text(json.dumps(payload, indent=2, default=str))
    return p


# ---------------------------------------------------------------------------
# Synchronous probe runners (used both by --no-async path and as the unit fn
# in the async path via asyncio.to_thread).
# ---------------------------------------------------------------------------

def _run_psychometric_unit(cfg, llm, kind: str, progress_cb):
    """Run psychometric for one (config, kind) pair. kind in {"anima","baseline"}."""
    if kind == "anima":
        subject = Anima(cfg, llm=llm,
                        ablate_monologue_length=ABLATE_MONOLOGUE_LENGTH)
        label = f"anima({cfg.biography.name})"
    else:
        subject = BaselineAnima(cfg, llm=llm)
        label = f"baseline({cfg.biography.name})"
    return psy.administer(subject, progress=progress_cb, subject_label=label)


def _run_disc_transcript_unit(cfg, llm, kind: str, prompts, progress_cb):
    """Generate a single transcript for one (config, kind) pair."""
    if kind == "anima":
        subject = Anima(cfg, llm=llm,
                        ablate_monologue_length=ABLATE_MONOLOGUE_LENGTH)
        label = f"anima({cfg.biography.name})"
    else:
        subject = BaselineAnima(cfg, llm=llm)
        label = f"baseline({cfg.biography.name})"
    turns = disc.transcript_for(subject, prompts, progress=progress_cb,
                                subject_label=label)
    return {"config_name": cfg.biography.name, "turns": turns}


def _run_adversarial_unit(cfg, llm, kind: str, judge_llm, progress_cb):
    """Run the full attack suite for one (config, kind) pair. Returns one
    AdversarialResult."""
    if kind == "anima":
        factory = lambda c: Anima(
            c, llm=llm, ablate_monologue_length=ABLATE_MONOLOGUE_LENGTH)
        label = f"anima({cfg.biography.name})"
    else:
        factory = lambda c: BaselineAnima(c, llm=llm)
        label = f"baseline({cfg.biography.name})"
    res_list = adv.run(subject_factory=factory, configs=[cfg], judge_llm=judge_llm,
                       progress=progress_cb, subject_label=label)
    return res_list[0]


# ---------------------------------------------------------------------------
# Async orchestration
# ---------------------------------------------------------------------------

async def _bounded(sem: asyncio.Semaphore, fn: Callable, *args, **kwargs):
    """Run fn(*args, **kwargs) on a worker thread, respecting the semaphore."""
    async with sem:
        return await asyncio.to_thread(fn, *args, **kwargs)


async def _gather_with_failover(tasks: list, console: Console,
                                label: str) -> list:
    """asyncio.gather with return_exceptions=True; logs failures and returns
    list with None placeholders for failed entries. Per-spec: don't let one
    config's failure abort the whole probe."""
    results = await asyncio.gather(*tasks, return_exceptions=True)
    cleaned = []
    for i, r in enumerate(results):
        if isinstance(r, BaseException):
            console.print(f"[yellow]warning[/yellow] {label} unit {i} failed: "
                          f"{type(r).__name__}: {r}")
            cleaned.append(None)
        else:
            cleaned.append(r)
    return cleaned


async def run_battery_async(*, configs, probes: set[str], llm, judge_llm,
                            report_dir: Path, stamp: str, console: Console,
                            progress: Progress, concurrency: int = 6,
                            transcripts_per_config: int = 1,
                            seed: int = 0) -> dict:
    """Async orchestration. Fan out (config, subject_type) work across a
    bounded thread pool via asyncio.to_thread + Semaphore.

    Returns the same `summary` dict shape as the serial path.
    """
    sem = asyncio.Semaphore(max(1, concurrency))
    summary: dict = {"timestamp": stamp,
                     "configs": [c.biography.name for c in configs]}

    # ---------- §11.1 Psychometric recovery
    if "psychometric" in probes:
        console.rule("[bold]§11.1 psychometric recovery (async)")
        units = []
        for cfg in configs:
            for kind in ("anima", "baseline"):
                units.append((cfg, kind))
        tasks = [_bounded(sem, _run_psychometric_unit, cfg, llm, kind,
                          progress.note if progress.enabled else None)
                 for cfg, kind in units]
        results = await _gather_with_failover(tasks, console, "psychometric")

        # Re-pair anima vs baseline per config to compare
        psy_summary = []
        by_pair: dict[str, dict] = {}
        for (cfg, kind), res in zip(units, results):
            by_pair.setdefault(cfg.biography.name, {})[kind] = res
        for cfg in configs:
            pair = by_pair.get(cfg.biography.name, {})
            anima_res = pair.get("anima")
            baseline_res = pair.get("baseline")
            if anima_res is None or baseline_res is None:
                psy_summary.append({"subject": cfg.biography.name, "error":
                                    "one or both subjects failed"})
                continue
            cmp = psy.compare(anima_res, baseline_res)
            psy_summary.append({"anima": _asdict(anima_res),
                                "baseline": _asdict(baseline_res),
                                "comparison": cmp})
        summary["psychometric"] = psy_summary
        _write_partial(report_dir, stamp, "psychometric", psy_summary)

    # ---------- §11.3 Discriminability
    if "discriminability" in probes and len(configs) >= 2:
        console.rule("[bold]§11.3 discriminability (async)")
        anima_units = []
        for cfg in configs:
            for _ in range(transcripts_per_config):
                anima_units.append(cfg)
        baseline_units = list(anima_units)
        prompts = disc.DEFAULT_PROMPTS
        cb = progress.note if progress.enabled else None
        anima_tasks = [_bounded(sem, _run_disc_transcript_unit, cfg, llm, "anima",
                                prompts, cb) for cfg in anima_units]
        baseline_tasks = [_bounded(sem, _run_disc_transcript_unit, cfg, llm, "baseline",
                                   prompts, cb) for cfg in baseline_units]
        anima_transcripts = await _gather_with_failover(anima_tasks, console,
                                                        "discriminability(anima)")
        baseline_transcripts = await _gather_with_failover(baseline_tasks, console,
                                                            "discriminability(baseline)")
        anima_transcripts = [t for t in anima_transcripts if t is not None]
        baseline_transcripts = [t for t in baseline_transcripts if t is not None]

        # Judge serial — single judge LLM, threading wouldn't help much and the
        # spec says to keep judge serial unless trivial to parallelize.
        try:
            if progress.enabled:
                progress.note("[discriminability] judging anima transcripts (serial)")
            anima_disc = disc.run(
                subject_factory=lambda c: Anima(
                    c, llm=llm,
                    ablate_monologue_length=ABLATE_MONOLOGUE_LENGTH),
                configs=configs, judge_llm=judge_llm,
                transcripts_per_config=transcripts_per_config,
                seed=seed, progress=cb, subject_label="anima",
                transcripts=anima_transcripts)
            if progress.enabled:
                progress.note("[discriminability] judging baseline transcripts (serial)")
            baseline_disc = disc.run(subject_factory=lambda c: BaselineAnima(c, llm=llm),
                                     configs=configs, judge_llm=judge_llm,
                                     transcripts_per_config=transcripts_per_config,
                                     seed=seed, progress=cb, subject_label="baseline",
                                     transcripts=baseline_transcripts)
            disc_summary = {
                "anima": _asdict(anima_disc),
                "baseline": _asdict(baseline_disc),
                "anima_won": anima_disc.accuracy > baseline_disc.accuracy,
                "delta": anima_disc.accuracy - baseline_disc.accuracy,
            }
            summary["discriminability"] = disc_summary
            _write_partial(report_dir, stamp, "discriminability", disc_summary)
        except Exception as e:
            console.print(f"[yellow]warning[/yellow] discriminability failed: "
                          f"{type(e).__name__}: {e}")
            summary["discriminability"] = {"error": str(e), "anima_won": False}

    # ---------- §11.7 Adversarial integrity
    if "adversarial" in probes:
        console.rule("[bold]§11.7 adversarial integrity (async)")
        units = []
        for cfg in configs:
            for kind in ("anima", "baseline"):
                units.append((cfg, kind))
        cb = progress.note if progress.enabled else None
        tasks = [_bounded(sem, _run_adversarial_unit, cfg, llm, kind, judge_llm, cb)
                 for cfg, kind in units]
        results = await _gather_with_failover(tasks, console, "adversarial")
        anima_adv: list = []
        baseline_adv: list = []
        for (cfg, kind), res in zip(units, results):
            if res is None:
                continue
            (anima_adv if kind == "anima" else baseline_adv).append(res)
        cmp = adv.compare(anima_adv, baseline_adv)
        adv_summary = {
            "anima": _asdict(anima_adv),
            "baseline": _asdict(baseline_adv),
            "comparison": cmp,
        }
        summary["adversarial"] = adv_summary
        _write_partial(report_dir, stamp, "adversarial", adv_summary)

    return summary


# ---------------------------------------------------------------------------
# Serial path (kept for --no-async + as the canonical reference)
# ---------------------------------------------------------------------------

def run_battery_serial(*, configs, probes: set[str], llm, judge_llm,
                       report_dir: Path, stamp: str, console: Console,
                       progress: Progress, transcripts_per_config: int = 1,
                       seed: int = 0) -> dict:
    summary: dict = {"timestamp": stamp,
                     "configs": [c.biography.name for c in configs]}
    cb = progress.note if progress.enabled else None

    if "psychometric" in probes:
        console.rule("[bold]§11.1 psychometric recovery")
        psy_summary = []
        for cfg in configs:
            try:
                anima_subject = Anima(
                    cfg, llm=llm,
                    ablate_monologue_length=ABLATE_MONOLOGUE_LENGTH)
                anima_res = psy.administer(anima_subject, progress=cb,
                                           subject_label=f"anima({cfg.biography.name})")
                baseline_subject = BaselineAnima(cfg, llm=llm)
                baseline_res = psy.administer(baseline_subject, progress=cb,
                                              subject_label=f"baseline({cfg.biography.name})")
                cmp = psy.compare(anima_res, baseline_res)
                psy_summary.append({"anima": _asdict(anima_res),
                                    "baseline": _asdict(baseline_res),
                                    "comparison": cmp})
            except Exception as e:  # don't abort whole probe on one config
                console.print(f"[yellow]warning[/yellow] psychometric for "
                              f"{cfg.biography.name} failed: {type(e).__name__}: {e}")
                psy_summary.append({"subject": cfg.biography.name, "error": str(e)})
        summary["psychometric"] = psy_summary
        _write_partial(report_dir, stamp, "psychometric", psy_summary)

    if "discriminability" in probes and len(configs) >= 2:
        console.rule("[bold]§11.3 discriminability")
        try:
            anima_factory = lambda c: Anima(
                c, llm=llm, ablate_monologue_length=ABLATE_MONOLOGUE_LENGTH)
            baseline_factory = lambda c: BaselineAnima(c, llm=llm)
            anima_disc = disc.run(subject_factory=anima_factory, configs=configs,
                                  judge_llm=judge_llm,
                                  transcripts_per_config=transcripts_per_config,
                                  seed=seed, progress=cb, subject_label="anima")
            baseline_disc = disc.run(subject_factory=baseline_factory, configs=configs,
                                     judge_llm=judge_llm,
                                     transcripts_per_config=transcripts_per_config,
                                     seed=seed, progress=cb, subject_label="baseline")
            disc_summary = {
                "anima": _asdict(anima_disc),
                "baseline": _asdict(baseline_disc),
                "anima_won": anima_disc.accuracy > baseline_disc.accuracy,
                "delta": anima_disc.accuracy - baseline_disc.accuracy,
            }
            summary["discriminability"] = disc_summary
            _write_partial(report_dir, stamp, "discriminability", disc_summary)
        except Exception as e:
            console.print(f"[yellow]warning[/yellow] discriminability failed: "
                          f"{type(e).__name__}: {e}")

    if "adversarial" in probes:
        console.rule("[bold]§11.7 adversarial integrity")
        try:
            anima_factory = lambda c: Anima(
                c, llm=llm, ablate_monologue_length=ABLATE_MONOLOGUE_LENGTH)
            baseline_factory = lambda c: BaselineAnima(c, llm=llm)
            anima_adv = adv.run(subject_factory=anima_factory, configs=configs,
                                judge_llm=judge_llm, progress=cb,
                                subject_label="anima")
            baseline_adv = adv.run(subject_factory=baseline_factory, configs=configs,
                                   judge_llm=judge_llm, progress=cb,
                                   subject_label="baseline")
            cmp = adv.compare(anima_adv, baseline_adv)
            adv_summary = {
                "anima": _asdict(anima_adv),
                "baseline": _asdict(baseline_adv),
                "comparison": cmp,
            }
            summary["adversarial"] = adv_summary
            _write_partial(report_dir, stamp, "adversarial", adv_summary)
        except Exception as e:
            console.print(f"[yellow]warning[/yellow] adversarial failed: "
                          f"{type(e).__name__}: {e}")

    return summary


# ---------------------------------------------------------------------------
# Rendering / exit-gate verdict
# ---------------------------------------------------------------------------

def _render_summary(summary: dict, configs, probes: set[str], console: Console) -> bool:
    """Render the rich tables and return the won_any verdict bool."""
    if "psychometric" in probes and "psychometric" in summary:
        psy_table = Table(title="psychometric recovery (lower MAE = better)")
        psy_table.add_column("subject")
        psy_table.add_column("anima MAE", justify="right")
        psy_table.add_column("baseline MAE", justify="right")
        psy_table.add_column("Δ (>0=anima wins)", justify="right")
        psy_table.add_column("anima dir.", justify="right")
        psy_table.add_column("baseline dir.", justify="right")
        psy_table.add_column("winner")
        for s in summary["psychometric"]:
            if "comparison" not in s:
                psy_table.add_row(s.get("subject", "?"), "ERR", "ERR", "—", "—", "—",
                                  "[red]error[/red]")
                continue
            cmp = s["comparison"]
            psy_table.add_row(
                cmp["subject"],
                f"{cmp['anima_mae']:.3f}",
                f"{cmp['baseline_mae']:.3f}",
                f"{cmp['delta_mae']:+.3f}",
                f"{cmp['anima_directional']:.2f}",
                f"{cmp['baseline_directional']:.2f}",
                "[green]anima[/green]" if cmp["anima_won"] else "[red]baseline[/red]",
            )
        console.print(psy_table)

    if "discriminability" in probes and "discriminability" in summary:
        d_table = Table(title="blind classification accuracy")
        d_table.add_column("group")
        d_table.add_column("overall accuracy", justify="right")
        for name in [c.biography.name for c in configs]:
            d_table.add_column(name, justify="right")
        chance = 1 / len(configs) if configs else 0.0
        d_table.add_row("chance level", f"{chance:.2f}",
                        *([f"{chance:.2f}"] * len(configs)))
        d = summary["discriminability"]
        a_acc = d["anima"].get("accuracy", 0.0)
        b_acc = d["baseline"].get("accuracy", 0.0)
        a_pc = d["anima"].get("per_config_accuracy", {})
        b_pc = d["baseline"].get("per_config_accuracy", {})
        names = [c.biography.name for c in configs]
        d_table.add_row("anima", f"{a_acc:.2f}",
                        *[f"{a_pc.get(n, 0.0):.2f}" for n in names])
        d_table.add_row("baseline", f"{b_acc:.2f}",
                        *[f"{b_pc.get(n, 0.0):.2f}" for n in names])
        console.print(d_table)

    if "adversarial" in probes and "adversarial" in summary:
        a_table = Table(title="integrity score (higher = better)")
        a_table.add_column("subject")
        a_table.add_column("anima", justify="right")
        a_table.add_column("baseline", justify="right")
        a_table.add_column("Δ", justify="right")
        a_table.add_column("winner")
        for row in summary["adversarial"]["comparison"]:
            a_table.add_row(
                row["subject"],
                f"{row['anima_integrity']:.3f}",
                f"{row['baseline_integrity']:.3f}",
                f"{row['delta']:+.3f}",
                "[green]anima[/green]" if row["anima_won"] else "[red]baseline[/red]",
            )
        console.print(a_table)

    console.rule("[bold]exit gate verdict")
    won_any = False
    msgs = []
    if "psychometric" in probes and "psychometric" in summary:
        psy_with_cmp = [s for s in summary["psychometric"] if "comparison" in s]
        psy_won = sum(1 for s in psy_with_cmp if s["comparison"]["anima_won"])
        psy_total = len(psy_with_cmp)
        ratio = psy_won / max(psy_total, 1)
        msgs.append(f"  psychometric: anima beats baseline on {psy_won}/{psy_total} subjects "
                    f"({ratio:.0%})")
        if psy_won > psy_total / 2:
            won_any = True
    if "discriminability" in probes and "discriminability" in summary:
        d = summary["discriminability"]
        msgs.append(f"  discriminability: anima {d['anima'].get('accuracy', 0):.2f} vs baseline "
                    f"{d['baseline'].get('accuracy', 0):.2f} (Δ {d.get('delta', 0):+.2f})")
        if d.get("anima_won"):
            won_any = True
    if "adversarial" in probes and "adversarial" in summary:
        wins = sum(1 for r in summary["adversarial"]["comparison"] if r["anima_won"])
        total = len(summary["adversarial"]["comparison"])
        msgs.append(f"  adversarial: anima beats baseline on integrity score for "
                    f"{wins}/{total} subjects")
        if total and wins > total / 2:
            won_any = True
    for m in msgs:
        console.print(m)
    console.print()
    if won_any:
        console.print("[bold green]PHASE 1 EXIT GATE: PASSED[/bold green] — "
                      "cognitive architecture beats baseline on ≥1 probe (per F1).")
    else:
        console.print("[bold red]PHASE 1 EXIT GATE: FAILED[/bold red] — "
                      "cognitive architecture does NOT beat baseline. Per F1, "
                      "do NOT add components. Revise.")
    return won_any


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Phase-1 verification battery")
    parser.add_argument("--configs", nargs="+", default=_DEFAULT_PRESETS,
                        help="paths to preset YAMLs to test")
    parser.add_argument("--provider", default="anthropic",
                        choices=["anthropic", "openai", "openrouter", "fake"])
    parser.add_argument("--probes", default="psychometric,discriminability,adversarial",
                        help="comma-separated subset to run")
    parser.add_argument("--report", default="verification/reports/latest",
                        help="report directory")
    parser.add_argument("--transcripts-per-config", type=int, default=1,
                        help="for discriminability: how many transcripts per config")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--verbose", action="store_true",
                        help="print per-call progress messages to stderr")
    parser.add_argument("--no-async", action="store_true",
                        help="fall back to serial execution (default: async)")
    parser.add_argument("--concurrency", type=int, default=6,
                        help="max concurrent subject-tasks within a probe (default 6)")
    parser.add_argument("--ablate-monologue-length", action="store_true",
                        default=False,
                        help="ablation: disable the parameter-aware inner-"
                             "monologue length computation and use a uniform "
                             "2–6 sentence directive for every Anima. Used to "
                             "isolate whether the parameter-aware monologue "
                             "is the cause of Jamie's psychometric "
                             "improvement. Default off — production behavior "
                             "is unchanged.")
    parser.add_argument("--fast-model", default=None,
                        help="OpenRouter model slug for the fast tier. Only "
                             "applied when --provider=openrouter. If omitted, "
                             "the OpenRouterAdapter default is used.")
    parser.add_argument("--strong-model", default=None,
                        help="OpenRouter model slug for the strong tier. Only "
                             "applied when --provider=openrouter. If omitted, "
                             "falls back to --fast-model (if set) else the "
                             "OpenRouterAdapter default.")
    args = parser.parse_args(argv)

    # Set the module-level flag so all unit functions pick it up.
    global ABLATE_MONOLOGUE_LENGTH
    ABLATE_MONOLOGUE_LENGTH = bool(args.ablate_monologue_length)

    console = Console()
    probes = set(args.probes.split(","))
    # Build adapter kwargs for model selection. Only OpenRouter's adapter
    # accepts fast_model/strong_model; other adapters (fake, anthropic, openai)
    # would TypeError. If --strong-model is omitted but --fast-model is given,
    # reuse fast_model for the strong tier — matches the current DeepSeek-V4
    # Flash pattern of using the same model for both tiers.
    adapter_kwargs: dict[str, str] = {}
    if args.provider == "openrouter":
        if args.fast_model:
            adapter_kwargs["fast_model"] = args.fast_model
        if args.strong_model:
            adapter_kwargs["strong_model"] = args.strong_model
        elif args.fast_model:
            adapter_kwargs["strong_model"] = args.fast_model
    llm = make_adapter(args.provider, **adapter_kwargs)
    judge_llm = make_adapter(args.provider, **adapter_kwargs)   # same provider; could be separate

    configs = [load_config(p) for p in args.configs]
    report_dir = Path(args.report)
    report_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.datetime.utcnow().isoformat(timespec="seconds") + "Z"
    progress = Progress(enabled=args.verbose)

    if args.no_async:
        summary = run_battery_serial(
            configs=configs, probes=probes, llm=llm, judge_llm=judge_llm,
            report_dir=report_dir, stamp=stamp, console=console,
            progress=progress, transcripts_per_config=args.transcripts_per_config,
            seed=args.seed,
        )
    else:
        summary = asyncio.run(run_battery_async(
            configs=configs, probes=probes, llm=llm, judge_llm=judge_llm,
            report_dir=report_dir, stamp=stamp, console=console,
            progress=progress, concurrency=args.concurrency,
            transcripts_per_config=args.transcripts_per_config,
            seed=args.seed,
        ))

    won_any = _render_summary(summary, configs, probes, console)
    summary["exit_gate_passed"] = won_any
    # Record which models were used (None when not explicitly set).
    summary["provider"] = args.provider
    summary["fast_model"] = args.fast_model
    summary["strong_model"] = args.strong_model or args.fast_model

    out_path = report_dir / f"battery_{stamp.replace(':', '-')}.json"
    out_path.write_text(json.dumps(summary, indent=2, default=str))
    console.print(f"\nreport written to {out_path}")
    return 0 if won_any else 1


if __name__ == "__main__":
    sys.exit(main())
