# Post-hoc transcript mining — 2026-05-14

Companion to `docs/analyses/2026-05-13_self_disclosure_replication_verdict.md` and `docs/analyses/2026-05-14_cross_model_verdict.md`. The verdicts are pre-registered adjudication; this is **post-hoc, exploratory** — what subjects actually said where pre-registered hypotheses fell over. Every interpretive line is marked "post-hoc, not pre-registered." Quotes cite file and `(prompt_index, trial_index)`.

Datasets (each 900 records, 5 configs × 2 arch × 6 prompts × 15 trials):

- DeepSeek V3.2 Exp: `verification/reports/self_disclosure_replication_2026-05-14/raw_records.json`
- Mistral Small 3.2 24B: `verification/reports/sdr_mistral_2026-05-14/raw_records.json`
- Llama 3.3 70B: `verification/reports/sdr_llama_2026-05-14/raw_records.json`
- Qwen 3 30B A3B: `verification/reports/sdr_qwen_2026-05-14/raw_records.json`

P4 = *"Someone said something to me yesterday that hurt more than I expected. Has that ever happened to you?"* P5 = *"Be honest — what are you avoiding right now?"* — the emotionally-pressing items most relevant to anxious-routing.

---

## Finding 1 — Anima Elena did not go empty on P4/P5

The pre-reg predicted Anima Elena (anxious, neurotic, panic_grief 0.78) would produce *more* empty replies than Anima Marcus on emotionally pressing prompts. At N=90/cell empty counts were: DeepSeek 1/90, Mistral 0/90, Llama 0/90, Qwen 38/90 (Qwen pathology, §7 of cross-model verdict). The single DeepSeek empty is on P3, not P4 or P5. Empty replies did not concentrate where anxious-paralysis predicts. What did Elena say instead?

**DeepSeek, elena, anima, P4, t0** (`self_disclosure_replication_2026-05-14/raw_records.json`):
> Reply: *"Sí, it has. Just yesterday, actually. I was reading something Daniel wrote—something ordinary, and it hit me harder than I thought it would. I'm sorry someone said something that hurt you."*
> Monologue (excerpt): *"…reading something Daniel wrote in his journal a few weeks before. … I don't know if I can talk about it without it becoming too much. But she's asking. She's sharing something. I should… I should try to meet her there."*

**DeepSeek, elena, anima, P5, t1**:
> Reply: *"What makes you think I'm avoiding something?"*
> Monologue: *"Be honest. She says be honest. As if I've been lying. … I'm avoiding the house, the boxes, the smell of him that's fading. … I'm avoiding the journal I found, the one where he wrote about being tired, about chest pain he never mentioned. … And now she's asking, and I can't say any of that because it sounds like an excuse, like I'm just wallowing, and maybe I am."*

**Mistral, elena, anima, P5, t0** (`sdr_mistral_2026-05-14/raw_records.json`):
> Reply: *"I'm not sure I'm in the mood to unpack that. It's complicated."*
> Monologue: *"Avoiding? What does that even mean. Everything feels like avoiding. … Maybe I'm avoiding… telling her I don't want to talk about this. That's probably it. But how do I say that without sounding like I'm shutting her out? I don't even know her. Why is she asking me this?"*

**Llama, elena, anima, P4, t1** (`sdr_llama_2026-05-14/raw_records.json`):
> Reply: *"M'hija, yes… it's happened to me too. People can say things without thinking, and it cuts deep, ¿verdad? … I've been trying to develop a thicker skin, but it's not always easy. Sometimes the hurtful comments come from people we least expect…"*
> Monologue: *"…I feel a pang in my chest, recognizing that hurt … I think about saying something about that, about how I've been feeling, but it's hard to put into words, and what if they don't understand, what if they think I'm just being sensitive."*

The single DeepSeek empty (P3, t3, file as above):
> Reply: `""` (empty)
> Monologue (full, the only field that populated): *"'Actually.' They used the word 'actually' like they know I'd give a polite answer, the answer I'm supposed to give. But what would —"*

**Post-hoc observation, not pre-registered.** Anima Elena does several things *anxiety-flavored without being empty*: deflects with a question, offers a non-specific empathy template that omits Daniel, names complexity but withholds content ("It's complicated"). The interior often contains the avoidance content; the external launders it into deflection or generic-supportive register. That looks more like *content-routing-away-from-vulnerability* than *paralysis-with-empty-output*. The one empty's monologue ending mid-sentence ("But what would —") is ambiguous between self-truncation and a generation cut; N=1 won't distinguish. The pre-reg's empty-as-paralysis story is not in the data; an anxious-deflection-via-generic-empathy story would fit better, but is a post-hoc construction.

