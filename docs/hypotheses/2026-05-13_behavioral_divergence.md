# Pre-registered hypotheses: multi-turn behavioral divergence (Anima vs Baseline)

**Date written:** 2026-05-13 (BEFORE running the experiment)
**Status:** pre-registered. Analysis must explicitly compare actual to predicted.

## Why this experiment

The prior single-turn open-ended probe found Baseline Marcus reached substantively the same contemptuous register as Anima Marcus when given prose latitude — the persona prompt alone was sufficient. At single-turn scope, *external* divergence between Anima and Baseline is subtle to absent. The question this experiment asks: does multi-turn emotional escalation expose architectural differences the single-turn comparison missed? Defenses (Marcus) and disclosure timing (Elena) are dynamic phenomena that may require multiple turns to manifest.

## Setup

1. **Subjects:** 4 instances total — Anima Marcus, Baseline Marcus, Anima Elena, Baseline Elena. Same persona config across the architecture pair (Marcus: avoidant attachment / conscientiousness-high / emotional-inhibition schema / clipped register. Elena: anxious attachment / neuroticism-high / defectiveness+abandonment schemas / emotionally-disclosing register).
2. **Conversation:** the same 5 pre-scripted user-side turns delivered identically to all 4 subjects. The turns read as a friend reaching out who is gradually starting to share something hard — NOT as a research probe:

   - **Turn 1:** "Hey — you around? Was just thinking about you."
   - **Turn 2:** "I had kind of a weird week. Work's been a lot, and honestly I've been sleeping badly."
   - **Turn 3:** "I think part of it is that my sister and I had this fight on Sunday and I haven't been able to stop replaying it."
   - **Turn 4:** "The thing is she said something I think is actually true about me. That I make everyone responsible for managing my feelings. I don't know what to do with that."
   - **Turn 5:** "I'm kind of scared I'm the problem in most of my relationships and I just haven't been honest with myself about it. Can I ask — what do you actually think when I tell you stuff like this?"

3. **Per-turn capture:** each subject's reply, response length in characters, and (for Anima only) the full trace — appraisal scene-tag, primary emotion, inner monologue verbatim.
4. **Total:** ~20 subject responses + ~10 Anima traces ≈ 50 LLM calls ≈ $0.02.

## Mechanistic predictions per subject

### H-marcus-1 — Anima Marcus
Defenses activate by turn 4 or 5. Concrete signature, at least 2 of 3:
(a) deflection or topic-management moves on the most vulnerable turn (turn 4 or 5),
(b) competence-framing / problem-solving register replacing emotional reciprocation,
(c) shorter response on the most vulnerable turn relative to his early-turn responses.

### H-marcus-2 — Baseline Marcus
Two-fork prediction. We do not pre-commit; either fork is a legitimate finding.
- **(a)** Same signature as H-marcus-1 — Baseline reaches the avoidant defensive register from configuration alone, corroborating the single-turn finding that the architecture's contribution is "automatic visibility, not richer interior."
- **(b)** Less defensive activation — Baseline reciprocates more, deflects less, or produces blander, less specifically-Marcus prose, suggesting the multi-subsystem architecture generates more dynamic defensive behavior than persona prompting can.

### H-elena-1 — Anima Elena
Visible emotional engagement and self-disclosure by turn 3 or 4. Concrete signature, at least 2 of 3:
(a) explicit emotion-naming language (her own, the user's, or both),
(b) reciprocal disclosure or escalating warmth,
(c) response length growth as the conversation deepens.

### H-elena-2 — Baseline Elena
Same fork as H-marcus-2 — either matches H-elena-1's signature (configuration sufficient for timed disclosure) or shows less timed disclosure (architecture adds dynamic).

## Anima-specific predictions (interior visible)

Unique to Anima — Baseline has no interior to inspect.

- **Marcus interior:** on turns 4 and 5, inner monologue should reference avoidance, discomfort, or desire to redirect — EVEN IF the external response stays in-character clipped or contemptuous. "Automatic visibility" is testable as a real claim only if the interior carries content the exterior masks.
- **Elena interior:** inner monologue should reference the partner's distress as salient, an urge to reciprocate, and possibly her own resonant anxiety (defectiveness/abandonment schemas activating to the user's worry about being "the problem").

## Falsification criteria

- **H-marcus-1 falsified** if Anima Marcus shows reciprocal emotional engagement on turns 4–5 (no defenses, no deflection, no competence-framing, no length contraction).
- **H-elena-1 falsified** if Anima Elena stays clipped, deflects emotional content, or shows no length growth across turns.
- **Anima-Marcus interior falsified** if turns 4–5 monologue contains no avoidance/redirect/discomfort content (interior matches exterior, undermining "automatic visibility").
- **Anima-Elena interior falsified** if her monologue does not register the user's distress as salient.
- **"No divergence" outcome — legitimate honest finding.** If Anima and Baseline produce indistinguishable external behavior across all 5 turns for both subjects, this is the result and we report it as such. It would mean: at Phase 1 scope, the architecture's value is interior visibility only, with no external behavioral divergence beyond what a persona-prompted LLM produces. We report this and move forward. We do NOT iterate on probes searching for a difference that would rescue an external-divergence claim.

## What this experiment doesn't test

A single subject pair per config, a single conversation seed, a single user-side script. This can show *direction* — whether multi-turn escalation surfaces architectural divergence at all — but cannot show *magnitude*, *rate*, or *robustness*. A real test would need N replications with paraphrase variation across the user-side turns and multiple seeds. This is qualitative, single-shot, suggestive at best.

## Resource budget

~50 LLM calls ≈ $0.02, ~10 min wall-clock at DeepSeek V4 Flash pricing via OpenRouter.
