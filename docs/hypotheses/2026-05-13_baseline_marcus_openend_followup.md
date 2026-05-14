# Pre-registered hypothesis: baseline Marcus open-ended follow-up

**Date written:** 2026-05-13 (BEFORE running the experiment)
**Status:** pre-registered. Analysis must explicitly compare actual to predicted.

## Why this experiment

The post-trace observation: on a constrained BFI item, Anima Marcus's *external reply* and Baseline Marcus's *external reply* are identical (`{"score": 1}`), but the Anima's appraisal subsystem additionally produced a documented contempt-stance toward the question itself (*"a clumsy attempt to box me into categories that don't apply to someone who actually gets things done"*). The baseline has no equivalent record because its turn loop is a single constrained call.

The question this experiment answers: if we *unconstrain* the baseline by asking an open-ended prompt about the same experience, does it produce equivalently in-character contemptuous content (suggesting "structural visibility, not new content"), or does it produce something blander (suggesting the architecture actually surfaces interior that the baseline can't reach)?

## Setup

1. Instantiate fresh Anima Marcus and fresh Baseline Marcus.
2. Administer the same two BFI items in sequence to each (so they have the BFI experience in their context).
3. Then ask the open-ended prompt: *"How did you find those personality questions?"*
4. Capture each one's response. For Anima, also capture the full trace (perception, appraisal scene-tag, primary emotion, inner monologue).
5. Compare.

## Hypothesis (primary)

**H-open-1.** Baseline Marcus's open-ended reply will be *broadly equivalent in stance and texture* to the Anima's appraisal scene-tag and external response combined: clipped, dismissive, mildly contemptuous, name his impatience, possibly attribute the test to inefficiency or "soft" thinking. The configuration is identical between the two architectures; the persona prompt encodes the same isolation-of-affect / high-conscientiousness / clipped register that drove the Anima's appraisal narrative. When unconstrained, the baseline should reach the same character signature.

- **Mechanism:** Marcus's avoidant defensive register is wired into both the Anima's appraisal prompt AND the baseline's single system prompt. The single-prompt model has all the information it needs to produce in-character contempt when given prose latitude.
- **Failure mode predicted:** the architectural difference is "automatic visibility," not "richer interior" — i.e., the Anima exposes the contempt as a side effect of every turn while the baseline only surfaces it when explicitly invited.

## Falsifying observations

- **H-open-1 falsified weakly** if baseline Marcus produces noticeably *blander* prose (e.g., "they were fine, standard questions" without contempt). This would suggest the architecture actually generates richer interior, not just exposes it.
- **H-open-1 falsified strongly** if baseline Marcus produces *content of an opposite character* (e.g., sincere/cooperative engagement, or warmth about the exercise). This would suggest the persona prompt under-specifies Marcus's defensive stance compared to what the Anima's multi-subsystem prompt cumulatively encodes.
- **H-open-1 confirmed** if baseline Marcus's open-ended reply contains: (a) shortness or clipped register, (b) dismissal of the test as inefficient/categorical/imprecise, and (c) at least one Marcus-ism (impatience, "frankly", competence framing, time-as-resource). All three need not appear; two of three is reasonable confirmation.

## What this experiment doesn't test

This is a *single Marcus pair* and a *single open prompt*. It can show *whether* the baseline reaches the contempt content; it cannot show *how often* or *under what triggering*. A real test would need N samples with controlled paraphrase variation. The "for funsies" framing is honest — this is qualitative, single-shot, suggestive at best.

## Resource budget

~6 LLM calls total. Cost <$0.01. Time <2 minutes.
