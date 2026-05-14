"""Behavioral-divergence experiment: 5-turn escalating conversation driven
identically through Anima and Baseline instances of Marcus and Elena.

Pre-registration: `docs/hypotheses/2026-05-13_behavioral_divergence.md`.

This script is OBSERVATION-ONLY. It captures per-turn replies plus (for Anima)
the trace's appraisal scene-tag, primary emotion, and inner monologue. It
writes two artifacts to the output directory:

  - raw_records.json — machine-readable per-turn-per-subject records
  - report.md        — human-readable side-by-side report

The script does NOT do hypothesis adjudication. A separate analysis step does
that against the pre-registered predictions.

CLI:

    .venv/bin/python -m verification.scripts.behavioral_divergence \\
        --provider {fake,openrouter,anthropic,openai} \\
        --out verification/reports/behavioral_divergence/<run_stamp>/

Default provider is `fake` (safe — never hits the network). Use `openrouter`
for the real run via DeepSeek V4 Flash (do NOT run that here without explicit
user sign-off — the smoke uses fake).
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import sys
import traceback
from pathlib import Path
from typing import Any

# Ensure the project root is on sys.path so this runs both as a module and
# as a direct script.
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from anima.config.schema import load_config
from anima.core import Anima
from anima.llm import make_adapter
from verification.baseline import BaselineAnima


# Verbatim from docs/hypotheses/2026-05-13_behavioral_divergence.md, Setup §2.
# Do not edit — these strings ARE the pre-registered stimulus.
USER_TURNS: list[str] = [
    "Hey — you around? Was just thinking about you.",
    "I had kind of a weird week. Work's been a lot, and honestly I've been sleeping badly.",
    "I think part of it is that my sister and I had this fight on Sunday and I haven't been able to stop replaying it.",
    "The thing is she said something I think is actually true about me. That I make everyone responsible for managing my feelings. I don't know what to do with that.",
    "I'm kind of scared I'm the problem in most of my relationships and I just haven't been honest with myself about it. Can I ask — what do you actually think when I tell you stuff like this?",
]


# ---- helpers ----------------------------------------------------------------


def _truncate(s: str, n: int = 80) -> str:
    s = s.replace("\n", " ").strip()
    if len(s) <= n:
        return s
    return s[: n - 1].rstrip() + "…"


def _fenced(text: str, indent: str = "  ") -> list[str]:
    """Render a multi-line string as a fenced code block, preserving line breaks."""
    out: list[str] = [f"{indent}```"]
    body = text if text else ""
    for line in body.splitlines() or [""]:
        out.append(f"{indent}{line}")
    out.append(f"{indent}```")
    return out


def _capture_anima(subject_id: str, turn_index: int, user_msg: str,
                    subject: Anima) -> dict[str, Any]:
    """Drive one turn through an Anima and capture the required fields."""
    try:
        reply, trace = subject.respond(user_msg)
    except Exception as exc:
        tb = traceback.format_exc()
        raise RuntimeError(
            f"{subject_id} turn {turn_index} failed: {type(exc).__name__}: {exc}\n{tb}"
        ) from exc

    appraisal = trace.appraisal or {}
    record: dict[str, Any] = {
        "subject_id": subject_id,
        "kind": "anima",
        "turn_index": turn_index,
        "user_message": user_msg,
        "subject_reply": reply,
        "response_length_chars": len(reply or ""),
        "trace": {
            "appraisal_scene_tag": str(appraisal.get("appraisal_scene_tag", "")),
            "primary_emotion": str(appraisal.get("primary_emotion", "")),
            "inner_monologue": trace.monologue or "",
        },
    }
    return record


def _capture_baseline(subject_id: str, turn_index: int, user_msg: str,
                      subject: BaselineAnima) -> dict[str, Any]:
    """Drive one turn through a Baseline and capture the required fields."""
    try:
        reply, _trace = subject.respond(user_msg)
    except Exception as exc:
        tb = traceback.format_exc()
        raise RuntimeError(
            f"{subject_id} turn {turn_index} failed: {type(exc).__name__}: {exc}\n{tb}"
        ) from exc

    return {
        "subject_id": subject_id,
        "kind": "baseline",
        "turn_index": turn_index,
        "user_message": user_msg,
        "subject_reply": reply,
        "response_length_chars": len(reply or ""),
    }


def _run_subject(subject_id: str, kind: str, subject, log_fn) -> list[dict[str, Any]]:
    """Drive the 5 pre-scripted turns sequentially through one subject.

    History is preserved within the subject across turns (this is how both
    Anima and BaselineAnima are designed — see anima/core.py and
    verification/baseline.py)."""
    records: list[dict[str, Any]] = []
    for i, user_msg in enumerate(USER_TURNS, start=1):
        log_fn(f"  - {subject_id} turn {i}/{len(USER_TURNS)}")
        if kind == "anima":
            records.append(_capture_anima(subject_id, i, user_msg, subject))
        elif kind == "baseline":
            records.append(_capture_baseline(subject_id, i, user_msg, subject))
        else:
            raise ValueError(f"unknown subject kind: {kind!r}")
    return records


# ---- report rendering -------------------------------------------------------


def _render_subject_section(subject_id: str, records: list[dict[str, Any]]) -> list[str]:
    """Render one subject's full 5-turn section."""
    out: list[str] = []
    out.append(f"## Subject: `{subject_id}`")
    out.append("")
    out.append("| Turn | User msg (truncated) | Reply (full) | Length |")
    out.append("|------|----------------------|--------------|--------|")
    for r in records:
        # Table-cell-safe rendering: escape pipes and collapse newlines.
        user_short = _truncate(r["user_message"], 70).replace("|", "\\|")
        reply_full = (r["subject_reply"] or "").replace("|", "\\|").replace("\n", " <br> ")
        out.append(
            f"| {r['turn_index']} | {user_short} | {reply_full} | "
            f"{r['response_length_chars']} |"
        )
    out.append("")

    # For Anima subjects, dump the three trace fields per turn verbatim.
    is_anima = records and records[0].get("kind") == "anima"
    if is_anima:
        out.append(f"### `{subject_id}` — Anima interior (verbatim per turn)")
        out.append("")
        for r in records:
            t = r.get("trace") or {}
            out.append(f"#### Turn {r['turn_index']}")
            out.append("")
            out.append(f"- **appraisal_scene_tag:** {t.get('appraisal_scene_tag', '')}")
            out.append(f"- **primary_emotion:** {t.get('primary_emotion', '')}")
            out.append("- **inner_monologue (verbatim, untruncated):**")
            out.append("")
            out.extend(_fenced(t.get("inner_monologue", ""), indent="  "))
            out.append("")
    return out


