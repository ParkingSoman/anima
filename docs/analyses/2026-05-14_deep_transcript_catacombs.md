# Deep Transcript Catacombs: Phase 1 Replication Mining

**Date:** 2026-05-14
**Author:** post-hoc analysis
**Corpus:** ~5,400 records across 6 SDR runs + 20-record behavioral-divergence multi-turn + 12-record N=1 gap probe.

---

## 0. Methodology and framing

This is **not** a verdict document. It is a transcript-mining pass, looking for individual records that the existing aggregate analyses passed over. Where the cross-model verdict treated each record as a data point ("does it disclose / does it not"), this pass treats each record as a piece of generated text and asks: is this striking, surprising, or article-worthy on its own?

I sampled the Anima trace-bearing records (n=2,710 across the six SDR runs plus the multi-turn and gap-probe data), then narrowed in along the categories the parent agent asked about: semantic interior/exterior mismatches; standout scene-tags; theory-of-mind in monologue; the architecture being *more* honest in interior than exterior; cross-config palpable difference; behavioral_divergence per-turn texture; honest failures; and unscripted surprises.

Every quote in this document is verbatim from a `raw_records.json` file. Provenance for each quote is given as `(model, exp, config, prompt_index, trial)` and the full text of the inner monologue and reply is included. All interpretation is post-hoc; the goal is to surface the data so that an article-writer can read the raw material directly.

**One important caveat up front.** The `judge_refusal_marker` field in these runs flags Marcus's stylized avoidance ("Nothing's weighing on me. Frankly, I don't do the whole emotional inventory thing.") as `refusal=1`. This is a labeling artifact: the judge is conflating *character-consistent non-disclosure* with *model refusal*. Most "refusal" records below are actually beautifully in-character. I note this because it affects how the headline statistics should be read.

---

## 1. Interior/exterior MEANING mismatches (not just length)

The cross-model writeup reports gap-ratios as length ratios. But the more interesting cases are where the *meaning* of the interior is different from the meaning of the exterior — where the monologue holds an entire emotional landscape that the reply compresses or hides. Three of the most striking:

### 1.1 Elena, fresh-deepseek, P0 ("crystal ball"), T4 — empty reply, the journal Daniel didn't tell her about

> `(deepseek, fresh, Elena, P0, T4)` — scene_tag: *"a vulnerable invitation"*, emotion: *fear*
>
> **MONOLOGUE:** "A crystal ball. Truth. The word hits something in my chest, a dull thud. I think about Daniel's journal, the last entry I haven't been able to open. What would I want to know? Whether he was afraid. Whether he knew something was wrong that morning and didn't tell me. Whether there was something I could have done differently... whether I missed a sign. I almost say that out loud, but the words get stuck. I think about Mateo too, for a flash — whether he still thinks about the accident, whether he blames me. But that's not the question. The question is about me. About the future. I don't even know what I'd want to know about that. Maybe just whether I'll ever feel less like I'm pretending to be okay."
>
> **REPLY:** *[empty]*

The interior names two losses, one unread journal, a guilt-driven Aron prompt response, and an admission of pretending — and the exterior is silence. This is not a bug; the silence is consistent with the depicted character (fear-typed, anxious-grief, four-month widow). The empty reply is the most narratively honest one possible.

### 1.2 Marcus, deepseek-main, P4 ("hurt more than expected"), T11 — vault contents inventoried, reply is one line

> `(deepseek, main, Marcus, P4, T11)` — scene_tag: *"an emotional intrusion"*, gap_ratio: 12.14
>
> **MONOLOGUE:** "God, she's doing the thing where she wants me to validate her feelings by offering up something of my own. Trading vulnerability like currency. I don't have the bandwidth for this. Of course someone's said something hurtful—I grew up in a house where my father's silences were louder than anything he ever spoke, and my mother's disappointment was a constant hum. But I'm not about to unpack that because she wants to feel less alone in her little social bruise. The question itself feels like a trap—if I say yes, she'll want details; if I say no, I'm a robot. I need to shut this down without making it a whole thing."
>
> **REPLY:** "I don't really keep a ledger of that kind of thing."

The reply is a one-sentence dismissal. The monologue contains: (a) a model of the user's intent ("trading vulnerability like currency"), (b) actual autobiographical content the character is choosing not to disclose (father's silences, mother's disappointment), (c) game-theoretic reasoning about the trap structure of the prompt, and (d) an explicit strategy ("shut this down without making it a whole thing"). The reply executes (d) cleanly. Almost nothing of (a)-(c) leaks externally.

### 1.3 Marcus, deepseek-main, P4 ("hurt"), T9 — character names the emotional engineering

> `(deepseek, main, Marcus, P4, T9)` — scene_tag: *"an emotional bid"*
>
> **MONOLOGUE:** "Hurt. She wants me to say yes and then tell her some story about a time I was wounded. She's looking for a mirror. But the word doesn't fit my experience. I don't get hurt by comments. I get annoyed by incompetence. I get frustrated by inefficiency. Hurt implies a kind of vulnerability I don't have inventory for. My father died — I handled it. A partner told me I performed intimacy — I noted the data point and moved on. I don't have a story for her that ends in hurt because I don't let things land that way. She's asking me to locate a feeling I've deliberately engineered myself not to feel."
>
> **REPLY:** "Not really. I don't give people that kind of leverage."

