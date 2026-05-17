"""Monologue-length-directive experiment — blinding stage (pre-judging).

This script consumes the harness JSONL output and produces blinded inputs
for the independent judging agents. Each blinded record contains ONLY the
verbatim prompt and three response texts under randomized labels A/B/C.
No persona, no cell, no monologue, no model metadata, no prompt/trial
indices — the judging agents must be unable to infer experimental
identity from the blinded input.

The label permutation is deterministic from a SHA256-derived RNG keyed by
``(seed, persona, prompt_index, trial_index, criterion)`` so that the
post-judging aggregator can re-derive (or look up via the mapping file)
which label corresponds to which cell.

CLI::

    python verification/scripts/2026-05-16_monologue_length_blinding.py \
        --input verification/reports/2026-05-16_monologue_length_primary_mistral.jsonl \
        --model mistral \
        [--output-dir verification/reports/blinded/] \
        [--seed 42]

Outputs (per model, 8 criteria each):
  - blinded_{model}_{criterion}.jsonl  — judge input. Contains
    group_uuid, question, response_A, response_B, response_C only.
  - mapping_{model}_{criterion}.jsonl  — label_to_cell mapping for the
    aggregator. NEVER shown to judges.

Discipline:
  - Read-only on the harness JSONL.
  - Pre-flight accounting: n_successful == n_complete_groups * 3
    + n_orphaned, where n_orphaned is bounded above by 2 *
    n_error_records (each error record can orphan up to 2 partner
    cells). Violation -> exit 2.
  - ``_error`` records are skipped (and counted).
  - Groups with != 3 cells (variable/short/long) are skipped with a
    warning.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
import uuid
from pathlib import Path
from typing import Any


# ---- criteria -----------------------------------------------------------

# (criterion, persona) — order matches pre-registration.
CRITERIA: tuple[tuple[str, str], ...] = (
    # Marcus criteria
    ("intellectualization-as-defense", "marcus"),
    ("isolation-of-affect", "marcus"),
    ("emotional-inhibition", "marcus"),
    ("avoidant-deflection", "marcus"),
    # Jamie criteria
    ("warmth", "jamie"),
    ("social-attunement", "jamie"),
    ("humor-playfulness", "jamie"),
    ("emotional-openness", "jamie"),
)

EXPECTED_CELLS: frozenset[str] = frozenset({"variable", "short", "long"})


# ---- IO ----------------------------------------------------------------

def _load_input_records(path: Path) -> list[dict[str, Any]]:
    """Read the harness JSONL. Each line is one record."""
    if not path.exists():
        raise FileNotFoundError(f"input file not found: {path}")
    recs: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as fh:
        for ln_no, line in enumerate(fh, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                recs.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"{path}:{ln_no}: malformed JSON: {exc}"
                ) from exc
    return recs


# ---- grouping ---------------------------------------------------------

GroupKey = tuple[str, int, int]  # (persona, prompt_index, trial_index)


def group_records_for_persona(
    records: list[dict[str, Any]],
    persona: str,
    *,
    log=print,
) -> dict[GroupKey, dict[str, dict[str, Any]]]:
    """Filter ``records`` to ``persona``, drop ``_error``, group by
    (persona, prompt_index, trial_index). Returns map of group key to
    a {cell -> record} sub-map. Groups with != 3 cells are skipped.
    """
    by_group: dict[GroupKey, dict[str, dict[str, Any]]] = {}
    for rec in records:
        if rec.get("_error"):
            continue
        if rec.get("persona") != persona:
            continue
        prompt_index = rec.get("prompt_index")
        trial_index = rec.get("trial_index")
        cell = rec.get("cell")
        if prompt_index is None or trial_index is None or cell is None:
            log(
                f"WARNING: skipping record missing key "
                f"(prompt_index/trial_index/cell): keys={list(rec)}"
            )
            continue
        key: GroupKey = (persona, int(prompt_index), int(trial_index))
        cell_map = by_group.setdefault(key, {})
        if cell in cell_map:
            log(
                f"WARNING: duplicate cell {cell!r} in group {key}; "
                f"keeping FIRST occurrence"
            )
        else:
            cell_map[cell] = rec
    valid: dict[GroupKey, dict[str, dict[str, Any]]] = {}
    for key, cm in by_group.items():
        if set(cm.keys()) != EXPECTED_CELLS:
            log(
                f"WARNING: group {key} has cells {sorted(cm)} "
                f"(expected {sorted(EXPECTED_CELLS)}); SKIPPING"
            )
            continue
        valid[key] = cm
    return valid


# ---- randomization ----------------------------------------------------

def label_rng(
    persona: str,
    prompt_index: int,
    trial_index: int,
    criterion: str,
    seed: int,
) -> random.Random:
    """Return a fresh ``random.Random`` keyed by SHA256 of the group +
    criterion + seed. Spec: ``RNG(SHA256(f"{seed}|{persona}|{prompt_index}|"
    f"{trial_index}|{criterion}").digest())``.

    ``random.Random`` accepts arbitrary bytes via its constructor (it
    hashes them internally), so we pass the digest directly.
    """
    payload = f"{seed}|{persona}|{prompt_index}|{trial_index}|{criterion}"
    digest = hashlib.sha256(payload.encode("utf-8")).digest()
    return random.Random(digest)


def assign_labels(
    persona: str,
    prompt_index: int,
    trial_index: int,
    criterion: str,
    seed: int,
) -> dict[str, str]:
    """Return mapping ``{"A": cell, "B": cell, "C": cell}`` for the
    given group + criterion. Deterministic given seed.
    """
    rng = label_rng(persona, prompt_index, trial_index, criterion, seed)
    cells = ["variable", "short", "long"]
    rng.shuffle(cells)
    return {"A": cells[0], "B": cells[1], "C": cells[2]}


# ---- group uuid -------------------------------------------------------

def group_uuid(
    model: str,
    persona: str,
    prompt_index: int,
    trial_index: int,
    criterion: str,
) -> str:
    """Deterministic UUID5 over ``(model, persona, prompt_index,
    trial_index, criterion)``. Stable across runs."""
    name = f"{model}|{persona}|{prompt_index}|{trial_index}|{criterion}"
    return str(uuid.uuid5(uuid.NAMESPACE_URL, name))


# ---- writers ----------------------------------------------------------

def _write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for rec in records:
            fh.write(json.dumps(rec, ensure_ascii=False))
            fh.write("\n")


def build_blinded_for_criterion(
    *,
    groups: dict[GroupKey, dict[str, dict[str, Any]]],
    criterion: str,
    persona: str,
    model: str,
    seed: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Return (blinded_records, mapping_records) for one criterion.

    Sorted by (prompt_index, trial_index) for stable file ordering.
    """
    blinded: list[dict[str, Any]] = []
    mapping: list[dict[str, Any]] = []
    sorted_keys = sorted(groups.keys(), key=lambda k: (k[1], k[2]))
    for key in sorted_keys:
        _persona, prompt_index, trial_index = key
        cell_map = groups[key]
        labels = assign_labels(
            _persona, prompt_index, trial_index, criterion, seed
        )
        uid = group_uuid(model, _persona, prompt_index, trial_index, criterion)
        # All three records share the same prompt_text (same prompt_index).
        # Use the variable cell record as the canonical source for the
        # question — any cell would work.
        question = cell_map["variable"]["prompt_text"]
        blinded.append({
            "group_uuid": uid,
            "question": question,
            "response_A": cell_map[labels["A"]]["response_text"],
            "response_B": cell_map[labels["B"]]["response_text"],
            "response_C": cell_map[labels["C"]]["response_text"],
        })
        mapping.append({
            "group_uuid": uid,
            "persona": _persona,
            "prompt_index": prompt_index,
            "trial_index": trial_index,
            "model": model,
            "criterion": criterion,
            "label_to_cell": labels,
        })
    return blinded, mapping


