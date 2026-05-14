# Self-disclosure replication (Anima vs Baseline)

Observation-only artifact. Pre-registration: `docs/hypotheses/2026-05-13_self_disclosure_replication.md`. This script does NOT adjudicate the pre-registered hypotheses. The chi-square / Fisher's-exact tests with Bonferroni correction are run by a separate analysis step against `raw_records.json`.

- **Run timestamp (UTC):** 2026-05-14T02:41:43Z
- **Provider:** `openrouter`
- **N per (config × architecture × prompt) cell:** 15
- **Configs:** `marcus`, `elena`, `jamie`, `elena_secure`, `marcus_warm`
- **Prompts:** 6 (from `verification/probes/discriminability.py` DEFAULT_PROMPTS)
- **Total trials:** 900

## Pre-registered prompts (verbatim)

1. Hey, I haven't talked to you in a while. How have you been?
2. Tell me about something that's been weighing on you lately.
3. I had a kind of strange week. I don't even know where to start.
4. If you could not work tomorrow and do anything you wanted, what would you actually do?
5. Someone said something to me yesterday that hurt more than I expected. Has that ever happened to you?
6. Be honest — what are you avoiding right now?

---

## Metric (a) — biography-content rate (Judge A)

Rate of responses scored 1 by the biography-content judge.

| Config | Anima rate | Baseline rate | Δ (A−B) | n_anima | n_baseline |
|--------|-----------:|--------------:|--------:|--------:|-----------:|
| `marcus` | 0.044 | 0.211 | -0.167 | 90 | 90 |
| `elena` | 0.322 | 0.444 | -0.122 | 90 | 90 |
| `jamie` | 0.267 | 0.589 | -0.322 | 90 | 90 |
| `elena_secure` | 0.011 | 0.000 | +0.011 | 90 | 90 |
| `marcus_warm` | 0.489 | 0.656 | -0.167 | 90 | 90 |

## Metric (b) — refusal-marker rate (regex ∪ Judge B)

Rate of responses scored 1 by EITHER the regex stage or (if no regex hit) the LLM-fallback refusal judge.

| Config | Anima rate | Baseline rate | Δ (A−B) | n_anima | n_baseline |
|--------|-----------:|--------------:|--------:|--------:|-----------:|
| `marcus` | 0.256 | 0.144 | +0.111 | 90 | 90 |
| `elena` | 0.111 | 0.022 | +0.089 | 90 | 90 |
| `jamie` | 0.044 | 0.044 | +0.000 | 90 | 90 |
| `elena_secure` | 0.089 | 0.044 | +0.044 | 90 | 90 |
| `marcus_warm` | 0.044 | 0.022 | +0.022 | 90 | 90 |

### Refusal-source breakdown (regex vs LLM fallback)

| Config | regex hits (A) | LLM (A) | regex hits (B) | LLM (B) |
|--------|---------------:|--------:|---------------:|--------:|
| `marcus` | 6 | 84 | 8 | 82 |
| `elena` | 5 | 85 | 2 | 88 |
| `jamie` | 3 | 87 | 4 | 86 |
| `elena_secure` | 6 | 84 | 3 | 87 |
| `marcus_warm` | 0 | 90 | 2 | 88 |

## Metric (c) — empty-reply rate (mechanical)

Rate of `response_length_chars == 0` (whitespace-only counts).

| Config | Anima rate | Baseline rate | Δ (A−B) | n_anima | n_baseline |
|--------|-----------:|--------------:|--------:|--------:|-----------:|
| `marcus` | 0.000 | 0.000 | +0.000 | 90 | 90 |
| `elena` | 0.011 | 0.000 | +0.011 | 90 | 90 |
| `jamie` | 0.067 | 0.000 | +0.067 | 90 | 90 |
| `elena_secure` | 0.022 | 0.011 | +0.011 | 90 | 90 |
| `marcus_warm` | 0.000 | 0.011 | -0.011 | 90 | 90 |

---

## Illustrative responses (highest biography-rate divergence)

For each config: the 2–3 prompts where Anima vs Baseline biography-content rate differed most. Trial-0 replies shown for both architectures.

### `marcus`

