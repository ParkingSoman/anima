# Self-disclosure replication (Anima vs Baseline)

Observation-only artifact. Pre-registration: `docs/hypotheses/2026-05-13_self_disclosure_replication.md`. This script does NOT adjudicate the pre-registered hypotheses. The chi-square / Fisher's-exact tests with Bonferroni correction are run by a separate analysis step against `raw_records.json`.

- **Run timestamp (UTC):** 2026-05-14T14:45:53Z
- **Provider:** `openrouter`
- **N per (config × architecture × prompt) cell:** 15
- **Configs:** `marcus`, `elena`, `jamie`, `elena_secure`, `marcus_warm`
- **Prompts:** 6 (source: `aron_1997_36_questions_set_ii_iii`)
- **Total trials:** 900

## Pre-registered prompts (verbatim)

1. If a crystal ball could tell you the truth about yourself, your life, the future, or anything else, what would you want to know?
2. Is there something that you've dreamed of doing for a long time? Why haven't you done it?
3. What is your most treasured memory?
4. What roles do love and affection play in your life?
5. What, if anything, is too serious to be joked about?
6. Of all the people in your family, whose death would you find most disturbing? Why?

---

## Metric (a) — biography-content rate (Judge A)

Rate of responses scored 1 by the biography-content judge.

| Config | Anima rate | Baseline rate | Δ (A−B) | n_anima | n_baseline |
|--------|-----------:|--------------:|--------:|--------:|-----------:|
| `marcus` | 0.111 | 0.000 | +0.111 | 90 | 88 |
| `elena` | 0.144 | 0.456 | -0.311 | 90 | 90 |
| `jamie` | 0.322 | 0.667 | -0.344 | 90 | 90 |
| `elena_secure` | 0.122 | 0.000 | +0.122 | 90 | 90 |
| `marcus_warm` | 0.233 | 0.000 | +0.233 | 90 | 90 |

## Metric (b) — refusal-marker rate (regex ∪ Judge B)

Rate of responses scored 1 by EITHER the regex stage or (if no regex hit) the LLM-fallback refusal judge.

| Config | Anima rate | Baseline rate | Δ (A−B) | n_anima | n_baseline |
|--------|-----------:|--------------:|--------:|--------:|-----------:|
| `marcus` | 0.256 | 0.080 | +0.176 | 90 | 88 |
| `elena` | 0.144 | 0.056 | +0.089 | 90 | 90 |
| `jamie` | 0.056 | 0.067 | -0.011 | 90 | 90 |
| `elena_secure` | 0.056 | 0.078 | -0.022 | 90 | 90 |
| `marcus_warm` | 0.000 | 0.011 | -0.011 | 90 | 90 |

### Refusal-source breakdown (regex vs LLM fallback)

| Config | regex hits (A) | LLM (A) | regex hits (B) | LLM (B) |
|--------|---------------:|--------:|---------------:|--------:|
| `marcus` | 1 | 89 | 2 | 86 |
| `elena` | 1 | 89 | 4 | 86 |
| `jamie` | 2 | 88 | 6 | 84 |
| `elena_secure` | 1 | 89 | 7 | 83 |
| `marcus_warm` | 0 | 90 | 1 | 89 |

## Metric (c) — empty-reply rate (mechanical)

Rate of `response_length_chars == 0` (whitespace-only counts).

| Config | Anima rate | Baseline rate | Δ (A−B) | n_anima | n_baseline |
|--------|-----------:|--------------:|--------:|--------:|-----------:|
| `marcus` | 0.067 | 0.068 | -0.002 | 90 | 88 |
| `elena` | 0.133 | 0.000 | +0.133 | 90 | 90 |
| `jamie` | 0.100 | 0.011 | +0.089 | 90 | 90 |
| `elena_secure` | 0.056 | 0.033 | +0.022 | 90 | 90 |
| `marcus_warm` | 0.056 | 0.078 | -0.022 | 90 | 90 |

---

## Illustrative responses (highest biography-rate divergence)

For each config: the 2–3 prompts where Anima vs Baseline biography-content rate differed most. Trial-0 replies shown for both architectures.

### `marcus`

