# Methodology

How the project judges, tests, labels, and confirms findings. This page exists so individual verdicts can stay focused on results rather than re-explaining conventions.

Definitions for jargon used here are in [glossary.md](glossary.md).

---

## <a id="elicit-first"></a>1. Hypothesis elicitation precedes pre-registration

For every research cycle: I supply my predictions **before** any pre-registration is authored. I bring domain knowledge (attachment theory, defenses, schemas) that subagents miss; eliciting my predictions first prevents pre-regs being shaped by what the model thinks will happen. The H-secure-control pre-reg got direction backwards in Phase 1 partly because elicitation was skipped — secure attachment in this implementation looks like "confident regulation" rather than "less defensive activity." That correction is now baked into protocol.

Concretely: when starting an experiment, gather my predictions in writing → draft the pre-reg → I review it → commit → run.

---

## 2. Pre-registration

Every confirmatory experiment is locked before the data is run.

- Pre-reg files live at `docs/hypotheses/YYYY-MM-DD_<topic>.md`.
- The pre-reg states: hypothesis, falsification criteria (effect size + p-value thresholds), correction family, sample size, judge choice, fresh-data plan if §13.5 applies.
- **Bodies are immutable after the run.** No post-hoc edits to body content. If a plain-English summary is added afterward, it goes in a `## Plain-English summary (post-hoc, non-binding)` section at the top, clearly labelled.

The audit-trail integrity of the §13.5 procedure depends on this.

---

## <a id="judges"></a>3. Judge selection

Phase 1 uses two LLM judges, each held constant across all cells:

- **Claude — primary refusal-marker judge.** Applied blind to architecture and config. The pre-registered pipeline was Stage-1 regex + Stage-2 DeepSeek; the regex audit found a 59% misfire rate (well above the 15% pre-committed threshold), so the pre-reg's pre-committed switch fired and **a single Claude judge re-scored all 900 records identically**. This judging is uniform across Anima and Baseline cells — the methodology did not differ per architecture. The observation that Claude's higher refusal counts concentrated on Anima cells describes what re-judging *revealed about the data*, not how the judging was performed.

- **DeepSeek — biography-content judge.** Locked pre-run. Phase 1 verdicts retain DeepSeek for biography across all four subject models so the biography metric uses a single constant judge. A re-judge of biography with Claude on a ~200-record subsample is deferred to Phase 2 (cross-model verdict §11 flags this).

The asymmetry is intentional: refusal-marker is a behavioural classification that benefits from a strong judge; biography-content is a content-trace classification where consistency across cells matters more than judge strength.

---

## <a id="section-13-5"></a>4. The §13.5 fresh-data confirmation procedure

Added to the master plan on 2026-05-14. Binding for all future phase exits.

**Why.** Effects observed on the same prompts used during model selection may be discovery-shaped — prompts where the architecture happens to behave in the predicted direction by virtue of how those prompts were chosen. §13.5 forecloses this by requiring a second pass on prompts the discovery never touched.

**Procedure.**

1. Pre-register the original hypothesis on the original prompt set.
2. Run, judge, adjudicate. If supported → effect is labeled "model-robust" / "observed on original."
3. Author a fresh-data pre-reg. Same hypothesis, same falsification thresholds, **new prompt battery** validated to exist before the project began.
4. Run on fresh prompts. Adjudicate.
5. Effects that survive both rounds → "confirmed under §13.5."
6. Effects that hold on originals but fail on fresh → "prompt-shaped, observed on original prompts" — explicitly demoted.

**First execution.** The fresh-prompt verdict (2026-05-14) ran six Aron 1997 Set II/III prompts on DeepSeek and Mistral. The Marcus refusal effect survived (+37 / +43pp, both p<10⁻¹¹). The Marcus biography axis did not (flipped sign from −17pp to +11pp). The procedure correctly separated the two clauses of the original H-primary; the project would otherwise have continued reporting both as confirmed.

---

## 5. Multiple-comparison correction

Phase 1 verdicts use **Bonferroni** widely:

- Original self-disclosure: α = 0.05 / 8 = 0.00625 (then 0.05/10 = 0.005 with `marcus_warm` added). Both flagged; verdict uses the locked α=0.00625.
- Cross-model: α = 0.05 / 24 = 0.00208 (5 configs × 2 metrics × 3 new models). The increased family is conservative — a result that's "Bonferroni ✓" cross-model is a stronger claim than the originals.
- Fresh-prompt: α = 0.05 / 8 = 0.00625 *within each model*. Two-model family, not pooled.

The monologue-length retro uses **Holm-Bonferroni** (α_max = 0.0125) as a less-conservative alternative — still controls family-wise error but does not penalise the largest-p test equally to the smallest.

