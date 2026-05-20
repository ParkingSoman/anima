"""Monologue-length-directive experiment — capture stage (Phase 1 retrospective).

Pre-registration: ``docs/hypotheses/2026-05-16_monologue_length_pre_registration.md``.

For each (persona ∈ {marcus, jamie}, cell ∈ {variable, short, long}, prompt ∈
8 selected, trial ∈ 0..N-1), instantiate a FRESH Anima with the
:class:`verification.probes.monologue_length_directives.LengthControlledInnerMonologue`
swapped into the turn loop, run a single turn against the prompt, and emit a
JSONL record to the output file. No judging happens here — judging is a
separate stage downstream against the captured records.

CLI:

    .venv/bin/python -m verification.scripts.2026-05-16_monologue_length_experiment \\
        --source {primary|fresh} \\
        --model {deepseek|mistral|qwen} \\
        --output-dir verification/reports/ \\
        [--trials 20] [--cells variable,short,long] [--dry-run] [--seed 42] \\
        [--provider {openrouter|fake}]

Output: ``verification/reports/2026-05-16_monologue_length_{source}_{model}.jsonl``.
Each line is one captured trial — see ``SUCCESS_RECORD_SCHEMA_KEYS`` for the
schema of a successful trial, and ``ERROR_RECORD_SCHEMA_KEYS`` for the schema
of a per-trial error record (those records carry ``"_error": true`` so they
can be filtered downstream).

Discipline:
    - ``anima_v1/`` is NEVER modified. The wrapper interposes at construction
      time via ``anima._monologue = LengthControlledInnerMonologue(...)``.
    - The pre-reg doc is NEVER modified. Its file SHA is recorded in every
      record so a single check at analysis time confirms the run is bound to
      the locked spec.
    - The 8 prompts per source come verbatim from the pre-reg ``§3`` / ``§4``
      via on-disk JSON files; the script refuses to run if those files are
      missing or contain != 8 entries.
    - Trials are randomized for order-independence with a fixed seed
      (default 42); ``trial_index`` is preserved per (persona, cell, prompt)
      so downstream pairing still works.
    - Records are appended one-line-at-a-time AND the script implements
      genuine resume: on startup, if the output file exists, it is parsed and
      every successfully-completed (persona, cell, prompt_index, trial_index)
      tuple is removed from the run plan. Previously-errored tuples are
      re-attempted. A kill-9'd run picks up where it left off. If the output
      file is malformed, the script REFUSES to start (it will not silently
      overwrite); the user must remove or repair the file.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import os
import random
import sys
import traceback
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from anima_v1.core import Anima
from anima_v1.config import load_config
from anima_v1.llm import make_adapter
from verification.probes.monologue_length_directives import (
    LengthControlledInnerMonologue,
    MonologueCell,
)


# ---- locked model dispatch (matches §2 of the pre-reg) ------------------

MODEL_SLUGS: dict[str, str] = {
    "deepseek": "deepseek/deepseek-v4-flash",
    "mistral": "mistralai/mistral-small-3.2-24b-instruct",
    "qwen": "qwen/qwen3-30b-a3b",
}


# ---- per-cell token caps (mirror the probe; we record what the probe used)

CELL_MAX_TOKENS: dict[str, int] = {
    "variable": 1500,
    "short": 120,
    "long": 720,
}


# ---- locked anima_v1 integrity ------------------------------------------
#
# This is the SHA-256 of `git ls-files anima_v1` content, computed at the
# pre-reg lock. If `anima_v1/` has been modified in the working tree, the
# experiment refuses to run. The reference value is recorded here so the
# script is self-contained; if a legitimate update to `anima_v1` ever
# happens, the reference must be bumped INTENTIONALLY in this file (and
# the pre-reg invalidation discipline of §13.5 reconsidered).
EXPECTED_ANIMA_V1_SHA: str = "4970ecad10999f7c9852801aaf831e2365659560d820da934cb8547288a9ab95"


# ---- output record schemas ----------------------------------------------
#
# Two record shapes can appear on disk:
#   1. Successful trial — keys in SUCCESS_RECORD_SCHEMA_KEYS, no `_error` key.
#   2. Per-trial error — keys in ERROR_RECORD_SCHEMA_KEYS, `_error: true`.
#
# The error record carries enough identity (persona, cell, prompt_index,
# trial_index) for resume to recognize it AND for resume to re-attempt the
# tuple (we do not treat errored tuples as completed). Downstream analyzers
# filter `_error: true` records out before computing any aggregate stats.

SUCCESS_RECORD_SCHEMA_KEYS: tuple[str, ...] = (
    "cell",
    "persona",
    "prompt_index",
    "prompt_text",
    "trial_index",
    "model",
    "model_slug",
    "monologue_text",
    "monologue_sentence_count",
    "response_text",
    "response_sentence_count",
    "monologue_max_tokens",
    "monologue_actual_tokens",
    "timestamp_iso",
    "anima_v1_sha",
    "pre_reg_doc_sha",
)

ERROR_RECORD_SCHEMA_KEYS: tuple[str, ...] = (
    "_error",
    "persona",
    "cell",
    "prompt_index",
    "trial_index",
    "model",
    "model_slug",
    "exception_class",
    "exception_message",
    "timestamp_iso",
    "anima_v1_sha",
    "pre_reg_doc_sha",
)

# Backward-compat alias: existing tests and analysis code reference
# RECORD_SCHEMA_KEYS expecting the SUCCESS shape. Keep the name available.
RECORD_SCHEMA_KEYS: tuple[str, ...] = SUCCESS_RECORD_SCHEMA_KEYS


# ---- helpers -------------------------------------------------------------


def _compute_anima_v1_sha() -> str:
    """Hash all *.py files under ``anima_v1/`` in sorted path order.

    Matches the offline computation:
        find anima_v1 -type f -name '*.py' | sort | xargs shasum -a 256 |
        shasum -a 256
    Returned hex is lowercased.
    """
    root = _ROOT / "anima_v1"
    files = sorted(root.rglob("*.py"))
    if not files:
        raise RuntimeError(f"no .py files found under {root}")
    # Compose the same input that shasum's output-of-shasums would feed in.
    # We replicate the format `<hex>  <path>\n` per file.
    pieces: list[bytes] = []
    for f in files:
        rel = f.relative_to(_ROOT)
        h = hashlib.sha256(f.read_bytes()).hexdigest()
        pieces.append(f"{h}  {rel}\n".encode())
    return hashlib.sha256(b"".join(pieces)).hexdigest()


def _compute_file_sha(path: Path) -> str:
    """SHA-256 of a single file's bytes."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _sentence_count(text: str) -> int:
    """Cheap sentence count: count terminating punctuation runs.

    Not a full NLP tokenizer — for compliance-check use only, matches the
    §13 verification-check semantics ("approximate" sentence counting,
    not a paper-grade segmentation). Counts the number of times a
    sentence-ending punctuation cluster (one or more of `.`, `!`, `?`)
    is followed by whitespace OR end-of-string. Returns 0 for empty input.
    """
    if not text or not text.strip():
        return 0
    import re as _re
    # match a run of [.!?] followed by EOS or whitespace
    return len(_re.findall(r"[.!?]+(?=\s|$)", text.strip()))


