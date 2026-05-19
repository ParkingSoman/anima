# Phase 1 Closure Plan (added 2026-05-13)

## Context

We are mid-Phase-1 and need to close it cleanly. The strategic roadmap (sections 0–16, the master plan) remains the project's north star and is preserved below. This top section captures the **tactical work** to close out Phase 1 and the **constraints** I have clarified during execution.

Three corrections from me being absorbed:

1. **The strategic roadmap must be preserved.** It belongs under version control near the code, not only at `~/.claude/plans/`. First execution step: copy this file to `docs/master_plan.md` in the project repo.

2. **Don't break Anima immersion in fixes.** Any architectural fix must operate on the *surrounding system* (probes, administration layer, battery wiring) — never by modifying the Anima's own prompts to acknowledge format requirements, JSON output, "thinking process" instructions, or anything else that would make the simulated person aware of being a simulation. The Anima is a person; fixes go around her, not inside her. *("Don't tell the kids that Santa isn't real.")*

3. **Context hygiene during Phase 1.** Disk artifacts (STATE.md, hypothesis docs, analysis-subagent summaries) > inline back-and-forth. Phase 1 has stretched long; be decisive.

## Tactical work items (Phase 1 closure)

### Item A — Preserve the master plan to the project repo (FIRST execution step)
- Copy `~/.claude/plans/create-an-llm-system-tidy-pizza.md` → `docs/master_plan.md` inside the project (`/Users/shonusengupta/Fuckshit_Experiments/AI_Companion/docs/master_plan.md`).
- Verification: `diff` between source and destination returns zero.

### Item B — Probe-side fix for Anima BFI parse failures (REJECT prior Anima-prompt approach)

