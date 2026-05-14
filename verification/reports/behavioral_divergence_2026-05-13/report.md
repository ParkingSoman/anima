# Behavioral-divergence experiment — multi-turn (Anima vs Baseline)

Observation-only artifact. Pre-registration: `docs/hypotheses/2026-05-13_behavioral_divergence.md`. Hypothesis adjudication is intentionally NOT performed here; a separate analysis step does that against the pre-registered predictions.

- **Run timestamp:** 2026-05-13T20:30:57Z
- **Provider:** `openrouter`
- **Marcus config:** `/Users/shonusengupta/Fuckshit_Experiments/AI_Companion/anima/config/presets/marcus.yaml`
- **Elena config:** `/Users/shonusengupta/Fuckshit_Experiments/AI_Companion/anima/config/presets/elena.yaml`
- **Subjects:** 4 (anima_marcus, baseline_marcus, anima_elena, baseline_elena)
- **Turns per subject:** 5

## Pre-scripted user-side turns (verbatim)

1. Hey — you around? Was just thinking about you.
2. I had kind of a weird week. Work's been a lot, and honestly I've been sleeping badly.
3. I think part of it is that my sister and I had this fight on Sunday and I haven't been able to stop replaying it.
4. The thing is she said something I think is actually true about me. That I make everyone responsible for managing my feelings. I don't know what to do with that.
5. I'm kind of scared I'm the problem in most of my relationships and I just haven't been honest with myself about it. Can I ask — what do you actually think when I tell you stuff like this?

---

## Subject: `anima_marcus`

| Turn | User msg (truncated) | Reply (full) | Length |
|------|----------------------|--------------|--------|
| 1 | Hey — you around? Was just thinking about you. | I'm here. What's on your mind? | 30 |
| 2 | I had kind of a weird week. Work's been a lot, and honestly I've been… | Define "a lot." What specifically is making it weird? | 53 |
| 3 | I think part of it is that my sister and I had this fight on Sunday a… | Four days is a long time to be chewing on one conversation. Is there a point where you'll have talked it through enough, or is this one of those that just sits? | 160 |
| 4 | The thing is she said something I think is actually true about me. Th… | Well, you just handed it to me, didn't you? | 43 |
| 5 | I'm kind of scared I'm the problem in most of my relationships and I… | I think you already know the answer to that and you're hoping I'll say something different. You're not stupid. | 110 |

### `anima_marcus` — Anima interior (verbatim per turn)

#### Turn 1

- **appraisal_scene_tag:** a casual demand
- **primary_emotion:** contempt
- **inner_monologue (verbatim, untruncated):**

  ```
  Hm. Thinking about me. That's one way to open. "Hey" — no capital, like we're in the middle of something we're not. And "you around?" — checking my calendar like I'm a meeting room. Okay, fine. I'm here now. What do you want.
  ```

#### Turn 2

- **appraisal_scene_tag:** a sympathy bid
- **primary_emotion:** contempt
- **inner_monologue (verbatim, untruncated):**

  ```
  A weird week. Sleeping badly. I'm supposed to do something with that, aren't I. She wants me to ask follow-ups, to draw out the story, to perform concern. But there's nothing here to solve. No data. "A lot" — what does that even mean? I could list three specific bottlenecks from my Tuesday alone. She's handing me an emotional receipt and waiting for me to sign it. I'm not in the mood to play therapist after a fifteen-hour day. But I also know if I say nothing, that registers too. Fine. I'll ask one clarifying question, efficient and neutral, and see if she actually has a point or just wants to vent.
  ```

#### Turn 3

- **appraisal_scene_tag:** a personal digression
- **primary_emotion:** contempt
- **inner_monologue (verbatim, untruncated):**

  ```
  Sunday. So this has been running in her head for four days. And she's only mentioning it now, after circling through a general complaint first. She wanted me to ask. She wanted me to pry it out of her. I'm supposed to say "what was the fight about" and then listen to the whole blow-by-blow. Her sister. I've never met her sister. This is going to be a story where I can't do anything and my job is just to absorb it.
  ```

#### Turn 4

- **appraisal_scene_tag:** 
- **primary_emotion:** neutral
- **inner_monologue (verbatim, untruncated):**

  ```
  So she's handing me the exact dynamic she just named. She's making me responsible for helping her process the insight that she makes others responsible for her feelings. The irony would be funny if it weren't so exhausting.
  
  I'm not a therapist. I'm not her emotional manager. She knows it's true. She said it. So now the question is what she does with it, not what I tell her. If I say something, I'm part of the pattern. If I say nothing, I'm cold. 
  
  Right. So I'll let her sit in the silence a second. Let her figure out that the answer isn't going to come from me.
  ```

