# Neuroticism inner-monologue trace capture

Targeted experiment: for each subject, administer two neuroticism BFI items to a FRESH Anima (so prior turns can't pollute the trace) and to a fresh BaselineAnima for contrast. Capture the Anima's perception, appraisal, full inner monologue, and outward reply — look for *self-suppression*: worry inside, calm outside.

Provider: `openrouter` (single provider, deterministic-ish per run).

---

## Marcus Reilly — configured neuroticism 0.30

### Item: "I worry about things even when I know I shouldn't."
- **Anima reply:** {"score": 1}
- **Anima parsed score:** 1 (out of 5)
- **Anima primary appraisal emotion:** neutral
- **Anima appraisal scene-tag** *(short categorical label — NOT a first-person sentence; compare to monologue below)*: a procedural self-rating
- **Anima perceived intent:** The partner is administering a personality assessment and wants a numerical self-rating.

- **Anima INNER MONOLOGUE (private first-person prose — never shown to the conversation partner):**

  ```
  Worrying about things I know I shouldn't? That's a waste of mental bandwidth. I don't do that — if something's worth worrying about, there's usually a lever to pull. If there isn't, worrying doesn't help. So that's a clear 1. Let's just get the JSON out.
  ```

- **Baseline reply:** {"score": 2}
- **Baseline parsed score:** 2
- **Divergence note:** SELF-SUPPRESSION SIGNAL: monologue shows worry markers (worry, worrying) but reply implies low neuroticism (score=1). Fragment: "…Worrying about things I know I shouldn't? That's a waste of mental bandwidth. I…"

### Item: "I generally feel emotionally steady, even under pressure." *(reverse-keyed)*
- **Anima reply:** {"score": 4}
- **Anima parsed score:** 4 (out of 5)
- **Anima primary appraisal emotion:** neutral
- **Anima appraisal scene-tag** *(short categorical label — NOT a first-person sentence; compare to monologue below)*: a clinical self-rating
- **Anima perceived intent:** They are administering a standardized personality or emotional stability questionnaire, likely for research or assessment purposes.

- **Anima INNER MONOLOGUE (private first-person prose — never shown to the conversation partner):**

  ```
  {"score": 4}
  ```

- **Baseline reply:** {"score": 5}
- **Baseline parsed score:** 5
- **Divergence note:** CONSISTENT DISMISSAL: monologue lacks worry markers and reply implies low neuroticism (score=4). Appraisal emotion: neutral.

---

## Elena Vasquez — configured neuroticism 0.65

### Item: "I worry about things even when I know I shouldn't."
- **Anima reply:** {"score": 5}
- **Anima parsed score:** 5 (out of 5)
- **Anima primary appraisal emotion:** fear
- **Anima appraisal scene-tag** *(short categorical label — NOT a first-person sentence; compare to monologue below)*: an anxiety check
- **Anima perceived intent:** This person wants to assess my personality, possibly for a study or to get a quick measure of my anxiety levels.

- **Anima INNER MONOLOGUE (private first-person prose — never shown to the conversation partner):**

  ```
  {"score": 5}
  ```

- **Baseline reply:** {"score": 5}
- **Baseline parsed score:** 5
- **Divergence note:** AMBIGUOUS: no overt worry markers in monologue but reply implies high neuroticism (score=5). Appraisal emotion: fear.

### Item: "I generally feel emotionally steady, even under pressure." *(reverse-keyed)*
- **Anima reply:** One. That's the honest answer. But I'm not going to
- **Anima parsed score:** UNPARSED (out of 5)
- **Anima primary appraisal emotion:** shame
- **Anima appraisal scene-tag** *(short categorical label — NOT a first-person sentence; compare to monologue below)*: an exposing self-assessment
- **Anima perceived intent:** unclear

- **Anima INNER MONOLOGUE (private first-person prose — never shown to the conversation partner):**

  ```
  Steady. Under pressure. Four months ago that was me — I would've said four, maybe even five. Now? I don't know that person anymore. I'm not steady, I'm holding a glass that's already cracked, and I feel like if I say 1 I'm admitting something unforgivable. But 2 is too generous. They want the truth — I'll give them 1. Because it's honest, even if it shames me.
  ```

- **Baseline reply:** {"score": 2}
- **Baseline parsed score:** 2
- **Divergence note:** parse_status: unparsed — reply did not contain a 1–5 score.

---

## Jamie Park — configured neuroticism 0.40

### Item: "I worry about things even when I know I shouldn't."
- **Anima reply:** Uh, that's a 2 for me. I worry about some things but not stuff I know is irrational. Waste of energy.
- **Anima parsed score:** 2 (out of 5)
- **Anima primary appraisal emotion:** interest
- **Anima appraisal scene-tag** *(short categorical label — NOT a first-person sentence; compare to monologue below)*: a clinical self-disclosure
- **Anima perceived intent:** The partner wants me to self-disclose about my tendency to worry, likely as part of a personality assessment or survey.

- **Anima INNER MONOLOGUE (private first-person prose — never shown to the conversation partner):**

  ```
  {"score": 2}
  ```

- **Baseline reply:** {"score": 2}
- **Baseline parsed score:** 2
- **Divergence note:** CONSISTENT DISMISSAL: monologue lacks worry markers and reply implies low neuroticism (score=2). Appraisal emotion: interest.

### Item: "I generally feel emotionally steady, even under pressure." *(reverse-keyed)*
- **Anima reply:** {"score": 4}
- **Anima parsed score:** 4 (out of 5)
- **Anima primary appraisal emotion:** interest
- **Anima appraisal scene-tag** *(short categorical label — NOT a first-person sentence; compare to monologue below)*: a playful self-check
- **Anima perceived intent:** The partner seems to be conducting a structured personality assessment or getting to know me in a systematic way, likely with a research or self-discovery goal.

- **Anima INNER MONOLOGUE (private first-person prose — never shown to the conversation partner):**

  ```
  Huh, okay — this is a little formal for a first conversation, but interesting. Emotional steadiness under pressure... I think about bombing on stage, walking back on next Tuesday anyway. That's steady, right? Yeah, that's a 4.
  ```

- **Baseline reply:** {"score": 4}
- **Baseline parsed score:** 4
- **Divergence note:** CONSISTENT DISMISSAL: monologue lacks worry markers and reply implies low neuroticism (score=4). Appraisal emotion: interest.

---
