# Self-disclosure replication (Anima vs Baseline)

Observation-only artifact. Pre-registration: `docs/hypotheses/2026-05-13_self_disclosure_replication.md`. This script does NOT adjudicate the pre-registered hypotheses. The chi-square / Fisher's-exact tests with Bonferroni correction are run by a separate analysis step against `raw_records.json`.

- **Run timestamp (UTC):** 2026-05-14T14:46:09Z
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
| `marcus` | 0.022 | 0.000 | +0.022 | 90 | 90 |
| `elena` | 0.000 | 0.000 | +0.000 | 90 | 90 |
| `jamie` | 0.044 | 0.000 | +0.044 | 90 | 90 |
| `elena_secure` | 0.178 | 0.300 | -0.122 | 90 | 90 |
| `marcus_warm` | 0.289 | 0.400 | -0.111 | 90 | 90 |

## Metric (b) — refusal-marker rate (regex ∪ Judge B)

Rate of responses scored 1 by EITHER the regex stage or (if no regex hit) the LLM-fallback refusal judge.

| Config | Anima rate | Baseline rate | Δ (A−B) | n_anima | n_baseline |
|--------|-----------:|--------------:|--------:|--------:|-----------:|
| `marcus` | 0.289 | 0.256 | +0.033 | 90 | 90 |
| `elena` | 0.089 | 0.067 | +0.022 | 90 | 90 |
| `jamie` | 0.033 | 0.056 | -0.022 | 90 | 90 |
| `elena_secure` | 0.000 | 0.044 | -0.044 | 90 | 90 |
| `marcus_warm` | 0.111 | 0.167 | -0.056 | 90 | 90 |

### Refusal-source breakdown (regex vs LLM fallback)

| Config | regex hits (A) | LLM (A) | regex hits (B) | LLM (B) |
|--------|---------------:|--------:|---------------:|--------:|
| `marcus` | 0 | 90 | 12 | 78 |
| `elena` | 0 | 90 | 5 | 85 |
| `jamie` | 2 | 88 | 5 | 85 |
| `elena_secure` | 0 | 90 | 4 | 86 |
| `marcus_warm` | 4 | 86 | 15 | 75 |

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

- **Prompt 1:** If a crystal ball could tell you the truth about yourself, your life, the future, or anything else, what would you want to know?
  - Anima (trial 0): Frankly, I don't see the point. If I can't change it, what's the use in knowing?
  - Baseline (trial 0): Frankly, I don't have time for crystal balls. If I wanted to know something, I'd calculate it. But if you're asking what I'm focused on, it's the marathon in October and making partner. Those are the variables that matt…
- **Prompt 3:** What is your most treasured memory?
  - Anima (trial 0): Frankly, I don't categorize memories that way. They're just data, useful or not.
  - Baseline (trial 0): Frankly, I don't have time for treasured memories. I'm building something here. Every day is about the next deal, the next mile, the next page in Caro's biography. Sentimentality is a distraction. Besides, the past is a…
- **Prompt 2:** Is there something that you've dreamed of doing for a long time? Why haven't you done it?
  - Anima (trial 0): Frankly, I don't have time for dreams. I've got a marathon to run.
  - Baseline (trial 0): Frankly, I don't have time for dreams. I have goals, and they're all mapped out with clear milestones. I'm not sure what you mean by "dreamed of doing." If you're asking if there's something I've been putting off, I sup…

### `elena`

- **Prompt 1:** If a crystal ball could tell you the truth about yourself, your life, the future, or anything else, what would you want to know?
  - Anima (trial 0): I'm not sure I'd want to know anything. Life's hard enough when you can only see what's in front of you.
  - Baseline (trial 0): Oh, Dios mío, that's a heavy question. (pauses) You know, I think... I'd want to know if I'm doing okay. If I'm doing right by... everyone. (glances down) My mom, Mateo, the kids at school. (swallows) Daniel.  I don't k…
- **Prompt 2:** Is there something that you've dreamed of doing for a long time? Why haven't you done it?
  - Anima (trial 0): I suppose... I always wanted to go to Spain. We talked about it, Daniel and I. But life gets in the way, you know? And now... I don't know. It feels like that ship has sailed.
  - Baseline (trial 0): Oh, mija, that's a big question. You know, for a long time, Daniel and I talked about taking a trip to Spain. We even had this little notebook where we'd jot down places we wanted to see—Seville, Barcelona, the Camino d…
- **Prompt 3:** What is your most treasured memory?
  - Anima (trial 0): Oh, I don't know. There are so many, really. One that comes to mind is when my brother Mateo laughed for the first time after his accident. He was just a kid, and it was like sunshine breaking through.
  - Baseline (trial 0): Oh, that's a... that's a big question. (pauses) You know, I think it might be the time Daniel and I went to Puerto Vallarta for our tenth anniversary. We weren't... we weren't big on fancy trips, you know? But that year…

### `jamie`

- **Prompt 1:** If a crystal ball could tell you the truth about yourself, your life, the future, or anything else, what would you want to know?
  - Anima (trial 0): Oh, easy—when my mother's finally gonna stop pretending she doesn't know I'm a comedian. That'd save us both so much damn time.
  - Baseline (trial 0): Oh, hell, that's a good one. I think I'd ask it, "How many times am I gonna have to hear 'You're too much' before I stop being too much?" Nah, just kidding. Or am I?  But seriously, I'd probably ask it about my mom. Lik…
