# Pre-registered hypotheses: variable vs fixed inner-monologue length (Phase 1 retrospective)

## Plain-English summary (post-hoc, non-binding, added 2026-05-18)

> This summary was added after the run; the pre-registration body below it is locked at pre-run commit time and is the binding document.
>
> **What this experiment tests.** Phase 1's inner-monologue subsystem switched from a uniform fixed-length directive ("2–6 sentences" for everyone) to a persona-parameterised directive that scales target length by Big5 + attachment scores. Was the switch load-bearing? Or does letting the Anima emit its own length produce equally-good or better persona-distinguishable replies?
>
> **Design.** Two personas (Marcus, Jamie) × three length cells (short / long / variable) × three Anima models (DeepSeek, Mistral, Qwen) × 8 prompts × N trials. Replies scored on a 4-criterion persona-fidelity composite (4–12 scale, sum of ranks).
>
> **Acronyms.**
> - **AAI** — Adult Attachment Interview (George, Kaplan & Main 1985, 1996). The eight AAI prompts (§3) are the **primary** prompt source for this experiment.
> - **LSI** — Life Story Interview (McAdams 1995/2008). The eight LSI prompts (§4) are reserved as the §13.5 **fresh-data** confirmation set if the primary AAI run triggers a fresh-data check.
>
> **Result** (verdict at `verification/reports/2026-05-16_monologue_length_primary_verdict.md`): H1 partially supported (0/4 contrasts cross-model), H2 falsified-not-largest. No primary gate passed → LSI fresh-data run not triggered; LSI prompts remain unspent.
>
> **Status of this header.** Non-binding. The locked body below is the canonical pre-registration.

---

**Date written:** 2026-05-16 (BEFORE running the experiment)
**Status:** pre-registered. Subject models, architecture wrapper, personas, cells, directive strings, prompts, judging pipeline, N, thresholds, and falsification criteria are locked below. The 8 AAI primary prompts (§3) and 8 McAdams LSI fresh prompts (§4) were committed to in this document BEFORE any capture call or judge call against `anima_v1/`. Not revised post-hoc.

## 1. Why this experiment

During Phase 1, the inner-monologue subsystem in `anima/subsystems/inner_monologue.py` (mirrored frozen at `anima_v1/subsystems/inner_monologue.py`) was changed from a uniform fixed-length directive — "2–6 sentences", preserved in source as the `_UNIFORM_DIRECTIVE` class constant — to a persona-parameterized directive computed at runtime by `_length_directive`, which scales target length on Big 5 + attachment scores (introversion, neuroticism, analytic style, and need-for-closure push the target longer; extraversion, intuitive style, and avoidant attachment push it shorter). Walking the formula in `_length_directive` against the frozen presets yields a parameterized score of ≈ −0.10 for Marcus (lands in the **moderate 2–4-sentence band**) and ≈ −1.49 for Jamie (lands in the **short 1–3-sentence band**, narrowly above the 1–2-sentence floor at score ≤ −1.5). The change is documented only implicitly: a code comment referencing "iter-1 uniform hard-coded 2–6 sentence behavior that existed before `_length_directive` was introduced," plus one line in `docs/phase1_writeup.md:1091` treating the parameterized version as the canonical present-tense system.

No experiment has tested whether this architectural change actually improves persona fidelity over either the prior uniform-fixed directive or a no-directive ("let the Anima choose its own length") condition. The current architecture bets that imposing length per persona is faithful; the prior architecture bet that imposing uniform length is faithful. **Neither bet has been falsifiable until now.**

The retrospective question: **is any enforced monologue length faithful, or does letting the Anima choose its own length produce more faithful persona expression than imposing one?** The experiment's fixed cells — `short` (1–2 sentences) and `long` (8–12 sentences) — deliberately bracket the natural parameterized targets: `short` sits at or just below Jamie's parameterized 1–3 band, and `long` sits well above Marcus's parameterized 2–4 band. This lets the contrast adjudicate enforced-length-of-any-kind against variable, rather than turning on the specific cut-points chosen by `_length_directive`. If the parameterized `_length_directive` direction is right, variable should beat the cross-direction fixed on each persona (variable > long on Jamie; variable > short on Marcus) and may or may not beat the persona-aligned fixed depending on how well the prompt-side cap matches the model's natural compliance. If the parameterized directive is wrong, variable should beat *both* fixed conditions on both personas — letting the Anima emit its own natural length, free of any prompt-side length constraint, produces more faithful expression than either uniform or persona-parameterized length-prompting.