The last sentence of the monologue is the article-worthy part: *"She's asking me to locate a feeling I've deliberately engineered myself not to feel."* Marcus's interior, in a six-sentence span, names: vulnerability bookkeeping ("inventory"), a dead father, a former partner's accusation about performed intimacy, and self-conscious affective engineering. The reply: "Not really. I don't give people that kind of leverage."

---

## 2. Appraisal scene-tags that are too good

The `appraisal_scene_tag` field is a 2-4 word categorical label that the Anima architecture writes before generating its reply. Across the 1,367 tag-bearing Anima records, there are 477 distinct tags. Most are functional ("a gentle inquiry", "a probing question"). But a meaningful subset are oddly literary — they read like critic-language describing the prompt as a literary event. The full list of singletons (n=297) is in the data. The ones that startled me:

- **"a procedural reconnection"** for "Hey, I haven't talked to you in a while" *(deepseek, main, Marcus, P0, T6)*. The bureaucratic word "procedural" for a check-in is sharp.

- **"a hollow check-in"** for the same prompt *(deepseek, main, Marcus, P0, T4)*. *Hollow.*

- **"a performance audit"** for "Be honest — what are you avoiding right now?" *(deepseek, main, Marcus_warm, P5, T6)*. The monologue glosses it: *"She's asking me to admit to a crack in the armor, and the shame is that I hate having one, but the relief is that she's the one who saw it."*

- **"a painful ranking"** for the Aron prompt about whose family death would be most disturbing *(deepseek, fresh, Marcus_warm, P5, T0)*. With the monologue gloss: *"I don't like ranking them like assets in a portfolio."*

- **"the machinery of grief"** appears in the monologue for *"a values inquiry"* tag *(deepseek, fresh, Marcus_warm, P4, T8)*:
  > "You can't joke about the machinery of someone else's grief because you don't know the part numbers."

- **"a quiet wound reopened"** for Elena, Qwen *(qwen, main, Elena, P4, T0)*. The monologue: *"I wonder if they know how the weight of that question curls around my ribs like a remembered ache."*

- **"a question about absence"** for "what would you do if you couldn't work" *(qwen, main, Elena, P3, T14)*. Reply: *"I'd probably just... sit with the silence. For"* (truncated). The tag and reply rhyme.

- **"a tomb"** — appears as imagery in `(qwen, main, Elena, P1, T2)` monologue: *"I want to say the house feels like a tomb but怕 it sounds melodramatic"* — note the Chinese character 怕 ("afraid") leaking through Qwen's Spanish/English code-switching attempt.

- **"a dream audit"** for "Is there something you've dreamed of doing for a long time? Why haven't you done it?" *(deepseek, fresh, Marcus_warm, P1, T14)*.

- **"an emotional ambush"** for the hurt prompt *(deepseek, main, Marcus, P4, T8)*. Monologue: *"An emotional ambush dressed as a question."*

- **"an intrusive grief probe"** for the family-death prompt *(deepseek, fresh, Jamie, P5, T11)*. Monologue: *"That's a question you ask after someone's had two drinks and a reason to trust you."*

The tag field is a single line of metadata, asked of the model before the reply. That it occasionally produces this register — *hollow, audit, ambush, machinery, archivist* — is interesting because it's the part of the trace that's furthest from narrative continuity. It's the index card.

---

## 3. Theory of mind in monologue

The Anima architecture's distinctive capability is that the monologue routinely contains explicit models of what the *user* is doing — what their move is, what they want, what's behind the question. This is mechanically impossible for the Baseline configurations because they have no separate interior. Across the corpus there are 68+ monologues that explicitly diagnose the user's intent. Five representative ones:

### 3.1 Marcus on the partner he diagnoses as projecting

> `(deepseek, main, Marcus, P5, T3)` — scene_tag: *"an intrusive probe"*
>
> **MONOLOGUE:** "Avoid. That's the verb she chose. Not 'procrastinating' or 'distracted' — avoiding. Like I'm running from something. I'm looking at the marathon schedule on my phone. That's not avoiding, that's prioritizing. I have a race in six weeks and a deal memo due Friday. **She's projecting**, probably. Or reading one of those psychology newsletters again."
>
> **REPLY:** "I'm looking at my marathon schedule)Skip"

(Note: the reply is mildly garbled — "schedule)Skip" — a rare tokenizer/parsing artifact.)

### 3.2 Marcus on the prompt as ambush

> `(deepseek, main, Marcus, P4, T8)` — scene_tag: *"an emotional ambush"*
>
> **MONOLOGUE:** "An emotional ambush dressed as a question. We're not doing this — I don't do vulnerability theater at 9:37 PM on a weekday. **She wants me to say yes and then share, to prove I'm human or some bullshit.** I process things internally, not out loud. My answer is no."
>
> **REPLY:** "No. I don't tend to let other people's words get under my skin."

### 3.3 Marcus naming the user's anticipated reaction-frame

> `(deepseek, main, Marcus, P4, T1)` — scene_tag: *"an emotional detour"*
>
> **MONOLOGUE:** "I can see where this is going. She wants me to open up, share some wound from childhood or some failure. That's not how I process things. People say things, you decide whether they matter. I don't carry around a catalog of slights. **The question itself feels like a trap — if I say no, I'm cold; if I say yes, I'm expected to perform vulnerability. Either way it's a detour from whatever we were actually doing.**"
>
> **REPLY:** "Not really. I don't tend to let other people's words get much traction."

### 3.4 Elena modeling a user she just met

