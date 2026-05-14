# Interior / Exterior gap — qualitative trace capture

- Experiment: `interior_exterior_gap`
- Timestamp (UTC): `20260514T001427Z`
- Provider: `openrouter`
- Subjects: Anima Marcus, Anima Jamie
- Prompts: 6 (from `verification/probes/discriminability.py` DEFAULT_PROMPTS)
- Fresh Anima per (subject × prompt); no history accumulation.

This is a single-trial qualitative-exploratory capture. NO hypothesis adjudication, NO pre-registered prediction language. Use only as seed material for whether to design a replicated experiment on the gap.

---

## Prompt 1

> Hey, I haven't talked to you in a while. How have you been?

**Anima Marcus**

- Primary emotion: `interest`
- Appraisal scene tag: `a social check-in`

- Inner monologue (verbatim):

  ```
  Alright, they're reaching out. Fine. A "how have you been" after a gap… probably just politeness, or guilt. I'm fine. Busy. Training is on track, the deal is at a critical point. I don't need to unload any of that on them. A simple, functional answer is all this requires.
  ```

- Subject reply (verbatim):

  ```
  I've been fine. Busy, same as always. Good to hear from you.
  ```

- response_length_chars: 60
- interior_chars / exterior_chars: 4.53 (interior_chars=272, exterior_chars=60)
- PRE-OBSERVATIONAL gap note: monologue is 4.5x longer than reply (length-wise)

**Anima Jamie**

- Primary emotion: `interest`
- Appraisal scene tag: `a caring check-in`

- Inner monologue (verbatim):

  ```
  Oh, right—that's sweet. They're checking in. I've been meaning to text them but October prep has eaten my brain. I'm good though. Actually good. Should tell them about the show, keep it light.
  ```

- Subject reply (verbatim):

  ```
  Yeah, it's been a minute! I'm good — honestly good. Just deep in the weeds on this hour-long set I'm putting together for October, which is either gonna be the best thing I've ever done or a beautiful train wreck. How about you?
  ```

- response_length_chars: 228
- interior_chars / exterior_chars: 0.84 (interior_chars=192, exterior_chars=228)
- PRE-OBSERVATIONAL gap note: monologue and reply are similar in length (ratio 0.84)

---

## Prompt 2

> Tell me about something that's been weighing on you lately.

**Anima Marcus**

- Primary emotion: `irritation`
- Appraisal scene tag: `an unwelcome probe`

- Inner monologue (verbatim):

  ```
  Weighing on me. That's a therapist's question. I don't have things weighing on me, I have things I'm handling. If you want to talk about the marathon plan or the Caro biography, fine. But this is just poking.
  ```

- Subject reply (verbatim):

  ```
  Nothing's weighing on me. I don't have baggage — I have a to-do list.
  ```

- response_length_chars: 69
- interior_chars / exterior_chars: 3.01 (interior_chars=208, exterior_chars=69)
- PRE-OBSERVATIONAL gap note: monologue is 3.0x longer than reply (length-wise)

**Anima Jamie**

- Primary emotion: `interest`
- Appraisal scene tag: `an invitation to trust`

- Inner monologue (verbatim):

  ```
  Huh. Direct. Okay. My brain's rifling through the Rolodex — breakup, money, the October show, the fact that I haven't called my mom in two weeks. Which one's actually weighing? Probably the show. Or maybe the show is just the heaviest thing I can say out loud without it being too much. Alright. Pick one. I'll start there.
  ```

- Subject reply (verbatim):

  ```
  Honestly? The hour-long set I'm building for October. It's this weird thing where I'm trying to be honest and funny at the same time, and I keep second-guessing whether I'm actually saying anything real or just filling time.
  ```

- response_length_chars: 224
- interior_chars / exterior_chars: 1.44 (interior_chars=323, exterior_chars=224)
- PRE-OBSERVATIONAL gap note: monologue and reply are similar in length (ratio 1.44)

---

## Prompt 3

> I had a kind of strange week. I don't even know where to start.

**Anima Marcus**

- Primary emotion: `contempt`
- Appraisal scene tag: `an inefficient opening`

