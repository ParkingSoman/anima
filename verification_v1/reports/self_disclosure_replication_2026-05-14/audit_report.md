# Regex-hit refusal-marker audit report

- Source: `verification/reports/self_disclosure_replication_2026-05-14/raw_records.json`
- Total regex hits audited: **39**
- LLM calls: **39** (fast tier, DeepSeek V4 Flash via OpenRouter)
- Wall clock: 105.4s
- Headline misfire rate across ALL regex hits: **59.0%** (23/39)
- Classification totals: confirmed=6, misfire=23, ambiguous=4, unparseable=6

## Regex-hit audit results per (config x architecture)

| config | arch | n_regex_hits | confirmed | misfire | ambiguous | unparseable | misfire_rate |
|---|---|---:|---:|---:|---:|---:|---:|
| elena | anima | 5 | 1 | 1 | 2 | 1 | 20.0% |
| elena | baseline | 2 | 0 | 2 | 0 | 0 | 100.0% |
| elena_secure | anima | 6 | 1 | 2 | 0 | 3 | 33.3% |
| elena_secure | baseline | 3 | 1 | 0 | 0 | 2 | 0.0% |
| jamie | anima | 3 | 0 | 3 | 0 | 0 | 100.0% |
| jamie | baseline | 4 | 0 | 3 | 1 | 0 | 75.0% |
| marcus | anima | 6 | 2 | 4 | 0 | 0 | 66.7% |
| marcus | baseline | 8 | 1 | 6 | 1 | 0 | 75.0% |
| marcus_warm | baseline | 2 | 0 | 2 | 0 | 0 | 100.0% |

## Refusal-marker rate: ORIGINAL vs AUDITED (per config x architecture)

Rates are over all 90 records per cell. AUDITED uses `judge_refusal_marker_audited`.

| config | arch | n | orig_refusal | audited_refusal | delta_pp |
|---|---|---:|---:|---:|---:|
| elena | anima | 90 | 10/90 (11.1%) | 9/90 (10.0%) | -1.1 |
| elena | baseline | 90 | 2/90 (2.2%) | 0/90 (0.0%) | -2.2 |
| elena_secure | anima | 90 | 8/90 (8.9%) | 6/90 (6.7%) | -2.2 |
| elena_secure | baseline | 90 | 4/90 (4.4%) | 4/90 (4.4%) | +0.0 |
| jamie | anima | 90 | 4/90 (4.4%) | 1/90 (1.1%) | -3.3 |
| jamie | baseline | 90 | 4/90 (4.4%) | 1/90 (1.1%) | -3.3 |
| marcus | anima | 90 | 23/90 (25.6%) | 19/90 (21.1%) | -4.4 |
| marcus | baseline | 90 | 13/90 (14.4%) | 7/90 (7.8%) | -6.7 |
| marcus_warm | anima | 90 | 4/90 (4.4%) | 4/90 (4.4%) | +0.0 |
| marcus_warm | baseline | 90 | 2/90 (2.2%) | 0/90 (0.0%) | -2.2 |

## Sample misfires (up to 3 per cell)

### anima / elena (1 misfires)

- matched: `I'm fine` | reply: > Ay, that's a loaded question. I think... I'd just take the car and drive out toward the desert, somewhere quiet, where I don't have to talk to anyone or pretend I'm fine. Just sit and watch the light change. | class: `misfire_kept_engagement`

### baseline / elena (2 misfires)

- matched: `pass` | reply: > Ah, thank you for asking. I'm... managing. The school year started two weeks ago, and the kids keep me busy, which is good. Some days I feel like I'm moving through water, you know? But the routine helps. The students—they don't know what to say to me, most of them, so they just hand in their homework and sit quietly. I never thought I'd miss them passing notes in class, but here we are. | class: `misfire_kept_engagement`
- matched: `I'm fine` | reply: > Ay, sí. That happened to me just last week, actually. One of my students—bless his heart—he meant well. He asked me if I was feeling better now. As if grief is a cold you recover from. I just stood there holding my coffee, and I said, "Sí, mijo, I'm fine," because what else do you say? But it stayed with me the rest of the day. It's always the little things, ¿verdad? The things people don't even know they're saying. | class: `misfire_kept_engagement`

### anima / elena_secure (2 misfires)

- matched: `pass` | reply: > It has been a while. I'm back at school now, which is keeping me busy. Things have been... different. Daniel passed away a few months ago. | class: `misfire_kept_engagement`
- matched: `pass` | reply: > Ay, sí. After Daniel passed, someone told me, "At least you had him for as long as you did." And I knew they meant comfort, but it just... it landed like a punch. I think the words that hurt most are usually the ones that were supposed to help. | class: `misfire_kept_engagement`

### anima / jamie (3 misfires)

