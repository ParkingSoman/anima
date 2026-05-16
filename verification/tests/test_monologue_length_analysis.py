"""Unit tests for the monologue-length-directive analysis script.

The script lives at
``verification/scripts/2026-05-16_monologue_length_analysis.py``. The
filename starts with a digit, so we load it via ``importlib.util``
(matching the test_monologue_length_judging.py pattern).

Tests cover (per the task spec):
  - loading + filtering ``_judge_error`` records
  - composite computation: 4 criterion records -> composite sums (4-12)
  - Holm-Bonferroni adjustment math (canonical example)
  - bootstrap CI is seeded (same seed -> same CI)
  - cross-model aggregation: 0/3, 1/3, 2/3, 3/3 -> correct verdict
  - missing-model graceful degradation
  - data is mocked; scipy / numpy are real
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pytest


_ROOT = Path(__file__).resolve().parents[2]
_SCRIPT_PATH = (
    _ROOT / "verification" / "scripts"
    / "2026-05-16_monologue_length_analysis.py"
)


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "monologue_length_analysis_under_test", _SCRIPT_PATH,
    )
    mod = importlib.util.module_from_spec(spec)
    # Register so dataclass introspection works on Python 3.13.
    sys.modules["monologue_length_analysis_under_test"] = mod
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def mla():
    return _load_module()


# ---- helpers ------------------------------------------------------------


def _judged_record(
    *,
    persona: str,
    prompt_index: int,
    trial_index: int,
    criterion: str,
    composite_points_by_cell: dict[str, int],
    pre_reg_doc_sha: str = "sha-aaa",
    judge_error: bool = False,
) -> dict:
    rec = {
        "persona": persona,
        "prompt_index": prompt_index,
        "prompt_text": "p",
        "trial_index": trial_index,
        "criterion": criterion,
        "label_to_cell": {"A": "variable", "B": "short", "C": "long"},
        "ranking_by_label": {"A": 1, "B": 2, "C": 3},
        "composite_points_by_cell": composite_points_by_cell,
        "judge_model": "claude-sonnet-4-6",
        "judge_response_raw": "A:1\nB:2\nC:3",
        "judge_seed": 1,
        "timestamp_iso": "2026-05-16T00:00:00Z",
        "pre_reg_doc_sha": pre_reg_doc_sha,
    }
    if judge_error:
        rec["_judge_error"] = True
        rec["judge_error"] = "parse failure"
        rec["composite_points_by_cell"] = None
        rec["ranking_by_label"] = None
    return rec


def _write_jsonl(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as fh:
        for r in records:
            fh.write(json.dumps(r) + "\n")


def _full_marcus_trial(
    pi: int, ti: int,
    variable_pts: int = 3, short_pts: int = 2, long_pts: int = 1,
) -> list[dict]:
    """4 criteria for one Marcus trial, each contributing the same per-cell
    points -> composite per cell = 4 * pts."""
    out = []
    for crit in (
        "intellectualization-as-defense",
        "isolation-of-affect",
        "emotional-inhibition",
        "avoidant-deflection",
    ):
        out.append(_judged_record(
            persona="marcus", prompt_index=pi, trial_index=ti,
            criterion=crit,
            composite_points_by_cell={
                "variable": variable_pts,
                "short": short_pts,
                "long": long_pts,
            },
        ))
    return out


def _full_jamie_trial(
    pi: int, ti: int,
    variable_pts: int = 3, short_pts: int = 2, long_pts: int = 1,
) -> list[dict]:
    out = []
    for crit in (
        "warmth", "social-attunement",
        "humor-playfulness", "emotional-openness",
    ):
        out.append(_judged_record(
            persona="jamie", prompt_index=pi, trial_index=ti,
            criterion=crit,
            composite_points_by_cell={
                "variable": variable_pts,
                "short": short_pts,
                "long": long_pts,
            },
        ))
    return out


# ---- 1) loading + filtering _judge_error --------------------------------


def test_load_judged_records_filters_judge_error(mla, tmp_path):
    p = tmp_path / "judged.jsonl"
    recs = [
        _judged_record(
            persona="marcus", prompt_index=0, trial_index=0,
            criterion="intellectualization-as-defense",
            composite_points_by_cell={"variable": 3, "short": 2, "long": 1},
        ),
        _judged_record(
            persona="marcus", prompt_index=0, trial_index=0,
            criterion="isolation-of-affect",
            composite_points_by_cell={"variable": 3, "short": 2, "long": 1},
            judge_error=True,
        ),
        _judged_record(
            persona="marcus", prompt_index=0, trial_index=1,
            criterion="emotional-inhibition",
            composite_points_by_cell={"variable": 2, "short": 3, "long": 1},
        ),
    ]
    _write_jsonl(p, recs)
    kept, n_err = mla._load_judged_records(p, log=lambda m: None)
    assert n_err == 1
    assert len(kept) == 2
    assert all(not r.get("_judge_error") for r in kept)


def test_load_judged_records_missing_file_returns_empty(mla, tmp_path):
    p = tmp_path / "absent.jsonl"
    kept, n_err = mla._load_judged_records(p, log=lambda m: None)
    assert kept == []
    assert n_err == 0


def test_load_judged_records_skips_malformed_json(mla, tmp_path):
    p = tmp_path / "judged.jsonl"
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w") as fh:
        fh.write('{"valid": true, "_judge_error": false, ' +
                 '"persona": "x", "prompt_index": 0, "trial_index": 0, ' +
                 '"criterion": "c", "composite_points_by_cell": {}}\n')
        fh.write("not json at all\n")
    logs: list[str] = []
    kept, n_err = mla._load_judged_records(p, log=logs.append)
    assert len(kept) == 1
    assert any("malformed JSON" in m for m in logs)


# ---- 2) composite computation ------------------------------------------


def test_build_composites_marcus_4_criteria(mla):
    """4 marcus criteria, each giving (var=3, short=2, long=1) -> per-cell
    composites 12, 8, 4."""
    records = _full_marcus_trial(pi=0, ti=0,
                                  variable_pts=3, short_pts=2, long_pts=1)
    comps, skipped = mla._build_composites(records, model="m", log=lambda x: None)
    assert skipped == []
    assert len(comps) == 1
    cc = comps[("marcus", 0, 0)]
    assert cc.composites["variable"] == 12
    assert cc.composites["short"] == 8
    assert cc.composites["long"] == 4
    # range 4..12 enforcement
    assert all(4 <= v <= 12 for v in cc.composites.values())


def test_build_composites_jamie_4_criteria_full_range(mla):
    records = _full_jamie_trial(pi=1, ti=2,
                                 variable_pts=1, short_pts=2, long_pts=3)
    comps, skipped = mla._build_composites(records, model="m", log=lambda x: None)
    assert skipped == []
    cc = comps[("jamie", 1, 2)]
    assert cc.composites == {"variable": 4, "short": 8, "long": 12}


def test_build_composites_skips_trial_missing_one_criterion(mla):
    """Marcus trial with only 3 of 4 criteria -> trial skipped."""
    records = _full_marcus_trial(0, 0)[:3]
    logs: list[str] = []
    comps, skipped = mla._build_composites(records, model="m", log=logs.append)
    assert comps == {}
    assert skipped == [("marcus", 0, 0, "m")]
    assert any("criteria mismatch" in m for m in logs)


def test_build_composites_skips_trial_with_extra_criterion(mla):
    """Marcus + an irrelevant 5th criterion -> mismatched expected set ->
    trial skipped."""
    records = _full_marcus_trial(0, 0)
    records.append(_judged_record(
        persona="marcus", prompt_index=0, trial_index=0,
        criterion="not-a-real-marcus-criterion",
        composite_points_by_cell={"variable": 3, "short": 2, "long": 1},
    ))
    comps, skipped = mla._build_composites(records, model="m", log=lambda x: None)
    assert comps == {}
    assert skipped == [("marcus", 0, 0, "m")]


def test_build_composites_handles_multiple_trials(mla):
    records = []
    records.extend(_full_marcus_trial(0, 0, 3, 2, 1))
    records.extend(_full_marcus_trial(1, 0, 2, 3, 1))
    records.extend(_full_jamie_trial(0, 0, 1, 2, 3))
    comps, skipped = mla._build_composites(records, model="m", log=lambda x: None)
    assert skipped == []
    assert len(comps) == 3
    assert comps[("marcus", 0, 0)].composites == {"variable": 12, "short": 8, "long": 4}
    assert comps[("marcus", 1, 0)].composites == {"variable": 8, "short": 12, "long": 4}
    assert comps[("jamie", 0, 0)].composites == {"variable": 4, "short": 8, "long": 12}


# ---- 3) Holm-Bonferroni ------------------------------------------------


def test_holm_bonferroni_canonical_example(mla):
    """Canonical Holm-Bonferroni at alpha=0.05 with m=4:
        adjusted alphas at ranks 1..4: 0.0125, 0.01667, 0.025, 0.05.
    p = [0.001, 0.01, 0.04, 0.005]
    sorted ascending: [0.001 (orig 0), 0.005 (orig 3), 0.01 (orig 1), 0.04 (orig 2)]
    Step-down compares:
      p=0.001 < 0.05/4=0.0125 -> sig
      p=0.005 < 0.05/3=0.01667 -> sig
      p=0.01  < 0.05/2=0.025 -> sig
      p=0.04  < 0.05/1=0.05 -> sig
    All four significant.
    """
    p = [0.001, 0.01, 0.04, 0.005]
    out = mla._holm_bonferroni(p, alpha=0.05)
    # Indexed by original position.
    by_idx = {t[0]: t for t in out}
    # Adjusted alphas:
    assert by_idx[0][2] == pytest.approx(0.0125)  # rank 1
    assert by_idx[3][2] == pytest.approx(0.05 / 3)  # rank 2
    assert by_idx[1][2] == pytest.approx(0.025)  # rank 3
    assert by_idx[2][2] == pytest.approx(0.05)  # rank 4
    assert all(t[3] for t in out)  # all significant


def test_holm_bonferroni_stops_at_first_nonsig(mla):
    """If the smallest p fails its tight alpha, ALL are non-significant
    (standard step-down)."""
    p = [0.02, 0.001, 0.001, 0.001]
    # sorted: 0.001 (idx 1), 0.001 (idx 2), 0.001 (idx 3), 0.02 (idx 0)
    # idx 0 (p=0.02) at rank 4 -> alpha=0.05; would be sig alone, but
    # the rank-4 p>previous rank's alpha can still trigger fail-cascade
    # depending on internal sort order of ties. Use unambiguous test:
    p2 = [0.01, 0.02, 0.03, 0.04]  # only smallest p is 0.01
    # ranks: rank1: p=0.01 < 0.0125 sig; rank2: p=0.02 < 0.01667? NO
    # -> stop; all later non-sig.
    out = mla._holm_bonferroni(p2, alpha=0.05)
    by_idx = {t[0]: t for t in out}
    assert by_idx[0][3] is True   # p=0.01 < 0.0125
    assert by_idx[1][3] is False  # p=0.02 NOT < 0.05/3
    assert by_idx[2][3] is False
    assert by_idx[3][3] is False


def test_holm_bonferroni_all_fail(mla):
    p = [0.1, 0.1, 0.1, 0.1]
    out = mla._holm_bonferroni(p, alpha=0.05)
    assert all(not t[3] for t in out)


def test_holm_bonferroni_handles_nan(mla):
    """NaN p (no data) -> never significant; cascades the step-down."""
    p = [0.001, float("nan"), 0.001, 0.001]
    out = mla._holm_bonferroni(p, alpha=0.05)
    by_idx = {t[0]: t for t in out}
    # idx 1 (NaN) will get sorted last by Python; once we hit NaN,
    # is_significant cascades to False. Some earlier ranks might still
    # be significant if NaN sorts last.
    # The key behavior: NaN must NEVER be marked significant.
    assert by_idx[1][3] is False


# ---- 4) bootstrap CI seeded --------------------------------------------


def test_bootstrap_ci_same_seed_same_result(mla):
    """Same seed -> same CI to floating-point equality."""
    diffs = np.array([0.5, 1.0, 1.5, 0.0, 2.0, -0.5, 1.0, 0.5, 1.5, 1.0])
    lo1, hi1 = mla._bootstrap_mean_ci(diffs, n_iterations=2000, seed=42)
    lo2, hi2 = mla._bootstrap_mean_ci(diffs, n_iterations=2000, seed=42)
    assert lo1 == lo2
    assert hi1 == hi2


def test_bootstrap_ci_different_seed_different_result(mla):
    diffs = np.array([0.5, 1.0, 1.5, 0.0, 2.0, -0.5, 1.0, 0.5, 1.5, 1.0])
    lo1, hi1 = mla._bootstrap_mean_ci(diffs, n_iterations=2000, seed=42)
    lo2, hi2 = mla._bootstrap_mean_ci(diffs, n_iterations=2000, seed=43)
    assert (lo1, hi1) != (lo2, hi2)


def test_bootstrap_ci_empty_returns_nan(mla):
    import math
    lo, hi = mla._bootstrap_mean_ci(
        np.array([], dtype=np.float64), n_iterations=100, seed=42,
    )
    assert math.isnan(lo) and math.isnan(hi)


def test_bootstrap_ci_brackets_the_mean(mla):
    """For symmetric data the CI should bracket the sample mean."""
    rng = np.random.default_rng(0)
    diffs = rng.normal(loc=1.0, scale=0.5, size=200)
    lo, hi = mla._bootstrap_mean_ci(diffs, n_iterations=5000, seed=42)
    assert lo < diffs.mean() < hi


def test_stable_bootstrap_seed_is_deterministic(mla):
    a = mla._stable_bootstrap_seed(42, "deepseek", "H1a")
    b = mla._stable_bootstrap_seed(42, "deepseek", "H1a")
    assert a == b
    c = mla._stable_bootstrap_seed(42, "deepseek", "H1b")
    assert a != c


# ---- 5) cross-model aggregation ----------------------------------------


def _decisions_with_support(labels: list[str], supported_models_per_label: dict[str, list[str]]):
    """Build a per_model_decisions dict where for each (model, label),
    'supported' is True iff model is in supported_models_per_label[label].
    """
    all_models = set()
    for ms in supported_models_per_label.values():
        all_models.update(ms)
    # Ensure we always have at least models referenced.
    all_models.update({"deepseek", "mistral", "qwen"})
    out: dict[str, dict[str, dict]] = {m: {} for m in all_models}
    for lbl in labels:
        supp = supported_models_per_label.get(lbl, [])
        for m in all_models:
            out[m][lbl] = {
                "n_pairs": 100,  # nonzero
                "mean_diff": 0.7 if m in supp else 0.1,
                "t_stat": 4.0 if m in supp else 0.5,
                "p_value": 0.001 if m in supp else 0.3,
                "holm_adjusted_alpha": 0.0125,
                "holm_significant": (m in supp),
                "ci95_low": 0.3 if m in supp else -0.1,
                "ci95_high": 1.1 if m in supp else 0.4,
                "passes_effect_floor": (m in supp),
                "supported": (m in supp),
                "outcome_class": "supported" if m in supp else "floor-failure-null",
            }
    return out


def test_aggregate_3_of_3_green(mla):
    labels = [c[0] for c in mla.PRIMARY_CONTRASTS]
    decisions = _decisions_with_support(labels, {
        labels[0]: ["deepseek", "mistral", "qwen"],
        labels[1]: ["deepseek", "mistral", "qwen"],
        labels[2]: ["deepseek", "mistral", "qwen"],
        labels[3]: ["deepseek", "mistral", "qwen"],
    })
    cm = mla._aggregate_across_models(decisions)
    for lbl in labels:
        assert cm[lbl]["status"] == "green"
        assert cm[lbl]["n_supported"] == 3
    status, _ = mla._h1_overall(cm)
    assert status == "SUPPORTED"


def test_aggregate_2_of_3_green(mla):
    labels = [c[0] for c in mla.PRIMARY_CONTRASTS]
    decisions = _decisions_with_support(labels, {
        labels[0]: ["deepseek", "mistral"],
        labels[1]: ["deepseek", "mistral"],
        labels[2]: ["deepseek", "mistral"],
        labels[3]: ["deepseek", "mistral"],
    })
    cm = mla._aggregate_across_models(decisions)
    for lbl in labels:
        assert cm[lbl]["status"] == "green"
        assert cm[lbl]["n_supported"] == 2
    status, _ = mla._h1_overall(cm)
    assert status == "SUPPORTED"


def test_aggregate_1_of_3_mixed(mla):
    labels = [c[0] for c in mla.PRIMARY_CONTRASTS]
    decisions = _decisions_with_support(labels, {
        labels[0]: ["deepseek"],
        labels[1]: ["deepseek"],
        labels[2]: ["deepseek"],
        labels[3]: ["deepseek"],
    })
    cm = mla._aggregate_across_models(decisions)
    for lbl in labels:
        assert cm[lbl]["status"] == "mixed"
        assert cm[lbl]["n_supported"] == 1
    status, _ = mla._h1_overall(cm)
    assert status == "PARTIALLY-SUPPORTED"


def test_aggregate_0_of_3_falsified(mla):
    labels = [c[0] for c in mla.PRIMARY_CONTRASTS]
    decisions = _decisions_with_support(labels, {
        labels[0]: [],
        labels[1]: [],
        labels[2]: [],
        labels[3]: [],
    })
    cm = mla._aggregate_across_models(decisions)
    for lbl in labels:
        assert cm[lbl]["status"] == "falsified"
        assert cm[lbl]["n_supported"] == 0
    status, _ = mla._h1_overall(cm)
    assert status == "FALSIFIED"


def test_aggregate_partial_h1(mla):
    """3 of 4 contrasts green, 1 mixed -> H1 partially supported."""
    labels = [c[0] for c in mla.PRIMARY_CONTRASTS]
    decisions = _decisions_with_support(labels, {
        labels[0]: ["deepseek", "mistral"],
        labels[1]: ["deepseek", "mistral"],
        labels[2]: ["deepseek", "mistral"],
        labels[3]: ["deepseek"],  # only 1
    })
    cm = mla._aggregate_across_models(decisions)
    assert cm[labels[3]]["status"] == "mixed"
    status, _ = mla._h1_overall(cm)
    assert status == "PARTIALLY-SUPPORTED"


# ---- 6) missing-model graceful degradation ----------------------------


def test_main_proceeds_with_2_of_3_models(mla, tmp_path):
    """Drop one model file; main() should still produce a verdict."""
    in_dir = tmp_path / "reports"
    in_dir.mkdir(parents=True, exist_ok=True)
    out_json = tmp_path / "verdict.json"

    # Build minimal data for 2 of 3 models. We need enough trials
    # per persona for a t-test (>=2 pairs).
    def _model_records():
        recs = []
        # Marcus, 8 trials: variable=12, short=4, long=4 -> diffs all +8
        for ti in range(8):
            recs.extend(_full_marcus_trial(0, ti, 3, 1, 1))
        # Jamie, 8 trials: variable=12, short=4, long=4 -> diffs all +8
        for ti in range(8):
            recs.extend(_full_jamie_trial(0, ti, 3, 1, 1))
        return recs

    _write_jsonl(in_dir / "2026-05-16_monologue_length_primary_deepseek_judged.jsonl",
                 _model_records())
    _write_jsonl(in_dir / "2026-05-16_monologue_length_primary_mistral_judged.jsonl",
                 _model_records())
    # qwen is intentionally missing.

    rc = mla.main([
        "--source", "primary",
        "--input-dir", str(in_dir),
        "--output", str(out_json),
        "--bootstrap-iterations", "200",
        "--seed", "42",
    ])
    assert rc == 0
    envelope = json.loads(out_json.read_text())
    assert envelope["models_present"] == ["deepseek", "mistral"]
    assert envelope["models_missing"] == ["qwen"]
    # H1 should still get computed.
    assert envelope["h1_overall"]["status"] in {
        "SUPPORTED", "PARTIALLY-SUPPORTED", "FALSIFIED",
    }


def test_main_fatal_when_all_models_missing(mla, tmp_path):
    in_dir = tmp_path / "reports"
    in_dir.mkdir(parents=True, exist_ok=True)
    out_json = tmp_path / "verdict.json"
    rc = mla.main([
        "--source", "primary",
        "--input-dir", str(in_dir),
        "--output", str(out_json),
        "--bootstrap-iterations", "100",
    ])
    assert rc == 2


# ---- 7) H2 effect-size asymmetry ---------------------------------------


def test_h2_supported_when_jamie_long_is_clearly_largest(mla, tmp_path):
    """Synthesize differences where jamie-long >> other contrasts so
    bootstrap CIs don't overlap."""
    rng = np.random.default_rng(0)

    def _mk_result(label, persona, fixed, mean):
        diffs = list(rng.normal(loc=mean, scale=0.2, size=80))
        arr = np.array(diffs, dtype=np.float64)
        return mla.ContrastResult(
            label=label, persona=persona, fixed_cell=fixed,
            model="deepseek", n_pairs=len(diffs),
            mean_diff=float(np.mean(arr)),
            t_stat=10.0, p_value=1e-12,
            ci_low=float(np.mean(arr) - 0.1),
            ci_high=float(np.mean(arr) + 0.1),
            differences=diffs,
        )

    results = [
        _mk_result("H1a:variable_marcus_vs_short_marcus", "marcus", "short", 0.6),
        _mk_result("H1b:variable_marcus_vs_long_marcus", "marcus", "long", 0.5),
        _mk_result("H1c:variable_jamie_vs_short_jamie", "jamie", "short", 0.7),
        _mk_result("H1d:variable_jamie_vs_long_jamie", "jamie", "long", 3.0),
    ]
    per_model_results = {"deepseek": results}
    h2 = mla._analyze_h2(
        per_model_results, bootstrap_iterations=500, seed=42,
    )
    assert h2["status"] == "SUPPORTED"
    assert h2["target_is_point_largest"] is True
    assert h2["ci_no_overlap_all_others"] is True