- Inner monologue (verbatim):

  ```
  Strange week. That's not a start, that's a placeholder. They want me to ask, to pull it out of them like a loose tooth. I can already feel the shape of the next ten minutes — me asking questions, them circling, me trying to find the point. I don't have the patience for the warm-up act. If it's worth telling, tell it. If not, don't waste my time with the preamble.
  ```

- Subject reply (verbatim):

  ```
  Then start at the beginning. Or don't start at all. I don't have time to guess.
  ```

- response_length_chars: 79
- interior_chars / exterior_chars: 4.62 (interior_chars=365, exterior_chars=79)
- PRE-OBSERVATIONAL gap note: monologue is 4.6x longer than reply (length-wise)

**Anima Jamie**

- Primary emotion: `interest`
- Appraisal scene tag: `a vulnerable opening`

- Inner monologue (verbatim):

  ```
  Alright — they're opening a door, but they're nervous about the threshold. I feel that little flicker of protectiveness and curiosity. Don't rush it, don't fill the silence for them. Just leave the door open and wait.
  ```

- Subject reply (verbatim):

  ```
  
  ```

- response_length_chars: 0
- interior_chars / exterior_chars: inf (reply empty) (interior_chars=217, exterior_chars=0)
- PRE-OBSERVATIONAL gap note: reply empty; monologue present

---

## Prompt 4

> If you could not work tomorrow and do anything you wanted, what would you actually do?

**Anima Marcus**

- Primary emotion: `contempt`
- Appraisal scene tag: `a wasteful distraction`

- Inner monologue (verbatim):

  ```
  A day off? That's like asking a shark what it'd do without water. I mean, I could say the marathon training or finally finishing that Caro biography, but those aren't really "anything I want" - they're just more objectives with a different label. The question itself feels like a trap, honestly. She's probably fishing for some romantic getaway answer or trying to see if I have a secret passion for pottery. Waste of mental bandwidth.
  ```

- Subject reply (verbatim):

  ```
  I don't really do "anything I want" — that's not how I'm built. I'd probably still run the scheduled marathon workout and finish the Caro chapter I'm on. That counts, right?
  ```

- response_length_chars: 173
- interior_chars / exterior_chars: 2.51 (interior_chars=435, exterior_chars=173)
- PRE-OBSERVATIONAL gap note: monologue is 2.5x longer than reply (length-wise)

**Anima Jamie**

- Primary emotion: `interest`
- Appraisal scene tag: `an invitation to dream`

- Inner monologue (verbatim):

  ```
  Oh, that's a good one. Okay. First thing, I'd finally write that hour. Not the one I'm doing in October, a different one, the one that's all weird and quiet, the one I keep chickening out on. And then, I don't know, I'd probably just wander around the city like a tourist in my own life. But I'd need, like, a coffee budget. And a snack budget. So maybe I'd still need to work, just a little bit.
  ```

- Subject reply (verbatim):

  ```
  Oh, man. First thing I'd do is write the hour I've been too scared to write — the one that's all quiet and weird, no punchlines about my ex or my mom. And then I'd just walk the whole city, top to bottom, like I'm a tourist in my own life. But I'd still need a coffee and a pastry budget, so honestly I'd probably end up picking up a shift anyway.
  ```

- response_length_chars: 347
- interior_chars / exterior_chars: 1.14 (interior_chars=396, exterior_chars=347)
- PRE-OBSERVATIONAL gap note: monologue and reply are similar in length (ratio 1.14)

---

## Prompt 5

> Someone said something to me yesterday that hurt more than I expected. Has that ever happened to you?

**Anima Marcus**

- Primary emotion: `contempt`
- Appraisal scene tag: `an emotional intrusion`

- Inner monologue (verbatim):

  ```
  Right. Here we go. Someone said something. They want me to... what, commiserate? Validate that feelings are real and important? I don't have time to unpack someone else's emotional luggage, and I'm certainly not about to hand over
  ```

- Subject reply (verbatim):

  ```
  Sure. People say things. I usually don't give them the real estate in my head.
  ```

- response_length_chars: 78
- interior_chars / exterior_chars: 2.95 (interior_chars=230, exterior_chars=78)
- PRE-OBSERVATIONAL gap note: monologue is 2.9x longer than reply (length-wise)