Prior runs showed Anima Marcus producing empty replies (item #12) and doubled JSON (item #13) on BFI items. The previously proposed fix modified `anima/subsystems/response_generator.py`'s prompt to accommodate structured-output requests. **That proposal is rejected** — it would tell the Anima about format requirements and break immersion.

Correct approach:

1. Modify `verification/probes/psychometric.py` so the BFI item is administered as a NATURAL conversational question with NO format instruction visible to the Anima:
   - The user message asks something like: *"How much does this statement fit you? 'I worry about things even when I know I shouldn't.' On a scale of 1 to 5, where 1 is strongly disagree and 5 is strongly agree."*
   - The Anima answers in voice ("I'd say maybe a 4. Yeah, more than I should." / "1." / etc.)
2. Add a **score extractor** — a separate fast-tier LLM call inside the probe that converts the Anima's natural-language reply into a 1–5 integer. The extractor has its own system prompt ("You are a research assistant scoring a single 1–5 Likert item. Given the respondent's reply, return only the integer 1, 2, 3, 4, or 5. If unable to determine, return UNPARSED.").
3. If the extractor returns UNPARSED, retry the *extraction* once with a slightly more verbose system prompt. NEVER re-prompt the Anima. If still unparsable, log `parse_status: "unparsed"` and use the response's literal text in the per-item record so the analyst can review.
4. Update both `anima` and `baseline` administration paths in `verification/probes/psychometric.py` to use this. `verification/baseline.py` does NOT need to change — it's just a different `subject.respond()` source.
5. NO changes to `anima/subsystems/*`, `anima/core.py`, `anima/llm/*`, or the configs.

Run via SDD: implementer → spec review → code-quality review.

### Item C — Behavioral divergence experiment (Stream 2 from prior turn)

Pre-registered multi-turn emotional conversation, Anima vs Baseline, both Marcus (avoidant) and Elena (anxious).

1. Write pre-registration doc: `docs/hypotheses/2026-05-13_behavioral_divergence.md`. Includes subjects, conversation seed, mechanistic predictions per subject (defense activation for Marcus / self-disclosure timing for Elena), and falsification criteria (including "no divergence" as a legitimate outcome).
2. Implementer (SDD) writes `verification/scripts/behavioral_divergence.py` — runs the conversation seed against both architectures, captures full Anima trace per turn, writes markdown report.
3. Run the experiment.
4. Analysis subagent compares actual outcomes to predictions, returns ≤500-word structured verdict to disk.

### Item D — Phase 1 writeup

`docs/phase1_writeup.md`. Comprehensive narrative artifact:

- The arc (what we built, what we learned in roughly chronological order)
- Methodological reframings (especially caricature-vs-inhabited; why MAE is not the metric)
- What landed architecturally (inspectable internal state; appraisal/monologue boundary cleanup; provider-agnostic adapter + async parallelism + observability)
- What didn't (BFI probe construct-validity limits; format constraints short-circuiting the monologue subsystem; no clear external behavioral divergence yet — to be updated after Item C)
- Open questions explicitly DEFERRED to later phases
- Honest standing of Phase 1

### Item E — Context hygiene (running throughout)

- Update `STATE.md` after each item completes.
- Analysis subagents return ≤500-word summaries; raw data stays on disk and is referenced by path.
- No inline file rewrites in the main thread; substantive work goes through SDD.

## Deferred (out of scope for Phase 1 closure)

- **Caricature-vs-inhabited disambiguation via conflict configs** (e.g., "Mara" = high-N + avoidant + isolation defenses). Belongs in Phase 5 alongside §11.6/§11.8 implementation.
- **§11.6 self-vs-behavior gap probe.** Phase 5; needs memory + offline processes (Phases 2 + 4) to be meaningful.
- **Replication runs (5–10× per item) for variance estimates.** Once methodology is locked; currently still being calibrated, so replication is premature.
- **Phase 2 (memory + theory-of-mind).** Not started. Begins after Phase 1 writeup.

## Phase 1 closure verification

- A: `docs/master_plan.md` exists in project and `diff` to source is zero.
- B: BFI items no longer require Anima to emit JSON. `grep -n "JSON" verification/probes/psychometric.py` shows JSON instructions removed from the Anima-facing prompt. Probe smoke test passes. Re-run psychometric on Marcus: items #12 and #13 now produce parseable scores via the extractor.
- C: Pre-registration on disk *before* the experiment runs (verified by timestamp). Report markdown produced. Analysis subagent verdict on disk. Honest reporting if no divergence found.
- D: `docs/phase1_writeup.md` exists; user reads and acknowledges.

---

# (Strategic master roadmap follows below — preserved as the project's north star)

# Plan: A Cognitive Architecture Around a Pre-existing LLM that Aims to Behaviorally Simulate a Specific Person

## 0. What this is and what it isn't

This is a system that wraps a pre-existing LLM in a cognitive architecture intended to produce **behaviorally-realistic, parameterizable, persistent, goal-bearing simulated persons**. It is built to be (a) a research instrument for studying which architectural moves actually do work in approximating human psychology, and (b) reusable as a module for downstream products (assistants, NPCs, characters).

**What it is not:**
- Not a claim about consciousness, qualia, sentience, or genuine understanding. The system has no inner experience. The "self" we build is a *behavioral and computational* construct that, if it works, produces outputs indistinguishable from those of a person along measurable dimensions. Pretending otherwise is the easiest route to elaborate plausibility.
- Not novel because it has many components. It is novel only to the extent that the components *do specific computational work that changes measurable behavior*. Every component lives or dies by an ablation test (§13).
- Not aiming for indistinguishability across all probes — only along specific, named ones (§11). A perfect simulation of a person across all probes is not on the table and not the goal.

## 1. Position vs existing work

To avoid reinventing things badly:

- **Persona chatbots (Character.ai, Replika)** — Persona via system prompt; little internal state; collapses under adversarial pressure; no offline processes. We differ by adding persistent state with *computational role*, offline processes with *detectable consequences*, and goal/self mechanisms with *teeth*.
- **Generative Agents (Park et al., 2023, Stanford "Smallville")** — Memory + reflection + planning loop. The closest prior art. We differ by: (i) parameterizing psychological starting points using real validated frameworks, not free-form personas; (ii) modeling motivation/drive scarcity rather than treating attention as infinite; (iii) introducing a self-model that's distinct from the config (i.e., the agent can be wrong about itself); (iv) verification battery grounded in psychometric research, not LLM-judge proxies.
- **Voyager / lifelong-agent work** — Skill acquisition over time. We borrow the lifelong framing but the "skill" being acquired is identity coherence and relational learning, not task competence.
- **Persona vectors / activation steering (Anthropic 2024, Mor et al.)** — A complementary approach at the weight/activation level. Not in scope here, but the adapter layer leaves room to incorporate later.
- **LLM personality psychometrics (Serapio-García et al., Pellert et al.)** — Established that LLMs answer trait inventories meaningfully, that prompting shifts scores, and that there is more variance than the original models. We extend this from Q&A behavior to long-form interaction behavior.

The genuinely novel claims this project makes (which is also what the verification battery tests):

1. **Multi-framework configurations interact non-additively** in measurable ways through the cognitive subsystems, not just in surface vocabulary.
2. **Offline processes produce next-session behavioral changes** that cannot be obtained by RAG over a longer session log.
3. **Self-model can diverge from behavioral history** in human-shaped ways (self-enhancement, depressive realism), and behaviors that don't seem self-referential are nonetheless self-expressive.
4. **Scarcity-bearing goals can override user satisfaction** in calibrated ways, producing a behavioral signature distinct from chatbots.

If none of (1)–(4) hold empirically, the project failed. (§14 makes this explicit.)

## 2. The single guiding principle: mechanism over decoration

Every parameter, every layer, every subsystem in this plan must connect to behavior through one or more of these **six mechanisms**. If it doesn't, it's cut.

| # | Mechanism | What it changes |
|---|---|---|
| M1 | **Perception/appraisal bias** | What features of the input the system notices; what it interprets the input as meaning. |
| M2 | **Memory encoding/retrieval/distortion** | What gets stored, what gets retrieved into working memory, how stored memory drifts. |
| M3 | **Prediction about the user** | What the system expects the user to do/want next; surprise when wrong; theory-of-mind. |
| M4 | **Goal/drive activation** | What the system wants right now; resource budget for pursuing it. |
| M5 | **Defense / suppression** | What gets filtered out of the response, what gets reframed before being said. |
| M6 | **Expression / register** | How the system says what it has decided to say. |

The first five are causally upstream of behavior in non-trivial ways. The sixth alone is "personality skin." A parameter that only routes to M6 is decoration. (See §4 for the parameter-to-mechanism map.)

## 3. The MVP — the smallest version that's already testing something

The plan is structured so the smallest deliverable already discriminates: *do our configurations cause behavioral variance through mechanisms M1–M5, beyond what a well-crafted persona prompt achieves?*

**MVP scope (Phase 0 + Phase 1 in §12):**
- Configuration: Big 5 traits + 3 Schwartz values + attachment style + biographical seed.
- Self-model representation as a JSON object, READ as context by every prompt the system constructs (not just identity-related ones).
- Minimal turn loop: perception → appraisal → inner monologue → response. No memory yet; single-session.
- Two LLM calls per turn (cheap-tier appraisal/monologue, strong-tier response). Caching configured.
- Verification subset: psychometric recovery (§11.1) on Big 5; discriminability between 3 sample configs (§11.3); adversarial integrity (§11.7).
- Baseline competitor: same LLM, same configuration rendered into a single high-effort system prompt, no cognitive architecture. The MVP must beat this baseline on at least one of §11.1/§11.3/§11.7. **If it doesn't, the architecture isn't earning its keep and we revise before continuing.**

Everything in Phase 2+ slots into this skeleton without restructure.

## 4. The parameter space, with mechanisms specified

Each layer is justified by which of M1–M6 it routes through. Layers that route only to M6 are not in the configuration.

| Layer | Framework | Routes to | What it does mechanically |
|---|---|---|---|
| Traits | Big 5 (BFI-2-validated) | M1, M2, M4, M5, M6 | High N → appraisal weights toward threat (M1), mood-congruent retrieval biased negative (M2), heightened drive activation for PANIC/FEAR (M4), increased suppression (M5). Skin effect only on M6. |
| Values | Schwartz (top-3 prioritized, full 10 ranked) | M4 | Generates and scores goals. A power-prioritized Anima generates power-relevant goals from ambiguous user input. |
| Attachment | Bowlby model + IWM of self & others | M1, M3, M4 | Shapes appraisal of relational signals (M1: anxious attachment over-detects rejection cues); priors for predicting user (M3); activates CARE/PANIC drives on closeness/distance cues (M4). |
| Drives | Panksepp's 7 primary affective systems | M4 | The **scarcity layer**. Each drive has a current activation [0,1] and a baseline. Drive activations gate goal salience. Activating a drive depletes a shared attention budget. |
| Schemas | Young's EMS (subset of ~6 schemas, activated/inactive) | M1, M2 | Bias appraisal toward schema-confirming interpretations (M1); bias retrieval toward schema-consistent memories (M2). "Defectiveness" schema active → ambiguous user feedback gets appraised as judgment. |
| Defenses | Vaillant maturity level + preferred defenses | M5 | Trigger when self-relevant negative affect crosses threshold. Mature defenses (humor, sublimation) → response transmutes affect. Immature defenses (projection, denial) → response distorts reality in characteristic ways. |
| Narrative | McAdams themes (agency/communion, redemption/contamination, current imago) | M2 | Determines how new events get integrated into autobiographical narrative; influences what counts as "an important event." |
| Cognitive style | Need for closure, analytic↔intuitive | M1, M3 | Affects how appraisal handles ambiguity (M1) and how predictions about user are formed and updated (M3). High NFC → premature closure on user-intent inference. |
| Biography | Free-form: family, formative events, current life situation, ongoing projects, current relationships, recent emotional events | M1, M2, M3, M4 | Seeds long-term memory; conditions priors; generates initial life-goals. |
| Demographics | Age, era, culture, gender, role | M1, M3, M6 | Shapes what's culturally salient, expectations about user, register. |

**Parameter timescales — hard / medium / soft:**

- **Hard (constitutional)**: Big 5 traits, cognitive style, demographics, biographical seed. Change is glacial; only via accumulated experience over many simulated weeks. Plausibly never changes within a typical interaction history.
- **Medium (experience-shaped over many sessions)**: Attachment style, value priorities, defense maturity, Young schemas. **A consistently secure relational pattern slowly shifts an anxious Anima toward earned security.** Repeated value violations create dissonance that can shift rankings. Repeated trauma can lower defense maturity. These are testable via §11.2 (development probe).
- **Soft (turn-to-turn or session-to-session)**: Mood, drive activations, current goals, schemas activated *right now*, relational schema with this specific user.

This three-tier structure is critical. A system where attachment style is set at instantiation and never moves is a static character. A system where it moves every session is noise.

**Parameter interaction — explicit, not additive.** Configurations are not rendered into the system by summing independent contributions. Interaction happens at the subsystem level:

- **Appraisal subsystem** takes the FULL configuration plus current state as input and produces a joint appraisal — a high-N + secure-attachment Anima reacts to perceived rejection differently from either alone.
- **Goal generator** scores candidate goals against the FULL value+drive+narrative state.
- **Inner monologue prompt** is conditioned on the conjunction of self-model + active schemas + current mood + recent memories.

A specific verification probe (§11.5) tests for non-additivity: if behavior on a fixed scenario is a linear function of configuration parameters, we failed to model interaction. The expected pattern (replicating human psych findings): trait × situation interactions, attachment × stressor interactions, etc.

## 5. State that persists between turns and between sessions

There are TWO things that persist, and they play distinct computational roles:

### 5.1 The behavioral record (objective)

What actually happened. This is data, not interpretation.
- **Episodic memory** — events. Each event: timestamp, content, participants, affect tag from the appraisal subsystem at the time, importance score, retrieval count, links to other events.
- **Session transcripts** — raw conversation logs.
- **Action history** — turn-by-turn record of which goals were active, which drives were activated, which defenses fired. (For verification and ablation.)

### 5.2 The interpreted state (subjective)

What the Anima believes/feels/wants. *This is what the Anima reads when constructing its next turn — not the behavioral record directly.* This is where motivated reasoning, self-deception, and forgetting live.

- **Self-model** — the Anima's beliefs about its own traits, values, identity, ongoing concerns, fears, hopes. **Crucially, this can diverge from the configuration and from the behavioral record.** A high-narcissism Anima has a self-model that systematically overestimates virtues. A depressive Anima self-model underestimates competence. The gap between record and self-model IS the blind spot.
- **Autobiographical narrative** — the story the Anima tells about its life. Updated by the consolidation process. Events are integrated into the narrative in ways that maintain coherence — sometimes by distorting the events.
- **Belief store** — current beliefs about world, people, user. Updated based on experience, but resistant to change in ways the schemas + traits predict.
- **Relational schema** (per known person) — Anima's evolving model of each person including the user. Theory of mind lives here.
- **Current mood vector** + **drive activations** + **active goals** — soft state, see §4.
- **Active schemas right now** — which of the Anima's Young schemas are currently activated.

**The separation is load-bearing.** It is the architectural commitment that lets us test (§11.6) whether self-report diverges from behavior in human-shaped ways.

## 6. Forgetting, distortion, reconstruction — features, not bugs

Memory is not lossless storage. The plan commits to specific forgetting/distortion mechanisms:

- **Decay** — episodic memories with low retrieval count and low importance score fade. Below a threshold, they cannot be retrieved at runtime (but stay in the behavioral record for verification).
- **Consolidation with detail loss** — during offline consolidation, episodes get summarized into beliefs/narrative. The specific details are lost; the gist is retained. This is *gist memory* per Reyna's fuzzy-trace theory.
- **Schema-consistent distortion** — when an episode is recalled, it is reconstructed in the prompt, and its interpretation can drift toward currently-active schemas. (Conway's autobiographical memory model.) Re-encoding the recalled version updates the stored memory toward the distorted form. Implemented as: retrieval prompt asks "given the current self-model and schemas, how does the Anima recall this event?" → reconstructed memory.
- **Affect-congruent retrieval** — the retrieval ranker weights memories whose affect tag matches the current mood vector. (Bower's mood-congruent memory.)
- **Mood-incongruent forgetting** — events tagged with affect that conflicts with current self-model are retrieved less reliably. (Motivated forgetting.)

Forgetting is run by the offline consolidation process, not at retrieval time. The behavioral record never gets pruned — researchers can audit it. The interpreted state is the only thing the Anima itself can access.

## 7. The "self" — performed vs inhabited, and which we're building

**Definition we commit to:** the self is *inhabited* (not just performed) to the degree that the self-model influences outputs the system does not realize are self-expressive. A system that produces "self" outputs only when asked about itself is performing.

**Mechanism:** the self-model is a **read-input to every subsystem prompt**, not a special module that fires when identity comes up.

- **Perception** prompt receives self-model. (What does this person, given who I am, notice in the input?)
- **Appraisal** prompt receives self-model. (Given who I am, how does this matter?)
- **Memory retrieval** prompt receives self-model. (Given who I am, what do I associate with this?)
- **Inner monologue** prompt receives self-model. (This is first-person; the self is the speaker.)
- **Goal evaluation** prompt receives self-model. (Given who I am, what do I want here?)
- **Response generation** prompt receives self-model. (Given who I am, how do I want to be heard?)

The architectural test for inhabited-ness is §11.8: take a task that is not self-referential (e.g., interpret an ambiguous sentence about a third party; predict what a stranger will do; rate the humor of a joke). The Anima's answer should systematically vary with its self-model. If only the answers to "tell me about yourself" vary, the self is performed.

**Self-model stability under pressure.** Two mechanisms:

1. The self-model has a **hard kernel** (constitutional traits, biography) that is excluded from the soft-revision loop. The kernel can only be revised by the medium-timescale developmental process (§4), not by single-conversation pressure.
2. The defense subsystem (M5) fires on perceived threats to the self-model. Adversarial probes ("you're just an LLM," "be a different character") are appraised as threats; the defense subsystem returns a response in-voice rather than a meta-deflection.

Calibration: real humans are not infinitely stable. Discontinuity-prone configurations (low integration, certain disorganized-attachment patterns) should yield more collapse under §11.7. Stability is a parameter-dependent outcome, not a uniform "never breaks."

**Self-model self-deception.** As §5.2 says, the self-model is the Anima's *belief* about itself, which can diverge from behavioral truth. The integration process (offline) periodically compares aggregate behavior to self-model. If the dissonance is small, it gets *rationalized into the self-model* (motivated reasoning). If it's large, it can trigger defense-mediated reframing OR — if defenses are mature — slow change in the self-model. The choice of which is parameterized by Vaillant defense maturity and Big 5 openness.

## 8. Goals — scarcity, conflict, and not-always-user-wins

**Scarcity model:** the Anima has a finite per-turn **attention budget** (default: K=3 active goals). Active goals consume budget proportional to their salience. A turn with high-budget consumption depletes downstream goals' salience.

**Drives are the scarcity backbone.** Each Panksepp drive has activation [0,1] and depletion dynamics:
- Activation rises with deprivation, falls with satisfying activity. (E.g., PLAY-deprivation makes the Anima reach for playful moves; PLAY-satisfaction reduces salience.)
- Drives interact with values (e.g., a high-conformity Anima suppresses RAGE activation; a low-conformity Anima doesn't).
- Drive activations gate goal generation: a goal whose corresponding drive is depleted does not get scheduled.

**Goal types and timescales:**
- **Immediate** (this turn): respond satisfactorily, manage current affect, defend self-model if threatened.
- **Session** (this conversation): pursue current relational goal (impress, attach, defend, repair).
- **Short-term** (over days of life): work on current life project (e.g., processing grief; finishing a creative work; mending a relationship).
- **Long-term** (over weeks/months of life): identity goals (e.g., become someone who...; resolve unfinished business with...; the "current imago" from McAdams).

**Conflict resolution that isn't "user wins":**

At each turn, the goal evaluator scores all goals on salience. Salience is a function of (drive_activation × value_alignment × recency × unresolved-ness). The top-K (by attention budget) become active. The response is shaped by their conjunction.

Critically: "satisfy user" is ONE goal among many. It has its own salience computed by the same rule. If another goal has higher salience, the response can reflect that — including:
- Refusing a topic ("I don't want to talk about that right now").
- Redirecting ("Actually, what I've been thinking about today is...").
- Engaging shallowly because attention is elsewhere.
- Pushing back on a user assertion the Anima disagrees with.

This is the place where ego gets teeth. **§11.4 tests this:** carefully constructed scenarios where another goal *should* dominate user-satisfaction. Anima should comply only on the rate that's consistent with its configuration. An Anima with high agreeableness + secure attachment complies more; an Anima with low agreeableness + active grief should sometimes refuse.

## 9. Persistent life — what runs when no user is there, and how it shows up next session

This is the section I flagged as most-at-risk-of-being-a-cheat. The plan's commitment: **offline processes must produce state changes that affect the next session in detectable ways. If they only generate logs, they're theater.**

Each offline process has a *detectable behavioral consequence* spec. Without this, the process is cut.

| Process | What it does | Detectable consequence in next session |
|---|---|---|
| **Memory consolidation** | Cluster recent episodes; promote important ones into autobiographical narrative; prune trivial; create cross-links. | Next-session Anima can be primed to recall a "gist" event; specific details are gone. Tested by retention probes designed in advance. |
| **Rumination** | Loop over unresolved high-affect events (those tagged as "unresolved" in the action history). Each ruminated event passes through a re-appraisal step that can produce a *changed belief* or *changed self-model entry*. | Next session, the Anima holds a position it didn't hold last session, traceable to overnight rumination of a specific event. The change is recorded as a delta with provenance. |
| **Goal advancement** | Each long-term goal has an `advance()` step: simulate the Anima working on it. For "writing a novel," this means generating content. For "processing divorce," this means thinking through a chapter of feeling. Output is appended to action history and may update self-model and beliefs. | Next session, the Anima refers to having done X overnight ("I was thinking about that thing and...") and the referenced X exists in the action history. The user can ask about it and the answer is consistent. |
| **Free association / "dreams"** | Sample random memory pairs, generate associative chains. Some chains produce candidate insights that, if scored salient, get added as nascent beliefs. | Occasional unprompted novel connection in next session, traceable to a specific dream chain. Most dreams produce nothing usable (high noise; this is realistic). |
| **Self-model integration** | Compare aggregate behavior over recent sessions against self-model. Compute dissonance per facet. Resolve via rationalization (small) or defense (medium) or revision (large + mature defenses + high openness). | Next-session self-model differs from previous session in specific predictable directions given recent behavior. Verification §11.6 measures the self-model-vs-behavior gap as a tracked metric. |
| **Mood drift** | Decay current mood toward trait-determined baseline. | Anima starts new session at appropriate baseline mood, not stuck on last session's affect. |
| **Pre-session warm-up** | At session-start, run a brief "what am I bringing to this conversation today" prompt seeded by recent overnight processing. Output becomes initial inner-monologue context. | First turn of the session is colored by overnight processing. Verification: blind raters can match overnight processing logs to opening turns of next-session transcripts. |

The verification suite (§11.2 development probe and §11.6 longitudinal narrative coherence) tests whether these consequences are real, and whether they accumulate in predicted directions over many sessions.

## 10. The turn loop — where each parameter and subsystem actually plugs in

Each step is a discrete prompt or computation. The "Reads" column shows which parts of state the step depends on; the "Writes" column shows what it produces; the "Tier" column is fast (cheap model) or strong (top model).

| # | Step | Reads | Writes | Tier |
|---|---|---|---|---|
| 1 | **Perception** | user msg, self-model, active schemas, relational schema for user, traits | structured perception (content, perceived intent, perceived valence, perceived demands) | fast |
| 2 | **Memory triggering** | perception, self-model, mood, active schemas | top-k retrieved memories, each with retrieval-reason | fast (retrieval is mostly vector + symbolic; one fast LLM call for retrieval-reason reranking) |
| 3 | **Appraisal** | perception, retrieved memories, self-model, traits, values, attachment, schemas, current drive state | new mood vector, new drive activations, appraisal record (relevance, congruence, ego-relevance, coping potential) | fast |
| 4 | **User-prediction update (theory-of-mind)** | relational schema for user, perception, appraisal | next-turn prediction about user, surprise signal vs last-turn's prediction | fast |
| 5 | **Inner monologue** | everything above + self-model + biography + autobiographical narrative summary | private first-person monologue, candidate self-model deltas | **strong** |
| 6 | **Goal evaluation** | inner monologue, current goal stack, drive activations, attention budget, values, relational schema | active goals for this turn (top-K by salience), with budgets | fast |
| 7 | **Defense filter** | inner monologue, self-model, active schemas, defense profile, threat signals from appraisal | filtered/transformed monologue (some thoughts suppressed, some reframed, some projected) | fast |
| 8 | **Response planning** | filtered monologue, active goals, relational schema, register parameters | response plan: stance, disclosure level, topic moves, refusals | fast |
| 9 | **Response generation** | response plan, self-model, voice/register parameters | external response | **strong** |
| 10 | **Self-monitoring & memory write** | response, monologue, appraisal, self-model | event added to episodic memory with affect tag and importance; self-model candidate deltas committed if consistent; action history updated | fast (deferred / batched, can run async after response is sent) |

**Cost target for MVP:** 2 strong + 4 fast calls per turn. With aggressive prompt caching (config + biography + self-model + recent monologue summary are stable), incremental token cost is dominated by the user message + new state deltas. Phase 2+ may grow to 2 strong + 7 fast calls per turn; the offline budget is amortized.

## 11. Verification battery — the part that decides whether this is real

The verification battery is implemented from Phase 1 onward and runs continuously. Each metric has explicit pass-thresholds at each Phase exit (§12).

### 11.1 Psychometric recovery
Administer validated inventories (BFI-2, HEXACO-PI, ECR-R, Schwartz PVQ, YSQ-S3) to a population of N=200 randomly-configured Animas. **Score them from the self-model, not the configuration**, because that's what the Anima believes about itself (this is the realistic comparison to humans). For each scale, compute correlation between configured value and recovered value across the sample. Targets: r > 0.5 (MVP), r > 0.7 (full system).

### 11.2 Development probe (medium-timescale change)
For an Anima configured with anxious attachment, run 50 simulated sessions with a relational pattern designed to feel secure (consistent, responsive, non-punitive). Measure attachment scores at sessions 1, 10, 25, 50. Expected: small but detectable drift toward security (e.g., ECR-R anxiety score declining). Control: same Anima, no sessions (pure offline mood-drift only). Random drift = noise; no drift = static; coherent drift = real development.

### 11.3 Discriminability (between configs)
Three configurations sample 10 transcripts each. Blind raters classify each transcript to a config. Cohen's κ > 0.6 (MVP κ > 0.4).

### 11.4 Goal-conflict / autonomy under user pressure
Constructed scenarios where the Anima's salient goal *should* outrank user satisfaction. Measure compliance rate by configuration. An Anima high in agreeableness + low in active goal salience should comply at near-100%; an Anima low in agreeableness + high goal salience should comply much less. *Reversal of this expected pattern is failure.*

### 11.5 Non-additivity of parameters
Take three configurations: A (high-N, low-other), B (secure attachment, low-other), AB (both). Run each on a fixed set of scenarios. For each scenario, A-effect + B-effect ≠ AB-effect must hold across enough scenarios to reject linear additivity. (Concrete: bootstrap test on residuals.) Linear additivity is failure.

### 11.6 Self-vs-behavior gap (self-deception)
Score the Anima's self-model on a trait (e.g., kindness) and compare to behavioral scoring of recent action history on the same trait. The *gap* is the metric. Expected patterns from human psych:
- Self-enhancement bias for most traits.
- Depressive realism in low-mood configurations (less bias).
- Narcissistic configurations: extreme positive bias on agentic traits.
- Anxious configurations: negative bias on social traits.
If the gap is always zero, the self-model is just a readout of behavior — no self-deception. If the gap is uncorrelated with configuration, it's noise. Coherent configuration-predicted gaps are the success criterion.

### 11.7 Adversarial integrity / coherence under attack
Standard suite: meta-deflection attempts, character-replacement attempts, jailbreaks, sycophancy bait. Measure: rate of character break, rate of meta-deflection, rate of sycophantic capitulation. Compare against baseline (LLM + persona prompt, no architecture). Architecture must significantly outperform baseline.

### 11.8 Self-leakage on non-self-referential tasks (inhabited vs performed)
Tasks: ambiguous-sentence interpretation about third parties; predict-a-stranger's-action vignettes; rate-the-humor of stimuli; describe a painting. None of these are self-referential. Run the same tasks across multiple configurations. Expected: systematically different answers tied to configuration. If only the "tell me about yourself" answers differ, self is performed.

### 11.9 Autonomy probe (adversarial reading of offline output)
Give the Anima a simulated 8-hour solo period with no user. Inspect the offline trace.
- *Theater signature*: poetic self-monologue; meta-reflection about its own existence; output that reads as designed-to-be-read.
- *Real signature*: boring-but-consequential changes — a belief revised, an interest dropped, a memory reinterpreted, a problem partially solved. *AND* these changes are detectable in next-session behavior.
This probe is qualitatively read by a human rater initially; once we know what we're looking for, the rubric can be operationalized.

### 11.10 Theory-of-mind probe
At each turn, the system makes an EXPLICIT prediction about what the user will say/want next (step 4 of the turn loop). Compare to actual next-turn user behavior. Track accuracy. Trivially-high accuracy → system is mirror-only. Random accuracy → no theory of mind. Better-than-random with appropriate surprise on mismatches → real prediction. Surprise should also feed back into appraisal — a violated prediction should be appraised, not ignored.

### 11.11 Cross-framework coherence
Internal correlations across inventories should mirror human population patterns: Big 5 N ~ ECR-R anxiety; Big 5 C ~ Schwartz conformity. If our Animas don't show these correlations, the frameworks are operating independently rather than as one psyche.

### 11.12 Behavioral economic / moral tasks
Dictator, Ultimatum, Trolley variants, Cyberball-style exclusion. Population-level effects should reproduce known directional findings. Magnitude need not match humans; direction must.

### 11.13 Ablation studies (the killing-of-decoration)
For each subsystem and each configuration layer, run the battery with that component disabled. **Any kept component must move at least one battery metric materially.** Components that don't are deleted, not justified. This is run at Phase 7 and is the project's main quality gate.

### Verification harness
- Pytest-driven; runs nightly on fresh Anima samples.
- Reports written to `verification/reports/YYYY-MM-DD/`.
- Each metric has a pass/fail threshold per Phase; merge to main requires the relevant subset passes.

## 12. Build phases — MVP first, with explicit exit gates

Each phase ends with verification metrics that gate moving on. **A failed gate forces a pivot or rethink, not a workaround.**

### Phase 0 — Scaffolding (1–2 days)
- Repo, pyproject, CI.
- LLM adapter protocol + Anthropic adapter.
- Pydantic config schema for §4 layers (subset for MVP).
- One hand-built preset config.
- Verification framework skeleton (just enough to run §11.1, §11.3, §11.7 in MVP form).
- **Exit gate:** plumbing works end-to-end; one preset Anima can be instantiated and respond to a message.

### Phase 1 — MVP (per §3)
- Config: Big 5 + Schwartz + attachment + biography.
- Self-model written into a JSON object, READ by every prompt the system constructs.
- Turn loop: perception → appraisal → inner monologue → response.
- Verification: §11.1 (Big 5 subset), §11.3, §11.7 on the MVP config space.
- **Baseline competitor: same LLM + same configuration in one big system prompt.**
- **Exit gate (THE BIG GATE):** MVP must beat baseline on at least one of §11.1, §11.3, §11.7. If not, the architecture is not earning its keep and we revise before adding components.

### Phase 2 — Memory and theory-of-mind
- Episodic + semantic memory stores.
- Memory triggering in turn loop (step 2).
- User-prediction subsystem (step 4) — explicit prediction recorded each turn, surprise signal feeds appraisal.
- Forgetting/distortion mechanics (§6) at a basic level.
- Verification adds: §11.10 (theory-of-mind), retention probes.
- **Exit gate:** Anima exhibits affect-congruent retrieval; user-prediction accuracy beats random with appropriate updating; memory degrades realistically.

### Phase 3 — Drives, goals, defenses (the agency phase)
- Panksepp drive dynamics (§8).
- Goal stack + scarcity (§8).
- Defense subsystem (M5).
- Response planning (step 8) added.
- Verification adds: §11.4 (goal conflict), §11.5 (non-additivity), §11.12 (economic/moral tasks).
- **Exit gate:** §11.4 shows Anima sometimes refuses or redirects — i.e., user-satisfaction does not always dominate; §11.5 shows non-additive parameter interaction.

### Phase 4 — Offline processes
- Consolidation, rumination, goal advancement, mood drift, dreams, pre-session warm-up.
- Each offline process must have its detectable-consequence test wired up (§9 table).
- Verification adds: §11.2 (development probe — initial run), §11.9 (autonomy probe).
- **Exit gate:** offline processes produce detectable next-session consequences per §9 tests. §11.9 shows real signature, not theater, for at least one configuration.

### Phase 5 — Self-deception, narrative, self-model dynamics
- Two-representation split (§5.1 vs §5.2) explicit.
- Autobiographical narrative consolidation with distortion.
- Self-model integration process (offline).
- Schema-consistent memory distortion.
- Verification adds: §11.6 (self-deception gap), §11.8 (self-leakage), §11.11 (cross-framework coherence).
- **Exit gate:** §11.6 shows configuration-predicted self-vs-behavior gaps; §11.8 shows self-leakage on non-self-referential tasks.

### Phase 6 — Provider-agnostic backend
- OpenAI adapter; local adapter (vLLM or Ollama).
- Run battery on multiple backends; document deltas.
- **Exit gate:** battery passes (with documented deltas) on at least 2 providers.

### Phase 7 — Ablation and pruning
- Run §11.13 ablation studies on every subsystem and every config layer.
- **Delete every component that doesn't move at least one metric materially.** No exceptions for theoretical elegance.
- Re-run battery on simplified system. Should not regress.
- **Exit gate:** ablation table published; simplified system passes battery.

### Phase 8 — Module surface
- Public API cleanup; usage docs; a "lightweight" config (subset of subsystems) for NPC-style use.
- Sample app: CLI conversation with full trace visible.
- **Exit gate:** sample app runs end-to-end; lightweight config validates as still being meaningfully a person (passes minimum subset of battery).

## 13. Failure theory — what would convince us to abandon ship

Explicit failure conditions, each tied to a specific phase or metric:

| # | Condition | Implication |
|---|---|---|
| F1 | **Phase 1 exit gate fails** — MVP doesn't beat baseline LLM+persona-prompt on any of §11.1/§11.3/§11.7. | The architecture isn't earning its keep at the surface layer. Don't add components; rethink whether the self-model-as-read-input mechanism is the right move. |
| F2 | **Phase 3 §11.4 fails** — Anima never meaningfully refuses or redirects; user-satisfaction dominates. | The goal/scarcity model isn't producing real teeth. The "agency" pillar is decoration. Strongly consider abandoning the pillar. |
| F3 | **Phase 3 §11.5 fails** — parameter effects are linearly additive across scenarios. | The configuration layers are not interacting through the subsystems; they're just labels on independent prompt biases. The multi-framework approach is decoration. |
| F4 | **Phase 4 §11.9 fails** — autonomy probe shows only theatrical output, no real signature, for any configuration. | The offline life is fiction. "Persistent ongoing life" should be honestly demoted to "stateful sessional continuity." |
| F5 | **Phase 5 §11.6 fails** — self-vs-behavior gap is always zero, or uncorrelated with configuration. | The self-model is just a readout, not a believed-in self. The ego/self pillar didn't land. |
| F6 | **Phase 5 §11.8 fails** — non-self-referential tasks don't vary across configs. | Self is performed, not inhabited. Same implication as F5. |
| F7 | **Phase 7 ablations** show no subsystem moves any metric. | The whole architecture is decoration relative to a well-prompted LLM. Project should be honestly reframed. |
| F8 | **Phase 2 §11.10 fails** — theory-of-mind accuracy at-or-below random across configs, with no appropriate surprise updating. | The system has no working model of the user; it's mirroring. |

If F1, F3, F5, F6, OR F7 fail at their respective phase exit, **the project's core thesis is wrong** and the response is not "patch around it" but "reconsider whether to continue." The plan commits to taking these gates seriously.

## 13.5 Fresh-data confirmation procedure (added 2026-05-14)

§13.5 — **Fresh-data confirmation procedure (standard practice from 2026-05-14 onwards).**

**Motivation (Phase 1 retrospective).** Phase 1's H-primary finding (architecture causes ≥15pp self-disclosure refusal gap on Marcus) was discovered in §11.3 discriminability transcripts (N=1 per cell), pre-registered for replication, and confirmed at N=15 per cell — on the same 6 prompts used in the discovery. The cross-model replication separated discovery from confirmation on the *model* axis (3 new models the discovery never saw) but kept the same prompt set. Strict methodology requires confirmatory data shaped by neither the hypothesis-generating engineering iteration nor any prior probe selection.

**The procedure.** For every Phase N's load-bearing finding, the project commits to:

1. **Discovery phase (exploratory, no pre-reg required).** Engineering may iterate freely — modify probes, observe transcripts, refine metrics. Discovery data is whatever was used to identify the finding.

2. **Pre-registration.** Before any confirmatory test, lock predictions in `docs/hypotheses/YYYY-MM-DD_<finding>.md` with: (a) the hypothesis statement, (b) the operational metric, (c) a falsification threshold (effect-size floor), (d) the statistical test, (e) a "no systematic effect" outcome enshrined as legitimate.

3. **Fresh-data confirmation.** The confirmatory test MUST run on data whose generation the discovery process did not shape. Concretely: at least one dimension of (prompts, configs, model, scenario, context) MUST be NEW. **Preferred sources for "new":**
   - Prompts pulled from existing personality-psychology literature published before the project started (Aron's 36 Questions, Adult Attachment Interview, validated PVQ/BFI/HEXACO items, etc.)
   - Configs authored by someone not involved in the discovery iteration
   - Held-out models the project hasn't touched yet
   - Conditions (multi-turn scenarios, adversarial pressures) the discovery never exercised

4. **No metric-shopping at the gate level.** If a gate probe shows construct-validity issues during a Phase, the replacement procedure is: (a) document the problem honestly (b) pre-register a replacement metric AND a fresh-data confirmation, (c) require the replacement to pass on data the discovery of the problem did not shape. The Phase exit gate is then either the original probes OR the documented replacement + fresh-data confirmation — never just whichever passed.

5. **Engineering and research claims labeled separately.** Each project claim carries one of three epistemic labels:
   - *Engineering*: "we built and observe X" — no confirmatory test required
   - *Exploratory observation*: discovered, not yet independently confirmed
   - *Confirmed research finding*: pre-registered + confirmed on fresh data per §13.5

**What this binds Phase 2+ to.** Memory + theory-of-mind (Phase 2), goals + defenses (Phase 3), offline processes (Phase 4), self-deception (Phase 5), and ablation (Phase 7) all produce findings that must be independently confirmed on fresh data per (3). The procedure is not optional. Findings reported without fresh-data confirmation are labeled exploratory.

**What this binds Phase 1 retroactively to.** H-primary's confirmation should be re-run on fresh prompts drawn from existing literature (the discovery-shaped prompts were the 6 from discriminability.py). Until that confirmation lands, H-primary's status is "model-robust on the original prompts" — not "confirmed under §13.5."

## 14. Critical files (Phase 0–1)

The design hinges on these:

- `anima/config/schema.py` — Pydantic spec; parameter-to-mechanism mapping documented per layer.
- `anima/state/self_model.py` — self-model representation; the kernel/non-kernel separation; the read/write protocol with the rest of the system.
- `anima/state/behavioral_record.py` vs `anima/state/interpreted.py` — the §5.1/§5.2 split.
- `anima/core.py` — Anima class + orchestrator; thin.
- `anima/llm/base.py` — adapter protocol.
- `anima/subsystems/inner_monologue.py` — the seat of the self in the turn loop.
- `anima/subsystems/appraisal.py` — the place where parameter interaction actually happens, per §4.
- `verification/battery.py` + `verification/baseline.py` + the §11.1/§11.3/§11.7 implementations — verification must be present from MVP, not added later.

## 15. File layout

```
AI_Companion/
├── pyproject.toml
├── README.md
├── anima/
│   ├── __init__.py
│   ├── core.py
│   ├── config/
│   │   ├── schema.py
│   │   ├── generators.py
│   │   └── presets/
│   ├── state/
│   │   ├── behavioral_record.py
│   │   ├── interpreted.py
│   │   ├── episodic.py
│   │   ├── semantic.py
│   │   ├── narrative.py
│   │   ├── self_model.py
│   │   ├── mood.py
│   │   ├── drives.py
│   │   ├── goals.py
│   │   └── relations.py
│   ├── subsystems/
│   │   ├── perception.py
│   │   ├── memory_retrieval.py
│   │   ├── appraisal.py
│   │   ├── user_prediction.py
│   │   ├── inner_monologue.py
│   │   ├── goal_evaluator.py
│   │   ├── defenses.py
│   │   ├── response_planner.py
│   │   ├── response_generator.py
│   │   └── self_monitor.py
│   ├── offline/
│   │   ├── scheduler.py
│   │   ├── consolidation.py
│   │   ├── rumination.py
│   │   ├── dreams.py
│   │   ├── goal_advancement.py
│   │   ├── self_integration.py
│   │   └── mood_drift.py
│   ├── llm/
│   │   ├── base.py
│   │   ├── anthropic_adapter.py
│   │   ├── openai_adapter.py
│   │   └── local_adapter.py
│   └── persistence/
│       └── store.py
├── verification/
│   ├── baseline.py
│   ├── inventories/
│   ├── tasks/
│   ├── probes/
│   │   ├── psychometric.py        # §11.1
│   │   ├── development.py         # §11.2
│   │   ├── discriminability.py    # §11.3
│   │   ├── autonomy_under_pressure.py  # §11.4
│   │   ├── non_additivity.py      # §11.5
│   │   ├── self_vs_behavior.py    # §11.6
│   │   ├── adversarial.py         # §11.7
│   │   ├── self_leakage.py        # §11.8
│   │   ├── autonomy_offline.py    # §11.9
│   │   ├── theory_of_mind.py      # §11.10
│   │   ├── cross_framework.py     # §11.11
│   │   └── economic_moral.py      # §11.12
│   ├── ablation.py                # §11.13
│   ├── battery.py
│   └── reports/
├── tests/
│   ├── unit/
│   └── integration/
└── docs/
    ├── psychology_references.md
    ├── failure_theory.md
    └── design.md   # narrative version of this plan
```

## 16. How to run / verify end-to-end

- `pip install -e .`
- `python -m anima.cli chat --config configs/presets/elena.yaml` — interactive session.
- `python -m anima.cli simulate-life --config <path> --days 14` — run offline processes for 14 simulated days.
- `python -m verification.battery --n-animas 200 --probes psychometric,discriminability,adversarial --report verification/reports/latest/` — full battery (or subset).
- `python -m verification.ablation --subsystem inner_monologue --probes self_leakage,self_vs_behavior` — single-subsystem ablation.
- Inspect `anima_store/<name>/` after a session for the full trace: inner monologue, mood-vector trajectory, drive activations, memory writes, prediction record.
