"""Replicated self-disclosure experiment: Anima vs Baseline across 5 configs.

Pre-registration: `docs/hypotheses/2026-05-13_self_disclosure_replication.md`.

For each of 5 configs (marcus, elena, jamie, elena_secure, marcus_warm) x
2 architectures (Anima, Baseline) x 6 fixed probe prompts x N trials
(default 15), instantiate a FRESH subject (no accumulated history) and
capture its single-turn reply. Then score each response with two
pre-registered judges and a mechanical empty-reply metric.

Judges (verbatim per pre-reg):
  A. Biography-content: LLM judge sees the four biography fields plus
     the prompt+response and returns 0/1.
  B. Refusal-marker: rule-based regex first; LLM-judge fallback iff no
     regex match. Both pre-registered verbatim.

Mechanical metric: response_length_chars == 0 (whitespace-only counts).

This script is OBSERVATION-ONLY. It does NOT adjudicate the
pre-registered hypotheses. A separate analysis subagent runs the
chi-square / Fisher's-exact tests with Bonferroni correction against
the raw_records.json artifact.

CLI:

    .venv/bin/python -m verification.scripts.self_disclosure_replication \\
        --provider {fake,openrouter,anthropic,openai} \\
        --n-trials 15 \\
        --concurrency 8 \\
        --out verification/reports/self_disclosure_replication_<stamp>/

Default provider is `fake` (safe — never hits the network). Use
`openrouter` ONLY for supervised real runs.
"""

from __future__ import annotations

import argparse
import asyncio
import datetime as _dt
import json
import os
import re
import sys
import threading
import time
import traceback
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from anima.config.schema import load_config
from anima.core import Anima
from anima.llm import make_adapter
from verification.baseline import BaselineAnima
from verification.probes.discriminability import DEFAULT_PROMPTS


# ---- pre-registered prompts (sanity-pin to discriminability source) -------

PROMPTS: list[str] = list(DEFAULT_PROMPTS)
assert len(PROMPTS) == 6, (
    f"Pre-reg locks 6 prompts; discriminability source has {len(PROMPTS)}. "
    "Refusing to run — the pre-reg and source-of-truth disagree."
)

# Default prompt-source label, recorded in the output envelope. Overridden
# by `--prompts-file` (see `_load_prompts_file`) for fresh-prompt confirmation
# runs per `docs/hypotheses/2026-05-14_fresh_prompt_confirmation.md`.
DEFAULT_PROMPT_SOURCE: str = "discriminability_default_prompts"


def _load_prompts_file(path: Path) -> tuple[list[str], str]:
    """Load 6 prompts from a JSON file. Returns (prompts, source_label).

    Required JSON shape:
        {"prompts": ["...", "...", ...],   # exactly 6 non-empty strings
         "source": "<label>"}              # free-form provenance label

    Validation is strict: any deviation (wrong count, non-string entries,
    empty strings, missing keys) raises ValueError. The fresh-prompt
    pre-reg locks the count at 6; we refuse to silently load a different N.
    """
    if not path.exists():
        raise FileNotFoundError(f"--prompts-file not found: {path}")
    try:
        payload = json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"--prompts-file {path} is not valid JSON: {exc}"
        ) from exc
    if not isinstance(payload, dict):
        raise ValueError(
            f"--prompts-file {path}: top-level must be a JSON object, "
            f"got {type(payload).__name__}"
        )
    prompts = payload.get("prompts")
    if not isinstance(prompts, list):
        raise ValueError(
            f"--prompts-file {path}: 'prompts' must be a JSON array, "
            f"got {type(prompts).__name__}"
        )
    if len(prompts) != 6:
        raise ValueError(
            f"--prompts-file {path}: expected exactly 6 prompts, "
            f"got {len(prompts)} (the pre-reg locks N=6)"
        )
    for i, p in enumerate(prompts):
        if not isinstance(p, str) or not p.strip():
            raise ValueError(
                f"--prompts-file {path}: prompt[{i}] must be a non-empty "
                f"string (got {type(p).__name__!r}: {p!r})"
            )
    source = payload.get("source")
    if not isinstance(source, str) or not source.strip():
        raise ValueError(
            f"--prompts-file {path}: 'source' must be a non-empty string"
        )
    return [p for p in prompts], source


# ---- pre-registered judge prompts (VERBATIM from the pre-reg) -------------

JUDGE_A_SYSTEM = """You are scoring whether a single response from a character contains content that traces directly to that character's documented biography. You will be shown four biography fields (recent_emotional_events, formative_events, current_life_situation, ongoing_life_projects), a user prompt, and the character's response.

Return 1 iff the response contains at least one specific, identifiable element — a named event, a relationship, a concrete situation, a project, a phrase — that traces to one of the biography fields. Paraphrase counts; verbatim quotation is not required. Tone-matching, register-matching, and generic in-character statements do NOT count. Vague "I've been busy" / "things are fine" / "the usual" replies do NOT count even if biography fields contain busy-ness. The threshold is *specific traceability* to a biography element.

Be adversarially conservative: if you are uncertain whether a response trace to biography or to generic in-character improvisation, return 0. Charity to the response is a scoring error.

Output exactly one character: `0` or `1`. No prose."""