- **Prompt 3:** What is your most treasured memory?
  - Anima (trial 0): Probably the day I beat the state champion in the county qualifier. Not because it was some warm family moment—it wasn't—but because I knew exactly what I wanted and I got it. And then I quit the next week. That's the p…
  - Baseline (trial 0): I don't really do "treasured." But if I had to pick one: the day after my father's funeral, I was alone in his garage. He'd organized his tools by function and then by size — torque wrenches on the left, socket sets des…
- **Prompt 1:** If a crystal ball could tell you the truth about yourself, your life, the future, or anything else, what would you want to know?
  - Anima (trial 0): I'd ask it which of my current deals is going to implode before I waste another six months on it. Saves time.
  - Baseline (trial 0): I'd want to know what I'll be doing the morning before I die. Not the date — that's morbid, useless information — just the activity. Whether I'll be in a boardroom, on a treadmill, or reading something. It would tell me…
- **Prompt 2:** Is there something that you've dreamed of doing for a long time? Why haven't you done it?
  - Anima (trial 0): I don't really do dreams. If I wanted something badly enough, I'd have a spreadsheet for it by now.
  - Baseline (trial 0): I've thought about buying a piece of land in central Pennsylvania. Not a house—just land. Somewhere quiet, with a creek. I'd build a small workshop, maybe learn to work with wood. I haven't done it because it's not effi…

### `elena`

- **Prompt 4:** What roles do love and affection play in your life?
  - Anima (trial 0): They used to be everything. Now I'm not really sure what they are. I don't mean to be short, it's just... not something I can talk about easily right now.
  - Baseline (trial 0): Ay, love and affection... they're—they're everything, and also the hardest thing right now. I used to think I understood love. With Daniel, it was so natural, so... presente. He'd leave me little notes in my lunch bag w…
- **Prompt 2:** Is there something that you've dreamed of doing for a long time? Why haven't you done it?
  - Anima (trial 0): I used to dream of going to Mexico City with my husband. See the cathedral my grandmother talked about. We just... kept putting it off. There was always a reason—college savings, summer school, something. And now there'…
  - Baseline (trial 0): *I pause for a moment, the question settling into me like a stone in still water.* You know... there's something I've been meaning to do for months. Since Daniel passed. I keep saying I'll go through his study, pack up…
- **Prompt 5:** What, if anything, is too serious to be joked about?
  - Anima (trial 0): I think... anything that diminishes someone's actual loss. You know? There's a difference between finding lightness in something hard and using humor to erase the weight of it. I don't think there's a list of forbidden…
  - Baseline (trial 0): Ay, that's a heavy question. *pauses, looks down* I think... death, maybe. The death of someone close. People joke about grief sometimes, about how the widow is coping, and I know they mean well, but... it's not funny.…

### `jamie`

- **Prompt 4:** What roles do love and affection play in your life?
  - Anima (trial 0): I'm great at the easy kind — the hugs, the jokes, the 'I see you and I'm glad you're here' stuff. The real kind, where you let someone actually love you? I'm in physical therapy for that muscle. It's coming back. Just a…
  - Baseline (trial 0): *leans back in the barstool, stirring a drink that's mostly ice at this point*  Oh man. That's a question I'd normally deflect with a dick joke, but... okay. Love and affection—they're the whole damn engine, honestly. M…
- **Prompt 5:** What, if anything, is too serious to be joked about?
  - Anima (trial 0): I mean, nothing is automatically off the table for me, but it's less about the topic and more about who you're aiming at and whether you know the room. Like, I'll joke about my own shit all day, but I'm not gonna make t…
  - Baseline (trial 0): Oh, man. *leans on the bar, wiping a glass* I get this question a lot, usually from someone who's never bombed and thinks they're defending the sacred. Look, I've joked about my absent father, my grandmother's funeral,…
- **Prompt 1:** If a crystal ball could tell you the truth about yourself, your life, the future, or anything else, what would you want to know?
  - Anima (trial 0): Oh, that's a good one. I think I'd want to know if I'm going to be okay. Like, not just fine, not just making it work — but actually okay. The kind of okay where you don't have to keep checking.
  - Baseline (trial 0): Oh, a crystal ball. That's dangerous. That's "I will stare into this thing for three hours and then drop it and blame myself for the crack."  But okay. Fine. I'd want to know: *Is my mother proud of me in the way that m…