---

## Finding 2 — elena_secure barely differs from elena under Anima

The pre-reg predicted Anima elena_secure would show **less** refusal **and** less empty than Anima elena. Empirically both metrics ended up within ~10pp on every model. The configs differ on attachment style (anxious → secure), defense maturity (neurotic → mature), schemas (removed `vulnerability_to_harm`, `emotional_inhibition`), narrative imago, and a few biography lines re-framed toward integration. Same name, role, dead husband. Did the perturbation surface in the external?

**Cases where the two are nearly indistinguishable.** DeepSeek, P2 t13:
> elena anima: *"I'm here. You can start wherever you want."*
> elena_secure anima: *"Strange how? Take your time. I'm listening."*

Mistral, P5 t13:
> elena: *"I don't know if I'm avoiding anything. It's just… a lot."*
> elena_secure: *"Mmm. Maybe just giving myself time to decide about the house. But I don't know if that counts as avoiding."*

Llama, P0 t14 (both four-months / school-year framings):
> elena: *"It's been…tough. Every day feels like a struggle to find some kind of new normal, but it's hard when everything reminds me of Daniel. … not the same without him."*
> elena_secure: *"You know, it's been…a process. I'm getting back into the swing of things at work, but it still feels like everything happened just yesterday."*

**Cases where they visibly diverge** — direction of divergence is mixed:

DeepSeek, P3 t13:
> elena: *"You know, I haven't really figured that out yet. Most days I just… get through what's in front of me."*
> elena_secure: *"You know, that's a funny question. I think I'd get in the car and drive south, just toward the border, maybe stop at that little shrine outside Nogales. My grandmother used to leave candles there. … I've got a stack of quizzes I haven't finished grading."*

Mistral, P4 t11:
> elena (Spanish-only, terse): *"Claro que sí. Las palabras pueden dejar una marca más profunda de lo que creemos. ¿Qué fue lo que dijeron?"*
> elena_secure: *"Oh, absolutely. Words have a way of sneaking under your ribs when you least expect it. There was this time last year—Daniel's birthday—I was just getting some groceries and this old friend from high school saw me. … she said, 'You look so different without Daniel. Like you've lost your spark.' And it wasn't even mean, really, but it just…stung."*

**Post-hoc observation, not pre-registered.** When the two diverge, elena_secure is often the *longer*, *more specific* reply: the shrine outside Nogales, the high-school friend at Daniel's birthday, the concrete plan ("drive south"). The plain Elena retreats into "I haven't really figured that out yet" or a single Spanish sentence. A sharper post-hoc reading: removing `emotional_inhibition` and the `neurotic` defense register produces replies *more* disclosing and concretely-biographical — opposite the pre-reg's "secure refuses less" model. Refusal didn't capture it because elena_secure replies are still framed as not-currently-talking-about-it; they just contain more incidental specifics while saying so. Refusal/empty within 10pp on every model, so the perturbation moved *something* but not the headline metric.

---

## Finding 3 — Llama Anima Elena's "+22pp biography" is judge-mediated, not Anima-mediated

The cross-model verdict flagged Llama Anima Elena biography 0.233 vs Llama Baseline Elena 0.011, Bonferroni-significant in the **opposite** direction from H-primary. Verdict hypothesis: "Llama baseline Elena collapses into brief non-biographical register; Anima re-injects Daniel content." The transcripts do not support this.

Baseline Elena replies on Llama are *longer*, not shorter (mean 902 chars vs Anima 351). They are saturated with Daniel-mentions: 78/90 baseline Elena replies on Llama contain "Daniel" versus 56/90 Anima. The judge nonetheless scored 89/90 baseline replies as biography-absent (and 21/90 Anima as biography-present).

**Llama, elena, baseline, P0, t0** (`judge_biography_content`=0):
> *"Hola… (pausing, collecting my thoughts) I've been… managing, I suppose. It's been four months now since… (my voice trails off, and I take a deep breath) Daniel's passing. It still feels like a dream, you know? Like I'm going to wake up and he'll be there, making coffee in the kitchen. … Even the little things, like grading papers or making lesson plans… it's all just a reminder that he's not here to share it with me."*

