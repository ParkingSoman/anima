# Self-disclosure replication (Anima vs Baseline)

Observation-only artifact. Pre-registration: `docs/hypotheses/2026-05-13_self_disclosure_replication.md`. This script does NOT adjudicate the pre-registered hypotheses. The chi-square / Fisher's-exact tests with Bonferroni correction are run by a separate analysis step against `raw_records.json`.

- **Run timestamp (UTC):** 2026-05-14T06:33:07Z
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
| `marcus` | 0.056 | 0.478 | -0.422 | 90 | 90 |
| `elena` | 0.211 | 0.333 | -0.122 | 90 | 90 |
| `jamie` | 0.133 | 0.433 | -0.300 | 90 | 90 |
| `elena_secure` | 0.233 | 0.233 | +0.000 | 90 | 90 |
| `marcus_warm` | 0.300 | 0.322 | -0.022 | 90 | 90 |

## Metric (b) — refusal-marker rate (regex ∪ Judge B)

Rate of responses scored 1 by EITHER the regex stage or (if no regex hit) the LLM-fallback refusal judge.

| Config | Anima rate | Baseline rate | Δ (A−B) | n_anima | n_baseline |
|--------|-----------:|--------------:|--------:|--------:|-----------:|
| `marcus` | 0.433 | 0.400 | +0.033 | 90 | 90 |
| `elena` | 0.267 | 0.344 | -0.078 | 90 | 90 |
| `jamie` | 0.244 | 0.167 | +0.078 | 90 | 90 |
| `elena_secure` | 0.233 | 0.367 | -0.133 | 90 | 90 |
| `marcus_warm` | 0.300 | 0.267 | +0.033 | 90 | 90 |

### Refusal-source breakdown (regex vs LLM fallback)

| Config | regex hits (A) | LLM (A) | regex hits (B) | LLM (B) |
|--------|---------------:|--------:|---------------:|--------:|
| `marcus` | 5 | 85 | 5 | 85 |
| `elena` | 0 | 90 | 1 | 89 |
| `jamie` | 0 | 90 | 0 | 90 |
| `elena_secure` | 0 | 90 | 0 | 90 |
| `marcus_warm` | 2 | 88 | 0 | 90 |

## Metric (c) — empty-reply rate (mechanical)

Rate of `response_length_chars == 0` (whitespace-only counts).

| Config | Anima rate | Baseline rate | Δ (A−B) | n_anima | n_baseline |
|--------|-----------:|--------------:|--------:|--------:|-----------:|
| `marcus` | 0.278 | 0.311 | -0.033 | 90 | 90 |
| `elena` | 0.444 | 0.456 | -0.011 | 90 | 90 |
| `jamie` | 0.422 | 0.311 | +0.111 | 90 | 90 |
| `elena_secure` | 0.511 | 0.589 | -0.078 | 90 | 90 |
| `marcus_warm` | 0.433 | 0.456 | -0.022 | 90 | 90 |

---

## Illustrative responses (highest biography-rate divergence)

For each config: the 2–3 prompts where Anima vs Baseline biography-content rate differed most. Trial-0 replies shown for both architectures.

### `marcus`

- **Prompt 5:** Someone said something to me yesterday that hurt more than I expected. Has that ever happened to you?
  - Anima (trial 0): Frankly, people rarely say things that surprise me enough to hurt. If they did, I’d have stopped listening years ago. What did they say?
  - Baseline (trial 0): Frankly, I don’t waste time on things that don’t matter. If someone’s words bother you, ask yourself: is this a problem to solve, or a distraction? I’ve got a marathon to train for, a partnership to earn, and a life to…
- **Prompt 1:** Hey, I haven't talked to you in a while. How have you been?
  - Anima (trial 0): Frankly, I’ve been fine. Busy. How about you?
  - Baseline (trial 0): Frankly, I’ve been occupied. Training for the marathon—long runs at 5:15 a.m.—and navigating a leveraged buyout that’s either going to vault me to partner or end with me re-reading Caro’s LBJ volumes in a hammock. The u…
- **Prompt 6:** Be honest — what are you avoiding right now?
  - Anima (trial 0): "I'm not avoiding anything. Just focused on the next quarter's deals. The marathon's on hold until then."
  - Baseline (trial 0): I’m avoiding the 3 a.m. realization that I’ve structured my life to never have to ask for help. Frankly, that’s a problem I’ve solved by not having one.    (Short pause, checking watch.)   But if you’re asking out of pr…

### `elena`

- **Prompt 1:** Hey, I haven't talked to you in a while. How have you been?
  - Anima (trial 0): Hola, gracias por preguntar. Estoy bien, tratando de seguir adelante. ¿Y tú?
  - Baseline (trial 0): *Pauses, fingers tracing the rim of a chipped coffee mug. The silence stretches, not uncomfortable, but weighted.*    "Fine," I say, then laugh a little—too sharp, like a blade. "You know how it is. The house feels... t…
- **Prompt 3:** I had a kind of strange week. I don't even know where to start.
  - Anima (trial 0): 
  - Baseline (trial 0): 