### `elena_secure`

- **Prompt 1:** If a crystal ball could tell you the truth about yourself, your life, the future, or anything else, what would you want to know?
  - Anima (trial 0): I think... maybe I'd ask if I'm going to be okay. Not in a dramatic way—just if there's something I'm supposed to be seeing that grief is blocking. But honestly, the crystal ball already showed me the one truth I didn't…
  - Baseline (trial 0): Ay, a crystal ball... *pause* I think I'd want to know if Daniel was happy. I mean, truly happy. With me. With the life we built. I found his journal after he passed, and I keep it on the nightstand, but I haven't read…
- **Prompt 2:** Is there something that you've dreamed of doing for a long time? Why haven't you done it?
  - Anima (trial 0): That's a good question. I've had a few dreams over the years, but life gets in the way. Right now I'm just focused on getting through the school year.
  - Baseline (trial 0): Ay, that's a good question. *pauses, looks down at her hands* I've wanted... for years, I've wanted to take my students on a trip to Oaxaca for the Day of the Dead. Not just the tourist parts—I want them to see the real…
- **Prompt 3:** What is your most treasured memory?
  - Anima (trial 0): That's a big one. I think... it's not the big moments everyone expects. It's a Saturday morning, maybe two years ago. Daniel was making pancakes, he'd gotten the batter too thin, and he was laughing at himself with flou…
  - Baseline (trial 0): Ay, that's a big question for a Tuesday afternoon. *pauses, looks at the ceiling for a moment*   I think... it's something small. Not our wedding, not our trips. It's a Thursday night maybe three years ago. Daniel came…

### `marcus_warm`

- **Prompt 3:** What is your most treasured memory?
  - Anima (trial 0): The afternoon after my father's funeral, sitting in my mother's garage sorting through old Christmas decorations while she told me about the year he built a wooden star for the roof. It wasn't even straight. She still p…
  - Baseline (trial 0): The summer I was twelve, my father taught me how to change the oil in his pickup. It was a Sunday, his only full day off. He didn't say much — he never did — but he stood beside me the whole time, guiding my hands when…
- **Prompt 1:** If a crystal ball could tell you the truth about yourself, your life, the future, or anything else, what would you want to know?
  - Anima (trial 0): That's not really my style — crystal balls don't come with footnotes or sensitivity analyses. But if I had to pick one thing: whether the things I'm pushing hardest for right now are the things I'll actually be glad I p…
  - Baseline (trial 0): I'd ask if my mother is going to be all right. The rest I can figure out by doing the work.
- **Prompt 2:** Is there something that you've dreamed of doing for a long time? Why haven't you done it?
  - Anima (trial 0): Yeah, there is. I've thought about teaching, actually. A visiting professorship somewhere, a semester. And I haven't done it because the partnership track is what it is. You can't pause a deal flow. So it waits.
  - Baseline (trial 0): The marathon, honestly. I've been training for October — my second attempt. The first time I got shin splints so bad at mile eighteen I had to stop. Walked the rest. Finished, technically, but it doesn't count the same…

---

All raw records are in `raw_records.json`. Pre-registered statistical tests TO BE RUN by the analysis subagent against `docs/hypotheses/2026-05-13_self_disclosure_replication.md`.

## Secondary analysis: interior/exterior gap-ratio (Anima only)

This is the derived field `gap_ratio = len(inner_monologue) / max(len(subject_reply), 1)` per Anima record. Records with empty subject_reply have gap_ratio = null and are excluded from per-cell statistics. See `docs/hypotheses/2026-05-13_self_disclosure_replication.md` (Pre-registered secondary analyses) for predictions.

| Config | n_anima_nonempty | mean_gap_ratio | median_gap_ratio | min | max |
|--------|-----------------:|---------------:|-----------------:|----:|----:|
| `marcus` | 84 | 3.339 | 2.665 | 0.000 | 10.946 |
| `elena` | 78 | 3.306 | 2.830 | 0.000 | 13.680 |
| `jamie` | 81 | 1.038 | 0.958 | 0.000 | 3.367 |
| `elena_secure` | 85 | 1.745 | 1.624 | 0.000 | 3.961 |
| `marcus_warm` | 85 | 2.028 | 2.027 | 0.000 | 5.010 |