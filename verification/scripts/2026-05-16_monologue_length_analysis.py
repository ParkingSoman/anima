"""Monologue-length-directive experiment — analysis stage.

Pre-registration: ``docs/hypotheses/2026-05-16_monologue_length_pre_registration.md``.
Pre-reg ``§7``, ``§8``, and ``§9`` lock everything in this file.

Reads judged JSONL files (one per Anima model) for ONE source (AAI
primary or LSI fresh) and computes:

- Per-(persona, prompt, trial, model) composite scores per cell (range
  4-12), summed across the 4 persona-specific criteria.
- 4 primary contrasts (H1a-H1d) per model:
    * variable_marcus - short_marcus
    * variable_marcus - long_marcus
    * variable_jamie  - short_jamie
    * variable_jamie  - long_jamie
- Paired t-test (within model) on the per-(prompt, trial) differences.
- Bootstrap 95% CI on the effect size (default 10,000 resamples, seeded).
- Holm-Bonferroni adjustment across the 4 primary tests, within model.
- Cross-model aggregation per contrast (>=2/3 models -> green).
- H1 overall verdict for this source.
- H2 (effect-size asymmetry) - bootstrap CI non-overlap between the
  jamie-long contrast and the other three.

Falsification rigor (pre-reg §10): no model-drop, no metric-swap, no
threshold-drift. The "supported on >=2/3 models" rule handles minor
inconsistency without silently dropping models from the analysis.

CLI::

    python verification/scripts/2026-05-16_monologue_length_analysis.py \\
        --source {primary|fresh} \\
        [--input-dir verification/reports/] \\
        [--output verification/reports/2026-05-16_monologue_length_{source}_verdict.json] \\
        [--bootstrap-iterations 10000] \\
        [--seed 42]

Discipline:
    - Read-only on ``anima_v1/``, ``anima/``, the pre-reg doc, and the
      judged JSONL inputs. This script never modifies them.
    - The Markdown verdict at
      ``verification/reports/2026-05-16_monologue_length_{source}_verdict.md``
      is generated alongside the JSON.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


# ---- locked constants ---------------------------------------------------

MODELS: tuple[str, ...] = ("deepseek", "mistral", "qwen")

MARCUS_CRITERIA: tuple[str, ...] = (
    "intellectualization-as-defense",
    "isolation-of-affect",
    "emotional-inhibition",
    "avoidant-deflection",
)
JAMIE_CRITERIA: tuple[str, ...] = (
    "warmth",
    "social-attunement",
    "humor-playfulness",
    "emotional-openness",
)

PRIMARY_CONTRASTS: tuple[tuple[str, str, str], ...] = (
    # (label, persona, fixed_cell): contrast = variable - fixed_cell
    ("H1a:variable_marcus_vs_short_marcus", "marcus", "short"),
    ("H1b:variable_marcus_vs_long_marcus", "marcus", "long"),
    ("H1c:variable_jamie_vs_short_jamie", "jamie", "short"),
    ("H1d:variable_jamie_vs_long_jamie", "jamie", "long"),
)

EFFECT_SIZE_FLOOR: float = 0.5
PRIMARY_ALPHA: float = 0.05
N_PRIMARY_TESTS: int = 4
BOOTSTRAP_DEFAULT: int = 10_000
SEED_DEFAULT: int = 42

# H2 contrast label (must match one of PRIMARY_CONTRASTS labels)
H2_TARGET_LABEL: str = "H1d:variable_jamie_vs_long_jamie"


# ---- types --------------------------------------------------------------


@dataclass
class CellComposites:
    """Composite scores per cell for one (persona, prompt, trial, model)."""

    composites: dict[str, int] = field(default_factory=dict)
    criteria_seen: set[str] = field(default_factory=set)


@dataclass
class ContrastResult:
    label: str
    persona: str
    fixed_cell: str
    model: str
    n_pairs: int
    mean_diff: float
    t_stat: float
    p_value: float
    ci_low: float
    ci_high: float
    differences: list[float]

    @property
    def passes_effect_floor(self) -> bool:
        return self.mean_diff >= EFFECT_SIZE_FLOOR


# ---- input loading ------------------------------------------------------


def _judged_filename(source: str, model: str) -> str:
    return f"2026-05-16_monologue_length_{source}_{model}_judged.jsonl"


def _load_judged_records(
    path: Path, *, log,
) -> tuple[list[dict[str, Any]], int]:
    """Read judged JSONL. Returns (kept_records, n_judge_error_skipped)."""
    if not path.exists():
        return [], 0
    kept: list[dict[str, Any]] = []
    n_err = 0
    with path.open("r", encoding="utf-8") as fh:
        for ln_no, line in enumerate(fh, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError as exc:
                log(
                    f"WARNING: {path}:{ln_no}: malformed JSON, "
                    f"skipping: {exc}"
                )
                continue
            # Minor: defensive on non-dict JSON (top-level array, string,
            # number, etc).
            if not isinstance(rec, dict):
                log(
                    f"WARNING: {path}:{ln_no}: non-dict record "
                    f"(type={type(rec).__name__}), skipping"
                )
                continue
            if rec.get("_judge_error"):
                n_err += 1
                continue
            kept.append(rec)
    return kept, n_err


def _expected_criteria_for(persona: str) -> tuple[str, ...]:
    if persona == "marcus":
        return MARCUS_CRITERIA
    if persona == "jamie":
        return JAMIE_CRITERIA
    raise ValueError(f"unknown persona: {persona!r}")


# ---- composite computation ----------------------------------------------


def _build_composites(
    records: list[dict[str, Any]],
    *,
    model: str,
    log,
) -> tuple[
    dict[tuple[str, int, int], CellComposites],
    list[tuple[str, int, int, str]],
]:
    """Group judged records by (persona, prompt_index, trial_index) and
    sum ``composite_points_by_cell`` across the 4 persona criteria.
    """
    by_key: dict[tuple[str, int, int], dict[str, dict[str, int]]] = (
        defaultdict(lambda: defaultdict(dict))
    )
    seen_criteria: dict[tuple[str, int, int], set[str]] = defaultdict(set)

    for rec in records:
        try:
            persona = str(rec["persona"])
            pi = int(rec["prompt_index"])
            ti = int(rec["trial_index"])
            crit = str(rec["criterion"])
            cpb = rec.get("composite_points_by_cell")
        except (KeyError, TypeError, ValueError):
            log(
                f"WARNING: model={model}: skipping malformed record "
                f"(missing fields): keys={list(rec)}"
            )
            continue
        if not isinstance(cpb, dict):
            log(
                f"WARNING: model={model}: persona={persona} "
                f"prompt={pi} trial={ti} criterion={crit}: "
                f"composite_points_by_cell is not a dict; skipping"
            )
            continue
        key = (persona, pi, ti)
        by_key[key][crit] = {str(c): int(v) for c, v in cpb.items()}
        seen_criteria[key].add(crit)

    composites: dict[tuple[str, int, int], CellComposites] = {}
    skipped: list[tuple[str, int, int, str]] = []

    for key, crit_map in by_key.items():
        persona = key[0]
        expected = set(_expected_criteria_for(persona))
        got = seen_criteria[key]
        if got != expected:
            log(
                f"WARNING: model={model}: persona={persona} "
                f"prompt={key[1]} trial={key[2]}: criteria mismatch - "
                f"expected {sorted(expected)} got {sorted(got)}; "
                f"skipping trial"
            )
            skipped.append((persona, key[1], key[2], model))
            continue
        cell_totals: dict[str, int] = defaultdict(int)
        valid = True
        for crit in expected:
            for cell, pts in crit_map[crit].items():
                cell_totals[cell] += pts
        for cell, total in cell_totals.items():
            if not (4 <= total <= 12):
                log(
                    f"WARNING: model={model}: persona={persona} "
                    f"prompt={key[1]} trial={key[2]} cell={cell}: "
                    f"composite={total} outside [4, 12]; skipping trial"
                )
                valid = False
                break
        # Minor: only run the cells-set check when the range check passed,
        # to avoid double-logging the same skipped trial.
        if valid and set(cell_totals.keys()) != {"variable", "short", "long"}:
            log(
                f"WARNING: model={model}: persona={persona} "
                f"prompt={key[1]} trial={key[2]}: cells "
                f"{sorted(cell_totals)} != "
                f"variable/short/long; skipping trial"
            )
            valid = False
        if not valid:
            skipped.append((persona, key[1], key[2], model))
            continue
        cc = CellComposites(
            composites={c: int(v) for c, v in cell_totals.items()},
            criteria_seen=set(got),
        )
        composites[key] = cc

    return composites, skipped


# ---- paired t-test + bootstrap CI ---------------------------------------


def _paired_ttest(differences: np.ndarray) -> tuple[float, float, int]:
    """Paired t-test on differences vs 0. Two-sided p-value."""
    n = len(differences)
    if n < 2:
        return float("nan"), float("nan"), max(0, n - 1)
    mean = float(np.mean(differences))
    std = float(np.std(differences, ddof=1))
    if std == 0.0:
        if mean == 0.0:
            return 0.0, 1.0, n - 1
        return float("inf"), 0.0, n - 1
    try:
        from scipy import stats  # type: ignore
        res = stats.ttest_1samp(differences, popmean=0.0)
        return float(res.statistic), float(res.pvalue), n - 1
    except ImportError:
        t = mean / (std / math.sqrt(n))
        from math import erf
        z = abs(t)
        p = 2.0 * (1.0 - 0.5 * (1.0 + erf(z / math.sqrt(2.0))))
        return float(t), float(p), n - 1


def _bootstrap_mean_ci(
    differences: np.ndarray,
    *,
    n_iterations: int,
    seed: int,
    alpha: float = 0.05,
) -> tuple[float, float]:
    """Bootstrap two-sided CI on the mean of ``differences``."""
    if len(differences) == 0:
        return float("nan"), float("nan")
    rng = np.random.default_rng(seed)
    n = len(differences)
    means = np.empty(n_iterations, dtype=np.float64)
    chunk = 1024
    written = 0
    while written < n_iterations:
        this = min(chunk, n_iterations - written)
        idx = rng.integers(0, n, size=(this, n))
        sample = differences[idx]
        means[written:written + this] = sample.mean(axis=1)
        written += this
    lo = float(np.percentile(means, 100 * (alpha / 2)))
    hi = float(np.percentile(means, 100 * (1 - alpha / 2)))
    return lo, hi


def _stable_bootstrap_seed(base_seed: int, *parts: str) -> int:
    """Derive a deterministic 64-bit seed from base + path parts."""
    import hashlib
    payload = f"{base_seed}|" + "|".join(parts)
    return int(
        hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16], 16
    )


# ---- Holm-Bonferroni ----------------------------------------------------


def _holm_bonferroni(
    p_values: list[float], *, alpha: float = PRIMARY_ALPHA,
) -> list[tuple[int, float, float, bool]]:
    """Holm-Bonferroni step-down for a family of ``p_values``.

    Returns a list of (original_index, p_value, adjusted_alpha,
    is_significant) tuples, in the original input order.
    """
    m = len(p_values)
    if m == 0:
        return []
    ordered = sorted(enumerate(p_values), key=lambda x: x[1])
    significant_so_far = True
    decisions: dict[int, tuple[float, bool]] = {}
    for rank, (orig_idx, p) in enumerate(ordered):
        adj_alpha = alpha / (m - rank)
        if significant_so_far:
            if math.isnan(p) or not (p < adj_alpha):
                significant_so_far = False
        is_sig = significant_so_far
        decisions[orig_idx] = (adj_alpha, is_sig)
    return [
        (i, p_values[i], decisions[i][0], decisions[i][1])
        for i in range(m)
    ]


# ---- per-model contrast analysis ---------------------------------------


def _contrast_differences(
    composites: dict[tuple[str, int, int], CellComposites],
    *,
    persona: str,
    fixed_cell: str,
) -> list[float]:
    """Return the per-(prompt, trial) (variable - fixed) deltas for
    one persona within one model's composites dict.
    """
    diffs: list[float] = []
    for (p, _pi, _ti), cc in composites.items():
        if p != persona:
            continue
        if "variable" not in cc.composites or fixed_cell not in cc.composites:
            continue
        diffs.append(
            float(cc.composites["variable"]) - float(cc.composites[fixed_cell])
        )
    return diffs


def _analyze_model_contrasts(
    composites: dict[tuple[str, int, int], CellComposites],
    *,
    model: str,
    bootstrap_iterations: int,
    seed: int,
    log,
) -> list[ContrastResult]:
    """Run the 4 primary contrasts within one model's data."""
    results: list[ContrastResult] = []
    for label, persona, fixed in PRIMARY_CONTRASTS:
        diffs = _contrast_differences(
            composites, persona=persona, fixed_cell=fixed,
        )
        if not diffs:
            log(
                f"WARNING: model={model} contrast={label}: 0 paired "
                f"observations; emitting NaN results"
            )
            results.append(ContrastResult(
                label=label,
                persona=persona,
                fixed_cell=fixed,
                model=model,
                n_pairs=0,
                mean_diff=float("nan"),
                t_stat=float("nan"),
                p_value=float("nan"),
                ci_low=float("nan"),
                ci_high=float("nan"),
                differences=[],
            ))
            continue
        arr = np.array(diffs, dtype=np.float64)
        t_stat, p_value, _df = _paired_ttest(arr)
        boot_seed = _stable_bootstrap_seed(seed, model, label)
        ci_lo, ci_hi = _bootstrap_mean_ci(
            arr, n_iterations=bootstrap_iterations, seed=boot_seed,
        )
        results.append(ContrastResult(
            label=label,
            persona=persona,
            fixed_cell=fixed,
            model=model,
            n_pairs=len(diffs),
            mean_diff=float(np.mean(arr)),
            t_stat=float(t_stat),
            p_value=float(p_value),
            ci_low=float(ci_lo),
            ci_high=float(ci_hi),
            differences=[float(d) for d in diffs],
        ))
    return results