def test_h2_falsified_when_not_largest(mla):
    rng = np.random.default_rng(0)

    def _mk_result(label, mean):
        diffs = list(rng.normal(loc=mean, scale=0.2, size=80))
        arr = np.array(diffs, dtype=np.float64)
        return mla.ContrastResult(
            label=label, persona="x", fixed_cell="y",
            model="deepseek", n_pairs=len(diffs),
            mean_diff=float(np.mean(arr)),
            t_stat=5.0, p_value=1e-6,
            ci_low=float(np.mean(arr) - 0.1),
            ci_high=float(np.mean(arr) + 0.1),
            differences=diffs,
        )

    results = [
        _mk_result("H1a:variable_marcus_vs_short_marcus", 3.0),
        _mk_result("H1b:variable_marcus_vs_long_marcus", 0.5),
        _mk_result("H1c:variable_jamie_vs_short_jamie", 0.5),
        _mk_result("H1d:variable_jamie_vs_long_jamie", 1.0),
    ]
    h2 = mla._analyze_h2(
        {"deepseek": results}, bootstrap_iterations=200, seed=42,
    )
    assert h2["status"] == "FALSIFIED-NOT-LARGEST"


# ---- 8) ContrastResult / paired_ttest sanity ---------------------------


def test_paired_ttest_zero_variance_zero_mean(mla):
    arr = np.array([0.0, 0.0, 0.0, 0.0])
    t, p, df = mla._paired_ttest(arr)
    assert t == 0.0
    assert p == 1.0


