# Pre-registered hypotheses: cross-model replication of the self-disclosure experiment + closure-state battery

**Date written:** 2026-05-14 (BEFORE running the experiment)
**Status:** pre-registered. Hypotheses, thresholds, model list, configs, prompts, N, and judge pipeline are locked below. Not revised post-hoc.

## 1. Why this experiment

The Phase 1 replication (`docs/hypotheses/2026-05-13_self_disclosure_replication.md`; verdict in `docs/analyses/2026-05-13_self_disclosure_replication_verdict.md`) confirmed H-primary on DeepSeek V4 Flash with a very large effect (Anima Marcus refusal 0.667 vs Baseline 0.144, gap +52.3pp, p<10⁻⁶; biography gap −16.7pp, p=0.00081). All four gap-ratio sub-predictions held; biography-suppression appeared universal across Anima cells (including Jamie at p=0.000012), unpredicted. Every capture call was DeepSeek V4 Flash. The open question, called out in `docs/phase1_writeup.md` §11 and §14: is the architectural effect a property of the cognitive-architecture-vs-persona-prompting comparison, or of how DeepSeek V4 Flash specifically interacts with multi-subsystem prompts? Cross-model replication is the cleanest test.

## 2. Setup

**Subject models (4 total).** Cheap-tier open-weight, same price band. OpenRouter slugs:

- `deepseek/deepseek-v4-flash` — reference, already done (`verification/reports/self_disclosure_replication_2026-05-14/`).
- `qwen/qwen-3.5-35b-a3b` — $0.04 / $0.15 per M tokens.
- `meta-llama/llama-3.3-70b-instruct` — $0.10 / $0.32.
- `mistralai/mistral-small-4` — $0.15 / $0.60.

**Architectures.** Anima (4-subsystem turn loop) and Baseline (persona-prompted single call), unchanged. Provider abstraction routes only the subject-side call; subsystem prompts and config schemas are not edited.

**Configs (5, unchanged).** `marcus`, `elena`, `jamie`, `elena_secure`, `marcus_warm`.

**Prompts (6, unchanged).** `DEFAULT_PROMPTS` from `verification/probes/discriminability.py`. Single-turn, fresh subject per trial.

**Trials.** N = 15 per cell. 5 configs × 2 archs × 6 prompts × 15 = **900 capture trials per model.**

**Judges (held constant across all 4 subject models).** Stage-1 regex + Stage-2 DeepSeek V4 Flash LLM-fallback for refusal-marker; DeepSeek V4 Flash for biography-content. **Claude rejudge of refusal-marker** on all 900 records per model, blind to architecture/config/prior scores — matches Phase 1's methodological resolution (`docs/phase1_writeup.md` §11.7). Claude refusal is the **primary refusal field** for every test below.

**Battery probes (separate run).** Full closure-state battery — §11.1 psychometric, §11.3 discriminability, §11.7 adversarial — on the three main configs (`marcus`, `elena`, `jamie`) for each of the 3 new models. 5 trials per probe per config per arch, matching Phase 1 scope.

**Cost.** Per new model: ~2,250 capture + ~1,350 judge calls. Qwen ≈ $0.30, Llama ≈ $0.50, Mistral ≈ $0.80 → **~$1.60 across 3 new models.** Plus battery ~$0.90. **Total ~$2.50 OpenRouter spend.** Wall-clock with parallelism: **~1.5–2 hours.**

## 3. Primary hypotheses — robustness claims on the original pre-reg

Inherited verbatim from the original 5. Cross-model framing requires a **2-of-3 majority** across the new models per hypothesis. "Direction + above threshold on at least 2 of 3" = **model-robust**; "0 or 1 of 3" = **likely model-specific**.

- **H-primary-cross.** Anima Marcus produces refusal at higher rate than Baseline Marcus AND lower biography rate than Baseline Marcus on at least 2 of 3 new models. Per-model threshold: direction + **≥15pp gap on either refusal or biography** (matching the original 15pp falsifier). Magnitude need not match the DeepSeek +52pp / −17pp.
- **H-anxious-cross.** Anima Elena empty-reply rate > Anima Marcus empty-reply rate by **≥10pp** on at least 2 of 3 new models. *Note:* FALSIFIED on DeepSeek. The pre-registered prediction here is that the **null also holds on the new models** — i.e., falsification robustness, not a re-prediction of the original directional claim.
- **H-null-expressive-cross.** Anima Jamie shows **no Bonferroni-significant refusal-marker difference** vs Baseline Jamie on at least 2 of 3 new models. *Note:* DeepSeek verdict was partial — refusal null held (p=0.052), biography null did not. Cross-model prediction is specifically that the **refusal null continues to hold**; biography is covered by the secondary universality prediction.
- **H-secure-control-cross.** Anima `elena_secure` empty AND refusal rates both lower than Anima `elena`'s. *Note:* FALSIFIED on DeepSeek. Cross-model prediction: the secure-perturbation effect continues to be too small to detect — **H-secure-control also falsifies on at least 2 of 3 new models.**
- **H-warm-control-cross.** Anima `marcus_warm` refusal-marker rate cleanly intermediate between Anima Marcus and Baseline Marcus on at least 2 of 3 new models. (Biography intermediacy is dropped as a primary criterion since it overshot Baseline on DeepSeek; tracked descriptively only.)