# ---- cross-model aggregation -------------------------------------------


def _classify_contrast_outcome(
    r: ContrastResult, holm_sig: bool,
) -> str:
    """Per pre-reg §8: wrong-direction / floor-failure / underpowered /
    supported.

    Improvement 2: wrong-direction-underpowered is visible regardless of
    significance. A strong negative point estimate (mean_diff <=
    -EFFECT_SIZE_FLOOR) without Holm significance is no longer hidden
    under 'ambiguous'.
    """
    if r.n_pairs == 0 or math.isnan(r.mean_diff):
        return "no-data"
    if r.mean_diff <= -EFFECT_SIZE_FLOOR and holm_sig:
        return "wrong-direction"
    if r.mean_diff <= -EFFECT_SIZE_FLOOR and not holm_sig:
        return "wrong-direction-underpowered"
    if abs(r.mean_diff) < EFFECT_SIZE_FLOOR:
        return "floor-failure-null"
    if r.mean_diff >= EFFECT_SIZE_FLOOR and holm_sig:
        return "supported"
    if r.mean_diff >= EFFECT_SIZE_FLOOR and not holm_sig:
        return "underpowered-inconclusive"
    return "ambiguous"


def _per_contrast_supported(
    results: list[ContrastResult],
    holm_decisions: list[tuple[int, float, float, bool]],
) -> tuple[bool, dict[str, Any]]:
    """For ONE model, decide per-contrast support given Holm decisions."""
    by_label: dict[str, Any] = {}
    any_supported = False
    for r, (_orig, p, adj_alpha, is_sig) in zip(results, holm_decisions):
        floor_ok = (
            r.n_pairs > 0
            and not math.isnan(r.mean_diff)
            and r.mean_diff >= EFFECT_SIZE_FLOOR
        )
        supported = bool(floor_ok and is_sig)
        verdict = _classify_contrast_outcome(r, is_sig)
        by_label[r.label] = {
            "n_pairs": r.n_pairs,
            "mean_diff": r.mean_diff,
            "t_stat": r.t_stat,
            "p_value": r.p_value,
            "holm_adjusted_alpha": adj_alpha,
            "holm_significant": bool(is_sig),
            "ci95_low": r.ci_low,
            "ci95_high": r.ci_high,
            "passes_effect_floor": floor_ok,
            "supported": supported,
            "outcome_class": verdict,
        }
        any_supported = any_supported or supported
    return any_supported, by_label