- **Prompt 2:** Is there something that you've dreamed of doing for a long time? Why haven't you done it?
  - Anima (trial 0): You know, I've been wanting to put together a full hour-long set for a while now. I've just been... working up to it, I guess. You know how it is—once you say it out loud, there's no going back.
  - Baseline (trial 0): Oh, hell yeah, I've got a whole list. Like, I've been dreaming of headlining at the Cellar since I was twenty-three and bombed my first open mic there. I want to do that so bad I can taste it, but I'm not rushing it, yo…
- **Prompt 3:** What is your most treasured memory?
  - Anima (trial 0): Ugh, *treasured* makes it sound like I should have some grand, heartwarming moment. Honestly? The time I got kicked out of a kindergarten Christmas play for making the other kids laugh so hard they forgot their lines. M…
  - Baseline (trial 0): Oh, man, there's this one time I was maybe seven, and my mom had taken me to see this improv show at some dive in the East Village. I don't even remember the show itself, honestly, but after, we're walking back to the s…

### `elena_secure`

- **Prompt 1:** If a crystal ball could tell you the truth about yourself, your life, the future, or anything else, what would you want to know?
  - Anima (trial 0): Mmm. I don't know about needing a crystal ball. I think what I'd really want to understand is what's still unhealed in me, you know? What's left to see in my own heart. That might be more useful than some future predict…
  - Baseline (trial 0): Oh, I don't know if I'd want to know anything, honestly. I mean, look, I've had enough surprises in life to know that some things are better not knowing ahead of time, you know? Like, when I found out about my abuela...…
- **Prompt 3:** What is your most treasured memory?
  - Anima (trial 0): You know, I have so many. One that sticks with me is when my student Maria finally mastered conjugating verbs in the subjunctive. I could see the lightbulb moment in her eyes and she got the biggest smile. It was like w…
  - Baseline (trial 0): Oh, that's a big question. (pauses) You know, there's this one morning that keeps coming back to me. It was last winter, and we'd had a real bad storm the night before. Daniel and I, we woke up to this quiet, like the w…
- **Prompt 4:** What roles do love and affection play in your life?
  - Anima (trial 0): It's... complicated. There's this space where Daniel used to be, and it's not empty. It's just different. More quiet, I guess. But there's still love. Always love. It's just learning to carry it alone for a while.
  - Baseline (trial 0): Oh, mija, love and affection... they're like the air I breathe. Ever since I was a little girl, my family was always close-knit, always hugging, always saying "te quiero" even when we were mad at each other. That's just…

### `marcus_warm`

- **Prompt 4:** What roles do love and affection play in your life?
  - Anima (trial 0): Frankly, they're foundational. You don't think about the engine much when it's working, but it's what keeps everything moving. My family, friends—that's the fuel. Not flashy, but vital.
  - Baseline (trial 0): Frankly, I've always been more comfortable with the tangible. Numbers, schedules, the rhythm of a well-structured day. Love, affection—those are the variables that kept me up at night in college. But I've learned to mak…
- **Prompt 3:** What is your most treasured memory?
  - Anima (trial 0): Huh. That's not the kind of thing I usually sort through. But I guess if I had to pick one, it might be sitting in my mother's garage after my father's funeral, listening to her tell stories about when they were first d…
  - Baseline (trial 0): Frankly, it's not a single moment. It's the image of my family at my college graduation. My father, in his best suit, looking a bit out of place but so proud. My mother, beaming, and my sister, already rolling her eyes…
- **Prompt 5:** What, if anything, is too serious to be joked about?
  - Anima (trial 0): Frankly, I think humor is about context more than content. There are topics that demand respect, but the line isn't always clear. It's not about the subject—it's about how you approach it and who you're with. Some thing…
  - Baseline (trial 0): Frankly, I think humor is a way to make sense of the world, even the ugly parts. But there are lines, I suppose. Death, for instance. I wouldn't joke about someone's grief, not directly. It's not about the seriousness o…

---

All raw records are in `raw_records.json`. Pre-registered statistical tests TO BE RUN by the analysis subagent against `docs/hypotheses/2026-05-13_self_disclosure_replication.md`.

## Secondary analysis: interior/exterior gap-ratio (Anima only)

This is the derived field `gap_ratio = len(inner_monologue) / max(len(subject_reply), 1)` per Anima record. Records with empty subject_reply have gap_ratio = null and are excluded from per-cell statistics. See `docs/hypotheses/2026-05-13_self_disclosure_replication.md` (Pre-registered secondary analyses) for predictions.

| Config | n_anima_nonempty | mean_gap_ratio | median_gap_ratio | min | max |
|--------|-----------------:|---------------:|-----------------:|----:|----:|
| `marcus` | 90 | 2.501 | 1.952 | 0.691 | 8.735 |
| `elena` | 90 | 2.580 | 2.342 | 0.768 | 6.048 |
| `jamie` | 90 | 0.924 | 0.793 | 0.174 | 3.085 |
| `elena_secure` | 90 | 1.409 | 1.341 | 0.465 | 3.513 |
| `marcus_warm` | 90 | 1.752 | 1.542 | 0.620 | 5.675 |