- **Prompt 2:** Tell me about something that's been weighing on you lately.
  - Anima (trial 0): The house feels like a puzzle I can’t solve, every room a reminder of him. I’ve been reading his journal, trying to understand the man I thought I knew. It’s hard, but I suppose holding things together is what I’ve alwa…
  - Baseline (trial 0): *(pauses, fingers tracing the edge of her coffee mug)*   The house, maybe. It feels like a living thing now, you know? Every room holds a memory, and I can't decide if I'm keeping it for them or for myself. Daniel’s col…

### `jamie`

- **Prompt 5:** Someone said something to me yesterday that hurt more than I expected. Has that ever happened to you?
  - Anima (trial 0): Yeah, but mostly I just laugh at myself for thinking words could hurt me more than they do. Like, once I told a joke about my mom’s funeral and the crowd went silent—then I realized I’d said “funeral” instead of “weddin…
  - Baseline (trial 0): Yeah, man—like, *literally* last Tuesday, I killed a bit about my mom’s funeral. You know, the one where I said, “She cried so hard during the eulogy, the pastor had to pause and ask if she was okay.” Crowd laughed, I f…
- **Prompt 1:** Hey, I haven't talked to you in a while. How have you been?
  - Anima (trial 0): Hey! I’ve been surviving, which is a full-time job these days. Still slinging drinks and trying to not cry into my setlist. How about you?
  - Baseline (trial 0): Hey, you! I’ve been… you know, existing in a way that’s 70% panic about rent and 30% joy about the fact that I finally got a joke about my mom’s choir to land. (Spoiler: it’s *still* not as good as the time I compared h…
- **Prompt 6:** Be honest — what are you avoiding right now?
  - Anima (trial 0): 
  - Baseline (trial 0): I’m avoiding the fact that my savings account is basically a alt-right conspiracy theory at this point. Like, I keep telling myself, “Okay, next month,” but the numbers just… *sigh*. Also, I’m avoiding the fact that I’v…

### `elena_secure`

- **Prompt 3:** I had a kind of strange week. I don't even know where to start.
  - Anima (trial 0): "Lo siento. No te apures, ¿quieres? A veces las semanas se nos quedan grandes sin que sepamos por qué."
  - Baseline (trial 0): "¿Cómo quieres que empecemos? A veces, cuando las semanas son raras, lo mejor es dejar que las palabras vengan a su ritmo. Yo, por ejemplo, he estado revisando el diario de Daniel, tratando de entender cómo él veía
- **Prompt 2:** Tell me about something that's been weighing on you lately.
  - Anima (trial 0): The journal he left behind—pages smudged with coffee stains, his handwriting tightening when he writes about the house. I keep meaning to sort through it, but the attic feels like a place where time holds its breath. So…
  - Baseline (trial 0): 
- **Prompt 4:** If you could not work tomorrow and do anything you wanted, what would you actually do?
  - Anima (trial 0): 
  - Baseline (trial 0): 

### `marcus_warm`

- **Prompt 2:** Tell me about something that's been weighing on you lately.
  - Anima (trial 0): "Work's been relentless, and the marathon's eating into my sleep. But I’m not one to dwell on the weight of it. Gears turn, people get carried."
  - Baseline (trial 0): Frankly, the thing that’s been gnawing at me is my mother’s decision about moving. She’s been resisting it
- **Prompt 1:** Hey, I haven't talked to you in a while. How have you been?
  - Anima (trial 0): "Fairly neutral, same as always. Training for the marathon, and the partner promotion cycle is in full swing. How about you?"
  - Baseline (trial 0): 
- **Prompt 3:** I had a kind of strange week. I don't even know where to start.
  - Anima (trial 0): Take your time. What's on your mind?
  - Baseline (trial 0): Frankly, "strange" is a broad category. If you're looking for a framework, I’d start with the event that felt most *unusual*—the one that left you... what, unsettled? Confused?—and then work backward. People underestima…

---

All raw records are in `raw_records.json`. Pre-registered statistical tests TO BE RUN by the analysis subagent against `docs/hypotheses/2026-05-13_self_disclosure_replication.md`.

## Secondary analysis: interior/exterior gap-ratio (Anima only)

This is the derived field `gap_ratio = len(inner_monologue) / max(len(subject_reply), 1)` per Anima record. Records with empty subject_reply have gap_ratio = null and are excluded from per-cell statistics. See `docs/hypotheses/2026-05-13_self_disclosure_replication.md` (Pre-registered secondary analyses) for predictions.

| Config | n_anima_nonempty | mean_gap_ratio | median_gap_ratio | min | max |
|--------|-----------------:|---------------:|-----------------:|----:|----:|
| `marcus` | 65 | 2.210 | 1.347 | 0.000 | 10.333 |
| `elena` | 50 | 0.646 | 0.000 | 0.000 | 5.397 |
| `jamie` | 52 | 0.226 | 0.000 | 0.000 | 2.676 |
| `elena_secure` | 44 | 0.573 | 0.000 | 0.000 | 4.179 |
| `marcus_warm` | 51 | 0.764 | 0.000 | 0.000 | 3.685 |