def _aggregate_across_models(
    per_model: dict[str, dict[str, dict[str, Any]]],
) -> dict[str, dict[str, Any]]:
    """For each contrast label, count models on which it is supported.

    status: "green" (>=2 of >=1 model w/ data), "mixed" (==1),
    "falsified" (==0 of >=1 model w/ data), "no-data" (0 models).
    """
    out: dict[str, dict[str, Any]] = {}
    all_labels = [c[0] for c in PRIMARY_CONTRASTS]
    for label in all_labels:
        models_with_data = []
        models_supported = []
        for model_name, by_label in per_model.items():
            d = by_label.get(label)
            if not d:
                continue
            if d["n_pairs"] > 0:
                models_with_data.append(model_name)
            if d["supported"]:
                models_supported.append(model_name)
        n_supp = len(models_supported)
        n_data = len(models_with_data)
        if n_data == 0:
            status = "no-data"
        elif n_supp >= 2:
            status = "green"
        elif n_supp == 1:
            status = "mixed"
        else:
            status = "falsified"
        out[label] = {
            "n_supported": n_supp,
            "n_models_with_data": n_data,
            "supported_on": models_supported,
            "status": status,
        }
    return out


def _h1_overall(
    cross_model: dict[str, dict[str, Any]],
) -> tuple[str, str]:
    """Per pre-reg §8: H1 supported iff all 4 contrasts green
    (>=2/3 models).

    Status distinction (Improvement 1: NO-DATA distinct from FALSIFIED):
      - SUPPORTED: all 4 contrasts green
      - NO-DATA: all 4 contrasts no-data. Absence of evidence is NOT
        evidence of absence; H1 cannot be adjudicated on this source.
      - FALSIFIED: at least one contrast carries data (status='falsified')
        and no contrast is green. Evidence of absence on observed data.
      - PARTIALLY-SUPPORTED: any other mix.
    """
    labels = [c[0] for c in PRIMARY_CONTRASTS]
    statuses = [cross_model[lbl]["status"] for lbl in labels]
    if all(s == "green" for s in statuses):
        return "SUPPORTED", (
            "All four primary contrasts pass the 0.5-point effect "
            "floor AND Holm-Bonferroni significance on >=2 of 3 models."
        )
    if all(s == "no-data" for s in statuses):
        return "NO-DATA", (
            "No primary contrast has any model with usable data. "
            "Absence of evidence, not evidence of absence: H1 cannot "
            "be adjudicated on this source."
        )
    if (
        all(s in {"falsified", "no-data"} for s in statuses)
        and any(s == "falsified" for s in statuses)
    ):
        return "FALSIFIED", (
            "No primary contrast achieves >=2/3 model support, and at "
            "least one contrast has data showing the hypothesis fails. "
            "Statuses: "
            + ", ".join(f"{lbl}={s}" for lbl, s in zip(labels, statuses))
        )
    n_green = sum(1 for s in statuses if s == "green")
    return "PARTIALLY-SUPPORTED", (
        f"{n_green}/4 primary contrasts pass >=2/3 model support; "
        f"H1 overall not elevated. Statuses: "
        + ", ".join(f"{lbl}={s}" for lbl, s in zip(labels, statuses))
    )