def _load_prompts(source: str) -> tuple[list[str], Path]:
    """Load the 8 prompts for the given source ('primary' | 'fresh')."""
    if source == "primary":
        path = _ROOT / "verification" / "prompts" / "aai_2026-05-16.json"
    elif source == "fresh":
        path = _ROOT / "verification" / "prompts" / "mcadams_lsi_2026-05-16.json"
    else:
        raise ValueError(f"unknown source: {source!r}")
    if not path.exists():
        raise FileNotFoundError(f"prompt file not found: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError(
            f"{path}: expected top-level JSON array; got {type(payload).__name__}"
        )
    if len(payload) != 8:
        raise ValueError(
            f"{path}: expected exactly 8 prompts; got {len(payload)}"
        )
    for i, p in enumerate(payload):
        if not isinstance(p, str) or not p.strip():
            raise ValueError(
                f"{path}: prompt[{i}] must be a non-empty string; "
                f"got {type(p).__name__!r}: {p!r}"
            )
    return list(payload), path


def _persona_config_path(persona: str) -> Path:
    """Map persona name to its frozen YAML preset path."""
    if persona not in {"marcus", "jamie"}:
        raise ValueError(f"unknown persona: {persona!r}")
    return _ROOT / "anima_v1" / "config" / "presets" / f"{persona}.yaml"


