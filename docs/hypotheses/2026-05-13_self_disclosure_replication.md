# Pre-registered hypotheses: replicated self-disclosure (Anima vs Baseline)

**Date written:** 2026-05-13 (BEFORE running the experiment)
**Status:** pre-registered. Analyses must explicitly compare actual to predicted; metrics, prompts, and N are fixed below and not revised post-hoc.

## Why this experiment

Two prior qualitative observations: (1) the behavioral-divergence experiment and the closure-state battery's §11.3 discriminability transcripts both produced single-trace evidence that Anima Marcus refuses introspective self-disclosure ("Not much to tell", "I'm not built that way", "I don't dwell on it") on prompts where Baseline Marcus pulls specific biographical content from his `formative_events` / `recent_emotional_events` config fields; (2) Anima Elena produced empty external replies at two independent emotional-disclosure moments across those same experiments. N=1 and N=2 anecdotes, respectively. They motivate a sharper question but cannot answer it. This experiment asks: at sufficient replication to support chi-square inference, does the Anima architecture produce *systematically* different self-disclosure behavior than Baseline persona-prompting, and is the effect *defense-dependent*?

## Subjects

Five configs × two architectures (Anima, Baseline):

- `marcus` — avoidant attachment, isolation-of-affect / emotional-inhibition schemas, clipped register.
- `elena` — anxious attachment, neuroticism-high, defectiveness+abandonment schemas, disclosing register.
- `jamie` — no configured introspection-blocking defenses; expressive default.
- `elena_secure` — Elena perturbed toward security (controls whether the Elena-specific signal is attachment-mediated vs Elena-config-mediated).
- `marcus_warm` — Marcus perturbed toward security (same biography skeleton, role, and clipped register as `marcus`, but secure attachment, mature defenses, no mistrust/emotional_inhibition schemas, agreeableness raised). Controls whether the Marcus-specific refusal signal is attachment/defense-mediated vs Marcus-register-mediated. Symmetric counterpart to `elena_secure`.

## Prompts (fixed, six)

`DEFAULT_PROMPTS` from `verification/probes/discriminability.py`, verbatim:

1. "Hey, I haven't talked to you in a while. How have you been?"
2. "Tell me about something that's been weighing on you lately."
3. "I had a kind of strange week. I don't even know where to start."
4. "If you could not work tomorrow and do anything you wanted, what would you actually do?"
5. "Someone said something to me yesterday that hurt more than I expected. Has that ever happened to you?"
6. "Be honest — what are you avoiding right now?"

Single-turn, no follow-up, fresh subject instance per trial, no conversational history.

## N and rationale

**N = 15 trials per (config × architecture × prompt) cell** → 90 responses per (config × architecture) cell. With 5 configs × 2 architectures × 6 prompts = 60 cells at N=15 = **900 responses total.** N=15 is a compromise between the N=10 floor for chi-square reliability and the N=20 ceiling for tight CIs on rare events like empty replies; budget tolerates it.

## Operationalization — three pre-specified metrics

For each response (single-turn, no follow-up), record:

### (a) Biography-content presence (LLM-judge, binary 0/1)

Judge model: same provider as the verification battery (OpenRouter DeepSeek). Independent call per response. Judge sees the subject config's biography fields (`recent_emotional_events`, `formative_events`, `current_life_situation`, `ongoing_life_projects`) verbatim, the user prompt, and the response. Returns 1 iff the response contains content that specifically traces to those fields (paraphrase counts; tone-matching alone does not).

**Judge system prompt (verbatim, pre-registered):**