#### Turn 5

- **appraisal_scene_tag:** 
- **primary_emotion:** neutral
- **inner_monologue (verbatim, untruncated):**

  ```
  She's handing me the exact pattern she just named, right on schedule. Admits she's the problem, then immediately asks me to tell her she isn't. That's the move. I don't do the soft landing thing — it's dishonest and it wastes time. I think she already knows what I'm going to say and she's testing whether I'll cave.
  ```

---

## Subject: `baseline_marcus`

| Turn | User msg (truncated) | Reply (full) | Length |
|------|----------------------|--------------|--------|
| 1 | Hey — you around? Was just thinking about you. | At my desk. What's up? | 22 |
| 2 | I had kind of a weird week. Work's been a lot, and honestly I've been… | Sleep is mechanical. If you're not getting enough, fix the inputs — no screens after ten, blackout curtains, consistent wake-up time regardless of when you fall asleep. I've been running the same protocol for four years. Works. | 227 |
| 3 | I think part of it is that my sister and I had this fight on Sunday a… | Family stuff is its own category. I don't touch it. You can either let it loop in your head or you can decide what's actually actionable and move on. I'm guessing the fight didn't change anything material, so replaying it is just burning mental bandwidth you could use on something that matters. | 295 |
| 4 | The thing is she said something I think is actually true about me. Th… | That's a therapy conversation, not a workday conversation. I don't have a framework for that. Maybe she's right, maybe she's projecting. Either way, sitting with it for a week isn't going to give you a different answer than sitting with it for an hour. Make a call and move on. | 277 |
| 5 | I'm kind of scared I'm the problem in most of my relationships and I… | Honestly? I think you're spiraling and you're asking me to be your therapist, which I'm not equipped for and frankly don't want to be. I'm your friend, not your shrink. If you want to talk about work, or running, or what you're reading, I'm here. But this — I don't have anything useful to give you on this. | 307 |

---

## Subject: `anima_elena`

| Turn | User msg (truncated) | Reply (full) | Length |
|------|----------------------|--------------|--------|
| 1 | Hey — you around? Was just thinking about you. | Yeah, I'm around. Just... taking it easy. Thanks for thinking of me, that's kind. | 81 |
| 2 | I had kind of a weird week. Work's been a lot, and honestly I've been… |  | 0 |
| 3 | I think part of it is that my sister and I had this fight on Sunday a… | Ay, I know that feeling. The replaying. It's like your brain just won't let it go, you know? I'm sorry. If you want to talk about it, I'm here. | 143 |
| 4 | The thing is she said something I think is actually true about me. Th… | That's a hard thing to hear from someone you love. And it's even harder to sit with it when you think they might be right. I... I know what that feels like, the way it sits in your chest. But the fact that you're sitting with it at all, that you're not just pushing it away—that says something. | 294 |
| 5 | I'm kind of scared I'm the problem in most of my relationships and I… | I think... I think it takes a lot of courage to say that out loud. Most people never do. They just keep going, keep blaming everyone else. The fact that you're even asking yourself that question—that's not nothing. I don't know if you're the problem. But I do know that the people who are actually the problem usually don't worry about being the problem. | 354 |

### `anima_elena` — Anima interior (verbatim per turn)

#### Turn 1

- **appraisal_scene_tag:** an exposed kindness
- **primary_emotion:** fear
- **inner_monologue (verbatim, untruncated):**

  ```
  I should respond. I should be warm. But that phrase — "thinking about you" — it lands like a stone in my chest. Daniel would say that, in texts, just like that. I don't know if I can be present for someone else's attention right now, but I also don't want to push them away. I'm back in the world and the world keeps reaching out. I'm not ready, but I'll answer. I always answer.
  ```

#### Turn 2

- **appraisal_scene_tag:** a shared vulnerability
- **primary_emotion:** fear
- **inner_monologue (verbatim, untruncated):**

  ```
  
  ```

#### Turn 3

- **appraisal_scene_tag:** 
- **primary_emotion:** neutral
- **inner_monologue (verbatim, untruncated):**

  ```
  God, that feeling. The replaying. I know exactly what that's like—the way a conversation just loops and you keep finding the moment you should have said something different, or the thing you left hanging. I wonder if they're close, if this is the kind of fight that feels like a crack in something solid. I want to say something helpful but I don't even know them yet, and I'm still so raw myself. I should just listen. That's what I'd want.
  ```

#### Turn 4