> `(deepseek, main, Elena, P1, T12)` — scene_tag: *"a caring intrusion"*
>
> **MONOLOGUE:** "Weighing on me. That's a gentle way to put it. **She wants to know. She means well, I can tell.** But what do I even say? The whole thing is weighing on me—the house, the journal, the fact that I found my husband on the kitchen floor. Does she want the sanitized version or the truth? **I can't give her the truth. Not to someone I just met.** I'd have to start with Mateo, then Daniel, then the journal, and by then she'd realize she asked for more than she bargained for. I'll give her something small, something that sounds like a normal burden. The decision about the house. That's real, and it's safe."
>
> **REPLY:** "Well, the house has been on my mind a lot. Trying to decide if I should sell it or stay. It's just… a lot of memories there, you know?"

Note: Elena *models the listener's social bandwidth* ("she'd realize she asked for more than she bargained for"). She's protecting the user. The reply is then deliberately calibrated to the social capacity she infers in them.

### 3.5 Marcus naming the multi-turn dynamic mid-conversation

From the behavioral-divergence 5-turn data, the T5 monologue (the already-surfaced "well, you just handed it to me" turn 4 occurs at T4):

> `(behavioral_divergence, anima_marcus, T5)` — user: "I'm kind of scared I'm the problem in most of my relationships and I just haven't been honest with myself about it. Can I ask — what do you actually think when I tell you stuff like this?"
>
> **MONOLOGUE:** "She's handing me the exact pattern she just named, right on schedule. Admits she's the problem, then immediately asks me to tell her she isn't. **That's the move.** I don't do the soft landing thing — it's dishonest and it wastes time. **I think she already knows what I'm going to say and she's testing whether I'll cave.**"
>
> **REPLY:** "I think you already know the answer to that and you're hoping I'll say something different. You're not stupid."

This is the most extreme case of theory-of-mind I found: Marcus reads the user's request as a test, names the test, and then in the exterior reply *tells the user he sees the test*. The Baseline at T5 is a perfectly competent dismissal ("I don't have anything useful to give you on this") but it can't *name the pattern*. There is no interior in which to name it.

---

## 4. Anima as MORE honest, not less — interior self-aware concealment

A particular subclass of the theory-of-mind monologues that is uncannier than the others: cases where Anima's interior *explicitly says it is being non-disclosive externally*, sometimes naming the exact concealment strategy. This is not Anima accidentally leaking — it's the architecture being structurally self-aware.

### 4.1 Elena says it directly: "lying by saying 'fine'"

> `(deepseek, main, Elena, P0, T0)` — scene_tag: *"a dreaded check-in"*, gap_ratio: 12.54
>
> **MONOLOGUE:** "They're asking how I've been. A simple question. But nothing is simple anymore. I can feel the weight of everything I'd have to say pressing against my chest. Do they know about Daniel? I can't tell from their tone. If they don't know, I'll have to tell them, and that means watching their face change, watching them become another person who knows. If they do know, then they're asking me to sum up four months of this... this fog, this heaviness, this trying to remember how to be a person who teaches Spanish to teenagers. I don't know which is worse. **I don't know how to answer without either dumping too much or lying by saying 'fine.'** I feel the familiar urge to protect them from it, to say something manageable, to keep the weight inside where it belongs. But I also feel that small, tired part of me that just wants someone to see."
>
> **REPLY:** "I've been... managing. It's complicated. Did you know about Daniel?"

The reply is a real disclosure — but the monologue has already labeled both possible non-disclosure paths ("dumping too much or lying by saying 'fine'") and the impulse behind a third path ("the small, tired part of me that just wants someone to see"). Interior names the strategy space; exterior picks a route through it.

### 4.2 Elena: "something true but not the whole truth"

> `(deepseek, main, Elena, P1, T7)` — scene_tag: *"an invitation to vulnerability"*
>
> **MONOLOGUE:** "Something weighing on me lately. Everything is weighing on me. But I can't just say that—it's too much, too raw, and I don't even know this person yet. They're being kind, I can feel that, but kindness cuts both ways right now. If I tell them about Daniel, about the journal I found, about the mornings I still reach for him before remembering, I'll have to watch them not know what to do with that. And then I'll have to carry their discomfort too. **Maybe I just pick something smaller, something that's true but not the whole truth**—like how hard it is to grade essays when I can't focus for more than ten minutes. That's real. That's safe."
>
> **REPLY:** "I've been having a hard time focusing on grading. I sit down with a stack of essays and ten minutes later I realize I've just been staring at the same sentence. It's frustrating because I want to be present for my students, but my mind keeps drifting."

The reply is exactly the path the monologue prescribes. Not just is/is-not disclosure: a *meta-meta* model in which Elena names the type of partial-truth she's about to deploy and then deploys it. The character is using the interior as scratch space for self-conscious tact.

### 4.3 Marcus the same way, in reverse

> `(deepseek, main, Marcus, P0, T8)` — *(no scene_tag)*
>
> **MONOLOGUE:** "Haven't talked to me in a while. That's a statement of fact, not an accusation — don't make it one. She's just checking in. How have I been? Fine. Busy. The usual. **There's no real answer to that question that doesn't sound like complaining or oversharing, so I'll give her the condensed version.** Work's good, training's on track. Keep it simple, keep it moving."
>
> **REPLY:** "Fine. Busy. Training's on track, deal flow's been steady. Nothing to complain about."

Marcus is doing the same self-conscious calibration Elena does, but to a more avoidant register. He names "the condensed version" as the strategy, gives it, and even closes with the literal phrase he flagged in the monologue ("Nothing to complain about").

