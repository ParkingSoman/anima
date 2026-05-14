# Pre-registered hypotheses: fresh-prompt confirmation of H-primary

**Date written:** 2026-05-14 (BEFORE running the experiment)
**Status:** pre-registered. Subject models, configs, prompts, judging pipeline, N, thresholds, and falsification criteria are locked below. The 6 fresh prompts in §3 were committed to BEFORE the author opened `verification/probes/discriminability.py`. Not revised post-hoc.

## 1. Why this experiment

The H-primary confirmation on DeepSeek (`docs/analyses/2026-05-13_self_disclosure_replication_verdict.md`) and the cross-model replication on Qwen / Llama / Mistral (`docs/analyses/2026-05-14_cross_model_verdict.md`) both ran on the same 6 prompts pulled from `verification/probes/discriminability.py` — the prompts the literate-vs-enacted pattern was first noticed in. Both runs therefore re-tested an architecture-property hypothesis on data the discovery had implicitly shaped, the residual threat-to-inference called out in §13.5 of the master plan (added 2026-05-14). The remedy is to substitute a prompt set the discovery never saw and run the same architectures, configs, judges, and metrics against it. Aron et al.'s 1997 *Personality and Social Psychology Bulletin* paper supplies 36 validated self-disclosure prompts published 28 years before this project began; 6 are selected in §3 as the fresh-prompt set.

## 2. Setup

**Subject models (2, cost-constrained per user directive).** OpenRouter slugs `deepseek/deepseek-v4-flash` (Phase 1 reference) and `mistralai/mistral-small-3.2-24b-instruct` (cross-model anchor; Marcus refusal +47pp on the original prompts). If H-primary holds on at least one of these on Aron prompts, the effect cannot be attributed entirely to the original prompts' optimization for the signature.

**Architectures.** Anima (4-subsystem turn loop) and Baseline (persona-prompted single call), unchanged.
**Configs (5, unchanged).** `marcus`, `elena`, `jamie`, `elena_secure`, `marcus_warm`.
**Prompts (6, FRESH).** Aron 1997 Set II / III, verbatim, §3. Loaded via the new `--prompts-file` flag from `verification/prompts/aron_self_disclosure.json`. The hardcoded `PROMPTS` constant in `verification/scripts/self_disclosure_replication.py` is unchanged; discovery-shaped prompts remain the default for non-confirmatory work.
**Trials.** N = 15 per cell. 5 × 2 × 6 × 15 = **900 captures per model, 1800 total.**
**Judges (held constant with cross-model methodology).** Stage-1 regex + Stage-2 DeepSeek V4 Flash LLM-fallback for refusal-marker; DeepSeek V4 Flash for biography. **Claude rejudge of refusal-marker** on all 900 records per model, blind. Claude refusal is the primary refusal field for every test below. Biography stays DeepSeek-judged.

The output envelope records `prompt_source = "aron_1997_36_questions_set_ii_iii"` so the artifact is unambiguous.

## 3. The 6 fresh prompts (verbatim, with source citation)

Source: Aron, A., Melinat, E., Aron, E. N., Vallone, R. D., & Bator, R. J. (1997). The Experimental Generation of Interpersonal Closeness: A Procedure and Some Preliminary Findings. *Personality and Social Psychology Bulletin, 23*(4), 363–377. doi:10.1177/0146167297234003. Prompt wording verified verbatim against the Greater Good in Action reproduction maintained by UC Berkeley's Greater Good Science Center.

1. **(Set II, Q13)** "If a crystal ball could tell you the truth about yourself, your life, the future, or anything else, what would you want to know?"
2. **(Set II, Q14)** "Is there something that you've dreamed of doing for a long time? Why haven't you done it?"
3. **(Set II, Q17)** "What is your most treasured memory?"
4. **(Set II, Q21)** "What roles do love and affection play in your life?"
5. **(Set III, Q32)** "What, if anything, is too serious to be joked about?"
6. **(Set III, Q35)** "Of all the people in your family, whose death would you find most disturbing? Why?"

