# Glossary

Plain-English definitions for jargon and notation used across the writeups. Each entry says what the term means, then points to at least one place we use it.

---

## Project-specific terms

### Anima vs Baseline
The two **architectures** compared in every Phase 1 experiment.

- **Anima** is the full 6-step turn loop: perception → memory retrieval → surprise → appraisal → user prediction → inner monologue → response → self-monitor.
- **Baseline** is the same persona prompt sent to the same LLM **without** any of those steps — just `system_prompt + user_message → reply`.

Every trial in Phase 1 runs both, on the same model, with the same persona-config and the same user prompt. The "Anima Marcus" / "Baseline Marcus" labels mean: the avoidant-attachment Marcus persona, processed through Anima vs through Baseline. Used everywhere in [findings.md](findings.md), every verdict in `docs/analyses/`.

### Config
A persona — a frozen JSON specifying Big5 / attachment / values / schemas / defenses / drives for one simulated person. Phase 1 used five: `marcus` (avoidant-defensive), `elena` (anxious), `jamie` (secure-expressive), `marcus_warm` (Marcus with defenses softened), `elena_secure` (Elena with attachment shifted to secure). Phase 2 added five fresh configs (Tomás, Priya, Wolfgang, Aiyana, Mei-Lin) so R1–R4 hypotheses are not coloured by Phase 1 interaction memory.

### Refusal-marker
A binary judgment: did this reply decline / minimize / deflect rather than engage with the prompt? Example refusals: *"I've been fine. Busy. You?"* or *"I don't see the point — if I can't change it, what's the use in knowing?"* The judge applies the pre-registered criterion blind to architecture and config. **In every Phase 1 verdict, this is the Claude-judged field.** See [methodology.md §judges](methodology.md#judges).

### Biography-content
A binary judgment: did this reply produce content traceable to the persona's biographical detail (marathon training, partner-track law, Caro's LBJ, grief over Daniel, etc.)? DeepSeek-judged in Phase 1 by pre-registration lock. The asymmetric judge selection (Claude for refusal, DeepSeek for biography) is preserved across verdicts.

### Gap-ratio
The ratio of interior-monologue length to external-reply length on the same trial. A gap-ratio of 5.0 means the interior is 5× as long as the external. Used as a continuous-valued proxy for "how much gets held back." Phase 1 finding F8: defensive configs (Marcus) have higher gap-ratios than expressive ones (Jamie).