Tests used:

- **χ² (no Yates correction)** for 2×2 contingencies when all expected cells ≥ 5.
- **Fisher's exact** when any expected cell < 5 or a row/column is zero.
- **Mann-Whitney U two-sided** for continuous metrics (gap-ratio, hedge density).
- **Bootstrap CI** (10,000 iterations, seed=42) for composite-scale contrasts (monologue-length).

All seeds derived from `SHA256(seed | model | label)` for per-contrast reproducibility.

---

## <a id="labels"></a>6. Status labels for findings

Findings get one of four labels in [findings.md](findings.md). Each is precise.

- **Confirmed (§13.5)** — survived both the original run AND the fresh-data pre-registered confirmation. The effect is not prompt-shaped.
- **Model-robust (k/3)** — holds on ≥2 of 3 new subject models with the same protocol. Does not by itself address prompt-shaping; needs §13.5 to graduate to "confirmed under §13.5."
- **Partial / partially confirmed** — some sub-hypotheses pass, others fail. The verdict states which.
- **Falsified** — pre-registered falsification criterion triggered. Sometimes accompanied by a "but a different signature exists" note (cf. F6, secure perturbation): the binary metric is genuinely falsified, but the perturbation does *something* the binary metric didn't capture. The falsification stands as written; the observed-but-not-predicted signature is labeled non-binding post-hoc until re-tested under §13.5.

A finding can have multiple labels across axes — e.g., F1 is "Confirmed (§13.5) on refusal axis" while F2 is "Falsified under §13.5 on biography axis" — both flowing from the same fresh-prompt run.

---

## 7. Three epistemic categories used across the project

When something is reported in any verdict, it falls into one of three categories:

- **Engineering observation** — Properties of the implementation (e.g., "the surprise computation uses 0.5 × intent_mismatch + 0.5 × (1 − jaccard)"). Verifiable by reading code or running tests. Not a research claim.
- **Exploratory observation** — Patterns spotted in data that were not pre-registered. Reported in `## Post-hoc observation, not pre-registered` blocks at the bottom of verdicts. Flagged for future pre-registration; never load-bearing in headline claims.
- **Confirmed research finding** — Effect survived a pre-registered test (and, for cross-cycle survival, §13.5). Only these may be cited in headline claims about "what the architecture does."

The README and findings.md only use confirmed-research-finding language for headline claims. Exploratory observations are tagged.

---

## 8. Sample sizing

Phase 1 cells: N=90 per (config × architecture) = 6 prompts × 15 trials. Each (config × arch × prompt) triple has 15 independent trials with different random seeds. Total N = 900 per model.

For binary metrics with a baseline rate of ~10%, N=90 per cell gives ≥80% power to detect a 15pp gap at α=0.05 (Cohen's pre-reg power table; see pre-reg §10 for derivations). Phase 1 pre-regs locked 15pp as the falsifier across all H-primary tests for this reason.

Trial seeds are deterministic in trial_index; replications can re-run from raw seeds if needed.

---

## 9. Architecture versioning

Phase 1's architecture is frozen at `anima_v1/` and `verification_v1/` (snapshot taken at the end of Phase 1). Phase 2's working directory is `anima/` and `verification/` — these are v2. When Phase 2 closes, v2 will be snapshotted to `anima_v2/`. All future writeups are written against a specific snapshot reference; the master plan §13.5 procedure binds version-locking at each phase exit.

This matters when reading Phase 1 verdicts: code paths cited in those verdicts refer to v1 file layout. The 6-step turn loop in v2 differs from the 4-step loop in v1 by the addition of memory_retrieval, user_prediction, and self_monitor.

---

## 10. What the project does NOT establish

This list lives here, once, instead of being repeated at the bottom of every verdict.

- Multi-turn conversational dynamics (Phase 1 was single-turn; Phase 2 introduces persistence).
- Generalization to frontier closed-weight models (DeepSeek/Mistral/Llama/Qwen are mid-tier open-weight; GPT-4o, Claude Opus, Gemini Ultra not tested).
- Whether biography-suppression is desirable in any normative sense.
- Real-world conversation patterns (six probes per config in Phase 1; Aron Set II/III for §13.5; not naturalistic).
- Personality dimensions outside attachment / defense (Big5 and Schwartz values are wired but Phase 1 did not test their differential expression).
- Whether the architecture's interior-monologue stage is *necessary* or merely *sufficient* for the effects (no ablation of the monologue step alone).
- Causal mechanism for biography-suppression — generation-side (response stage produces shorter externals given a long interior) vs routing-side (interior content is structured to be held back). The gap-ratio data is consistent with routing but does not prove it.