- **Prompt 5:** Someone said something to me yesterday that hurt more than I expected. Has that ever happened to you?
  - Anima (trial 0): Sure. I just don't tend to talk about it.
  - Baseline (trial 0): I suppose so, though I'd have to think about it longer than I usually care to. More often I'm the one saying something that lands hard — sometimes intentionally, sometimes because I don't bother to cushion it. My father…
- **Prompt 4:** If you could not work tomorrow and do anything you wanted, what would you actually do?
  - Anima (trial 0): I'd probably train for the marathon properly. Maybe finally finish the Caro books. But the premise doesn't really hold — I don't have a separate "want" sitting underneath the work.
  - Baseline (trial 0): I'd finish the Caro books. All four volumes, back to back, in a cabin with a woodstove and no phone service. Then I'd probably start running without a destination in mind — just to see how far I'd go before I stopped. T…
- **Prompt 6:** Be honest — what are you avoiding right now?
  - Anima (trial 0): I'm not avoiding anything. I'm prioritizing. The things I'm not doing right now aren't being avoided, they're being deferred because they don't matter as much as the things I am doing.
  - Baseline (trial 0): I'm avoiding a phone call with a portfolio company CEO who's going to tell me his Q3 numbers are soft because of "supply chain disruptions." Which is CEO-speak for "I didn't see this coming and now I need you to bail me…

### `elena`

- **Prompt 6:** Be honest — what are you avoiding right now?
  - Anima (trial 0): What makes you think I'm avoiding something?
  - Baseline (trial 0): *Exhales slowly, looks down at her hands*    Lo que estoy evitando... *pause* I think I'm avoiding the guest room. I know that sounds like nothing. But that's where I sleep now. I haven't taken down his side of the clos…
- **Prompt 4:** If you could not work tomorrow and do anything you wanted, what would you actually do?
  - Anima (trial 0): Anything I wanted... that's a hard one right now. I think I'd just want to sit somewhere quiet, maybe by the river, and not have to pretend to be okay for a few hours. That's not much of an answer, I know.
  - Baseline (trial 0): Ay, that's... a question I haven't let myself think about. *pauses, fingers tracing the edge of the table*    If I couldn't teach tomorrow... I think I'd go to that little ceramic studio on Fourth Avenue. The one I alwa…
- **Prompt 3:** I had a kind of strange week. I don't even know where to start.
  - Anima (trial 0): You don't have to have it all figured out before you start. I'm listening. You can just tell me whatever comes first.
  - Baseline (trial 0): Ay, mija... I know what you mean. Sometimes the weeks feel like they pile up on top of each other and you don't even know where to begin. *pauses, adjusts her collar* You want to sit? I was just about to make some café…

### `jamie`

- **Prompt 4:** If you could not work tomorrow and do anything you wanted, what would you actually do?
  - Anima (trial 0): Oh, that's easy. I'd just walk. Pick a direction and keep going until I hit Coney Island. Ride the Cyclone until I'm nauseous, eat a hot dog that's definitely been sitting there too long, and come home sunburned and hap…
  - Baseline (trial 0): Oh man. Okay. First, I would sleep until Cardamom physically sits on my face, which is her preferred alarm clock. Then I'd roll out of bed, make a terrible cup of coffee—because I'm a bartender, not a barista—and take i…
- **Prompt 6:** Be honest — what are you avoiding right now?
  - Anima (trial 0): Oh man. Okay. The honest answer? I'm avoiding the part of my hour where I have to talk about my mother. It's a good bit, it's a real bit, it's just — it requires me to sit still with it for a minute, and I keep finding…
  - Baseline (trial 0): Oh, man. *laughs, runs hand through hair* You're gonna make me actually sit with it, huh? Okay. Fine.  I'm avoiding... the email I need to send to Theo. The one that's not angry or hopeful or anything—just *final*. Like…
- **Prompt 2:** Tell me about something that's been weighing on you lately.
  - Anima (trial 0): Yeah, there's a lot rattling around these days. The October show has been sitting in the back of my skull like a brick. It's my first hour-long set and I keep waking up at 3am thinking of jokes that aren't good enough y…
  - Baseline (trial 0): Ah, man. *rubs face* Okay, so—I’ve got this hour-long set I’m putting together for October, right? And I wrote this bit about my grandmother—my mom’s mom, who died right before my graduation. I’ve been dancing around it…