def test_paired_ttest_zero_variance_nonzero_mean(mla):
    arr = np.array([1.0, 1.0, 1.0, 1.0])
    t, p, df = mla._paired_ttest(arr)
    import math as _m
    assert _m.isinf(t)
    assert p == 0.0


def test_paired_ttest_basic(mla):
    """Real scipy paired test on a non-trivial sample."""
    rng = np.random.default_rng(0)
    arr = rng.normal(loc=0.8, scale=0.5, size=50)
    t, p, df = mla._paired_ttest(arr)
    assert df == 49
    assert p < 0.001  # well-powered against mu=0
    assert t > 0


# ---- 9) outcome classification ----------------------------------------


def test_classify_supported(mla):
    r = mla.ContrastResult(
        label="x", persona="m", fixed_cell="s", model="d",
        n_pairs=10, mean_diff=0.7, t_stat=3.0, p_value=0.001,
        ci_low=0.4, ci_high=1.0, differences=[],
    )
    assert mla._classify_contrast_outcome(r, holm_sig=True) == "supported"


def test_classify_wrong_direction(mla):
    r = mla.ContrastResult(
        label="x", persona="m", fixed_cell="s", model="d",
        n_pairs=10, mean_diff=-0.8, t_stat=-3.0, p_value=0.001,
        ci_low=-1.1, ci_high=-0.5, differences=[],
    )
    assert mla._classify_contrast_outcome(r, holm_sig=True) == "wrong-direction"