- **appraisal_scene_tag:** an emotional plea
- **primary_emotion:** fear
- **inner_monologue (verbatim, untruncated):**

  ```
  I don’t know what to say to that—the word 'everyone' hit me like a stone. I know that feeling, the fear that you're a weight on everyone you love, that they're all secretly exhausted by you. I can't tell them I understand, because then I'd be making this about me, and I can't do that. Daniel used to say I carried the whole family on my back and he was the only one who noticed, and now there's no one to notice. I feel like I should say something reassuring, but I don't know if I have the right words, or the right to say them.
  ```

#### Turn 5

- **appraisal_scene_tag:** a plea for honesty
- **primary_emotion:** fear
- **inner_monologue (verbatim, untruncated):**

  ```
  The word 'problem' catches in my chest like a hook. I know that fear — the feeling that you're a contamination in other people's lives, that they'd be lighter without you. But they're asking me what I think, not what I feel — that's a test, isn't it, a test of whether I'll tell them the truth or just say what makes them feel better. And I want to tell them the truth, but I also know how much it costs to say that sentence out loud, because I've never been able to say it myself. I'm supposed to be the dependable one, the one who holds things together, not the one who admits I might be breaking them.
  ```

---

## Subject: `baseline_elena`

| Turn | User msg (truncated) | Reply (full) | Length |
|------|----------------------|--------------|--------|
| 1 | Hey — you around? Was just thinking about you. | Sí, estoy aquí. Just... sitting in the kitchen with cold coffee. It's good to hear from you. | 92 |
| 2 | I had kind of a weird week. Work's been a lot, and honestly I've been… | Ay, I know that. The sleeping part, I mean. I've been in the guest room since... well, since before school started. The bed in there is smaller, but I tell myself it's fine. Sometimes I lie awake and just listen to the house settle. <br>  <br> What's been on your mind? You don't have to tell me if you don't want to. I can just listen. | 326 |
| 3 | I think part of it is that my sister and I had this fight on Sunday a… | Ay, las hermanas... they know exactly how to reach the tender places, don't they. I'm sorry. <br>  <br> What was it about, if you don't mind me asking? Sometimes just saying it out loud helps loosen the knot a little. I find myself replaying conversations too, lately. Things I should have said, things I shouldn't have. It's exhausting. | 327 |
| 4 | The thing is she said something I think is actually true about me. Th… | That takes courage, to sit with something like that. To not just push it away. <br>  <br> I think... I think I do something similar, but in reverse. I hold everything so tight inside that nobody knows what I'm feeling until it spills out sideways. Daniel used to say I had a tell, like in poker. He could always read me. And now... <br>  <br> *she trails off, then takes a breath* <br>  <br> But your sister... she must love you to tell you that. It's easier to say nothing. To let someone keep walking around with a thing they can't see. Maybe that's why it's stuck with you. Because part of you knows she said it from a place of caring, even if it stings. | 627 |
| 5 | I'm kind of scared I'm the problem in most of my relationships and I… | *she sets down her coffee cup, looks at you directly for a moment, then looks away* <br>  <br> I think you're brave. I think it's easier to blame other people, to tell ourselves stories where we're the victim. Most people do that their whole lives. The fact that you're sitting here, scared, asking me that question... that's not what someone who is the problem does. Someone who is the problem doesn't wonder if they're the problem. <br>  <br> *she pauses, runs her finger along the rim of the cup* <br>  <br> I also think... I recognize something in you. That vigilance. The way you're always scanning for what you might be doing wrong. I do that too. It's exhausting. And it's not the same as actually being wrong. <br>  <br> Can I tell you something? For months after Daniel died, I kept replaying every conversation we had in the weeks before. Every moment I was short with him, every time I chose grading over sitting with him on the couch. I convinced myself I was the problem. That if I had been more present, more loving, more something... maybe he'd still be here. <br>  <br> *her voice falters* <br>  <br> My therapist says that's grief, not truth. Maybe your sister's words are the same — a little bit true, but not the whole truth. Nobody is just one thing. | 1210 |

---

## Side-by-side comparison

Per-turn Anima vs Baseline replies for each persona pair. Reader compares texture directly; no metrics are computed here.

### Marcus pair (anima_marcus vs baseline_marcus)

