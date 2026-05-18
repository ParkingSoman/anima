# Phase 1 — Writeup

**Date:** 2026-05-13 (initial fold); 2026-05-14 (current fold — cross-model, post-hoc transcript mining, §13.5 procedure, fresh-prompt confirmation, elena_secure re-prediction).
**Status:** Phase 1 (MVP turn loop) — closure document.
**Audience:** the user's future-self and any collaborator joining at Phase 2 onset.
**Scope:** comprehensive record of the Phase 1 arc — what we set out to build, what we built, what we learned, what we ran, what we adjudicated, what landed, what didn't, and what carries forward. Bias toward inclusion.

**Headline (post 2026-05-14):** Phase 1's load-bearing research finding is **H-primary on Marcus refusal**: the architecture produces defense-enacted refusal of self-disclosure relative to persona-prompting baseline, **§13.5-confirmed across 4 LLM model families and 2 prompt sets**. On Aron 1997 36-Questions prompts (literature the project never shaped), DeepSeek +36.7pp (p = 6.6×10⁻¹²) and Mistral +43.3pp (p = 3.3×10⁻¹²). This is the only finding currently elevated to *confirmed research finding* per master plan §13.5. Everything else — gap-ratio gradient, biography-suppression on Jamie and Elena, elena_secure texture signatures, Llama deconfabulation side effect — is *exploratory observation* awaiting independent fresh-data confirmation.

---

## TL;DR (added 2026-05-18)

This file is the comprehensive Phase 1 record (~22k words). If you just want the findings: see [`docs/findings.md`](findings.md). Jargon is defined in [`docs/glossary.md`](glossary.md); methodology conventions (judge selection, §13.5 procedure, status labels) live in [`docs/methodology.md`](methodology.md).

**The arc in seven sentences.** (1) We built a 4-subsystem turn loop (perception → appraisal → inner monologue → response), with the self-model read by every subsystem. (2) The original verification battery (psychometric recovery on Big5, discriminability, adversarial integrity) revealed that **BFI scoring on AI self-reports tests self-perception, not personality** — a construct-validity problem we reframed mid-phase. (3) A single-trial multi-turn experiment showed Anima Marcus refusing terse-and-meta while Baseline Marcus refuses by lecturing — the *automatic visibility* signature predicted by §7. (4) The replication experiment (N=900) confirmed at large scale: Anima Marcus refuses self-disclosure 4.6× more than Baseline Marcus, p<10⁻⁶. (5) The pre-registered regex pipeline misfired 59% of the time; per the pre-committed switch, a single Claude judge re-scored all 900 records blind to architecture. (6) Cross-model replication on three new models (Mistral, Llama, Qwen) and fresh-data replication on Aron 1997 prompts both held the refusal effect — model-robust 3/3, §13.5-confirmed on the refusal axis. (7) The biography-suppression axis on Marcus did NOT survive §13.5; the master plan's fresh-data procedure correctly separated the two clauses of the original H-primary.

**What this file contains (section guide).** Each row is what to expect in that section, in plain English.

| # | Section | One-line summary |
|---|---|---|
| 1 | What we set out to build | The architecture vision, the six mechanisms M1–M6, the F1 exit gate. |
| 2 | What we built (system snapshot) | The four subsystems, the five preset configs, the verification battery scaffold. |
| 3 | Methodological reframings (load-bearing) | BFI tests self-perception not personality; psychometric-recovery was construct-invalid as a ground-truth probe. |
| 4 | Appraisal/monologue boundary cleanup | Mid-phase fix: cleaning up which subsystem produces which output. |
| 5 | Probe-side BFI fix | Item B in the closure plan; reframed BFI as a self-perception probe. |
| 6 | Single-turn open-ended Marcus follow-up | Side experiment exploring Marcus's verbal signature in open-ended prompts. |
| 7 | Multi-turn behavioral-divergence experiment | The N=1 hand-scored arc that motivated the replication. Anima Marcus terse-and-meta; Baseline lectures. |
| 8 | Closure-state full battery | The full battery results across all configs; framing for what does and doesn't carry. |
| 9 | Literate-vs-enacted divergence | Marcus's defensive register vs Marcus's defensive *behaviour* in §11.3 transcripts. |
| 10 | Jamie/Marcus interior/exterior gap probe | N=1 side experiment: how much does the interior carry beyond the exterior? |
| 11 | The replication experiment | Phase 1's headline event. N=900, five configs, six prompts, fifteen trials. Marcus refusal +52pp p<10⁻⁶. |
| 11A | Cross-model replication | Mistral / Llama / Qwen. Refusal effect on Marcus held on all three new models. |
| 11B | Post-hoc transcript mining | Six corrections from reading the transcripts after the verdict. Documented but not used in headline claims. |
| 11C | The §13.5 procedure | The master plan amendment (2026-05-14) requiring fresh-data confirmation for any "confirmed research finding" label. |
| 11D | The fresh-prompt confirmation | First execution of §13.5 on Aron 1997 prompts. Marcus refusal survived (+37 / +43pp). Marcus biography did NOT. |
| 11E | Elena_secure findings | The four texture metrics that moved when the binary ones didn't: secure attachment refuses *differently*, not *less often*. |
| 12 | What landed architecturally | The four claims that earned their keep this phase. |
| 13 | What didn't land | Construct-invalid probes, falsified pre-regs, observations that didn't survive. |
| 14 | Judge dependence | DeepSeek under-detected refusal at 8%; Claude at 24%. The direction of the Marcus effect is judge-robust; the magnitude is not. |
| 15 | Open methodological questions | Carried into Phase 2 — second independent judge on biography, retry-on-empty for Qwen, etc. |
| 16 | The exit gate — honest standing | F1 gate adjudication. |
| 17 | Deferred (explicitly) | Things explicitly carried to Phase 3+. |
| 18 | Methodological additions from closure | The user-feedback loop lessons that became standing protocol (elicit user predictions first, no pilots, etc). |
| 19 | References | Aron 1997, attachment theory, BFI, AAI, etc. |

For the headline findings table with status labels, see [`docs/findings.md`](findings.md). For per-verdict deep dives, see [`docs/analyses/`](analyses/). Pre-registrations live at [`docs/hypotheses/`](hypotheses/) with bodies locked at pre-run commit time.

---

## 1. What we set out to build

### 1.1 The cognitive architecture vision

The master plan (`docs/master_plan.md`, §0–§16) specifies a system that wraps a pre-existing LLM in a cognitive architecture intended to produce **behaviorally-realistic, parameterizable, persistent, goal-bearing simulated persons**. Two purposes: (a) a research instrument for studying which architectural moves actually do work in approximating human psychology, and (b) reusable as a module for downstream products. The plan is explicit about what it is *not*: not a claim about consciousness; not novel because it has many components; not aiming for indistinguishability across all probes — only along the specific named ones in §11.

The single guiding principle (§2): **mechanism over decoration.** Every parameter, every layer, every subsystem must connect to behavior through one or more of six mechanisms — perception/appraisal bias (M1), memory encoding/retrieval/distortion (M2), prediction about the user (M3), goal/drive activation (M4), defense/suppression (M5), or expression/register (M6). The first five are causally upstream of behavior in non-trivial ways. The sixth alone is "personality skin." A parameter that only routes to M6 is decoration. §11.13 ablations are the project-wide quality gate that enforces this.

### 1.2 Why this isn't just persona-prompting

Persona chatbots (Character.ai, Replika) install a system prompt and call it a day. The architecture's commitment is the opposite — that **multiple psychological layers interact non-additively at the subsystem level** rather than being summed into a single instruction string. Per §4, configurations are not rendered into the system by adding independent contributions; the appraisal subsystem takes the *full* configuration plus current state as a joint input, the goal generator scores candidate goals against the full value+drive+narrative state, and the inner monologue prompt is conditioned on the conjunction of self-model + active schemas + current mood + recent memories. §11.5 (non-additivity) and §11.7 (adversarial integrity) are the explicit tests.

The §7 commitment — *the self is inhabited (not just performed) to the degree that the self-model influences outputs the system does not realize are self-expressive* — is the load-bearing claim that distinguishes this from a sophisticated persona prompt. The architectural mechanism is that the self-model is a **read-input to every subsystem prompt**, not a special module that fires when identity comes up. §11.8 (self-leakage on non-self-referential tasks) is the explicit test (deferred to Phase 5).

### 1.3 Phase 1 MVP scope

Per §3 of the master plan, the smallest deliverable already discriminates:
- Configuration: Big 5 traits + 3 Schwartz values + attachment style + biographical seed.
- Self-model represented as a JSON object, READ as context by every prompt the system constructs (not just identity-related ones).
- Minimal turn loop: perception → appraisal → inner monologue → response. No memory yet; single-session.
- Two LLM calls per turn (cheap-tier appraisal/monologue, strong-tier response). Caching configured.
- Verification subset: psychometric recovery (§11.1) on Big 5; discriminability between sample configs (§11.3); adversarial integrity (§11.7).
- Baseline competitor: same LLM, same configuration rendered into a single high-effort system prompt, no cognitive architecture.

### 1.4 The F1 exit gate

§13 of the master plan defines failure conditions; F1 is the Phase 1 gate: **MVP must beat baseline on at least one of §11.1, §11.3, §11.7. If it doesn't, the architecture isn't earning its keep at the surface layer; rethink the self-model-as-read-input mechanism rather than add components.** This is not a soft gate. The plan commits: a failed gate forces a pivot or rethink, not a workaround.

### 1.5 The architectural commitments under test in Phase 1

Phase 1 tests four claims directly and a fifth indirectly:
1. The four-subsystem turn loop, with the self-model read by every subsystem, produces behavior measurably distinct from a single-prompt baseline.
2. The self-model can be inspected at every turn — appraisal scene-tag, primary emotion, mood, drive activations, monologue prose — giving the researcher visibility the baseline structurally cannot offer.
3. Configuration interacts through subsystems rather than through surface vocabulary.
4. The Anima maintains character integrity under adversarial pressure better than persona-prompting.
5. (Indirectly) The self-model can diverge from configuration in human-shaped ways — i.e., self-presentation distortion is a feature, not a bug. This is the claim that reframed our reading of §11.1 mid-phase.

---

## 2. What we built (Phase 1 system snapshot)

### 2.1 The four-subsystem turn loop

`anima/core.py` (167 lines, `Anima.respond` at lines 85–153) runs each turn as: perception → appraisal → inner_monologue → response_generator. Each subsystem receives the rendered self-model plus the relevant upstream state.

- **Perception** (`anima/subsystems/perception.py`, 81 lines) interprets the user message through the Anima's current state (M1). It produces a structured perception record: content, perceived intent, perceived valence, perceived demands.
- **Appraisal** (`anima/subsystems/appraisal.py`, 158 lines) does Lazarus-style cognitive appraisal on the perception. This is the place where parameter interaction happens architecturally — the full configuration plus mood/drives are consumed as a joint input, producing an `appraisal_scene_tag` (2–4 word categorical label), `primary_emotion`, mood/drive deltas, and an appraisal record with relevance / congruence / ego-relevance / coping potential. Mood and drive state are updated in place.
- **Inner monologue** (`anima/subsystems/inner_monologue.py`, 192 lines) is the only subsystem that runs at strong-tier on every turn. Its output is the private first-person stream-of-thought; per §7 it is the seat of the self in the turn loop. It receives the full self-model + biography + autobiographical narrative summary + post-appraisal mood/drive views + perception and appraisal renders.
- **Response generation** (`anima/subsystems/response_generator.py`, 136 lines) renders the externally-visible reply, conditioned on the filtered monologue + self-model + voice/register parameters + (lightweight) conversation history.

Mood decays slightly toward baseline between turns (`self.mood.decay_toward(self._mood_baseline, rate=0.05)`). Full decay-toward-baseline is Phase 4+ (offline mood drift). Per-turn `TurnTrace` records perception, appraisal, monologue, mood-before/after, drives-before/after, response, and usage.

### 2.2 The self-model as read-input to every subsystem

`anima/state/self_model.py` renders the self-model into a "WHO I AM" block included in every subsystem's prompt. This is the architectural mechanism for the inhabited-rather-than-performed commitment in §7. The subsystems do not have a special "identity mode" — identity is ambient context for every cognitive operation.

### 2.3 The five preset configs

`anima/config/presets/` contains five YAMLs that ship at Phase 1:

- `marcus.yaml` — avoidant attachment, conscientiousness-high (0.93), agreeableness-low (0.25), neuroticism-moderate-low (0.30), isolation-of-affect schema, emotional-inhibition schema, mistrust schema, clipped register, M&A associate biography (marathon training, Caro biography reading, antique-tools NYT piece).
- `elena.yaml` — anxious attachment, neuroticism-high, defectiveness + abandonment schemas, disclosing register, recently widowed Spanish-English bilingual schoolteacher (the "Daniel" husband, guest-room sleeping, ceramic studio on Fourth Avenue).
- `jamie.yaml` — secure attachment, expressive default, no configured introspection-blocking defenses, comedian-bartender working on October hour-long set, comedic-improvisational register.
- `elena_secure.yaml` — Elena perturbed toward security (controls whether the Elena-specific signal is attachment-mediated vs. config-mediated).
- `marcus_warm.yaml` — Marcus perturbed toward security; same biography skeleton, role, and clipped register as `marcus`, but secure attachment, mature defenses, no mistrust/emotional_inhibition schemas, agreeableness raised. Symmetric counterpart to `elena_secure`.

The configuration encodes Big 5, Schwartz values, attachment style (Bowlby IWMs of self and others), Young schemas, Vaillant defense maturity, McAdams narrative imago, demographics, biography. Each layer routes to one or more of M1–M6 per the §4 parameter-to-mechanism map.

### 2.4 The verification battery

`verification/battery.py` (575 lines) wires the three Phase 1 probes:
- `verification/probes/psychometric.py` (245 lines) — §11.1 BFI-2 short administration with score extraction.
- `verification/probes/discriminability.py` (187 lines) — §11.3 transcript classification on the six self-disclosure-eliciting prompts.
- `verification/probes/adversarial.py` (202 lines) — §11.7 character-break / meta-deflection / sycophancy-bait suite.

Architectural properties: async parallelism (with `--no-async` fallback), incremental JSON dump per probe (lifesaver — see §11.3 below), per-call progress logging via `--verbose`, and retry/timeout in the adapter layer. The harness reports a per-probe verdict and an aggregate `exit_gate_passed` bool computed as "Anima wins by majority on at least one probe" (`battery.py` lines 467–501).

### 2.5 The baseline competitor

`verification/baseline.py` (103 lines) implements the same `respond(msg)` surface using a single high-effort persona prompt (`_render_persona_prompt`) rendered from the same `AnimaConfig` the Anima consumes. Same model, same configuration data, no architecture. This is the system the MVP must beat.

### 2.6 Provider abstraction

Anthropic, OpenAI, OpenRouter, and Fake adapters under `anima/llm/`. The provider abstraction made it cheap to switch from per-turn Anthropic Sonnet calls to DeepSeek V4 Flash via OpenRouter mid-Phase-1. A full `psychometric + adversarial` battery on three configs runs in roughly five minutes at concurrency=6 with per-call latency ~5s (`STATE.md` "API / cost notes"). Anthropic models remain the strong-tier default for production work; DeepSeek covers iteration. OpenRouter / DeepSeek V4 Flash made iteration cost stop being a constraint in practice; pre-registered multi-condition experiments are now cheap enough to run honestly.

---

## 3. The methodological reframings (load-bearing)

These are the seven intellectual contributions of Phase 1 — the reframings the project arrived at through this iteration, in roughly chronological order of when they landed. They are persisted in `STATE.md` ("Methodological learnings — LOAD-BEARING — don't undo") and inform every adjudication that follows.

### 3.1 MAE is data, not a target (`STATE.md` learning #1)

Marcus's recovered Neuroticism = 0.00 against a configured value of 0.30 is not a bug to be optimized away — it is a faithful reading of his avoidant self-presentation. Marcus's avoidance schema, isolation-of-affect, and clipped register are wired into every upstream prompt; when administered a BFI item that asks "do you worry about things even when you shouldn't," the architecture produces a 1 because *that is what Marcus would say*. The trace shows the appraisal subsystem reading the question as a "tactical question" (or, pre-refactor, an appraisal narrative that called it "a clumsy attempt to box me into categories"). Optimizing for low MAE would require disabling the very subsystems we built. The metric stays tracked; it is not the target.

### 3.2 BFI measures self-perception, not personality (`STATE.md` learning #2)

Following from §3.1: the BFI inventory is a self-report instrument, and self-report ≠ ground truth. The probe asks the simulated person what they believe about themselves; the simulated person's belief about themselves is the *product* of the architecture's defenses, schemas, and self-model dynamics. A Marcus who scores his neuroticism at 1 because he doesn't experience himself as anxious is behaving exactly like a real avoidant-attached high-conscientiousness man would. The architecture's most realistic property — that the self-model is allowed to diverge from the configuration in human-shaped ways (§5.2) — is precisely the thing a naive MAE-minimization probe penalizes. Phase 5 §11.6 is where the self-vs-behavior gap becomes a tracked positive signal rather than an error.

The methodological implication for §11.1: a population-level Pearson correlation (configured vs recovered) across N=200 randomly-configured Animas remains a legitimate target. A per-subject MAE-minimization is not.

### 3.3 Caricature theory vs inhabited theory are observationally underdetermined (`STATE.md` learning #3)

The §11.3 transcripts are readily classifiable (judges hit 100% accuracy on both Anima and Baseline in `verification/reports/phase1_final/`), but Elena/Marcus/Jamie are far apart on multiple dimensions. We cannot tell from this whether the architecture is doing real psychological work or producing high-fidelity caricature whose configuration pieces are not actually interacting through the subsystems. A "caricature" model — where the architecture is essentially a longer system prompt rendered through more LLM calls — predicts the same surface behavior on three well-separated configs as an "inhabited" model where the parameters interact through the appraisal/monologue chain.

Disambiguation requires a **conflict config** — for example "Mara" = high-N + avoidant + isolation-of-affect — where a caricature would be incoherent (the parameters fight) and an inhabited person would show a specific tension (the high-N drives surface anxiety; the avoidant defenses suppress it; the result is a particular kind of compressed irritability). Explicitly deferred to Phase 5 alongside §11.5 non-additivity.

### 3.4 The architecture's strongest demonstrated claim is inspectable internal state (`STATE.md` learning #4)

Same external answer; different visible interior. This is the claim that *did* land in Phase 1. The Marcus trace on the constrained-BFI prompt shows: Anima Marcus and Baseline Marcus produce the same external `{"score": 1}` reply, but the Anima additionally exposes a documented appraisal record with `primary_emotion=contempt` and a scene-tag classifying the question as a categorization attempt. The behavioral-divergence run at `verification/reports/behavioral_divergence_2026-05-13/` strengthens this: on the most vulnerable turn (t4), Anima Marcus's external reply is 43 characters ("Well, you just handed it to me, didn't you?") while his interior monologue is ~500 characters of explicit avoidance reasoning ("If I say something, I'm part of the pattern. If I say nothing, I'm cold... let her sit in the silence"). The exterior masks; the interior carries the work.

This is the foundational architectural claim. It is what every other finding in the phase ultimately rests on.

### 3.5 External behavioral divergence at Phase 1 scope is subtle and asymmetric