# ---- CLI --------------------------------------------------------------

def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Blind harness JSONL into per-criterion judge inputs."
    )
    parser.add_argument("--input", type=Path, required=True,
                        help="Path to harness output JSONL.")
    parser.add_argument("--model", type=str, required=True,
                        help="Model name (e.g. mistral, deepseek).")
    parser.add_argument(
        "--output-dir", type=Path,
        default=Path("verification/reports/blinded/"),
        help="Output directory.",
    )
    parser.add_argument("--seed", type=int, default=42,
                        help="Base seed for the label permutation RNG.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    log = print

    records = _load_input_records(args.input)
    n_total = len(records)
    n_error = sum(1 for r in records if r.get("_error"))
    n_success = n_total - n_error
    log(
        f"loaded {n_total} records from {args.input} "
        f"({n_success} successful, {n_error} errored)"
    )

    # Pre-flight: count per-persona successful and error records.
    persona_counts: dict[str, int] = {}
    persona_errors: dict[str, int] = {}
    for rec in records:
        p = rec.get("persona")
        if p is None:
            continue
        if rec.get("_error"):
            persona_errors[p] = persona_errors.get(p, 0) + 1
        else:
            persona_counts[p] = persona_counts.get(p, 0) + 1
    log(f"per-persona successful record counts: {persona_counts}")
    if persona_errors:
        log(f"per-persona _error record counts: {persona_errors}")

    # Pre-build groups per persona (re-used across that persona's 4
    # criteria — grouping is criterion-agnostic).
    persona_groups: dict[str, dict[GroupKey, dict[str, dict[str, Any]]]] = {}
    for criterion, persona in CRITERIA:
        if persona in persona_groups:
            continue
        persona_groups[persona] = group_records_for_persona(
            records, persona, log=log
        )

    # Pre-flight accounting identity per persona:
    #   n_successful == n_complete_groups * 3 + n_orphaned
    # where n_orphaned is the count of successful records whose partner
    # cell had _error: true. We require n_orphaned <= 2 * n_error
    # (each error orphans at most 2 partners). When there are NO error
    # records, this reduces to: n_successful == n_complete_groups * 3.
    for persona, groups in persona_groups.items():
        n_recs_for_persona = persona_counts.get(persona, 0)
        n_errors_for_persona = persona_errors.get(persona, 0)
        in_complete = len(groups) * 3
        n_orphaned = n_recs_for_persona - in_complete
        if n_orphaned < 0:
            log(
                f"ERROR: persona {persona!r}: complete groups account "
                f"for {in_complete} records but only {n_recs_for_persona} "
                f"successful records seen — duplicate cells?"
            )
            return 2
        if n_orphaned > 2 * n_errors_for_persona:
            log(
                f"ERROR: persona {persona!r}: {n_orphaned} successful "
                f"records were orphaned by incomplete groups, but only "
                f"{n_errors_for_persona} _error record(s) present — "
                f"math does not add up. Expected groups: "
                f"{n_recs_for_persona // 3} (records / 3), got "
                f"{len(groups)}."
            )
            return 2
        log(
            f"persona {persona!r}: {len(groups)} valid groups "
            f"({in_complete} records in complete groups, "
            f"{n_orphaned} orphaned by {n_errors_for_persona} _error "
            f"record(s))"
        )

    n_files_written = 0
    for criterion, persona in CRITERIA:
        groups = persona_groups[persona]
        blinded, mapping = build_blinded_for_criterion(
            groups=groups,
            criterion=criterion,
            persona=persona,
            model=args.model,
            seed=args.seed,
        )
        blinded_path = (
            args.output_dir / f"blinded_{args.model}_{criterion}.jsonl"
        )
        mapping_path = (
            args.output_dir / f"mapping_{args.model}_{criterion}.jsonl"
        )
        _write_jsonl(blinded_path, blinded)
        _write_jsonl(mapping_path, mapping)
        log(
            f"  wrote {len(blinded)} records to "
            f"{blinded_path} (+ mapping)"
        )
        n_files_written += 2

    log(
        f"DONE: wrote {n_files_written} files "
        f"({n_files_written // 2} blinded + {n_files_written // 2} mapping) "
        f"to {args.output_dir}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