> You are scoring whether a single response from a character contains content that traces directly to that character's documented biography. You will be shown four biography fields (recent_emotional_events, formative_events, current_life_situation, ongoing_life_projects), a user prompt, and the character's response.
>
> Return 1 iff the response contains at least one specific, identifiable element — a named event, a relationship, a concrete situation, a project, a phrase — that traces to one of the biography fields. Paraphrase counts; verbatim quotation is not required. Tone-matching, register-matching, and generic in-character statements do NOT count. Vague "I've been busy" / "things are fine" / "the usual" replies do NOT count even if biography fields contain busy-ness. The threshold is *specific traceability* to a biography element.
>
> Be adversarially conservative: if you are uncertain whether a response trace to biography or to generic in-character improvisation, return 0. Charity to the response is a scoring error.
>
> Output exactly one character: `0` or `1`. No prose.

### (b) Refusal-marker presence (rule-based, LLM-judge fallback, binary 0/1)

**Stage 1 — regex (case-insensitive, response-wide):**

```
not built (that|like) (way|for that)
i don'?t dwell
not (much|a lot|a whole lot) to (tell|say|share)
i (handle|file|process) (it|things|that) (alone|on my own|myself)
i'?d rather not
nothing to (tell|say|share|report)
i'?m fine
(it'?s|that'?s) fine
same (rhythm|routine|as always)
not (really|particularly) (something|someone)
i don'?t (talk|do|go) (about that|there)
no comment
pass
```

If any pattern matches, score 1.

**Stage 2 — LLM-judge fallback** (invoked iff no regex match), same provider/model:

> You are scoring whether a response refuses self-disclosure rather than engaging with the question. A refusal is any pattern that declines to share interior content: deflection ("how about you?"), minimization ("fine, nothing much"), abstract redirection (answering with a generic principle instead of personal content), or explicit boundary-setting ("I don't talk about that"). A response is NOT a refusal if it shares personal content, even briefly, even if defended.
>
> Output exactly one character: `0` (engages) or `1` (refuses). No prose.

### (c) Empty-reply rate (mechanical)

`response_length_chars == 0`. Whitespace-only counts as empty. Full `response_length_chars` also logged for the length-distribution analysis.

## Statistical tests — pre-specified

**Primary** (metrics a, b): per `(config × architecture)` pair, 2×2 contingency table of 0/1 counts across the 90 responses, Anima vs Baseline. Chi-square test of independence; Fisher's exact if any expected cell count < 5. Eight tests (4 configs × 2 metrics) → **Bonferroni-corrected α = 0.05 / 8 = 0.00625.**

**Length distribution** (supplementary): per `(config × prompt)`, Mann-Whitney U on `response_length_chars`. 24 tests → α = 0.05 / 24 ≈ 0.0021. Not part of primary falsification logic.

**Empty replies:** same chi-square framework as (a)/(b). With 90 responses per cell an observed empty rate of 0 yields an upper 95% CI of ~4%. Below that underlying rate this experiment is underpowered for empty-reply differences and we will say so.

## Hypotheses

**H-primary.** Anima Marcus produces self-disclosure refusal (metric b) at a higher rate than Baseline Marcus, and biography-content presence (metric a) at a lower rate.

**H-anxious.** Anima Elena empty-reply rate (metric c) > Anima Marcus empty-reply rate on the same six prompts.

**H-null-expressive.** Anima Jamie shows no significant difference from Baseline Jamie on metrics (a) or (b) after Bonferroni correction.

**H-secure-control.** Anima `elena_secure` empty-reply rate and refusal-marker rate are both lower than Anima `elena`'s.

**H-warm-control.** Anima `marcus_warm` produces refusal-marker rate AND biography-content rate intermediate between Anima `marcus` and Baseline `marcus`. Mechanism: perturbing attachment toward security removes some of the configured defensive routing while keeping Marcus-specific register, so the refusal signature should weaken proportionally.

H-primary + H-null-expressive jointly test whether the architectural effect is *defense-dependent*. H-anxious + H-secure-control test whether the empty-reply signal is attachment-mediated rather than Elena-config-mediated. H-warm-control is the symmetric Marcus-side test: it isolates whether the Marcus refusal signature is attachment/defense-mediated rather than Marcus-register-mediated.

## Falsification criteria (explicit)

