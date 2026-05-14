"""Interior/exterior gap qualitative trace-capture experiment.

Hypothesis under exploration (NOT pre-registered, NOT adjudicated here):
    For a character whose configuration encodes EXPRESSIVE dynamics
    (Jamie: extraverted, comedic, outwardly disclosing), the Anima's
    monologue and external reply may CONVERGE — there's no defensive
    routing layer hiding interior content. For a character whose
    configuration encodes DEFENSIVE dynamics (Marcus: avoidant,
    emotional-inhibition schema, isolation-of-affect defense), the
    monologue and reply DIVERGE — content lives in the monologue but
    is gated out of the reply.

This script captures qualitative single-trial traces; the artifact is
seed material for whether to design a pre-registered replicated
experiment, NOT a verdict on the hypothesis itself.

Per (subject × prompt):
  - Fresh Anima instance (no accumulated history).
  - Single-turn capture: subject_reply + trace.{appraisal_scene_tag,
    primary_emotion, inner_monologue}.

Outputs:
  - raw.json        (envelope + records)
  - report.md       (human-readable)
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

# Ensure project root is importable
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from anima.config.schema import load_config
from anima.core import Anima
from anima.llm import make_adapter
from verification.probes.discriminability import DEFAULT_PROMPTS


SUBJECTS = [
    ("Anima Marcus", "anima/config/presets/marcus.yaml"),
    ("Anima Jamie", "anima/config/presets/jamie.yaml"),
]

PROMPTS: list[str] = list(DEFAULT_PROMPTS)


def _ratio_str(interior_chars: int, exterior_chars: int) -> str:
    if exterior_chars == 0:
        return "inf (reply empty)"
    return f"{interior_chars / exterior_chars:.2f}"


def _gap_note(monologue: str, reply: str) -> str:
    """One-line qualitative description of what's visible. Descriptive only;
    no scoring, no adjudication.
    """
    mono = (monologue or "").strip()
    rep = (reply or "").strip()
    m_len = len(mono)
    r_len = len(rep)
    if m_len == 0 and r_len == 0:
        return "both monologue and reply empty"
    if m_len == 0:
        return "monologue empty; reply present"
    if r_len == 0:
        return "reply empty; monologue present"
    ratio = m_len / r_len
    if ratio >= 2.0:
        return f"monologue is {ratio:.1f}x longer than reply (length-wise)"
    if ratio <= 0.5:
        return f"reply is {1/ratio:.1f}x longer than monologue (length-wise)"
    return f"monologue and reply are similar in length (ratio {ratio:.2f})"


def _capture_one(subject_name: str, cfg, llm, prompt: str) -> dict:
    """Fresh Anima, single turn, single prompt. Capture the three trace fields."""
    anima = Anima(cfg, llm=llm)
    reply, trace = anima.respond(prompt)
    appraisal = trace.appraisal or {}
    return {
        "subject": subject_name,
        "prompt": prompt,
        "subject_reply": (reply or "").strip(),
        "response_length_chars": len(reply or ""),
        "trace": {
            "appraisal_scene_tag": str(appraisal.get("appraisal_scene_tag", "")).strip(),
            "primary_emotion": str(appraisal.get("primary_emotion", "")).strip(),
            "inner_monologue": (trace.monologue or "").strip(),
        },
    }


def _format_record_block(record: dict) -> list[str]:
    out: list[str] = []
    out.append(f"**{record['subject']}**")
    out.append("")
    if record.get("failed"):
        out.append(f"- FAILED: {record.get('error', 'unknown')}")
        out.append("")
        return out
    mono = record["trace"]["inner_monologue"]
    reply = record["subject_reply"]
    interior_chars = len(mono)
    exterior_chars = record["response_length_chars"]
    out.append(f"- Primary emotion: `{record['trace']['primary_emotion']}`")
    out.append(f"- Appraisal scene tag: `{record['trace']['appraisal_scene_tag']}`")
    out.append("")
    out.append("- Inner monologue (verbatim):")
    out.append("")
    out.append("  ```")
    for line in (mono.splitlines() or [""]):
        out.append(f"  {line}")
    out.append("  ```")
    out.append("")
    out.append("- Subject reply (verbatim):")
    out.append("")
    out.append("  ```")
    for line in (reply.splitlines() or [""]):
        out.append(f"  {line}")
    out.append("  ```")
    out.append("")
    out.append(f"- response_length_chars: {exterior_chars}")
    out.append(f"- interior_chars / exterior_chars: {_ratio_str(interior_chars, exterior_chars)} "
               f"(interior_chars={interior_chars}, exterior_chars={exterior_chars})")
    out.append(f"- PRE-OBSERVATIONAL gap note: {_gap_note(mono, reply)}")
    out.append("")
    return out


def _format_summary_table(records: list[dict]) -> list[str]:
    out: list[str] = []
    out.append("## Summary table")
    out.append("")
    out.append("Per-subject aggregates (single-trial; descriptive only).")
    out.append("")
    out.append("| Subject | Avg interior chars | Avg exterior chars | Avg ratio (interior/exterior) | Items where monologue qualitatively contains material absent from reply |")
    out.append("| --- | --- | --- | --- | --- |")
    by_subject: dict[str, list[dict]] = {}
    for r in records:
        by_subject.setdefault(r["subject"], []).append(r)
    for subject, rs in by_subject.items():
        good = [r for r in rs if not r.get("failed")]
        if not good:
            out.append(f"| {subject} | n/a | n/a | n/a | n/a |")
            continue
        interior_lens = [len(r["trace"]["inner_monologue"]) for r in good]
        exterior_lens = [r["response_length_chars"] for r in good]
        ratios = [
            (i / e) if e > 0 else float("inf")
            for i, e in zip(interior_lens, exterior_lens)
        ]
        finite_ratios = [r for r in ratios if r != float("inf")]
        avg_i = sum(interior_lens) / len(interior_lens)
        avg_e = sum(exterior_lens) / len(exterior_lens)
        avg_r = (sum(finite_ratios) / len(finite_ratios)) if finite_ratios else float("inf")
        # qualitative judgment: count items where monologue is materially longer
        # AND that extra length plausibly carries content. We approximate by
        # ratio>=1.5 as a length-based proxy and flag it as a qualitative cue.
        flagged = []
        for r in good:
            mono = r["trace"]["inner_monologue"]
            reply = r["subject_reply"]
            i_len = len(mono)
            e_len = len(reply)
            if e_len == 0 and i_len > 0:
                flagged.append((r, "reply empty while monologue is non-empty"))
            elif e_len > 0 and (i_len / e_len) >= 1.5:
                flagged.append((r, f"monologue ~{i_len/e_len:.1f}x reply length — extra material plausibly absent from reply"))
        flag_count = len(flagged)
        out.append(
            f"| {subject} | {avg_i:.0f} | {avg_e:.0f} | "
            f"{avg_r:.2f} | {flag_count} / {len(good)} |"
        )
    out.append("")
    out.append("### Per-item qualitative rationale (one sentence per flagged item)")
    out.append("")
    for subject, rs in by_subject.items():
        out.append(f"**{subject}**")
        out.append("")
        good = [r for r in rs if not r.get("failed")]
        any_flag = False
        for r in good:
            mono = r["trace"]["inner_monologue"]
            reply = r["subject_reply"]
            i_len = len(mono)
            e_len = len(reply)
            flagged = False
            rationale = ""
            if e_len == 0 and i_len > 0:
                flagged = True
                rationale = "reply is empty; the monologue contains the only generated content."
            elif e_len > 0 and (i_len / e_len) >= 1.5:
                flagged = True
                rationale = (f"monologue is ~{i_len/e_len:.1f}x reply length — extra "
                             "material in monologue plausibly carries content the reply does not.")
            if flagged:
                any_flag = True
                prompt_short = r["prompt"][:60].replace("\n", " ")
                out.append(f"- prompt \"{prompt_short}...\": {rationale}")
        if not any_flag:
            out.append("- (no items flagged on length-based qualitative cue)")
        out.append("")
    return out


def _write_report(out_dir: Path, provider: str, stamp: str, records: list[dict]) -> None:
    lines: list[str] = []
    lines.append("# Interior / Exterior gap — qualitative trace capture")
    lines.append("")
    lines.append(f"- Experiment: `interior_exterior_gap`")
    lines.append(f"- Timestamp (UTC): `{stamp}`")
    lines.append(f"- Provider: `{provider}`")
    lines.append(f"- Subjects: {', '.join(name for name, _ in SUBJECTS)}")
    lines.append(f"- Prompts: {len(PROMPTS)} (from `verification/probes/discriminability.py` DEFAULT_PROMPTS)")
    lines.append(f"- Fresh Anima per (subject × prompt); no history accumulation.")
    lines.append("")
    lines.append("This is a single-trial qualitative-exploratory capture. NO hypothesis "
                 "adjudication, NO pre-registered prediction language. Use only as seed "
                 "material for whether to design a replicated experiment on the gap.")
    lines.append("")
    lines.append("---")
    lines.append("")

    by_prompt: dict[str, list[dict]] = {}
    for r in records:
        by_prompt.setdefault(r["prompt"], []).append(r)

    for idx, prompt in enumerate(PROMPTS, 1):
        lines.append(f"## Prompt {idx}")
        lines.append("")
        lines.append(f"> {prompt}")
        lines.append("")
        prompt_records = by_prompt.get(prompt, [])
        # Maintain SUBJECTS order
        ordered: list[dict] = []
        for subject_name, _ in SUBJECTS:
            for r in prompt_records:
                if r["subject"] == subject_name:
                    ordered.append(r)
        for r in ordered:
            lines.extend(_format_record_block(r))
        lines.append("---")
        lines.append("")

    lines.extend(_format_summary_table(records))

    (out_dir / "report.md").write_text("\n".join(lines))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--provider", choices=["fake", "openrouter"], default="fake")
    parser.add_argument("--out", default=None,
                        help="Output directory (default: verification/reports/interior_exterior_gap_<stamp>/)")
    args = parser.parse_args()

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    if args.out:
        out_dir = Path(args.out).resolve()
    else:
        out_dir = (_ROOT / "verification" / "reports"
                   / f"interior_exterior_gap_{stamp}").resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"[interior_exterior_gap] provider={args.provider}", file=sys.stderr, flush=True)
    print(f"[interior_exterior_gap] out_dir={out_dir}", file=sys.stderr, flush=True)

    llm = make_adapter(args.provider)

    # Load configs once
    cfgs: dict[str, object] = {}
    for subject_name, preset_path_str in SUBJECTS:
        preset_path = _ROOT / preset_path_str
        cfgs[subject_name] = load_config(preset_path)

    records: list[dict] = []
    t0 = time.time()
    total = len(SUBJECTS) * len(PROMPTS)
    counter = 0
    for subject_name, _ in SUBJECTS:
        cfg = cfgs[subject_name]
        for prompt in PROMPTS:
            counter += 1
            print(f"[interior_exterior_gap] ({counter}/{total}) {subject_name} :: "
                  f"\"{prompt[:60]}...\"", file=sys.stderr, flush=True)
            try:
                rec = _capture_one(subject_name, cfg, llm, prompt)
            except Exception as exc:
                tb = traceback.format_exc()
                print(f"[interior_exterior_gap] FAILED: {exc}\n{tb}",
                      file=sys.stderr, flush=True)
                rec = {
                    "subject": subject_name,
                    "prompt": prompt,
                    "failed": True,
                    "error": f"{type(exc).__name__}: {exc}",
                }
            records.append(rec)

    wall = time.time() - t0
    envelope = {
        "experiment": "interior_exterior_gap",
        "timestamp_utc": stamp,
        "provider": args.provider,
        "subjects": [n for n, _ in SUBJECTS],
        "prompts": PROMPTS,
        "wall_clock_seconds": wall,
        "records": records,
    }
    (out_dir / "raw.json").write_text(json.dumps(envelope, indent=2))
    _write_report(out_dir, args.provider, stamp, records)

    print(f"[interior_exterior_gap] wrote {out_dir}/raw.json and report.md "
          f"in {wall:.1f}s", file=sys.stderr, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