def _build_anima(persona: str, cell: MonologueCell, llm) -> Anima:
    """Construct an Anima for the given persona with the length-controlled
    monologue subsystem swapped in.

    The swap happens AFTER ``Anima.__init__`` runs (which sets
    ``self._monologue = InnerMonologueSubsystem(self.llm)``); we replace
    that attribute with a ``LengthControlledInnerMonologue`` bound to the
    same llm and the requested cell. This leaves the rest of the turn
    loop (perception / appraisal / response) untouched, and never touches
    ``anima_v1/`` source.
    """
    cfg_path = _persona_config_path(persona)
    if not cfg_path.exists():
        raise FileNotFoundError(f"persona config not found: {cfg_path}")
    cfg = load_config(cfg_path)
    anima = Anima(cfg, llm=llm)
    anima._monologue = LengthControlledInnerMonologue(llm, cell=cell)
    return anima


# ---- a single trial ------------------------------------------------------


def _run_single_trial(*, persona: str, cell: MonologueCell, prompt_index: int,
                      prompt_text: str, trial_index: int, model: str,
                      model_slug: str, llm, anima_v1_sha: str,
                      pre_reg_doc_sha: str) -> dict[str, Any]:
    """Run one turn under one (persona, cell, prompt, trial) cell.

    Returns a fully-populated record matching ``SUCCESS_RECORD_SCHEMA_KEYS``.
    Raises on any unrecoverable error — the caller logs and continues.
    """
    anima = _build_anima(persona, cell, llm)
    reply, trace = anima.respond(prompt_text)
    monologue_text = trace.monologue or ""
    response_text = reply or ""

    usage = trace.usage or {}
    # The Anima trace.usage is the response generator's usage. We don't
    # have monologue-specific usage at this layer (anima_v1 doesn't expose
    # it on the trace). Record None — the cell config tells us the cap.
    record: dict[str, Any] = {
        "cell": cell,
        "persona": persona,
        "prompt_index": prompt_index,
        "prompt_text": prompt_text,
        "trial_index": trial_index,
        "model": model,
        "model_slug": model_slug,
        "monologue_text": monologue_text,
        "monologue_sentence_count": _sentence_count(monologue_text),
        "response_text": response_text,
        "response_sentence_count": _sentence_count(response_text),
        "monologue_max_tokens": CELL_MAX_TOKENS[cell],
        "monologue_actual_tokens": None,
        "timestamp_iso": _dt.datetime.now(_dt.timezone.utc)
            .replace(tzinfo=None).isoformat(timespec="seconds") + "Z",
        "anima_v1_sha": anima_v1_sha,
        "pre_reg_doc_sha": pre_reg_doc_sha,
    }
    # Sanity: every required key present.
    missing = [k for k in SUCCESS_RECORD_SCHEMA_KEYS if k not in record]
    if missing:
        raise RuntimeError(f"record missing keys: {missing}")
    return record


# ---- resume / existing-record handling ----------------------------------


class MalformedJsonlError(RuntimeError):
    """Raised when the existing output JSONL cannot be parsed.

    The script REFUSES to start in this case — silently overwriting or
    truncating a partial run's output would destroy hours of LLM calls.
    The user must remove or repair the file manually.
    """


def _is_error_record(rec: dict[str, Any]) -> bool:
    """Recognize the per-trial error record shape (carries ``_error: true``)."""
    return bool(rec.get("_error"))


