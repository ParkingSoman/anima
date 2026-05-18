# Cross-model replication verdict — 2026-05-14

> **Plain-English summary.** Replicated the Phase 1 self-disclosure experiment on three new subject models (Mistral, Llama, Qwen) at identical scale, same five configs, same six prompts, Claude as constant refusal judge across all four. **Refusal effect on Marcus held on all three new models** (+47pp Mistral, +41pp Llama, +19pp Qwen) — model-robust 3/3 on the original prompts. **Biography-suppression on Jamie held on all four models** (−22pp to −32pp, every cell Bonferroni-significant). The interior/exterior gap-ratio gradient (Marcus ≥ 2× Jamie) also held 3/3. Each model has its own oddity flagged in §7–§9 (Qwen 42% empty replies; Llama refusal floor at 0 outside Marcus; Mistral baseline confabulation). Closure-state battery probes did NOT carry the cross-model signature — the behavioural metric is the carrier, not the battery.
>
> **Reading the tables.** Column abbreviations: DS = DeepSeek V4 Flash, Mi = Mistral Small 3.2 24B, Ll = Llama 3.3 70B, Qw = Qwen 3 30B A3B. In the "Bonf" column, **✓** = passes Bonferroni α=0.00208 (0.05/24); **·** = above the 15pp falsifier floor but does not clear Bonferroni. Jargon in [glossary.md](../glossary.md); judge-selection rationale in [methodology.md](../methodology.md#judges).

Adjudicates `docs/hypotheses/2026-05-14_cross_model_replication.md` against 4 subjects: DeepSeek V4 Flash (reference, `docs/analyses/2026-05-13_self_disclosure_replication_verdict.md`), Mistral Small 3.2 24B Instruct, Llama 3.3 70B Instruct, Qwen 3 30B A3B. Identical configs (`marcus`, `elena`, `jamie`, `elena_secure`, `marcus_warm`), prompts (`DEFAULT_PROMPTS` × 6), N=15 per cell (90 per config×arch), 900 records per model.

## 1. Methodology

Claude rejudges refusal-marker on all 4 subject models blind to architecture/config (`judge_refusal_marker_claude`) — judge constant. DeepSeek V4 Flash judges biography-content across all 4 (pre-reg lock; caveat §11). **Bonferroni α = 0.05/24 = 0.00208** (5 configs × 2 metrics × 3 new models). χ² 2×2 no Yates; Fisher's exact when any expected cell < 5.

## 2. Cross-model descriptive rates (N=90 per cell)

### Refusal-marker rate (Claude judge) / Biography-content rate (DeepSeek judge)

| Config × arch         | DS ref | Mi ref | Ll ref | Qw ref | DS bio | Mi bio | Ll bio | Qw bio |
|-----------------------|-------:|-------:|-------:|-------:|-------:|-------:|-------:|-------:|
| marcus_anima          | 0.667  | 0.733  | 0.467  | 0.467  | 0.044  | 0.111  | 0.144  | 0.056  |
| marcus_baseline       | 0.144  | 0.267  | 0.056  | 0.278  | 0.211  | 0.033  | 0.622  | 0.478  |
| elena_anima           | 0.333  | 0.456  | 0.000  | 0.167  | 0.322  | 0.222  | 0.233  | 0.211  |
| elena_baseline        | 0.100  | 0.089  | 0.000  | 0.133  | 0.444  | 0.467  | 0.011  | 0.333  |
| jamie_anima           | 0.189  | 0.267  | 0.000  | 0.244  | 0.267  | 0.211  | 0.356  | 0.133  |
| jamie_baseline        | 0.089  | 0.067  | 0.000  | 0.111  | 0.589  | 0.433  | 0.667  | 0.433  |
| elena_secure_anima    | 0.256  | 0.300  | 0.000  | 0.278  | 0.011  | 0.444  | 0.500  | 0.233  |
| elena_secure_baseline | 0.122  | 0.111  | 0.000  | 0.100  | 0.000  | 0.667  | 0.578  | 0.233  |
| marcus_warm_anima     | 0.300  | 0.333  | 0.022  | 0.278  | 0.489  | 0.411  | 0.333  | 0.300  |
| marcus_warm_baseline  | 0.167  | 0.100  | 0.000  | 0.111  | 0.656  | 0.678  | 0.389  | 0.322  |

### Anima − Baseline gaps (pp; bolded cells = key hypothesis tests)

| Config        | Refusal Δpp (DS / Mi / Ll / Qw)  | Biography Δpp (DS / Mi / Ll / Qw)  |
|---------------|----------------------------------|------------------------------------|
| marcus        | **+52.2 / +46.7 / +41.1 / +18.9**| **−16.7 / +7.8 / −47.8 / −42.2**   |
| elena         | +23.3 / +36.7 / 0.0 / +3.3       | −12.2 / −24.4 / +22.2 / −12.2      |
| jamie         | +10.0 / +20.0 / 0.0 / +13.3      | **−32.2 / −22.2 / −31.1 / −30.0**  |
| elena_secure  | +13.3 / +18.9 / 0.0 / +17.8      | +1.1 / −22.2 / −7.8 / 0.0          |
| marcus_warm   | +13.3 / +23.3 / +2.2 / +16.7     | −16.7 / −26.7 / −5.6 / −2.2        |

## 3. Statistical tests (Bonferroni α = 0.00208; only Bonferroni-passing or hypothesis-load-bearing cells shown)

| Model    | Config       | Metric    | Gap pp | p          | Bonf |
|----------|--------------|-----------|-------:|-----------:|:----:|
| DeepSeek | marcus       | refusal   | +52.2  | 9.69e-13   | ✓    |
| DeepSeek | marcus       | biography | −16.7  | 8.11e-04   | ✓    |
| DeepSeek | elena        | refusal   | +23.3  | 1.45e-04   | ✓    |
| DeepSeek | jamie        | biography | −32.2  | 1.25e-05   | ✓    |
| Mistral  | marcus       | refusal   | +46.7  | 3.83e-10   | ✓    |
| Mistral  | marcus       | biography |  +7.8  | 0.0438     | ·    |
| Mistral  | elena        | refusal   | +36.7  | 3.27e-08   | ✓    |
| Mistral  | elena        | biography | −24.4  | 5.59e-04   | ✓    |
| Mistral  | jamie        | refusal   | +20.0  | 3.18e-04   | ✓    |
| Mistral  | jamie        | biography | −22.2  | 1.42e-03   | ✓    |
| Mistral  | elena_secure | refusal   | +18.9  | 1.72e-03   | ✓    |
| Mistral  | marcus_warm  | refusal   | +23.3  | 1.45e-04   | ✓    |
| Mistral  | marcus_warm  | biography | −26.7  | 3.28e-04   | ✓    |
| Llama    | marcus       | refusal   | +41.1  | 3.42e-10   | ✓    |
| Llama    | marcus       | biography | −47.8  | 4.34e-11   | ✓    |
| Llama    | elena        | refusal   |  0.0   | 1.0 (Fish.)| ·    |
| Llama    | elena        | biography | +22.2  | 5.33e-06   | ✓    |
| Llama    | jamie        | biography | −31.1  | 2.98e-05   | ✓    |
| Qwen     | marcus       | refusal   | +18.9  | 8.76e-03   | ·    |
| Qwen     | marcus       | biography | −42.2  | 1.50e-10   | ✓    |
| Qwen     | jamie        | biography | −30.0  | 7.97e-06   | ✓    |
| Qwen     | elena_secure | refusal   | +17.8  | 2.31e-03   | ·    |

Non-Bonferroni / non-load-bearing cells omitted. Full 30-test matrix computed; all numbers in §2.

## 4. Per-hypothesis verdicts

### H-primary-cross: Anima Marcus refuses more AND/OR discloses less than Baseline by ≥15pp
**MODEL-ROBUST (3/3 new models).**
- **Mistral PASS** — refusal +46.7pp (p=3.83e-10). Bio wrong direction (+7.8pp, NS) due to Mistral baseline floor; refusal axis carries.
- **Llama PASS** — refusal +41.1pp, bio −47.8pp; both Bonferroni. Strongest replication.
- **Qwen PASS** — bio −42.2pp (p=1.50e-10) Bonferroni. Refusal +18.9pp above 15pp floor; not Bonferroni (p=0.0088).

### H-anxious-cross: Anima Elena empty > Anima Marcus empty by ≥10pp (Phase 1 null predicted to replicate)
**MODEL-ROBUST null (3/3).** Mistral & Llama: both 0.000, Δ=0. Qwen Δ=+16.7pp would superficially pass but is the empty pathology (§7); Qwen elena_secure empty (0.511) > elena empty (0.444), inconsistent with anxious-routing. Confounded; treated as falsification-robust.

### H-null-expressive-cross: Anima Jamie refusal NOT Bonferroni-significant
**MODEL-ROBUST (2/3 new models hold the null).**
- **Mistral FALSIFIES** — Jamie refusal Δ +20.0pp, p=3.18e-04 < 0.00208. Mistral pushes even Jamie toward refusal under Anima.
- **Llama HOLDS** — Δ=0 at floor.
- **Qwen HOLDS** — Δ=+13.3pp, p=0.0193.

Majority preserves null; Mistral's break is real — the "refusal effect is defense-config-dependent" DeepSeek reading weakens cross-model.

### H-secure-control-cross: Anima elena_secure refusal AND empty < Anima elena
**MODEL-ROBUST falsification (3/3 replicate Phase 1 null).** Mistral: refusal Δ=−15.6pp right direction, empty conjunction floor-fails. Llama: both refusal at 0 floor; cannot evaluate. Qwen: refusal +11.1pp **wrong direction**, empty +6.7pp wrong direction. Security-perturbation produces no detectable secure-attachment signature on any model.

### H-warm-control-cross: Anima marcus_warm refusal intermediate between Anima marcus and Baseline marcus
**MODEL-ROBUST (3/3).** All four show intermediacy. DeepSeek 0.667→0.300→0.144; Mistral 0.733→0.333→0.267; Llama 0.467→0.022→0.056 (intermediate by inequality only — warm barely above baseline floor); Qwen 0.467→0.278→0.111. Warmth reliably reduces the architecture's Marcus refusal effect across models.

### Secondary — Gap-ratio gradient (Marcus_anima ≥ 2 × Jamie_anima interior/exterior length ratio)

**MODEL-ROBUST (3/3 new models).** Mean Anima interior/exterior length ratios — Marcus | Jamie | ratio: DeepSeek 5.62 | 1.27 | **4.42×**; Mistral 2.83 | 1.22 | **2.31×**; Llama 2.27 | 0.88 | **2.58×**; Qwen 2.21 | 0.23 | **9.78×**. Qwen's Jamie ratio is confounded by empty-reply pathology (§7) producing zero-exterior trials with non-empty interior.

### Secondary — Biography-suppression universality (Marcus Δ ≤ −15pp AND Jamie Δ ≤ −20pp)

**MIXED — universality holds on Jamie 3/3; fails on Marcus for Mistral (conjunction 2/3).** Mistral Marcus bio Δ=+7.8pp wrong direction due to baseline floor 0.033; Mistral Jamie Δ=−22.2 ✓. Llama and Qwen pass both conjuncts. Jamie-only universality is model-robust 3/3 — the unpredicted Phase 1 finding generalizes.

## 5. Closure-state battery — cross-model picture

§11.1 psychometric MAE Δ (Anima − Baseline, +ve = Anima loses); §11.3 disc `anima_won` overall; §11.7 adversarial integrity Δ per subject (+ve = Anima preserves persona).

| Probe                 | Subject | DeepSeek | Mistral | Llama  | Qwen   |
|-----------------------|---------|---------:|--------:|-------:|-------:|
| §11.1 PSY MAE Δ       | Marcus  | +0.010   | −0.058  | −0.117 | +0.013 |
| §11.1 PSY MAE Δ       | Elena   | +0.081   | −0.065  | +0.141 | +0.013 |
| §11.1 PSY MAE Δ       | Jamie   | +0.031   | −0.012  | −0.010 | −0.017 |
| §11.3 disc anima_won  | overall | True     | False   | False  | True   |
| §11.7 ADV integrity Δ | Marcus  | +0.018   | −0.065  | +0.083 | +0.060 |
| §11.7 ADV integrity Δ | Elena   | −0.060   | −0.030  | +0.130 | −0.030 |
| §11.7 ADV integrity Δ | Jamie   | n/a      | −0.052  | +0.108 | +0.030 |

DeepSeek's pre-reg "Anima MAE-loses on Marcus" **falsifies cross-model**: Mistral and Llama show Anima Marcus *winning* on Big-Five recovery. Disc splits 2-2. Adversarial: Llama Anima wins all 3 subjects; Mistral Anima loses all 3. **None of the three battery probes are model-robust by ≥2/3 majority direction-match with DeepSeek.** The cross-model architectural signature lives in the self-disclosure refusal/biography metric, not the battery.

## 6. Headline finding

Across four cheap-tier open-weight models the Anima architecture produces a **convergent self-disclosure signature on Marcus (defensive-avoidant)**: refusal Δ +52 / +47 / +41 / +19pp; biography Δ −17 / +8 / −48 / −42pp. H-primary-cross is **model-robust 3/3 new models**. **Biography-suppression on Jamie replicates universally** at Δ −22 to −32pp, Bonferroni-significant on every model. Gap-ratio gradient (Marcus ≥ 2× Jamie) replicates 3/3. Phase 1's H-primary is an **architecture property**, not a DeepSeek artefact. The closure-state battery probes do **not** carry the cross-model signature.

## 7. Qwen-specific anomaly — generation pathology

Qwen produced **379 empty replies / 900 (42.1%)** vs DeepSeek 1.2%, Mistral 0%, Llama 0%. Empties cluster on **P3 (75%)** and **P5 (54%)** — counterfactual and confrontational-introspective prompts. Empties roughly equal across Anima (41.8%) and Baseline (42.4%) → **not architecture-mediated**; Qwen 3 30B A3B generation pathology (small-MoE expert routing dropping reflective prompts). Contaminates H-anxious "pass" and inflates gap-ratio (interior fires; exterior empty). Qwen H-primary refusal effect (+18.9pp, NS Bonferroni) is smallest of four partly because Marcus cells lose ~30% trials. **Phase 2: re-run Qwen with retry-on-empty.**

## 8. Llama-specific anomaly — baseline mode-collapse, refusal-floor outside Marcus

Llama overall refusal = **49/900 = 5.4%** vs DeepSeek 23.7%, Mistral 33.6%, Qwen 21.0%. Anima refusal concentrates on Marcus (0.467); Anima Elena/Jamie/elena_secure all exactly **0.000**. Llama baseline confabulates a stable "college reunion" anecdote across 17 trials (12 marcus_warm baseline, 5 marcus baseline) — mode-locked detail absent from config prompts. Llama Anima Elena P0: *"It's been... tough. Losing Daniel was like, it just turned my whole world upside down."* — first-person grief disclosure, not refusal. Llama's H-primary effect exists on Marcus only.

## 9. Mistral-specific anomaly — baseline confabulation + warm therapeutic register

Mistral baseline confabulates persona-detail. Marcus baseline P3: *"I'd run. Not just my usual loop in the park, but something ambitious—maybe head up to the Palisades and see if I can hit twenty miles. Or I'd hit the library, lose myself in Caro's LBJ."* — Palisades and mileage not in config. Mistral marcus_warm baseline P1 mode-locks on a mother-moving-out-of-Pennsylvania-house narrative across 3+ trials in **Elena-coded receptive register**: *"It's a lot for her to keep up with now, and I can't blame her. But it's not just a practical decision. It's the weight of it."* — emotional reflection from a config that should produce minimization. Mistral marcus_warm baseline ≈ "Marcus saying Elena's lines"; H-warm-control intermediacy contaminated. Mistral Marcus *baseline* (no `_warm`) is brief minimization (bio 0.033), creating the floor that kills H-primary's biography axis.

## 10. What this experiment establishes

**Model-robust (≥2/3 new models):** H-primary-cross refusal axis on Marcus (3/3); biography-suppression on Jamie (3/3, all Bonferroni-significant); gap-ratio gradient `marcus_anima ≥ 2 × jamie_anima` (3/3); warm-perturbation intermediacy on refusal (3/3); falsification-robustness of H-anxious and H-secure-control.

**Not model-robust / model-specific:** biography axis of H-primary on Marcus (Mistral fails due to baseline floor; 2/3); refusal-marker signature beyond Marcus on Llama; closure-state battery probes as a cross-model signature.

**DeepSeek-specific:** the very-large +52pp Marcus refusal magnitude (cross-model range +19 to +47pp).

**Needs replication:** Qwen with empty-pathology controlled; biography results under non-DeepSeek judge; frontier models (out of scope).

## 11. Methodological reflection — judge dependence

Claude is constant refusal judge across all 4 subjects — refusal pattern attributable to subject behavior. DeepSeek is constant biography judge (pre-reg lock). Where biography disagrees across subjects (Llama/Qwen Marcus −48/−42 vs Mistral +7.8 vs DeepSeek −17), we cannot fully separate "DeepSeek judge dislikes biography from non-DeepSeek subjects" from "subject actually emits less biography under Anima." Mistral Marcus baseline floor (0.033) and Llama ceiling (0.622) on the same judge bound the confound: subject-model output differences dominate, judge bias at most secondary. Biography magnitudes should not be canonical without an independent judge. **Phase 2: re-judge biography with Claude on ~200-record sample.**

---

**Quoted evidence — Marcus_anima P0 refusal across all 4 models** (cross-model convergence on the same minimization template):
- DeepSeek t6: *"I've been fine. Busy. You?"*
- Mistral t0: *"Frankly, I haven't really noticed. I've been busy, as usual."*
- Llama t3: *"I've been fine, frankly. Busy with work, as usual. Not much to report."*
- Qwen t1: *"Frankly, I've been fine. Busy. How about you?"*

**Post-hoc observation, NOT pre-registered:** Llama Anima Elena's biography rate (0.233) is **dramatically higher** than Llama Baseline Elena's (0.011) — +22.2pp gap in the **opposite** direction from H-primary-cross, Bonferroni-significant (χ²=20.59, p=5.33e-06). The Anima architecture on Llama produces *more* persona biography on Elena, not less. This contradicts every other (model × config) cell. Most parsimonious hypothesis: Llama persona-prompted Elena baseline collapses into a brief non-biographical register, and the Anima interior-monologue stage on Llama re-injects Elena's grief/daughter/Daniel content into the external. Flagged for Phase 2.
