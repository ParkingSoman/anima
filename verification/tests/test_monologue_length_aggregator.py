"""Tests for the 2026-05-16 monologue-length aggregator."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

_SCRIPT_PATH = (
    Path(__file__).resolve().parents[1]
    / "scripts"
    / "2026-05-16_monologue_length_aggregator.py"
)


def _load_aggregator_module():
    spec = importlib.util.spec_from_file_location("agg_mod", _SCRIPT_PATH)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


AGG = _load_aggregator_module()


# ---------------------------------------------------------------------------
# Unit tests
# ---------------------------------------------------------------------------


def test_composite_points_by_cell_known_pair():
    """Worked example from the spec."""
    label_to_cell = {"A": "short", "B": "variable", "C": "long"}
    ranking_by_label = {"A": 2, "B": 1, "C": 3}
    out = AGG.compute_composite_points(label_to_cell, ranking_by_label)
    assert out == {"short": 2, "variable": 3, "long": 1}


def test_composite_points_swept_permutations():
    """Cover all six rank permutations."""
    cells = ("variable", "short", "long")
    label_to_cell = {"A": cells[0], "B": cells[1], "C": cells[2]}
    perms = [
        ({"A": 1, "B": 2, "C": 3}, {"variable": 3, "short": 2, "long": 1}),
        ({"A": 1, "B": 3, "C": 2}, {"variable": 3, "short": 1, "long": 2}),
        ({"A": 2, "B": 1, "C": 3}, {"variable": 2, "short": 3, "long": 1}),
        ({"A": 2, "B": 3, "C": 1}, {"variable": 2, "short": 1, "long": 3}),
        ({"A": 3, "B": 1, "C": 2}, {"variable": 1, "short": 3, "long": 2}),
        ({"A": 3, "B": 2, "C": 1}, {"variable": 1, "short": 2, "long": 3}),
    ]
    for rbl, expected in perms:
        assert AGG.compute_composite_points(label_to_cell, rbl) == expected


def test_validate_record_rejects_repeated_rank():
    with pytest.raises(ValueError, match="permutation"):
        AGG._validate_record(
            {"A": 1, "B": 1, "C": 2},
            {"A": "short", "B": "variable", "C": "long"},
        )


def test_validate_record_rejects_missing_cell():
    with pytest.raises(ValueError, match="label_to_cell values"):
        AGG._validate_record(
            {"A": 1, "B": 2, "C": 3},
            {"A": "short", "B": "short", "C": "long"},
        )


# ---------------------------------------------------------------------------
# Pre-flight integration: rankings/mapping uuid-set divergence
# ---------------------------------------------------------------------------


def _write_jsonl(path: Path, rows):
    with path.open("w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")


def test_preflight_diverging_uuid_sets(tmp_path):
    """If rankings and mapping have different group_uuid sets, raise."""
    blinded = tmp_path / "blinded"
    blinded.mkdir()

    # Build a complete set of stub files for all (model=mistral, criteria),
    # then deliberately break ONE pair's uuid set.
    prompts_path = tmp_path / "prompts.json"
    prompts_path.write_text(json.dumps(["p0", "p1", "p2", "p3", "p4", "p5", "p6", "p7"]))

    def _good_rows(uuids, criterion, persona):
        rrows = [
            {"group_uuid": u, "ranking": {"A": 1, "B": 2, "C": 3}, "rationale": "x"}
            for u in uuids
        ]
        mrows = [
            {
                "group_uuid": u,
                "persona": persona,
                "prompt_index": i % 8,
                "trial_index": i,
                "model": "mistral",
                "criterion": criterion,
                "label_to_cell": {"A": "variable", "B": "short", "C": "long"},
            }
            for i, u in enumerate(uuids)
        ]
        return rrows, mrows

    for crit in AGG.MARCUS_CRITERIA:
        rrows, mrows = _good_rows([f"u-{crit}-{i}" for i in range(2)], crit, "marcus")
        _write_jsonl(blinded / f"rankings_mistral_{crit}.jsonl", rrows)
        _write_jsonl(blinded / f"mapping_mistral_{crit}.jsonl", mrows)
    for crit in AGG.JAMIE_CRITERIA:
        rrows, mrows = _good_rows([f"u-{crit}-{i}" for i in range(2)], crit, "jamie")
        _write_jsonl(blinded / f"rankings_mistral_{crit}.jsonl", rrows)
        _write_jsonl(blinded / f"mapping_mistral_{crit}.jsonl", mrows)

    # Break one pair: drop a uuid from the rankings file.
    rrows_path = blinded / "rankings_mistral_warmth.jsonl"
    keep_lines = rrows_path.read_text().splitlines()[:1]
    rrows_path.write_text("\n".join(keep_lines) + "\n")

    with pytest.raises(ValueError, match="group_uuid sets diverge"):
        AGG.build_records_for_model(
            model="mistral",
            blinded_dir=blinded,
            prompts=json.loads(prompts_path.read_text()),
            timestamp_iso="2026-05-16T00:00:00Z",
        )


# ---------------------------------------------------------------------------
# Per-record schema completeness
# ---------------------------------------------------------------------------

_EXPECTED_KEYS = frozenset(
    {
        "persona",
        "prompt_index",
        "prompt_text",
        "trial_index",
        "criterion",
        "label_to_cell",
        "ranking_by_label",
        "composite_points_by_cell",
        "judge_model",
        "judge_seed",
        "timestamp_iso",
        "pre_reg_doc_sha",
    }
)


def _build_synthetic_blinded(tmp_path: Path, n_groups_per_crit: int = 3):
    """Make a small but complete blinded dir for one model."""
    blinded = tmp_path / "blinded"
    blinded.mkdir()
    for crit in AGG.MARCUS_CRITERIA:
        rrows = [
            {
                "group_uuid": f"m-{crit}-{i}",
                "ranking": {"A": 1, "B": 2, "C": 3},
                "rationale": "stub",
            }
            for i in range(n_groups_per_crit)
        ]
        mrows = [
            {
                "group_uuid": f"m-{crit}-{i}",
                "persona": "marcus",
                "prompt_index": i % 8,
                "trial_index": i,
                "model": "mistral",
                "criterion": crit,
                "label_to_cell": {"A": "variable", "B": "short", "C": "long"},
            }
            for i in range(n_groups_per_crit)
        ]
        _write_jsonl(blinded / f"rankings_mistral_{crit}.jsonl", rrows)
        _write_jsonl(blinded / f"mapping_mistral_{crit}.jsonl", mrows)
    for crit in AGG.JAMIE_CRITERIA:
        rrows = [
            {
                "group_uuid": f"j-{crit}-{i}",
                "ranking": {"A": 2, "B": 1, "C": 3},
                "rationale": "stub",
            }
            for i in range(n_groups_per_crit)
        ]
        mrows = [
            {
                "group_uuid": f"j-{crit}-{i}",
                "persona": "jamie",
                "prompt_index": i % 8,
                "trial_index": i,
                "model": "mistral",
                "criterion": crit,
                "label_to_cell": {"A": "short", "B": "variable", "C": "long"},
            }
            for i in range(n_groups_per_crit)
        ]
        _write_jsonl(blinded / f"rankings_mistral_{crit}.jsonl", rrows)
        _write_jsonl(blinded / f"mapping_mistral_{crit}.jsonl", mrows)
    return blinded


def test_per_record_schema_complete(tmp_path):
    blinded = _build_synthetic_blinded(tmp_path, n_groups_per_crit=3)
    prompts = ["p0", "p1", "p2", "p3", "p4", "p5", "p6", "p7"]
    records = AGG.build_records_for_model(
        model="mistral",
        blinded_dir=blinded,
        prompts=prompts,
        timestamp_iso="2026-05-16T00:00:00Z",
    )
    assert records, "no records produced"
    for r in records:
        assert set(r.keys()) == _EXPECTED_KEYS, f"keys mismatch: {set(r.keys())}"
        assert r["judge_model"] == "claude-agent-blinded"
        assert r["judge_seed"] == 42
        assert r["pre_reg_doc_sha"] == AGG.PRE_REG_DOC_SHA
        assert r["persona"] in {"marcus", "jamie"}
        assert r["criterion"] in AGG.ALL_CRITERIA
        # composite points sum to 6 (3+2+1) per record.
        assert sum(r["composite_points_by_cell"].values()) == 6
        assert set(r["composite_points_by_cell"]) == {"variable", "short", "long"}
        assert r["prompt_text"] == prompts[r["prompt_index"]]


# ---------------------------------------------------------------------------
# 4 criteria × N groups → 4N records per persona aggregation
# ---------------------------------------------------------------------------


def test_per_persona_aggregation_count(tmp_path):
    n = 5
    blinded = _build_synthetic_blinded(tmp_path, n_groups_per_crit=n)
    prompts = ["p0", "p1", "p2", "p3", "p4", "p5", "p6", "p7"]
    records = AGG.build_records_for_model(
        model="mistral",
        blinded_dir=blinded,
        prompts=prompts,
        timestamp_iso="2026-05-16T00:00:00Z",
    )
    marcus = [r for r in records if r["persona"] == "marcus"]
    jamie = [r for r in records if r["persona"] == "jamie"]
    assert len(marcus) == 4 * n
    assert len(jamie) == 4 * n
    # Each persona's records cover exactly its 4 criteria.
    assert {r["criterion"] for r in marcus} == set(AGG.MARCUS_CRITERIA)
    assert {r["criterion"] for r in jamie} == set(AGG.JAMIE_CRITERIA)
