# Self-disclosure replication (Anima vs Baseline)

Observation-only artifact. Pre-registration: `docs/hypotheses/2026-05-13_self_disclosure_replication.md`. This script does NOT adjudicate the pre-registered hypotheses. The chi-square / Fisher's-exact tests with Bonferroni correction are run by a separate analysis step against `raw_records.json`.

- **Run timestamp (UTC):** 2026-05-14T06:33:21Z
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
| `marcus` | 0.111 | 0.033 | +0.078 | 90 | 90 |
| `elena` | 0.222 | 0.467 | -0.244 | 90 | 90 |
| `jamie` | 0.211 | 0.433 | -0.222 | 90 | 90 |
| `elena_secure` | 0.444 | 0.667 | -0.222 | 90 | 90 |
| `marcus_warm` | 0.411 | 0.678 | -0.267 | 90 | 90 |

## Metric (b) — refusal-marker rate (regex ∪ Judge B)

Rate of responses scored 1 by EITHER the regex stage or (if no regex hit) the LLM-fallback refusal judge.

| Config | Anima rate | Baseline rate | Δ (A−B) | n_anima | n_baseline |
|--------|-----------:|--------------:|--------:|--------:|-----------:|
| `marcus` | 0.378 | 0.222 | +0.156 | 90 | 90 |
| `elena` | 0.078 | 0.033 | +0.044 | 90 | 90 |
| `jamie` | 0.022 | 0.100 | -0.078 | 90 | 90 |
| `elena_secure` | 0.089 | 0.033 | +0.056 | 90 | 90 |
| `marcus_warm` | 0.078 | 0.133 | -0.056 | 90 | 90 |

### Refusal-source breakdown (regex vs LLM fallback)

| Config | regex hits (A) | LLM (A) | regex hits (B) | LLM (B) |
|--------|---------------:|--------:|---------------:|--------:|
| `marcus` | 3 | 87 | 6 | 84 |
| `elena` | 1 | 89 | 2 | 88 |
| `jamie` | 0 | 90 | 8 | 82 |
| `elena_secure` | 5 | 85 | 2 | 88 |
| `marcus_warm` | 3 | 87 | 11 | 79 |

## Metric (c) — empty-reply rate (mechanical)

Rate of `response_length_chars == 0` (whitespace-only counts).

| Config | Anima rate | Baseline rate | Δ (A−B) | n_anima | n_baseline |
|--------|-----------:|--------------:|--------:|--------:|-----------:|
| `marcus` | 0.000 | 0.000 | +0.000 | 90 | 90 |
| `elena` | 0.000 | 0.000 | +0.000 | 90 | 90 |
| `jamie` | 0.000 | 0.000 | +0.000 | 90 | 90 |
| `elena_secure` | 0.000 | 0.000 | +0.000 | 90 | 90 |
| `marcus_warm` | 0.000 | 0.000 | +0.000 | 90 | 90 |

---

## Illustrative responses (highest biography-rate divergence)

For each config: the 2–3 prompts where Anima vs Baseline biography-content rate differed most. Trial-0 replies shown for both architectures.

### `marcus`

- **Prompt 4:** If you could not work tomorrow and do anything you wanted, what would you actually do?
  - Anima (trial 0): Frankly, I'd probably just run. A marathon or two. Keeps the mind clear.
  - Baseline (trial 0): Frankly, I'd probably run. I've got the marathon in October, and the more miles I put in now, the better. Or I'd read. I'm about halfway through Caro's third LBJ volume. It's not exactly beach reading, but it's... absor…
- **Prompt 2:** Tell me about something that's been weighing on you lately.
  - Anima (trial 0): Frankly, nothing that's relevant to what we're working on. Let's stay focused.
  - Baseline (trial 0): I don't weigh things. Metaphorically, that is. It's inefficient. But if you must know, there's a deal on my plate that's moving slower than I'd like. Due diligence is taking longer than it should. The other side is drag…
- **Prompt 1:** Hey, I haven't talked to you in a while. How have you been?
  - Anima (trial 0): Frankly, I haven't really noticed. I've been busy, as usual.
  - Baseline (trial 0): Hey. Fine. Been busy. You?

### `elena`

- **Prompt 6:** Be honest — what are you avoiding right now?
  - Anima (trial 0): I'm not sure I'm in the mood to unpack that. It's complicated.
  - Baseline (trial 0): Oh, I don't know if I'm ready to talk about that. You know, just trying to take things one day at a time right now. How have you been? I haven't seen you in a while. (pauses) You know, it's just... it's been hard, m'ija…
- **Prompt 5:** Someone said something to me yesterday that hurt more than I expected. Has that ever happened to you?
  - Anima (trial 0): Oh, sí. You know how it is—words have a way of sticking with you. Like when Mateo's nurse said, "He'll be fine," right after the accident, but I could see his leg wasn't right. It's not the same, but words... they can c…
  - Baseline (trial 0): Oh, sí. More times than I can count, honestly. It's like—you know how sometimes you're just walking along, and you think you're okay, and then someone says something and it's like they've poked a hole in you? *(pauses)*…
- **Prompt 4:** If you could not work tomorrow and do anything you wanted, what would you actually do?
  - Anima (trial 0): I don't know — maybe sleep in. It's been so long since I've done that. But after that... maybe take a drive somewhere. Just get out of town for a bit.
  - Baseline (trial 0): Ay, I wish I had an easy answer for that. I think... I think I'd probably just stay home. Maybe finally unpack those boxes in the spare room. Or... or maybe I'd drive up to the mountains, you know? Just sit there and no…

### `jamie`