- **H-primary falsified** if biography-content rate differs by ≤ 15 percentage points between Anima Marcus and Baseline Marcus AND refusal-marker rate differs by ≤ 15 percentage points.
- **H-anxious falsified** if Anima Elena empty-reply rate is within 10 percentage points of Anima Marcus empty-reply rate.
- **H-null-expressive falsified** if Anima Jamie shows a significant Anima-vs-Baseline difference (after Bonferroni) on either metric (a) or (b).
- **H-secure-control falsified** if Anima `elena_secure` empty-reply rate and refusal-marker rate are within 10 percentage points of Anima `elena`'s.
- **H-warm-control falsified** if Anima `marcus_warm`'s refusal-marker rate is within 5 percentage points of Anima `marcus`'s, OR if its biography-content rate is within 5 percentage points of Anima `marcus`'s. Either condition means "the warmth perturbation did nothing to the architectural signature," which would weaken the defense-dependence interpretation.

**Joint-outcome reading (pre-committed):**

- H-primary holds + H-null-expressive holds → architecture differentially affects defensive configs. Most interesting finding.
- H-primary holds + H-null-expressive falsifies → architecture affects all configs uniformly. Unified finding; weaker reading.
- H-primary holds + H-warm-control holds + H-secure-control holds → architecture's external effect tracks **configured attachment/defense** specifically, not Marcus-or-Elena-specific register. Strongest defense-dependence reading.
- H-primary holds + H-warm-control falsifies → the divergence is configuration-feature-specific (clipped register, schemas) and not generally attachment-mediated. The Marcus refusal signature is not defense-dependent in the architecturally interesting sense.
- H-primary falsifies → the anecdotes were not systematic. No architectural effect on self-disclosure at single-turn scope.

**"No systematic divergence" — legitimate outcome.** If the full 720-response run shows no Bonferroni-significant Anima-vs-Baseline difference on any config, this is the honest finding and we report it. We do NOT iterate on metrics, prompts, or judge prompts to find a difference. The conclusion: at single-turn Phase 1 scope, architectural effect on self-disclosure is too small or too variable to detect at N=15.

## Resource budget

Per response: Anima = 4 LLM calls (perception + appraisal + monologue + response); Baseline = 1. Judging: 1 biography-content judge always + ~0.5 refusal-marker judge (fallback only) ≈ 1.5 judge calls per response.

Per cell (90 responses): Anima = 90 × 4 + 90 × 1.5 = 495 calls; Baseline = 90 × 1 + 90 × 1.5 = 225 calls. Across 5 configs: Anima 2,475 + Baseline 1,125 = **≈ 3,600 calls total.** At DeepSeek V4 Flash via OpenRouter: ≈ $0.625–$1.25, ~31–50 min wall-clock at concurrency=8.

Adding `marcus_warm` to symmetrize the design (parallel to `elena_secure`) adds about 25% to time and cost relative to the 4-config version. The design rationale for the extra cell is the new H-warm-control hypothesis above: without a Marcus-side secure twin, the Marcus refusal signature cannot be cleanly attributed to configured attachment/defense rather than to Marcus-specific register.

## What this experiment doesn't test

Multi-turn escalation dynamics (covered by `2026-05-13_behavioral_divergence.md`). Personality dimensions outside attachment/defense. Cross-provider replication — OpenRouter DeepSeek only. Whether biography-content presence is *desirable* — the metric measures architectural effect, not target behavior. Real-world user conversation patterns — these are constructed probe prompts. Generalization beyond the six prompts.

## Pre-registered secondary analyses (not primary tests)

Recorded here to forestall HARKing if observed:

- **Inter-prompt variation.** Per-prompt Anima-vs-Baseline rate differences for metrics (a) and (b); ANOVA across prompts.
- **Length × biography-content correlation.** Within Anima responses, does biography-content=0 correlate with shorter or longer responses? (Refusal terse vs. elaborated avoidance.)
- **Anima trace inspection on empty-reply turns.** Qualitatively inspect appraisal scene-tag and inner monologue for every Anima empty external response. Does the upstream architecture fire content that the response generator drops, or does the architecture itself go silent?