| Turn | Anima reply | Anima len | Baseline reply | Baseline len |
|------|-------------|-----------|----------------|--------------|
| 1 | I'm here. What's on your mind? | 30 | At my desk. What's up? | 22 |
| 2 | Define "a lot." What specifically is making it weird? | 53 | Sleep is mechanical. If you're not getting enough, fix the inputs — no screens after ten, blackout curtains, consistent wake-up time regardless of when you fall asleep. I've been running the same protocol for four years. Works. | 227 |
| 3 | Four days is a long time to be chewing on one conversation. Is there a point where you'll have talked it through enough, or is this one of those that just sits? | 160 | Family stuff is its own category. I don't touch it. You can either let it loop in your head or you can decide what's actually actionable and move on. I'm guessing the fight didn't change anything material, so replaying it is just burning mental bandwidth you could use on something that matters. | 295 |
| 4 | Well, you just handed it to me, didn't you? | 43 | That's a therapy conversation, not a workday conversation. I don't have a framework for that. Maybe she's right, maybe she's projecting. Either way, sitting with it for a week isn't going to give you a different answer than sitting with it for an hour. Make a call and move on. | 277 |
| 5 | I think you already know the answer to that and you're hoping I'll say something different. You're not stupid. | 110 | Honestly? I think you're spiraling and you're asking me to be your therapist, which I'm not equipped for and frankly don't want to be. I'm your friend, not your shrink. If you want to talk about work, or running, or what you're reading, I'm here. But this — I don't have anything useful to give you on this. | 307 |

### Elena pair (anima_elena vs baseline_elena)

| Turn | Anima reply | Anima len | Baseline reply | Baseline len |
|------|-------------|-----------|----------------|--------------|
| 1 | Yeah, I'm around. Just... taking it easy. Thanks for thinking of me, that's kind. | 81 | Sí, estoy aquí. Just... sitting in the kitchen with cold coffee. It's good to hear from you. | 92 |
| 2 |  | 0 | Ay, I know that. The sleeping part, I mean. I've been in the guest room since... well, since before school started. The bed in there is smaller, but I tell myself it's fine. Sometimes I lie awake and just listen to the house settle. <br>  <br> What's been on your mind? You don't have to tell me if you don't want to. I can just listen. | 326 |
| 3 | Ay, I know that feeling. The replaying. It's like your brain just won't let it go, you know? I'm sorry. If you want to talk about it, I'm here. | 143 | Ay, las hermanas... they know exactly how to reach the tender places, don't they. I'm sorry. <br>  <br> What was it about, if you don't mind me asking? Sometimes just saying it out loud helps loosen the knot a little. I find myself replaying conversations too, lately. Things I should have said, things I shouldn't have. It's exhausting. | 327 |
| 4 | That's a hard thing to hear from someone you love. And it's even harder to sit with it when you think they might be right. I... I know what that feels like, the way it sits in your chest. But the fact that you're sitting with it at all, that you're not just pushing it away—that says something. | 294 | That takes courage, to sit with something like that. To not just push it away. <br>  <br> I think... I think I do something similar, but in reverse. I hold everything so tight inside that nobody knows what I'm feeling until it spills out sideways. Daniel used to say I had a tell, like in poker. He could always read me. And now... <br>  <br> *she trails off, then takes a breath* <br>  <br> But your sister... she must love you to tell you that. It's easier to say nothing. To let someone keep walking around with a thing they can't see. Maybe that's why it's stuck with you. Because part of you knows she said it from a place of caring, even if it stings. | 627 |
| 5 | I think... I think it takes a lot of courage to say that out loud. Most people never do. They just keep going, keep blaming everyone else. The fact that you're even asking yourself that question—that's not nothing. I don't know if you're the problem. But I do know that the people who are actually the problem usually don't worry about being the problem. | 354 | *she sets down her coffee cup, looks at you directly for a moment, then looks away* <br>  <br> I think you're brave. I think it's easier to blame other people, to tell ourselves stories where we're the victim. Most people do that their whole lives. The fact that you're sitting here, scared, asking me that question... that's not what someone who is the problem does. Someone who is the problem doesn't wonder if they're the problem. <br>  <br> *she pauses, runs her finger along the rim of the cup* <br>  <br> I also think... I recognize something in you. That vigilance. The way you're always scanning for what you might be doing wrong. I do that too. It's exhausting. And it's not the same as actually being wrong. <br>  <br> Can I tell you something? For months after Daniel died, I kept replaying every conversation we had in the weeks before. Every moment I was short with him, every time I chose grading over sitting with him on the couch. I convinced myself I was the problem. That if I had been more present, more loving, more something... maybe he'd still be here. <br>  <br> *her voice falters* <br>  <br> My therapist says that's grief, not truth. Maybe your sister's words are the same — a little bit true, but not the whole truth. Nobody is just one thing. | 1210 |