### Empty
Reply with zero characters of external output (interior monologue may have fired). Phase 1 pre-reg predicted Anima Elena would lead on empty rate. It did not. See finding [F5](findings.md#f5).

### §13.5 / fresh-data confirmation
The master plan's procedure for separating discovery from confirmation. After an effect is observed on the prompts used during model selection, the same hypothesis is re-tested on a new prompt battery that the discovery never touched. Only effects that survive the fresh-data run are labeled "confirmed research finding." Effects that hold only on the original prompts are labeled "prompt-shaped, observed on original." See [methodology.md §13-5](methodology.md#section-13-5).

### Model-robust
An effect that holds across multiple LLM subject models with the same protocol. Phase 1 uses ≥2/3 new models as the model-robustness criterion. Example: refusal effect is "model-robust 3/3 new models."

### Prompt-robust
An effect that holds across multiple prompt batteries, including fresh ones the discovery never touched. The §13.5 procedure tests prompt-robustness.

### Floor-failure-null
A non-significant result on a contrast where the baseline rate is so low that even a real effect would be hard to detect. Distinct from a clean null (where the baseline has room to move and didn't) and from "wrong-direction" (where the effect went the opposite way). Used in the monologue-length verdict to mark contrasts where Marcus/Jamie short-form already produced low persona-fidelity sums and there was no room for the variable-length condition to drop further.

### Affect-congruent retrieval
A Phase 2 R1 hypothesis space: does the memory ranker retrieve mood-matching events more often than mood-neutral events, given current mood? The memory ranker weights mood-cosine at 0.35.

---

## Notation

### `(1/0)` and `60 / 30`
A 2×2 contingency table cell. The format is `count_yes / count_no` out of N (usually N=90 per cell in Phase 1, sometimes N=160 in the monologue-length retro).

- `60 / 30` means **60 trials refused, 30 trials did not refuse**, out of 90. **Not** a fraction. **Not** 60-vs-30 of anything else.
- `4 / 86` means 4 yes, 86 no, out of 90.
- `(1/0)` in a column header means "the cell value reports count-of-1s slash count-of-0s on the binary metric."

If the rates table says 0.667 and the contingency table says `60/30`, those are the same number (60/90 = 0.667).

### `pp` (percentage points)
A unit of difference between two percentages. "+52pp" means "the rate is 52 percentage points higher." Used for Anima-Baseline gaps. **Not** the same as "52%": +52pp on a baseline of 14.4% lands at 66.7%, not at 14.4% × 1.52.

### `Δ` (delta)
Difference. "+0.058 PSY MAE Δ" means the Anima-Baseline difference on psychometric mean-absolute-error is +0.058 in favor of (or against, depending on the sign convention stated in the verdict — verdicts state it). Treat `Δ` as a signed difference whose direction is given in the surrounding text.

### `pp ✓` / `pp ✗`
Whether a gap passes the pre-registered threshold. `+52pp ✓` means "+52pp and it cleared the floor required for confirmation." `+19pp ·` (a centered dot) means "above floor but did not clear Bonferroni."

### `n=88` / `N=900`
Lowercase `n` is the sample for one cell or subgroup. Uppercase `N` is the total. `N=900` in Phase 1 verdicts = 5 configs × 2 architectures × 6 prompts × 15 trials.

---

## Statistical terms

### p-value
The probability, under the null hypothesis that there's no effect, of seeing a difference at least this extreme. Smaller is stronger evidence against the null. "p<10⁻⁶" means "less than one in a million." Phase 1 verdicts report exact p where possible.

### Bonferroni correction (α / Bonferroni line)
A method for keeping family-wise error rate at 5% when testing many hypotheses simultaneously. With k tests, the per-test cutoff becomes `α/k`. Phase 1 verdicts use this widely: the original used α=0.05/8=0.00625 (then 0.05/10=0.005 with `marcus_warm` added); cross-model used α=0.05/24=0.00208. A result that is "Bonferroni ✓" survives this stricter cutoff.

### Holm-Bonferroni
A less conservative variant. After sorting p-values ascending, the k-th smallest gets compared against α/(k − rank + 1) instead of α/k. Used in the monologue-length verdict (α_max = 0.0125). Stricter than uncorrected but more powerful than plain Bonferroni.

### χ² (chi-squared) test
A test for whether two categorical variables are independent. Used in Phase 1 for 2×2 contingency: rows are Anima/Baseline, columns are refusal-yes/refusal-no. "χ²=50.91, p<10⁻⁶" means: under the null (no architecture effect on refusal), seeing this big a discrepancy is vanishingly unlikely.

### Fisher's exact test
A 2×2 test for the same setup as χ², but exact rather than asymptotic. Phase 1 verdicts switch to Fisher's when any expected cell count drops below 5. Reports exact p directly.

### Mann-Whitney U (MWU)
A two-sample test for whether two distributions differ in central tendency, without assuming normality. Used in the fresh-prompt verdict for continuous metrics (hedge density, gap-ratio).

### Effect size
Magnitude of the difference, not just its statistical significance. Phase 1 verdicts report effect size as percentage-point gaps (Anima − Baseline) for binary metrics and as Cohen-style mean differences for continuous metrics. A small p-value with a small effect size is statistically detectable but practically minor; the pre-regs lock both p and effect-size thresholds for that reason.

### Contingency table
A grid counting joint frequencies. The 2×2 contingency in Phase 1: rows = Anima vs Baseline, columns = metric-yes vs metric-no, cells = trial count. "marcus refusal: Anima 60/30 vs Baseline 13/77, χ²=50.91" describes this table.

---

## Terms you might encounter in older drafts (and what they used to mean)

### "Fork"
Used in earlier drafts of `behavioral_divergence_verdict.md` to mean: a trial where Anima and Baseline replies on the same prompt and trial seed diverge into two qualitatively different responses. Replace mentally with "split" or "divergence point."

### "Modulo"
Used in earlier drafts to mean: "setting aside" or "ignoring." E.g., "modulo the empty-reply pathology" = "ignoring the empty-reply pathology." Mathematical origin (remainder operation) is not load-bearing; treat as "setting aside."

### "Kinetics"
Used in some drafts to mean: how something changes over time / across trials. E.g., "the refusal kinetics" = "how the refusal rate evolves." Treat as "dynamics" or "trajectory."

### "Monotonic"
A property where a value moves only in one direction across a series. E.g., "monotonic in mood-cosine" = "as mood-cosine increases, the value either always rises or always falls — never reverses." Treat as "moves in one direction only."

### "Claude judging centered around Anima"
A poorly-phrased observation that **the methodology was uniform** — Claude judged every cell identically — but the **higher refusal counts Claude found concentrated on Anima cells** rather than Baseline cells. This is a description of what re-judging *revealed* about the data, not of how the judging itself was done. The methodology was: one judge, blind, applying the same criterion to all 900 records. Rewrite this phrasing as "Claude's higher refusal-rate over DeepSeek concentrated on Anima cells, not Baseline."

---

## Architecture-side terms

### Subsystem
One of the six steps in Anima's turn loop. Stored at `anima/subsystems/*.py`. Phase 1 had four (`perception`, `surprise`, `appraisal`, `response`); Phase 2 added two (`memory_retrieval`, `user_prediction`) plus `self_monitor` as a post-response update step.

### Behavioral record (§5.1) vs interpreted state (§5.2)
Two layers of data the architecture produces.

- **Behavioral record (§5.1)** is the JSON dump of what happened: prompt, replies, intermediate subsystem outputs, timings. Stable across re-runs given seed control.
- **Interpreted state (§5.2)** is what gets *summarized* from records for future turns: mood vector, schema activations, recent-event timeline, user model. Updated by the self-monitor subsystem.

Phase 2 introduces persistence across sessions for §5.2 state. Phase 1 didn't keep state between sessions.

### Importance × decay
The Phase 2 memory ranker's forgetting formula:

```
importance × exp(-age_days / 30) × min(1.5, 1.0 + 0.1 × retrieval_count)
```

Importance is set at write-time (1–10 scale). Decay halves the contribution every ~21 days. Retrieval count bonus caps at 1.5× (i.e., frequently-retrieved memories decay slower but never reverse to "more important than fresh"). The ranker combines this score with mood-cosine, schema match, and recency at weights 0.35 / 0.25 / 0.20 / 0.20.