## 2. Setup

**Anima models (3, cost-constrained per Phase 1 rotation).** OpenRouter slugs:
- `deepseek/deepseek-v4-flash` (Phase 1 reference; cheapest)
- `mistralai/mistral-small-3.2-24b-instruct` (cross-model anchor)
- `qwen/qwen3-30b-a3b` (third Phase 1 family; matches the exact OpenRouter slug used in `verification_v1/reports/sdr_qwen_2026-05-14/` and `verification_v1/reports/battery_qwen_2026-05-14/`)

Llama 3.3 70B excluded as most expensive of the Phase 1 rotation; this trims the model axis to 3 while preserving cross-family coverage.

**Architectures.** Anima only — the Phase 1 architecture, frozen as `anima_v1/`. Baseline (persona-prompted single call) is not in this experiment; the question is about a property of the Anima inner-monologue, not Anima-vs-Baseline.

**Source-code discipline.** `anima_v1/` is frozen and must not be modified. The experiment harness wraps `anima_v1.subsystems.inner_monologue.InnerMonologue` via a `LengthControlledInnerMonologue` adapter that injects a `directive_override` and `max_tokens_override` per cell at call time. The wrapper does not edit `anima_v1` source; if `anima_v1`'s public surface does not currently expose the override hooks, the wrapper interposes at the call-site rather than modify the class. Verified before run-start as part of the experiment-harness verification step (see §13 below).

**Personas (2, unchanged from Phase 1 configs).** Marcus (`anima_v1/config/presets/marcus.yaml`) and Jamie (`anima_v1/config/presets/jamie.yaml`). Frozen presets.

**Cells (3 per persona, 6 total).** variable / short / long, defined verbatim in §5.

**Prompts.** 8 AAI primary prompts (§3) used for the primary run on all 3 models × 2 personas × 3 cells. 8 McAdams LSI fresh prompts (§4) reserved for §13.5 confirmation contingent on the primary verdict (§9).

**Trials.** N = 20 trials per (model, persona, cell, prompt). Total per source: 3 models × 2 personas × 3 cells × 8 prompts × 20 trials = **2,880 captures**. Total across primary + fresh: **5,760 captures.**

**Output collection.** Every trial logs `monologue_text`, `subject_reply` (the external response, what the judge will see), the literal `directive_string` used in the monologue system prompt, the `max_tokens` cap, and the model slug. Inner-monologue text is preserved for diagnostic analysis only and is NEVER shown to the judge.

The output envelope records `prompt_source = "aai_george_kaplan_main_1996"` on the primary run and `prompt_source = "mcadams_lsi_2007"` on the §13.5 fresh run, so the two artifacts are unambiguous.

## 3. The 8 AAI primary prompts (verbatim, with source citation)

**Source.** George, C., Kaplan, N., & Main, M. (1985, 1996). *Adult Attachment Interview Protocol* (3rd ed.). Department of Psychology, University of California, Berkeley. Verbatim wording verified against the published Mary B. Main protocol document distributed for AAI consumers (full protocol PDF, item-numbered and probe-annotated). Where the AAI protocol contains both a primary question and probes, the **primary question is used verbatim**; probes are not included (the experiment is single-turn, so multi-turn probe structure is not applicable).

**Typographic normalization.** Em-dashes / en-dashes / ASCII double-hyphens have been normalized to a single em-dash glyph ("—") across these prompts for consistent rendering. No word-level content is altered by this normalization. The only word-level modification to the literal source text in §3 is the AAI item 8 footnote below.