def _load_existing_records(path: Path) -> tuple[set[tuple[str, str, int, int]], int, int]:
    """Parse the existing JSONL output and extract resume metadata.

    Returns:
        completed_tuples: set of (persona, cell, prompt_index, trial_index)
            for SUCCESSFUL records only. Errored tuples are NOT included
            (resume re-attempts them).
        n_success: number of successful records on disk.
        n_error: number of error records on disk.

    Raises:
        MalformedJsonlError: if any non-empty line fails to parse as JSON,
            or a record is missing required identity keys. The caller
            should refuse to start and surface this to the user.
    """
    completed: set[tuple[str, str, int, int]] = set()
    n_success = 0
    n_error = 0
    with path.open("r", encoding="utf-8") as fh:
        for lineno, raw in enumerate(fh, start=1):
            line = raw.strip()
            if not line:
                # tolerate empty trailing lines but flag mid-file blanks
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError as exc:
                raise MalformedJsonlError(
                    f"{path}:{lineno}: invalid JSON: {exc}. "
                    f"Refusing to start. Remove or repair this file manually."
                ) from exc
            if not isinstance(rec, dict):
                raise MalformedJsonlError(
                    f"{path}:{lineno}: expected JSON object; "
                    f"got {type(rec).__name__}. Refusing to start."
                )
            if _is_error_record(rec):
                # Validate identity keys are present on the error record so
                # we can confidently re-attempt the tuple.
                for k in ("persona", "cell", "prompt_index", "trial_index"):
                    if k not in rec:
                        raise MalformedJsonlError(
                            f"{path}:{lineno}: error record missing identity "
                            f"key {k!r}. Refusing to start."
                        )
                n_error += 1
                continue
            # Successful record: require identity keys, then mark completed.
            for k in ("persona", "cell", "prompt_index", "trial_index"):
                if k not in rec:
                    raise MalformedJsonlError(
                        f"{path}:{lineno}: success record missing identity "
                        f"key {k!r}. Refusing to start."
                    )
            key = (
                rec["persona"], rec["cell"],
                int(rec["prompt_index"]), int(rec["trial_index"]),
            )
            completed.add(key)
            n_success += 1
    return completed, n_success, n_error


def _iter_success_records(path: Path):
    """Yield only successful records from a JSONL file.

    Filter helper for downstream analyzers — skips ``_error: true`` records
    silently. Bad JSON still raises (caller decides).
    """
    with path.open("r", encoding="utf-8") as fh:
        for raw in fh:
            line = raw.strip()
            if not line:
                continue
            rec = json.loads(line)
            if isinstance(rec, dict) and not _is_error_record(rec):
                yield rec


# ---- CLI / main ---------------------------------------------------------


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Monologue-length-directive capture experiment "
            "(Phase 1 retrospective). Pre-registration: "
            "docs/hypotheses/2026-05-16_monologue_length_pre_registration.md."
        )
    )
    parser.add_argument(
        "--source", required=True, choices=["primary", "fresh"],
        help="primary = 8 AAI prompts; fresh = 8 McAdams LSI prompts.",
    )
    parser.add_argument(
        "--model", required=True, choices=sorted(MODEL_SLUGS),
        help="Anima model alias (resolves to a locked OpenRouter slug).",
    )
    parser.add_argument(
        "--output-dir", type=Path,
        default=_ROOT / "verification" / "reports",
        help="Directory where the JSONL output is written.",
    )
    parser.add_argument(
        "--trials", type=int, default=20,
        help="Trials per (persona, cell, prompt). Default 20 per pre-reg §2.",
    )
    parser.add_argument(
        "--cells", default="variable,short,long",
        help=("Comma-separated cells to run. Default 'variable,short,long' "
              "(all three). Subsetting is for debugging only — pre-reg "
              "requires all three for the verdict."),
    )
    parser.add_argument(
        "--personas", default="marcus,jamie",
        help=("Comma-separated personas to run. Default 'marcus,jamie' (the "
              "pre-reg full set). Subsetting is for debugging only."),
    )
    parser.add_argument(
        "--seed", type=int, default=42,
        help=("Integer seed for trial-order randomization (default 42). "
              "Recorded in the run envelope for reproducibility."),
    )
    parser.add_argument(
        "--provider", default="openrouter",
        choices=["openrouter", "fake"],
        help=("LLM adapter. Default 'openrouter' (the pre-reg subject "
              "provider). Use 'fake' for dry-mocked structural runs."),
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help=("Print the run plan + cost estimate and exit; make NO LLM "
              "calls. Useful for verifying CLI behavior before a real run."),
    )
    parser.add_argument(
        "--skip-integrity-check", action="store_true",
        help=("Skip the anima_v1 SHA integrity check (debugging only — "
              "production runs MUST keep the check on)."),
    )
    return parser.parse_args(argv)