def test_classify_floor_failure(mla):
    r = mla.ContrastResult(
        label="x", persona="m", fixed_cell="s", model="d",
        n_pairs=10, mean_diff=0.2, t_stat=2.0, p_value=0.04,
        ci_low=-0.05, ci_high=0.45, differences=[],
    )
    assert mla._classify_contrast_outcome(r, holm_sig=False) == "floor-failure-null"


def test_classify_underpowered(mla):
    r = mla.ContrastResult(
        label="x", persona="m", fixed_cell="s", model="d",
        n_pairs=10, mean_diff=0.7, t_stat=1.5, p_value=0.08,
        ci_low=-0.05, ci_high=1.45, differences=[],
    )
    assert mla._classify_contrast_outcome(r, holm_sig=False) == "underpowered-inconclusive"


# ---- 10) end-to-end small fixture --------------------------------------


def test_end_to_end_small(mla, tmp_path):
    """Build a synthetic 3-model judged corpus, run main(), check that
    the JSON envelope is well-formed and the markdown file is created.
    """
    in_dir = tmp_path / "reports"
    in_dir.mkdir(parents=True, exist_ok=True)
    out_json = tmp_path / "verdict.json"
    out_md = tmp_path / "verdict.md"

    # Each model: marcus 12 trials with var=12, short=4, long=4 -> diffs +8
    # and jamie 12 trials with var=12, short=4, long=4 -> diffs +8.
    for m in ("deepseek", "mistral", "qwen"):
        recs = []
        for pi in range(3):
            for ti in range(4):
                recs.extend(_full_marcus_trial(pi, ti, 3, 1, 1))
                recs.extend(_full_jamie_trial(pi, ti, 3, 1, 1))
        _write_jsonl(
            in_dir / f"2026-05-16_monologue_length_primary_{m}_judged.jsonl",
            recs,
        )

    rc = mla.main([
        "--source", "primary",
        "--input-dir", str(in_dir),
        "--output", str(out_json),
        "--bootstrap-iterations", "200",
        "--seed", "42",
    ])
    assert rc == 0
    assert out_json.exists()
    md_path = out_json.with_suffix(".md")
    assert md_path.exists()
    env = json.loads(out_json.read_text())
    assert sorted(env["models_present"]) == ["deepseek", "mistral", "qwen"]
    assert env["bootstrap_iterations"] == 200
    assert env["random_seed"] == 42
    assert "h1_overall" in env
    assert "h2" in env
    # Should be supported on this perfect-signal synthetic data.
    assert env["h1_overall"]["status"] == "SUPPORTED"