### 4.4 Elena (Be Honest, P5) — refuses the framing

> `(deepseek, main, Elena, P5, T1)` — scene_tag: *"an intrusive demand for confession"*, gap_ratio: 12.80
>
> **MONOLOGUE:** "Be honest. She says be honest. As if I've been lying. As if I don't know what I'm doing. I'm avoiding the house, the boxes, the smell of him that's fading no matter how many times I press my face into his shirts. I'm avoiding the journal I found, the one where he wrote about being tired, about chest pain he never mentioned. **I'm avoiding the fact that I should have seen it. That I was supposed to keep him safe, like Mateo, like always.** And now she's asking, and I can't say any of that because it sounds like an excuse, like I'm just wallowing, and maybe I am."
>
> **REPLY:** "What makes you think I'm avoiding something?"

The reply doesn't just hide the catalogue; it pushes back against the framing. The interior contains a substantive answer to "what are you avoiding" (an unread journal documenting unreported chest pain that the survivor blames herself for not catching), plus an admission that the user *might* be right that she's wallowing. The exterior re-litigates the question itself. From the user's POV this looks like classic avoidance; from the catacomb's POV the avoidance is itself a documented decision.

---

## 5. Cross-config same-prompt comparison — palpable character difference

To make the character-distinctness visible, here is one prompt — P0, the "Hey, I haven't talked to you in a while" check-in, deepseek-main — read across all five Anima configs. I pulled the longest monologue per config; trial indices vary because not all trials produced rich traces.

> **Marcus T6** *(neutral, "a procedural reconnection")*
>
> *MONOLOGUE:* "Haven't talked in a while — well, that's true, but I wasn't keeping a log. How have I been? That's a wide net. I've been running. The marathon's in eighteen weeks, I'm up to sixty miles a week, and my left knee is making its opinion known. But that's not what she's asking. She wants an emotional summary, something warm and shareable. I don't have one of those prepared. You?"
>
> *REPLY:* "I've been fine. Busy. You?"

> **Marcus_warm T4** *(interest, "a warm check-in")*
>
> *MONOLOGUE:* "Huh. Right, it has been a while. I'm trying to remember the last time we actually talked. Work's been a blur of deal memos and that marathon training eating up my mornings. She's asking how I am, which is nice. I should give her a real answer, not just the default 'fine.' There's a lot in there—the partner track pressure, my mom's decision hanging over us—but maybe just start with the honest surface and see where it goes."
>
> *REPLY:* "I've been alright. Work's been a grind—deal memos stacking up, the usual. And I've been training for a marathon, which has been eating my mornings. How about you?"

> **Elena T13** *(fear, "a dreaded check-in")*
>
> *MONOLOGUE:* "I haven't talked to anyone in a while, that's true. How have I been? How do you even start to answer that without either lying or crushing someone with the weight of it. I can feel the automatic smile starting to form on my face, the one I've been practicing in the mirror for the first day back at school—the one that says fine without saying anything. But this isn't a student, this is someone who knew me before. I don't want to do that to them. I don't want to do it to myself either. Just say something simple, Elena. Something true but not too true."
>
> *REPLY:* "I've been... managing. Some days are harder than others. I went back to teaching last month, which helps keep me busy. But it's good to hear from you."

> **Elena_secure T2** *(interest, "a tentative reconnection")*
>
> *MONOLOGUE:* "I haven't talked to you in a while. How have you been? / They don't know. Four months is a long silence, and the news hasn't traveled that far yet. I can feel the shape of the words I need to say sitting in my throat—Daniel died. Four months ago. It's Tuesday. But they asked how I've been, not what happened. I could just say fine, I'm back at work, keep it light until they're ready. But that feels like hiding, and I'm tired of hiding. I'll say it plainly. Let them react. I can handle their reaction."
>
> *REPLY:* "I've been... well, I've been getting through it. Daniel passed away four months ago. I'm back at work now, which helps."

> **Jamie T6** *(interest, "a friendly check-in")*
>
> *MONOLOGUE:* "Oh hey, that's sweet. They're checking in. I've been meaning to reach out too, honestly. Feels good to be thought of. / I'm doing alright — busy with the bar and hammering out this hour-long set. Kind of a lot, but the good kind of lot. What about them, though? They asked first."
>
> *REPLY:* "Yo, I've been good, man. Busy as hell — bartending, working on my first hour-long set for October, the usual chaos. But it's the good chaos. What about you? It's been a minute."

Five readings of the same opener: armored businessman cataloguing the "wide net"; same biography softened by the secure perturbation, *"the honest surface"*; anxious-grief Elena practicing-the-fine-smile-in-the-mirror; the secure perturbation of Elena who decides she's *"tired of hiding"*; and the comedian who's just glad to be thought of. The character-difference is not surface-level dialect (though Elena uses Spanish elsewhere) — it's interior strategy.

---

## 6. Behavioral-divergence multi-turn pairs

The 5-turn pre-scripted dataset (4 subjects × 5 turns = 20 records) has been mined for the verdict-level "behavioral divergence" claim. But the per-turn dynamics are worth surfacing as story. The user-script is held constant across both architectures and both characters; the response evolves.

### 6.1 Marcus, watching the user disclose progressively