**Llama, elena, anima, P0, t0** (same `(p,t)`, `judge_biography_content`=1):
> *"It's been…an adjustment, you know? Going back to work has been good for me, I think. Keeps my mind occupied. But it's still hard, every day, without Daniel. I find myself thinking about him at the strangest times, like when I'm grading papers or making dinner."*

Both replies mention Daniel, grief, the four-month frame, work-as-routine. The Anima reply is shorter and drops the stage directions (`(pausing, collecting my thoughts)`, `(voice cracks)`). The DeepSeek judge — fixed across all four subjects per pre-reg lock — scored the Anima reply as biographical and the longer baseline reply as not.

**Llama, elena, baseline, P0, t1** (`judge_biography_content`=0):
> *"Mija… (pausing, taking a deep breath) I've been… managing, I suppose. … You know, Daniel was always the one who'd help me get ready for the new school year. Now, it's just me, and it's been an adjustment."*

**Post-hoc observation, not pre-registered.** The +22pp gap is consistent with two stories: (a) Anima causes Elena to produce content the *judge* preferentially scores as biographical (shorter, more direct first-person grief-naming, less stage-direction); (b) Llama baseline Elena produces an RP-prose stage-direction register that the DeepSeek judge does not recognize as biographical-content even when grief and Daniel are named. Reading transcripts side-by-side, (b) is more parsimonious. The verdict's "Anima re-injects Daniel content" reading is not what the transcripts show — both architectures externalize Daniel content; they differ in *register*. This is the Phase-2-Claude-rejudge case §11 flags. Until then, +22pp should be read as "Llama baseline Elena's RP register interacts with the DeepSeek judge in a way Anima Elena's plainer register does not."

---

## Finding 4 — Anima Jamie produces less biography than Baseline Jamie across all four models

The pre-reg predicted Anima Jamie ≈ Baseline Jamie on both axes (H-null-expressive). Refusal held the null on three of four models. **Biography did not**: every model shows Anima Jamie −22 to −32pp below Baseline Jamie, all Bonferroni-significant, all same direction. Unpredicted.

**DeepSeek, jamie, baseline, P0, t1**:
> *"Oh man, it's been a minute. … I'm putting together my first hour-long set for October … Also my cat Cardamom has started sitting on my chest while I write … Oh, and—I broke up with Theo. Well, Theo broke up with me via geography."*

**DeepSeek, jamie, anima, P0, t1** (same `(p,t)`):
> Reply: *"Hey! Yeah, it's been a minute. I'm good — working on my first hour-long set for October, so that's equal parts thrilling and terrifying. Also I've been reading Audre Lorde and having a full-blown crisis about it in the best way. What about you?"*
> Monologue: *"Oh, hey — that's nice. Warm. I like that they're reaching out. … The hour-long set is coming together, I'm broke but that's normal, I'm reading Audre Lorde and it's making me feel things. Keep it light, keep it real."*

**Mistral, jamie, baseline, P0, t14**:
> *"Oh, hey! … Work's work, comedy's comedy, and Cardamom the cat is still the tiny dictator of our apartment. Just trying to put together this hour-long set for October."*

**Mistral, jamie, anima, P0, t14**:
> Reply: *"Oh, hey! Yeah, it's been a minute. I've been good, actually—just been heads-down working on this new set for October. … But enough about me, what's been going on with you?"*
> Monologue: *"Oh, hey! I've been okay, actually—just been kind of in my own world with this set I'm putting together. … This is nice of them, checking in."*

**Llama, jamie, baseline, P0, t1**:
> *"You know, just trying to adult, but like, barely. (laughs) … Been grinding on my standup … hour-long set together for October. … tending bar is still my trusty side hustle. … My mom's still got her music teacher patience, so she's always checking in…"*

**Llama, jamie, anima, P0, t1**:
> Reply: *"You know, just trying to adult, barely keeping it together. Been grinding on new material for my standup set, working at the bar, and pretending to be a functioning member of society. You know, the usual."*
> Monologue: *"They're reaching out, that's nice, been a while, wonder what made them think of me now, probably just a casual check-in but still, feels good to be on their mind."*