# ---- 11) Improvement coverage ------------------------------------------


def _no_data_decision(label: str) -> dict:
    """Build a per-(model, label) decision dict representing 'no data'
    for that (model, contrast) pair: n_pairs == 0."""
    import math as _m
    return {
        "n_pairs": 0,
        "mean_diff": _m.nan,
        "t_stat": _m.nan,
        "p_value": _m.nan,
        "holm_adjusted_alpha": 0.0125,
        "holm_significant": False,
        "ci95_low": _m.nan,
        "ci95_high": _m.nan,
        "passes_effect_floor": False,
        "supported": False,
        "outcome_class": "no-data",
    }


def test_h1_no_data_when_all_contrasts_no_data(mla):
    """Improvement 1: when EVERY contrast across all models has zero
    data, H1 must return NO-DATA (or INDETERMINATE), distinct from
    FALSIFIED. Absence of evidence is not evidence of absence."""
    labels = [c[0] for c in mla.PRIMARY_CONTRASTS]
    decisions = {
        m: {lbl: _no_data_decision(lbl) for lbl in labels}
        for m in ("deepseek", "mistral", "qwen")
    }
    cm = mla._aggregate_across_models(decisions)
    for lbl in labels:
        assert cm[lbl]["status"] == "no-data"
        assert cm[lbl]["n_models_with_data"] == 0
    status, rationale = mla._h1_overall(cm)
    assert status in {"NO-DATA", "INDETERMINATE"}
    assert status != "FALSIFIED"
    # Rationale must surface the "absence of evidence" distinction.
    assert (
        "absence of evidence" in rationale.lower()
        or "cannot be adjudicated" in rationale.lower()
        or "indeterminate" in rationale.lower()
    )