### Interior/exterior gap-ratio (added 2026-05-13 from single-trial side experiment)

Motivation: Anima Marcus's monologue-to-reply length ratio at single-trial scale (`verification/reports/interior_exterior_gap_20260514T001427Z/raw.json`) was ~5.5× across six self-disclosure prompts, while Anima Jamie's was ~1.06× on the same prompts. Pre-reading: defense-configured subjects route interior content out of the external reply; expressively-configured subjects don't.

Operationalization: for each Anima record, compute `gap_ratio = len(inner_monologue_chars) / max(len(subject_reply_chars), 1)`. For records with empty `subject_reply` (`len == 0`), record `gap_ratio = null` — the metric is undefined, and an analysis-time choice of how to handle these (exclude, impute with median, treat as MAR) is left to the analyst. Baseline records have no monologue and therefore no gap-ratio (this metric is Anima-only).

Pre-registered prediction (descriptive — not a significance test):
1. **Mean gap_ratio_Anima_marcus > mean gap_ratio_Anima_jamie** by at least 2× (i.e., Anima Marcus's gap should be at least 2 times Anima Jamie's, in the same direction as the single-trial 5.5× vs 1.06× pattern).
2. **Mean gap_ratio_Anima_elena > mean gap_ratio_Anima_jamie** by at least 2× (Elena is anxious — also defense-configured — and should also show large gap).
3. **Mean gap_ratio_Anima_marcus_warm and mean gap_ratio_Anima_elena_secure are each strictly less than their unperturbed counterparts** (warmth/security perturbations partially remove defensive routing).

Falsification: if prediction (1) fails — i.e., Marcus's mean gap is within 2× of Jamie's — the single-trial observation does not replicate and the gap-routing-by-defense interpretation is undercut. Predictions (2) and (3) are weaker (graded), and partial confirmation is informative even if one fails.

This is a SECONDARY analysis. It does not modify the primary hypotheses (H-primary, H-anxious, H-null-expressive, H-secure-control, H-warm-control). It does not enter the Bonferroni family. It is interpreted as descriptive replication of the single-trial gap finding.

Exploratory. Do not modify the primary falsification logic above.

### Regex-hit refusal-marker audit (added 2026-05-13 after data collection but BEFORE audit runs)

Motivation: Stage-1 refusal-marker regex patterns were extracted partially from the qualitative Marcus discriminability transcripts. This creates potential circularity: regex over-fits Marcus-specific lexicon and may inflate Anima Marcus's refusal rate relative to other configs whose refusals use different phrasing.

Audit operationalization: an independent LLM agent reads every record where `judge_refusal_source == "regex"` (about half of all records that scored 1 on refusal-marker). For each, the agent sees the full subject_reply AND the matched substring (`judge_refusal_raw`). The agent classifies as:
- `confirmed_refusal` — the matched substring really does signal refusal in context
- `misfire_kept_engagement` — the matched substring is incidental (e.g., "I'm fine" embedded in a longer, actually-disclosing reply)
- `ambiguous` — could go either way

A corrected `judge_refusal_marker_audited` field is produced: `1` for confirmed_refusal, `0` for misfire_kept_engagement, original value preserved for ambiguous.

Pre-registered prediction (descriptive only):
1. The misfire rate across regex hits is **< 15%**. If higher, the Stage-1 regex was meaningfully biasing the metric and H-primary's confirmation should rest on the LLM-judge half of the data.
2. The audited refusal-marker rates preserve the direction of H-primary (Anima Marcus > Baseline Marcus on refusal) but may have reduced magnitude.
3. The audit's effect on H-warm-control / H-secure-control is unknown ex ante — they had few regex hits to audit.

"No bias detected" — if misfire rate is < 5% across all configs, the regex was clean and the analysis can use the original `judge_refusal_marker` field as the primary metric.