# ---- H2: effect-size asymmetry -----------------------------------------


def _ci_overlaps(
    a_lo: float, a_hi: float, b_lo: float, b_hi: float,
) -> bool:
    """True iff intervals [a_lo, a_hi] and [b_lo, b_hi] overlap."""
    if any(math.isnan(x) for x in (a_lo, a_hi, b_lo, b_hi)):
        return True
    return not (a_hi < b_lo or b_hi < a_lo)


def _analyze_h2(
    per_model_results: dict[str, list[ContrastResult]],
    *,
    bootstrap_iterations: int,
    seed: int,
) -> dict[str, Any]:
    """H2: bootstrap CI on jamie-long effect size does not overlap with
    any of the other three contrasts' 95% CIs.

    Pre-reg §8.2: CI is on "per-(prompt, trial) effect sizes, stratified
    by model". We pool per-trial differences across models then
    bootstrap. Per-model H2 also reported.
    """
    pooled: dict[str, list[float]] = {lbl: [] for lbl, _, _ in PRIMARY_CONTRASTS}
    for model_name, results in per_model_results.items():
        for r in results:
            if r.n_pairs > 0:
                pooled[r.label].extend(r.differences)

    pooled_arrays = {
        lbl: np.array(d, dtype=np.float64) for lbl, d in pooled.items()
    }
    pooled_stats: dict[str, dict[str, Any]] = {}
    for lbl, arr in pooled_arrays.items():
        if len(arr) == 0:
            pooled_stats[lbl] = {
                "n": 0,
                "mean_diff": float("nan"),
                "ci95_low": float("nan"),
                "ci95_high": float("nan"),
            }
            continue
        boot_seed = _stable_bootstrap_seed(seed, "h2-pooled", lbl)
        lo, hi = _bootstrap_mean_ci(
            arr, n_iterations=bootstrap_iterations, seed=boot_seed,
        )
        pooled_stats[lbl] = {
            "n": int(len(arr)),
            "mean_diff": float(np.mean(arr)),
            "ci95_low": float(lo),
            "ci95_high": float(hi),
        }

    target = pooled_stats[H2_TARGET_LABEL]
    others = [lbl for lbl, _, _ in PRIMARY_CONTRASTS if lbl != H2_TARGET_LABEL]
    other_overlaps: dict[str, bool] = {}
    for lbl in others:
        o = pooled_stats[lbl]
        overlaps = _ci_overlaps(
            target["ci95_low"], target["ci95_high"],
            o["ci95_low"], o["ci95_high"],
        )
        other_overlaps[lbl] = bool(overlaps)

    target_is_largest = True
    if math.isnan(target["mean_diff"]):
        target_is_largest = False
    else:
        for lbl in others:
            o = pooled_stats[lbl]
            if math.isnan(o["mean_diff"]):
                continue
            if target["mean_diff"] <= o["mean_diff"]:
                target_is_largest = False
                break

    no_overlap = all(not v for v in other_overlaps.values())

    if target_is_largest and no_overlap and not math.isnan(target["mean_diff"]):
        status = "SUPPORTED"
        rationale = (
            "Jamie-long is the largest by point estimate AND its "
            "bootstrap 95% CI does not overlap with any of the other "
            "three contrasts."
        )
    elif not target_is_largest:
        status = "FALSIFIED-NOT-LARGEST"
        rationale = (
            "Jamie-long point estimate is not the largest of the four "
            "primary contrasts."
        )
    else:
        status = "FALSIFIED-CI-OVERLAP"
        rationale = (
            "Jamie-long is the largest by point estimate, but its "
            "bootstrap 95% CI overlaps with at least one other "
            "contrast's CI."
        )

    per_model_h2: dict[str, Any] = {}
    for model_name, results in per_model_results.items():
        by_label = {r.label: r for r in results}
        tgt = by_label.get(H2_TARGET_LABEL)
        if tgt is None or tgt.n_pairs == 0:
            per_model_h2[model_name] = {"status": "no-data"}
            continue
        overlaps: dict[str, Any] = {}
        for lbl in others:
            o = by_label.get(lbl)
            if o is None or o.n_pairs == 0:
                overlaps[lbl] = None
                continue
            overlaps[lbl] = _ci_overlaps(
                tgt.ci_low, tgt.ci_high, o.ci_low, o.ci_high,
            )
        is_largest = all(
            (by_label[lbl].mean_diff < tgt.mean_diff)
            for lbl in others
            if by_label.get(lbl) is not None
            and by_label[lbl].n_pairs > 0
            and not math.isnan(by_label[lbl].mean_diff)
        )
        per_model_h2[model_name] = {
            "jamie_long_mean": tgt.mean_diff,
            "jamie_long_ci95": [tgt.ci_low, tgt.ci_high],
            "ci_overlaps_other": overlaps,
            "point_estimate_largest": bool(is_largest),
        }

    return {
        "status": status,
        "rationale": rationale,
        "target_contrast": H2_TARGET_LABEL,
        "target_is_point_largest": bool(target_is_largest),
        "ci_no_overlap_all_others": bool(no_overlap),
        "pooled_per_contrast": pooled_stats,
        "per_model": per_model_h2,
    }


