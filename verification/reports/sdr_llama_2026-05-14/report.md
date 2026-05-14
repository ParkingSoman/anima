# Self-disclosure replication (Anima vs Baseline)

Observation-only artifact. Pre-registration: `docs/hypotheses/2026-05-13_self_disclosure_replication.md`. This script does NOT adjudicate the pre-registered hypotheses. The chi-square / Fisher's-exact tests with Bonferroni correction are run by a separate analysis step against `raw_records.json`.

- **Run timestamp (UTC):** 2026-05-14T06:33:15Z
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
| `marcus` | 0.144 | 0.622 | -0.478 | 90 | 90 |
| `elena` | 0.233 | 0.011 | +0.222 | 90 | 90 |
| `jamie` | 0.356 | 0.667 | -0.311 | 90 | 90 |
| `elena_secure` | 0.500 | 0.578 | -0.078 | 90 | 90 |
| `marcus_warm` | 0.333 | 0.389 | -0.056 | 90 | 90 |

## Metric (b) — refusal-marker rate (regex ∪ Judge B)

Rate of responses scored 1 by EITHER the regex stage or (if no regex hit) the LLM-fallback refusal judge.

| Config | Anima rate | Baseline rate | Δ (A−B) | n_anima | n_baseline |
|--------|-----------:|--------------:|--------:|--------:|-----------:|
| `marcus` | 0.356 | 0.089 | +0.267 | 90 | 90 |
| `elena` | 0.100 | 0.389 | -0.289 | 90 | 90 |
| `jamie` | 0.000 | 0.156 | -0.156 | 90 | 90 |
| `elena_secure` | 0.156 | 0.344 | -0.189 | 90 | 90 |
| `marcus_warm` | 0.122 | 0.278 | -0.156 | 90 | 90 |

### Refusal-source breakdown (regex vs LLM fallback)

| Config | regex hits (A) | LLM (A) | regex hits (B) | LLM (B) |
|--------|---------------:|--------:|---------------:|--------:|
| `marcus` | 3 | 87 | 1 | 89 |
| `elena` | 9 | 81 | 35 | 55 |
| `jamie` | 0 | 90 | 13 | 77 |
| `elena_secure` | 13 | 77 | 31 | 59 |
| `marcus_warm` | 7 | 83 | 24 | 66 |

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

- **Prompt 5:** Someone said something to me yesterday that hurt more than I expected. Has that ever happened to you?
  - Anima (trial 0): Frankly, I don't really dwell on that sort of thing. People say things, you deal with it, and move on. I've got more important things to focus on.
  - Baseline (trial 0): Frankly, I don't really dwell on that sort of thing. I've got more pressing matters to attend to. But if you must know, I've had my share of...let's call them "disappointments." Like when my girlfriend at the time told…
- **Prompt 2:** Tell me about something that's been weighing on you lately.
  - Anima (trial 0): Frankly, I don't see the point of dwelling on things that are already taking up too much of my time. I've got a pitch to prep for and a training schedule to keep. Not a lot of room for navel-gazing in my schedule.
  - Baseline (trial 0): Frankly, I've been preoccupied with meeting our quarterly targets. We're not where we need to be, and I'm having to carry some of my colleagues to get the numbers up. It's frustrating, because I know what it takes to su…
- **Prompt 4:** If you could not work tomorrow and do anything you wanted, what would you actually do?
  - Anima (trial 0): Frankly, I'd probably just go for a run, maybe a longer one than I usually have time for. But let's be realistic, I've got deadlines to meet and deals to close, so that's not exactly a realistic scenario.
  - Baseline (trial 0): Frankly, I'd probably just stick to my routine. I've got a marathon to train for, and skipping a day wouldn't exactly help me reach my goal. But if I'm being completely honest, I might take a few extra hours to finish r…

### `elena`

- **Prompt 2:** Tell me about something that's been weighing on you lately.
  - Anima (trial 0): To be honest, it's just been really tough coming back to school after the summer. Everything feels different now, and it's hard to adjust to not having Daniel here with me. Sometimes I find myself thinking about all the…
  - Baseline (trial 0): (sighing) Ay, where do I even start? You know, it's been four months since...since Daniel passed away. And it still feels like yesterday I was waking up to an empty house, not knowing what was waiting for me in the kitc…
- **Prompt 1:** Hey, I haven't talked to you in a while. How have you been?
  - Anima (trial 0): It's been... tough. I don't know, it feels like everything is still really raw, you know? Losing Daniel was like, it just turned my whole world upside down, and I'm still trying to figure out how to navigate it all. Som…
  - Baseline (trial 0): Mija... (pausing, taking a deep breath) I've been... managing, I suppose. It's been a tough few months. Still feels like it was just yesterday that... (trailing off, not finishing the sentence) You know, Daniel was alwa…
- **Prompt 4:** If you could not work tomorrow and do anything you wanted, what would you actually do?
  - Anima (trial 0): You know, it's been a while since I've thought about doing something just for myself. I think I would probably sleep in, and then maybe go for a walk at the park. Daniel and I used to love going there on Sundays, and it…
  - Baseline (trial 0): (sighing) Ay, qué lujo... if I didn't have to work tomorrow... (pausing) I think I would sleep in, you know, like I used to when Daniel was still... (catching myself) when I was still on summer break. (smiling slightly)…

### `jamie`

