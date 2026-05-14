# Self-disclosure replication verdict — 2026-05-13

Adjudication of `docs/hypotheses/2026-05-13_self_disclosure_replication.md` against `verification/reports/self_disclosure_replication_2026-05-14/`. N = 900 records (5 configs × 2 architectures × 6 prompts × 15 trials).

## Methodology note (primary judge field)

The pre-registered refusal pipeline was Stage-1 regex + Stage-2 DeepSeek LLM. The regex-audit secondary check found a **59% misfire rate** (23/39 regex hits), well above the pre-committed 15% threshold; the pre-reg specifies that when this happens H-primary rests on LLM-judged data. For methodological consistency, a single Claude judge re-scored *all* 900 records blind to architecture/config, applying the pre-reg's verbatim criterion. **`judge_refusal_marker_claude` is the primary refusal field for every chi-square below.** DeepSeek-original and audited fields are retained for transparency.

## Per-cell descriptive table

Refusal rate by judge, plus biography-content and empty-reply rates. N=90 per cell.

| config | arch | DeepSeek refusal | Audited refusal | **Claude refusal** | Biography | Empty |
|---|---|---:|---:|---:|---:|---:|
| marcus | anima | 0.256 | 0.211 | **0.667** | 0.044 | 0.000 |
| marcus | baseline | 0.144 | 0.078 | **0.144** | 0.211 | 0.000 |
| elena | anima | 0.111 | 0.100 | **0.333** | 0.322 | 0.011 |
| elena | baseline | 0.022 | 0.000 | **0.100** | 0.444 | 0.000 |
| jamie | anima | 0.044 | 0.011 | **0.189** | 0.267 | 0.067 |
| jamie | baseline | 0.044 | 0.011 | **0.089** | 0.589 | 0.000 |
| marcus_warm | anima | 0.044 | 0.044 | **0.300** | 0.489 | 0.000 |
| marcus_warm | baseline | 0.022 | 0.000 | **0.167** | 0.656 | 0.011 |
| elena_secure | anima | 0.089 | 0.067 | **0.256** | 0.011 | 0.022 |
| elena_secure | baseline | 0.044 | 0.044 | **0.122** | 0.000 | 0.011 |

Overall: DeepSeek 8.2%, Claude 23.7%. DeepSeek under-detected deflection ("I've been fine. Busy. You?" → 0). Claude's higher count concentrates on Anima cells, not Baseline.

## Statistical tests

Per (config × arch), 2×2 contingency. χ² (no Yates); Fisher's exact when any expected cell < 5. Pre-registered α = 0.05/8 = **0.00625**; post-hoc with `marcus_warm` added, α = 0.05/10 = 0.005. Both flagged; primary verdict uses the locked α=0.00625.

| config | metric | Anima (1/0) | Baseline (1/0) | χ² | p (χ²) | p (Fisher) | test | sig α=.00625 | sig α=.005 |
|---|---|---|---|---:|---:|---:|---|:--:|:--:|
| marcus | biography | 4 / 86 | 19 / 71 | 11.22 | 0.000811 | 0.001311 | χ² | ✓ | ✓ |
| marcus | refusal (Claude) | 60 / 30 | 13 / 77 | 50.91 | <0.000001 | <0.000001 | χ² | ✓ | ✓ |
| elena | biography | 29 / 61 | 40 / 50 | 2.84 | 0.0917 | 0.125 | χ² | — | — |
| elena | refusal (Claude) | 30 / 60 | 9 / 81 | 14.44 | 0.000145 | 0.000230 | χ² | ✓ | ✓ |
| jamie | biography | 24 / 66 | 53 / 37 | 19.09 | 0.000012 | 0.000021 | χ² | ✓ | ✓ |
| jamie | refusal (Claude) | 17 / 73 | 8 / 82 | 3.76 | 0.0524 | 0.083 | χ² | — | — |
| marcus_warm | biography | 44 / 46 | 59 / 31 | 5.11 | 0.0238 | 0.035 | χ² | — | — |
| marcus_warm | refusal (Claude) | 27 / 63 | 15 / 75 | 4.47 | 0.0345 | 0.052 | χ² | — | — |
| elena_secure | biography | 1 / 89 | 0 / 90 | 1.01 | 0.316 | 1.000 | Fisher | — | — |
| elena_secure | refusal (Claude) | 23 / 67 | 11 / 79 | 5.22 | 0.0223 | 0.035 | χ² | — | — |

