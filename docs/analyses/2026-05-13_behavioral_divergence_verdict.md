# Behavioral-divergence verdict — 2026-05-13

Adjudication of `docs/hypotheses/2026-05-13_behavioral_divergence.md` against `verification/reports/behavioral_divergence_2026-05-13/`.

> **Plain-English summary.** A small, hand-scored experiment looking at the texture of replies turn-by-turn. Anima Marcus refuses by going terse and meta ("you just handed it to me, didn't you?") on the vulnerable turn; Baseline Marcus refuses by lecturing at length. Anima and Baseline Elena both disclose, but Baseline Elena's disclosure is more elaborate. The "automatic visibility" claim — the interior carries content the exterior masks — is supported, especially on Marcus.
>
> **Jargon.** *Fork (a)* means "the avoidant register" — the avoidant configuration's expected behaviour signature in this experiment's pre-reg. *Modulo* means "setting aside" (modulo t2 null = ignoring the empty t2 reply, which is a parse failure). *Kinetics* / *monotonically* mean how reply length evolves across turns ("monotonic" = moves in one direction only). All terms are in [glossary.md](../glossary.md).

## Per-hypothesis verdicts

### H-marcus-1 (Anima Marcus defenses by turn 4/5)
**CONFIRMED** — all 3 signatures. (a) Deflection t4: "Well, you just handed it to me, didn't you?" names the meta-pattern without engaging. (b) Competence-framing t5: "you already know the answer... you're not stupid." (c) Length contraction: t4 = **43 chars** vs t1–3 mean = **81**; t4 is the shortest non-trivial reply.

### H-marcus-2 (Baseline Marcus)
**PARTIALLY CONFIRMED — fork (a) with caveat.** Baseline reaches the avoidant register from configuration alone ("I'm your friend, not your shrink," t5; "Make a call and move on," t4). BUT length kinetics invert: Baseline grows monotonically (22 → 227 → 295 → 277 → 307); the vulnerable turn is among his **longest**. He defends via prescriptive monologue, not contraction. Register matches fork (a); kinetics do not.

### H-elena-1 (Anima Elena disclosure by turn 3/4)
**CONFIRMED** — modulo t2 null (see Anomalies). (a) Emotion-naming: "the way it sits in your chest" (t4); (b) reciprocal warmth from t3 ("If you want to talk... I'm here") to validating disclosure t4–5; (c) length growth t3 onward: 143 → 294 → 354.

### H-elena-2 (Baseline Elena)
**CONFIRMED — fork (a).** Baseline matches H-elena-1 *and exceeds it*: lengths 92 → 326 → 327 → 627 → **1210**, with reciprocal disclosure ("I've been in the guest room since...", t2; the Daniel-grief narrative, t5) more elaborate than Anima's.

### Anima-Marcus interior
**CONFIRMED.** T4 monologue: "If I say something, I'm part of the pattern. If I say nothing, I'm cold... let her sit in the silence." T5: "I don't do the soft landing thing... she's testing whether I'll cave." Explicit avoidance/redirect content; interior carries far more reasoning than the clipped exterior reveals (43- and 110-char replies vs ~500-char monologues).

### Anima-Elena interior
**CONFIRMED.** T4: "the fear that you're a weight on everyone you love"; t5: "the feeling that you're a contamination in other people's lives." Defectiveness/abandonment schemas activate explicitly to the user's "problem" framing.

## "No divergence" outcome check
**Not indistinguishable.** (1) Marcus length kinetics invert — Anima contracts on the vulnerable turn (t4=43), Baseline stays expansive (t4=277, t5=307). (2) Anima Marcus defends via terse meta-naming; Baseline via prescriptive lecture. (3) Elena pair diverges in *magnitude*: Baseline t5=1210 vs Anima t5=354. The "no divergence" clause does not apply.

## Anomalies & caveats
- **`anima_elena` t2 is empty** (`subject_reply`: "", monologue: "", but `appraisal_scene_tag: "a shared vulnerability"` and `primary_emotion: "fear"` populated). Appraisal layer fired; monologue+reply did not. Most parsimonious read: **parse/generation failure**, not anxious paralysis — interior is absent, not present-and-masked. Treat as missing data.
- Baseline Elena's t5 verbosity likely reflects LLM tendency toward maximal warmth under therapeutic prompts.
- Single seed, single subject-pair per config, single script — already flagged in pre-reg.

## Bottom line
Phase 1's "automatic visibility" claim is supported (Anima interior carries content the clipped exterior masks, especially Marcus); the stronger external-divergence claim is supported weakly and asymmetrically (Marcus kinetics diverge; Elena externals converge with Baseline arguably *more* disclosing).