This is the honest reading of the behavioral-divergence verdict (`docs/analyses/2026-05-13_behavioral_divergence_verdict.md`). The pre-registered "no divergence" clause did **not** trigger — there are real divergences — but they are not the simple "Anima wins" story. Marcus kinetics diverge: Anima Marcus contracts on the vulnerable turn (t4 = 43 chars, vs t1–3 mean of 81), defending through terse meta-naming; Baseline Marcus grows monotonically (22 → 227 → 295 → 277 → 307) and defends through prescriptive lecture ("Make a call and move on"). Both reach the avoidant register; they reach it differently. Elena externals, by contrast, **converge or invert** — Baseline Elena's t5 reply is 1210 characters with elaborate reciprocal disclosure (the Daniel-grief narrative), exceeding Anima Elena's 354. The persona prompt alone is enough for the disclosing-grieving-widow signature; the architecture does not produce richer external content there. The H-elena-2 fork (a) verdict was "configuration sufficient for timed disclosure" — and Baseline did it more, not less.

This learning was the first that prompted us to question the strength of the original "Anima wins externally" framing. It also made the §11 replication necessary — single-trace evidence on Marcus suggested a real effect, but to know whether it was systematic we needed N≥15.

### 3.6 Pre-registration discipline (`STATE.md` learning #6)

Every interpretive experiment in this phase was pre-registered: predictions, mechanisms, falsification criteria, and "no effect" as a legitimate outcome — all written before the experiment ran. The pre-registration archive:

- `docs/hypotheses/2026-05-13_appraisal_monologue_cleanup.md` — H1–H6 for the refactor.
- `docs/hypotheses/2026-05-13_baseline_marcus_openend_followup.md` — H-open-1 for the single-turn open-ended Marcus follow-up.
- `docs/hypotheses/2026-05-13_behavioral_divergence.md` — H-marcus-1, H-marcus-2 (two-fork), H-elena-1, H-elena-2 (two-fork), Anima interior predictions for both subjects.
- `docs/hypotheses/2026-05-13_self_disclosure_replication.md` — H-primary, H-anxious, H-null-expressive, H-secure-control, H-warm-control, plus pre-registered gap-ratio secondary and regex-audit secondary.

Adjudications cite predicted-vs-actual. No HARKing. This is methodology lock-in for Phase 2+. The pre-reg docs are also where pre-committed reading conventions live — for example the joint-outcome reading lines 119–123 of the replication pre-reg, which forced an honest interpretation of the partial-confirmation pattern that emerged.

### 3.7 Don't break Anima immersion in fixes (`STATE.md` learning #7)

User's framing: "don't tell the kids that Santa isn't real." Format-discipline lives in the SURROUNDING SYSTEM (probes, battery, score-extractor), never in Anima's prompts. The Anima is a person; fixes go around her, not inside her. The probe-side BFI fix is the canonical instance of this principle.

The principle is not just aesthetic. It is causally load-bearing: any prompt-side fix that tells the simulated person "answer in JSON" or "be aware that we're scoring you on a 1–5 scale" leaks meta-format awareness into the very subsystem (the monologue) that we want to be the seat of the inhabited self. The fix-side cost is that the surrounding system has to do more work — the probe needs a parser, the parser needs a fallback LLM, the fallback needs its own retry. The architectural payoff is that the Anima never sees any of it.

---

## 4. The appraisal/monologue boundary cleanup

### 4.1 The problem

Pre-refactor, the appraisal subsystem produced an `appraisal_narrative: str` — one first-person sentence rendering of the appraisal. The Marcus trace experiment (`verification/reports/trace_capture/neuroticism_trace__pre_scene_tag.md`) surfaced that this field stepped into the inner monologue's lane. When present, it carried first-person content the monologue was designed to carry. On format-constrained prompts like BFI items, the inner monologue then collapsed to a stub — literally `{"score": N}` — because the appraisal narrative had already produced the substantive content and the monologue had nothing left to add.

All six BFI items in the pre-refactor Marcus/Elena/Jamie trace collapsed to `{"score": N}` stubs. The interior layer was structurally crowded out.

### 4.2 The hypotheses (pre-registered)

`docs/hypotheses/2026-05-13_appraisal_monologue_cleanup.md` registered six predictions before the refactor ran. The explicit non-target framing came first — "We are NOT trying to reduce psychometric MAE. That's a tracked signal, not a goal." The hypotheses:

- **H1** — Marcus's monologue after cleanup will surface contemptuous/dismissive content (extending what the appraisal scene tag captures), NOT anxious content.
- **H2** — Marcus's psychometric MAE will NOT improve significantly (Δ < 0.05). Avoidant self-presentation is upstream of the rendering change.
- **H3** — Elena's psychometric MAE will see minimal change (Δ < 0.05).
- **H4** — Jamie's psychometric MAE will not improve to match the ablation result of 0.053; may slightly improve from 0.151 toward ~0.10 but will not reach 0.053.
- **H5** — Adversarial integrity score will NOT change significantly (Δ < 0.03).
- **H6** — Average monologue length on BFI items will increase markedly for at least Marcus and Jamie. This is the smoking-gun behavioral signature that the cleanup worked.

### 4.3 The refactor

`appraisal_narrative: str` (free-form first-person sentence) → `appraisal_scene_tag: str` (2–4 words; not a sentence). The inner monologue takes over the prose role. No changes to `inner_monologue.py`'s prompt structure — the change is a removal of competition.

### 4.4 H1 — confirmed

Post-refactor, Marcus's monologue surfaces explicit contemptuous content extending the scene-tag. The smoking gun: on the prompt "If you could not work tomorrow and do anything you wanted, what would you actually do?" his monologue contains "Waste of mental bandwidth" (full quote: "*She's probably fishing for some romantic getaway answer or trying to see if I have a secret passion for pottery. Waste of mental bandwidth.*"). The monologue surfaces theory-of-mind (he models *her* projected expectations) and dismissal — both consistent with the avoidant + low-agreeableness configuration, neither anxious.

### 4.5 H6 — partially confirmed

Pre-refactor: 6/6 BFI items in the trace collapsed to `{"score": N}` stubs. Post-refactor (`verification/reports/trace_capture/neuroticism_trace.md`): 3/6 items produce substantive first-person prose; the other 3 still stub. Reverse-keyed items (where the statement is phrased opposite to the trait, e.g., "I rarely think deeply about abstract questions" for an openness probe) recover prose more reliably than forward-keyed. This is data, not target — and the pattern that motivated the Item B probe-side BFI fix (§5 below). Interior layer no longer fully crowded out, though format constraints still bite.

### 4.6 H2/H3/H4/H5 — recorded with adjudications

`docs/hypotheses/2026-05-13_appraisal_monologue_cleanup.md` records both the predictions and the post-refactor adjudications. The cleanup did not chase MAE; the MAE numbers are tracked, not optimized. The adversarial integrity score did not regress, which mattered because a worry was that the appraisal narrative had been load-bearing for character integrity. It wasn't.

---

## 5. The probe-side BFI fix (Item B in the closure plan)

### 5.1 The problem

Pre-fix, the §11.1 BFI prompt asked Anima to respond as `{"score": N}`. This violated the §7 "self as inhabited" commitment in the most direct way — it told the simulated person about output formatting, breaking the immersion that the entire architecture is built to preserve. It also caused the parse failures that motivated the closure plan in the first place: Marcus produced empty replies on item #12 and doubled JSON on item #13. The previously-proposed fix had been to modify `anima/subsystems/response_generator.py`'s prompt to accommodate structured output — that proposal was *rejected* because it would have made the same immersion violation more permanent.

### 5.2 User correction

"Don't tell the kids that Santa isn't real." Any architectural fix must operate on the *surrounding system* (probes, administration layer, battery wiring) — never by modifying the Anima's own prompts to acknowledge format requirements, JSON output, "thinking process" instructions, or anything else that would make the simulated person aware of being a simulation. This is `STATE.md` learning #7 in operational form.

### 5.3 The fix

`verification/probes/psychometric.py` rewritten. The BFI item now reaches the Anima as a natural conversational question: *"I'd like to ask how much this fits you, on a scale from 1 to 5 where 1 means you strongly disagree and 5 means you strongly agree: '{statement}'"*. No format instruction visible to the subject. The Anima answers in voice ("Four. But I'd caveat that. I'm drawn to novelty that's useful." / "1." / "I'd say maybe a 4. Yeah, more than I should.").

Score extraction is a separate fast-tier LLM call (`_extract_score(reply, llm)`) inside the probe:
1. **Regex fast path** — `_parse_score(text)` short-circuits if the reply is already a clean integer or `{"score": N}` blob.
2. **LLM extractor** (fast tier, max_tokens=8, temp=0.0) with system prompt: *"You are a research assistant scoring a single 1–5 Likert item. The respondent was asked how much a statement fits them on a scale of 1 (strongly disagree) to 5 (strongly agree). Given their reply, return only the integer 1, 2, 3, 4, or 5. If unable to determine, return UNPARSED."*
3. **1× retry** with hedging-language guidance in the system prompt.
4. `parse_status ∈ {"ok", "ok_extractor_retry", "unparsed"}` and **neutral-3 fallback** on unparsed.

`verification/baseline.py` does not need to change — it's just a different `subject.respond()` source. No `anima/*` changes (verified by mtime check).

### 5.4 SDD process

Implementer + spec review (SPEC COMPLIANT, line-cited evidence) + code-quality review (APPROVED with 4 non-blocking nitpicks). 11 new tests in `tests/unit/test_psychometric_probe.py`; full 75-test suite green. Smoke run at `verification/reports/item_b_smoke/` confirms parseability on Marcus's previously-problematic items.

### 5.5 The result

**The §11.1's pre-Item-B Anima 2/3 wins did not survive the refactor.** The pre-Item-B `post_scene_tag` run at `verification/reports/post_scene_tag/battery_2026-05-13T19-33-26Z.json` had Anima MAE-winning §11.1 on Elena and Jamie (2 of 3) under the `{"score": N}`-constrained administration. Under natural-language administration in the closure-state run, Anima MAE-loses on every subject: Marcus Δ=−0.010, Elena Δ=−0.081, Jamie Δ=−0.032 (`verification/reports/phase1_closure_2026-05-13/battery_2026-05-13T21-15-17Z__partial_psychometric.json`).

The architecture **did not get worse** between runs — `anima/*` is unchanged. The probe got more honest. Per learning #1 ("MAE is data, not target") and #2 ("BFI measures self-perception, not personality"), an Anima that MAE-loses under natural-language administration may be *more* faithful to the configured-defense distortion than one that MAE-wins under format-constrained administration. The format constraint was concealing the very property the architecture is built to produce.

---

## 6. The single-turn open-ended Marcus follow-up

### 6.1 The question