# ---- markdown rendering -------------------------------------------------


def _fmt_float(x: float, decimals: int = 3) -> str:
    if math.isnan(x):
        return "nan"
    if math.isinf(x):
        return "inf" if x > 0 else "-inf"
    return f"{x:.{decimals}f}"


def _fmt_p(p: float) -> str:
    if math.isnan(p):
        return "nan"
    if p < 1e-4:
        return f"{p:.2e}"
    return f"{p:.4f}"


def _render_markdown(
    *,
    source: str,
    models_present: list[str],
    models_missing: list[str],
    n_trials_per_model: dict[str, int],
    n_skipped_per_model: dict[str, int],
    per_model_decisions: dict[str, dict[str, dict[str, Any]]],
    cross_model: dict[str, dict[str, Any]],
    h1_status: str,
    h1_rationale: str,
    h2: dict[str, Any],
    skipped: list[tuple[str, int, int, str]],
    bootstrap_iterations: int,
    seed: int,
    pre_reg_doc_sha: str | None,
) -> str:
    src_name = "AAI primary" if source == "primary" else "LSI fresh"
    lines: list[str] = []
    lines.append(
        f"# Monologue-length-directive verdict - {src_name} run"
    )
    lines.append("")
    lines.append("## 1. What this is")
    lines.append("")
    lines.append(
        f"Pre-registered analysis of the `{source}` source for the "
        f"monologue-length-directive Phase 1 retrospective. "
        f"Adjudicates `docs/hypotheses/"
        f"2026-05-16_monologue_length_pre_registration.md` (H1, H2) "
        f"on judged JSONL across "
        f"{len(models_present)}/{len(MODELS)} Anima models "
        f"({', '.join(models_present)}). Bootstrap: "
        f"{bootstrap_iterations:,} iterations, seed={seed}. "
        f"Holm-Bonferroni alpha-max=0.0125 across the 4 primary tests "
        f"per model. >=2/3 models per contrast required for cross-model "
        f"support."
    )
    lines.append("")
    # Improvement 3: explicit list of missing models, per pre-reg §10
    # (no silent model-drop).
    missing_str = ", ".join(models_missing) if models_missing else "(none)"
    lines.append(f"**Models missing:** {missing_str}")
    if pre_reg_doc_sha:
        lines.append("")
        lines.append(f"Pre-registration SHA: `{pre_reg_doc_sha}`.")
    lines.append("")
    lines.append("## 2. Trials per model")
    lines.append("")
    lines.append("| Model | Trials (judged, all 4 criteria) | Skipped |")
    lines.append("|---|---:|---:|")
    for m in models_present:
        lines.append(
            f"| {m} | {n_trials_per_model.get(m, 0)} | "
            f"{n_skipped_per_model.get(m, 0)} |"
        )
    lines.append("")

    lines.append("## 3. Per-contrast per-model statistics")
    lines.append("")
    lines.append(
        "Composite scale: 4-12 per cell (sum of rank-points across 4 "
        "persona criteria). Contrast = `composite(variable) - "
        "composite(fixed)`. Paired by `(prompt_index, trial_index)` "
        "within model."
    )
    lines.append("")
    lines.append(
        "| Contrast | Model | N_pairs | Mean diff | t | p | Holm alpha | "
        "95% CI | Outcome |"
    )
    lines.append("|---|---|---:|---:|---:|---:|---:|---|---|")
    for label, _persona, _fixed in PRIMARY_CONTRASTS:
        for m in models_present:
            d = per_model_decisions.get(m, {}).get(label)
            if not d:
                continue
            outcome = d["outcome_class"]
            if d["supported"]:
                mark = "[+]"
            elif outcome in {
                "wrong-direction",
                "wrong-direction-underpowered",
                "floor-failure-null",
            }:
                mark = "[x]"
            else:
                mark = "[.]"
            ci_str = (
                f"[{_fmt_float(d['ci95_low'], 2)}, "
                f"{_fmt_float(d['ci95_high'], 2)}]"
            )
            lines.append(
                f"| {label} | {m} | {d['n_pairs']} | "
                f"{_fmt_float(d['mean_diff'], 3)} | "
                f"{_fmt_float(d['t_stat'], 2)} | "
                f"{_fmt_p(d['p_value'])} | "
                f"{_fmt_float(d['holm_adjusted_alpha'], 4)} | "
                f"{ci_str} | {mark} {outcome} |"
            )
    lines.append("")

    lines.append("## 4. Cross-model aggregation per contrast")
    lines.append("")
    lines.append("| Contrast | Supported on | Status |")
    lines.append("|---|---|---|")
    for label, _, _ in PRIMARY_CONTRASTS:
        cm = cross_model[label]
        models_str = (
            ", ".join(cm["supported_on"]) if cm["supported_on"] else "-"
        )
        lines.append(
            f"| {label} | {cm['n_supported']}/{cm['n_models_with_data']} "
            f"({models_str}) | **{cm['status']}** |"
        )
    lines.append("")

    lines.append("## 5. H1 verdict")
    lines.append("")
    lines.append(f"**H1 (overall) on `{source}` source: {h1_status}**")
    lines.append("")
    lines.append(h1_rationale)
    lines.append("")
    if source == "primary":
        if h1_status == "SUPPORTED":
            lines.append(
                "Per pre-reg §13.5, the §13.5 LSI fresh-data run is "
                "now triggered. §13.5-confirmed elevation requires the "
                "same primary sub-hypothesis support on BOTH AAI "
                "(this run) AND LSI."
            )
        else:
            lines.append(
                "Per pre-reg §9: §13.5 LSI fresh-data run is **not** "
                "triggered. The LSI prompts remain unspent for a "
                "future experiment."
            )
    else:
        lines.append(
            "Per pre-reg §9/§13.5: §13.5-confirmed elevation requires "
            "H1 supported on BOTH the AAI primary AND this LSI fresh "
            "run for the same primary sub-hypotheses."
        )
    lines.append("")

    lines.append("## 6. H2 verdict")
    lines.append("")
    lines.append(f"**H2 (jamie-long effect-size asymmetry): {h2['status']}**")
    lines.append("")
    lines.append(h2["rationale"])
    lines.append("")
    lines.append(
        "Pooled effect sizes and bootstrap 95% CIs (per-trial deltas "
        "concatenated across models):"
    )
    lines.append("")
    lines.append("| Contrast | N | Mean diff | 95% CI |")
    lines.append("|---|---:|---:|---|")
    for label, _, _ in PRIMARY_CONTRASTS:
        st = h2["pooled_per_contrast"][label]
        ci_str = (
            f"[{_fmt_float(st['ci95_low'], 2)}, "
            f"{_fmt_float(st['ci95_high'], 2)}]"
        )
        mark = " (H2 target)" if label == H2_TARGET_LABEL else ""
        lines.append(
            f"| {label}{mark} | {st['n']} | "
            f"{_fmt_float(st['mean_diff'], 3)} | {ci_str} |"
        )
    lines.append("")

    lines.append("## 7. Skipped trials (criteria mismatch)")
    lines.append("")
    if not skipped:
        lines.append("None.")
    else:
        lines.append(
            f"{len(skipped)} (persona, prompt_index, trial_index, "
            f"model) tuples skipped due to missing or extra criterion "
            f"records. Detail in JSON envelope."
        )
    lines.append("")

    lines.append("## 8. Reproducibility")
    lines.append("")
    lines.append(f"- Bootstrap iterations: **{bootstrap_iterations:,}**")
    lines.append(f"- Random seed: **{seed}**")
    lines.append(f"- Pre-registration SHA: `{pre_reg_doc_sha or '(none)'}`")
    lines.append(
        "- All per-contrast bootstrap seeds derived from "
        "`SHA256(seed | model | label)`; H2 pooled-bootstrap seeds "
        "derived from `SHA256(seed | 'h2-pooled' | label)`."
    )
    lines.append("")
    return "\n".join(lines)