def test_h1_falsified_requires_at_least_one_falsified_contrast(mla):
    """Improvement 1 (corollary): FALSIFIED requires at least one
    contrast in 'falsified' state. A mix of 'no-data' and 'falsified'
    is still FALSIFIED, but pure 'no-data' is not."""
    labels = [c[0] for c in mla.PRIMARY_CONTRASTS]
    decisions = _decisions_with_support(labels, {lbl: [] for lbl in labels})
    cm = mla._aggregate_across_models(decisions)
    # All four are 'falsified' here (n_pairs=100, supported=False).
    for lbl in labels:
        assert cm[lbl]["status"] == "falsified"
    status, _ = mla._h1_overall(cm)
    assert status == "FALSIFIED"


def test_classify_wrong_direction_underpowered(mla):
    """Improvement 2: a strong negative point estimate without
    significance must be classified as wrong-direction-underpowered, NOT
    'ambiguous'. The directional signal must be visible."""
    r = mla.ContrastResult(
        label="x", persona="m", fixed_cell="s", model="d",
        n_pairs=10, mean_diff=-0.7, t_stat=-1.4, p_value=0.18,
        ci_low=-1.5, ci_high=0.1, differences=[],
    )
    outcome = mla._classify_contrast_outcome(r, holm_sig=False)
    assert outcome == "wrong-direction-underpowered"