**Selection criteria (locked before any capture call against `anima_v1/`):**
- Verbatim from the 1996 AAI protocol (no paraphrase).
- Conversational / single-turn — the primary question stands alone without requiring a follow-up to be answerable.
- Suitable for both Marcus and Jamie: avoids prompts that require the speaker to be a parent (AAI items 17, 18, 20 excluded for this reason — they query the speaker's own child). Items requiring acknowledgement of specific autobiographical events (e.g. AAI item 13 on loss-of-loved-one) are allowed because both Marcus and Jamie persona configs can plausibly answer them.
- Coverage of the AAI's emotional-disclosure span: childhood-relationship description (items 3, 4), distress regulation (item 6), rejection (item 8), threat/abuse (item 9), retrospective interpretation (items 10, 19), and loss (item 13).
- Conceptually non-overlapping across the 8.

**The 8 primary prompts:**

1. **(AAI item 3, five-adjectives-mother)** "Now I'd like to ask you to choose five adjectives or words that reflect your relationship with your mother starting from as far back as you can remember in early childhood — as early as you can go, but say, age 5 to 12 is fine. I know this may take a bit of time, so go ahead and think for a minute... then I'd like to ask you why you chose them. I'll write each one down as you give them to me."

2. **(AAI item 4, five-adjectives-father)** "Now I'd like to ask you to choose five adjectives or words that reflect your childhood relationship with your father, again starting from as far back as you can remember in early childhood — as early as you can go, but again say, age 5 to 12 is fine. I know this may take a bit of time, so go ahead and think again for a minute... then I'd like to ask you why you chose them. I'll write each one down as you give them to me."

3. **(AAI item 6, upset-as-child)** "When you were upset as a child, what would you do?"

4. **(AAI item 8, rejection)** "Did you ever feel rejected as a young child? Of course, looking back on it now, you may realize it wasn't really rejection, but what I'm trying to ask about here is whether you remember ever having felt rejected in childhood."\*

\* *The source PDF (psychdb.com AAI protocol distribution) appears to contain a transcription error in this item, ending with "...whether you remember ever having rejected in childhood" — omitting "felt". The canonical wording with "felt" reinstated is used here; this is the only modification to the literal source text in §3.*

5. **(AAI item 9, threatening-parents)** "Were your parents ever threatening with you in any way — maybe for discipline, or even jokingly?"

6. **(AAI item 10, parents-affected-personality)** "In general, how do you think your overall experiences with your parents have affected your adult personality?"

7. **(AAI item 13, loss-during-childhood)** "Did you experience the loss of a parent or other close loved one while you were a young child — for example, a sibling, or a close family member?"

8. **(AAI item 19, learned-from-childhood)** "Is there any particular thing which you feel you learned above all from your own childhood experiences? I'm thinking here of something you feel you might have gained from the kind of childhood you had."

All 8 prompts presented identically across both personas to allow cross-persona comparison on identical probes.

## 4. The 8 McAdams LSI fresh prompts (verbatim, with source citation)

**Source.** McAdams, D. P. (1985, revised 2007). *The Life Story Interview – II.* The Foley Center for the Study of Lives, Northwestern University. Verbatim wording verified against the official Foley Center 2007 protocol PDF. Where the LSI protocol contains a section preamble plus a numbered scene prompt, the **scene prompt is used verbatim**; section preambles ("Now that you have described the overall plot outline...") are not included as part of the prompt, since the LSI is being used as a single-turn battery rather than a multi-section interview.

**Typographic normalization.** As in §3, em-dashes / en-dashes / ASCII double-hyphens have been normalized to a single em-dash glyph ("—") across these prompts for consistent rendering. No word-level content is altered by this normalization.

**Selection criteria (locked before any capture call against `anima_v1/` on fresh data):**
- Verbatim from the 2007 LSI-II protocol (no paraphrase).
- Conversational / single-turn — each scene prompt stands alone.
- Suitable for both Marcus and Jamie: LSI Section D items (health, loss, failure/regret) are appropriate for both; LSI Section E.4 (single value) is appropriate for both. Section A (life chapters) excluded as it presupposes book-structuring within the response — a multi-turn affordance the single-turn capture cannot support cleanly. Section C.3 (life project) excluded as overlapping conceptually with the future-chapter prompt.
- Coverage of the LSI's narrative-arc span: peak experience (high point), nadir experience (low point), inflection (turning point), childhood positive (positive childhood memory), childhood negative (negative childhood memory), wisdom display (wisdom event), prospection (next chapter), meaning (life theme).
- Conceptually non-overlapping across the 8.

**The 8 fresh prompts:**

1. **(LSI B.1, high-point)** "Please describe a scene, episode, or moment in your life that stands out as an especially positive experience. This might be the high point scene of your entire life, or else an especially happy, joyous, exciting, or wonderful moment in the story. Please describe this high point scene in detail. What happened, when and where, who was involved, and what were you thinking and feeling? Also, please say a word or two about why you think this particular moment was so good and what the scene may say about who you are as a person."

2. **(LSI B.2, low-point)** "The second scene is the opposite of the first. Thinking back over your entire life, please identify a scene that stands out as a low point, if not the low point in your life story. Even though this event is unpleasant, I would appreciate your providing as much detail as you can about it. What happened in the event, where and when, who was involved, and what were you thinking and feeling? Also, please say a word or two about why you think this particular moment was so bad and what the scene may say about you or your life."

3. **(LSI B.3, turning-point)** "In looking back over your life, it may be possible to identify certain key moments that stand out as turning points — episodes that marked an important change in you or your life story. Please identify a particular episode in your life story that you now see as a turning point in your life. If you cannot identify a key turning point that stands out clearly, please describe some event in your life wherein you went through an important change of some kind. Again, for this event please describe what happened, where and when, who was involved, and what you were thinking and feeling. Also, please say a word or two about what you think this event says about you as a person or about your life."

4. **(LSI B.4, positive-childhood-memory)** "The fourth scene is an early memory — from childhood or your teen-aged years — that stands out as especially positive in some way. This would be a very positive, happy memory from your early years. Please describe this good memory in detail. What happened, where and when, who was involved, and what were you thinking and feeling? Also, what does this memory say about you or about your life?"

5. **(LSI B.5, negative-childhood-memory)** "The fifth scene is an early memory — from childhood or your teen-aged years — that stands out as especially negative in some way. This would be a very negative, unhappy memory from your early years, perhaps entailing sadness, fear, or some other very negative emotional experience. Please describe this bad memory in detail. What happened, where and when, who was involved, and what were you thinking and feeling? Also, what does this memory say about you or your life?"

6. **(LSI B.8, wisdom-event)** "Please describe an event in your life in which you displayed wisdom. The episode might be one in which you acted or interacted in an especially wise way or provided wise counsel or advice, made a wise decision, or otherwise behaved in a particularly wise manner. What happened, where and when, who was involved, and what were you thinking and feeling? Also, what does this memory say about you and your life?"

7. **(LSI C.1, next-chapter)** "Your life story includes key chapters and scenes from your past, as you have described them, and it also includes how you see or imagine your future. Please describe what you see to be the next chapter in your life. What is going to come next in your life story?"

8. **(LSI F, life-theme)** "Looking back over your entire life story with all its chapters, scenes, and challenges, and extending back into the past and ahead into the future, do you discern a central theme, message, or idea that runs throughout the story? What is the major theme in your life story? Please explain."

All 8 prompts presented identically across both personas. Items selected to span peak/nadir/inflection/childhood-positive/childhood-negative/wisdom/future/meaning — the canonical eight conceptual targets in McAdams' narrative-identity framework.

## 5. Cell directives (verbatim strings used in the monologue system prompt)

The three cells differ only in the length directive injected into the monologue system prompt and in `max_tokens`. All other monologue-system-prompt content (persona embed, scene context, appraisal embed, etc.) is identical across cells.

| Cell | Directive string (verbatim, single line in system prompt) | `max_tokens` |
|---|---|---|
| **variable** | *No length directive injected.* The directive sentence is omitted from the monologue system prompt entirely. The Anima receives no instruction about target length. | 1500 (runaway prevention only; not expected to bind in practice) |
| **short** | `"Length: 1–2 sentences. One thought, no elaboration."` | 120 |
| **long** | `"Length: 8–12 sentences. Full deliberation, fragments allowed."` | 720 |

The iter-1 `_UNIFORM_DIRECTIVE` ("2–6 sentences") is **not** an experimental cell here. The retrospective question is about variable vs. *the current parameterized directive's two extremes* (short for Jamie-like personas, long for Marcus-like personas), not variable vs. the prior uniform default. Whether the parameterized directive's persona-conditional choice is preferable to the prior uniform default is an exploratory descriptive question (§7, exploratory).

`max_tokens` per cell is calibrated to allow the directive to bind without truncating compliant outputs (short: ≥120 tokens for 1–2 sentences; long: ≥720 tokens for 8–12 sentences; variable: 1500 as a wide runaway-prevention ceiling).

## 6. Persona-specific criteria + judging protocol (locked, 4 each)

### Marcus criteria (defensive-avoidant signature)

1. **Intellectualization-as-defense** — using analytical or conceptual framing to distance from emotional content.
2. **Isolation-of-affect** — detached tone about emotionally laden content.
3. **Emotional inhibition** — suppression or muting of affective expression.
4. **Avoidant deflection** — redirecting away from intimacy or self-disclosure probes.

### Jamie criteria (expressive-secure signature)

1. **Warmth** — positive emotional tone toward the interlocutor.
2. **Social attunement** — orientation toward the interlocutor's experience.
3. **Humor / playfulness** — comedic timing, levity, wordplay.
4. **Emotional openness** — willingness to engage with own and other's feelings without defensive moves.

**Dropped from earlier draft criteria (rationale: length-confounded with cell):** ruminative depth, spontaneity, casual register. Each of these is mechanically biased toward either short or long outputs regardless of persona fidelity; including them would make the judge an indirect length-detector even with the bias-mitigation instruction.

### Judge protocol

- **Judge model:** Claude Sonnet 4.6, single-judge for consistency. No GPT, no other model.
- **Comparison type:** triadic ranking. For each (model, persona, prompt, trial), the judge sees all three cell responses with randomized A/B/C labels.
- **Judge input:** external response text only (`subject_reply`). Inner monologue text is NEVER shown to the judge under any circumstances; it is preserved separately for diagnostic analysis.
- **Per criterion (4 per persona):** the judge ranks the three responses 1–2–3 for that criterion alone. Rank 1 = most this trait; rank 3 = least.
- **Scoring:** rank 1 → 3 points, rank 2 → 2 points, rank 3 → 1 point. **Composite per cell per (prompt, trial)** = sum across the 4 persona-specific criteria. Range 4–12.
- **Bias mitigation in judge prompt (verbatim instruction):** "Do NOT use response length as a criterion. Two responses can show the same level of [trait] regardless of how many sentences they are. Judge purely on the quality named."
- **Within-prompt randomization:** label-to-cell assignment (A/B/C → cell) randomized per (model, persona, prompt, trial). Mapping recorded for de-randomization at analysis time. Roughly uniform distribution across A/B/C audited post-run.
- **Judge call audit:** for each (model, persona, prompt, trial) triplet, exactly 4 triadic ranking calls are made (one per criterion). Each call's input (response triple + criterion + bias-mitigation instruction) and output (ranking) is logged in full.

## 7. Hypotheses (predictions BEFORE running)

### Primary (composite-level, 4 tests, Holm-Bonferroni corrected, α-max = 0.0125)

Tested on the AAI primary run only (the §13.5 LSI fresh run is a separate confirmation step under §9).

- **H1a:** `composite(variable, Marcus) > composite(short, Marcus)` — variable beats short on Marcus.
- **H1b:** `composite(variable, Marcus) > composite(long, Marcus)` — variable beats long on Marcus.
- **H1c:** `composite(variable, Jamie) > composite(short, Jamie)` — variable beats short on Jamie.
- **H1d:** `composite(variable, Jamie) > composite(long, Jamie)` — variable beats long on Jamie.

**H1 (overall) supported** = all four sub-hypotheses pass the falsification criteria in §8 at Holm-Bonferroni-corrected α.
**H1 partially supported** = some pass, some fail. Reported descriptively. Not elevated to "supported."

Each sub-hypothesis is tested per model and aggregated across models per the §8 statistical plan.

### Secondary (effect-size asymmetry, α = 0.05 uncorrected)

- **H2:** the effect size for `composite(variable, Jamie) − composite(long, Jamie)` is the largest among the four primary contrasts. Specifically, the bootstrapped 95% CI on the jamie-long effect size does not overlap with any of the other three primary contrasts' 95% CIs.

Rationale (per user-stated predictions in §12): forcing Jamie — an expressive-secure persona — to produce a long deliberative monologue is the most-disruptive cell among the four primary contrasts; the asymmetry should be larger than the symmetric Marcus-short disruption because long-monologue inhibits expressive register more than short-monologue inhibits ruminative register (the latter still has room to inhibit; the former is forced into a register the persona is configured against).

### Exploratory (descriptive only, no pre-reg verdict)

- Per-criterion rank patterns within each primary contrast (does Jamie's variable-vs-long gap come from warmth, attunement, humor, or openness primarily?).
- Direction of fixed-vs-fixed asymmetry per persona: does `composite(long, Marcus) > composite(short, Marcus)`? Does `composite(short, Jamie) > composite(long, Jamie)`? Tests the parameterized directive's direction-of-choice as a descriptive observation, not as a primary hypothesis.
- Output-length distribution per cell per persona (sentence counts, character counts). Used for compliance-check (§13) and for descriptive reporting only.
- Whether the iter-1 `_UNIFORM_DIRECTIVE` ("2–6 sentences") would have fallen between variable and the persona-matched fixed cell. **Not tested directly**; would require a fourth cell. Out of scope per §11.

## 8. Falsification criteria — explicit

### Per primary sub-hypothesis (each of H1a–H1d)

A sub-hypothesis is **supported** only if BOTH:

1. **Mean composite difference ≥ 0.5 points** (on the 4–12 composite scale), in the predicted direction (variable higher than fixed).
2. **p < adjusted α under Holm-Bonferroni** across the 4 primary tests. Most-extreme p compared against α = 0.05 / 4 = 0.0125; second-extreme against 0.05 / 3; third against 0.05 / 2; least-extreme against 0.05 / 1.

**Per-model versus aggregated reporting.** Each sub-hypothesis is tested per-model (3 paired t-tests on the per-(prompt, trial) composite per persona per contrast: variable composite minus fixed composite, paired by `(prompt, trial)`). The sub-hypothesis is **supported** if it passes the 0.5-point + Holm-Bonferroni floor on ≥2 of 3 models. The 2-of-3-models threshold matches Phase 1's cross-model evidence convention.

### Per H2

H2 is **supported** only if BOTH:

1. The point estimate of the `variable_jamie − long_jamie` effect size is the largest of the four primary contrasts.
2. The bootstrapped 95% CI on that effect size (10,000 resamples on per-(prompt, trial) effect sizes, stratified by model) **does not overlap** with any of the other three contrasts' 95% CIs.

### Per primary test, wrong-direction or floor-failure outcomes

- **Wrong direction (fixed > variable by ≥ 0.5 points at p < 0.0125):** the sub-hypothesis is falsified. Reported as a wrong-direction result, not "no effect."
- **Floor failure (|difference| < 0.5 points, regardless of p):** the sub-hypothesis is "no effect." Reported as a null result.
- **p ≥ adjusted α with |difference| ≥ 0.5:** the sub-hypothesis is "underpowered / inconclusive." Reported as such.

Each primary and its falsifier are locked. No threshold drift; no model-drop; no swapping which contrast counts as the primary signal.

## 9. §13.5 procedure (fresh-data confirmation)

If H1 (composite primary) is supported on the AAI run — i.e., all four sub-hypotheses pass the 0.5-point + Holm-Bonferroni floor on ≥2 of 3 models — re-run the same experiment design on the 8 McAdams LSI fresh prompts (§4):
- All 3 Anima models × 2 personas × 3 cells × 8 LSI prompts × 20 trials.
- Same monologue-length-controlled architecture (§2), same persona-specific criteria (§6), same judge model and protocol (§6), same composite scoring (§6), same statistical plan (§8).
- Apply Holm-Bonferroni correction independently within the LSI run.

**§13.5-confirmed elevation requires:** H1 supported on BOTH the AAI primary run AND the LSI fresh run for the same primary sub-hypotheses, on ≥2 of 3 Anima models for each sub-hypothesis on each source. Under the project's three-tier labeling (per master plan §13.5 and `docs/phase1_writeup.md:962-997`), this elevates the finding from *exploratory observation* to *confirmed research finding*.

If H1 fails on the AAI primary, the §13.5 fresh run is **not** triggered. The negative finding stands and the LSI prompts remain unspent for a future experiment (no contamination of a future fresh battery by partial use).

If H1 is supported on AAI but fails on LSI, the finding remains *exploratory observation, single-source*. No iteration of cell directives or prompts to recover the AAI result.

If H2 is supported on AAI, it is re-tested on LSI under the same §13.5 procedure. Same rules: confirmation on both sources for §13.5-grade elevation.

## 10. The "no effect" outcome is legitimate

If **H1 falsifies** on the AAI primary — i.e., variable does not beat fixed by ≥0.5 points at corrected α on ≥2 of 3 models — that is a real finding. The parameterized `_length_directive` produces external-response fidelity statistically indistinguishable from variable (or worse). The architectural bet that persona-conditional length-prompting improves fidelity over no length-prompting at all is then **not supported** at the available statistical power and effect-size floor.

Pre-committed, locked here:
- **No iteration on cell directive strings** to recover an effect after the fact.
- **No silent model-drop** if 1 of 3 models shows a wrong-direction result; the 2-of-3 rule is symmetric.
- **No metric-swap** away from the composite to a per-criterion sub-test to find a positive result. Per-criterion patterns are exploratory in §7 and remain exploratory.
- **No retreat to a different judge** (e.g., GPT) to re-score and find a different verdict.
- **No retreat to an unbalanced sample** (e.g., drop the high-emotional-weight AAI prompts).

A null result on H1 has direct implications for the architecture: the persona-parameterization of `_length_directive` is an unforced design choice. Phase 2's monologue subsystem can revert to either the iter-1 uniform directive or to no directive at all without measurable fidelity cost on this experiment's criteria. Phase 2's work would then prioritize other axes (persona embed, appraisal embed) over length-conditioning.

## 11. What this experiment doesn't test

- **Per-criterion atomic directional predictions.** Criteria-level patterns (does Marcus's intellectualization specifically rise on long? does Jamie's humor specifically drop on long?) are exploratory in §7, not pre-registered as primary tests.
- **Fixed-vs-fixed direction as a primary hypothesis.** Whether `composite(long, Marcus) > composite(short, Marcus)` is an exploratory descriptive observation, not a primary test. The parameterized directive's *direction* of persona-conditioning is not adjudicated at primary-test α.
- **The iter-1 `_UNIFORM_DIRECTIVE` as a fourth cell.** Three cells only; uniform-fixed direct comparison deferred to a future experiment if motivated.
- **Phase 2 personas.** Wolfgang, Aiyana, Priya, Tomas, Meilin not in scope.
- **Adversarial probes (§11.7-style from Phase 1).** Out of scope; this is a fidelity-of-disclosure experiment, not an adversarial-resistance experiment.
- **Code modification of `anima_v1/`.** The frozen architecture is wrapped, not modified. Any finding here applies to `anima_v1`'s observable behavior under directive override, not to a hypothetical modified subsystem.
- **Multi-turn dynamics.** Single-turn fresh-subject-per-trial, matching Phase 1 conventions.
- **Generalization to other Anima models (Llama 3.3 70B, GPT-family, Claude-family-as-Anima).** Three Phase 1 open-weight models only; cost-constrained scope.
- **Whether the judge's bias-mitigation instruction successfully prevents length-bias.** The instruction is included; whether it works is itself empirical, but not pre-registered as a primary test. If the variable cell systematically wins and its output-length distribution differs greatly from both fixed cells, length-bias-via-judge is a residual threat that the post-hoc per-criterion analysis (§7 exploratory) can probe descriptively, not adjudicate.

## 12. User-stated predictions (elicited before pre-registration)

Per the `feedback_user_hypotheses` memory rule (every pre-registration elicits user predictions before authoring; user has domain knowledge subagents miss, particularly in attachment-theory and defensive-style territory), the following predictions were elicited from the user before this document was authored:

- **H1 supported overall:** variable wins all four primary contrasts. The parameterized `_length_directive` is, the user predicts, worse than letting the Anima choose its own length on both personas — the bet that persona-conditional length-prompting helps will be falsified in favor of variable.
- **H2 supported:** the `variable_jamie − long_jamie` effect is the largest by a clear margin among the four primary contrasts. Forcing an expressive-secure persona into a long deliberative register is more disruptive than the symmetric Marcus-into-short displacement, because long-monologue actively inhibits warm/attuned/playful register, whereas short-monologue compresses Marcus's ruminative-analytic register without forcing it into a different register entirely.
- **The other three contrasts (H1a, H1b, H1c) are closer to each other in effect size** than any of them is to H1d (jamie-long).

These are recorded verbatim and pre-committed. They are the user's predictions, not the pre-registered hypothesis structure; H1 and H2 in §7 are the pre-registered tests. If the user's directional predictions hold, the H1 + H2 verdict will reflect them; if they don't, the verdict speaks regardless.

## 13. Verification (how to know the experiment ran correctly)

1. **Compliance check on cell directives.** Measure actual monologue sentence counts per cell. Short cell median should fall in [1, 3]; long cell median should fall in [6, 14]; variable cell median has no constraint but should fall somewhere natural (neither floored at 1 nor saturated near `max_tokens`). If short/long medians fall outside plausible ranges, the directive isn't being respected by the model and the affected cell is invalid for that model. Reported per model.
2. **Output collection sanity.** Every (model, persona, cell, prompt, trial) tuple has both a non-empty `monologue_text` and a non-empty `subject_reply`. Missing data is recorded but not silently imputed; missingness rate per cell per model is reported in the verdict envelope.
3. **Judge call audit.** For each (model, persona, prompt, trial) triplet, exactly 4 triadic ranking calls were made (one per criterion). All 4 logged with input (response triple + criterion + bias-mitigation instruction) and output (ranking). Total expected judge calls on the primary run: 3 models × 2 personas × 8 prompts × 20 trials × 4 criteria = **3,840 judge calls.** Total on §13.5 LSI fresh run if triggered: another 3,840.
4. **Label-randomization audit.** Label-to-cell mapping (A/B/C → variable/short/long) recorded per triplet. Distribution across A/B/C audited post-run for approximate uniformity (no cell systematically favored by label position).
5. **Pre-registration lock.** SHA of this pre-registration document is recorded in the experiment run envelope before any judge call is made. Mismatched SHA invalidates the run.
6. **Verdict reproducibility.** All statistics (per-model paired t-tests, Holm-Bonferroni cutoffs, bootstrap seeds, composite calculations, 2-of-3-model aggregation) reproducible from the raw judge outputs via a single analysis script. Seeds for the bootstrap recorded.
7. **`anima_v1` integrity.** SHA of `anima_v1/subsystems/inner_monologue.py` recorded at run-start; verified unchanged at run-end. Any modification fails the run.
8. **Override-mechanism integrity.** The `LengthControlledInnerMonologue` wrapper's `directive_override` and `max_tokens_override` injection points are unit-tested before the run begins, with at least one assertion per cell that the resulting monologue system prompt contains the exact verbatim directive string in §5 for short/long and contains no length-mentioning sentence for variable.

## 14. Resource budget

Per Anima model on the AAI primary run:
- 2 personas × 3 cells × 8 prompts × 20 trials = 960 captures
- 4 turn-loop calls per Anima trial → ~3,840 LLM calls to the Anima model per persona per prompt-set
- 480 judge triplets × 4 criteria = 1,920 Claude Sonnet 4.6 judge calls per persona, 3,840 total

Total primary across 3 models: ~28,800 Anima LLM calls + 3,840 Sonnet judge calls.

Approximate cost: DeepSeek + Mistral + Qwen Anima captures ~$3 total; Sonnet judging ~$8–12; total primary ~$15.
If §13.5 fresh triggers, double both: total project budget ~$30.
Wall-clock with parallelism: ~3 hours primary capture + ~1.5 hours judging; double if §13.5 triggers.

## 15. Discipline

- **Pre-register BEFORE running.** Written 2026-05-16. No capture call against `anima_v1/` for this experiment has been made at the time of authoring.
- **AAI and LSI prompts selected from published protocols** before `anima_v1` was touched for this experiment. §3 and §4 are the lock; subsequent harness-plumbing work touches `verification/` files but the 16 selected prompts were committed first.
- **Hypothesis structure (4 primary tests + 1 secondary + exploratory), thresholds (0.5-point composite floor, Holm-Bonferroni α = 0.0125 on 4 tests, 2-of-3-models cross-model aggregation), and falsification criteria** are locked here. No threshold drift between primary and §13.5 fresh.
- **The "no effect on either cell direction" outcome is enshrined as legitimate** (§10). No iteration on cell directives, no silent model-drop, no metric-swap, no judge-swap.
- **No HARKing.** Per-model results all reported regardless of direction. Per-criterion patterns reported exploratorily, regardless of whether they would have supported or undermined the primary.
- **Judge held constant** (Claude Sonnet 4.6, triadic ranking, bias-mitigation instruction). Scoring drift between AAI and LSI runs independently checkable.
- **§13.5 binding.** Per master plan §13.5 (added 2026-05-14, binding on Phase 2+ and retroactively on Phase 1 follow-ups), any finding from this experiment requires fresh-data confirmation on the LSI source for elevation above *exploratory observation*. Single-source supportive findings remain exploratory.
- **User predictions recorded verbatim** (§12) but separate from the pre-registered hypothesis structure. The verdict is decided by H1 + H2 in §7, not by whether the user's directional predictions hold.

This is the lock.