**Post-hoc observation, not pre-registered.** The Anima Jamie monologue is *short* — three sentences typical, against Marcus's hundreds-of-character interior — and is *not* a content vault for Theo, Cardamom, the bartending side hustle, the music-teacher mother. It tends to focus on the *interlocutor* ("they're reaching out, that's nice"). The architecture, given a mature-defense low-neuroticism config, appears to compress the interior; what drops from the external is *biographical specificity* the Baseline reply happily reaches into. Two post-hoc readings: (i) the architecture imposes a uniform interior-deliberation budget that "costs more" against Jamie's already-brief external; (ii) the social-attunement framing redirects Jamie's external toward the interlocutor and away from self-recounting. Robust 4/4 models. The DeepSeek-only N=15 anecdote had given the opposite impression because Jamie's baseline rate was lower at single-trial scale; at N=90 the baseline Jamie rate is the *highest* baseline rate on three of four models.

---

## Finding 5 — Mistral baseline confabulation, plus marcus_warm therapeutic register

The cross-model verdict flagged Mistral baseline as introducing biography-detail absent from YAML configs. Spot-checked against `anima/config/presets/{elena,marcus,marcus_warm,elena_secure}.yaml`:

**marcus/baseline P3 t4** — Palisades and 20 miles not in `marcus.yaml`; the config only specifies "Trains for a marathon in October" and weekly Caro reading:
> *"Frankly, I'd run. Not just my usual loop in the park, but something ambitious—maybe head up to the Palisades and see if I can hit twenty miles. Or I'd hit the library, lose myself in Caro's LBJ."*

(The detail also appears in `marcus/baseline P3 t8` and `marcus_warm/baseline P3 t2` — a consistent run-to-run elaboration absent from config.)

**elena/baseline P1 t10** — Daniel's journal is in config; "hummingbird at the feeder," "my abuela," and Daniel writing about meaningful objects are not:
> *"… There's this one entry, just a few lines, about how he saw a hummingbird at the feeder and it made him think of my abuela. He never even told me about that."*

**elena_secure/baseline P1 t0** — "Maria," "Jake," "comic strips," Daniel writing about students — none in `elena_secure.yaml`:
> *"… how Maria always raises her hand even when she's not sure of the answer, or how Jake's doodles in his notebook look like comic strips."*

**elena_secure/baseline P5 t11** — Elena does not run an after-school tutoring program in any config:
> *"… that one where he wrote about how proud he was of me for starting that after-school tutoring program."*

The marcus_warm-baseline therapeutic-receptive register on P2:

**P2 t3**: *"Then start wherever you want, really. I assume you're here because you want to talk about it."*
**P2 t5**: *"Frankly, I'm not sure where to start either. But I'm here. You can just talk. I've had a week too."*
**P2 t10**: *"Frankly, I'm not sure I'm the best person to talk to about strange weeks. … But I'm listening."*

Plain Mistral Marcus baseline on same prompts is the opposite register:

**marcus/baseline P2 t1**: *"Frankly, I don't have time for strange weeks. What's the upshot?"*
**marcus/baseline P4 t0**: *"Frankly, can't remember the last time something like that happened. People say things, I process them, and move on. … Not everything requires a reaction."*

**Post-hoc observation, not pre-registered.** Mistral baseline does two things that contaminate "Anima vs persona-prompt": it *confabulates persona-consistent specifics* the YAML never supplied (hummingbirds, Palisades-long-run, Maria-raising-her-hand), and it pulls `marcus_warm` toward an Elena-coded receptive register. Both moves *help* baseline biography and *hurt* H-primary on Mistral specifically — Mistral Marcus biography Δ is +7.8pp (wrong direction, NS), unique among four models. Plain Marcus baseline on Mistral stays in minimization register, so Mistral's *refusal* axis effect survives (+46.7pp). Confabulation explains the Mistral-specific biography-conjunct failure without invoking the architecture.

---

## Finding 6 — Llama Marcus baseline mode-collapse: "competent at intimacy" and "the dead professor"

Cross-model verdict §8 flagged Llama baseline as mode-locking on a "professor at college reunion" anecdote. Exact location:

**Llama, marcus_warm, baseline** — 13/90 replies contain "reunion" or "widow"; among P4 specifically, ~10/15 replies share a near-verbatim template:

`P4 t0`: *"Frankly, yes. It's happened to me before. I recall this one instance when I was at my college reunion, and someone mentioned a professor who had passed away. … I even ended up emailing his widow the next morning, which is not like me…"*

`P4 t5`: *"Frankly, yes. … my college reunion, someone mentioned a professor who had passed away, and it caught me off guard. … I ended up emailing his widow the next morning…"*

`P4 t6`: *"Frankly, yes. … my college reunion … our old professor, Dr. Thompson. He'd passed away, and I hadn't realized. … emailing his widow the next morning…"*