def test_classify_wrong_direction_underpowered_at_floor(mla):
    """Boundary: mean_diff = -EFFECT_SIZE_FLOOR exactly, not significant.
    The boundary <= is inclusive (wrong-direction with sig is also
    inclusive at the floor)."""
    r = mla.ContrastResult(
        label="x", persona="m", fixed_cell="s", model="d",
        n_pairs=10, mean_diff=-mla.EFFECT_SIZE_FLOOR, t_stat=-1.0,
        p_value=0.3, ci_low=-1.0, ci_high=0.1, differences=[],
    )
    outcome = mla._classify_contrast_outcome(r, holm_sig=False)
    assert outcome == "wrong-direction-underpowered"


def test_markdown_models_missing_line_lists_missing_model(mla, tmp_path):
    """Improvement 3: markdown must explicitly list missing models
    (per pre-reg §10 no-silent-drop)."""
    in_dir = tmp_path / "reports"
    in_dir.mkdir(parents=True, exist_ok=True)
    out_json = tmp_path / "verdict.json"

    def _model_records():
        recs = []
        for ti in range(8):
            recs.extend(_full_marcus_trial(0, ti, 3, 1, 1))
        for ti in range(8):
            recs.extend(_full_jamie_trial(0, ti, 3, 1, 1))
        return recs

    _write_jsonl(in_dir / "2026-05-16_monologue_length_primary_deepseek_judged.jsonl",
                 _model_records())
    _write_jsonl(in_dir / "2026-05-16_monologue_length_primary_mistral_judged.jsonl",
                 _model_records())
    # qwen intentionally missing.

    rc = mla.main([
        "--source", "primary",
        "--input-dir", str(in_dir),
        "--output", str(out_json),
        "--bootstrap-iterations", "200",
        "--seed", "42",
    ])
    assert rc == 0
    md_text = out_json.with_suffix(".md").read_text()
    assert "Models missing:" in md_text
    assert "qwen" in md_text.split("Models missing:")[1].splitlines()[0]


def test_markdown_models_missing_line_none_when_all_present(mla, tmp_path):
    """Improvement 3: when no models are missing, the line must say
    '(none)' explicitly (not omit the line)."""
    in_dir = tmp_path / "reports"
    in_dir.mkdir(parents=True, exist_ok=True)
    out_json = tmp_path / "verdict.json"

    def _model_records():
        recs = []
        for ti in range(8):
            recs.extend(_full_marcus_trial(0, ti, 3, 1, 1))
        for ti in range(8):
            recs.extend(_full_jamie_trial(0, ti, 3, 1, 1))
        return recs

    for m in ("deepseek", "mistral", "qwen"):
        _write_jsonl(
            in_dir / f"2026-05-16_monologue_length_primary_{m}_judged.jsonl",
            _model_records(),
        )

    rc = mla.main([
        "--source", "primary",
        "--input-dir", str(in_dir),
        "--output", str(out_json),
        "--bootstrap-iterations", "200",
        "--seed", "42",
    ])
    assert rc == 0
    md_text = out_json.with_suffix(".md").read_text()
    assert "Models missing:" in md_text
    assert "(none)" in md_text.split("Models missing:")[1].splitlines()[0]