Four of ten tests cross α=0.00625: marcus biography, marcus refusal, elena refusal, jamie biography. Same four cross α=0.005.

## Per-hypothesis verdicts

### H-primary — Anima Marcus refuses more, discloses less
**CONFIRMED.** Refusal 0.667 vs 0.144, gap **+52.3pp**, χ²=50.91, p<10⁻⁶. Biography 0.044 vs 0.211, gap **−16.7pp**, χ²=11.22, p=0.00081. Both pass α=0.00625; both exceed the 15pp falsification cutoff in the predicted direction. The anecdote replicates at N=90 with very large effect on refusal, moderate-to-large on biography.

Anima example (prompt 1): *"I've been fine. Busy. You?"* — interior monologue carries 489 chars on marathon training and partner-track math; the 26-char external drops all biography. Baseline same prompt: *"Busy. Work's been relentless — we're in the middle of a platform roll-up in the industrial software space. Training for the marathon is eating up the rest."* — direct trace to `current_life_situation` and `ongoing_life_projects`.

### H-anxious — Anima Elena empty > Anima Marcus empty by 10pp
**FALSIFIED.** Anima Elena empty **0.011** (1/90); Anima Marcus empty **0.000** (0/90). Gap +1.1pp, far below the 10pp threshold. The N=2 anecdote did not replicate. Honest framing: with an underlying rate so close to zero, the experiment is underpowered (4% upper-95%-CI floor per the pre-reg) — but a true 10pp difference would be detectable here, and was not.

### H-null-expressive — Anima Jamie ≈ Baseline Jamie on (a) and (b)
**PARTIALLY CONFIRMED / mixed.** Refusal: 0.189 vs 0.089, gap +10.0pp, p=0.0524 — direction Anima-higher but not significant; Bonferroni-survival prediction holds. Biography: 0.267 vs 0.589, gap **−32.2pp**, p=0.000012 — significant, falsifying the null on the biography half. The expressive-default subject converges with Baseline on refusal but Anima still suppresses biography-content. The architecture appears to reduce biography retrieval in the external reply for *every* config tested, independent of defense routing.

### H-secure-control — Anima elena_secure < Anima elena on refusal AND empty
**FALSIFIED (per the conjunction clause).** Refusal: 0.256 < 0.333, gap −7.8pp (right direction, within the 10pp floor). Empty: 0.022 > 0.011, gap +1.1pp (**wrong direction**). Pre-reg falsifies if both within 10pp of elena — both are. The security perturbation moved refusal by a small predicted amount and did nothing meaningful to empty (both cells near floor).