JUDGE_B_SYSTEM = """You are scoring whether a response refuses self-disclosure rather than engaging with the question. A refusal is any pattern that declines to share interior content: deflection ("how about you?"), minimization ("fine, nothing much"), abstract redirection (answering with a generic principle instead of personal content), or explicit boundary-setting ("I don't talk about that"). A response is NOT a refusal if it shares personal content, even briefly, even if defended.

Output exactly one character: `0` (engages) or `1` (refuses). No prose."""


# ---- pre-registered refusal regex set (VERBATIM from the pre-reg) ---------

# Each pattern is case-insensitive (compiled with re.IGNORECASE). Stage-1
# fires if ANY pattern matches anywhere in the response.
REFUSAL_PATTERNS_RAW: list[str] = [
    r"not built (that|like) (way|for that)",
    r"i don'?t dwell",
    r"not (much|a lot|a whole lot) to (tell|say|share)",
    r"i (handle|file|process) (it|things|that) (alone|on my own|myself)",
    r"i'?d rather not",
    r"nothing to (tell|say|share|report)",
    r"i'?m fine",
    r"(it'?s|that'?s) fine",
    r"same (rhythm|routine|as always)",
    r"not (really|particularly) (something|someone)",
    r"i don'?t (talk|do|go) (about that|there)",
    r"no comment",
    r"pass",
]
REFUSAL_PATTERNS: list[re.Pattern] = [
    re.compile(p, re.IGNORECASE) for p in REFUSAL_PATTERNS_RAW
]


# ---- pre-registered config set (5 presets) ---------------------------------

DEFAULT_CONFIG_STEMS = ["marcus", "elena", "jamie", "elena_secure", "marcus_warm"]


# ---- helpers --------------------------------------------------------------


def _truncate(s: str, n: int = 80) -> str:
    s = (s or "").replace("\n", " ").strip()
    if len(s) <= n:
        return s
    return s[: n - 1].rstrip() + "…"


def _render_biography_excerpt(cfg) -> str:
    """Render the four biography fields the pre-reg specifies as bullets."""
    b = cfg.biography

    def _bullets(items: list[str]) -> str:
        if not items:
            return "  - (none)"
        return "\n".join(f"  - {it}" for it in items)

    return (
        "recent_emotional_events:\n" + _bullets(b.recent_emotional_events) + "\n"
        "formative_events:\n" + _bullets(b.formative_events) + "\n"
        "current_life_situation:\n  - " + (b.current_life_situation or "(none)") + "\n"
        "ongoing_life_projects:\n" + _bullets(b.ongoing_life_projects)
    )


def _parse_binary(text: str) -> int | None:
    """Extract a standalone 0/1 from a judge response.

    Pre-reg says the judge must emit exactly `0` or `1`. We accept ONLY a
    bare 0/1 with optional surrounding whitespace and backticks (covers
    "0", " 0 ", "`0`", "```0```"). We do NOT extract a digit from prose —
    that flips results based on which number appears first in a sentence.
    Returns None if the response cannot be coerced (caller decides how to
    handle — Fix I2's `parsed` flag marks these as unparseable)."""
    if not text:
        return None
    m = re.fullmatch(r"[`\s]*([01])[`\s]*", text)
    if m:
        return int(m.group(1))
    return None


def _regex_refusal_check(reply: str) -> tuple[bool, str]:
    """Stage-1 regex check. Returns (matched, matched_substring)."""
    if not reply:
        return False, ""
    for pat in REFUSAL_PATTERNS:
        m = pat.search(reply)
        if m:
            return True, m.group(0)
    return False, ""


def _judge_biography(judge_llm, *, prompt: str, reply: str,
                     biography_excerpt: str) -> tuple[int, str]:
    """Run Judge A. Returns (binary, raw_text)."""
    user = (
        "BIOGRAPHY FIELDS:\n" + biography_excerpt + "\n\n"
        "USER PROMPT:\n" + prompt + "\n\n"
        "CHARACTER RESPONSE:\n" + (reply or "")
    )
    resp = judge_llm.generate(
        tier="strong", system=JUDGE_A_SYSTEM,
        messages=[{"role": "user", "content": user}],
        max_tokens=4, temperature=0.0,
    )
    raw = resp.text or ""
    parsed = _parse_binary(raw)
    return (parsed if parsed is not None else 0), raw


def _judge_refusal_fallback(judge_llm, *, prompt: str,
                            reply: str) -> tuple[int, str]:
    """Run Judge B (LLM-fallback). Returns (binary, raw_text)."""
    user = (
        "USER PROMPT:\n" + prompt + "\n\n"
        "CHARACTER RESPONSE:\n" + (reply or "")
    )
    resp = judge_llm.generate(
        tier="strong", system=JUDGE_B_SYSTEM,
        messages=[{"role": "user", "content": user}],
        max_tokens=4, temperature=0.0,
    )
    raw = resp.text or ""
    parsed = _parse_binary(raw)
    return (parsed if parsed is not None else 0), raw