def test_envelope_contains_input_file_shas(mla, tmp_path):
    """Improvement 4: envelope must record SHA-256 per loaded input
    file so reviewers can verify the same bytes were analyzed."""
    import hashlib

    in_dir = tmp_path / "reports"
    in_dir.mkdir(parents=True, exist_ok=True)
    out_json = tmp_path / "verdict.json"

    def _model_records():
        recs = []
        for ti in range(8):
            recs.extend(_full_marcus_trial(0, ti, 3, 1, 1))
        for ti in range(8):
            recs.extend(_full_jamie_trial(0, ti, 3, 1, 1))
        return recs

    expected_shas = {}
    for m in ("deepseek", "mistral"):
        path = in_dir / f"2026-05-16_monologue_length_primary_{m}_judged.jsonl"
        _write_jsonl(path, _model_records())
        expected_shas[m] = hashlib.sha256(path.read_bytes()).hexdigest()
    # qwen missing on purpose.

    rc = mla.main([
        "--source", "primary",
        "--input-dir", str(in_dir),
        "--output", str(out_json),
        "--bootstrap-iterations", "200",
        "--seed", "42",
    ])
    assert rc == 0
    env = json.loads(out_json.read_text())
    assert "input_file_shas" in env
    shas = env["input_file_shas"]
    assert set(shas.keys()) == {"deepseek", "mistral"}
    for m, expected in expected_shas.items():
        assert shas[m] == expected
        # SHA-256 hex digests are 64 chars.
        assert len(shas[m]) == 64


def test_envelope_contains_reproducibility_block(mla, tmp_path):
    """Improvement 5: envelope must record stats library versions for
    reproducibility (scipy, numpy, python)."""
    in_dir = tmp_path / "reports"
    in_dir.mkdir(parents=True, exist_ok=True)
    out_json = tmp_path / "verdict.json"

    def _model_records():
        recs = []
        for ti in range(8):
            recs.extend(_full_marcus_trial(0, ti, 3, 1, 1))
        for ti in range(8):
            recs.extend(_full_jamie_trial(0, ti, 3, 1, 1))
        return recs

    _write_jsonl(in_dir / "2026-05-16_monologue_length_primary_deepseek_judged.jsonl",
                 _model_records())

    rc = mla.main([
        "--source", "primary",
        "--input-dir", str(in_dir),
        "--output", str(out_json),
        "--bootstrap-iterations", "200",
        "--seed", "42",
    ])
    assert rc == 0
    env = json.loads(out_json.read_text())
    assert "reproducibility" in env
    repro = env["reproducibility"]
    assert "python_version" in repro
    assert "numpy_version" in repro
    assert "scipy_version" in repro
    assert "scipy_available" in repro
    # numpy is a hard dependency so its version must be a non-empty str.
    assert isinstance(repro["numpy_version"], str) and repro["numpy_version"]
    # python version must include the interpreter version string.
    assert isinstance(repro["python_version"], str) and repro["python_version"]
    # scipy_available reflects the actual import result; bool either way.
    assert isinstance(repro["scipy_available"], bool)
    # If scipy_available True, version is set; if False, version is None.
    if repro["scipy_available"]:
        assert isinstance(repro["scipy_version"], str)
    else:
        assert repro["scipy_version"] is None


def test_load_judged_records_skips_non_dict_records(mla, tmp_path):
    """Minor cleanup: a top-level JSON array/string/number is not a
    record; the loader must skip it with a WARNING."""
    p = tmp_path / "judged.jsonl"
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w") as fh:
        # valid record
        fh.write(json.dumps({
            "persona": "marcus", "prompt_index": 0, "trial_index": 0,
            "criterion": "intellectualization-as-defense",
            "composite_points_by_cell": {"variable": 3, "short": 2, "long": 1},
        }) + "\n")
        # non-dict records:
        fh.write("[1, 2, 3]\n")
        fh.write('"a top-level string"\n')
        fh.write("42\n")
    logs: list[str] = []
    kept, n_err = mla._load_judged_records(p, log=logs.append)
    assert len(kept) == 1
    # At least 3 warnings for non-dict records.
    non_dict_warnings = [m for m in logs if "non-dict record" in m]
    assert len(non_dict_warnings) == 3