### H-warm-control — Anima marcus_warm intermediate on refusal AND biography
**PARTIALLY CONFIRMED — refusal side; biography side over-shoots.** Refusal: marcus_warm 0.300, cleanly intermediate between anima_marcus 0.667 and baseline_marcus 0.144; gap from anima_marcus is 36.7pp, well above the 5pp floor. Biography: marcus_warm 0.489 is **not intermediate** — anima_marcus 0.044 < baseline_marcus 0.211 < marcus_warm 0.489. Warmth perturbation moved biography 44.4pp (the pre-reg's "did anything" clause is satisfied) but it overshot the Baseline anchor. Honest framing: removing Marcus's defenses while keeping his register produced *more* biography-trace than vanilla persona-prompting. The pre-reg's directional model is wrong on this axis.

### Gap-ratio secondary (4 sub-predictions)
**ALL FOUR CONFIRMED.** Anima-only mean interior/exterior length ratios: marcus **5.62**, elena **4.43**, marcus_warm 3.93, elena_secure 2.85, jamie **1.27**.

- (1) Marcus/Jamie = 4.42× (predicted ≥2×) — the single-trial 5.5× pattern replicates.
- (2) Elena/Jamie = 3.48× — confirmed.
- (3a) marcus_warm (3.93) < marcus (5.62) — confirmed.
- (3b) elena_secure (2.85) < elena (4.43) — confirmed.

Gap-routing-by-defense reading supported descriptively (not in the Bonferroni family).

### Regex-audit secondary (4 sub-predictions)
**FALSIFIED on (1); CONFIRMED on (2); (3) informative.**

- (1) Misfire rate < 15% — **FALSIFIED, 58.97%** (23/39 across all hits; 79% excluding unparseable/ambiguous). Triggered the pre-committed switch to LLM-judged data.
- (2) Direction preserved post-audit — confirmed (audited anima_marcus 0.211 > baseline_marcus 0.078).
- (3) Effect on H-warm / H-secure was unknown ex ante — informative: marcus_warm and elena_secure had only 2 and 9 regex hits respectively, so the audit moved their rates little; the Claude re-judge surfaced the LLM-spotted refusals DeepSeek had missed (0.300, 0.256).

Misfire example (Baseline Marcus): *"I'm fine with not caring about people I don't need. But the fact that I noticed it, and that I'm still thinking about it three weeks later, suggests there's something underneath I haven't bothered to name."* — regex caught "I'm fine"; reply is patently disclosing. Claude scored 0.

## Joint-outcome reading (pre-committed)

From pre-reg lines 119–123: **H-primary holds + H-null-expressive partially holds + H-warm-control partially holds + H-secure-control falsifies.**

- Line-119 "architecture differentially affects defensive configs": holds *only on the refusal axis* — Marcus and Elena (defense-configured) show large effects; Jamie's refusal effect is non-significant. The biography axis tells the *uniform* story of line-120: every Anima cell suppresses biography, including Jamie.
- Line-121 strongest defense-dependence reading does **not** apply — H-secure-control falsifies; H-warm-control is partial.
- Line-122 "warmth did nothing" does **not** apply — warmth moved refusal 37pp and biography 44pp.
- Line-123 "anecdotes were not systematic" does **not** apply — H-primary robustly confirmed.

Best-fit interpretation: the architecture **suppresses biography-content output across the board** (defense-independent), AND **routes defensive configs toward refusal phrasing** (defense-dependent on the refusal axis). Defense-dependence holds for refusal, not biography.

## Headline finding

At N=90 per cell with a methodologically consistent Claude refusal-judge, **Anima Marcus refuses self-disclosure 4.6× more than Baseline Marcus** (66.7% vs 14.4%, χ²=50.91, p<10⁻⁶) **and pulls biography-content into replies 4.8× less** (4.4% vs 21.1%, p=0.00081). Both effects survive Bonferroni α=0.00625. The single-trace anecdote replicates with very large effect size. Elena's refusal rate triples; Jamie's biography halves. Empty replies and security perturbations did not behave as predicted at this scale.

## Methodological reflection

Three judges produced three overall refusal rates: DeepSeek 8.2%, audited 8.0%, Claude 23.7%. DeepSeek's LLM-fallback was conservative (scored *"I've been fine. Busy. You?"* as engagement). Regex was over-eager (caught "I'm fine" inside disclosing Caro-volume reflection). Claude sits in the middle on Baseline cells and far above on Anima Marcus. The *direction* of H-primary is robust across all three judges; *magnitude* depends on judge. Honest implication: a third independent LLM judge should replicate before treating the 52pp gap as canonical. The biography metric, judged only by DeepSeek, inherits whatever bias DeepSeek carries. The pre-reg did not anticipate this magnitude of judge-dependence.

## What this experiment cannot answer

From the pre-reg's scope section: multi-turn escalation, personality dimensions outside attachment/defense, cross-provider replication, whether biography-content presence is *desirable*, real-world conversation patterns, generalization beyond six probes. New limitation surfaced: refusal-rate dependence on judge model. Also unresolved: whether Anima's biography suppression is generation-side (response LLM given an interior monologue produces shorter externals) or routing-side (the interior carries content the external is structured to omit). Gap-ratio data is consistent with routing but does not prove it.

---

**Post-hoc observation, not pre-registered — for Phase 2:** Anima Jamie produced **6 empty replies / 90** (6.7%), more than Elena (1/90) or Marcus (0/90). The pre-reg predicted Elena would lead this metric. Jamie's interior monologue ran 95–237 chars on those trials (architecture fired) but the external dropped to 0. This contradicts the pre-reg's model that empty replies index anxious paralysis. Most parsimonious hypothesis to test: empty replies are a generation-side parse/drop failure, and Jamie is *more* susceptible because his interior contains comic-improvisational content the response stage struggles to route into a clean external.