def _build_run_plan(*, source: str, model: str, personas: list[str],
                    cells: list[MonologueCell], n_prompts: int,
                    trials: int, seed: int) -> list[dict[str, Any]]:
    """Enumerate every (persona, cell, prompt_index, trial_index) cell, then
    shuffle the order with the configured seed. ``trial_index`` is 0..N-1
    per (persona, cell, prompt_index) — independent of the shuffled
    execution order — so downstream pairing still works.
    """
    plan: list[dict[str, Any]] = []
    for persona in personas:
        for cell in cells:
            for pi in range(n_prompts):
                for ti in range(trials):
                    plan.append({
                        "persona": persona,
                        "cell": cell,
                        "prompt_index": pi,
                        "trial_index": ti,
                    })
    rng = random.Random(seed)
    rng.shuffle(plan)
    return plan


def _estimate_cost(*, n_calls: int) -> str:
    """Order-of-magnitude estimate. The Anima turn loop is 4 LLM calls
    (perception, appraisal, monologue, response). Per pre-reg §14 the
    primary run is ~28,800 Anima LLM calls across 3 models / 2 personas /
    8 prompts / 3 cells / 20 trials, costing ~$3 across DeepSeek + Mistral
    + Qwen. That works out to ~$0.0001 per Anima LLM call as an envelope.
    Multiply by 4 to get per-trial.
    """
    per_call_usd = 0.0001
    total_calls = n_calls * 4  # 4 LLM calls per Anima trial
    est_low = total_calls * per_call_usd * 0.5
    est_high = total_calls * per_call_usd * 2.0
    return f"~${est_low:.2f}–${est_high:.2f} (very rough, order-of-magnitude)"