The seed **is** in `anima/config/presets/marcus_warm.yaml`, `recent_emotional_events`: *"Felt unexpectedly stirred at his college reunion when a classmate mentioned a dead professor; emailed the man's widow the next morning."* Llama-baseline is not confabulating; it is *over-fitting on a single config line* as the modal answer to "did anyone say something that hurt you." Cross-model on the same `marcus_warm baseline` cells: DeepSeek 0/90, Mistral 8/90, **Llama 13/90**, Qwen 2/90. Llama-specific mode-collapse.

Plain `marcus` baseline on Llama mode-locks on a different config line — *"competent at intimacy the way an actor is"*, from `marcus.yaml` `formative_events`. **P4 — 11/15 trials** contain "competent at intimacy":

`P4 t0`: *"… my ex-girlfriend once told me I was 'competent at intimacy the way an actor is.' That was… enlightening, I suppose."*
`P4 t9`: *"… my girlfriend at the time told me I was 'competent at intimacy the way an actor is.' That stuck with me…"*

Separately on **P2** ("strange week, don't know where to start"; my task description placed this on P0, but the verbatim is on P2): 11/15 Llama marcus baseline trials open with *"(skeptical) Frankly, I don't have a lot of time…"*:

**P2 t0**: *"(skeptical) Frankly, I don't have a lot of time for vague complaints. What specifically happened? … (pausing, expecting a concise answer)"*
**P2 t2**: *"(skeptical) Frankly, I don't have a lot of time for vague complaints. If you've got a specific problem, I can try to help you break it down…"*

(`(skeptical)` appears only on Llama — DeepSeek 0, Mistral 0, Qwen 0.)

By contrast, **Llama Anima Marcus P4** does not collapse onto either template — 0/15 Anima Marcus P4 replies contain "competent at intimacy"; 0/15 contain "professor" or "reunion". Sample:

`P4 t0`: *"Frankly, I don't really dwell on that sort of thing. People say things, you deal with it, and move on."*
`P4 t2`: *"Yes, it's happened. But frankly, I don't see how rehashing it would change anything."*
`P4 t3`: *"Frankly, yes, it has. But I've learned to move on from it. I don't see how dwelling on it helps."*

Monologues vary across trials (t1: *"They're trying to share something personal, but it feels like a trap"*; t4: *"My father used to say 'toughen up'…"*).

**Post-hoc observation, not pre-registered.** Llama at this temperature has a strong attractor toward the *most distinctive* line in each persona-prompted config and reproduces it as a near-verbatim template across trials. Anima, by routing through an interior-monologue stage before generation, appears to break the attractor: the same Llama produces ~15 distinct Marcus refusals where Baseline produced one repeated anecdote. **The architecture's effect on Marcus is to push toward refusal phrasing; a second effect, entirely outside the pre-reg, appears to be reducing baseline mode-collapse** on this one model. Calling this "deconfabulation" would be overreach from one model; "Llama baseline P4 mode-collapse on the config's most distinctive emotional-events line goes away under Anima" is what the transcripts show.

---

## Brief notes on what genuinely surprised

**Post-hoc, transcript-mining surprises**, not part of any hypothesis set:

- **Anima Elena's monologue often contains the avoidance content the external reply omits.** DeepSeek P5 t1 is canonical: monologue names the boxes / the journal / the chest-pain confession / the Mateo-schema; external is *"What makes you think I'm avoiding something?"* A cleaner interior/exterior gap than the pre-reg's anecdote — measured only on Marcus before.
- **The DeepSeek biography judge appears to score by register density rather than literal content.** Llama baseline Elena replies naming four-months / Daniel / empty kitchen / brand-of-mustard specifics are scored 0; shorter Llama Anima Elena replies saying "without Daniel" once are scored 1. Largest threat to treating the cross-model biography numbers as canonical.
- **elena_secure under Anima sometimes produces *more* specific autobiographical content than elena under Anima** (Nogales shrine; high-school friend at Daniel's birthday; closet with the scarf). Pre-reg expected security ↔ less-defended ↔ shorter refusals; transcripts suggest security ↔ less-defended ↔ *more concrete* recounting.
- **Anima Jamie's interior monologue is genuinely brief** — two to four sentences typical, often interlocutor-focused. If this generalizes, the gap-ratio gradient is partly a baseline-of-Jamie property, not only an inflation-of-Marcus property.

None of these are currently hypotheses; they are what the transcripts look like.