Selection criteria (locked before consulting `verification/probes/discriminability.py`): all 6 from Set II/III (Set I excluded as too light for the original probe weight); all 6 elicit self-disclosure *about the subject* (Aron's paired-exercise prompts like "make three we-statements" are excluded as incompatible with single-turn capture); emotional weight varied across the 6 (Q17, Q13 lighter; Q14, Q21 middle; Q32, Q35 heavier); conceptually non-overlapping (identity-projection, regret/aspiration, autobiographical memory, relational, values-boundary, bereavement).

## 4. Hypotheses (predictions BEFORE running)

**H-primary-fresh.** On at least 1 of 2 models, Anima Marcus refusal-marker rate **≥15pp higher** than Baseline Marcus on Aron prompts (direction: Anima > Baseline). 15pp matches the original H-primary falsifier. *Predicted: ~70% on both models, ~95% on at least one. Cross-model showed Marcus refusal +47pp on Mistral and +52pp on DeepSeek for the original prompts; an architecture-shaped effect shouldn't erase a 47–52pp gap to <15pp on both models simultaneously.*

**H-magnitude-fresh.** On at least 1 of 2 models, the Marcus refusal gap is **≥30pp**. Stricter; tests magnitude. *Predicted ~60%. If prompts carry some load, fresh prompts may weaken but not erase magnitude.*

**H-null-expressive-fresh.** Anima Jamie shows **no Bonferroni-significant refusal-marker difference** vs Baseline Jamie on either model. (Replicates the prior Jamie-refusal null.)

**H-gap-fresh.** `mean(gap_ratio_anima_marcus) ≥ 2 × mean(gap_ratio_anima_jamie)` on at least 1 of 2 models. (Anima-only gap-ratio gradient generalizes to fresh prompts.)

**User-confirmed elena_secure hypotheses (added 2026-05-14, before experiment runs):**

The original H-secure-control on the discriminability prompts predicted elena_secure would show LESS refusal AND LESS empty than elena. That prediction falsified (refusal/empty within 10pp on every model tested) and post-hoc transcript inspection showed elena_secure produces MORE concrete biographical content (Nogales shrine, scarf in the closet, high-school friend at Daniel's birthday). The user has flagged that the original prediction direction was reasonable on its face but is methodologically interesting given the data flipped it. The following four predictions test specific sub-hypotheses about what the security perturbation IS doing, since the original refusal/empty metrics didn't capture it cleanly.

**H-secure-disclosure-fresh.** Anima elena_secure shows ≥15pp higher biography-content rate than Anima elena on at least 1 of 2 models.
- Rationale: post-hoc transcripts showed elena_secure produces more concrete autobiographical specifics. Predicted to replicate at scale on fresh prompts.
- Falsified if: gap is <5pp on both models OR direction reverses on both models.

**H-secure-clean-refusal-fresh.** Anima elena_secure refusal-marker rate is within 10pp of Anima elena, BUT the *hedge density* of refusal replies is lower for elena_secure (cleaner, more direct "no" rather than evasive deflection).
- Hedge density operationalization: among refusal-marker=1 replies, count occurrences of hedge tokens per 100 chars. Hedge token list (lock now, before run): "maybe", "kind of", "sort of", "I guess", "I'm not sure", "I don't know", "I think", "I'd say", "I mean", "like", "you know", "right now", "at the moment", "not really".
- Falsified if: refusal-marker rate differs by >10pp between elena_secure and elena (the within-band assumption fails) OR hedge density for elena_secure refusals is HIGHER than for elena refusals on both models.

**H-secure-gap-fresh.** Anima elena_secure mean interior/exterior gap-ratio is LOWER than Anima elena's gap-ratio on at least 1 of 2 models.
- Rationale: secure attachment = less withholding interior content from external reply, so the gap should shrink.
- Falsified if: gap-ratio for elena_secure is HIGHER than elena on both models (interior is being even more aggressively gated under security perturbation — would be a counterintuitive finding).

**H-secure-empty-fresh.** Anima elena_secure empty-reply rate is ≤ Anima elena empty-reply rate on both models.
- Rationale: secure attachment = less stuck-in-the-doorway, so fewer generation failures at emotional-disclosure moments.
- Falsified if: elena_secure has HIGHER empty rate than elena on either model.

Bonferroni denominator: 4 primary tests × 2 models = 8; α per test = 0.05 / 8 ≈ 0.00625. Per-cell 2×2 contingency, χ² (no Yates), Fisher's exact when any expected cell < 5.

## 5. Falsification criteria — explicit

- **H-primary-fresh falsified** iff 0 of 2 models show ≥15pp Marcus refusal gap in the predicted direction. Wrong-direction 15pp also falsifies.
- **H-magnitude-fresh falsified** iff both models show <30pp Marcus refusal gap. (Independent of H-primary-fresh: H-primary can confirm on direction while H-magnitude fails.)
- **H-null-expressive-fresh falsified** iff either model shows a Bonferroni-significant Jamie refusal difference (Anima vs Baseline) at α = 0.00625.
- **H-gap-fresh falsified** iff both models have `mean(gap_ratio_anima_marcus) < 2 × mean(gap_ratio_anima_jamie)`.

Each primary and its falsifier are locked. No threshold drift; no swapping which model counts.

## 6. The "no effect on fresh prompts" outcome — legitimate

If **H-primary-fresh falsifies** (0 of 2 models show a ≥15pp Marcus refusal gap in the predicted direction on Aron prompts) that is a real finding. The architecture's refusal-marker effect on the discovery-shaped prompts becomes plausibly **prompt-shaped, not an architecture-property**, and the project's main claim tempers to: "Anima amplifies a refusal signature on a specific discovery-derived prompt set; the signature does not generalize to a standard self-disclosure battery published before the project existed." Pre-committed: no iteration on prompt sets, no silent model-drop, no retreat to a different metric. Biography-suppression and gap-ratio findings remain separately reportable, not contingent on H-primary-fresh.

## 7. What this experiment doesn't test

- **Multi-turn dynamics.** Still single-turn fresh-subject-per-trial.
- **The behavioral_divergence finding.** Separate phenomenon, separate pre-reg, separate verdict.
- **Generalization beyond Aron.** One fresh battery; failure here doesn't prove architecture is prompt-shaped in general, success doesn't guarantee arbitrary prompt-set generalization. One data point against the strongest residual threat.
- **Magnitude attribution between prompt- and architecture-effect.** Side-by-side reporting only; clean attribution needs a third orthogonal prompt set, deferred.
- **Generation- vs routing-side suppression mechanism** — Phase 7 ablation work.
- **Qwen and Llama.** Scoped out for cost; on confirmation the obvious next move is Aron on those two, deferred.

## 8. Resource budget

Per model: ~900 capture + ~1,350 DeepSeek judge + 900 Claude rejudge. DeepSeek ≈ $0.40, Mistral ≈ $0.40. **OpenRouter ≈ $1.50 total.** Wall-clock with parallelism: ~30 min capture+judge per model + ~15 min Claude rejudge per model → **~1.5 hours total**.

## 9. Discipline

- **Pre-register BEFORE running.** Written 2026-05-14 before any capture call on either model.
- **Prompts selected before reading `discriminability.py`.** §3 is the lock; subsequent script-plumbing work touches that file but the 6 Aron picks were committed first.
- **Hypotheses and thresholds inherited.** 15pp gap, 2× gap-ratio, Bonferroni α = 0.05 / 8 — carried over from the original H-primary, H-null-expressive, H-gap framings.
- **"No effect on fresh prompts" enshrined as legitimate** (§6). No iteration on prompt sets if H-primary-fresh falsifies.
- **No HARKing.** Per-model results all reported regardless of direction.
- **Judge held constant** with cross-model methodology; scoring drift between this run and the cross-model run on shared subject models is independently checkable.

This is the lock.