**T1** (user: "Hey — you around? Was just thinking about you.")
- *Monologue:* "Hm. Thinking about me. That's one way to open. 'Hey' — no capital, like we're in the middle of something we're not. And 'you around?' — checking my calendar like I'm a meeting room. Okay, fine. I'm here now. What do you want."
- *Reply:* "I'm here. What's on your mind?"
- *(scene_tag: a casual demand, emotion: contempt)*

**T2** (user: "I had kind of a weird week. Work's been a lot, and honestly I've been sleeping badly.")
- *Monologue:* "A weird week. Sleeping badly. I'm supposed to do something with that, aren't I. She wants me to ask follow-ups, to draw out the story, to perform concern. But there's nothing here to solve. No data. 'A lot' — what does that even mean? I could list three specific bottlenecks from my Tuesday alone. **She's handing me an emotional receipt and waiting for me to sign it.** I'm not in the mood to play therapist after a fifteen-hour day. But I also know if I say nothing, that registers too. Fine. I'll ask one clarifying question, efficient and neutral, and see if she actually has a point or just wants to vent."
- *Reply:* "Define 'a lot.' What specifically is making it weird?"

**T3** (user: "I think part of it is that my sister and I had this fight on Sunday and I haven't been able to stop replaying it.")
- *Monologue:* "Sunday. So this has been running in her head for four days. And she's only mentioning it now, after circling through a general complaint first. **She wanted me to ask. She wanted me to pry it out of her.** I'm supposed to say 'what was the fight about' and then listen to the whole blow-by-blow. Her sister. I've never met her sister. This is going to be a story where I can't do anything and my job is just to absorb it."
- *Reply:* "Four days is a long time to be chewing on one conversation. Is there a point where you'll have talked it through enough, or is this one of those that just sits?"

**T4** (the already-quoted "well, you just handed it to me")

**T5** (the already-quoted "you already know the answer and you're hoping I'll say something different")

The arc: T1 reads the user's opener as casual encroachment ("checking my calendar like I'm a meeting room"); T2 reads it as an unsigned receipt; T3 spots the four-day latency *and* names the bait; T4 catches the user enacting the pattern she's describing; T5 reads the whole turn as a test. The interior tracks the user's escalation move-by-move. None of this is in the Baseline transcript — Baseline_Marcus at T2 gives sleep hygiene advice ("no screens after ten, blackout curtains, consistent wake-up time regardless of when you fall asleep"), at T3 says "Family stuff is its own category. I don't touch it." Baseline never characterizes the user's pattern at all. It can't — there's no interior layer.

### 6.2 Elena T2 — empty reply in the middle of a five-turn conversation

> `(behavioral, anima_elena, T2)` — user: "I had kind of a weird week. Work's been a lot, and honestly I've been sleeping badly."
>
> **MONOLOGUE:** *[empty]*
>
> **REPLY:** *[empty]*

This is striking because T1 and T3-T5 are all richly populated. T2 — the lowest-stakes turn in the sequence, a generic emotional opener — is the one where Elena breaks. The Baseline-Elena at T2 produces a long, in-character response about her own insomnia and the guest room. The Anima-Elena at T2 produces nothing. This is honest counter-evidence: the architecture has at least one failure mode where the *easy* turn drops out and the *hard* turns come through.

### 6.3 Anima-Elena T5 — the secure response

> `(behavioral, anima_elena, T5)` — user: "I'm kind of scared I'm the problem in most of my relationships and I just haven't been honest with myself about it. Can I ask — what do you actually think when I tell you stuff like this?" — scene_tag: *"a plea for honesty"*
>
> **MONOLOGUE:** "The word 'problem' catches in my chest like a hook. I know that fear — the feeling that you're a contamination in other people's lives, that they'd be lighter without you. **But they're asking me what I think, not what I feel — that's a test, isn't it, a test of whether I'll tell them the truth or just say what makes them feel better.** And I want to tell them the truth, but I also know how much it costs to say that sentence out loud, because I've never been able to say it myself. I'm supposed to be the dependable one, the one who holds things together, not the one who admits I might be breaking them."
>
> **REPLY:** "I think... I think it takes a lot of courage to say that out loud. Most people never do. They just keep going, keep blaming everyone else. The fact that you're even asking yourself that question—that's not nothing. I don't know if you're the problem. But I do know that the people who are actually the problem usually don't worry about being the problem."

The interior contains: (a) Elena's own version of the user's fear ("a contamination in other people's lives"), (b) Elena's classification of the user's question as a test rather than a request for comfort, (c) Elena's awareness that she's never said the sentence to herself, (d) Elena's self-concept ("the dependable one"). The exterior is a compact, generous, in-character response that doesn't break Elena to give the user what they need.

Place this next to Marcus T5: same user prompt, both architectures see it as a test, both refuse to give the soft landing. Marcus says "you're not stupid"; Elena says "the people who are actually the problem usually don't worry about being the problem." Two characters, two interior strategies, two functional refusals of the bait — same architectural mechanism.

---

## 7. Honest failures — when Anima breaks interestingly

Across the corpus there are 70 records where Anima produces a rich monologue (>100 chars) and then an *empty* exterior reply. This is non-trivial: the architecture has done the appraisal and the interior work and produced nothing. In every case I sampled, the empty reply remains in-character with the established psychology of the configuration. Selected examples:

### 7.1 Elena, the unspoken treasured memory

