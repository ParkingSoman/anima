"""Aggregate blinded judging outputs into the judged JSONL format.

For each (model, criterion) pair we read:
  - verification/reports/blinded/rankings_{model}_{criterion}.jsonl
  - verification/reports/blinded/mapping_{model}_{criterion}.jsonl

We emit one combined judged JSONL per model:
  verification/reports/2026-05-16_monologue_length_primary_{model}_judged.jsonl
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List

MODELS = ("mistral", "deepseek", "qwen")
MARCUS_CRITERIA = (
    "intellectualization-as-defense",
    "isolation-of-affect",
    "emotional-inhibition",
    "avoidant-deflection",
)
JAMIE_CRITERIA = (
    "warmth",
    "social-attunement",
    "humor-playfulness",
    "emotional-openness",
)
ALL_CRITERIA = MARCUS_CRITERIA + JAMIE_CRITERIA

PRE_REG_DOC_SHA = "1496ff5cfcb16318a6a56d66e29b6cc91c90aeea7572ce6b4834cfdca9b710e8"
JUDGE_MODEL = "claude-agent-blinded"
JUDGE_SEED = 42

VALID_CELLS = frozenset({"variable", "short", "long"})
VALID_RANKS = frozenset({1, 2, 3})


def _load_jsonl(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"Required input not found: {path}")
    rows: List[Dict[str, Any]] = []
    with path.open() as f:
        for ln_no, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"Bad JSON in {path} line {ln_no}: {exc}") from exc
    return rows


def _index_by_uuid(rows: Iterable[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    for r in rows:
        uid = r["group_uuid"]
        if uid in out:
            raise ValueError(f"Duplicate group_uuid: {uid}")
        out[uid] = r
    return out


def compute_composite_points(
    label_to_cell: Dict[str, str], ranking_by_label: Dict[str, int]
) -> Dict[str, int]:
    """rank 1 -> 3 points, rank 2 -> 2 points, rank 3 -> 1 point."""
    rank_to_pts = {1: 3, 2: 2, 3: 1}
    out = {"variable": 0, "short": 0, "long": 0}
    for label, cell in label_to_cell.items():
        rank = ranking_by_label[label]
        out[cell] = rank_to_pts[rank]
    return out


def _validate_record(ranking_by_label: Dict[str, int], label_to_cell: Dict[str, str]) -> None:
    rl = sorted(ranking_by_label.values())
    if rl != [1, 2, 3]:
        raise ValueError(
            f"ranking_by_label must be a permutation of (1,2,3); got {ranking_by_label}"
        )
    cells = set(label_to_cell.values())
    if cells != VALID_CELLS:
        raise ValueError(
            f"label_to_cell values must be exactly {sorted(VALID_CELLS)}; got {label_to_cell}"
        )
    if set(ranking_by_label.keys()) != {"A", "B", "C"}:
        raise ValueError(
            f"ranking_by_label labels must be A/B/C; got {set(ranking_by_label.keys())}"
        )
    if set(label_to_cell.keys()) != {"A", "B", "C"}:
        raise ValueError(
            f"label_to_cell labels must be A/B/C; got {set(label_to_cell.keys())}"
        )


def load_prompts(prompt_path: Path) -> List[str]:
    with prompt_path.open() as f:
        prompts = json.load(f)
    if not isinstance(prompts, list) or not all(isinstance(p, str) for p in prompts):
        raise ValueError(f"Prompt file {prompt_path} must be a flat list of strings")
    return prompts


def build_records_for_model(
    model: str,
    blinded_dir: Path,
    prompts: List[str],
    timestamp_iso: str,
) -> List[Dict[str, Any]]:
    """Build the flat judged records for one model across all criteria."""
    records: List[Dict[str, Any]] = []
    for criterion in ALL_CRITERIA:
        rankings_path = blinded_dir / f"rankings_{model}_{criterion}.jsonl"
        mapping_path = blinded_dir / f"mapping_{model}_{criterion}.jsonl"
        rankings = _index_by_uuid(_load_jsonl(rankings_path))
        mapping = _index_by_uuid(_load_jsonl(mapping_path))

        # Pre-flight #1: identical group_uuid sets.
        if set(rankings) != set(mapping):
            missing_in_rank = set(mapping) - set(rankings)
            missing_in_map = set(rankings) - set(mapping)
            raise ValueError(
                f"group_uuid sets diverge for {model}/{criterion}: "
                f"in mapping but not rankings={sorted(missing_in_rank)[:5]}; "
                f"in rankings but not mapping={sorted(missing_in_map)[:5]}"
            )

        for uid, mrow in mapping.items():
            rrow = rankings[uid]
            ranking_by_label = {
                "A": int(rrow["ranking"]["A"]),
                "B": int(rrow["ranking"]["B"]),
                "C": int(rrow["ranking"]["C"]),
            }
            label_to_cell = {
                "A": mrow["label_to_cell"]["A"],
                "B": mrow["label_to_cell"]["B"],
                "C": mrow["label_to_cell"]["C"],
            }
            # Pre-flight #2: per-record validation.
            _validate_record(ranking_by_label, label_to_cell)

            prompt_index = int(mrow["prompt_index"])
            if not (0 <= prompt_index < len(prompts)):
                raise ValueError(
                    f"prompt_index out of range for {model}/{criterion} uuid={uid}: "
                    f"{prompt_index} not in [0,{len(prompts)})"
                )

            composite = compute_composite_points(label_to_cell, ranking_by_label)

            records.append(
                {
                    "persona": mrow["persona"],
                    "prompt_index": prompt_index,
                    "prompt_text": prompts[prompt_index],
                    "trial_index": int(mrow["trial_index"]),
                    "criterion": criterion,
                    "label_to_cell": label_to_cell,
                    "ranking_by_label": ranking_by_label,
                    "composite_points_by_cell": composite,
                    "judge_model": JUDGE_MODEL,
                    "judge_seed": JUDGE_SEED,
                    "timestamp_iso": timestamp_iso,
                    "pre_reg_doc_sha": PRE_REG_DOC_SHA,
                }
            )
    return records


def write_records(records: List[Dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as f:
        for rec in records:
            f.write(json.dumps(rec) + "\n")


def rank1_frequency_table(
    records: List[Dict[str, Any]],
) -> Dict[str, Dict[str, Dict[str, int]]]:
    """Per (persona, criterion, cell) -> count of rank-1 occurrences."""
    table: Dict[str, Dict[str, Dict[str, int]]] = defaultdict(
        lambda: defaultdict(lambda: Counter())
    )
    for rec in records:
        persona = rec["persona"]
        criterion = rec["criterion"]
        for cell, pts in rec["composite_points_by_cell"].items():
            if pts == 3:  # rank 1
                table[persona][criterion][cell] += 1
    # Convert to plain dicts for serialization / printing.
    return {p: {c: dict(cnt) for c, cnt in d.items()} for p, d in table.items()}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output-dir",
        default="verification/reports/",
        help="Directory to write judged JSONLs into.",
    )
    parser.add_argument(
        "--blinded-dir",
        default="verification/reports/blinded/",
        help="Directory containing rankings_*.jsonl and mapping_*.jsonl",
    )
    parser.add_argument(
        "--prompts-path",
        default="verification/prompts/aai_2026-05-16.json",
        help="Flat JSON list of prompt strings.",
    )
    args = parser.parse_args()

    blinded_dir = Path(args.blinded_dir)
    output_dir = Path(args.output_dir)
    prompts_path = Path(args.prompts_path)

    prompts = load_prompts(prompts_path)
    timestamp_iso = _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    expected_counts = {"mistral": 1280, "deepseek": 1272, "qwen": 1280}

    for model in MODELS:
        records = build_records_for_model(
            model=model,
            blinded_dir=blinded_dir,
            prompts=prompts,
            timestamp_iso=timestamp_iso,
        )
        out_path = output_dir / f"2026-05-16_monologue_length_primary_{model}_judged.jsonl"
        write_records(records, out_path)
        actual = len(records)
        expected = expected_counts[model]
        status = "OK" if actual == expected else "MISMATCH"
        print(f"[{status}] {model}: wrote {actual} records to {out_path} (expected {expected})")

        # Per-model rank-1 frequency tables.
        table = rank1_frequency_table(records)
        for persona in sorted(table):
            for criterion in sorted(table[persona]):
                cells = table[persona][criterion]
                total = sum(cells.values())
                parts = ", ".join(
                    f"{c}={cells.get(c, 0)}/{total}"
                    for c in ("variable", "short", "long")
                )
                print(f"  {model} {persona} {criterion}: {parts} rank-1")


if __name__ == "__main__":
    main()