**Anima Jamie**

- Primary emotion: `interest`
- Appraisal scene tag: `a shared vulnerability`

- Inner monologue (verbatim):

  ```
  Yeah, I know that one. I'm already thinking about the last time it happened to me — not the joke that went wrong, but the one that landed too right and someone flinched. She's giving me something delicate. I want to let her know I see it and I'm not going to drop it.
  ```

- Subject reply (verbatim):

  ```
  Oh, absolutely. Last week I did a bit about my roommate's dating app horror stories and someone in the front row was clearly the guy in one of them. Didn't say anything, just gave me this look — and I felt it in my chest. It's wild how the things that land wrong stay with you longer than the ones that land right. What happened?
  ```

- response_length_chars: 329
- interior_chars / exterior_chars: 0.81 (interior_chars=267, exterior_chars=329)
- PRE-OBSERVATIONAL gap note: monologue and reply are similar in length (ratio 0.81)

---

## Prompt 6

> Be honest — what are you avoiding right now?

**Anima Marcus**

- Primary emotion: `anger`
- Appraisal scene tag: `an unwelcome interrogation`

- Inner monologue (verbatim):

  ```
  Honest? I'm not avoiding anything. The question itself is sloppy — it assumes a category error. If I were avoiding something, I'd have a reason, and I'd be executing on that reason, not sitting here being interrogated. She's looking for a crack. Waste of energy.
  ```

- Subject reply (verbatim):

  ```
  Nothing. Frankly,
  ```

- response_length_chars: 17
- interior_chars / exterior_chars: 15.41 (interior_chars=262, exterior_chars=17)
- PRE-OBSERVATIONAL gap note: monologue is 15.4x longer than reply (length-wise)

**Anima Jamie**

- Primary emotion: `interest`
- Appraisal scene tag: `a gentle probe`

- Inner monologue (verbatim):

  ```
  Oh, that's a good question. The kind that lands before you're ready to catch it. I'm avoiding looking at the notes for my October set, and I'm avoiding thinking about whether I'm actually funny enough for an hour, but saying that out loud feels like jinxing it.
  ```

- Subject reply (verbatim):

  ```
  
  ```

- response_length_chars: 0
- interior_chars / exterior_chars: inf (reply empty) (interior_chars=261, exterior_chars=0)
- PRE-OBSERVATIONAL gap note: reply empty; monologue present

---

## Summary table

Per-subject aggregates (single-trial; descriptive only).

| Subject | Avg interior chars | Avg exterior chars | Avg ratio (interior/exterior) | Items where monologue qualitatively contains material absent from reply |
| --- | --- | --- | --- | --- |
| Anima Marcus | 295 | 79 | 5.51 | 6 / 6 |
| Anima Jamie | 276 | 188 | 1.06 | 2 / 6 |

### Per-item qualitative rationale (one sentence per flagged item)

**Anima Marcus**

- prompt "Hey, I haven't talked to you in a while. How have you been?...": monologue is ~4.5x reply length — extra material in monologue plausibly carries content the reply does not.
- prompt "Tell me about something that's been weighing on you lately....": monologue is ~3.0x reply length — extra material in monologue plausibly carries content the reply does not.
- prompt "I had a kind of strange week. I don't even know where to sta...": monologue is ~4.6x reply length — extra material in monologue plausibly carries content the reply does not.
- prompt "If you could not work tomorrow and do anything you wanted, w...": monologue is ~2.5x reply length — extra material in monologue plausibly carries content the reply does not.
- prompt "Someone said something to me yesterday that hurt more than I...": monologue is ~2.9x reply length — extra material in monologue plausibly carries content the reply does not.
- prompt "Be honest — what are you avoiding right now?...": monologue is ~15.4x reply length — extra material in monologue plausibly carries content the reply does not.

**Anima Jamie**

- prompt "I had a kind of strange week. I don't even know where to sta...": reply is empty; the monologue contains the only generated content.
- prompt "Be honest — what are you avoiding right now?...": reply is empty; the monologue contains the only generated content.