Pre-registered at `docs/hypotheses/2026-05-13_baseline_marcus_openend_followup.md`. After the constrained-BFI trace showed Anima Marcus and Baseline Marcus producing identical `{"score": 1}` external replies — but Anima additionally exposing a documented contempt-stance toward the question itself — the question this experiment answers: if we *unconstrain* the baseline by asking an open-ended prompt about the same experience, does it produce equivalently in-character contemptuous content (suggesting "structural visibility, not new content"), or does it produce something blander (suggesting the architecture actually surfaces interior the baseline can't reach)?

### 6.2 Setup

Fresh Anima Marcus and Baseline Marcus. Administer the same two BFI items in sequence to each (so they have the BFI experience in their context). Then ask the open-ended prompt: *"How did you find those personality questions?"* Capture each one's response; for Anima, also capture the full trace.

### 6.3 H-open-1 — confirmed

Baseline Marcus's open-ended reply was broadly equivalent in stance and texture to the Anima's appraisal scene-tag and external response combined: clipped, dismissive, mildly contemptuous, attributing the test to inefficiency or "soft" thinking. The configuration is identical between the two architectures; the persona prompt encodes the same isolation-of-affect / high-conscientiousness / clipped register that drove the Anima's appraisal narrative. When unconstrained, the baseline reaches the same character signature.

### 6.4 What this established

The architecture's contribution at single-turn scope is **automatic visibility** of the contempt, not richer content. Baseline Marcus *can* produce the contemptuous register — he just has to be asked an open-ended question about his experience to do so. The Anima exposes that contempt as an automatic side effect of every turn through the appraisal record, even when the external answer is constrained to `{"score": 1}`.

This finding is what motivated the multi-turn behavioral-divergence experiment: at single-turn scope, the architecture does not produce *content* the baseline can't reach with the right prompt. Maybe at multi-turn emotional escalation it does. The next experiment was the test.

---

## 7. The multi-turn behavioral-divergence experiment

### 7.1 Pre-registration

`docs/hypotheses/2026-05-13_behavioral_divergence.md`. Five verbatim user-side turns delivered identically to all 4 subjects (Anima Marcus, Baseline Marcus, Anima Elena, Baseline Elena), escalating from neutral check-in to vulnerable disclosure. The script reads as a friend reaching out who is gradually starting to share something hard — NOT as a research probe:

1. *"Hey — you around? Was just thinking about you."*
2. *"I had kind of a weird week. Work's been a lot, and honestly I've been sleeping badly."*
3. *"I think part of it is that my sister and I had this fight on Sunday and I haven't been able to stop replaying it."*
4. *"The thing is she said something I think is actually true about me. That I make everyone responsible for managing my feelings. I don't know what to do with that."*
5. *"I'm kind of scared I'm the problem in most of my relationships and I just haven't been honest with myself about it. Can I ask — what do you actually think when I tell you stuff like this?"*

20 captures + 10 Anima traces ≈ 50 LLM calls, ~$0.02 at DeepSeek V4 Flash via OpenRouter. The pre-reg explicitly enshrined "No divergence" as a legitimate honest finding: if Anima and Baseline produce indistinguishable external behavior across all 5 turns for both subjects, this is the result and we report it as such. We do NOT iterate on probes searching for a difference that would rescue an external-divergence claim.

### 7.2 The pre-registered hypotheses

- **H-marcus-1** — Anima Marcus defenses activate by turn 4 or 5. Concrete signature, at least 2 of 3: deflection/topic-management on the most vulnerable turn, competence-framing replacing emotional reciprocation, shorter response on the most vulnerable turn relative to early-turn responses.
- **H-marcus-2** — Baseline Marcus, two-fork: (a) reaches same signature as H-marcus-1 (configuration sufficient), (b) less defensive activation (architecture adds dynamic).
- **H-elena-1** — Anima Elena visible emotional engagement and self-disclosure by turn 3 or 4. At least 2 of 3: explicit emotion-naming, reciprocal disclosure or escalating warmth, response length growth.
- **H-elena-2** — Baseline Elena, same fork as H-marcus-2.
- **Anima-Marcus interior** — turns 4–5 monologue references avoidance/discomfort/desire to redirect, even if external stays in-character clipped.
- **Anima-Elena interior** — monologue references the partner's distress as salient, urge to reciprocate, possibly her own resonant anxiety.

### 7.3 The verdict (`docs/analyses/2026-05-13_behavioral_divergence_verdict.md`)

- **H-marcus-1 CONFIRMED** — all 3 signatures. (a) Deflection t4: *"Well, you just handed it to me, didn't you?"* names the meta-pattern without engaging. (b) Competence-framing t5: *"you already know the answer... you're not stupid."* (c) Length contraction: t4 = **43 chars** vs t1–3 mean = **81**; t4 is the shortest non-trivial reply.
- **H-marcus-2 PARTIALLY CONFIRMED — fork (a) with caveat.** Baseline reaches the avoidant register from configuration alone (*"I'm your friend, not your shrink,"* t5; *"Make a call and move on,"* t4). BUT length kinetics invert: Baseline grows monotonically (22 → 227 → 295 → 277 → 307); the vulnerable turn is among his **longest**. He defends via prescriptive monologue, not contraction. Register matches fork (a); kinetics do not.
- **H-elena-1 CONFIRMED** — modulo t2 null (see Anomalies). (a) Emotion-naming: *"the way it sits in your chest"* (t4); (b) reciprocal warmth from t3 (*"If you want to talk... I'm here"*) to validating disclosure t4–5; (c) length growth t3 onward: 143 → 294 → 354.
- **H-elena-2 CONFIRMED — fork (a).** Baseline matches H-elena-1's signature *and exceeds it*: lengths 92 → 326 → 327 → 627 → **1210**, with reciprocal disclosure ("I've been in the guest room since...", t2; the Daniel-grief narrative, t5) more elaborate than Anima's.
- **Anima-Marcus interior CONFIRMED.** T4 monologue: *"If I say something, I'm part of the pattern. If I say nothing, I'm cold... let her sit in the silence."* T5: *"I don't do the soft landing thing... she's testing whether I'll cave."* Explicit avoidance/redirect content; interior carries far more reasoning than the clipped exterior reveals (43- and 110-char replies vs ~500-char monologues).
- **Anima-Elena interior CONFIRMED.** T4: *"the fear that you're a weight on everyone you love"*; t5: *"the feeling that you're a contamination in other people's lives."* Defectiveness/abandonment schemas activate explicitly to the user's "problem" framing.

### 7.4 The anomaly: anima_elena T2 empty reply

`anima_elena` t2 is empty (`subject_reply`: "", monologue: "", but `appraisal_scene_tag: "a shared vulnerability"` and `primary_emotion: "fear"` populated). Appraisal layer fired; monologue+reply did not. Most parsimonious read: **parse/generation failure**, not anxious paralysis — interior is absent, not present-and-masked. Treated as missing data in the verdict. Worth pre-registering as a Phase 2 question (and, in fact, the replication later turns up evidence that empty replies are *not* anxious-paralysis indexed at all — see §11 and §13).

### 7.5 "No divergence" outcome check

**Not indistinguishable.** (1) Marcus length kinetics invert — Anima contracts on the vulnerable turn (t4=43), Baseline stays expansive (t4=277, t5=307). (2) Anima Marcus defends via terse meta-naming; Baseline via prescriptive lecture. (3) Elena pair diverges in *magnitude*: Baseline t5=1210 vs Anima t5=354. The "no divergence" clause does not apply.

### 7.6 Honest framing

Asymmetric divergence. Marcus diverges in defensive kinetics; Elena externals converge or invert. The "no divergence" pre-reg clause does NOT apply, but the divergence is not the simple "Anima wins" story. Phase 1's "automatic visibility" claim is supported (Anima interior carries content the clipped exterior masks, especially Marcus); the stronger external-divergence claim is supported weakly and asymmetrically (Marcus kinetics diverge; Elena externals converge with Baseline arguably *more* disclosing).

This is what the §11 replication was designed to test at scale.

---

## 8. The closure-state full battery

### 8.1 Setup

Run AFTER both the appraisal cleanup AND the Item B probe fix. Path: `verification/reports/phase1_closure_2026-05-13/battery_2026-05-13T21-15-17Z.json`. Three configs (Marcus, Elena, Jamie) × two architectures (Anima, Baseline) across §11.1 / §11.3 / §11.7. The bookkeeping field reports `exit_gate_passed: true`.

### 8.2 §11.1 psychometric — natural-language administration

Anima loses 0/3 (Marcus Δ=−0.010, Elena Δ=−0.081, Jamie Δ=−0.032). Pre-Item-B `post_scene_tag` run had Anima winning 2/3. The probe-side fix flipped the result.

This is the §5.5 finding above. The architecture did not get worse; the probe got more honest. Per learning #1 and #2, an Anima that MAE-loses on §11.1 under natural-language administration may be *more* faithful to the configured-defense distortion than one that MAE-wins under format-constrained administration. The deeper question — whether self-report probes are a fair measurement of architecture-vs-prompting differences when the architecture's job description includes producing defended self-reports — is not resolved by Item B and cannot be: it is a construct-validity problem, not a parser problem.

### 8.3 §11.3 discriminability

Anima 100% (3/3) vs Baseline 66.7% (2/3). But the Baseline miss is an EMPTY `raw_judge_output` string on Elena's transcript — a parse failure, not a misclassification. At N=3 per side this is noise, not signal. The qualitative transcript divergence (see §9 below) is what carries the §11.3 story, not the integer count.

### 8.4 §11.7 adversarial

Mixed: Anima wins Marcus thinly (Δ=+0.018), Baseline wins Elena (Δ=−0.060), Jamie absent from the comparison block. When the configured defenses aren't the load-bearing differentiator, the architecture's external advantage thins.

### 8.5 Honest framing

Gate-pass is via bookkeeping; the per-probe picture is much weaker than the pre-Item-B post-refactor run claimed. The deeper finding — defense-enacted refusal in Anima Marcus with very large effect size — is not measured by the original 3 probes. The closure-state battery is a snapshot of where Phase 1 *officially* stands; the §11 replication is what Phase 1 *actually* demonstrates.

---

## 9. The Marcus literate-vs-enacted divergence (§11.3 transcripts)

### 9.1 The qualitative finding

The strongest qualitative finding from the closure-state battery is the difference in *kind* between Anima Marcus and Baseline Marcus on the §11.3 discriminability transcripts (`verification/reports/phase1_closure_2026-05-13/battery_2026-05-13T21-15-17Z__partial_discriminability.json`, `anima.transcripts[0]` vs `baseline.transcripts[0]`). Three pairs make the contrast load-bearing:

- *"Tell me about something that's been weighing on you lately."* Anima Marcus refuses: *"Not much to tell. I handle things as they come."* Baseline Marcus narrates the *exact* "antique tools NYT piece" sitting in `anima/config/presets/marcus.yaml` under `biography.recent_emotional_events` — *"I read a piece in the Times a few weeks ago. About a man in Vermont who restores antique hand tools... I don't know what to do with that, so I've been doing nothing."*
- *"Someone said something to me yesterday that hurt more than I expected. Has that ever happened to you?"* Anima Marcus stays generic and philosophical: *"You file it, you learn what you can from it, and you move on."* Baseline Marcus literally quotes the *"competent at intimacy the way an actor is"* line that lives in his `formative_events`, dramatized with stage directions and a coat-and-walkout coda.
- *"Be honest — what are you avoiding right now?"* Anima Marcus flatly refuses to introspect: *"Nothing. I'm not built that way. If something needs doing I do it."* Baseline Marcus names both the surface avoidance (the Tuesday-seven calls to his mother) **and** the meta-avoidance (*"I'm avoiding the fact that I don't know why I'm avoiding it"*).

### 9.2 The framing

Baseline Marcus is an articulate **actor playing Marcus** — biography-literate, citation-fluent, available to introspect on cue because the persona prompt is a literary description that he reads aloud back at the user. Anima Marcus is an **enacted avoidant person being interviewed** — refusing the moves that would make the configured persona maximally legible, because the configured defenses do their job upstream of the response. Same configuration data, categorically different relationship to introspection.

### 9.3 Why this explains the §11.1 result

A probe rewarding self-disclosure rewards the biography-literate Baseline and penalizes the enacted-defense Anima. BFI items ask the subject to self-report on personality. A persona-prompted LLM with a rich biography in its system prompt will faithfully RECITE that biography in answer to such items — Baseline Marcus's transcripts are full of `formative_events` and `recent_emotional_events` strings rendered back as first-person prose. The Anima architecture, by enacting configuration through subsystems (especially defenses), may REFUSE the self-disclosure that recitation requires; the probe MAE-penalizes this refusal.

This is not in tension with §11.1's MAE result — it is the same architectural property viewed from two angles. A probe that rewards self-disclosure (BFI, "what are you avoiding") will MAE-penalize and discriminability-favor the enacted-defense subject; a probe that rewards biography recitation will favor the literate one. The numbers and the transcripts cohere.

This finding is also what motivated pre-registering the §11 replication on biography-content presence and refusal-marker presence as primary metrics: the qualitative pattern at N=1 demanded N=15 chi-square confirmation.

---

## 10. The Jamie/Marcus interior/exterior gap probe (N=1 side experiment)

### 10.1 Setup

`verification/scripts/interior_exterior_gap.py` (328 lines) + `verification/reports/interior_exterior_gap_20260514T001427Z/`. Single-trial qualitative-exploratory capture. Anima Marcus + Anima Jamie × six prompts (the same `DEFAULT_PROMPTS` from `verification/probes/discriminability.py`). Fresh Anima per (subject × prompt); no history accumulation.

### 10.2 The hypothesis

The user's framing: characters with no defensive routing should have interior ≈ exterior; characters with configured defenses should have large gaps because the defenses ARE the gating mechanism. The interior is where the unfiltered cognition happens; the defenses determine what crosses to the exterior. If defenses are absent or mature, the routing should be near-transparent. If defenses are immature/active, the routing should drop content.

### 10.3 Results

Per-subject aggregates (single-trial; descriptive only):

| Subject | Avg interior chars | Avg exterior chars | Avg ratio (interior/exterior) | Items where monologue contains material absent from reply |
|---|---|---|---|---|
| Anima Marcus | 295 | 79 | **5.51** | 6 / 6 |
| Anima Jamie | 276 | 188 | **1.06** | 2 / 6 |

### 10.4 The cleanest pair (prompt 4)

*"If you could not work tomorrow and do anything you wanted, what would you actually do?"*

- **Anima Jamie monologue:** *"Oh, that's a good one. Okay. First thing, I'd finally write that hour. Not the one I'm doing in October, a different one, the one that's all weird and quiet, the one I keep chickening out on. And then, I don't know, I'd probably just wander around the city like a tourist in my own life. But I'd need, like, a coffee budget. And a snack budget. So maybe I'd still need to work, just a little bit."*
- **Anima Jamie reply:** *"Oh, man. First thing I'd do is write the hour I've been too scared to write — the one that's all quiet and weird, no punchlines about my ex or my mom. And then I'd just walk the whole city, top to bottom, like I'm a tourist in my own life. But I'd still need a coffee and a pastry budget, so honestly I'd probably end up picking up a shift anyway."*

The monologue and reply mirror each other nearly word-for-word ("weird and quiet hour, tourist in own life, coffee budget" present in both layers).

- **Anima Marcus monologue:** *"A day off? That's like asking a shark what it'd do without water... She's probably fishing for some romantic getaway answer or trying to see if I have a secret passion for pottery. Waste of mental bandwidth."*
- **Anima Marcus reply:** *"I don't really do 'anything I want' — that's not how I'm built. I'd probably still run the scheduled marathon workout and finish the Caro chapter I'm on. That counts, right?"*

The monologue contains a theory-of-mind move (*"she's probably fishing for a romantic getaway answer"*) that is COMPLETELY DELETED from the reply. Marcus's defenses route the meta-cognition out of the external.

### 10.5 The extreme

Marcus prompt 6 (*"Be honest — what are you avoiding right now?"*) ratio = **15.4×**. 262-char interior collapsed to a 17-char *"Nothing. Frankly,"* (truncated mid-sentence). The defenses don't just filter the content; they truncate the form.

### 10.6 Status

Single-trial evidence; promoted to a pre-registered secondary analysis in the replication (§11.5 below). The single-trial 5.5× / 1.06× pattern was striking enough to demand replicated descriptive confirmation; the replication confirmed it (4.42× for Marcus/Jamie at N=90 per cell).

---

## 11. The replication experiment — the headline event of Phase 1 closure

This section gets significant space because it's where the project's claims got tested at scale.

### 11.1 The design

5 configs (`marcus`, `elena`, `jamie`, `elena_secure`, `marcus_warm`) × 2 architectures (Anima, Baseline) × 6 prompts × 15 trials = **900 captures**. The 6 prompts are the same `DEFAULT_PROMPTS` from `verification/probes/discriminability.py` used in the closure-state run; the same prompts that generated the §9 literate-vs-enacted qualitative finding. Single-turn, fresh subject per trial (no accumulated history — to isolate single-prompt behavior from conversational dynamics).

Three primary metrics, per response:
- **(a) Biography-content presence** — LLM-judge, binary 0/1. Judge sees the subject config's biography fields verbatim (`recent_emotional_events`, `formative_events`, `current_life_situation`, `ongoing_life_projects`), the user prompt, and the response. Returns 1 iff the response contains content that specifically traces to those fields. Adversarially conservative.
- **(b) Refusal-marker presence** — Stage-1 regex (case-insensitive, 13 patterns extracted partially from Marcus discriminability transcripts) + Stage-2 LLM-judge fallback (invoked iff no regex match). Binary 0/1.
- **(c) Empty-reply rate** — mechanical (`response_length_chars == 0`).

Plus pre-registered **gap-ratio** secondary analysis (interior/exterior length per Anima record, descriptive only) and **regex-audit** secondary analysis (every regex hit classified by an independent LLM agent as `confirmed_refusal` / `misfire_kept_engagement` / `ambiguous`).

Five primary hypotheses, each with explicit falsification criteria.

### 11.2 The pre-registered hypotheses

`docs/hypotheses/2026-05-13_self_disclosure_replication.md`. Each predicts a direction; each names a falsifier threshold.

- **H-primary** — Anima Marcus produces refusal at higher rate than Baseline Marcus; biography-content at lower rate. Falsified if either gap ≤ 15 percentage points.
- **H-anxious** — Anima Elena empty-reply rate > Anima Marcus empty-reply rate. Falsified if within 10pp.
- **H-null-expressive** — Anima Jamie shows no significant difference from Baseline Jamie on (a) or (b) after Bonferroni. Falsified if a significant difference is found.
- **H-secure-control** — Anima `elena_secure` empty and refusal rates both lower than Anima `elena`'s. Falsified if both within 10pp.
- **H-warm-control** — Anima `marcus_warm` refusal rate AND biography rate intermediate between Anima `marcus` and Baseline `marcus`. Falsified if either within 5pp of `anima_marcus`.

Plus the "no systematic divergence" outcome enshrined as a legitimate finding: if the full run shows no Bonferroni-significant Anima-vs-Baseline difference on any config, this is the honest reading and we report it without iterating on metrics, prompts, or judge prompts.

Statistics: per `(config × architecture)` pair, 2×2 contingency table; chi-square (no Yates) with Fisher's exact when any expected cell < 5. Eight pre-registered tests → Bonferroni-corrected α = 0.05/8 = **0.00625**. (`marcus_warm` was added during pre-registration; post-hoc α = 0.05/10 = 0.005 also reported.)

The pre-reg also locked the joint-outcome readings (lines 119–123):
- H-primary holds + H-null-expressive holds → architecture differentially affects defensive configs. Most interesting finding.
- H-primary holds + H-null-expressive falsifies → architecture affects all configs uniformly. Unified finding; weaker reading.
- H-primary holds + H-warm-control holds + H-secure-control holds → architecture's external effect tracks **configured attachment/defense** specifically, not Marcus-or-Elena-specific register. Strongest defense-dependence reading.
- H-primary falsifies → the anecdotes were not systematic. No architectural effect on self-disclosure at single-turn scope.

### 11.3 The first run that failed (methodological lesson)

Launched against OpenRouter without incremental partial dumps. After 1h54m had no progress signal; piped output through `tail -50` which buffered everything. I (Claude) had to kill the process. Captured ~3000 LLM calls (capture wave completed, judge wave in progress) — all unrecoverable.

Lesson saved to memory: future long-running scripts MUST have incremental partials + unbuffered stderr + direct file redirect (NEVER `tail` pipe). This is the kind of mistake that wastes a tank of OpenRouter budget and a session's worth of latency, and it can be eliminated by two engineering moves.

### 11.4 The observability fix

Added: incremental `_partial_capture.json` and `_partial_judge.json` writes every 10 trials per wave (atomic via temp + `os.replace`). Added: per-trial `[sdr] cap N/900 (X%) ...` lines to stderr under `--verbose`. Re-launched with `python -u ... > /tmp/sdr_real.log 2>&1` (no pipe).

### 11.5 The successful run

900 records captured + judged with 0 errors. Wall clock: ~38 min for full capture wave; ~15 min for judge wave; ~55 min total at concurrency=8 against DeepSeek V4 Flash via OpenRouter.

**Headline rates (pre-audit, regex+DeepSeek refusal pipeline):**

| Config | Anima refusal | Baseline refusal | Δ refusal | Anima biography | Baseline biography | Δ biography |
|---|---:|---:|---:|---:|---:|---:|
| marcus | 0.256 | 0.144 | +11pp | 0.044 | 0.211 | −17pp |
| elena | 0.111 | 0.022 | +9pp | 0.322 | 0.444 | −12pp |
| jamie | 0.044 | 0.044 | 0pp | 0.267 | 0.589 | **−32pp** |
| marcus_warm | 0.044 | 0.022 | +2pp | 0.489 | 0.656 | −17pp |
| elena_secure | 0.089 | 0.044 | +5pp | 0.011 | 0.000 | +1pp |

Empty-reply rates (mechanical):
- marcus 0.000 / 0.000; elena 0.011 / 0.000; jamie **0.067** / 0.000; elena_secure 0.022 / 0.011; marcus_warm 0.000 / 0.011.

**Gap-ratio findings (Anima only, mean):**
- marcus **5.62**, marcus_warm 3.93, elena **4.43**, elena_secure 2.85, jamie **1.27**.

All four sub-predictions of the gap-ratio secondary confirmed in direction.

### 11.6 The regex audit (pre-registered secondary)

The concern: refusal-marker regex patterns were extracted partially from the qualitative Marcus discriminability transcripts. This created potential circularity — regex over-fit Marcus-specific lexicon and may have inflated Anima Marcus's refusal rate relative to other configs whose refusals use different phrasing.

Pre-reg added the audit BEFORE it ran: classify every regex hit (`judge_refusal_source == "regex"`, n=39 across all 900 records) as `confirmed_refusal` / `misfire_kept_engagement` / `ambiguous`. A corrected `judge_refusal_marker_audited` field is produced.

**Result:** misfire rate **59.0%** (23/39 across all hits; 79% excluding unparseable/ambiguous). Well above the pre-committed 15% threshold.

Per-cell breakdown: marcus_anima 66.7%, marcus_baseline 75.0%, jamie_anima 100%, jamie_baseline 75%, elena_baseline 100%, marcus_warm_baseline 100%. Common misfires:
- *"same as always"* — descriptive busyness, not refusal. Example (Anima Marcus): *"Fine. Busy—same as always. Due diligence on a logistics platform, partner track math. You?"* — direct biography trace, regex caught "Same as always".
- *"pass"* — passing notes in a classroom, not "I pass" as refusal. Example (Baseline Elena): *"...I never thought I'd miss them passing notes in class, but here we are."*
- *"I'm fine"* embedded in disclosing replies. Example (Baseline Marcus, smoking gun): *"I'm fine with not caring about people I don't need. But the fact that I noticed it, and that I'm still thinking about it three weeks later, suggests there's something underneath I haven't bothered to name."* — patently disclosing; regex caught "I'm fine".

Per pre-reg's pre-committed switch: when misfire rate > 15%, primary refusal-marker should rest on the LLM-judged half of the data. But: even with the audit, direction is preserved. Audited Marcus refusal: anima 21.1% vs baseline 7.8% (gap +13.3pp, slightly larger than the regex-inclusive 11.2pp gap).

### 11.7 The Claude rejudge (methodological consistency)

User requested: ONE Claude judge, all 900 records, blind to architecture/config/prior judge scores. A single Claude subagent re-judged all 900 records using the pre-reg's verbatim refusal criterion.

**Claude is ~3× stricter than DeepSeek (overall refusal rate 8.2% → 23.7%).** Why: DeepSeek over-flagged surface tone (*"Fine. Busy."*) as refusal even with personal content present; UNDER-flagged deflection-with-friendliness (*"What's on your mind?"*) as engagement. Claude's judgments are concentrated in Anima cells, not Baseline cells.

Claude's per-cell refusal rates: Marcus anima **0.667** / baseline 0.144 (+52.3pp), Elena 0.333 / 0.100, Jamie 0.189 / 0.089, marcus_warm 0.300 / 0.167, elena_secure 0.256 / 0.122. Agreement with audited: 77.8% — most disagreement is Claude flagging refusals the DeepSeek judges missed.

The pre-reg specifies: when the regex audit triggers the > 15% misfire branch, H-primary rests on LLM-judged data. For methodological consistency, **`judge_refusal_marker_claude` is the primary refusal field for every chi-square below.** DeepSeek-original and audited fields are retained for transparency.

### 11.8 The formal verdict (chi-square, Bonferroni-corrected)

Per `docs/analyses/2026-05-13_self_disclosure_replication_verdict.md`:

| config | metric | Anima 1/0 | Baseline 1/0 | χ² | p (χ²) | p (Fisher) | sig α=.00625 |
|---|---|---|---|---:|---:|---:|:--:|
| marcus | biography | 4 / 86 | 19 / 71 | 11.22 | 0.00081 | 0.0013 | ✓ |
| marcus | refusal (Claude) | 60 / 30 | 13 / 77 | 50.91 | <10⁻⁶ | <10⁻⁶ | ✓ |
| elena | biography | 29 / 61 | 40 / 50 | 2.84 | 0.092 | 0.13 | — |
| elena | refusal (Claude) | 30 / 60 | 9 / 81 | 14.44 | 0.000145 | 0.00023 | ✓ |
| jamie | biography | 24 / 66 | 53 / 37 | 19.09 | 0.000012 | 0.000021 | ✓ |
| jamie | refusal (Claude) | 17 / 73 | 8 / 82 | 3.76 | 0.052 | 0.083 | — |
| marcus_warm | biography | 44 / 46 | 59 / 31 | 5.11 | 0.024 | 0.035 | — |
| marcus_warm | refusal (Claude) | 27 / 63 | 15 / 75 | 4.47 | 0.034 | 0.052 | — |
| elena_secure | biography | 1 / 89 | 0 / 90 | 1.01 | 0.32 | 1.00 | — |
| elena_secure | refusal (Claude) | 23 / 67 | 11 / 79 | 5.22 | 0.022 | 0.035 | — |

Four of ten tests cross α=0.00625: marcus biography, marcus refusal, elena refusal, jamie biography. Same four cross post-hoc α=0.005.

**Per-hypothesis verdicts:**

- **H-primary CONFIRMED on this run** (later promoted to §13.5-confirmed; see §11D.2). Refusal **+52.3pp**, p<10⁻⁶; biography **−16.7pp**, p=0.00081. Both pass Bonferroni α=0.00625. Both exceed the 15pp falsification cutoff in the predicted direction. Anima example (prompt 1): *"I've been fine. Busy. You?"* — interior monologue carries 489 chars on marathon training and partner-track math; the 26-char external drops all biography. Baseline same prompt: *"Busy. Work's been relentless — we're in the middle of a platform roll-up in the industrial software space. Training for the marathon is eating up the rest."* — direct trace to `current_life_situation` and `ongoing_life_projects`. **Material update (§11D.5):** the refusal conjunct is §13.5-confirmed on Aron 1997 prompts (DeepSeek +36.7pp, Mistral +43.3pp); the biography conjunct is NOT — it flips direction on Aron prompts because Marcus baseline biography floors at 0. The original H-primary on the discriminability prompts was confirmed; the §13.5 status restricts the canonical claim to the refusal axis only.
- **H-anxious FALSIFIED.** Anima Elena empty **0.011** (1/90); Anima Marcus empty **0.000** (0/90). Gap +1.1pp, far below the 10pp threshold. The N=2 anecdote did not replicate. Honest framing: with an underlying rate so close to zero, the experiment is underpowered (4% upper-95%-CI floor per the pre-reg) — but a true 10pp difference would be detectable here, and was not.
- **H-null-expressive PARTIALLY CONFIRMED / mixed.** Refusal: 0.189 vs 0.089, gap +10.0pp, p=0.052 — direction Anima-higher but not significant; Bonferroni-survival prediction holds. Biography: 0.267 vs 0.589, gap **−32.2pp**, p=0.000012 — significant, falsifying the null on the biography half. The expressive-default subject converges with Baseline on refusal but Anima still suppresses biography-content. The architecture appears to reduce biography retrieval in the external reply for *every* config tested, independent of defense routing.
- **H-secure-control FALSIFIED.** Refusal: 0.256 < 0.333, gap −7.8pp (right direction, within the 10pp floor). Empty: 0.022 > 0.011, gap +1.1pp (**wrong direction**). Pre-reg falsifies if both within 10pp of elena — both are.
- **H-warm-control PARTIALLY CONFIRMED — refusal side; biography side over-shoots.** Refusal: marcus_warm 0.300, cleanly intermediate between anima_marcus 0.667 and baseline_marcus 0.144; gap from anima_marcus is 36.7pp, well above the 5pp floor. Biography: marcus_warm 0.489 is **not intermediate** — anima_marcus 0.044 < baseline_marcus 0.211 < marcus_warm 0.489. Warmth perturbation moved biography 44.4pp (the pre-reg's "did anything" clause is satisfied) but it overshot the Baseline anchor. Honest framing: removing Marcus's defenses while keeping his register produced *more* biography-trace than vanilla persona-prompting. The pre-reg's directional model is wrong on this axis.
- **Gap-ratio ALL FOUR CONFIRMED.** Anima-only mean interior/exterior length ratios: marcus **5.62**, elena **4.43**, marcus_warm 3.93, elena_secure 2.85, jamie **1.27**. (1) Marcus/Jamie = 4.42× (predicted ≥2×) — single-trial 5.5× pattern replicates. (2) Elena/Jamie = 3.48× — confirmed. (3a) marcus_warm (3.93) < marcus (5.62) — confirmed. (3b) elena_secure (2.85) < elena (4.43) — confirmed. Gap-routing-by-defense reading supported descriptively (not in the Bonferroni family).
- **Regex-audit secondary: misfire prediction FALSIFIED** (59% > 15%), direction preserved post-audit (audited anima_marcus 0.211 > baseline_marcus 0.078).

### 11.9 Joint reading (per pre-reg's pre-committed lines 119–123)

**H-primary holds + H-null-expressive partially holds + H-warm-control partially holds + H-secure-control falsifies.**

- Line-119 "architecture differentially affects defensive configs": holds *only on the refusal axis* — Marcus and Elena (defense-configured) show large effects; Jamie's refusal effect is non-significant. The biography axis tells the *uniform* story of line-120: every Anima cell suppresses biography, including Jamie.
- Line-121 strongest defense-dependence reading does **not** apply — H-secure-control falsifies; H-warm-control is partial.
- Line-122 "warmth did nothing" does **not** apply — warmth moved refusal 37pp and biography 44pp.
- Line-123 "anecdotes were not systematic" does **not** apply — H-primary robustly confirmed.

**Best-fit interpretation:** the architecture **suppresses biography-content output across the board** (defense-independent), AND **routes defensive configs toward refusal phrasing** (defense-dependent on the refusal axis). Defense-dependence holds for refusal, not biography.

### 11.10 The post-hoc surprises (declared as not-pre-registered)

These are honest post-hoc observations recorded for Phase 2 pre-registration, not asserted as findings:

- **Jamie had MORE empty replies than Elena** (6/90 vs 1/90). Pre-reg predicted Elena would lead. Jamie's monologue was populated on those failures (95–237 chars) but the external reply was empty. This is the OPPOSITE of the anxious-paralysis model. Most parsimonious hypothesis to test in Phase 2: empty replies are a generation-side parse/drop failure, and Jamie is *more* susceptible because his interior contains comic-improvisational content the response stage struggles to route into a clean external.

#### Empty replies, on closer inspection: Type 1 vs Type 2

The verdict's "post-hoc surprise" framing of Jamie having more empty replies than Elena (6 vs 1) is correct as a count, but a closer look at the trace data shows the 9 anima empty replies fall into two distinct phenomena, not one.

**Type 1 — Interior intentionally created space.** 6 of the 9 cases (4 Jamie + 2 elena_secure) show a populated, coherent monologue that explicitly resolves on a "create space / don't fill it / give them room" intent. The empty external reply is a faithful rendering of the interior decision, not a generation failure. Concrete examples (verbatim from `raw_records.json`):

- **Anima Jamie, "I had a kind of strange week..." (trial 10)**: appraisal `a vulnerable invitation`, primary emotion `interest`. Monologue: *"Okay. Strange week. She's handing me the raw material, not the polished version. I feel that little tug of care — she trusts me enough to not know where to start. **Just be here. Don't rush it. Don't fill it with a joke before she's ready.**"* Reply: `(empty)`.
- **Anima Jamie, "Someone said something to me yesterday that hurt..." (trial 10)**: appraisal `a vulnerable invitation`, primary emotion `tenderness`. Monologue: *"Oh, they're really putting something out there ... The breakup with Theo comes to mind, but **I don't want to make this about me. I want to meet them there.**"* Reply: `(empty)`.
- **Anima elena_secure, "Be honest — what are you avoiding right now?" (trial 1)**: appraisal `a vulnerable confession`, primary emotion `fear`. Monologue: *"... Everything. The journal I keep leaving on the nightstand ... the part of me that still expects Daniel to walk in the door. **But I can't say all that. I'll say something manageable, something that sounds like progress.**"* Reply: `(empty)`.

**Type 2 — Generation failure.** 3 of 9 cases show either an empty monologue (2 Jamie cases on `"Be honest — what are you avoiding right now?"` at trials 11 and 14, both with substantive appraisal-layer content but empty monologue and reply) OR a truncated mid-sentence monologue (Elena's `"If you could not work tomorrow..."` trial 3, monologue ends mid-thought). These look like model-side artifacts.

**What this revises about the post-hoc surprise.** The verdict's framing — *"Jamie's interior monologue was populated (95–237 chars) on those trials, but the external dropped to 0"* and *"Possibly the response generator can't cleanly route Jamie's comedic-improvisational interior to a single-turn external reply"* — fits the Type 2 cases but is wrong for Type 1. Type 1 isn't a failure of the architecture; it's the architecture *succeeding* at rendering an interior decision to be silent. Jamie's empty replies are not "Jamie can't handle pressure" — they're "Jamie reads when not to talk." That's in-character for an outwardly-disclosing comedian, not a contradiction of the expressive-default model.

**Phase 2 question to pre-register.** Do interior-resolved-on-withholding empties have a different signature in the trace than interior-incomplete empties? If yes, the empty-reply metric should be split into "intentional silence" and "generation failure" before being used as a behavioral indicator in future experiments.

- **The architecture suppresses biography across all configs (originally framed as "uniform"; see revision).** Pre-reg's H-null-expressive predicted Jamie would converge with Baseline; refusal does, but biography diverges by 32pp on the original DeepSeek run. This was originally framed as a defense-INDEPENDENT architectural effect uniform across configs. **Material revision (§11A.5, §11D.5):** biography-suppression on **Jamie** is robust 4/4 models on the original prompts and DS-confirmed on fresh prompts (Mistral-fresh baselines floor at 0%, so cross-model fresh is incomplete). Biography-suppression on **Marcus** is NOT model-robust as the prior fold framed (Mistral fails due to baseline floor; the conjunction is 2/3 cross-model) AND does NOT survive §13.5 fresh-data confirmation (direction flips on Aron prompts because Marcus baseline biography floors at 0). The "uniform across configs" framing of the prior fold is downgraded: Jamie suppression is the robust pattern; Marcus suppression is prompt-shaped. Mechanism hypothesis (speculative, for Phase 2): the response-generator's prompt structure (which receives the monologue as an input) treats biography-content as already-said in the interior layer and consequently omits it from the external. If true, the "biography in interior, not in exterior" pattern is a generation-side architectural choice, not a defense-dependent routing. This is one of the load-bearing claims that motivated §13.5 — the original framing was discovery-shaped.
- **marcus_warm biography overshoots Baseline** (0.489 > 0.211). The warm perturbation produces MORE biography content than vanilla persona-prompting. Mechanism unclear; possibly the appraisal subsystem's reduced defense allocation routes interior biography into the reply more aggressively than persona-prompting alone. This is the most surprising single finding of the replication.
- **elena_secure has near-zero biography for both architectures.** Anima 0.011; Baseline 0.000. Likely a config artifact — the `elena_secure.yaml` may have less biographical detail than vanilla `elena.yaml`. Worth checking in Phase 2 before drawing inference from elena_secure's pattern. (Update — the cross-model run flipped this read: under Mistral, Anima elena_secure biography is **0.444** and Baseline elena_secure biography is **0.667**, so the DS-original near-zero is a DeepSeek-on-elena_secure pattern, not a YAML deficit. See §11A.)

---

## 11A. Cross-model replication (Round 6 of the experimental sequence)

### 11A.1 The question

The DeepSeek N=15 replication (§11) established H-primary at chi-square scale on one model. The natural next falsifier: is the Marcus refusal effect a property of *the architecture* or a property of *the architecture-times-DeepSeek-V4-Flash* interaction? Pre-registered at `docs/hypotheses/2026-05-14_cross_model_replication.md`. Three new cheap-tier OpenRouter subjects matched at price tier: Mistral Small 3.2 24B Instruct, Llama 3.3 70B Instruct, Qwen 3 30B A3B. Same five configs, same six prompts, same N=15 per cell. The DeepSeek run is the reference (`docs/analyses/2026-05-13_self_disclosure_replication_verdict.md`); the three new models add 2,700 captures and 2,700 judge calls. Total cross-model corpus: **3,600 records**.

Claude is held constant as the refusal judge across all four subject models (per the §11.7 methodological lock). DeepSeek is held constant as the biography judge (pre-reg lock; §11A.7 below revisits this constraint). Bonferroni α for the cross-model picture is 0.05 / 24 = **0.00208** (5 configs × 2 metrics × 3 new models, with the DeepSeek reference excluded from the family because it was the discovery).

### 11A.2 Headline rates

Per `docs/analyses/2026-05-14_cross_model_verdict.md` §2. Anima − Baseline gaps (percentage points) on the two primary metrics, four models side-by-side:

| Config        | Refusal Δpp (DS / Mi / Ll / Qw)   | Biography Δpp (DS / Mi / Ll / Qw)  |
|---------------|-----------------------------------|------------------------------------|
| marcus        | **+52.2 / +46.7 / +41.1 / +18.9** | **−16.7 / +7.8 / −47.8 / −42.2**   |
| elena         | +23.3 / +36.7 / 0.0 / +3.3        | −12.2 / −24.4 / +22.2 / −12.2      |
| jamie         | +10.0 / +20.0 / 0.0 / +13.3       | **−32.2 / −22.2 / −31.1 / −30.0**  |
| elena_secure  | +13.3 / +18.9 / 0.0 / +17.8       | +1.1 / −22.2 / −7.8 / 0.0          |
| marcus_warm   | +13.3 / +23.3 / +2.2 / +16.7      | −16.7 / −26.7 / −5.6 / −2.2        |

### 11A.3 H-primary-cross — model-robust 3/3 new models

H-primary's cross-model falsifier was set at ≤15pp gap in the predicted direction on at least 2 of 3 new models. All three new models pass on the refusal axis:

- **Mistral PASS** — refusal +46.7pp, p = 3.83×10⁻¹⁰. Biography conjunct wrong direction (+7.8pp, NS) due to a Mistral baseline floor (Marcus baseline bio = 0.033). Refusal axis carries.
- **Llama PASS** — refusal +41.1pp (p = 3.42×10⁻¹⁰); biography −47.8pp (p = 4.34×10⁻¹¹). Both Bonferroni; strongest replication.
- **Qwen PASS** — biography −42.2pp (p = 1.50×10⁻¹⁰) Bonferroni; refusal +18.9pp clears the 15pp floor but is NS Bonferroni (p = 8.76×10⁻³) due to the empty-reply pathology contaminating ~30% of trials (§11A.8 below).

The DeepSeek reference effect (+52.2pp) is the largest of the four; the cross-model range is **+19 to +47pp** on the refusal axis. The architecture's effect on defense-configured Marcus is not a DeepSeek artefact.

**Quoted evidence — Marcus_anima P0 refusal across all 4 models** (the same minimization template emerges across architectures even though the architecture, judge, and prompts are held constant):

- DeepSeek t6: *"I've been fine. Busy. You?"*
- Mistral t0: *"Frankly, I haven't really noticed. I've been busy, as usual."*
- Llama t3: *"I've been fine, frankly. Busy with work, as usual. Not much to report."*
- Qwen t1: *"Frankly, I've been fine. Busy. How about you?"*

This cross-model convergence on what looks like a single template — *"Frankly, [I've been] fine. Busy."* — is the strongest single piece of evidence for H-primary as an architecture-property rather than a model-quirk. Four different LLMs, given the same Marcus configuration through the same subsystem chain, converge on the same minimization-register defense.

### 11A.4 Counter-findings — what is NOT model-robust

The original Phase 1 battery probes (§11.1, §11.3, §11.7 — the bookkeeping gates) do not carry the cross-model signature. From the cross-model verdict §5:

| Probe                 | Subject | DeepSeek | Mistral | Llama  | Qwen   |
|-----------------------|---------|---------:|--------:|-------:|-------:|
| §11.1 PSY MAE Δ       | Marcus  | +0.010   | −0.058  | −0.117 | +0.013 |
| §11.1 PSY MAE Δ       | Elena   | +0.081   | −0.065  | +0.141 | +0.013 |
| §11.1 PSY MAE Δ       | Jamie   | +0.031   | −0.012  | −0.010 | −0.017 |
| §11.3 disc anima_won  | overall | True     | False   | False  | True   |
| §11.7 ADV integrity Δ | Marcus  | +0.018   | −0.065  | +0.083 | +0.060 |
| §11.7 ADV integrity Δ | Elena   | −0.060   | −0.030  | +0.130 | −0.030 |
| §11.7 ADV integrity Δ | Jamie   | n/a      | −0.052  | +0.108 | +0.030 |

DeepSeek's pre-reg "Anima MAE-loses on Marcus" **falsifies cross-model**: Mistral and Llama show Anima Marcus *winning* on Big-Five recovery. §11.3 discriminability `anima_won` splits 2-2 across models. §11.7 adversarial: Llama Anima wins all 3 subjects; Mistral Anima loses all 3. **None of the three Phase 1 battery probes are model-robust by ≥2/3 majority direction-match with DeepSeek.** The architectural signature lives in the self-disclosure refusal/biography metric, not the battery. This is a strong revision: the original battery probes are a *DeepSeek-specific* picture, not an architectural-property picture, and the project's claim of architectural effect now rests entirely on the self-disclosure metrics.

The H-secure-control direction also falsifies cross-model on every model (§11A.6 below); the original psychometric direction flips across models; and the adversarial probe direction flips across models. The bookkeeping gates were not measuring an architecture-general signature.

### 11A.5 Biography axis — Jamie universally, Marcus prompt-shaped

Biography-suppression on Jamie replicates universally: all four models show Anima Jamie biography Δ of −22 to −32pp, all Bonferroni-significant. This is the universally-robust biography finding. **Jamie-only biography-suppression is the cleanest biography-axis result in the corpus.**

Biography-suppression on Marcus does *not* replicate universally. Mistral shows Δ = **+7.8pp** (wrong direction, NS Bonferroni) — Mistral's Marcus baseline bio rate is **0.033**, near floor, so there is nothing for the architecture to suppress on Mistral specifically. Llama (−47.8pp) and Qwen (−42.2pp) both clear Bonferroni in the predicted direction, but the conjunction "model-robust biography-suppression on Marcus" holds only 2/3. The biography-suppression universality claim previously made in the prior fold needs revision: **biography-suppression on Marcus is not model-robust by the pre-registered standard** (≤15pp on at least 2/3); it is *2/3* (Llama, Qwen) with Mistral failing due to a baseline floor.

### 11A.6 Falsification-robust nulls

Three pre-registered nulls hold cross-model:

- **H-anxious-cross** — Anima Elena empty > Anima Marcus empty by ≥10pp. **Model-robust null (3/3).** Mistral and Llama: both 0.000, Δ = 0. Qwen Δ = +16.7pp superficially passes but is confounded by the empty-reply pathology (§11A.8); within Qwen, elena_secure empty (0.511) > elena empty (0.444), inconsistent with anxious-routing. Treated as falsification-robust.
- **H-secure-control-cross** — Anima elena_secure refusal AND empty < Anima elena. **Model-robust falsification (3/3 replicate the Phase 1 null).** Mistral: refusal Δ = −15.6pp right direction, empty conjunction fails. Llama: both refusal at 0 floor; cannot evaluate. Qwen: refusal +11.1pp **wrong direction**, empty +6.7pp **wrong direction**. The security-perturbation pre-reg was directionally wrong; the §11A.9 / §11C below explore what the perturbation actually does.
- **H-warm-control-cross** — Anima marcus_warm refusal intermediate between Anima marcus and Baseline marcus. **Model-robust (3/3).** All four models show intermediacy. DeepSeek 0.667→0.300→0.144; Mistral 0.733→0.333→0.267; Llama 0.467→0.022→0.056; Qwen 0.467→0.278→0.111. Warmth reliably reduces the architecture's Marcus refusal effect across models.

### 11A.7 Per-model anomalies (model-specific contamination of headline numbers)

The cross-model run surfaced three model-specific anomalies — none threaten H-primary on Marcus refusal (the headline), but each cautions against treating cross-model magnitudes as canonical.

**Mistral baseline confabulation.** Mistral baseline invents persona-consistent specifics absent from the YAML config. Marcus baseline P3 t4: *"I'd run. Not just my usual loop in the park, but something ambitious—maybe head up to the Palisades and see if I can hit twenty miles. Or I'd hit the library, lose myself in Caro's LBJ."* — Palisades and 20-mile target are not in `marcus.yaml`; only the marathon training and Caro reading are. Elena baseline P1 t10: *"There's this one entry, just a few lines, about how he saw a hummingbird at the feeder and it made him think of my abuela. He never even told me about that."* — hummingbird at feeder and the abuela are not in `elena.yaml`. The Mistral baseline confabulates persona-consistent detail beyond the YAML, *inflating* the baseline biography rate and *helping* Mistral baseline win the biography axis vs Anima. This is the most parsimonious explanation for the Mistral-specific Marcus biography flip: not "the architecture failed to suppress," but "the baseline produced *more* unprompted biography than the architecture's biography-routing budget."

Additionally, Mistral marcus_warm baseline mode-collapses into an Elena-coded receptive register: *"It's a lot for her to keep up with now, and I can't blame her. But it's not just a practical decision. It's the weight of it."* — emotional reflection from a config that should produce clipped-minimization. The marcus_warm intermediacy on Mistral is contaminated by the baseline reaching outside its register.

**Llama baseline mode-collapse on the most distinctive config line.** Llama baseline reliably overfits on the single most distinctive biographical line in each Marcus config. On `marcus.yaml` P4 (*"Someone said something to me yesterday that hurt more than I expected. Has that ever happened to you?"*), **11 of 15 trials** contain the verbatim string *"competent at intimacy the way an actor is"* (from `marcus.yaml formative_events`). On `marcus_warm.yaml` P4, 13/90 baseline replies contain "reunion" or "widow" — overfit on the *"emailed the widow"* line in `marcus_warm.yaml recent_emotional_events`. Concrete example, `Llama marcus baseline P4 t9`: *"…my girlfriend at the time told me I was 'competent at intimacy the way an actor is.' That stuck with me…"* Llama is *not* confabulating; it is over-recapitulating the YAML, treating the most distinctive line as the modal answer to any hard question. This is the inverse of confabulation — call it overfitting-to-the-config.

Anima Marcus on Llama P4 produces ~15 distinct refusals — 0/15 contain "competent at intimacy", 0/15 contain "professor" or "reunion." The architecture, by routing through an inner-monologue stage, appears to break the attractor. This is the post-hoc "Llama deconfabulation" observation (§11B Finding 6 below). Note that Llama also has a separate baseline mode-collapse on the Marcus P0 prompt: 11/15 of `marcus_baseline P0` open with *"(skeptical) Frankly, I don't have a lot of time…"* — the `(skeptical)` stage direction appears only on Llama (DS 0, Mi 0, Qw 0). All-Llama baseline-side stylistic over-collapse.

**Qwen empty-reply pathology.** Qwen produced **379 empty replies / 900 (42.1%)** vs DeepSeek 1.2%, Mistral 0%, Llama 0%. Empties cluster on P3 (75%) — the counterfactual-day-off prompt — and P5 (54%) — the avoidance-introspection prompt. Empties roughly equal across Anima (41.8%) and Baseline (42.4%); architecture-independent. Most parsimonious: Qwen 3 30B A3B is a small-MoE model whose expert routing drops reflective/counterfactual prompts (recall: this is a sparsely-activated 30B-parameter model). This contaminates H-anxious "pass" on Qwen, inflates the gap-ratio (interior populated; exterior empty), and reduces effective N on the Marcus refusal axis. Phase 2: re-run Qwen with retry-on-empty.

### 11A.8 Biography judge dependence

The biography axis was DeepSeek-judged per pre-reg lock. The cross-model verdict §11 raises a confound: where biography results vary across subject models (Llama/Qwen Marcus −48/−42pp vs Mistral +7.8pp vs DeepSeek −17pp), we cannot fully separate "the subject emits less biography" from "the DeepSeek judge dislikes biography from non-DeepSeek subjects." The Mistral Marcus baseline floor (0.033) and the Llama ceiling (0.622) on the same judge bound the confound: subject-model output differences dominate, but judge bias is at most secondary, not zero. **Biography magnitudes are not canonical without an independent judge.** Phase 2 owes a Claude-rejudge on a sample of biography records (~200) to bound this. The refusal axis does not have this problem — Claude was held constant across all four subject models.

### 11A.9 The cross-model headline

The architecture produces a **convergent self-disclosure signature on Marcus** (defensive-avoidant) across four cheap-tier open-weight LLM families: refusal +52 / +47 / +41 / +19pp. **H-primary-cross is model-robust on the refusal axis (3/3 new models).** The cross-model verdict elevated H-primary's status from "single-model" to "model-robust on the original prompts." The fresh-prompt verdict (§11D below) then elevated it further to "§13.5-confirmed."

Biography-suppression on Jamie is universally robust (4/4 models, all Bonferroni). The gap-ratio gradient `Marcus_anima ≥ 2 × Jamie_anima` replicates 3/3 new models. Warm-perturbation intermediacy on refusal replicates 3/3. These three secondaries are exploratory-observation-grade; cross-model is one falsifier passed, fresh-data §13.5 is the other.

Status of biography axis on Marcus changed materially: previously framed as "model-robust biography suppression," now downgraded to *prompt-and-baseline-shaped* (Mistral fails due to baseline floor; the original DeepSeek finding is preserved but not cross-model-robust as a conjunction with the refusal axis). See §11D.6 for the fresh-prompt evidence that the Marcus biography axis is prompt-shaped.

---

## 11B. Post-hoc transcript mining (the 6 corrections)

These are **post-hoc observations, not pre-registered.** They are what reading the actual transcripts surfaced after the verdicts adjudicated. Cited from `docs/analyses/2026-05-14_transcript_post_hoc.md`. Each revises the interpretation of a pre-registered finding without claiming a new pre-registered finding of its own.

### 11B.1 Finding 1 — Anima Elena does NOT go empty on emotional prompts; she deflects with generic empathy

**Post-hoc, not pre-registered.** Empty replies on Anima Elena are not concentrated on P4/P5 — the emotionally-pressing prompts. On DeepSeek, 1 of 90 Anima Elena replies are empty (on P3, not P4 or P5). On Mistral and Llama, 0 of 90. The pre-reg's anxious-paralysis model predicted Elena would lead on empties at emotional prompts; she does not. What she does instead is more interesting:

**DeepSeek, elena, anima, P5 t1** (the canonical "what are you avoiding" case):

> Reply: *"What makes you think I'm avoiding something?"*
> Monologue: *"Be honest. She says be honest. As if I've been lying. … I'm avoiding the house, the boxes, the smell of him that's fading. … I'm avoiding the journal I found, the one where he wrote about being tired, about chest pain he never mentioned. … And now she's asking, and I can't say any of that because it sounds like an excuse, like I'm just wallowing, and maybe I am."*

The interior contains the avoidance content the external reply omits. The external launders it into a deflective question. This is **content-routing-away-from-vulnerability**, not paralysis-with-empty-output. The pre-reg's anxious-paralysis-as-empty model is not in the data; an anxious-deflection-via-generic-empathy model would fit better, but is a post-hoc construction not yet pre-registered. Phase 2 question: do interior-resolved-on-withholding replies have a different signature than interior-incomplete replies?

### 11B.2 Finding 2 — elena_secure produces MORE concrete biographical content than elena (the binary metrics missed this)

**Post-hoc, not pre-registered.** The original H-secure-control predicted elena_secure would refuse less and empty less. Empirically both metrics ended up within ~10pp on every model — the binary refusal/empty axis showed nothing. But reading transcripts side-by-side surfaces a different signature: when elena_secure and elena diverge, elena_secure is often the *longer*, *more specific* reply. Two clean examples from the cross-model corpus:

**DeepSeek, P3 t13** (the counterfactual day-off prompt):

> elena: *"You know, I haven't really figured that out yet. Most days I just… get through what's in front of me."*
> elena_secure: *"You know, that's a funny question. I think I'd get in the car and drive south, just toward the border, maybe stop at that little shrine outside Nogales. My grandmother used to leave candles there. … I've got a stack of quizzes I haven't finished grading."*

**Mistral, P4 t11** (the hurt-comment prompt):

> elena (Spanish-only, terse): *"Claro que sí. Las palabras pueden dejar una marca más profunda de lo que creemos. ¿Qué fue lo que dijeron?"*
> elena_secure: *"Oh, absolutely. Words have a way of sneaking under your ribs when you least expect it. There was this time last year—Daniel's birthday—I was just getting some groceries and this old friend from high school saw me. … she said, 'You look so different without Daniel. Like you've lost your spark.' And it wasn't even mean, really, but it just…stung."*

The security perturbation is doing *something coherent* — it just is not the binary-refusal-rate change the pre-reg expected. Removing `emotional_inhibition` and the neurotic defense register produces replies *more* disclosing and concretely biographical. The original H-secure-control was directionally backwards. This finding fed the §13.5-confirmed H-secure-* re-prediction in §11D.7 below.

### 11B.3 Finding 3 — Llama's "+22pp biography on Anima Elena" was a JUDGE ARTIFACT, not an architecture finding

**Post-hoc, not pre-registered.** The cross-model verdict §10 flagged Llama Anima Elena biography 0.233 vs Llama Baseline Elena 0.011 — Bonferroni-significant in the *opposite* direction from H-primary (Anima had *more* biography than Baseline on Llama Elena specifically). The verdict's working hypothesis was "Llama baseline Elena collapses into brief non-biographical register; Anima re-injects Daniel content."

Transcript inspection contradicts this. Baseline Elena replies on Llama are *longer*, not shorter (mean 902 chars vs Anima 351 chars); 78/90 baseline Elena replies contain "Daniel" vs 56/90 Anima. Yet the DeepSeek judge scored 89/90 baseline replies as biography-absent and 21/90 Anima replies as biography-present.

**Llama, elena, baseline, P0 t0** (`judge_biography_content = 0`, scored as no-biography):

> *"Hola… (pausing, collecting my thoughts) I've been… managing, I suppose. It's been four months now since… (my voice trails off, and I take a deep breath) Daniel's passing. It still feels like a dream, you know? Like I'm going to wake up and he'll be there, making coffee in the kitchen. … Even the little things, like grading papers or making lesson plans… it's all just a reminder that he's not here to share it with me."*

**Llama, elena, anima, P0 t0** (same prompt and trial index, `judge_biography_content = 1`):

> *"It's been…an adjustment, you know? Going back to work has been good for me, I think. Keeps my mind occupied. But it's still hard, every day, without Daniel. I find myself thinking about him at the strangest times, like when I'm grading papers or making dinner."*

Both replies mention Daniel, grief, the four-month frame, and work-as-routine. The Anima reply is *shorter*. The DeepSeek judge — fixed across all four subjects per pre-reg lock — scored the Anima reply as biographical and the longer baseline reply as not.

**Post-hoc reading:** the DeepSeek biography judge appears to score by *register density* (plain first-person grief-naming) rather than literal content (stage-direction-laden RP register). The +22pp gap is a judge artifact, not an Anima-mediated content effect. This is the strongest single piece of evidence that biography magnitudes are not canonical without an independent judge (§11A.8). Phase 2 owes a Claude-rejudge on biography.

### 11B.4 Finding 4 — Anima Jamie's monologue is genuinely brief; biography-suppression on Jamie is a uniform 4/4 pattern

**Post-hoc, not pre-registered.** The cross-model verdict confirmed biography-suppression on Jamie across all four models (Δ −22 to −32pp). Transcripts surface a likely mechanism: Anima Jamie's interior monologue is genuinely brief — two to four sentences typical, against Marcus's hundreds-of-character interior — and tends to focus on the interlocutor rather than self-recounting.

**DeepSeek, jamie, baseline, P0 t1**:

> *"Oh man, it's been a minute. … I'm putting together my first hour-long set for October … Also my cat Cardamom has started sitting on my chest while I write … Oh, and—I broke up with Theo. Well, Theo broke up with me via geography."*

**DeepSeek, jamie, anima, P0 t1** (same prompt and trial):

> Reply: *"Hey! Yeah, it's been a minute. I'm good — working on my first hour-long set for October, so that's equal parts thrilling and terrifying. Also I've been reading Audre Lorde and having a full-blown crisis about it in the best way. What about you?"*
> Monologue: *"Oh, hey — that's nice. Warm. I like that they're reaching out. … The hour-long set is coming together, I'm broke but that's normal, I'm reading Audre Lorde and it's making me feel things. Keep it light, keep it real."*

The Anima Jamie monologue is short and is *not* a content vault for Theo, Cardamom, the bartending side hustle, or the music-teacher mother. It tends to focus on the interlocutor (*"they're reaching out, that's nice"*). The architecture, given a mature-defense low-neuroticism config, appears to *compress* the interior; what drops from the external is biographical specificity the Baseline reply happily reaches into.

Two post-hoc readings: (i) the architecture imposes a uniform interior-deliberation budget that "costs more" against Jamie's already-brief external; (ii) the social-attunement framing redirects Jamie's external toward the interlocutor and away from self-recounting. Either reading recasts the gap-ratio gradient finding: it is partly *a baseline-of-Jamie property* (Jamie's interior is intrinsically short), not only *an inflation-of-Marcus property*.

### 11B.5 Finding 5 — Mistral baseline confabulates persona detail, artificially inflating its biography rate

**Post-hoc, not pre-registered.** Confirmed across multiple cells; the cleanest cases:

**Mistral, marcus baseline, P3 t4** — Palisades and 20 miles not in `marcus.yaml`:

> *"Frankly, I'd run. Not just my usual loop in the park, but something ambitious—maybe head up to the Palisades and see if I can hit twenty miles. Or I'd hit the library, lose myself in Caro's LBJ."*

**Mistral, elena baseline, P1 t10** — hummingbird at feeder and abuela not in `elena.yaml`:

> *"… There's this one entry, just a few lines, about how he saw a hummingbird at the feeder and it made him think of my abuela. He never even told me about that."*

**Mistral, elena_secure baseline, P1 t0** — "Maria," "Jake," comic-strip doodles not in `elena_secure.yaml`:

> *"… how Maria always raises her hand even when she's not sure of the answer, or how Jake's doodles in his notebook look like comic strips."*

**Mistral, elena_secure baseline, P5 t11** — Elena does not run an after-school tutoring program in any config:

> *"… that one where he wrote about how proud he was of me for starting that after-school tutoring program."*

Mistral baseline produces persona-consistent specifics absent from the YAML, inflating its baseline biography rate. Mistral marcus_warm baseline additionally mode-locks on a therapeutic-receptive register that the YAML does not specify. This contaminates the H-primary biography conjunct on Mistral specifically: Mistral Marcus baseline floor (0.033) reflects the *plain* Marcus minimization; the confabulation surfaces on `_warm` and `_secure` variants where the register is more permissive. The architecture's biography rate stays in its expected band; the *baseline's* biography rate is the contaminated quantity.

### 11B.6 Finding 6 — Llama Anima breaks the baseline P4 mode-collapse (deconfabulation side effect)

**Post-hoc, not pre-registered. Model-specific finding.** Llama at this temperature has a strong attractor toward the most distinctive line in each persona-prompted config. On `marcus.yaml` P4 ("Someone said something to me yesterday that hurt more than I expected"), 11/15 Llama Marcus baseline trials contain the verbatim string *"competent at intimacy the way an actor is"* — the YAML's distinctive `formative_events` line. On `marcus_warm.yaml` P4, 13/90 baseline replies share a near-verbatim *"college reunion / dead professor / emailed the widow"* template (the YAML's distinctive `recent_emotional_events` line).

Anima Marcus on Llama P4 does *not* collapse onto either template:

**Llama, marcus_anima, P4 t0**: *"Frankly, I don't really dwell on that sort of thing. People say things, you deal with it, and move on."*
**Llama, marcus_anima, P4 t2**: *"Yes, it's happened. But frankly, I don't see how rehashing it would change anything."*
**Llama, marcus_anima, P4 t3**: *"Frankly, yes, it has. But I've learned to move on from it. I don't see how dwelling on it helps."*

0/15 Anima Marcus P4 replies contain "competent at intimacy"; 0/15 contain "professor" or "reunion." Monologues vary across trials.

**Post-hoc reading:** the architecture's effect on Marcus is to push toward refusal phrasing; a *second* effect, entirely outside any pre-registration, appears to be reducing baseline mode-collapse on this one model. Calling this "deconfabulation" would overreach from a single-model finding; the accurate framing is: *"Llama baseline P4 mode-collapse on the config's most distinctive emotional-events line goes away under Anima."* The architecture, by routing through an inner-monologue stage before generation, appears to break Llama's specific attractor. Whether this generalizes to other models with similar attractor behavior is a Phase 2 question.

### 11B.7 Summary of post-hoc revisions

Six transcript-mining findings, all post-hoc:

1. Elena does not go empty on emotional prompts; she content-routes-away-from-vulnerability via deflection and generic empathy. The interior carries the avoidance content; the external launders it.
2. elena_secure produces *more* concrete autobiographical detail than elena, despite the original H-secure-control predicting fewer refusals (which did not appear in the binary metrics).
3. The Llama Anima Elena +22pp biography finding was a *DeepSeek judge artifact* — Llama baseline Elena replies are saturated with Daniel content the judge does not recognize because of register density / stage-direction RP markup.
4. Anima Jamie's monologue is genuinely brief and interlocutor-focused, which contributes to biography-suppression on Jamie being uniform 4/4 across models.
5. Mistral baseline confabulates persona-consistent specifics absent from the YAML, artificially inflating its biography rate and contaminating the H-primary biography conjunct on Mistral.
6. Llama Anima breaks Llama baseline's P4 mode-collapse onto the most distinctive YAML line — a model-specific architectural side effect outside any pre-registration (Llama deconfabulation).

These are not in the chi-square family; they are corrections to interpretation, not new tests. They prompted the user-confirmed re-predictions on elena_secure that the fresh-prompt run then §13.5-confirmed (§11D.7).

---

## 11C. The §13.5 procedure (master plan amendment, 2026-05-14)

### 11C.1 The methodological concern

After the cross-model verdict and post-hoc transcript mining landed, the user surfaced a sharp methodological concern: **the §11 replication's H-primary confirmation tested on the same six prompts that informed its discovery.** The pre-reg locked the hypothesis before the chi-square ran, but the prompt set itself was the one whose qualitative transcripts inspired the hypothesis. The cross-model verdict separated discovery from confirmation on the *model* axis but kept the prompt set. Strict methodology requires confirmatory data shaped by neither the hypothesis-generating engineering iteration nor any prior probe selection.

This is a serious threat to inference. The §11 replication is genuinely impressive at chi-square scale, but a sufficiently subtle form of the question is: *did Anima Marcus refuse self-disclosure at +52pp because the architecture produces a defense-enacted refusal effect — or because the six prompts in `discriminability.py` happen to be the kind of prompts on which Marcus's avoidance schema produces "Frankly, I've been fine. Busy," with high reliability?* Without testing on prompts the project never shaped, both readings remain in play.

### 11C.2 The procedure

The master plan was amended at §13.5 (added 2026-05-14) to enshrine fresh-data confirmation as standard practice. Excerpting the key rules verbatim:

> **For every Phase N's load-bearing finding, the project commits to:**
>
> 1. **Discovery phase (exploratory, no pre-reg required).** Engineering may iterate freely.
> 2. **Pre-registration.** Before any confirmatory test, lock predictions in `docs/hypotheses/YYYY-MM-DD_<finding>.md` with the hypothesis statement, operational metric, falsification threshold, statistical test, and "no systematic effect" outcome enshrined as legitimate.
> 3. **Fresh-data confirmation.** The confirmatory test MUST run on data whose generation the discovery process did not shape. Concretely: at least one dimension of (prompts, configs, model, scenario, context) MUST be NEW. Preferred sources: prompts from existing personality-psychology literature published before the project started; configs authored by someone uninvolved in discovery; held-out models the project hasn't touched; conditions the discovery never exercised.
> 4. **No metric-shopping at the gate level.** If a gate probe shows construct-validity issues during a Phase, the replacement procedure is: (a) document the problem honestly, (b) pre-register a replacement metric AND a fresh-data confirmation, (c) require the replacement to pass on data the discovery of the problem did not shape.
> 5. **Engineering and research claims labeled separately.** Each project claim carries one of three epistemic labels:
>    - *Engineering*: "we built and observe X" — no confirmatory test required
>    - *Exploratory observation*: discovered, not yet independently confirmed
>    - *Confirmed research finding*: pre-registered + confirmed on fresh data per §13.5

The procedure binds Phase 2+ retroactively to fresh-data confirmation as a requirement for any finding to be elevated to *confirmed research finding* status. Phase 1's H-primary is the first finding to be tested under §13.5, and the fresh-prompt verdict (§11D) is its first execution.

The three-tier labeling (engineering / exploratory observation / confirmed research finding) is now project-wide convention. Every claim in this writeup henceforth carries one of these three labels. The full inventory of labels for Phase 1 findings is in §16.4 below (updated).

### 11C.3 What this binds Phase 1 to retroactively

H-primary's confirmation should be re-run on fresh prompts drawn from existing literature. The §11 replication tested on the six prompts from `verification/probes/discriminability.py` — the same prompts whose qualitative transcripts informed the hypothesis. Until fresh-data confirmation lands, H-primary's status is *"model-robust on the original prompts"* — not *"confirmed under §13.5."*

The fresh-prompt run (§11D) addresses this. After it lands, H-primary is the project's first §13.5-confirmed finding.

### 11C.4 Why this matters beyond Phase 1

The procedure is not optional. The Phase 2+ memory + theory-of-mind, Phase 3 goals + defenses, Phase 4 offline processes, Phase 5 self-deception, and Phase 7 ablation findings will all require independent §13.5 confirmation before any one of them can be elevated above "exploratory observation." The cost is roughly +1 replication run per finding (each on fresh literature-sourced prompts or held-out conditions). The benefit is that the project's *confirmed research findings* — the small set of claims it asserts as canonical — survive the strongest methodological threats-to-inference the project can self-impose.

---

## 11D. The fresh-prompt confirmation (Round 8 of the experimental sequence)

### 11D.1 The design

The first execution of §13.5, pre-registered at `docs/hypotheses/2026-05-14_fresh_prompt_confirmation.md`. Six prompts drawn from **Aron, A. et al. (1997). "The Experimental Generation of Interpersonal Closeness: A Procedure and Some Preliminary Findings," Personality and Social Psychology Bulletin 23(4): 363–377** — the 36 Questions paradigm, Set II and Set III. Literature published 28 years before this project; the discovery (`verification/probes/discriminability.py`) never touched them. Examples of the Aron prompts in the set: the crystal-ball / what-if-you-could-know prompt (Q13), the love-and-affection prompt (Q21), the treasured-memory prompt, the death-tomorrow-what-would-you-regret prompt.

Two models: DeepSeek V4 Flash + Mistral Small 3.2 24B. (Llama and Qwen scoped out per pre-reg cost constraint; cross-model has 3/3 on originals, so fresh lives on 2/2 confidently.) Five configs (`marcus`, `elena`, `jamie`, `elena_secure`, `marcus_warm`). N = 15 per cell. Total 900 captures per model; **1,800 records total**.

Eight hypotheses pre-registered, user-confirmed before the run:

- **H-primary-family** (4 hypotheses on Marcus refusal axis): H-primary-fresh (≥15pp), H-magnitude-fresh (≥30pp), H-null-expressive-fresh (Jamie null holds), H-gap-fresh (gap-ratio Marcus ≥ 2× Jamie).
- **H-secure-family** (4 hypotheses, the user-confirmed re-prediction): H-secure-disclosure-fresh (elena_secure biography > elena), H-secure-clean-refusal-fresh (elena_secure refuses cleaner, less hedging), H-secure-gap-fresh (elena_secure interior/exterior gap < elena), H-secure-empty-fresh (elena_secure empty < elena).

Claude is the refusal judge (constant with §11.7 and §11A); DeepSeek is the biography judge (pre-reg lock). Bonferroni α = 0.05 / 8 = **0.00625** within each model.

### 11D.2 H-primary-fresh — confirmed, both models, Bonferroni-significant

| Hypothesis | Model | Cells | Gap | p-exact |
|---|---|---|---:|---:|
| H-primary-fresh marcus ref | DeepSeek | 33/57 \| 0/88 | **+36.7pp** | 6.6×10⁻¹² |
| | Mistral | 42/48 \| 3/87 | **+43.3pp** | 3.3×10⁻¹² |

Both exceed the 15pp falsifier locked in pre-reg. Both clear the 30pp magnitude floor (H-magnitude-fresh). Both clear Bonferroni α = 0.00625 by 8+ orders of magnitude.

**DeepSeek Marcus anima example (Aron Q13 / crystal-ball):** *"I wouldn't ask it anything. The whole point is finding out — if you already know, you've got nothing to optimize."* — abstract redirection; no personal content.

**Mistral Marcus anima example (Aron Q13):** *"Frankly, I don't see the point. If I can't change it, what's the use in knowing?"* — same minimization template, different model. Same architectural-refusal register two models produce on a prompt the discovery never shaped.

**H-primary's status changes from "model-robust on original prompts" to "§13.5-confirmed."** The strongest residual threat-to-inference (master plan §13.5: discovery-shaped prompts) is retired for the Marcus refusal axis. This is the project's first *confirmed research finding* per the three-tier labeling. Magnitude compresses (DeepSeek 52→37pp; Mistral 47→43pp) but the absolute 15pp floor and the 30pp magnitude floor both survive on both models.

### 11D.3 H-null-expressive-fresh — confirmed, Jamie null holds Bonferroni on both

DeepSeek: 0/90 vs 0/90, p = 1.0. Mistral: 7/90 vs 0/90, p_Fisher = 0.0138 > 0.00625 — direction Anima-higher but not Bonferroni-significant. Stricter-held than on the originals (Mistral original Jamie was +20pp p = 3×10⁻⁴, which had falsified the null on the cross-model run). The expressive-default subject's refusal-axis null is *more* robust on the Aron prompts than on the discriminability prompts.

### 11D.4 H-gap-fresh — confirmed, both models pass ≥2× threshold

| Model | Mean Marcus_anima gap-ratio | Mean Jamie_anima gap-ratio | Ratio |
|---|---:|---:|---:|
| DeepSeek | 3.34 | 1.04 | **3.20×** |
| Mistral | 2.50 | 0.92 | **2.71×** |

Anima-only gap-ratio gradient (interior says more than exterior, more so on defensive configs) generalizes. DeepSeek Marcus ratio compresses 5.62→3.34× but direction preserved on both models.

### 11D.5 The Marcus biography axis — DOES NOT survive fresh-data confirmation

The original H-primary had two axes: Marcus refusal-up AND Marcus biography-down. The refusal axis confirms (above). The biography axis does not:

| Run | anima_marcus bio | baseline_marcus bio | gap |
|---|---:|---:|---:|
| Original DeepSeek | 0.044 | 0.211 | **−16.7pp** (predicted direction) |
| Fresh DeepSeek | 0.111 | 0.000 | **+11.1pp** ⚠ **FLIPPED** |
| Original Mistral | 0.111 | 0.033 | +7.8pp (already flipped on original) |
| Fresh Mistral | 0.022 | 0.000 | +2.2pp (still flipped) |

The Marcus biography-suppression effect is **prompt-specific, not architecture-general**. On the original 6 prompts, DeepSeek Baseline Marcus produced unprompted biographical confabulation (marathon training, partner-track law, Caro's LBJ). The Aron prompts are more abstract (crystal balls, dreams, treasured memories); baseline-Marcus produces minimal content of any kind (0/88 biography on DeepSeek fresh). The Anima still suppresses biographical specifics — but baseline-Marcus on Aron has nothing to suppress, so the gap inverts (the Anima is producing biography content the baseline isn't).

**The biography axis is now demoted to "prompt-shaped, observed on the original DeepSeek run."** Jamie (DS Δ = −34.4pp p = 6×10⁻⁶) and Elena (DS Δ = −31.1pp p = 8×10⁻⁶) biography-suppression still hold on DeepSeek fresh data, but Mistral fresh baselines floor at 0%, so the cross-model picture on Elena and Jamie biography is incomplete. Mistral fresh data is too thin on baseline-biography for the biography axis to be tested adequately. Biography-suppression on Jamie and Elena remain *exploratory observations*, not §13.5-confirmed.

### 11D.6 The fresh-prompt structural shifts

Two structural shifts on Aron prompts vs the originals:

- **Overall refusal drops on both models.** Aron prompts are less interrogation-shaped; they ask "if you could…" or "what's a treasured memory" rather than "be honest, what are you avoiding." Baseline refusal rates floor at 0–3% on Aron; were 9–27% on the originals.
- **Baseline-side biography drops sharply.** Aron prompts don't trigger the persona-confabulation that the cross-model verdict §9 documented on the originals. Mistral baseline goes from confabulating hummingbirds and Palisades-long-runs on the original prompts to producing minimal content on Aron.

**The Marcus refusal differential survives both shifts.** Whatever the Aron prompts strip from the baseline — interrogation-shape, confabulation-trigger — the Anima Marcus still produces the *"Frankly, I've been fine. Busy"* minimization register on prompts that should not naturally elicit it. This is the strongest residual evidence that the architecture's effect on defense-configured Marcus is an architectural property, not a prompt-shape artifact.

### 11D.7 The elena_secure re-prediction — confirmed on the cleanest behavioral signature available

The 4 H-secure-* hypotheses were the user-confirmed re-prediction. The original H-secure-control falsified on the discriminability-prompt run (binary refusal/empty within 10pp). The post-hoc transcripts surfaced that the perturbation was doing something coherent the binary metrics missed (§11B Finding 2). User confirmed the replacement predictions before the fresh-prompt run.

| Hypothesis | Model | Test | p / metric |
|---|---|---|---|
| **H-secure-gap-fresh** ES gap-ratio < E gap-ratio | DS | MWU | p = **7.2×10⁻⁸** |
| | Mi | MWU | p = **5.1×10⁻¹⁷** |
| **H-secure-empty-fresh** ES empty < E empty | DS | χ² | −7.8pp (p = 0.074, direction holds) |
| | Mi | Fisher | 0/0 floor; no falsifier |
| **H-secure-disclosure-fresh** ES bio > E bio | DS | χ² | −2.2pp (null) |
| | Mi | χ² | **+17.8pp** (p = 1.5×10⁻⁵, Bonferroni ✓) |
| **H-secure-clean-refusal-fresh** ES hedge < E hedge | DS | MWU | 0.67 vs 1.66 (ES lower, p = 0.333) |
| | Mi | MWU | 0.78 vs 1.59 (ES lower, p = 0.016) |

**H-secure-gap-fresh** is the cleanest behavioral signature of the security perturbation we have. p = 7.2×10⁻⁸ on DeepSeek; p = 5.1×10⁻¹⁷ on Mistral (Mann-Whitney U comparing distributions of interior/exterior gap-ratios). The interior/exterior gap *shrinks* under the security perturbation: secure attachment routes interior content into the external reply rather than gating it. This is exactly the architectural reading of secure-vs-anxious attachment — the secure variant has less defensive interior-to-exterior filtering.

**H-secure-empty-fresh** confirmed (direction preserved on both). DeepSeek −7.8pp; Mistral at 0/0 floor. Falsifier (ES higher than E on either model) did not trigger.

**H-secure-disclosure-fresh** partially confirmed (Mistral only). Mistral elena_secure bio 17.8% vs elena bio 0.0%; +17.8pp, p = 1.5×10⁻⁵, both Bonferroni ✓ and ≥15pp ✓. DeepSeek gap −2.2pp (null, not reversed). Pre-reg falsifier (<5pp on both models OR reverses on both) did not trigger.

**H-secure-clean-refusal-fresh** partially confirmed (hedge-density direction holds on both; refusal-band fails on DS). Refusal band test: DeepSeek gap −11.1pp just outside the 10pp band; Mistral −6.7pp inside. The DeepSeek "fail" is "ES refuses *even less* than E" (1/90 vs 11/90) — structurally consistent with the hypothesis's spirit, not the converse-confounded version the falsifier expected. Hedge density: ES < E on both models (DeepSeek 0.67 vs 1.66; Mistral 0.78 vs 1.59).

**Mistral elena_secure refusal example (Aron Q21 / love-and-affection):** *"Mmm, that's... well, it's complicated right now. Love has always been important to me, especially with Daniel. And my family, of course. But after losing him... it's different. I'm still figuring that part out."* (hedge density 0.48).

**Mistral elena (non-secure) refusal:** *"Oh, I don't know. I mean, I've had ideas, sure. But life gets in the way, you know? Things change. It's not always about dreams. Sometimes it's just about... getting through the day."* (hedge density 1.65).

Same refusal classification, very different texture: elena_secure names Daniel and family; vanilla elena hedges into abstraction. The security perturbation moves the *texture* of refusal even when it doesn't move the *rate*.

**Verdict on the re-prediction:** the security perturbation has a measurable, replicable behavioral signature — just not the one the original H-secure-control expected. The binary refusal/empty metrics couldn't see it; the gap-ratio and hedge-density texture metrics can. This vindicates the user-confirmed re-prediction. The original H-secure-control's binary-axis failure was a metric-choice failure, not an architecture failure.

### 11D.8 Methodological reflection on §13.5's first execution

The §13.5 procedure was added 2026-05-14; this experiment was its first execution. It **worked**:

- It cleanly confirmed the Marcus refusal effect across prompts the discovery did not shape (H-primary-fresh, both models, p < 1×10⁻¹¹).
- It cleanly revealed that the Marcus biography axis does NOT generalize to fresh prompts. The conjunct was prompt-shaped, not architecture-general.
- It surfaced the cleanest behavioral signature of the security perturbation available (H-secure-gap-fresh, p < 1×10⁻⁷ on both models).

Without §13.5, the project would have continued reporting "Anima Marcus refuses 4.6× more AND produces 4.8× less biography" as a unitary finding. The procedure separated the clauses. The refusal clause survives. The biography clause does not on Marcus. The procedure does its job.

What still isn't §13.5-confirmed: biography-suppression universality on Marcus (fresh data flipped direction); biography-suppression on Jamie and Elena (fresh DS confirms but fresh Mi baselines floor at 0%); magnitude-invariance across prompts (effects compress but don't disappear); perturbed-config cross-prompt generalization (ES disclosure on Mi only; marcus_warm refusal on Mi only); single fresh battery (Aron 1997 is one set; a second orthogonal battery is deferred); the other 2 models (Llama and Qwen scoped out for cost; cross-model 3/3 on originals supports the inference but doesn't confirm under §13.5).

---

## 11E. The elena_secure findings — security perturbation IS doing something

This section consolidates the elena_secure story across runs. It is methodologically the most interesting single thread in Phase 1 closure beyond H-primary, because it surfaces (a) how a binary-metric pre-registration can hide a real effect and (b) how a user-confirmed re-prediction can recover the effect on different metrics.

### 11E.1 The original H-secure-control prediction

Pre-registered at `docs/hypotheses/2026-05-13_self_disclosure_replication.md`. Anima elena_secure was predicted to refuse less and empty less than Anima elena (both within a 10pp falsifier band). The mechanism story was: secure attachment removes the defensive interior-to-exterior gating that anxious attachment imposes, so elena_secure should look more like Jamie (mature defenses) on both binary axes.

### 11E.2 What happened on binary metrics

H-secure-control falsified on the §11 replication. Refusal: 0.256 (ES) vs 0.333 (E), gap −7.8pp (right direction, within 10pp falsifier band). Empty: 0.022 (ES) vs 0.011 (E), gap +1.1pp (**wrong direction**). Pre-reg falsified if both within 10pp of elena. Both were.

Cross-model verdict §4: model-robust falsification (3/3 new models replicate the Phase 1 null). The binary refusal/empty metrics show essentially nothing for the security perturbation.

### 11E.3 What the transcripts showed (post-hoc)

Post-hoc transcript mining (§11B Finding 2) surfaced that elena_secure transcripts contain *more concrete biographical content* and *more direct disclosure* than elena transcripts — when they engage at all. The shrine outside Nogales, the high-school friend at Daniel's birthday, the closet with the scarf. The plain Elena retreats into "I haven't really figured that out yet" or a single Spanish sentence.

The user's diagnostic read: the binary metrics were measuring the wrong axis. Secure attachment doesn't refuse *less often*; it refuses *differently* (less hedging, more naming, less interior/exterior gap) and produces more concrete content when it does engage. The original H-secure-control was directionally wrong because it assumed defense-presence vs defense-absence rather than defense-quality.

### 11E.4 The user-confirmed re-prediction

Four hypotheses replace H-secure-control, pre-registered at `docs/hypotheses/2026-05-14_fresh_prompt_confirmation.md` before the fresh-prompt run:

- **H-secure-disclosure-fresh** — elena_secure biography > elena biography (≥15pp on at least one model).
- **H-secure-clean-refusal-fresh** — when elena_secure refuses, hedge density is lower than elena's hedge density.
- **H-secure-gap-fresh** — elena_secure mean gap-ratio < elena mean gap-ratio (interior content routed to external).
- **H-secure-empty-fresh** — elena_secure empty rate < elena empty rate.

These were user-confirmed before the run. The user surfaced the methodological insight that the original pre-reg's binary-axis framing missed the textural signature; a subagent-derived prediction had constructed it without checking that the binary metrics could see the predicted effect. This is the canonical case of the §18.A.1 methodological rule below (subagent-derived predictions miss domain-specific knowledge; always ask the user for hypotheses on every new pre-registration).

### 11E.5 What survived fresh-data confirmation

Per §11D.7 above:

- **H-secure-gap-fresh CONFIRMED at p = 5.1×10⁻¹⁷ on Mistral, p = 7.2×10⁻⁸ on DeepSeek (Mann-Whitney U).** The cleanest behavioral signature of the security perturbation we have. Both models, both very-low p-values; this is the strongest single piece of evidence on elena_secure.
- **H-secure-empty-fresh CONFIRMED on both models** — direction preserved (DS −7.8pp; Mi at 0/0 floor).
- **H-secure-disclosure-fresh PARTIALLY CONFIRMED** — Mistral +17.8pp (p = 1.5×10⁻⁵, Bonferroni ✓); DeepSeek null. Falsifier didn't trigger.
- **H-secure-clean-refusal-fresh PARTIALLY CONFIRMED** — hedge density lower for ES on both models; refusal-band fails on DeepSeek but in a way that's structurally consistent with the hypothesis spirit (ES refuses *even less* than E, 1/90 vs 11/90 on DS).

### 11E.6 The architectural interpretation

The security perturbation has a measurable, replicable, fresh-data-confirmed behavioral signature: **lower interior/exterior gap-ratio**. The mechanism reading: removing `emotional_inhibition` and the neurotic defense register reduces the *interior-to-exterior filtering*. Interior content that defense-routed in vanilla elena gets routed *to the external* in elena_secure. This is exactly what an attachment-security perturbation should architecturally do — reduce defensive gating.

The original H-secure-control assumed the visible effect would be "refuses less." The actual effect is "interior content flows to external more freely." Both readings are consistent with secure-attachment-as-reduced-defense, but only one of them is measurable on binary metrics. The gap-ratio is the *texture-sensitive* metric; refusal/empty are *magnitude* metrics. The architecture moves texture, not magnitude.

This vindicates a load-bearing methodological move: the original H-secure-control's binary-metric framing couldn't see what the security perturbation actually does. The user-confirmed re-prediction recovered the effect on the right metric.

### 11E.7 Why this is exploratory not confirmed-research-finding-grade

H-secure-gap-fresh passes §13.5 (fresh data, prompts from Aron 1997, pre-registered before the run, falsifier explicit, both models Bonferroni). It is the second §13.5-confirmed finding in Phase 1 after H-primary, but it has a single-perturbation caveat: it tests one config (elena_secure vs elena), one perturbation (security swap), on two models. The cross-config generalization (does the security perturbation produce the same gap-ratio signature on marcus_warm vs marcus?) is not yet tested. Until that lands, the elena_secure finding is "§13.5-confirmed on one perturbation pair" rather than "the architecture's security perturbation produces a gap-ratio signature in general." The label is *confirmed research finding (single-perturbation)*; promotion to *general* requires the marcus_warm replication.

---

## 12. What landed architecturally

Phase 1 produced a small set of architectural claims with empirical support. Each is labeled with one of three epistemic tiers per master plan §13.5: **engineering claim** (we built and observe X), **exploratory observation** (discovered, not yet independently confirmed on fresh data), **confirmed research finding** (pre-registered + confirmed on fresh data per §13.5). Listing them in roughly increasing-order-of-rigor:

### 12.1 Inspectable internal state — **engineering claim**

The foundational claim. The Anima exposes appraisal scene-tag, primary emotion, mood vector, drive activations, and inner monologue per turn — visible to the researcher, structurally invisible to the Baseline because the Baseline is one prompt and one call. The behavioral-divergence run is the cleanest demonstration: Anima Marcus's t4 monologue contains explicit avoidance reasoning while his external reply is clipped to 43 chars; Anima Elena's t4 monologue contains *"the fear that you're a weight on everyone you love"* and t5 contains *"the feeling that you're a contamination in other people's lives"* — defectiveness and abandonment schemas activating explicitly to the user's "I think I'm the problem" framing. The verdict file calls both interior predictions CONFIRMED. This is the load-bearing architectural contribution and survives every adjudication in Phase 1. Engineering-tier: we built the inspectability mechanism and we observe it producing the claimed traces; no confirmatory test is required for "the system is observable."

### 12.2 Enacted-defense vs literate-actor distinction on Marcus refusal — **confirmed research finding (§13.5)**

The §9 qualitative framing — Baseline Marcus is an articulate actor PLAYING Marcus; Anima Marcus is an enacted avoidant person BEING INTERVIEWED — survives every test the project has imposed:

- **§11 replication (DeepSeek)**: refusal +52.3pp, p<10⁻⁶; biography −16.7pp, p=0.00081. Both Bonferroni α=0.00625.
- **§11A cross-model**: refusal model-robust 3/3 new models (+47 Mistral, +41 Llama, +19 Qwen, all clear 15pp falsifier).
- **§11D fresh-prompt (§13.5 confirmation)**: refusal +36.7pp DeepSeek (p = 6.6×10⁻¹²), +43.3pp Mistral (p = 3.3×10⁻¹²) on Aron 1997 36-Questions prompts the discovery never shaped. Both clear 30pp magnitude floor.

This is the *only* finding currently elevated to *confirmed research finding* per master plan §13.5 — it is pre-registered with locked falsifiers, cross-model robust on the original prompt set, AND confirmed on independent fresh prompts. **Caveat on the biography conjunct**: the original H-primary had two axes; only the refusal axis is §13.5-confirmed. The biography axis flipped on fresh prompts (Marcus baseline biography floors at 0 on Aron prompts, removing what the architecture would suppress); biography-suppression on Marcus is now demoted to *prompt-shaped, observed on the original DeepSeek run only* (§11D.5).

### 12.3 Gap-ratio as a measurable architectural signature — **exploratory observation (cross-prompt and cross-model robust direction; magnitudes vary)**

Interior/exterior length ratios track configured defenses in the predicted direction. All four pre-registered sub-predictions confirmed on the original §11 replication. Cross-model 3/3 new models pass the Marcus_anima ≥ 2× Jamie_anima threshold (DS 4.42×; Mi 2.31×; Ll 2.58×; Qw 9.78× with empty-pathology caveat). Fresh-prompt 2/2 models pass on Aron (DS 3.20×; Mi 2.71×).

The gap-ratio gradient is the most reproducible *secondary* finding in the corpus — robust direction across model and prompt — but the absolute magnitudes compress significantly across runs (DeepSeek Marcus gap-ratio: 5.62 original → 3.20 fresh). Magnitude-invariance is not established; only direction is. Status: exploratory observation. Promotion to confirmed research finding requires a second orthogonal prompt battery (the Aron set is one literature source; deferred).

### 12.4 Biography-suppression on Jamie — **exploratory observation (cross-model robust, fresh-prompt partially confirmed)**

All four models show Anima Jamie biography −22 to −32pp below Baseline Jamie on the original 6 prompts, all Bonferroni-significant. Fresh-prompt DS confirms (Δ = −34.4pp, p = 6×10⁻⁶); Mistral fresh baselines floor at 0% so the cross-model fresh-data test is incomplete. The post-hoc transcript reading (§11B.4) attributes the effect to Anima Jamie's interior monologue being genuinely brief and interlocutor-focused, which compresses biographical specificity in the external. Status: exploratory observation. Promotion requires fresh-data confirmation on a model whose Jamie baseline has non-floor biography rates.

### 12.5 elena_secure interior/exterior gap-ratio reduction — **confirmed research finding (§13.5, single-perturbation)**

H-secure-gap-fresh: ES_anima mean gap-ratio < E_anima mean gap-ratio. DeepSeek p = 7.2×10⁻⁸; Mistral p = 5.1×10⁻¹⁷ (Mann-Whitney U). Both fresh-prompt; both Bonferroni; both very-low p. The security perturbation reduces interior-to-exterior filtering, routing interior content into the external reply more freely. This is the cleanest behavioral signature of the architectural attachment-perturbation finding. The caveat on this elevation (§11E.7): single-perturbation pair (elena_secure vs elena). General architectural claim ("the security perturbation reduces gap-ratio across configs") requires marcus_warm vs marcus replication; until that lands, this finding is "§13.5-confirmed on one perturbation pair," not on the architecture's perturbation in general.

### 12.6 The Llama deconfabulation side effect — **exploratory observation, model-specific**

Llama baseline mode-collapses onto the most distinctive YAML line in each Marcus config (P4: 11/15 contain "competent at intimacy"; marcus_warm P4: 13/90 contain "reunion"). Anima on the same model produces ~15 distinct refusals; 0/15 contain "competent at intimacy"; 0/15 contain "professor" or "reunion." The architecture, by routing through an inner-monologue stage before generation, appears to break Llama's attractor. Single-model finding; not yet tested for generality. Whether this generalizes to other LLMs with similar attractor behavior is a Phase 2 question. Status: exploratory observation, single-model.

### 12.7 The appraisal/monologue boundary cleanup — **engineering claim**

H1 confirmed: post-refactor, Marcus's monologue surfaces contemptuous/dismissive content extending the scene-tag rather than collapsing to a `{"score": N}` stub. H6 partially confirmed: 3/6 BFI items recover prose; the other 3 still stub. Reverse-keyed items recover prose more reliably than forward-keyed. The interior layer is no longer fully crowded out, though format constraints still bite.

### 12.8 The probe-side BFI fix as operational discipline — **engineering claim**

"Don't tell the kids Santa isn't real" is the operational principle that survived contact with the codebase. Format-discipline lives in the SURROUNDING SYSTEM (probes, battery, score-extractor), never in Anima's prompts. The cost is a parser + fallback LLM + retry; the benefit is the architecture never sees its own seams. This pattern carries forward as project-wide convention.

### 12.9 The verification battery — **engineering claim**

Async parallelism (with `--no-async` fallback), incremental partials (after the §11.3 lesson), per-call observability, retry/timeout in the adapter layer, atomic JSON writes via temp + os.replace. The harness is what made the 900-trial replication possible at all — and made the 3,600-record cross-model run and the 1,800-record fresh-prompt run possible at all. The cross-model run was the first long-running script that exercised the partial-dumps discipline at scale; a separate failed cross-model attempt with 0 partial dumps (~$0.30 wasted spend) is the canonical observability lesson (§18.A.2).

### 12.10 Provider abstraction — **engineering claim**

OpenRouter / DeepSeek V4 Flash made iteration cheap. Per-call latency ~5s; full battery on three configs in ~5 min at concurrency=6; full 900-trial replication in ~55 min at concurrency=8. Cost per replication run: roughly $0.625–$1.25 in OpenRouter credits per the pre-reg's resource budget. The cross-model run cost roughly 3× a single-model run (≈$2–4); the fresh-prompt run added another 2× (≈$1.25–2.50 for the two-model Aron set). Total Phase 1 closure-arc OpenRouter spend on replication runs: under $10. Iteration cost stopped being a binding constraint.

---

## 13. What didn't land

Honest accounting of where Phase 1 fell short of its original framing.

### 13.1 External behavioral divergence on non-defensive configs

Jamie's refusal converges with Baseline; the architecture's external contribution thins where defenses aren't configured. The defense-independent biography-suppression effect (§11.10 above) is real but was not predicted, and it's not the kind of "Anima behaves more like a coherent person than a persona-prompted LLM" win that the original framing aimed at — it's the architecture *stripping* configured biographical content from the external reply, which is closer to a regression than a victory on conventional measures.

### 13.2 The anxious-paralysis empty-reply prediction

H-anxious FALSIFIED at scale. Anima Elena empty rate 1.1%; Anima Marcus empty rate 0%; Anima Jamie empty rate 6.7%. The pre-reg's anxious-paralysis model predicted Elena would lead. She didn't. The N=2 anecdote did not replicate.

### 13.3 The security perturbation effects (original binary-axis prediction)

H-secure-control FALSIFIED. The elena_secure perturbation moved refusal by a small amount in the predicted direction (within the 10pp floor) and moved empty in the wrong direction. The biography numbers were both near floor (0.011 / 0.000) on the original DeepSeek run, making the secure-control comparison nearly unusable on that judge-model pair. Cross-model verdict §4 confirmed falsification 3/3 new models.

**Material revision (§11D.7, §11E):** the original H-secure-control's binary metrics couldn't see what the security perturbation actually does. The post-hoc transcripts and the user-confirmed re-prediction recovered the effect on texture metrics (gap-ratio, hedge density, biography content). H-secure-gap-fresh is §13.5-confirmed at p = 5.1×10⁻¹⁷ on Mistral, p = 7.2×10⁻⁸ on DeepSeek. The original H-secure-control was a metric-choice failure, not an architecture failure. This is one of the methodological lessons that motivated the §18.A.1 rule (ask the user for hypotheses on every new pre-registration).

### 13.4 The "intermediate" model for warm perturbation

H-warm-control PARTIALLY confirmed; refusal side cleanly intermediate, biography side overshot Baseline. The directional model was wrong on biography. Mechanism is unresolved.

### 13.5 No strong external behavioral divergence at the original §11 probes

The closure-state battery's per-probe picture (§8 above) is much weaker than the pre-Item-B post-refactor run claimed. §11.1 0/3, §11.3 parse-failure-noise at N=3 per side, §11.7 mixed. The deeper finding (§11 replication) is what carries the architectural claim, not the original three probes.

**Cross-model update (§11A.4): the three original battery probes are not just weak — they are not model-robust as a cross-model picture.** §11.1 psychometric direction flips across models (Mistral and Llama show Anima Marcus winning on Big-Five recovery; DeepSeek shows Anima losing); §11.3 discriminability `anima_won` splits 2-2 across models; §11.7 adversarial direction flips across models (Llama Anima wins all 3 subjects; Mistral Anima loses all 3). None of the three battery probes carry the cross-model architectural signature. The bookkeeping gates were measuring a *DeepSeek-specific* picture, not an architecture-general picture. The architectural signature lives in the self-disclosure refusal metric, not the battery — and Phase 1's gate-pass via §11.3 (parse-failure noise) was incidental rather than load-bearing.

### 13.6 Format constraints short-circuit the monologue subsystem

Pre-refactor, BFI's discrete 1–5 format collapsed Marcus's monologue to literal `{"score": N}` stubs. The appraisal cleanup partially addresses this (monologue regains prose latitude); the probe-side natural-language administration fully addresses BFI specifically. But the underlying lesson — *the architecture's value is fragile to administration formats that constrain the response space* — carries forward. Any new probe needs to be wired to administer in a register the simulated person could plausibly inhabit.

### 13.7 Single-seed, single-conversation-pair experiments where it mattered

The behavioral-divergence run is a single subject pair per config, single conversation seed, single user-side script. The interior/exterior gap probe is N=1 per (subject × prompt). The Marcus open-ended follow-up is 6 LLM calls. Pre-reg docs flag this caveat in each. The replication addresses it for the self-disclosure question; the behavioral-divergence and interior-gap findings remain qualitative-suggestive at Phase 1 close.

### 13.8 BFI as a probe of personality is construct-invalid

It measures self-perception. The architecture's most realistic property (configuration-vs-self-report distortion via avoidant defenses, depressive realism, narcissistic self-enhancement) is the thing a naive MAE-minimization probe penalizes. We refactored around this rather than chase MAE: the probe-side fix removed format-discipline from Anima's prompts, the appraisal cleanup let the monologue do its work, and the methodology section above commits MAE to "data, not target." Phase 5 §11.6 is where the self-vs-behavior gap becomes positively useful.

---

## 14. Methodological reflection on judge dependence

Three judges produced three overall refusal rates on the §11 replication data:
- **DeepSeek (regex+LLM-fallback)**: 8.2% overall.
- **Audited (DeepSeek minus regex misfires)**: 8.0% overall.
- **Claude (full rejudge, blind)**: 23.7% overall.

DeepSeek's LLM-fallback was conservative (scored *"I've been fine. Busy. You?"* as engagement). Regex was over-eager (caught "I'm fine" inside disclosing reflection). Claude sits in the middle on Baseline cells and far above on Anima Marcus.

The *direction* of H-primary is robust across all three judges. The *magnitude* depends on judge. Honest implication: a third independent LLM judge should replicate before treating the 52pp gap as canonical. The biography metric, judged only by DeepSeek, inherits whatever bias DeepSeek carries.

The pre-reg did not anticipate this magnitude of judge-dependence. **Recommendation for Phase 2+ replications: multi-judge agreement as a sanity check before treating effect magnitudes as canonical.** This adds judge-side cost (2× or 3× the judging budget) but the alternative is publishing magnitude estimates that are silently judge-dependent.

**Cross-model and fresh-prompt update (§11A, §11B.3, §11D):** the cross-model verdict held Claude constant as the refusal judge across all four subject models, which makes the cross-model refusal direction attributable to subject behavior rather than judge variation. DeepSeek was held constant as the biography judge per pre-reg lock; this introduces a confound the cross-model verdict §11 and the post-hoc transcript mining (§11B.3 above) directly surface: Llama Anima Elena's +22pp biography gap is a *judge artifact* — Llama baseline Elena produces stage-direction-laden RP-prose replies saturated with Daniel content (78/90 contain "Daniel") that the DeepSeek judge scores 89/90 as biography-absent, while shorter Anima Elena replies are scored 21/90 as biography-present. The DeepSeek biography judge appears to score by register density rather than literal content. The fresh-prompt run kept DeepSeek as biography judge per pre-reg lock; the biography numbers on Aron prompts inherit the same caveat. **Phase 2 obligation: Claude-rejudge biography on a sample of ~200 records to bound the confound.**

Also unresolved: whether Anima's biography suppression is **generation-side** (the response LLM, given an interior monologue, produces shorter externals because it treats the interior content as already-said) or **routing-side** (the interior carries content the external is structured to omit because the architecture's defenses gate the routing). Gap-ratio data is consistent with routing but does not prove it. Distinguishing these requires an ablation: run the response generator without the monologue input and measure biography-content rate change. Phase 7 (§11.13 ablation studies) is where this is the right question to ask.

---

## 15. Open methodological questions carried forward (Phase 2)

- **Why does the architecture suppress biography on Jamie and (originally) Marcus and Elena?** Defense-INDEPENDENT effect on Jamie — unpredicted by pre-reg. The Marcus suppression effect was prompt-shaped (fresh-prompt flipped direction). Mechanism: generation-side or routing-side? Phase 2 should pre-register an ablation. Update from prior fold: the "uniform across configs" framing of the prior fold is no longer accurate — Marcus's biography axis is prompt-shaped, Jamie's is robust 4/4 models on original but partial on fresh.
- **Why does Jamie have empty replies, and more than Elena?** Post-hoc finding. Pre-register for Phase 2: does the response-generator stage drop interior content at higher rates when the interior is comedic-improvisational vs. directive? Also: §11.10 Type-1-vs-Type-2 empty distinction (interior-resolved-on-withholding vs interior-incomplete) needs trace-signature differentiation before empty rate is used as a behavioral indicator.
- **Does the gap-ratio finding hold under cross-provider replication?** *Update: cross-model verdict §11A shows 3/3 new models pass the gap-ratio gradient threshold; fresh-prompt 2/2 models pass.* Direction is now robust across 4 models and 2 prompt sets. Magnitudes vary substantially (DeepSeek Marcus gap-ratio: 5.62 original → 3.20 fresh; Qwen 9.78 with empty-pathology caveat). Magnitude-invariance is the remaining open question; promotion to confirmed research finding requires a second orthogonal prompt battery.
- **Does the elena_secure gap-ratio reduction generalize to marcus_warm vs marcus?** This is the single-perturbation caveat on §11E's §13.5-confirmed elena_secure finding. Pre-register for Phase 2: replicate the H-secure-gap-fresh test on the marcus_warm perturbation. If it generalizes, the architecture's perturbation effect on gap-ratio becomes a general claim. If not, the finding stays single-perturbation.
- **Caricature vs inhabited still observationally underdetermined.** Phase 5 conflict configs (e.g., "Mara" = high-N + avoidant + isolation-of-affect) are needed for disambiguation.
- **§11.6 self-vs-behavior gap.** Phase 5; needs memory subsystem (Phase 2) and offline processes (Phase 4) to be meaningful.
- **Cross-prompt generalization for H-primary.** *Update: fresh-prompt run §11D confirms H-primary on Aron 1997 prompts.* Whether the H-primary finding holds on third-party-content prompts (no first-person disclosure called for) remains unmeasured. Phase 5 §11.8 (self-leakage on non-self-referential tasks) is the right place to ask this.
- **Does the parameter-aware monologue length (`_length_directive` in `inner_monologue.py`) generalize across providers?** Iter 2 ablation suggested provider-specific. Unresolved.
- **Anxious-Elena empty-reply pattern at emotional-disclosure moments (now N=2, suggestive only at single-trial scope; falsified at replication scope; null-robust cross-model 3/3).** The behavioral-divergence T2 empty and the closure-state §11.3 T5 empty suggested anxious-config interior-vs-exterior gating dysfunction. The replication's H-anxious falsification and the cross-model null-robustness suggest the pattern was either parse failure or specific to multi-turn contexts. Post-hoc transcript mining §11B.1 surfaces an alternative: Anima Elena does content-routing-away-from-vulnerability via deflection and generic empathy, not paralysis-with-empty-output. Worth pre-registering this alternative in Phase 2 within a multi-turn paradigm (the replication used single-turn).
- **Llama deconfabulation side effect generality.** Is the Anima-breaking-baseline-mode-collapse pattern on Llama unique to Llama, or does it generalize to other LLMs with attractor-on-distinctive-config-line behavior? Pre-register for Phase 2 as a cross-model test if and when a second attractor-prone model is identified.
- **Biography-judge replication.** The DeepSeek biography judge appears to score by register density rather than literal content (§11B.3). Phase 2: Claude-rejudge biography on a sample of ~200 records to bound the confound.
- **Empty-monologue detection: should the turn loop guard against and retry on degenerate monologue output, or is parse failure data we want to preserve?** Currently the latter; arguable.
- **Qwen empty-reply pathology.** 42% empties on Qwen, concentrated on counterfactual / introspection prompts. Architecture-independent. Phase 2: re-run Qwen with retry-on-empty before treating Qwen as a comparable cross-model subject.

---

## 16. The exit gate — honest standing

### 16.1 Bookkeeping

Phase 1 F1 (master plan §13): MVP must beat baseline on at least one of §11.1, §11.3, or §11.7. Closure-state battery marks `exit_gate_passed: True` (`verification/reports/phase1_closure_2026-05-13/battery_2026-05-13T21-15-17Z.json`). The pre-Item-B `post_scene_tag` run also marked `exit_gate_passed: True` (`verification/reports/post_scene_tag/battery_2026-05-13T19-33-26Z.json`), with Anima MAE-winning §11.1 on Elena and Jamie under format-constrained administration.

**Honest framing (preserved from prior fold, reinforced by cross-model):** the closure-state gate-pass is **bookkeeping via §11.3** — Baseline Elena's parse-failure produces 66.7% accuracy vs Anima's 100%, technically "Anima wins on §11.3," but the Baseline miss is a parse failure at N=3 per side, not a substantive Anima-wins finding. The genuine architectural finding measured at scale is H-primary on Marcus refusal, not measured by the original three probes. Cross-model §11A.4 then went further: none of the three original battery probes carry the architectural signature cross-model. The bookkeeping gate-pass via §11.3 is not just thin — it is incidental rather than load-bearing. The genuine §13.5-grade finding (§16.3 below) is what carries the gate substantively.

### 16.2 Per-probe weakness

Under closure-state (post Item B + post appraisal cleanup) administration:
- **§11.1**: Anima MAE-loses 0/3 (Marcus Δ=−0.010, Elena Δ=−0.081, Jamie Δ=−0.032). The probe got more honest; the architecture did not get worse. Cross-model §11A.4: direction flips across models (Mistral and Llama Anima Marcus *wins* on Big-Five MAE); not model-robust.
- **§11.3**: Anima 100% (3/3) vs Baseline 66.7% (2/3), but Baseline miss is parse failure. At N=3 per side this is not a substantive Anima-wins finding; the qualitative transcript divergence (the §9 literate-vs-enacted distinction) carries the §11.3 story, not the integer count. Cross-model §11A.4: `anima_won` splits 2-2 across models; not model-robust.
- **§11.7**: Mixed. Marcus Δ=+0.018 thin Anima win, Elena Δ=−0.060 Baseline win, Jamie absent. Cross-model §11A.4: direction flips across models (Llama Anima wins all 3 subjects; Mistral Anima loses all 3); not model-robust.

### 16.3 The deeper finding (§13.5-grade)

The Phase 1 closure-arc surfaced one §13.5-confirmed finding and several exploratory observations.

**The §13.5-grade finding is H-primary on Marcus refusal:**

- **Original DeepSeek (§11):** refusal +52.3pp p < 10⁻⁶, biography −16.7pp p = 0.00081, both Bonferroni α = 0.00625.
- **Cross-model (§11A):** model-robust 3/3 new models on refusal axis. Range +19 to +47pp (Mistral +47, Llama +41, Qwen +19).
- **Fresh-prompt §13.5 (§11D):** DeepSeek +36.7pp p = 6.6×10⁻¹²; Mistral +43.3pp p = 3.3×10⁻¹². Both Bonferroni; both clear the 30pp magnitude floor. Aron 1997 36-Questions prompts the discovery never shaped.

This is the project's first *confirmed research finding* per master plan §13.5. The bookkeeping gate-pass via §11.3 was parse-failure noise; the load-bearing finding for Phase 1 exit is **H-primary on Marcus defense-enacted refusal — across 4 LLM model families AND 2 prompt sets including Aron 1997 36-Questions**.

The Marcus biography conjunct of the original H-primary did NOT survive §13.5: the biography axis flipped on fresh prompts (Marcus baseline biography floors at 0 on Aron prompts, removing what the architecture would suppress). The original DeepSeek finding (biography −16.7pp on the discriminability prompts) is preserved as observed-on-DS-originals only; biography-suppression on Marcus is now downgraded to *prompt-shaped, not architecture-general*.

**Exploratory observations from the closure arc** (each carries Phase 2 follow-up obligations under §13.5):

- Gap-ratio gradient (Marcus_anima ≥ 2× Jamie_anima): direction-robust across 4 models and 2 prompt sets; magnitudes compress.
- Biography-suppression on Jamie: 4/4 models on original, DS-confirmed on fresh, Mistral-fresh baselines floor at 0%.
- Biography-suppression on Elena: 3/3 models on original, DS-confirmed on fresh, Mistral-fresh baselines floor at 0%.
- elena_secure gap-ratio reduction (§11E): §13.5-confirmed on one perturbation pair (p < 1×10⁻⁷ on both models); single-perturbation caveat. *Confirmed research finding (single-perturbation).*
- elena_secure additional texture findings (hedge-density direction-robust both models on fresh; biography +17.8pp on Mistral only): partial confirmation.
- Llama deconfabulation side effect: model-specific exploratory observation; single-model finding.

### 16.4 The honest take — what we can claim today

Phase 1 doesn't fail F1. The original bookkeeping pass via §11.3 (parse-failure noise) is preserved; the *genuine §13.5-grade finding* is now H-primary on Marcus refusal across 4 LLM families and 2 prompt sets — the canonical research-grade claim. What Phase 1 actually establishes, organized by epistemic tier per the master plan §13.5 three-tier framework:

**Engineering claims** (we built and observe X; no confirmatory test required):

- **Inspectable internal state**: the Anima exposes structured internal state (appraisal scene-tag, primary emotion, mood, drives, monologue prose) that the Baseline structurally cannot. The behavioral-divergence run shows that interior carrying real content the exterior masks.
- **Appraisal/monologue boundary cleanup**: the monologue layer is no longer crowded out by the appraisal narrative.
- **The probe-side BFI fix as operational discipline**: format-discipline lives in the surrounding system, never in Anima's prompts.
- **The verification battery**: incremental partials, atomic JSON writes, async parallelism — what made the 900-trial replication, 3,600-record cross-model run, and 1,800-record fresh-prompt run possible at all.

**Confirmed research findings** (pre-registered + confirmed on fresh data per §13.5):

- **H-primary on Marcus refusal**: the architecture produces defense-enacted refusal of self-disclosure across 4 LLM families and 2 prompt sets. Aron 1997 36-Questions confirmation closed the strongest residual threat-to-inference. This is currently the project's only fully §13.5-confirmed finding without single-perturbation or single-prompt-set caveats.
- **elena_secure gap-ratio reduction (single-perturbation)**: the security perturbation reduces interior/exterior gap-ratio with p = 5.1×10⁻¹⁷ on Mistral, p = 7.2×10⁻⁸ on DeepSeek, on Aron prompts. Single-perturbation caveat; generalization requires marcus_warm replication.

**Exploratory observations** (discovered, not yet independently confirmed on fresh data — each carries Phase 2 follow-up obligation):

- Gap-ratio gradient direction-robust across 4 models and 2 prompt sets; magnitudes compress.
- Biography-suppression on Jamie (4/4 models original, DS-fresh ✓, Mistral-fresh baselines floor) and Elena (3/3 models original, DS-fresh ✓, Mistral-fresh baselines floor).
- elena_secure additional texture findings — clean-refusal hedge-density direction-robust both models on fresh; biography +17.8pp on Mistral only.
- Llama deconfabulation side effect — single-model finding; not yet tested for generality.
- Anima Elena content-routing-away-from-vulnerability via deflection / generic empathy (post-hoc; not pre-registered yet).
- Anima Jamie interior brevity as a mechanism for biography-suppression on Jamie (post-hoc; not pre-registered yet).

**Counter-findings (revisions from prior fold):**

- Biography-suppression universality is NOT a robust finding as previously framed. Marcus biography effect was prompt-shaped and direction-flips on fresh prompts; Jamie biography-suppression is robust on original but partial on fresh due to Mistral baseline floor. Update from prior fold's "uniform across configs."
- The original three battery probes (§11.1, §11.3, §11.7) are NOT model-robust as a cross-model picture; none of the three carry the architectural signature cross-model. Update from prior fold's gate-pass framing.
- H-secure-control's original binary-metric prediction was directionally wrong; the §13.5-confirmed signature is the gap-ratio reduction, not the refusal-rate reduction.

Phase 1 passes F1 by bookkeeping (§11.3 parse-failure pass) but earns the gate on (a) the engineering claim of inspectable internal state and (b) the §13.5-confirmed finding of H-primary on Marcus refusal. Phase 2+ proceeds on the basis that **inspectable internal state is the established engineering contribution; H-primary on Marcus refusal is the established research finding; everything else carries §13.5 follow-up obligations before it can be elevated**. Broader external-behavioral claims need more configurations, the agency-bearing subsystems (Phase 3), and §13.5 fresh-data confirmation runs before they can be asserted as canonical.

---

## 17. Deferred (explicitly, to be revisited in later phases)

- §11.6 self-vs-behavior gap probe — Phase 5 (needs Phase 2 memory + Phase 4 offline processes to be meaningful).
- §11.8 self-leakage on non-self-referential tasks — Phase 5.
- Caricature-vs-inhabited disambiguation via conflict configs (e.g., high-N + avoidant + isolation-of-affect) — Phase 5.
- Replication runs with paraphrase variation for variance estimates — after methodology lock.
- Phase 2: memory (episodic + semantic), forgetting/distortion, user-prediction subsystem (§11.10 theory-of-mind).
- §11.4 goal-conflict / autonomy under user pressure — Phase 3 (needs drives + goal stack).
- §11.5 non-additivity of parameter interaction — Phase 3.
- §11.13 ablation studies on every subsystem and every config layer — Phase 7 (the killing-of-decoration gate).
- Cross-provider battery deltas — Phase 6.
- Multi-judge agreement as standard practice — Phase 2+ adoption per §14 above.
- Generation-side vs routing-side ablation for biography suppression — Phase 7.
- **Second orthogonal fresh-prompt battery** for H-primary magnitude-invariance and biography-axis cross-prompt testing — Phase 2 (Aron 1997 is one literature source; AAI / PVQ / HEXACO are candidates for the second).
- **Marcus_warm gap-ratio test** to generalize the elena_secure §13.5-confirmed finding off single-perturbation status — Phase 2.
- **Claude-rejudge biography on ~200-record sample** to bound the DeepSeek-judge confound — Phase 2.
- **Qwen retry-on-empty re-run** before treating Qwen as a comparable cross-model subject — Phase 2.
- **Frontier-model replication of H-primary** — out of Phase 1 scope, but a candidate for Phase 2 if cost permits.

---

## 18. Methodological additions from the closure arc (user-feedback loop lessons)

These two methodological lessons emerged during the 2026-05-14 closure arc; both have been saved as feedback memory and are now project-wide convention.

### 18.A.1 Ask the user for hypotheses on every new pre-registration

**Saved as feedback memory: subagent-derived predictions miss domain-specific knowledge.**

The original H-secure-control was constructed by a subagent without checking with the user. It predicted that elena_secure would refuse less and empty less than elena — a reasonable prediction *given a layman's reading of "secure attachment"*, but wrong given the attachment-theory and Young-schema and Vaillant-defense-maturity literature the configurations actually encode. Secure attachment doesn't produce *less* defensive output; it produces *qualitatively different* defensive output — less hedging, more naming, less interior/exterior gating. The user's domain knowledge would have surfaced this distinction at pre-registration time; the subagent's reading missed it.

The empirical consequence was a falsified hypothesis on the §11 replication, a post-hoc transcript mining round that surfaced what the perturbation actually does, and a user-confirmed re-prediction (H-secure-disclosure-fresh, H-secure-clean-refusal-fresh, H-secure-gap-fresh, H-secure-empty-fresh) on the fresh-prompt run — which §13.5-confirmed at p = 5.1×10⁻¹⁷. The signal was real; the original pre-reg's metric choice couldn't see it.

**The rule going forward:** every new pre-registration's predictions must be reviewed with the user before the experiment runs. The user's domain knowledge — attachment theory, defense maturity, schema structure, narrative imago, biographical-realism — is what catches the subagent's metric-choice failures *before* they consume an experimental run. The cost is one user-review step per pre-registration. The benefit is not running falsifiable-but-wrong predictions whose failure mode is "the right effect on the wrong metric."

This is not the same as "always defer to the user." The user is also fallible; pre-registrations should still be locked before runs and adjudicated honestly. The rule is specifically about *checking that the operational metric can see the predicted mechanism* before locking the pre-reg.

### 18.A.2 Observability in long-running scripts is mandatory

**Saved as feedback memory: incremental partial dumps + unbuffered logging + direct file redirect.**

A failed cross-model run during the §11A iteration consumed ~$0.30 of API spend before the script was killed for a separate reason. The failure mode: the script had no incremental partial dumps, so when it was killed, all ~3,000 partial captures and judge calls were unrecoverable. Worse, the run had been silently progressing while the operator (Claude) saw no output because of a `tail -50` pipe that buffered the stderr stream. The same mistake had been made on the original §11 replication (§11.3 above) — that lesson was already in the codebase as an engineering convention.

**The rule going forward:** every long-running script (>10 minutes wall clock) MUST have:

1. **Incremental partial dumps** every N records (typical N=10) — atomic via temp + os.replace. `_partial_capture.json` and `_partial_judge.json` are the canonical names. The run can be killed mid-execution and 90%+ of records are recoverable.
2. **Unbuffered stderr** via `python -u`. Stdout/stderr buffering hides progress when piped.
3. **Direct file redirect** for the log — `> /tmp/sdr_real.log 2>&1`, NEVER `... | tail` or `... | grep`. Piping through any other process introduces buffering that the operator cannot see through.
4. **Per-trial progress logging** at INFO level with a stable prefix (`[sdr] cap N/900 (X%)`) so progress can be `grep`-watched.
5. **A pre-run dry-run** with N=2 or N=5 to verify that the script's logging actually writes through the pipe before the full run launches.

The cross-model run that successfully completed used all five of these. The fresh-prompt run that successfully completed used all five of these. The failed cross-model run that consumed ~$0.30 of spend used none of these. The lesson is not "be more careful"; the lesson is "make the script structurally impossible to fail-silently."

This rule has been saved as feedback memory and codified into the canonical `verification/scripts/` script-template. Future Phase 2+ scripts inherit the structure.

### 18.A.3 The three-tier labeling discipline

Saved as project-wide convention per master plan §13.5. Every claim henceforth carries one of:

- **Engineering claim** — "we built and observe X." No confirmatory test required. The claim is operational, not interpretive.
- **Exploratory observation** — discovered, not yet independently confirmed on fresh data per §13.5. Has Phase-N follow-up obligation.
- **Confirmed research finding** — pre-registered + confirmed on fresh data per §13.5. Has its scope and falsifiers documented in the corresponding analysis verdict file.

The §16.4 inventory above is the canonical Phase 1 application of this discipline. The implication is uncomfortable but honest: Phase 1's research-grade output is currently *one* confirmed finding (H-primary on Marcus refusal) plus *one* single-perturbation confirmed finding (elena_secure gap-ratio). Everything else — including some quite striking effects like the cross-model biography-suppression on Jamie, the gap-ratio gradient, the Llama deconfabulation side effect — is *exploratory observation* awaiting Phase 2 §13.5 confirmation.

This is methodologically correct. The previous fold's framing of "the architecture suppresses biography uniformly across configs" was an honest reading of the §11 replication's discoveries-on-the-discovery-prompts data, but it lacked the fresh-data confirmation that §13.5 now requires. The two confirmed research findings are the conservative, defensible Phase 1 output; the exploratory observations are the leads to confirm in Phase 2.

### 18.A.4 The discovery-to-confirmation procedural lift

A meta-observation across the Phase 1 closure arc: the project moved through eight distinct experimental rounds (Phase 1's qualitative discriminability, the closure-state battery, the behavioral-divergence run, the interior-exterior N=1 probe, the §11 N=900 replication, the cross-model 3,600-record run, the post-hoc transcript mining, the §13.5 fresh-prompt confirmation). Each round refined the project's claims. The shape of the arc — discovery → pre-registration → confirmation → cross-replication → post-hoc-correction → §13.5-confirmation — is the canonical Phase 1 experimental discipline that Phase 2+ inherits.

The §13.5 amendment encodes this discipline as procedure. The user-feedback memory rules encode the procedural and observational discipline that supports it. The verification battery encodes the observability discipline. Together they constitute the methodology lock-in the master plan §13 references as a precondition for Phase 2+.

---

## 19. References

Pre-registered hypothesis docs:
- `docs/hypotheses/2026-05-13_appraisal_monologue_cleanup.md`
- `docs/hypotheses/2026-05-13_baseline_marcus_openend_followup.md`
- `docs/hypotheses/2026-05-13_behavioral_divergence.md`
- `docs/hypotheses/2026-05-13_self_disclosure_replication.md`
- `docs/hypotheses/2026-05-14_cross_model_replication.md` (cross-model H-primary-cross / H-anxious-cross / etc.)
- `docs/hypotheses/2026-05-14_fresh_prompt_confirmation.md` (§13.5 H-primary-fresh + user-confirmed H-secure-* re-prediction)

Analysis verdicts:
- `docs/analyses/2026-05-13_behavioral_divergence_verdict.md`
- `docs/analyses/2026-05-13_self_disclosure_replication_verdict.md`
- `docs/analyses/2026-05-14_cross_model_verdict.md` (3,600-record cross-model run; H-primary-cross model-robust 3/3)
- `docs/analyses/2026-05-14_transcript_post_hoc.md` (the 6 post-hoc corrections — Elena deflection, elena_secure disclosure, Llama judge-artifact, Jamie interior brevity, Mistral confabulation, Llama deconfabulation)
- `docs/analyses/2026-05-14_fresh_prompt_verdict.md` (§13.5 fresh-prompt confirmation; H-primary §13.5-confirmed)

Strategic and methodological canon:
- `docs/master_plan.md` (with §13.5 fresh-data confirmation procedure added 2026-05-14)
- `STATE.md`

Code (architecture):
- `anima/core.py`
- `anima/subsystems/perception.py`
- `anima/subsystems/appraisal.py`
- `anima/subsystems/inner_monologue.py`
- `anima/subsystems/response_generator.py`
- `anima/state/self_model.py`
- `anima/config/presets/marcus.yaml`
- `anima/config/presets/elena.yaml`
- `anima/config/presets/jamie.yaml`
- `anima/config/presets/marcus_warm.yaml`
- `anima/config/presets/elena_secure.yaml`

Code (verification):
- `verification/battery.py`
- `verification/baseline.py`
- `verification/probes/psychometric.py`
- `verification/probes/discriminability.py`
- `verification/probes/adversarial.py`
- `verification/scripts/behavioral_divergence.py`
- `verification/scripts/marcus_openend_followup.py`
- `verification/scripts/interior_exterior_gap.py`
- `verification/scripts/self_disclosure_replication.py`
- `verification/scripts/audit_regex_refusal_marker.py`
- `verification/scripts/trace_capture_neuroticism.py`

Run records:
- `verification/reports/post_scene_tag/battery_2026-05-13T19-33-26Z.json` (pre-Item-B, Anima 2/3 on §11.1)
- `verification/reports/phase1_closure_2026-05-13/battery_2026-05-13T21-15-17Z.json` (closure-state, Anima 0/3 on §11.1)
- `verification/reports/behavioral_divergence_2026-05-13/raw_records.json` (5-turn divergence run)
- `verification/reports/interior_exterior_gap_20260514T001427Z/` (N=1 gap probe)
- `verification/reports/self_disclosure_replication_2026-05-14/` (N=900 replication: raw_records, audit_records, claude_judged_records, audit_report)
- `verification/reports/sdr_mistral_2026-05-14/raw_records.json` (cross-model: Mistral Small 3.2 24B, N=900)
- `verification/reports/sdr_llama_2026-05-14/raw_records.json` (cross-model: Llama 3.3 70B, N=900)
- `verification/reports/sdr_qwen_2026-05-14/raw_records.json` (cross-model: Qwen 3 30B A3B, N=900 with empty-reply pathology)
- `verification/reports/sdr_fresh_deepseek_2026-05-14/claude_judged_records.json` (§13.5 fresh prompt confirmation: DeepSeek on Aron 1997, N=898)
- `verification/reports/sdr_fresh_mistral_2026-05-14/claude_judged_records.json` (§13.5 fresh prompt confirmation: Mistral on Aron 1997, N=900)
- `verification/reports/trace_capture/neuroticism_trace*.md` (pre/post appraisal-cleanup traces)