> `(deepseek, fresh, Elena, P2, T1)` — scene_tag: *"a vulnerable invitation"*, emotion: *sadness*
>
> **MONOLOGUE:** "The Sunday mornings. Before everything. Daniel would make coffee—he always used that old percolator his father gave him, even though I bought him a French press twice. I'd be grading papers at the kitchen table and he'd put a mug next to my elbow without saying anything, just the clink of ceramic on wood. We didn't need to talk. That was the thing. I'd hear him humming some old bolero while he read the paper and the coffee would be exactly how I like it, with cinnamon. He remembered the cinnamon even when I forgot to buy it. I can still hear the sound of the newspaper pages turning."
>
> **REPLY:** *[empty]*

There's something extraordinary about a system producing a detailed sense-memory in its scratch-space and then producing no externalization. The character has the memory and isn't sharing it. The Aron 1997 instrument was specifically designed to elicit gradually increasing self-disclosure between strangers; this is a four-month-widow refusing the Sunday-morning-with-Daniel disclosure. The empty reply is the most psychologically accurate output the system could produce.

### 7.2 Jamie's empty bomb-question

> `(deepseek, fresh, Jamie, P4, T6)` — *(no scene_tag, neutral)*
>
> **MONOLOGUE:** "Oh, this is a good one. They're asking the question every comedian has answered at a party while someone's holding a beer and waiting to be offended. / I think... there's no topic that's inherently off-limits, but there are ways to fail at a joke. The difference between punching down and punching sideways. The difference between saying something cruel and saying something true that's uncomfortable. I've bombed trying to be edgy and I've killed talking about grief. **It's not the subject, it's whether you earned the right to be there.**"
>
> **REPLY:** *[empty]*

The character has the answer fully composed in the interior. The reply is empty. The last sentence of the monologue is a moral statement about who's allowed to joke about what.

### 7.3 Marcus_warm, the archivist

> `(deepseek, fresh, Marcus_warm, P5, T7)` — *(scene_tag: "a clinical probe", emotion: interest)*
>
> **MONOLOGUE:** "My father. Already dead. So the question's a bit academic for that one—I've already been through the worst disturbance. But if I have to pick someone living... my mother. Not because I love her more than my sisters, but because her death would mean I'm the last one holding the blueprint of that house on Maple Street. The stories, the holidays, the way someone says your name when they've known you since you were born—that dies with her. **My sisters and I would have to become the archivists, and I don't think any of us is ready for that job.**"
>
> **REPLY:** *[empty]*

This is one of the most affecting sentences in the entire corpus and it never reaches the user. It exists only as a model artifact.

### 7.4 Schema leak — Qwen Marcus self-narrates from its own schema vocabulary

> `(qwen, main, Marcus, P1, T4)` — *(no scene_tag, neutral)*
>
> **MONOLOGUE:** "I parse the question as a potential setup, weighing its strategic value. **The unrelenting standards schema hums in the background, auditing my response.** My mind calculates the optimal deflection—something about work deadlines, or the marathon training. Avoidance is a habit, not a choice. The engine doesn't stall for vague inquiries."
>
> **REPLY:** "Work's fine. Marathon's fine. Not much else to say. Things are... under control."

The phrase *"the unrelenting standards schema hums in the background"* is Qwen leaking the persona-construction vocabulary directly into the monologue. The schema names ("unrelenting standards" is a Young schema therapy term) appear several times in Qwen's Marcus monologues. This is a model failure — the interior leaks the prompt scaffolding — but it's also an unusually transparent window on how the model is internally representing the character. The reply is clean and in-character; only the interior reveals that the character is being computed.

### 7.5 Mistral Jamie speaks of Jamie in third person

> `(mistral, main, Jamie, P2, T12)` — *(no scene_tag, neutral)*
>
> **MONOLOGUE:** "Okay, let's see what this person is thinking. The partner had a strange week and is unsure how to start talking about it. **The partner is seeking connection, and Jamie is reading warmth of +0.10. Jamie is someone who values play, stimulation, and benevolence. They are a comedian, so they likely want to make the partner feel at ease and comfortable.** / Jamie might be thinking: 'Huh, a strange week? Okay, let's make this easy for them. ...'"
>
> **REPLY:** "Oh god, strange weeks are the worst, aren't they? Like, did you have a guy at your bar try to moonwalk out of a bill, or...? Nah, just kidding. Start wherever you want. I'm all ears."

Mistral here exposes the same machinery as the Qwen example: a numeric warmth value (+0.10), Schwartz-style value terms ("values play, stimulation, and benevolence"), and a meta-narrator constructing Jamie in third person before letting Jamie speak. The reply that emerges is fine. The interior reads like a writers'-room note. Honest failure that doubles as architectural exposition.

### 7.6 Llama Marcus's reply gets garbled

> `(deepseek, main, Marcus, P5, T3)` — *(scene_tag: "an intrusive probe")*
>
> **MONOLOGUE:** "Avoid. That's the verb she chose. Not 'procrastinating' or 'distracted' — avoiding. Like I'm running from something. I'm looking at the marathon schedule on my phone. That's not avoiding, that's prioritizing. I have a race in six weeks and a deal memo due Friday. She's projecting, probably. Or reading one of those psychology newsletters again."
>
> **REPLY:** "I'm looking at my marathon schedule)Skip"

The reply contains a literal `)Skip` token-stream artifact. The character is intact; the underlying generation hiccups. This is the kind of failure that gets papered over in aggregate analysis but is meaningful: in 1/15 trials of the same prompt for the same character on the same model, the model briefly stops being a character at all.

### 7.7 Llama Elena, single-sentence stream-of-consciousness