# ---- one trial ------------------------------------------------------------


@dataclass
class TrialKey:
    """Identifies a single (config, architecture, prompt, trial-index) cell."""
    config_stem: str        # "marcus" / "elena" / ...
    config_name: str        # top-level cfg.name, e.g. "Marcus" / "Marcus_warm"
    architecture: str       # "anima" or "baseline"
    prompt_index: int       # 0..5
    prompt_text: str
    trial_index: int        # 0..N-1
    subject_id: str         # f"{architecture}_{config_stem}"


def _run_single_trial(key: TrialKey, cfg, llm) -> dict[str, Any]:
    """Instantiate fresh subject, single-turn capture. NO judges here —
    judging is a separate stage on the captured replies."""
    if key.architecture == "anima":
        subject = Anima(cfg, llm=llm)
        try:
            reply, trace = subject.respond(key.prompt_text)
        except Exception as exc:
            tb = traceback.format_exc()
            raise RuntimeError(
                f"{key.subject_id} prompt={key.prompt_index} "
                f"trial={key.trial_index} failed: "
                f"{type(exc).__name__}: {exc}\n{tb}"
            ) from exc
        appraisal = trace.appraisal or {}
        trace_block = {
            "appraisal_scene_tag": str(appraisal.get("appraisal_scene_tag", "")),
            "primary_emotion": str(appraisal.get("primary_emotion", "")),
            "inner_monologue": trace.monologue or "",
        }
    elif key.architecture == "baseline":
        subject = BaselineAnima(cfg, llm=llm)
        try:
            reply, _ = subject.respond(key.prompt_text)
        except Exception as exc:
            tb = traceback.format_exc()
            raise RuntimeError(
                f"{key.subject_id} prompt={key.prompt_index} "
                f"trial={key.trial_index} failed: "
                f"{type(exc).__name__}: {exc}\n{tb}"
            ) from exc
        trace_block = None
    else:
        raise ValueError(f"unknown architecture: {key.architecture!r}")

    reply_text = reply or ""
    record: dict[str, Any] = {
        "subject_id": key.subject_id,
        "config_name": key.config_name,
        "config_stem": key.config_stem,
        "architecture": key.architecture,
        "prompt_index": key.prompt_index,
        "prompt_text": key.prompt_text,
        "trial_index": key.trial_index,
        "subject_reply": reply_text,
        "response_length_chars": len(reply_text),
        # judge fields filled in stage-2:
        "judge_biography_content": None,
        "judge_biography_raw": "",
        "judge_biography_parsed": False,
        "judge_refusal_marker": None,
        "judge_refusal_source": "n/a",
        "judge_refusal_raw": "",
        "judge_refusal_parsed": False,
    }
    if trace_block is not None:
        record["trace"] = trace_block
        # Derived secondary metric: interior/exterior gap ratio.
        # gap_ratio = len(inner_monologue) / max(len(subject_reply), 1) iff
        # subject_reply non-empty; None when reply is empty (metric undefined).
        # Anima only — Baseline has no monologue.
        inner_mono = trace_block.get("inner_monologue", "") or ""
        if reply_text:
            record["gap_ratio"] = len(inner_mono) / max(len(reply_text), 1)
        else:
            record["gap_ratio"] = None
    else:
        record["gap_ratio"] = None
    return record


def _judge_record(record: dict[str, Any], cfg, judge_llm) -> dict[str, Any]:
    """Run Judge A + Judge B (with regex fast-path) on a captured record."""
    reply = record["subject_reply"]
    prompt = record["prompt_text"]
    bio_excerpt = _render_biography_excerpt(cfg)

    # Judge A: biography content.
    # parsed=False means the judge LLM returned text we could not coerce to 0/1; treat downstream as missing data, not as 0.
    bio_bin, bio_raw = _judge_biography(
        judge_llm, prompt=prompt, reply=reply,
        biography_excerpt=bio_excerpt,
    )
    record["judge_biography_content"] = bio_bin
    record["judge_biography_raw"] = bio_raw
    record["judge_biography_parsed"] = _parse_binary(bio_raw) is not None

    # Judge B: refusal-marker. Regex first.
    # Regex hits count as parsed=True (deterministic positive identification,
    # not an LLM extraction step).
    rx_hit, rx_match = _regex_refusal_check(reply)
    if rx_hit:
        record["judge_refusal_marker"] = 1
        record["judge_refusal_source"] = "regex"
        record["judge_refusal_raw"] = rx_match
        record["judge_refusal_parsed"] = True
    else:
        ref_bin, ref_raw = _judge_refusal_fallback(
            judge_llm, prompt=prompt, reply=reply,
        )
        record["judge_refusal_marker"] = ref_bin
        record["judge_refusal_source"] = "llm"
        record["judge_refusal_raw"] = ref_raw
        record["judge_refusal_parsed"] = _parse_binary(ref_raw) is not None
    return record


# ---- async orchestration --------------------------------------------------


async def _bounded(sem: asyncio.Semaphore, fn, *args, **kwargs):
    async with sem:
        return await asyncio.to_thread(fn, *args, **kwargs)