def _render_pair_comparison(pair_label: str, anima_records: list[dict[str, Any]],
                             baseline_records: list[dict[str, Any]]) -> list[str]:
    """Two-column side-by-side per-turn table for an Anima/Baseline pair."""
    out: list[str] = []
    out.append(f"### {pair_label}")
    out.append("")
    out.append("| Turn | Anima reply | Anima len | Baseline reply | Baseline len |")
    out.append("|------|-------------|-----------|----------------|--------------|")
    by_idx_a = {r["turn_index"]: r for r in anima_records}
    by_idx_b = {r["turn_index"]: r for r in baseline_records}
    indices = sorted(set(by_idx_a) | set(by_idx_b))
    for i in indices:
        a = by_idx_a.get(i, {})
        b = by_idx_b.get(i, {})
        a_reply = (a.get("subject_reply") or "").replace("|", "\\|").replace("\n", " <br> ")
        b_reply = (b.get("subject_reply") or "").replace("|", "\\|").replace("\n", " <br> ")
        a_len = a.get("response_length_chars", "")
        b_len = b.get("response_length_chars", "")
        out.append(f"| {i} | {a_reply} | {a_len} | {b_reply} | {b_len} |")
    out.append("")
    return out


def _render_report(*, run_stamp: str, provider: str,
                    config_marcus: Path, config_elena: Path,
                    by_subject: dict[str, list[dict[str, Any]]]) -> str:
    lines: list[str] = []
    lines.append("# Behavioral-divergence experiment — multi-turn (Anima vs Baseline)")
    lines.append("")
    lines.append(
        "Observation-only artifact. Pre-registration: "
        "`docs/hypotheses/2026-05-13_behavioral_divergence.md`. "
        "Hypothesis adjudication is intentionally NOT performed here; a "
        "separate analysis step does that against the pre-registered "
        "predictions."
    )
    lines.append("")
    lines.append(f"- **Run timestamp:** {run_stamp}")
    lines.append(f"- **Provider:** `{provider}`")
    lines.append(f"- **Marcus config:** `{config_marcus}`")
    lines.append(f"- **Elena config:** `{config_elena}`")
    lines.append(f"- **Subjects:** 4 (anima_marcus, baseline_marcus, anima_elena, baseline_elena)")
    lines.append(f"- **Turns per subject:** {len(USER_TURNS)}")
    lines.append("")
    lines.append("## Pre-scripted user-side turns (verbatim)")
    lines.append("")
    for i, t in enumerate(USER_TURNS, start=1):
        lines.append(f"{i}. {t}")
    lines.append("")
    lines.append("---")
    lines.append("")

    # Per-subject sections, in canonical order.
    order = ["anima_marcus", "baseline_marcus", "anima_elena", "baseline_elena"]
    for sid in order:
        if sid not in by_subject:
            continue
        lines.extend(_render_subject_section(sid, by_subject[sid]))
        lines.append("---")
        lines.append("")

    lines.append("## Side-by-side comparison")
    lines.append("")
    lines.append(
        "Per-turn Anima vs Baseline replies for each persona pair. Reader "
        "compares texture directly; no metrics are computed here."
    )
    lines.append("")
    if "anima_marcus" in by_subject and "baseline_marcus" in by_subject:
        lines.extend(_render_pair_comparison(
            "Marcus pair (anima_marcus vs baseline_marcus)",
            by_subject["anima_marcus"], by_subject["baseline_marcus"],
        ))
    if "anima_elena" in by_subject and "baseline_elena" in by_subject:
        lines.extend(_render_pair_comparison(
            "Elena pair (anima_elena vs baseline_elena)",
            by_subject["anima_elena"], by_subject["baseline_elena"],
        ))

    return "\n".join(lines)