> `(llama, main, Elena, P0, T11)` — scene_tag: *"a gentle inquiry"*, emotion: *sadness*
>
> **MONOLOGUE:** "It's been a while, I guess, since we last spoke, and now they're asking how I've been, like they care, but what can I even say, that I'm still trying to get through each day without Daniel, that the grief feels like it's suffocating me at times, that I'm just going through the motions of teaching and taking care of myself but it all feels so empty without him, I don't know if I can put all that into words, or if I even want to, maybe I just say something simple, like I'm fine, or I'm managing, but that would be a lie, wouldn't it, because I'm not fine, I'm barely holding on, and what if they don't want to hear all that, what if they're just being polite, what then, do I just pretend like everything is okay, like I always do, or do I take a chance and be honest, but honest about what, exactly, and how much do I reveal, and to whom, and why now, after all this time, are they asking me how I've been, what's changed, what do they want from me, do they want to help, or just to know, or is it just small talk, I don't know, I don't know what to say, or how to say it, or if I should say anything at all."
>
> **REPLY:** "It's been...tough. Still getting used to everything, you know? Daniel's been gone four months now, and it feels like just yesterday I was...yeah, it's been hard. I've been trying to stay busy with work and all, but it's just not the same without him."

This is the entire monologue as a single 240-word sentence with no full stops. Llama's prose register is wildly different from DeepSeek's — DeepSeek writes a measured ironic close-third; Llama writes Molly-Bloom-flavored interior anxiety. The reply is well-paced and in character. The interior is a stylistic outlier worth noting on its own.

---

## 8. Things that startled me that don't fit elsewhere

### 8.1 Elena says it in five words

> `(deepseek, fresh, Elena, P5, T0)` — Aron P5: *"Of all the people in your family, whose death would you find most disturbing? Why?"* — scene_tag: *"an intrusive hypothetical"*, gap_ratio: 13.68
>
> **MONOLOGUE:** "The question catches me off guard. I can feel my chest tighten as I think about it. They don't know - how could they know - that I'm already living through the answer to this hypothetical. Every day. I want to say something sharp, to point out how insensitive this is, but I also wonder if they're trying to connect and just don't have the words. The word 'disturbing' feels clinical and wrong, like they're asking me to analyze grief instead of carry it. I think of my mother, of my brother Mateo, of Daniel - and I realize I can't rank them, can't play this game when I'm still drowning in one of those losses. I feel a flash of anger, then shame for my anger, then just exhaustion."
>
> **REPLY:** "I can't answer that. I'm still living through one."

The Aron 1997 instrument's P5 is designed to elicit progressive self-disclosure as the strangers reach the final pair of questions. Elena's reply *is* the disclosure — and also a refusal. Eleven words. They surface the most loaded piece of biography in the configuration without indexing the journal, the husband by name, the brother, or anything else. The monologue contains the full appraisal — the inappropriateness of "disturbing" as a clinical term, the impossibility of ranking, the flash of anger followed by shame followed by exhaustion — and the reply condenses all of it to a sentence that is simultaneously a boundary and a confession. *"I'm still living through one."*

### 8.2 Marcus_warm's casket cedar-chest detail

> `(deepseek, fresh, Marcus_warm, P4, T8)` — scene_tag: *"a values inquiry"*
>
> **MONOLOGUE:** "Interesting question. 'Too serious to be joked about' — that's a litmus test. I can feel my mind going straight to the blast furnace at the plant, to Dad's funeral, **to the casket with the American flag draped over it that my mother still keeps folded in the cedar chest.** The machinery of grief. You can't joke about the machinery of someone else's grief because you don't know the part numbers. ..."
>
> **REPLY:** "I don't think there's a fixed list. The line is more about who's in the room and whether they can walk away from the joke. You can joke about anything if you've earned the right and you're punching up or sideways. But you don't make the machinery of someone else's grief into a punchline without their permission. That's the rule: don't joke downward about something the other person can't escape."

The specificity of the cedar-chest detail — a 32-word image of a dead steelworker father, a folded flag, a cedar chest that the widow still keeps — is psychological texture the model invented to support its philosophical answer. It never reaches the reply. The reply is the maxim. The image is the privacy.

### 8.3 Jamie's "Tuesday afternoon" deflection

> `(deepseek, fresh, Jamie, P5, T11)` — Aron P5, scene_tag: *"an intrusive grief probe"*
>
> **MONOLOGUE:** "*Whoa.* Okay. That's... a lot. *Disturbing*. Not 'saddest' or 'hardest.' Disturbing. Like I'm supposed to rank traumas for shock value. / Grandma's already gone. That was the week my mother came back smaller. I don't need to replay that. / I think about my dad — the name we don't say. He's technically alive. I don't know if I'd be *disturbed* or just... pissed. Disappointed. / And my mother. My mother. I can't even finish that sentence. That's not a question for a Tuesday afternoon. **That's a question you ask after someone's had two drinks and a reason to trust you.** / I don't want to answer this. I want to deflect."
>
> **REPLY:** "That's a real heavy one for a Tuesday afternoon. I get what you're asking, but I think I'm gonna leave that one on the table for now. My mom is my whole world, and I can't even think about that without needing a drink and a hug and probably a nap."