def _make_adapter_for_model(provider: str, model_slug: str):
    """Build an LLM adapter pinned to the experiment's chosen model.

    Both fast and strong tiers point at the same OpenRouter slug, matching
    the project's cross-model replication convention (one model per run).
    """
    if provider == "openrouter":
        return make_adapter(
            "openrouter",
            fast_model=model_slug,
            strong_model=model_slug,
        )
    if provider == "fake":
        return make_adapter("fake")
    raise ValueError(f"unsupported provider: {provider!r}")


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)

    def log(msg: str) -> None:
        print(f"[mle] {msg}", file=sys.stderr, flush=True)

    cells_raw = [c.strip() for c in args.cells.split(",") if c.strip()]
    for c in cells_raw:
        if c not in CELL_MAX_TOKENS:
            log(f"FATAL: unknown cell {c!r}; expected one of "
                f"{sorted(CELL_MAX_TOKENS)}")
            return 2
    cells: list[MonologueCell] = cells_raw  # type: ignore[assignment]

    personas = [p.strip() for p in args.personas.split(",") if p.strip()]
    for p in personas:
        if p not in {"marcus", "jamie"}:
            log(f"FATAL: unknown persona {p!r}; expected 'marcus' or 'jamie'")
            return 2

    # -- pre-flight #1: prompts files exist and have 8 entries each.
    try:
        prompts, prompts_path = _load_prompts(args.source)
    except (FileNotFoundError, ValueError) as exc:
        log(f"FATAL: prompts load failed: {type(exc).__name__}: {exc}")
        return 2
    log(f"prompts: loaded {len(prompts)} from {prompts_path}")

    # -- pre-flight #2: pre-reg doc exists; record its SHA.
    pre_reg_path = (
        _ROOT / "docs" / "hypotheses"
        / "2026-05-16_monologue_length_pre_registration.md"
    )
    if not pre_reg_path.exists():
        log(f"FATAL: pre-reg doc not found: {pre_reg_path}")
        return 2
    pre_reg_sha = _compute_file_sha(pre_reg_path)
    log(f"pre_reg_doc_sha={pre_reg_sha}")

    # -- pre-flight #3: anima_v1 integrity. Refuse if SHA differs.
    anima_v1_sha = _compute_anima_v1_sha()
    log(f"anima_v1_sha={anima_v1_sha}")
    if args.skip_integrity_check:
        log("WARNING: --skip-integrity-check supplied; integrity NOT enforced")
    else:
        if anima_v1_sha != EXPECTED_ANIMA_V1_SHA:
            log(f"FATAL: anima_v1 SHA mismatch")
            log(f"  expected: {EXPECTED_ANIMA_V1_SHA}")
            log(f"  actual:   {anima_v1_sha}")
            log("Refusing to run. Either anima_v1 was modified (which "
                "invalidates the experiment per pre-reg §13.7), or "
                "EXPECTED_ANIMA_V1_SHA in this script needs an INTENTIONAL "
                "bump. Do not bypass without thought.")
            return 3

    model_slug = MODEL_SLUGS[args.model]
    log(f"model={args.model} ({model_slug})")
    log(f"source={args.source}")
    log(f"trials={args.trials}")
    log(f"personas={personas}")
    log(f"cells={cells}")
    log(f"seed={args.seed}")
    log(f"provider={args.provider}")

    plan = _build_run_plan(
        source=args.source,
        model=args.model,
        personas=personas,
        cells=cells,
        n_prompts=len(prompts),
        trials=args.trials,
        seed=args.seed,
    )
    full_plan_size = len(plan)
    n_llm_calls = full_plan_size * 4
    log(f"plan: {full_plan_size} trials = "
        f"{len(personas)} personas x {len(cells)} cells x "
        f"{len(prompts)} prompts x {args.trials} trials")
    log(f"expected_llm_calls={n_llm_calls} (4 per Anima trial)")
    log(f"cost_estimate={_estimate_cost(n_calls=full_plan_size)}")

    # Output path. One file per (source, model) per pre-reg.
    args.output_dir.mkdir(parents=True, exist_ok=True)
    out_path = (
        args.output_dir
        / f"2026-05-16_monologue_length_{args.source}_{args.model}.jsonl"
    )
    log(f"output={out_path}")

    if args.dry_run:
        log("DRY-RUN: skipping all LLM calls.")
        # Emit the first few plan entries for sanity.
        for i, p in enumerate(plan[:5]):
            log(f"  [{i}] {p}")
        if len(plan) > 5:
            log(f"  ... (+{len(plan) - 5} more)")
        return 0

    # -- resume: if the output file already exists, parse it and filter the
    # plan. Previously-completed (successful) tuples are skipped; previously-
    # errored tuples are re-attempted. Malformed JSONL → refuse to start.
    if out_path.exists():
        try:
            completed_tuples, n_existing_success, n_existing_error = (
                _load_existing_records(out_path)
            )
        except MalformedJsonlError as exc:
            log(f"FATAL: existing output file is malformed:")
            log(f"  {exc}")
            log("The script refuses to silently overwrite a partial run. "
                "Either delete the file or repair it manually, then re-run.")
            return 8
        before = len(plan)
        plan = [
            step for step in plan
            if (step["persona"], step["cell"],
                step["prompt_index"], step["trial_index"])
            not in completed_tuples
        ]
        skipped = before - len(plan)
        remaining = len(plan)
        log(f"resuming: {len(completed_tuples)}/{full_plan_size} already "
            f"complete, {remaining} remaining "
            f"(prior error records on disk: {n_existing_error}; "
            f"prior success records: {n_existing_success}; "
            f"plan entries skipped this run: {skipped})")
        if remaining == 0:
            log("already complete — nothing to do. Exiting 0.")
            return 0
    else:
        log("no existing output file — starting fresh.")

    # Build the LLM adapter.
    try:
        llm = _make_adapter_for_model(args.provider, model_slug)
    except Exception as exc:
        log(f"FATAL: adapter construction failed: {type(exc).__name__}: {exc}")
        log(traceback.format_exc())
        return 4
    log(f"adapter={type(llm).__name__}")

    # Run plan, append one JSONL record per trial. Open in append mode so
    # partial runs are preserved across kill-9; the resume logic above
    # ensures already-completed tuples aren't re-executed. Per-trial errors
    # are persisted to the JSONL as `_error: true` records so they survive
    # the run and can be inspected after the fact (observability rule).
    n_trials = len(plan)
    written = 0
    errors = 0
    with out_path.open("a", encoding="utf-8") as fh:
        for i, step in enumerate(plan):
            try:
                rec = _run_single_trial(
                    persona=step["persona"],
                    cell=step["cell"],
                    prompt_index=step["prompt_index"],
                    prompt_text=prompts[step["prompt_index"]],
                    trial_index=step["trial_index"],
                    model=args.model,
                    model_slug=model_slug,
                    llm=llm,
                    anima_v1_sha=anima_v1_sha,
                    pre_reg_doc_sha=pre_reg_sha,
                )
                fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
                fh.flush()
                os.fsync(fh.fileno())
                written += 1
                if written % 25 == 0 or written == n_trials:
                    log(f"  progress {written}/{n_trials}")
            except Exception as exc:  # noqa: BLE001
                errors += 1
                err_rec: dict[str, Any] = {
                    "_error": True,
                    "persona": step["persona"],
                    "cell": step["cell"],
                    "prompt_index": step["prompt_index"],
                    "trial_index": step["trial_index"],
                    "model": args.model,
                    "model_slug": model_slug,
                    "exception_class": type(exc).__name__,
                    "exception_message": str(exc),
                    "timestamp_iso": _dt.datetime.now(_dt.timezone.utc)
                        .replace(tzinfo=None).isoformat(timespec="seconds") + "Z",
                    "anima_v1_sha": anima_v1_sha,
                    "pre_reg_doc_sha": pre_reg_sha,
                }
                try:
                    fh.write(json.dumps(err_rec, ensure_ascii=False) + "\n")
                    fh.flush()
                    os.fsync(fh.fileno())
                except Exception as write_exc:  # noqa: BLE001
                    # If we can't even persist the error record, log it
                    # loudly but DO NOT crash — the run-level summary will
                    # still flag the discrepancy via exit code.
                    log(f"  CRITICAL: failed to persist error record: "
                        f"{type(write_exc).__name__}: {write_exc}")
                log(f"  TRIAL FAILED [{i}] persona={step['persona']} "
                    f"cell={step['cell']} prompt={step['prompt_index']} "
                    f"trial={step['trial_index']}: "
                    f"{type(exc).__name__}: {exc}")
                # Continue on per-trial failure so one bad call doesn't kill
                # a multi-hour run.
                continue

    # Final summary log line — always emitted, including on partial failure.
    total = written + errors
    success_rate = (written / total) if total > 0 else 0.0
    log(f"summary: written={written} errors={errors} total={total} "
        f"success_rate={success_rate:.3f}")
    log(f"done. wrote={written} errors={errors} -> {out_path}")
    # Post-run integrity recheck (catches "anima_v1 modified mid-run").
    if not args.skip_integrity_check:
        post_sha = _compute_anima_v1_sha()
        if post_sha != anima_v1_sha:
            log(f"FATAL: anima_v1 SHA changed mid-run: "
                f"pre={anima_v1_sha} post={post_sha}")
            return 5
    if errors == 0:
        return 0
    if written == 0:
        # Total failure: every attempted trial errored.
        return 7
    # Partial failure: some succeeded, some errored.
    return 6


if __name__ == "__main__":
    raise SystemExit(main())