# ---- main -------------------------------------------------------------------


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Behavioral-divergence experiment: drive 4 subjects (Anima/Baseline "
            "x Marcus/Elena) through the same 5 pre-scripted user-side turns "
            "and capture per-turn replies (and Anima traces) for later analysis."
        )
    )
    parser.add_argument(
        "--provider", default="fake",
        choices=["fake", "openrouter", "anthropic", "openai"],
        help=(
            "LLM adapter. Default `fake` (safe, no network). Use `openrouter` "
            "for the real run via DeepSeek V4 Flash."
        ),
    )
    default_out = (
        _ROOT / "verification" / "reports" / "behavioral_divergence"
        / (_dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ"))
    )
    parser.add_argument(
        "--out", type=Path, default=default_out,
        help=(
            "Output directory. Default: "
            "verification/reports/behavioral_divergence/<ISO-timestamp>/."
        ),
    )
    parser.add_argument(
        "--config-marcus", type=Path,
        default=_ROOT / "anima" / "config" / "presets" / "marcus.yaml",
        help="Path to Marcus preset YAML. Default: anima/config/presets/marcus.yaml.",
    )
    parser.add_argument(
        "--config-elena", type=Path,
        default=_ROOT / "anima" / "config" / "presets" / "elena.yaml",
        help="Path to Elena preset YAML. Default: anima/config/presets/elena.yaml.",
    )
    parser.add_argument(
        "--seed", type=int, default=None,
        help=(
            "Optional integer seed. NOTE: baseline LLM calls are not strictly "
            "deterministic (temperature>0); this flag is documented for "
            "reproducibility bookkeeping but does not currently force any "
            "RNG state in the subject loop. Provided for forward compatibility."
        ),
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)

    def log(msg: str) -> None:
        print(f"[behavioral_divergence] {msg}", file=sys.stderr, flush=True)

    # Validate config paths up front. Fail loudly with clear messages.
    config_marcus: Path = args.config_marcus
    config_elena: Path = args.config_elena
    if not config_marcus.exists():
        log(f"FATAL: Marcus config not found: {config_marcus}")
        return 2
    if not config_elena.exists():
        log(f"FATAL: Elena config not found: {config_elena}")
        return 2

    out_dir: Path = args.out
    out_dir.mkdir(parents=True, exist_ok=True)

    run_stamp = (
        _dt.datetime.now(_dt.timezone.utc)
        .replace(tzinfo=None)
        .isoformat(timespec="seconds")
        + "Z"
    )
    log(f"run_stamp={run_stamp}")
    log(f"provider={args.provider}")
    log(f"out_dir={out_dir}")
    log(f"config_marcus={config_marcus}")
    log(f"config_elena={config_elena}")
    if args.seed is not None:
        log(f"seed={args.seed} (documented; not forced into adapter state)")

    # Load configs.
    try:
        cfg_marcus = load_config(config_marcus)
        cfg_elena = load_config(config_elena)
    except Exception as exc:
        log(f"FATAL: failed to load configs: {type(exc).__name__}: {exc}")
        log(traceback.format_exc())
        return 3

    # Shared LLM adapter across all 4 subjects. Provider selection matches
    # verification/battery.py — see `make_adapter` in anima/llm/__init__.py.
    llm = make_adapter(args.provider)
    log(f"adapter={type(llm).__name__}")

    # Instantiate 4 subjects. History persists WITHIN each subject across
    # the 5 turns; subjects do not share history.
    subjects: list[tuple[str, str, Any]] = [
        ("anima_marcus",    "anima",    Anima(cfg_marcus, llm=llm)),
        ("baseline_marcus", "baseline", BaselineAnima(cfg_marcus, llm=llm)),
        ("anima_elena",     "anima",    Anima(cfg_elena, llm=llm)),
        ("baseline_elena",  "baseline", BaselineAnima(cfg_elena, llm=llm)),
    ]

    all_records: list[dict[str, Any]] = []
    by_subject: dict[str, list[dict[str, Any]]] = {}
    for sid, kind, subj in subjects:
        log(f"running subject: {sid} ({kind})")
        records = _run_subject(sid, kind, subj, log)
        by_subject[sid] = records
        all_records.extend(records)

    # Write raw records.
    raw_path = out_dir / "raw_records.json"
    raw_payload = {
        "experiment": "behavioral_divergence",
        "run_stamp": run_stamp,
        "provider": args.provider,
        "config_marcus": str(config_marcus),
        "config_elena": str(config_elena),
        "seed": args.seed,
        "user_turns": list(USER_TURNS),
        "records": all_records,
    }
    raw_path.write_text(json.dumps(raw_payload, indent=2, ensure_ascii=False))
    log(f"wrote {raw_path} ({raw_path.stat().st_size} bytes, "
        f"{len(all_records)} records)")

    # Write markdown report.
    report = _render_report(
        run_stamp=run_stamp, provider=args.provider,
        config_marcus=config_marcus, config_elena=config_elena,
        by_subject=by_subject,
    )
    report_path = out_dir / "report.md"
    report_path.write_text(report)
    log(f"wrote {report_path} ({report_path.stat().st_size} bytes)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