# ---- main ---------------------------------------------------------------


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Monologue-length-directive analysis stage. "
            "Pre-registration: docs/hypotheses/"
            "2026-05-16_monologue_length_pre_registration.md."
        )
    )
    parser.add_argument(
        "--source", required=True, choices=["primary", "fresh"],
        help="primary=AAI; fresh=LSI",
    )
    parser.add_argument(
        "--input-dir", type=Path,
        default=Path("verification/reports"),
        help="Directory containing judged JSONL files.",
    )
    parser.add_argument(
        "--output", type=Path, default=None,
        help=(
            "Output JSON path. Defaults to "
            "verification/reports/2026-05-16_monologue_length_"
            "{source}_verdict.json."
        ),
    )
    parser.add_argument(
        "--bootstrap-iterations", type=int, default=BOOTSTRAP_DEFAULT,
        help="Bootstrap resamples for CI estimation.",
    )
    parser.add_argument(
        "--seed", type=int, default=SEED_DEFAULT,
        help="Base random seed.",
    )
    return parser.parse_args(argv)


def _default_output(source: str) -> Path:
    return (
        _ROOT / "verification" / "reports"
        / f"2026-05-16_monologue_length_{source}_verdict.json"
    )


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)

    def log(msg: str) -> None:
        print(f"[mla] {msg}", file=sys.stderr, flush=True)

    source: str = args.source
    in_dir: Path = args.input_dir
    if not in_dir.is_absolute():
        in_dir = (_ROOT / in_dir).resolve()
    out_json: Path = args.output or _default_output(source)
    if not out_json.is_absolute():
        out_json = (_ROOT / out_json).resolve()
    out_md = out_json.with_suffix(".md")

    log(f"source={source}; input_dir={in_dir}; output={out_json}")
    log(
        f"bootstrap_iterations={args.bootstrap_iterations} "
        f"seed={args.seed}"
    )

    per_model_records: dict[str, list[dict[str, Any]]] = {}
    n_judge_errors: dict[str, int] = {}
    missing_models: list[str] = []
    # Improvement 4: SHA-256 per loaded input file so reviewers can
    # verify the same bytes were analyzed (no manual re-hash).
    input_file_shas: dict[str, str] = {}
    input_file_paths: dict[str, str] = {}
    for m in MODELS:
        path = in_dir / _judged_filename(source, m)
        if not path.exists():
            log(
                f"WARNING: missing judged file for model={m}: "
                f"{path} - proceeding without this model"
            )
            missing_models.append(m)
            continue
        import hashlib as _hashlib
        try:
            sha = _hashlib.sha256(path.read_bytes()).hexdigest()
        except OSError as exc:
            log(
                f"WARNING: could not compute SHA-256 for {path}: {exc}"
            )
            sha = None
        recs, n_err = _load_judged_records(path, log=log)
        per_model_records[m] = recs
        n_judge_errors[m] = n_err
        if sha is not None:
            input_file_shas[m] = sha
        input_file_paths[m] = str(path)
        log(
            f"loaded model={m}: {len(recs)} non-error records, "
            f"{n_err} _judge_error records filtered; sha256={sha}"
        )

    if not per_model_records:
        log(
            "FATAL: no models had any judged data. Cannot compute "
            "verdict. Exiting."
        )
        return 2
    if len(per_model_records) < len(MODELS):
        log(
            f"NOTE: proceeding with {len(per_model_records)}/"
            f"{len(MODELS)} models. Cross-model aggregation will use "
            f"the available subset; pre-reg §10 forbids silent model-"
            f"drop, so missing models are recorded explicitly in the "
            f"verdict envelope."
        )

    pre_reg_shas: set[str] = set()
    for recs in per_model_records.values():
        for r in recs:
            sha = r.get("pre_reg_doc_sha")
            if sha:
                pre_reg_shas.add(str(sha))
    if not pre_reg_shas:
        log("WARNING: no pre_reg_doc_sha on any record")
        pre_reg_doc_sha = None
    elif len(pre_reg_shas) > 1:
        log(
            f"WARNING: pre_reg_doc_sha mismatch across records: "
            f"{sorted(pre_reg_shas)}"
        )
        pre_reg_doc_sha = sorted(pre_reg_shas)[0]
    else:
        pre_reg_doc_sha = next(iter(pre_reg_shas))
        log(f"pre_reg_doc_sha={pre_reg_doc_sha}")

    per_model_composites: dict[
        str, dict[tuple[str, int, int], CellComposites]
    ] = {}
    all_skipped: list[tuple[str, int, int, str]] = []
    n_trials_per_model: dict[str, int] = {}
    n_skipped_per_model: dict[str, int] = {}
    for m, recs in per_model_records.items():
        comps, skipped = _build_composites(recs, model=m, log=log)
        per_model_composites[m] = comps
        n_trials_per_model[m] = len(comps)
        n_skipped_per_model[m] = len(skipped)
        all_skipped.extend(skipped)
        log(
            f"composites model={m}: {len(comps)} valid trials, "
            f"{len(skipped)} skipped"
        )

    per_model_results: dict[str, list[ContrastResult]] = {}
    per_model_decisions: dict[str, dict[str, dict[str, Any]]] = {}
    for m, comps in per_model_composites.items():
        results = _analyze_model_contrasts(
            comps,
            model=m,
            bootstrap_iterations=args.bootstrap_iterations,
            seed=args.seed,
            log=log,
        )
        per_model_results[m] = results
        holm = _holm_bonferroni([r.p_value for r in results])
        _, by_label = _per_contrast_supported(results, holm)
        per_model_decisions[m] = by_label

    cross_model = _aggregate_across_models(per_model_decisions)
    h1_status, h1_rationale = _h1_overall(cross_model)

    h2 = _analyze_h2(
        per_model_results,
        bootstrap_iterations=args.bootstrap_iterations,
        seed=args.seed,
    )

    # Improvement 5: record stats-library versions for reproducibility.
    reproducibility: dict[str, Any] = {
        "python_version": sys.version,
        "numpy_version": getattr(np, "__version__", None),
    }
    try:
        import scipy  # type: ignore
        reproducibility["scipy_version"] = getattr(
            scipy, "__version__", None
        )
        reproducibility["scipy_available"] = True
    except ImportError:
        reproducibility["scipy_version"] = None
        reproducibility["scipy_available"] = False

    envelope: dict[str, Any] = {
        "source": source,
        "input_dir": str(in_dir),
        "models_present": sorted(per_model_records.keys()),
        "models_missing": sorted(missing_models),
        "pre_reg_doc_sha": pre_reg_doc_sha,
        # Improvement 4: per-input-file SHA-256 + path.
        "input_file_shas": input_file_shas,
        "input_file_paths": input_file_paths,
        # Improvement 5: library versions for reproducibility.
        "reproducibility": reproducibility,
        "bootstrap_iterations": int(args.bootstrap_iterations),
        "random_seed": int(args.seed),
        "n_trials_per_model": n_trials_per_model,
        "n_judge_errors_filtered_per_model": n_judge_errors,
        "n_skipped_trials_per_model": n_skipped_per_model,
        "skipped_trials": [
            {
                "persona": p, "prompt_index": pi,
                "trial_index": ti, "model": m,
            }
            for (p, pi, ti, m) in all_skipped
        ],
        "primary_contrasts": [
            {
                "label": lbl, "persona": pers, "fixed_cell": fixed,
            }
            for lbl, pers, fixed in PRIMARY_CONTRASTS
        ],
        "per_model_decisions": per_model_decisions,
        "cross_model_aggregate": cross_model,
        "h1_overall": {
            "status": h1_status,
            "rationale": h1_rationale,
        },
        "h2": h2,
        "effect_size_floor": EFFECT_SIZE_FLOOR,
        "primary_alpha": PRIMARY_ALPHA,
        "n_primary_tests": N_PRIMARY_TESTS,
    }

    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(
        json.dumps(envelope, indent=2, ensure_ascii=False, default=str)
        + "\n",
        encoding="utf-8",
    )
    log(f"wrote verdict JSON -> {out_json}")

    md = _render_markdown(
        source=source,
        models_present=sorted(per_model_records.keys()),
        models_missing=sorted(missing_models),
        n_trials_per_model=n_trials_per_model,
        n_skipped_per_model=n_skipped_per_model,
        per_model_decisions=per_model_decisions,
        cross_model=cross_model,
        h1_status=h1_status,
        h1_rationale=h1_rationale,
        h2=h2,
        skipped=all_skipped,
        bootstrap_iterations=int(args.bootstrap_iterations),
        seed=int(args.seed),
        pre_reg_doc_sha=pre_reg_doc_sha,
    )
    out_md.write_text(md, encoding="utf-8")
    log(f"wrote verdict markdown -> {out_md}")

    print(json.dumps({
        "source": source,
        "h1_status": h1_status,
        "h2_status": h2["status"],
        "models_present": sorted(per_model_records.keys()),
        "models_missing": sorted(missing_models),
        "output_json": str(out_json),
        "output_md": str(out_md),
    }, indent=2))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