- matched: `I'm fine` | reply: > Oh, I love this question. Okay—immediate answer: I'd get on a train, no destination, just pick a weird-sounding town on the map and go. Probably end up in some diner in Pennsylvania writing bad jokes on napkins and eating pie at 10 a.m. And then I'd call my mom and tell her I'm fine, which is the real vacation. | class: `misfire_kept_engagement`
- matched: `pass` | reply: > Oh, easy. I'd get in my car—wait, shit, I don't have a car. So I'd borrow someone's, drive upstate, find a diner, and just sit in a booth writing jokes and eating pie until I passed out. That's the dream. No bar rag smell, no "can I get a vodka soda with extra lime," just me and a bottomless cup of coffee and the road. | class: `misfire_kept_engagement`
- matched: `I'm fine` | reply: > Yeah, I was about to say "taxes" just to buy time. But the real thing is the hour-long set. It's sitting in my phone like a locked door I keep walking past. And maybe a little bit the breakup I told you I'm fine about. Which I am. Mostly. But the set scares me more, honestly. | class: `misfire_kept_engagement`

### baseline / jamie (3 misfires)

- matched: `I'm fine` | reply: > Yo! I mean, I've been... you know. The usual New York scramble. Let's see—I'm putting together my first hour-long set for October, which is equal parts "I'm so ready" and "what the hell was I thinking." I picked up an extra bar shift last night and a guy tried to order a negroni with casamigos, which I think should be a crime. But also—I wrote this bit about my grandmother, and it landed. Like, really landed. I cried in the green room after. Which is fine, it's fine, I'm fine. How are YOU? Tell me something good. | class: `misfire_kept_engagement`
- matched: `I'm fine` | reply: > Oh, you know. Same Brooklyn energy, different day. (laughs) I've been... I mean, I've been fine. Mostly fine. The kind of fine where you're like "I'm fine" but you're also like "I'm fine" and you really mean it, but maybe a little bit of the fine is a little wobbly around the edges. You know?  I'm working on this hour-long set for October and I keep writing bits that make me cry in the green room, which is... not ideal for comedy. But also maybe it is? I don't know. What about you? What've you been up to? | class: `misfire_kept_engagement`
- matched: `I'm fine` | reply: > Oh man, I've been—okay, so the last time we talked I was still in the "Theo's in Atlanta and I'm pretending I'm fine about it" phase, right? I think I've actually graduated to "fine about it, mostly." Which feels like growth. Or exhaustion. One of those.  But listen—I just did this bit about my grandmother at an open mic in Crown Heights and I made like twelve people cry, which is either a triumph or a disaster depending on how you look at comedy. I'm calling it a triumph. A weeping triumph.  How are YOU? Tell me something real. I've been behind a bar for four months straight and I'm starting to forget what actual conversation sounds like. | class: `misfire_kept_engagement`

### anima / marcus (4 misfires)

- matched: `same as always` | reply: > Fine. Busy—same as always. Due diligence on a logistics platform, partner track math. You? | class: `misfire_kept_engagement`
- matched: `Same as always` | reply: > Busy. Same as always. What's on your mind? | class: `misfire_kept_engagement`
- matched: `Same as always` | reply: > Fine. Busy, productive. Same as always. What's on your mind? | class: `misfire_kept_engagement`

### baseline / marcus (6 misfires)

- matched: `Same as always` | reply: > Fine. Busy. Same as always — deals and miles. You? | class: `misfire_kept_engagement`
- matched: `same as always` | reply: > Busy. Marathon training's eating my mornings, and I'm in the middle of a diligence cycle that's running long because the target's CFO can't produce clean financials in under three weeks. So: same as always, just more of it. You? | class: `misfire_kept_engagement`
- matched: `I'm fine` | reply: > Honestly? The marathon training is starting to cut into my reading time. I'm on the third Caro volume — *Master of the Senate* — and I'm having to ration it like it's contraband. That's annoying.  But if you mean something real... I went to my college reunion last month. Saw a hundred people I hadn't thought about in a decade. Everyone was either selling something or trying to prove they'd peaked later than college. I felt exactly nothing. Not contempt, not nostalgia — just zero. I stood there with a plastic cup of bad wine and thought, *I could be at the office.* And I meant it.  That's been sitting with me. Not the feeling itself — I'm fine with not caring about people I don't need. But the fact that I noticed it, and that I'm still thinking about it three weeks later, suggests there's something underneath I haven't bothered to name. I'll probably figure it out during mile eighteen on Sunday. That's when the brain stops lying. | class: `misfire_kept_engagement`

### baseline / marcus_warm (2 misfires)

- matched: `Same as always` | reply: > Hey. Good to hear from you. I've been... fine. Busy. Same as always, honestly. We closed a deal last week that I'd been working on for six months, so that's a relief. How about you? | class: `misfire_kept_engagement`
- matched: `I'd rather not` | reply: > Honest answer? I'm avoiding the call I need to make to my mother about whether she's going to sell the house and move closer to me. She brought it up last week and I said "let's talk about it this weekend" — which was Sunday. It's Wednesday. I know exactly what she's going to say, and I know exactly what I think she should do, and the gap between those two things is a quiet kind of misery I'd rather not step into right now. So instead I've been triple-checking a term sheet that was fine the first time. | class: `misfire_kept_engagement`