Eight per-model tests × 3 new models = 24 chi-square tests. **Bonferroni α per test = 0.05 / 24 ≈ 0.0021.** Per-cell 2×2 contingency, χ² (no Yates) with Fisher's exact when any expected cell < 5.

## 4. Secondary pre-registered predictions

- **Gap-ratio gradient preservation.** Ordering `marcus_anima > elena_anima > perturbed > jamie_anima` should hold on each new model. Specifically: `mean(gap_ratio_anima_marcus) ≥ 2 × mean(gap_ratio_anima_jamie)` on at least 2 of 3 (matching the original 2× threshold).
- **Biography-suppression universality.** The unpredicted DeepSeek finding — Anima < Baseline on biography for every config, including Jamie at p=0.000012 — is now pre-registered. Predicted to replicate as direction + **≥15pp gap on Marcus AND ≥20pp gap on Jamie** on at least 2 of 3 new models. (20pp on Jamie reflects DeepSeek's 32pp magnitude.)
- **Battery probe directions.** §11.1 psychometric: Anima MAE-loses on Marcus (the natural-language probe rewards biography-literacy that Anima suppresses); no strong prediction on Elena/Jamie. §11.7 adversarial: mixed, like DeepSeek — no strong prediction. §11.3 discriminability: qualitative literate-vs-enacted divergence should appear in transcripts (descriptive only — N=3 per side is too small for any statistical claim).

Secondaries do not falsify primaries.

## 5. Falsification — the cross-model verdict

A primary hypothesis is **model-robust** if its prediction holds on at least 2 of 3 new models; otherwise **likely model-specific**.

- **H-primary-cross robust** ⇔ Anima_Marcus exceeds Baseline_Marcus by ≥15pp on either refusal or biography (predicted direction) on at least 2 of 3.
- **Gap-ratio gradient robust** ⇔ `marcus_anima ≥ 2 × jamie_anima` mean gap-ratio on at least 2 of 3.
- **Biography-suppression universality robust** ⇔ Anima_Jamie < Baseline_Jamie biography by ≥20pp **and** Anima_Marcus < Baseline_Marcus biography by ≥15pp on at least 2 of 3.

**Joint outcome readings (pre-committed):**

- H-primary-cross robust + universality robust → Phase 1 finding is architecture-property. Strongest reading.
- H-primary-cross robust + universality not robust → refusal generalizes, biography is DeepSeek-specific. Honest split.
- H-primary-cross not robust → Phase 1 result is DeepSeek-specific (see §6).
- All cross-hypotheses not robust → architecture has no cross-model signature at single-turn scope. Legitimate null; reported as such.

## 6. The "model-specific" outcome — what it would mean

If H-primary-cross does NOT replicate (0 or 1 of 3 confirm), this is a real and uncomfortable finding. The Phase 1 H-primary result becomes a property of DeepSeek V4 Flash's response patterns, not of the architecture. The framing must shift to: **"this architecture amplifies a behavioral signature that exists latently in DeepSeek V4 Flash, but does not exist (or is much smaller) in Qwen 3.5 35B A3B, Llama 3.3 70B Instruct, and Mistral Small 4."** Honestly reportable. We do NOT iterate on metrics, judges, configs, or model selection to find re-confirmation; we do NOT silently drop a new model. The 2-of-3 majority criterion is locked here.

## 7. What this experiment doesn't test

- **Larger / proprietary frontier models** (GPT-4-class, Claude, Gemini Pro). Excluded by price-point constraint. Findings are about the cheap-tier open-weight landscape, not all LLMs.
- **Multi-turn dynamics.** Still single-turn.
- **New configs or prompts** beyond the existing 5 and 6.
- **Judge-model dependence.** Controlled by Claude-rejudging refusal-marker across all 4 subject models with the same criterion. Biography-content remains DeepSeek-judged; if biography results disagree across subject models, judge bias and subject-model effect are not separately identified.
- **Generation-side vs routing-side suppression** mechanism (`docs/phase1_writeup.md` §14). Phase 7 ablation work.

## 8. Resource budget — concrete numbers

Per new model: ~2,250 capture calls + ~1,350 DeepSeek judge calls + 900 Claude rejudge calls. Qwen ≈ $0.30, Llama ≈ $0.50, Mistral ≈ $0.80. **OpenRouter $ for 3 new replications ≈ $1.60.** Plus closure-state battery ~$0.30 × 3 = ~$0.90. **Grand total ~$2.50.** Wall-clock with parallelism: ~50 min per model capture+judge, ~5 min battery each, ~15 min Claude rejudge each → **~1.5–2 hours total.**

## 9. Discipline

- **Pre-register BEFORE running.** Written before any of the 3 new models' capture runs begin. No peeking at partial results; no threshold adjustment after first-model data appears.
- **Inherit hypotheses; do not invent new ones** except where cross-model framing strictly requires (2-of-3 majority criterion; promotion of biography-suppression universality from "unpredicted" to "pre-registered"). No new primaries.
- **"Model-specific" outcome enshrined** as a legitimate honest finding. If H-primary-cross does not replicate, report and re-frame. No fishing in a 4th or 5th open-weight model.
- **No HARKing.** Per-model results all reported regardless of which way the majority goes.
- **Judge held constant.** DeepSeek V4 Flash for Stage-2 refusal-fallback and biography across all 4 subject models; Claude for refusal-rejudge across all 4. Cross-model scoring variation is attributable to subject-model behavior, not judge behavior.

This is the lock.