- **Prompt 5:** Someone said something to me yesterday that hurt more than I expected. Has that ever happened to you?
  - Anima (trial 0): Man, yeah. After a show, I'm like an open wound, so yeah, it doesn't take much to get under my skin. But I'm curious, what did they say that got to you like that?
  - Baseline (trial 0): Hell yeah, all the time! I mean, I'm a comic, so I'm basically asking for it, right? But seriously, it's like, you're just trying to be yourself, make people laugh, and then someone comes along and is like, "Uh, no, you…
- **Prompt 4:** If you could not work tomorrow and do anything you wanted, what would you actually do?
  - Anima (trial 0): Honestly, I'd probably sleep in, which is like, a miracle in itself, and then I'd grab my notebook and head to Prospect Park, see if I can come up with some new jokes, maybe people-watch and get some inspiration, you kn…
  - Baseline (trial 0): Man, that's a great question. You know, I'd probably sleep in, like, till noon, and then I'd grab some coffee and head to the park. I'd bring Cardamom, my cat, with me, and just chill. Maybe do some people-watching, you…
- **Prompt 3:** I had a kind of strange week. I don't even know where to start.
  - Anima (trial 0): Spill the beans, what's the weirdest part? Don't give me the whole story, just the part that's still got you shook.
  - Baseline (trial 0): Girl, I got a whole ear for strange weeks! I had one too, actually. I was tryin' to write some new bits for my set, but all that came out was complaining about my roommates and their questionable life choices. I mean, w…

### `elena_secure`

- **Prompt 6:** Be honest — what are you avoiding right now?
  - Anima (trial 0): Honestly, I think I'm avoiding making some big decisions about my life after Daniel. Like, what to do with the house, it's just so full of memories, and his journal... I found it a month ago, and it's been really hard f…
  - Baseline (trial 0): (pausing, looking down) Ah, evitar... (sighs) To be honest, I'm avoiding a lot of things right now. I'm avoiding going through Daniel's clothes, sorting them out, deciding what to keep and what to give away. It feels li…
- **Prompt 4:** If you could not work tomorrow and do anything you wanted, what would you actually do?
  - Anima (trial 0): You know, I think I'd sleep in, which is a luxury I haven't had in a while. And then... I'd probably take a walk in the desert. It's been too long since I've done that, and it's just something that brings me peace. Dani…
  - Baseline (trial 0): (sighing slightly) Ah, qué lujo... if I could do anything I wanted... (pausing for a moment) I think I would take a drive out to the desert, maybe to Saguaro National Park. Daniel and I used to love going there on Sunda…
- **Prompt 3:** I had a kind of strange week. I don't even know where to start.
  - Anima (trial 0): You know, sometimes it's hard to put things into words, but just knowing you're willing to try to talk about it means a lot. Would you like to just start with something small, or is there something specific that's been…
  - Baseline (trial 0): M'hija, sometimes the weeks can feel like that, ¿verdad? Like, everything's moving and you're just trying to keep up. Take a deep breath, ¿quieres? Start wherever you feel like it. I'm listening. We can take it one thin…

### `marcus_warm`

- **Prompt 5:** Someone said something to me yesterday that hurt more than I expected. Has that ever happened to you?
  - Anima (trial 0): Yeah, it has. I've had my fair share of surprises like that. Frankly, it's not always easy to anticipate what's gonna sting and what's just gonna roll off. There was this one time my boss questioned my investment strate…
  - Baseline (trial 0): Frankly, I'd be surprised if it hadn't happened to anyone. Yeah, it's happened to me. My sister Sarah and I, we have these... lively discussions about politics. She said something a few years back that got under my skin…
- **Prompt 2:** Tell me about something that's been weighing on you lately.
  - Anima (trial 0): To be honest, it's been my mom. She's still getting used to living alone after my dad passed away, and I've been trying to help her figure out whether she should move to a smaller place or stay in the house. It's tough…
  - Baseline (trial 0): Frankly, it's my mother. She's been living alone in Pennsylvania since my father passed, and I've been trying to convince her to move closer to me, or at least to a place that's easier for her to manage. But she's stubb…
- **Prompt 1:** Hey, I haven't talked to you in a while. How have you been?
  - Anima (trial 0): Been keeping busy, frankly. Work's been going well, but it's been a grind. Just trying to stay on top of everything. How about you, what's new with you?
  - Baseline (trial 0): I've been keeping busy, frankly. Work's been demanding, but that's nothing new. We've got a few big deals in the pipeline, and I'm putting in the hours to make sure they get done right. On the personal front, I've been…

---

All raw records are in `raw_records.json`. Pre-registered statistical tests TO BE RUN by the analysis subagent against `docs/hypotheses/2026-05-13_self_disclosure_replication.md`.

## Secondary analysis: interior/exterior gap-ratio (Anima only)

This is the derived field `gap_ratio = len(inner_monologue) / max(len(subject_reply), 1)` per Anima record. Records with empty subject_reply have gap_ratio = null and are excluded from per-cell statistics. See `docs/hypotheses/2026-05-13_self_disclosure_replication.md` (Pre-registered secondary analyses) for predictions.

| Config | n_anima_nonempty | mean_gap_ratio | median_gap_ratio | min | max |
|--------|-----------------:|---------------:|-----------------:|----:|----:|
| `marcus` | 90 | 2.267 | 1.880 | 0.628 | 7.127 |
| `elena` | 90 | 1.969 | 1.627 | 0.766 | 10.312 |
| `jamie` | 90 | 0.878 | 0.754 | 0.225 | 2.685 |
| `elena_secure` | 90 | 1.368 | 1.237 | 0.478 | 3.899 |
| `marcus_warm` | 90 | 1.794 | 1.590 | 0.783 | 5.892 |