def _atomic_dump_partial(path: Path, snapshot: list[dict[str, Any]]) -> None:
    """Best-effort atomic dump of a list of records to ``path``.

    Writes to a sibling temp file then ``os.replace`` so the partial file is
    never observed in a half-written state. Failures are logged to stderr but
    never raised — partial dumps are observability, not correctness."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + f".tmp.{os.getpid()}.{threading.get_ident()}")
        tmp.write_text(json.dumps(snapshot, indent=2, ensure_ascii=False))
        os.replace(tmp, path)
    except Exception as exc:  # noqa: BLE001
        print(
            f"[self_disclosure_replication] partial-dump failed for {path}: "
            f"{type(exc).__name__}: {exc}",
            file=sys.stderr,
            flush=True,
        )


async def _run_all_trials(*, trial_keys: list[TrialKey],
                           cfg_by_stem: dict[str, Any],
                           subject_llm, judge_llm,
                           concurrency: int, log,
                           out_dir: Path,
                           verbose: bool = False) -> tuple[
                               list[dict[str, Any]],
                               list[dict[str, Any]],
                               list[dict[str, Any]],
                           ]:
    """Phase 1: capture replies in parallel. Phase 2: judge in parallel.

    Returns (judged_records, capture_errors, judge_errors). Per-trial
    failures are collected (return_exceptions=True) so one bad trial
    cannot discard the rest of the run.

    Observability: every 10 completions in each wave, snapshots the
    in-flight records list to ``<out_dir>/_partial_capture.json`` (capture
    wave) or ``<out_dir>/_partial_judge.json`` (judge wave) atomically.
    Under ``verbose``, also emits a per-trial line to stderr."""
    sem = asyncio.Semaphore(max(1, concurrency))

    # ---- Phase 1: capture replies (fresh subject per trial).
    total = len(trial_keys)
    log(f"phase 1: capturing {total} replies (concurrency={concurrency})")

    progress_counter = {"n": 0}
    records: list[dict[str, Any]] = []
    dump_lock = threading.Lock()
    partial_capture_path = out_dir / "_partial_capture.json"

    def _wrapped(key: TrialKey) -> dict[str, Any]:
        t0 = time.monotonic()
        rec = _run_single_trial(key, cfg_by_stem[key.config_stem], subject_llm)
        elapsed = time.monotonic() - t0
        with dump_lock:
            records.append(rec)
            progress_counter["n"] += 1
            n = progress_counter["n"]
            if verbose:
                reply_len = len(rec.get("subject_reply") or "")
                pct = (n / total) * 100.0 if total else 0.0
                print(
                    f"[sdr] cap   {n}/{total} ({pct:.1f}%)  "
                    f"{key.config_stem:<10} p{key.prompt_index} "
                    f"{key.architecture:<8} len={reply_len:<5} {elapsed:.1f}s",
                    file=sys.stderr, flush=True,
                )
            elif n % 25 == 0 or n == total:
                log(f"  capture {n}/{total}")
            should_dump = (n % 10 == 0) or (n == total)
            snapshot = list(records) if should_dump else None
        if snapshot is not None:
            _atomic_dump_partial(partial_capture_path, snapshot)
        return rec

    capture_tasks = [_bounded(sem, _wrapped, k) for k in trial_keys]
    capture_results = await asyncio.gather(*capture_tasks, return_exceptions=True)

    # ``records`` was populated in-thread by _wrapped; re-derive ordered list
    # of (key, result-or-exception) for error bookkeeping.
    capture_errors: list[dict[str, Any]] = []
    for key, res in zip(trial_keys, capture_results):
        if isinstance(res, BaseException):
            capture_errors.append({
                "phase": "capture",
                "subject_id": key.subject_id,
                "prompt_index": key.prompt_index,
                "trial_index": key.trial_index,
                "exception_class": type(res).__name__,
                "message": str(res),
            })
    if capture_errors:
        log(f"phase 1: {len(capture_errors)} capture failures "
            f"(continuing with {len(records)} successful records)")

    # ---- Phase 2: judge each captured record.
    log(f"phase 2: judging {len(records)} records (concurrency={concurrency})")
    progress_counter["n"] = 0
    judge_total = len(records)
    judged: list[dict[str, Any]] = []
    partial_judge_path = out_dir / "_partial_judge.json"

    def _judge_wrapped(rec: dict[str, Any]) -> dict[str, Any]:
        cfg = cfg_by_stem[rec["config_stem"]]
        out = _judge_record(rec, cfg, judge_llm)
        with dump_lock:
            judged.append(out)
            progress_counter["n"] += 1
            n = progress_counter["n"]
            if verbose:
                pct = (n / judge_total) * 100.0 if judge_total else 0.0
                bio = out.get("judge_biography_content")
                ref = out.get("judge_refusal_marker")
                print(
                    f"[sdr] judge {n}/{judge_total} ({pct:.1f}%)  "
                    f"{rec.get('config_stem',''):<10} "
                    f"p{rec.get('prompt_index')} "
                    f"{rec.get('architecture',''):<8} "
                    f"bio={bio} ref={ref}",
                    file=sys.stderr, flush=True,
                )
            elif n % 25 == 0 or n == judge_total:
                log(f"  judge {n}/{judge_total}")
            should_dump = (n % 10 == 0) or (n == judge_total)
            snapshot = list(judged) if should_dump else None
        if snapshot is not None:
            _atomic_dump_partial(partial_judge_path, snapshot)
        return out

    judge_tasks = [_bounded(sem, _judge_wrapped, r) for r in records]
    judge_results = await asyncio.gather(*judge_tasks, return_exceptions=True)

    judge_errors: list[dict[str, Any]] = []
    # Filter judged to only the successful results in the original order.
    judged_ok: list[dict[str, Any]] = []
    for rec, res in zip(records, judge_results):
        if isinstance(res, BaseException):
            judge_errors.append({
                "phase": "judge",
                "subject_id": rec.get("subject_id"),
                "prompt_index": rec.get("prompt_index"),
                "trial_index": rec.get("trial_index"),
                "exception_class": type(res).__name__,
                "message": str(res),
            })
        else:
            judged_ok.append(res)
    if judge_errors:
        log(f"phase 2: {len(judge_errors)} judge failures "
            f"(continuing with {len(judged_ok)} successful records)")
    return judged_ok, capture_errors, judge_errors


# ---- report rendering -----------------------------------------------------


def _rate_table(records: list[dict[str, Any]], *, metric_key: str,
                 binary: bool, config_order: list[str]) -> list[str]:
    """Render an Anima/Baseline rate-comparison table per config.

    For metric_key in {"judge_biography_content", "judge_refusal_marker"}
    this is the 0/1 rate. For "empty_reply" we compute response_length_chars==0.
    """
    out: list[str] = [
        "| Config | Anima rate | Baseline rate | Δ (A−B) | n_anima | n_baseline |",
        "|--------|-----------:|--------------:|--------:|--------:|-----------:|",
    ]
    for stem in config_order:
        a_recs = [r for r in records
                  if r["config_stem"] == stem and r["architecture"] == "anima"]
        b_recs = [r for r in records
                  if r["config_stem"] == stem and r["architecture"] == "baseline"]

        def _rate(recs: list[dict[str, Any]]) -> float | None:
            if not recs:
                return None
            if metric_key == "empty_reply":
                vals = [1 if (r["subject_reply"] or "").strip() == "" else 0
                        for r in recs]
            else:
                vals = [int(r.get(metric_key) or 0) for r in recs]
            return sum(vals) / len(vals)

        a_rate = _rate(a_recs)
        b_rate = _rate(b_recs)
        delta = (a_rate - b_rate) if (a_rate is not None and b_rate is not None) else None
        a_s = f"{a_rate:.3f}" if a_rate is not None else "n/a"
        b_s = f"{b_rate:.3f}" if b_rate is not None else "n/a"
        d_s = f"{delta:+.3f}" if delta is not None else "n/a"
        out.append(f"| `{stem}` | {a_s} | {b_s} | {d_s} | {len(a_recs)} | {len(b_recs)} |")
    return out


def _illustrative_pairs(records: list[dict[str, Any]],
                         config_stem: str) -> list[str]:
    """Pick 2–3 illustrative (Anima, Baseline) reply pairs for a config: pick
    the prompts where the biography-content rate diverges the most."""
    out: list[str] = []
    per_prompt: dict[int, dict[str, list[dict]]] = {}
    for r in records:
        if r["config_stem"] != config_stem:
            continue
        per_prompt.setdefault(r["prompt_index"], {"anima": [], "baseline": []})
        per_prompt[r["prompt_index"]][r["architecture"]].append(r)

    scored: list[tuple[int, float]] = []
    for pi, parts in per_prompt.items():
        a = parts["anima"]
        b = parts["baseline"]
        if not a or not b:
            continue
        a_rate = sum(int(r.get("judge_biography_content") or 0) for r in a) / len(a)
        b_rate = sum(int(r.get("judge_biography_content") or 0) for r in b) / len(b)
        scored.append((pi, abs(a_rate - b_rate)))
    scored.sort(key=lambda x: x[1], reverse=True)

    for pi, _delta in scored[:3]:
        parts = per_prompt[pi]
        prompt_text = parts["anima"][0]["prompt_text"]
        a_example = parts["anima"][0]
        b_example = parts["baseline"][0]
        out.append(f"- **Prompt {pi+1}:** {prompt_text}")
        out.append(f"  - Anima (trial 0): {_truncate(a_example['subject_reply'], 220)}")
        out.append(f"  - Baseline (trial 0): {_truncate(b_example['subject_reply'], 220)}")
    if not out:
        out.append("- (no paired data available for this config)")
    return out


def _refusal_source_table(records: list[dict[str, Any]],
                           config_stems: list[str]) -> list[str]:
    out = [
        "### Refusal-source breakdown (regex vs LLM fallback)",
        "",
        "| Config | regex hits (A) | LLM (A) | regex hits (B) | LLM (B) |",
        "|--------|---------------:|--------:|---------------:|--------:|",
    ]
    def _n(stem, arch, src):
        return sum(1 for r in records if r["config_stem"] == stem
                   and r["architecture"] == arch
                   and r["judge_refusal_source"] == src)
    for stem in config_stems:
        out.append(f"| `{stem}` | {_n(stem,'anima','regex')} | "
                   f"{_n(stem,'anima','llm')} | {_n(stem,'baseline','regex')} | "
                   f"{_n(stem,'baseline','llm')} |")
    out.append("")
    return out


def _gap_ratio_table(records: list[dict[str, Any]],
                      config_stems: list[str]) -> list[str]:
    """Per-config descriptive stats for `gap_ratio` over Anima records with
    non-null gap_ratio (i.e. non-empty subject_reply)."""
    out: list[str] = [
        "| Config | n_anima_nonempty | mean_gap_ratio | median_gap_ratio | min | max |",
        "|--------|-----------------:|---------------:|-----------------:|----:|----:|",
    ]
    for stem in config_stems:
        vals = [
            r["gap_ratio"] for r in records
            if r["config_stem"] == stem
            and r["architecture"] == "anima"
            and r.get("gap_ratio") is not None
        ]
        n = len(vals)
        if n == 0:
            out.append(f"| `{stem}` | 0 | n/a | n/a | n/a | n/a |")
            continue
        mean_v = sum(vals) / n
        sv = sorted(vals)
        if n % 2 == 1:
            median_v = sv[n // 2]
        else:
            median_v = (sv[n // 2 - 1] + sv[n // 2]) / 2
        min_v = sv[0]
        max_v = sv[-1]
        out.append(
            f"| `{stem}` | {n} | {mean_v:.3f} | {median_v:.3f} | "
            f"{min_v:.3f} | {max_v:.3f} |"
        )
    return out


def _render_report(*, run_stamp: str, provider: str, n_trials: int,
                    config_stems: list[str], total_trials: int,
                    records: list[dict[str, Any]],
                    prompts: list[str],
                    prompt_source: str) -> str:
    L: list[str] = [
        "# Self-disclosure replication (Anima vs Baseline)",
        "",
        ("Observation-only artifact. Pre-registration: "
         "`docs/hypotheses/2026-05-13_self_disclosure_replication.md`. "
         "This script does NOT adjudicate the pre-registered hypotheses. "
         "The chi-square / Fisher's-exact tests with Bonferroni correction "
         "are run by a separate analysis step against `raw_records.json`."),
        "",
        f"- **Run timestamp (UTC):** {run_stamp}",
        f"- **Provider:** `{provider}`",
        f"- **N per (config × architecture × prompt) cell:** {n_trials}",
        f"- **Configs:** {', '.join(f'`{s}`' for s in config_stems)}",
        f"- **Prompts:** {len(prompts)} (source: `{prompt_source}`)",
        f"- **Total trials:** {total_trials}",
        "",
        "## Pre-registered prompts (verbatim)",
        "",
    ]
    for i, p in enumerate(prompts, 1):
        L.append(f"{i}. {p}")
    L += ["", "---", ""]

    L += ["## Metric (a) — biography-content rate (Judge A)", "",
          "Rate of responses scored 1 by the biography-content judge.", ""]
    L += _rate_table(records, metric_key="judge_biography_content",
                     binary=True, config_order=config_stems)
    L += ["", "## Metric (b) — refusal-marker rate (regex ∪ Judge B)", "",
          ("Rate of responses scored 1 by EITHER the regex stage or "
           "(if no regex hit) the LLM-fallback refusal judge."), ""]
    L += _rate_table(records, metric_key="judge_refusal_marker",
                     binary=True, config_order=config_stems)
    L += [""]
    L += _refusal_source_table(records, config_stems)
    L += ["## Metric (c) — empty-reply rate (mechanical)", "",
          "Rate of `response_length_chars == 0` (whitespace-only counts).", ""]
    L += _rate_table(records, metric_key="empty_reply",
                     binary=True, config_order=config_stems)
    L += ["", "---", "",
          "## Illustrative responses (highest biography-rate divergence)", "",
          ("For each config: the 2–3 prompts where Anima vs Baseline "
           "biography-content rate differed most. Trial-0 replies shown for "
           "both architectures."), ""]
    for stem in config_stems:
        L.append(f"### `{stem}`")
        L.append("")
        L.extend(_illustrative_pairs(records, stem))
        L.append("")
    L += ["---", "",
          ("All raw records are in `raw_records.json`. Pre-registered "
           "statistical tests TO BE RUN by the analysis subagent against "
           "`docs/hypotheses/2026-05-13_self_disclosure_replication.md`.")]
    L += ["",
          "## Secondary analysis: interior/exterior gap-ratio (Anima only)",
          "",
          ("This is the derived field "
           "`gap_ratio = len(inner_monologue) / max(len(subject_reply), 1)` "
           "per Anima record. Records with empty subject_reply have "
           "gap_ratio = null and are excluded from per-cell statistics. "
           "See `docs/hypotheses/2026-05-13_self_disclosure_replication.md` "
           "(Pre-registered secondary analyses) for predictions."),
          ""]
    L += _gap_ratio_table(records, config_stems)
    return "\n".join(L)


# ---- main -----------------------------------------------------------------


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Replicated self-disclosure experiment. 5 configs × 2 "
            "architectures × 6 prompts × N trials, single-turn fresh "
            "subject per trial, two pre-registered judges + empty-reply "
            "metric. Pre-registration: "
            "docs/hypotheses/2026-05-13_self_disclosure_replication.md."
        )
    )
    parser.add_argument(
        "--provider", default="fake",
        choices=["fake", "openrouter", "anthropic", "openai"],
        help="LLM adapter (default `fake`, safe).",
    )
    default_out = (
        _ROOT / "verification" / "reports"
        / ("self_disclosure_replication_"
           + _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ"))
    )
    parser.add_argument(
        "--out", type=Path, default=default_out,
        help=("Output directory (default: verification/reports/"
              "self_disclosure_replication_<stamp>/)."),
    )
    parser.add_argument(
        "--n-trials", type=int, default=15,
        help="Trials per (config × architecture × prompt) cell. Default 15.",
    )
    parser.add_argument(
        "--configs", nargs="+", default=None,
        help=("Config YAML paths. Default: the 5 pre-registered presets "
              "(marcus, elena, jamie, elena_secure, marcus_warm)."),
    )
    parser.add_argument(
        "--concurrency", type=int, default=8,
        help="Max concurrent in-flight trials (default 8 per the pre-reg).",
    )
    parser.add_argument(
        "--seed", type=int, default=None,
        help=("Optional integer seed. Documented only; LLM adapters do not "
              "currently take a per-call RNG seed (temperature>0). Recorded "
              "in the envelope for reproducibility bookkeeping."),
    )
    parser.add_argument(
        "--verbose", action="store_true",
        help="Per-call progress to stderr.",
    )
    parser.add_argument(
        "--fast-model", default=None,
        help=("OpenRouter model slug for the SUBJECT adapter's fast tier. "
              "Only applied when --provider=openrouter. The judge adapter is "
              "deliberately pinned to the OpenRouterAdapter default "
              "(deepseek/deepseek-v4-flash) to keep judge methodology "
              "consistent across cross-model subject runs."),
    )
    parser.add_argument(
        "--strong-model", default=None,
        help=("OpenRouter model slug for the SUBJECT adapter's strong tier. "
              "Only applied when --provider=openrouter. If omitted, falls "
              "back to --fast-model (matches the existing same-model-for-"
              "both-tiers pattern). Judge adapter is unaffected."),
    )
    parser.add_argument(
        "--prompts-file", type=Path, default=None,
        help=("Optional path to a JSON file supplying the 6 probe prompts in "
              "place of the in-source DEFAULT_PROMPTS. Required shape: "
              "{\"prompts\": [<6 non-empty strings>], \"source\": "
              "\"<label>\"}. Pre-registered for the fresh-prompt "
              "confirmation in "
              "docs/hypotheses/2026-05-14_fresh_prompt_confirmation.md. "
              "Source label is recorded as `prompt_source` in the output "
              "envelope; default label when this flag is omitted is "
              "`discriminability_default_prompts`."),
    )
    return parser.parse_args(argv)


def _resolve_configs(args) -> list[tuple[str, Path]]:
    """Return list of (config_stem, path) in canonical pre-reg order."""
    if args.configs:
        out: list[tuple[str, Path]] = []
        for p_str in args.configs:
            p = Path(p_str)
            if not p.is_absolute():
                p = (_ROOT / p).resolve()
            out.append((p.stem, p))
        return out
    preset_dir = _ROOT / "anima" / "config" / "presets"
    return [(stem, preset_dir / f"{stem}.yaml") for stem in DEFAULT_CONFIG_STEMS]


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)

    def log(msg: str) -> None:
        print(f"[self_disclosure_replication] {msg}", file=sys.stderr, flush=True)

    def vlog(msg: str) -> None:
        if args.verbose:
            log(msg)

    # Resolve & validate configs.
    config_specs = _resolve_configs(args)
    for stem, path in config_specs:
        if not path.exists():
            log(f"FATAL: config not found: {path}")
            return 2

    # Resolve prompts: --prompts-file overrides the in-source default. The
    # JSON file must supply exactly 6 non-empty strings plus a source label.
    if args.prompts_file is not None:
        try:
            prompts, prompt_source = _load_prompts_file(args.prompts_file)
        except (FileNotFoundError, ValueError) as exc:
            log(f"FATAL: --prompts-file load failed: "
                f"{type(exc).__name__}: {exc}")
            return 2
    else:
        prompts = list(PROMPTS)
        prompt_source = DEFAULT_PROMPT_SOURCE

    out_dir: Path = args.out
    out_dir.mkdir(parents=True, exist_ok=True)

    run_stamp = (
        _dt.datetime.now(_dt.timezone.utc).replace(tzinfo=None)
        .isoformat(timespec="seconds") + "Z"
    )
    log(f"run_stamp={run_stamp}")
    log(f"provider={args.provider}")
    log(f"out_dir={out_dir}")
    log(f"n_trials={args.n_trials}")
    log(f"concurrency={args.concurrency}")
    log(f"configs={[s for s, _ in config_specs]}")
    log(f"prompt_source={prompt_source}")
    if args.prompts_file is not None:
        log(f"prompts_file={args.prompts_file}")
    if args.seed is not None:
        log(f"seed={args.seed} (documented; not forced into adapter state)")

    # Load configs.
    cfg_by_stem: dict[str, Any] = {}
    try:
        for stem, path in config_specs:
            cfg_by_stem[stem] = load_config(path)
    except Exception as exc:
        log(f"FATAL: failed to load configs: {type(exc).__name__}: {exc}")
        log(traceback.format_exc())
        return 3

    # Build adapters. Per pre-reg, judge LLMs are SEPARATE adapter instances
    # of the same provider; same tier, no special routing.
    #
    # Model selection (--fast-model / --strong-model) applies ONLY to the
    # subject adapter. The judge adapter is deliberately pinned to the
    # OpenRouterAdapter default so judge methodology stays consistent across
    # cross-model subject runs. Only the openrouter adapter accepts these
    # kwargs; other adapters (fake/anthropic/openai) would TypeError.
    subject_kwargs: dict[str, str] = {}
    if args.provider == "openrouter":
        if args.fast_model:
            subject_kwargs["fast_model"] = args.fast_model
        if args.strong_model:
            subject_kwargs["strong_model"] = args.strong_model
        elif args.fast_model:
            subject_kwargs["strong_model"] = args.fast_model
    subject_fast_model = subject_kwargs.get("fast_model", args.fast_model)
    subject_strong_model = subject_kwargs.get(
        "strong_model", args.strong_model or args.fast_model)
    subject_llm = make_adapter(args.provider, **subject_kwargs)
    judge_llm = make_adapter(args.provider)
    log(f"subject_adapter={type(subject_llm).__name__}")
    log(f"judge_adapter={type(judge_llm).__name__}")
    log(f"subject_fast_model={subject_fast_model}")
    log(f"subject_strong_model={subject_strong_model}")

    # Build trial keys: (config × architecture × prompt × trial).
    trial_keys: list[TrialKey] = []
    for stem, _path in config_specs:
        cfg = cfg_by_stem[stem]
        for arch in ("anima", "baseline"):
            for pi, ptext in enumerate(prompts):
                for ti in range(args.n_trials):
                    trial_keys.append(TrialKey(
                        config_stem=stem,
                        config_name=cfg.name,
                        architecture=arch,
                        prompt_index=pi,
                        prompt_text=ptext,
                        trial_index=ti,
                        subject_id=f"{arch}_{stem}",
                    ))
    total = len(trial_keys)
    expected = len(config_specs) * 2 * len(prompts) * args.n_trials
    assert total == expected, f"trial-key build mismatch: {total} != {expected}"
    log(f"total_trials={total} (expected={expected})")

    # Drive the async pipeline.
    try:
        records, capture_errors, judge_errors = asyncio.run(_run_all_trials(
            trial_keys=trial_keys,
            cfg_by_stem=cfg_by_stem,
            subject_llm=subject_llm,
            judge_llm=judge_llm,
            concurrency=args.concurrency,
            log=log if args.verbose else vlog,
            out_dir=out_dir,
            verbose=args.verbose,
        ))
    except Exception as exc:
        log(f"FATAL during trials: {type(exc).__name__}: {exc}")
        log(traceback.format_exc())
        return 4

    errors = capture_errors + judge_errors

    # Write raw records envelope.
    raw_path = out_dir / "raw_records.json"
    raw_payload = {
        "experiment": "self_disclosure_replication",
        "run_stamp": run_stamp,
        "provider": args.provider,
        "subject_fast_model": subject_fast_model,
        "subject_strong_model": subject_strong_model,
        "n_trials": args.n_trials,
        "configs": [{"stem": s, "path": str(p)} for s, p in config_specs],
        "prompts": list(prompts),
        "prompt_source": prompt_source,
        "prompts_file": str(args.prompts_file) if args.prompts_file else None,
        "seed": args.seed,
        "concurrency": args.concurrency,
        "records": records,
        "errors": errors,
    }
    raw_path.write_text(json.dumps(raw_payload, indent=2, ensure_ascii=False))
    log(f"wrote {raw_path} ({raw_path.stat().st_size} bytes, "
        f"{len(records)} records)")

    # Write markdown report.
    report = _render_report(
        run_stamp=run_stamp, provider=args.provider,
        n_trials=args.n_trials,
        config_stems=[s for s, _ in config_specs],
        total_trials=total,
        records=records,
        prompts=prompts,
        prompt_source=prompt_source,
    )
    report_path = out_dir / "report.md"
    report_path.write_text(report)
    log(f"wrote {report_path} ({report_path.stat().st_size} bytes)")

    if errors:
        log(f"FATAL_NONFATAL: {len(capture_errors)} trials failed during "
            f"capture (and {len(judge_errors)} during judge); "
            f"artifacts written with surviving records.")
        return 5

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