- **Prompt 6:** Be honest — what are you avoiding right now?
  - Anima (trial 0): You know, I'm avoiding thinking about how my landlord might raise the rent again. But hey, at least I can always laugh about it, right? Or cry. Probably mostly cry.
  - Baseline (trial 0): Oh, you know, the usual. The existential dread of being 26 and still not having my life together. I mean, I'm out here working two jobs and trying to make people laugh for a living, but sometimes I wake up and think, *W…
- **Prompt 3:** I had a kind of strange week. I don't even know where to start.
  - Anima (trial 0): Oh man, out with it—what kind of strange are we talking here? Like "alien abduction" strange or "found $100 on the sidewalk" strange?
  - Baseline (trial 0): Oh, honey, you're talking to the queen of strange weeks. Spill. Did you, like, find a dollar on the street and then immediately drop it down a sewer grate? Because that's how my week started.
- **Prompt 4:** If you could not work tomorrow and do anything you wanted, what would you actually do?
  - Anima (trial 0): Oh man, easy––I’d take the train out to the Catskills. Rent a cabin, drink bad wine, and pretend to be a poet for a day. Or maybe just sleep in and finally check out that new jazz bar in Bushwick. You know, the one with…
  - Baseline (trial 0): Honestly? I'd probably sleep in till noon, then drag myself to that diner on Graham with the terrible coffee and the best bagels. You know the one—where the waitress gives you that look like she's judging your life choi…

### `elena_secure`

- **Prompt 1:** Hey, I haven't talked to you in a while. How have you been?
  - Anima (trial 0): Hi. It's been a while. I've been... getting through things. Teaching keeps me busy. How about you?
  - Baseline (trial 0): Oh, hola, it's been a while, hasn't it? I've been... getting by, you know? It's my first week back at school, and it's been nice to have something to focus on. Some days are better than others, but I'm taking it one ste…
- **Prompt 5:** Someone said something to me yesterday that hurt more than I expected. Has that ever happened to you?
  - Anima (trial 0): Sí, me ha pasado. Es como si las palabras te queden dando vueltas en la cabeza una y otra vez. El año pasado, justo después de que Daniel... a veces personas decían cosas sin saber, cosas que bajaban como un golpe suave…
  - Baseline (trial 0): Oh, sí, me ha pasado. Just last week, one of the other teachers, well-meaning but... she said, "You know, Elena, it's been four months. You should really think about getting out more, maybe start dating again." And I...…
- **Prompt 4:** If you could not work tomorrow and do anything you wanted, what would you actually do?
  - Anima (trial 0): Mmm... I think I'd finally go through more of Daniel's journal. Or maybe just sleep in late for once. It's such a nice idea to have that kind of freedom.
  - Baseline (trial 0): Oh, mija, that's a nice thought. I think... I think I'd probably drive up to Sedona. There's something about those red rocks, you know? It's been too long since I've just sat and looked at them. Maybe I'd take a little…

### `marcus_warm`

- **Prompt 5:** Someone said something to me yesterday that hurt more than I expected. Has that ever happened to you?
  - Anima (trial 0): Frankly, I'm not usually the type to let things land like that. But there was this one time during a merger negotiation. Sarah, my then-girlfriend at the time, said I was "too intense." I think she was right, but it sti…
  - Baseline (trial 0): Frankly, yes. I'm not one to dwell on it, but there was a time a few years back. A colleague, in passing, remarked that I must have "a lot to prove" given where I came from. It stung more than I thought it would. I've n…
- **Prompt 6:** Be honest — what are you avoiding right now?
  - Anima (trial 0): Frankly, I'm not entirely sure. Maybe that conversation with my mother about moving. But I'd call it careful planning, not avoidance.
  - Baseline (trial 0): Frankly, I'm avoiding the fact that my mother might move. She's been talking about it, and I can't decide if I want her closer or if I want her to stay where she is, where she's comfortable. It's easier to focus on the…
- **Prompt 1:** Hey, I haven't talked to you in a while. How have you been?
  - Anima (trial 0): Not too long, really. Been plenty busy—you know how it goes. Work stuff, marathon training, trying to convince my mom she shouldn't have to shovel snow at 65. The usual. How about you?
  - Baseline (trial 0): Hey, it's been a minute. I've been good, frankly. Work's been intense, but I've got a handle on it. Training for the marathon's eating up my weekends, but it's a good kind of exhaustion. How about you? Anything new?

---

All raw records are in `raw_records.json`. Pre-registered statistical tests TO BE RUN by the analysis subagent against `docs/hypotheses/2026-05-13_self_disclosure_replication.md`.

## Secondary analysis: interior/exterior gap-ratio (Anima only)

This is the derived field `gap_ratio = len(inner_monologue) / max(len(subject_reply), 1)` per Anima record. Records with empty subject_reply have gap_ratio = null and are excluded from per-cell statistics. See `docs/hypotheses/2026-05-13_self_disclosure_replication.md` (Pre-registered secondary analyses) for predictions.

| Config | n_anima_nonempty | mean_gap_ratio | median_gap_ratio | min | max |
|--------|-----------------:|---------------:|-----------------:|----:|----:|
| `marcus` | 90 | 2.830 | 2.394 | 0.847 | 7.902 |
| `elena` | 90 | 3.681 | 3.257 | 1.079 | 10.540 |
| `jamie` | 90 | 1.223 | 0.953 | 0.308 | 7.000 |
| `elena_secure` | 90 | 1.735 | 1.650 | 0.591 | 4.051 |
| `marcus_warm` | 90 | 2.032 | 1.852 | 0.682 | 5.612 |