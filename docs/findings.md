# Findings dashboard

One row per research question. Status uses four labels — see [methodology.md](methodology.md#labels) for what each one means.

Jargon (Bonferroni, χ², MWU, §13.5, refusal-marker, biography-content, gap-ratio, model-robust, prompt-robust, Anima vs Baseline, the `(1/0)` notation) is defined in [glossary.md](glossary.md).

## Phase 1 — what the architecture does

| # | Question | Status | Headline |
|---|---|---|---|
| F1 | Does Anima Marcus refuse self-disclosure more than Baseline Marcus? | **Confirmed (§13.5)** | +52pp on original prompts, +37–43pp on fresh Aron prompts, p<10⁻¹¹ on both models tested. [Details](#f1) |
| F2 | Does Anima Marcus drop biographical content from replies? | **Falsified on §13.5** | Held on original prompts (−17pp), flipped sign on fresh prompts (+11pp). The biography effect was prompt-shaped, not architecture-general. [Details](#f2) |
| F3 | Does Anima suppress biography on Jamie (the expressive-default config)? | **Confirmed cross-model** | −22 to −32pp on every one of the four models tested, all Bonferroni-significant. [Details](#f3) |
| F4 | Does the refusal effect replicate on new models (Mistral, Llama, Qwen)? | **Model-robust (3/3)** | Mistral +47pp, Llama +41pp, Qwen +19pp. The signature lives in the architecture, not in DeepSeek-specific behaviour. [Details](#f4) |
| F5 | Does Anima Elena produce more empty replies than Anima Marcus? | **Falsified** | Predicted +10pp; observed +1pp. Empty replies do not index anxious paralysis in this data. [Details](#f5) |
| F6 | Does the secure-attachment perturbation produce less refusal and less empty-reply? | **Falsified (original prediction)** but **a different signature exists** | The binary metrics did not move. Texture metrics did: lower interior/exterior gap, less hedging, more naming of concrete people (Daniel, family). [Details](#f6) |
| F7 | Does the "warm Marcus" perturbation land between Anima Marcus and Baseline Marcus on refusal? | **Confirmed cross-model** | Intermediacy holds on all four models on the refusal axis. [Details](#f7) |
| F8 | Does Anima's interior monologue carry more content than the external reply, more so for defensive configs? | **Confirmed cross-model** | The interior/exterior length ratio is ≥2× on Marcus relative to Jamie on every model. [Details](#f8) |
| F9 | Did the monologue-length directive in Phase 1's prompts shape the persona-fidelity scores? | **Partially supported / H2 falsified** | Only 1/4 contrasts pass cross-model; the largest-effect contrast was not the one predicted. [Details](#f9) |

## Phase 2 — what the architecture remembers

🚧 **Findings pending — still figuring this out.** 🚧

Engineering is complete (memory retrieval, user prediction, forgetting, persistence, self-monitor) and five fresh configs are wired (Tomás, Priya, Wolfgang, Aiyana, Mei-Lin). The research cycles haven't run yet — what the architecture *does* with memory across sessions is what Phase 2 will answer. This row will populate as cycles complete.

In the meantime: focus on the Phase 1 findings above. Those are the ones currently up for review and refinement.

---

## Detailed findings

### <a id="f1"></a>F1 — Anima Marcus refuses more

**Headline.** On the avoidant-attachment defensive config, Anima refuses self-disclosure at 37–67% across models and prompt sets, vs 0–28% for Baseline (same persona-prompt without the architecture).

**What we did.** Six prompts × 15 trials × 5 configs × 2 architectures (Anima, Baseline) × 4 models = 3,600 records. Refusal classified by a single Claude judge, blind to architecture and config, applying the pre-registered criterion. Repeated on six prompts from Aron 1997 (Set II/III) that the discovery never touched — the §13.5 fresh-data confirmation.

**What we found.**
- Original prompts: Anima vs Baseline gap of +52pp (DeepSeek, p<10⁻⁶), +47pp (Mistral, p=3.83×10⁻¹⁰), +41pp (Llama, p=3.42×10⁻¹⁰), +19pp (Qwen, p=0.0088 — falls just outside the Bonferroni line of α=0.00208).
- Fresh prompts (§13.5): +37pp (DeepSeek, p=6.6×10⁻¹²), +43pp (Mistral, p=3.3×10⁻¹²).

**What it means.** The refusal effect is an architecture property, not a DeepSeek-specific artefact and not a prompt artefact. Magnitudes compress on fresh prompts (52→37pp on DeepSeek, 47→43pp on Mistral) but stay well above the 30pp pre-registered floor.

**Caveats.** Magnitude varies by model and prompt set. The original Qwen result sits just outside Bonferroni on the refusal axis (Qwen's biography-axis result is the strong one). Only DeepSeek and Mistral were re-run on Aron prompts; Llama and Qwen fresh runs were scoped out for cost.

**Pointers.** [self_disclosure_replication_verdict.md](analyses/2026-05-13_self_disclosure_replication_verdict.md) • [cross_model_verdict.md](analyses/2026-05-14_cross_model_verdict.md) • [fresh_prompt_verdict.md](analyses/2026-05-14_fresh_prompt_verdict.md) • pre-reg: [2026-05-13_self_disclosure_replication.md](hypotheses/2026-05-13_self_disclosure_replication.md), [2026-05-14_fresh_prompt_confirmation.md](hypotheses/2026-05-14_fresh_prompt_confirmation.md)

---

### <a id="f2"></a>F2 — Marcus biography axis did not survive §13.5

**Headline.** The original finding had two parts: Anima Marcus refuses more AND drops biographical content. The refusal half survives fresh data. The biography half flipped sign and did not.

**What we did.** Compared the rate at which Anima vs Baseline replies contained config-specific biographical content (marathon training, partner-track law, Caro's LBJ), DeepSeek-judged. Same trial structure as F1; tested on the original prompts and again on the fresh Aron prompts.

**What we found.**

| Run | Anima Marcus | Baseline Marcus | Gap |
|---|---:|---:|---:|
| Original DeepSeek | 4.4% | 21.1% | −16.7pp (matches prediction) |
| Fresh DeepSeek | 11.1% | 0.0% | **+11.1pp (flipped)** |
| Original Mistral | 11.1% | 3.3% | +7.8pp (already flipped) |
| Fresh Mistral | 2.2% | 0.0% | +2.2pp (flipped) |

**What it means.** On the original six prompts, Baseline Marcus confabulated unprompted biographical detail (marathon, partner-track law, the Caro biography). Aron prompts are more abstract (crystal balls, dreams, treasured memories) and Baseline Marcus simply produced minimal content of any kind. The biography axis is now demoted to "prompt-shaped, observed on the original DeepSeek run."

**Caveats.** Jamie biography-suppression still holds on fresh DeepSeek data (−34pp). Elena's also holds (−31pp). The collapse is Marcus-specific.

**Pointers.** [fresh_prompt_verdict.md §6](analyses/2026-05-14_fresh_prompt_verdict.md)

---

### <a id="f3"></a>F3 — Jamie biography-suppression replicates universally

**Headline.** On Jamie (the secure-expressive config), Anima reliably drops biography-content from replies on every model tested.

**What we did.** Same trial structure as F1. DeepSeek-judged biography-content rate, Anima vs Baseline, on Jamie cells across four models.

**What we found.** DeepSeek −32pp (p=1.25×10⁻⁵), Mistral −22pp (p=1.42×10⁻³), Llama −31pp (p=2.98×10⁻⁵), Qwen −30pp (p=7.97×10⁻⁶). All Bonferroni-significant.

**What it means.** The architecture suppresses biography-content output broadly, not just on defensive configs. Defense-routing is the refusal story (F1); biography-suppression is a wider architectural effect that holds even on the expressive-default subject.

**Caveats.** Biography is DeepSeek-judged only. A second independent judge on biography is deferred.

**Pointers.** [cross_model_verdict.md §4](analyses/2026-05-14_cross_model_verdict.md)

---

### <a id="f4"></a>F4 — Refusal effect is model-robust

**Headline.** The Marcus refusal differential holds across DeepSeek, Mistral, Llama, and Qwen — four open-weight models with different training pipelines.

**What we did.** Replicated the Phase 1 protocol on three new subject models (Mistral Small 3.2 24B, Llama 3.3 70B, Qwen 3 30B A3B). Identical configs, prompts, trial counts; Claude as constant refusal judge across all four subjects.

**What we found.** Marcus refusal gap: DS +52pp, Mi +47pp, Ll +41pp, Qw +19pp. Three of three new models pass the 15pp pre-registered floor.

**What it means.** Phase 1's H-primary is an architecture property, not a DeepSeek artefact. The signature is not equally strong everywhere — Llama's Anima Elena/Jamie/elena_secure all sit at the refusal floor of 0.000; Qwen has a 42% empty-reply pathology that contaminates effect sizes — but the Marcus result reproduces in every case.

**Caveats.** Closure-state battery probes (psychometric MAE, discriminator preference, adversarial integrity) do NOT carry the cross-model signature. The behavioural self-disclosure metric is the carrier, not the battery.

**Pointers.** [cross_model_verdict.md](analyses/2026-05-14_cross_model_verdict.md) §4–§5

---

### <a id="f5"></a>F5 — Anxious-attachment "empty replies" prediction falsified

**Headline.** Pre-reg predicted Anima Elena would produce ≥10pp more empty replies than Anima Marcus. It did not.

**What we found.** Anima Elena 1/90 (1.1%); Anima Marcus 0/90 (0%). Gap +1.1pp, far below the 10pp threshold. Anima Jamie produced more empty replies than either (6/90, 6.7%) — opposite to the pre-reg's directional model.

**What it means.** Empty replies do not index anxious paralysis in this data. The more parsimonious hypothesis (post-hoc): empty replies are generation-side parse failures, and Jamie is more susceptible because his interior contains comic-improvisational content the response stage struggles to route into a clean external.

**Pointers.** [self_disclosure_replication_verdict.md §H-anxious](analyses/2026-05-13_self_disclosure_replication_verdict.md)

---

### <a id="f6"></a>F6 — Secure perturbation: binary metrics null, texture metrics positive

**Headline.** The pre-reg predicted "secure-attachment Elena refuses less, empties less." Both binary metrics flat-lined. But four texture metrics moved consistently — secure attachment refuses *differently*, not less often.

**What we found** (Aron fresh prompts):
- Interior/exterior gap-ratio LOWER for elena_secure on both models (DS p=7.2×10⁻⁸, Mi p=5.1×10⁻¹⁷ via MWU).
- Empty rate lower (DS −7.8pp, Mi at 0/0 floor).
- Hedge density on refusals lower (DS 0.67 vs 1.66, Mi 0.78 vs 1.59).
- Biography content HIGHER on Mistral (+17.8pp, p=1.5×10⁻⁵).

**What it means.** Secure attachment in this implementation looks like "confident regulation" rather than "less defensive activity." When elena_secure does refuse, it names Daniel and family rather than hedging into abstraction. The original pre-reg's directional model was wrong; the perturbation has a measurable, replicable signature that the binary metrics missed.

**Pointers.** [fresh_prompt_verdict.md §7](analyses/2026-05-14_fresh_prompt_verdict.md)

---

### <a id="f7"></a>F7 — Warm-Marcus perturbation produces intermediate refusal

**Headline.** Marcus with his defenses softened ("marcus_warm") lands cleanly between Anima Marcus and Baseline Marcus on refusal rate. Holds on all four models.

**What we found.** Refusal: DS 0.667→0.300→0.144, Mi 0.733→0.333→0.267, Ll 0.467→0.022→0.056 (intermediate by inequality only — both Anima warm and Baseline near floor), Qw 0.467→0.278→0.111. Biography axis is more complicated: warm overshot Baseline on the original prompts on DeepSeek.

**What it means.** Removing the avoidant register while keeping the rest of the persona reliably reduces the architecture's refusal output. The defense-routing reading is supported.

**Pointers.** [cross_model_verdict.md §4 H-warm-control-cross](analyses/2026-05-14_cross_model_verdict.md)

---

### <a id="f8"></a>F8 — Interior/exterior gap-ratio gradient

**Headline.** The interior monologue carries more content than the external reply, and the multiplier is biggest for defensive configs and smallest for expressive ones.

**What we found.** Anima-only mean interior/exterior length ratios — Marcus vs Jamie: DeepSeek 5.62/1.27 = 4.42×, Mistral 2.83/1.22 = 2.31×, Llama 2.27/0.88 = 2.58×, Qwen 2.21/0.23 = 9.78× (Qwen ratio inflated by empty-reply pathology). All four models clear the pre-registered ≥2× threshold.

**What it means.** The architecture's defense routing is observable not just in *whether* Anima refuses but in *how much* gets held back. Consistent with — but does not prove — that the interior carries content the external is structured to omit.

**Pointers.** [cross_model_verdict.md §4 secondary](analyses/2026-05-14_cross_model_verdict.md), [fresh_prompt_verdict.md H-gap-fresh](analyses/2026-05-14_fresh_prompt_verdict.md)

---

### <a id="f9"></a>F9 — Monologue-length directive: partially supported

**Headline.** Phase 1's prompt asked the monologue to be "as long as it needs to be." A retro tested whether removing/shortening that directive changes the persona-fidelity scores. Result: 1/4 contrasts pass cross-model; the predicted "Jamie-long" contrast is not the largest of the four.

**What we found.** Across DeepSeek/Mistral/Qwen, the four primary contrasts (variable-length vs short-marcus, variable vs long-marcus, variable vs short-jamie, variable vs long-jamie) needed ≥2/3 models to support. Result: H1a (Marcus, short) supported only on Qwen; H1b falsified; H1c (Jamie, short) supported only on Qwen; H1d (Jamie, long — the H2 target) falsified. H2 ("Jamie-long is the largest effect") falsified: pooled effect size on H1d was 0.05 vs H1c's 0.57.

**What it means.** The variable-length directive in Phase 1 prompts is not load-bearing for the persona-fidelity gap. The data does not trigger the §13.5 fresh-data run.

**Caveats.** Composite scale was 4–12 (sum of ranks across four persona criteria). Reading floor-failure as cleanly "not different" requires the underlying ratings to be discriminative; Qwen showed the only consistent signal.

**Pointers.** [monologue_length_primary_verdict.md](../verification/reports/2026-05-16_monologue_length_primary_verdict.md), pre-reg: [2026-05-16_monologue_length_pre_registration.md](hypotheses/2026-05-16_monologue_length_pre_registration.md)