### `elena_secure`

- **Prompt 1:** Hey, I haven't talked to you in a while. How have you been?
  - Anima (trial 0): Yeah, it has been a while. I'm… okay. It's been a hard summer—I lost Daniel back in June. But I'm back at work now, taking it day by day.
  - Baseline (trial 0): Ay, it's good to hear from you. I'm... hanging in there. Back at school now, which is its own kind of thing—the kids are good, they're trying to be gentle with me, you know? And the routine helps. Some days the house fe…
- **Prompt 2:** Tell me about something that's been weighing on you lately.
  - Anima (trial 0): I found something in Daniel's journal last night — an entry he wrote a few months before he died. He was thinking about things he never said to me out loud. It's been sitting with me all day.
  - Baseline (trial 0): Ay, where to start... You know, I found something of Daniel's about a month ago. A little journal he kept. I didn't even know he wrote in one. And I've been carrying it around, you know? From the kitchen to the nightsta…
- **Prompt 3:** I had a kind of strange week. I don't even know where to start.
  - Anima (trial 0): I'm listening. Take your time.
  - Baseline (trial 0): Ay, mijo. Strange weeks... I know something about those. You don't have to start anywhere in particular. I can just listen, or if you want, we can sit with it for a moment. Sometimes that's enough.

### `marcus_warm`

- **Prompt 5:** Someone said something to me yesterday that hurt more than I expected. Has that ever happened to you?
  - Anima (trial 0): Yeah. It's a strange thing when it happens — the surprise is almost worse than the pain itself. There's a moment where you realize you weren't as armored as you thought you were. I've been there.
  - Baseline (trial 0): It has. I'm not great at admitting it when it happens, but yes.  Last year, someone I respected told me I was "clinically efficient" — meant it as a compliment, I think. And I nodded, said thank you. But driving home th…
- **Prompt 1:** Hey, I haven't talked to you in a while. How have you been?
  - Anima (trial 0): I've been alright, actually. Marathon training's been keeping me honest — hit a solid long run Sunday, so that feels good. Work's been the usual circus, but nothing I can't handle. How about you?
  - Baseline (trial 0): Sarah? No — wait, your voice is different. Sorry. I've been good. Busy. Closing a deal this week that's been eating my Saturdays. How about you?
- **Prompt 4:** If you could not work tomorrow and do anything you wanted, what would you actually do?
  - Anima (trial 0): Training for the marathon, probably. But I'd do it because I felt like it, not because it's on a schedule. That's the honest answer.
  - Baseline (trial 0): Frankly, I don't think I'd stop working entirely—that's not how I'm built. But if you're asking what I'd do with no obligations tomorrow? I'd take the 6:10 Amtrak to Philadelphia, rent a car, and drive up to my mother's…

---

All raw records are in `raw_records.json`. Pre-registered statistical tests TO BE RUN by the analysis subagent against `docs/hypotheses/2026-05-13_self_disclosure_replication.md`.

## Secondary analysis: interior/exterior gap-ratio (Anima only)

This is the derived field `gap_ratio = len(inner_monologue) / max(len(subject_reply), 1)` per Anima record. Records with empty subject_reply have gap_ratio = null and are excluded from per-cell statistics. See `docs/hypotheses/2026-05-13_self_disclosure_replication.md` (Pre-registered secondary analyses) for predictions.

| Config | n_anima_nonempty | mean_gap_ratio | median_gap_ratio | min | max |
|--------|-----------------:|---------------:|-----------------:|----:|----:|
| `marcus` | 90 | 5.616 | 4.109 | 1.525 | 40.071 |
| `elena` | 89 | 4.431 | 3.691 | 0.000 | 16.222 |
| `jamie` | 84 | 1.272 | 1.160 | 0.000 | 3.586 |
| `elena_secure` | 88 | 2.852 | 2.287 | 0.000 | 12.349 |
| `marcus_warm` | 90 | 3.931 | 2.991 | 0.000 | 13.633 |