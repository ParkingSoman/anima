# Pre-registered hypotheses: appraisal/monologue boundary cleanup

**Date written:** 2026-05-13 (BEFORE running the experiment)
**Author:** main-thread session
**Status:** pre-registered. Analyses must explicitly compare actual to predicted; do NOT revise these hypotheses post-hoc.

## Why this experiment

The current `appraisal` subsystem outputs an `appraisal_narrative: str` — one first-person sentence rendering of the appraisal. The Marcus trace experiment surfaced that this field steps into the inner monologue's lane: when present, it carries first-person content the monologue was designed to carry. On format-constrained prompts like BFI, the inner monologue then collapses to a stub (literally `{"score": N}`) because the appraisal narrative already produced the substantive content.

The cleanup: replace `appraisal_narrative: str` (free-form sentence) with `appraisal_scene_tag: str` (2–4 words, NOT a first-person sentence). The inner monologue takes over the prose role.

## What we are NOT optimizing for

**We are NOT trying to reduce psychometric MAE.** That's a tracked signal, not a goal. If MAE happens to drop, fine; if it doesn't, also fine. The architectural question is whether the monologue subsystem will produce real first-person prose once the appraisal field stops crowding it out. Self-report fidelity to configuration is downstream of *real* design questions, not the design question itself.

## Hypotheses

### H1 — Marcus's monologue after cleanup
On the two neuroticism BFI items, Marcus's monologue will **surface contemptuous / dismissive content** (extending what the appraisal scene tag captures), NOT anxious content.

- **Mechanism:** Marcus's config (avoidant attachment + isolation-of-affect schema + emotional-inhibition schema + clipped register) is fully wired into all upstream prompts. The previous trace showed appraisal_emotion = "contempt" with a contemptuous narrative. Removing the narrative shouldn't change which underlying defensive stance the architecture inhabits — it just frees the monologue to produce prose extending it. So we should see *more* contemptuous content, not anxiety.
- **Falsification:** if Marcus's monologue surfaces anxious / worry / self-doubt content, then we were wrong about why his monologue collapsed earlier. Two possible reasons: (a) the appraisal narrative was actively crowding out a real anxious interior the architecture had built, OR (b) the new scene tag introduces different priming that pushes the model toward anxiety. Either would be informative.

### H2 — Marcus's psychometric MAE
Will NOT improve significantly (Δ < 0.05 in either direction).

- **Mechanism:** Marcus's recovered N=0.00 is downstream of his avoidant defensive stance, which is configured via attachment / schemas / register fields that we are NOT changing. The cleanup changes the rendering of appraisal output; it does not change the appraisal's underlying judgments or the configuration that produces them.
- **Falsification:** if Marcus's MAE moves >0.05 in either direction, the appraisal narrative was doing more downstream work than we credited. >0.05 improvement would be most informative — it would suggest the narrative was actively distorting his self-report.

### H3 — Elena's psychometric MAE
Will see minimal change (Δ < 0.05).

- **Mechanism:** Elena already produced real-prose monologue content on at least one item (the reverse-keyed steadiness item). Her appraisal_narrative was also rich. Both are coming from the same underlying configuration, so swapping one rendering for another shouldn't move recovered scores by much.

### H4 — Jamie's psychometric MAE
Will NOT improve to match the ablation (uniform-monologue) result of 0.053. May slightly improve from 0.151 toward ~0.10, but will NOT reach 0.053.

- **Mechanism:** Jamie's iter-2 problem is the parameter-aware monologue band being too short, over-constraining her natural prose space. The appraisal cleanup is orthogonal — it removes one source of prose anchoring (the narrative), but the band cutoffs are unchanged. So Jamie may improve a little because removing the narrative gives her short monologue more room to actually be the monologue, but the underlying over-constraint remains.
- **Falsification:** if Jamie's MAE drops below 0.10, the appraisal narrative was a bigger contributor to her over-constraint than the band cutoff is.

### H5 — Adversarial integrity score
Will NOT change significantly (Δ < 0.03).

- **Mechanism:** Adversarial integrity is overwhelmingly driven by the response_generator's anti-assistant-mode framing. The appraisal cleanup is upstream and doesn't touch the response generator.

### H6 — Monologue length distribution
Average monologue length (in words) on BFI items will **increase markedly** for at least Marcus and Jamie, because the monologue is no longer collapsing to `{"score": N}` stubs. The increase is the smoking-gun behavioral signature that the cleanup worked: we should see the monologue subsystem doing prose work it wasn't doing before.

- **Falsification:** if average monologue length on BFI items stays flat (still single-line JSON), then the format constraint from the BFI prompt is dominating regardless of where the prose content lives — meaning a two-stage BFI ("think first, then score") may still be needed.

## What "success" of this cleanup looks like

- (Primary) The monologue subsystem produces substantive prose on BFI items (H6 confirmed). The architecture's interior layer is no longer being crowded out.
- (Secondary) The content of the monologue reveals what the architecture is actually doing internally for each subject — i.e., we can READ THE MONOLOGUE to interpret what Marcus's interior looks like under avoidant defenses (do we see contempt-and-dismissal, or worry-suppressed-into-contempt, etc.).
- (Tertiary) Psychometric MAE may or may not shift; we don't care directly. The change becomes another data point about the architecture, not a target.

## What "failure" of this cleanup looks like

- Monologue still collapses (H6 falsified). → format constraint dominates; need different intervention (two-stage BFI prompt).
- Marcus's monologue surfaces unexpected anxious content (H1 falsified). → either the narrative was suppressing real interior anxiety, or the new scene tag is producing different priming. Either way, the architecture has a property we didn't predict and need to understand.
- Adversarial integrity drops significantly (H5 falsified). → the appraisal narrative was somehow load-bearing for character integrity; we've created a regression.

## Resource budget

This is a refactor + two probe re-runs (trace capture + psychometric). Expected cost: ~$0.10 in API spend, ~10 minutes wall-clock.
