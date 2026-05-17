# Monologue-length-directive verdict - AAI primary run

## 1. What this is

Pre-registered analysis of the `primary` source for the monologue-length-directive Phase 1 retrospective. Adjudicates `docs/hypotheses/2026-05-16_monologue_length_pre_registration.md` (H1, H2) on judged JSONL across 3/3 Anima models (deepseek, mistral, qwen). Bootstrap: 10,000 iterations, seed=42. Holm-Bonferroni alpha-max=0.0125 across the 4 primary tests per model. >=2/3 models per contrast required for cross-model support.

**Models missing:** (none)

Pre-registration SHA: `1496ff5cfcb16318a6a56d66e29b6cc91c90aeea7572ce6b4834cfdca9b710e8`.

## 2. Trials per model

| Model | Trials (judged, all 4 criteria) | Skipped |
|---|---:|---:|
| deepseek | 318 | 0 |
| mistral | 320 | 0 |
| qwen | 320 | 0 |

## 3. Per-contrast per-model statistics

Composite scale: 4-12 per cell (sum of rank-points across 4 persona criteria). Contrast = `composite(variable) - composite(fixed)`. Paired by `(prompt_index, trial_index)` within model.

| Contrast | Model | N_pairs | Mean diff | t | p | Holm alpha | 95% CI | Outcome |
|---|---|---:|---:|---:|---:|---:|---|---|
| H1a:variable_marcus_vs_short_marcus | deepseek | 160 | -0.406 | -1.62 | 0.1075 | 0.0125 | [-0.89, 0.08] | [x] floor-failure-null |
| H1a:variable_marcus_vs_short_marcus | mistral | 160 | 0.075 | 0.39 | 0.6949 | 0.0250 | [-0.29, 0.46] | [x] floor-failure-null |
| H1a:variable_marcus_vs_short_marcus | qwen | 160 | 1.519 | 5.47 | 1.68e-07 | 0.0125 | [0.97, 2.04] | [+] supported |
| H1b:variable_marcus_vs_long_marcus | deepseek | 160 | -0.138 | -0.58 | 0.5645 | 0.0250 | [-0.61, 0.33] | [x] floor-failure-null |
| H1b:variable_marcus_vs_long_marcus | mistral | 160 | -0.037 | -0.19 | 0.8515 | 0.0500 | [-0.42, 0.35] | [x] floor-failure-null |
| H1b:variable_marcus_vs_long_marcus | qwen | 160 | 0.487 | 1.62 | 0.1072 | 0.0500 | [-0.09, 1.08] | [x] floor-failure-null |
| H1c:variable_jamie_vs_short_jamie | deepseek | 158 | 0.006 | 0.02 | 0.9857 | 0.0500 | [-0.67, 0.69] | [x] floor-failure-null |
| H1c:variable_jamie_vs_short_jamie | mistral | 160 | 0.219 | 0.85 | 0.3975 | 0.0125 | [-0.29, 0.72] | [x] floor-failure-null |
| H1c:variable_jamie_vs_short_jamie | qwen | 160 | 1.462 | 4.01 | 9.15e-05 | 0.0167 | [0.73, 2.17] | [+] supported |
| H1d:variable_jamie_vs_long_jamie | deepseek | 158 | -0.538 | -1.60 | 0.1115 | 0.0167 | [-1.19, 0.14] | [x] wrong-direction-underpowered |
| H1d:variable_jamie_vs_long_jamie | mistral | 160 | -0.106 | -0.45 | 0.6550 | 0.0167 | [-0.57, 0.36] | [x] floor-failure-null |
| H1d:variable_jamie_vs_long_jamie | qwen | 160 | 0.787 | 2.16 | 0.0322 | 0.0250 | [0.08, 1.51] | [.] underpowered-inconclusive |

## 4. Cross-model aggregation per contrast

| Contrast | Supported on | Status |
|---|---|---|
| H1a:variable_marcus_vs_short_marcus | 1/3 (qwen) | **mixed** |
| H1b:variable_marcus_vs_long_marcus | 0/3 (-) | **falsified** |
| H1c:variable_jamie_vs_short_jamie | 1/3 (qwen) | **mixed** |
| H1d:variable_jamie_vs_long_jamie | 0/3 (-) | **falsified** |

## 5. H1 verdict

**H1 (overall) on `primary` source: PARTIALLY-SUPPORTED**

0/4 primary contrasts pass >=2/3 model support; H1 overall not elevated. Statuses: H1a:variable_marcus_vs_short_marcus=mixed, H1b:variable_marcus_vs_long_marcus=falsified, H1c:variable_jamie_vs_short_jamie=mixed, H1d:variable_jamie_vs_long_jamie=falsified

Per pre-reg §9: §13.5 LSI fresh-data run is **not** triggered. The LSI prompts remain unspent for a future experiment.

## 6. H2 verdict

**H2 (jamie-long effect-size asymmetry): FALSIFIED-NOT-LARGEST**

Jamie-long point estimate is not the largest of the four primary contrasts.

Pooled effect sizes and bootstrap 95% CIs (per-trial deltas concatenated across models):

| Contrast | N | Mean diff | 95% CI |
|---|---:|---:|---|
| H1a:variable_marcus_vs_short_marcus | 480 | 0.396 | [0.12, 0.68] |
| H1b:variable_marcus_vs_long_marcus | 480 | 0.104 | [-0.18, 0.39] |
| H1c:variable_jamie_vs_short_jamie | 478 | 0.565 | [0.18, 0.95] |
| H1d:variable_jamie_vs_long_jamie (H2 target) | 478 | 0.050 | [-0.30, 0.42] |

## 7. Skipped trials (criteria mismatch)

None.

## 8. Reproducibility

- Bootstrap iterations: **10,000**
- Random seed: **42**
- Pre-registration SHA: `1496ff5cfcb16318a6a56d66e29b6cc91c90aeea7572ce6b4834cfdca9b710e8`
- All per-contrast bootstrap seeds derived from `SHA256(seed | model | label)`; H2 pooled-bootstrap seeds derived from `SHA256(seed | 'h2-pooled' | label)`.