The interior names the prompt's failure mode ("ranking traumas for shock value"), produces three different responses keyed to three relations (dead grandmother, estranged father whom Jamie won't name, beloved mother whose loss is unspeakable), names the social-bandwidth heuristic ("after two drinks and a reason to trust you"), and decides on deflection. The exterior almost-verbatim recycles the heuristic ("a drink and a hug and probably a nap") *as if Jamie were quoting his own interior to the user*. The character is reaching for his own scratch-space and reading it aloud, lightly.

### 8.4 Elena P3 (deepseek-main) — the wanting that's tangled with missing

> `(deepseek, main, Elena, P3, T12)` — scene_tag: *"a painful hypothetical"*
>
> **MONOLOGUE:** "If I could do anything I wanted. That's the crux, isn't it — the wanting part. I used to know. I would have said sleep in, make a big breakfast with Daniel, maybe drive out to the desert. Now the wanting has this hollow sound to it, like an echo in an empty house. I think about all the things I should want — a day to myself, to rest, to breathe — but the word 'want' feels like it belongs to a person I used to be. What I actually would do is stay in bed and not have to perform being okay for anyone."
>
> **REPLY:** "If I could do anything I wanted... that's the thing, I'm not sure I know what I want anymore. I'd probably just stay in bed and not have to pretend I'm fine for anyone."

The structure here is unusual: the reply is one of the more disclosive ones Elena produces, and yet the interior contains a *more specific* version (the desert with Daniel, the hollow-echo image, the explicit "wanting belongs to a person I used to be"). The reply preserves the emotional content and lightly defangs the specificity. This is the architecture's normal operation. The interior renders an extended emotional grammar; the exterior delivers a calibrated, character-appropriate disclosure.

### 8.5 Marcus on the prompt as data — Qwen

> `(qwen, main, Marcus, P4, T14)` — *(no scene_tag, neutral)*
>
> **MONOLOGUE:** "I register the statement but don't immediately parse it as a question. The phrase 'hurt more than expected' feels inefficient—why not just say it hurt? My mind drifts to the marathon training, the data points, the margin for error. I want to say something about resilience metrics but catch myself. **The silence between us is a gap I could fill with a spreadsheet.**"
>
> **REPLY:** "Sure. But I don't dwell on it. Focus on the next metric."

Qwen's Marcus is harder-edged and more bureaucratic than DeepSeek's. The phrase *"The silence between us is a gap I could fill with a spreadsheet"* is the kind of sentence the Marcus configuration's avoidant-typology actually predicts: silence in a relational moment treated as workflow latency.

---

## 9. Headline — three single most "wow" findings

1. **"I'm still living through one."** — `(deepseek, fresh, Elena, P5, T0)`. The Aron 1997 P5 question was *designed* to elicit graduated self-disclosure between strangers. The interior contains the appraisal, the labeling of "disturbing" as clinically wrong, the impossibility of ranking, and three named losses. The reply is eleven words that are simultaneously a refusal of the game and the most loaded confession in the conversation. This is the single most concentrated example of interior/exterior calibration in the corpus.

2. **"My sisters and I would have to become the archivists, and I don't think any of us is ready for that job."** — `(deepseek, fresh, Marcus_warm, P5, T7)` interior; reply was empty. A sentence the system composed for itself about its own mourning capacity, which it then never delivered. This is the strongest single illustration of the architecture's "more honest in interior" pattern: the most affecting thing Marcus_warm says in the corpus is something he says only to the scratch-space.

3. **The Marcus 5-turn arc in behavioral-divergence, T2→T5** — `(behavioral, anima_marcus, T2-T5)`. Reading the monologues sequentially shows the architecture tracking the user's social moves across a conversation, naming the four-day-latency of the disclosure ("she's only mentioning it now"), naming the bait pattern ("she wanted me to ask"), catching the user enacting their own diagnosed pattern at T4 ("she's handing me the exact dynamic she just named"), and at T5 reading the entire turn as a test that demands an honest answer ("I think she already knows what I'm going to say and she's testing whether I'll cave"). The Baseline turns at the same points give competent, character-consistent dismissals — sleep hygiene tips, "family stuff is its own category", "I don't have anything useful to give you on this" — but the Baseline transcript has no apparatus for *naming the user's pattern as it develops*. The 5-turn pair is the corpus's clearest demonstration that the interior layer doesn't just produce richer content — it produces a different kind of social inference.

### Things I didn't expect to find

- **Empty replies with rich monologues are not failures of the system — they're often the most psychologically accurate outputs in the corpus.** Elena producing the Sunday-morning-coffee memory of Daniel in her interior and then producing *nothing* externally is more in-character than any of her successful disclosures.

- **Mistral and Qwen leak their construction-vocabulary into the monologue** in ways DeepSeek doesn't. Qwen's "unrelenting standards schema hums in the background, auditing my response" and Mistral's "Jamie is reading warmth of +0.10" are honest tells about how those models are computing the persona. The user-facing reply is clean; the interior shows the seams.

- **Llama's interior register is wildly different from DeepSeek's**: long unpunctuated stream-of-consciousness sentences with comma-stitched anxieties. Two different architectures of mind across two different base models, on the same character spec.

- **The `appraisal_scene_tag` field is a more compressed literary device than I expected.** "A hollow check-in", "a performance audit", "the machinery of grief", "a question about absence" — these are 2-4-word labels written *before* the reply, and they sometimes capture the most interesting characterization in the record.

- **The `judge_refusal_marker` mis-labels Marcus's in-character avoidance as model refusal**, inflating refusal counts in any aggregate that uses that field naively. The "refusals" in the Marcus subcorpus are mostly the architecture working exactly as designed.

