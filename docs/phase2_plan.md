# Phase 2 Plan (added 2026-05-14)

> Preserved here on 2026-05-18 from `~/.claude/plans/create-an-llm-system-tidy-pizza.md` before that plan file was repurposed for the writeup-audit task. This is the canonical Phase 2 execution plan. STATE.md reflects current Phase 2 progress against it.

## Context

**Why Phase 2:** Phase 1 closed cleanly on 2026-05-14 with one §13.5-confirmed research finding (Anima Marcus produces self-disclosure refusal at much higher rate than Baseline Marcus, model-robust across 4 LLM families and prompt-robust across 2 prompt sets). Master plan §12 frames Phase 2 as **memory + theory-of-mind**, with three exit-gate criteria:

1. Anima exhibits affect-congruent retrieval
2. User-prediction (ToM) accuracy beats random with appropriate surprise updating
3. Memory degrades realistically

**The big leap:** Phase 1 built five distinct in-the-moment personas. Phase 2 turns them into five persons-with-history — Animas that sustain identity across time AND have a working model of who the user is. Per master plan §2, Phase 2 activates two new causal mechanisms that were dark in Phase 1: **M2** (memory encoding/retrieval/distortion) and **M3** (prediction about the user).

**Why this plan, now:** Phase 1 retrospective produced four binding rules:

1. **Engineering vs research separated and labeled per §13.5** (engineering / exploratory observation / confirmed research finding)
2. **Pre-register hypotheses before any interpretive experiment; ELICIT USER PREDICTIONS first**
3. **§13.5 construct-validity contingency procedure** governs metric replacement
4. **Architecture versioning** — Phase 1 frozen at `anima_v1/` + `verification_v1/`; user wants to chat with v1 alongside v2+ as Phase 2 develops

**User decisions locked (2026-05-14):**

- **Scope:** Full Phase 2 — memory store + retrieval + basic forgetting + user-prediction (ToM) + persistence + cross-session CLI demo
- **Versioning:** `anima/` is HEAD (mutable). At Phase 2 exit: `cp -R anima/ anima_v2/`; `cp -R verification/ verification_v2/`. CLI gains `--version v1|head` early, `--version v1|v2|head` after exit.
- **Hypothesis flow:** Per-pre-reg user elicitation BEFORE pre-reg authoring; engineering proceeds in parallel.

---

## Engineering deliverables (E0–E6)

Engineering is iteration-first per §13.5 rule 5. No pre-registration required for E0–E6. Each task runs via SDD: implementer → spec-compliance reviewer → code-quality reviewer.

### E0 — Five new Phase 2 configs (user-requested)

**Motivation:** Phase 1's 5 configs (marcus, elena, jamie, marcus_warm, elena_secure) are "discovery-iteration-shaped" — the user has read Phase 1 transcripts of each. Hypotheses formed for R1/R2/R4 on those configs would be colored by remembered Phase 1 behavior, not by framework reasoning. Per §13.5 #3 ("configs authored by someone not involved in the discovery iteration" is a preferred fresh-data source), Phase 2 research uses **five new configs the user has never interacted with**.

**Constraints:**

- Span psychologically distinct territory: different attachment styles, defense maturities, schema profiles, Big5 patterns.
- Zero overlap with the existing 5 Phase 1 personalities (no avoidant-engineer recapitulation, no anxious-teacher recapitulation).
- Each config must be **predictable from framework** — once the user reads the high-level psychological summary, they can form a prediction from attachment theory + defense theory + schema theory without needing to have chatted with the Anima.
- Full preset YAMLs under `anima/config/presets/` so they're runnable from day 1 with `--persona <name>`.

**Engineering separation:** Smoke tests for E5/E6 (cross-session recall) use **existing Marcus** so engineering verification doesn't contaminate the new configs with iteration history. The new configs only see the world during R1/R2/R4 research runs.

**Files to create:** `anima/config/presets/<name>.yaml` × 5

**SDD brief:** Construct 5 configs spanning these dimensions:
1. Attachment styles: must cover at least three of {dismissive-avoidant, fearful-avoidant/disorganized, anxious-preoccupied, earned-secure, secure-conflict}
2. Defense maturity: must include at least one immature, one neurotic, one mature
3. Schema profile: each config has 1–2 active schemas from Young's EMS; collectively cover at least 4 distinct schemas
4. Big5 patterns: must include at least one high-O config, at least one high-N config, at least one low-A config

### E1 — State scaffolding

**Files to create:**

- `anima/state/episodic.py`: `EpisodicEvent` dataclass + `EpisodicStore`. List-backed + JSON persistence.
- `anima/state/semantic.py`: `SemanticFact` + `SemanticStore` with crud.
- `anima/state/relations.py`: `RelationalSchema` (per known person) + `RelationsStore`.
- `anima/state/narrative.py`: **STUB ONLY** — Phase 5 will fill this.

Update `anima/state/__init__.py` to export new types.

### E2 — Memory retrieval subsystem (turn loop step 2)

**File:** `anima/subsystems/memory_retrieval.py`

- `MemoryRetrieval.run` returns `list[RetrievedMemory]` with `retrieval_reason` and `score`.
- Ranker: symbolic prefilter → mood-congruence weight (cosine on VAD) → schema-relevance weight → top-k.
- One fast-tier LLM call for retrieval-reason reranking per master plan §10 step 2.
- Hook in `anima/core.py` between perception and appraisal.

### E3 — User-prediction subsystem (turn loop step 4)

**File:** `anima/subsystems/user_prediction.py`

- `UserPrediction.run` returns `UserPrediction(next_intent_label, content_hint, surprise_score_vs_last)`.
- One fast-tier LLM call.
- Surprise score compares last turn's stored prediction to current perception. Feeds back into appraisal.
- Predictions stored on `RelationalSchema.surprise_history[]` across turns for §11.10 evaluation.
- Hook in `anima/core.py` between appraisal and inner_monologue.

### E4 — Forgetting (subset of §6 mechanics)

Phase 2 implements **three** of master plan §6's five mechanisms. The other two require an offline scheduler and are deferred to Phase 4.

**In scope (Phase 2):**

- **Affect-congruent retrieval** — ranker weight in E2 (Bower's mood-congruent memory).
- **Schema-consistent reconstruction at retrieval** — Conway-style. The retrieval-reason LLM call (in E2) is conditioned on current schemas/mood/self-model.
- **Decay** — `EpisodicEvent.importance_decayed(now) = importance * decay_fn(now - ts, retrieval_count)`. Threshold excludes from retrieval candidate list but keeps event in behavioral record per §5.1.

**Deferred to Phase 4:**

- Consolidation with detail loss (needs offline scheduler)
- Mood-incongruent forgetting (needs offline scheduler)

### E5 — Persistence (per-Anima JSON store)

**File:** `anima/persistence/store.py`

- `AnimaStore(name).load()` reads `anima_store/<name>/{behavioral_record.json, interpreted.json, transcripts/<session_id>.json}`.
- `AnimaStore(name).save()` writes atomically (tmp + rename).
- **Behavioral record (§5.1):** event_log, action_history, transcripts. NEVER pruned (auditable).
- **Interpreted state (§5.2):** self_model, beliefs, relational_schemas, mood, drives. Updated each turn.
- Load on Anima instantiation; save at session-end + every N turns (configurable, default N=5).

### E6 — Turn loop integration + CLI cross-session demo

**Modify `anima/core.py`:**

- Insert step 2 (memory_retrieval) and step 4 (user_prediction) into the turn loop.
- Expand step 10 (self_monitor) to write `EpisodicEvent` per turn with `affect_tag` from appraisal and `importance` scored from inner-monologue salience.

**Modify `anima/cli.py`:**

- Add `--version v1|head` flag (default `head`).
- Add `--session-id <id>` for resumption.
- Trace-display shows retrieved memories + user prediction per turn for debugging.

**Smoke test:** Two-session conversation as Marcus with the same `session-id`. Second session must reference a detail from the first.

---

## Research deliverables (R1–R4)

Each research item is preceded by **user-hypothesis elicitation** AND gated by §13.5 (fresh-data confirmation). Engineering may proceed in parallel with research planning, but no research run starts until the corresponding pre-reg is locked.

### R1 — Affect-congruent retrieval (master plan §12 gate criterion 1)

- **Configs used:** the 5 NEW Phase 2 configs from E0 (not Phase 1 configs)
- **Pre-reg:** `docs/hypotheses/YYYY-MM-DD_affect_congruent_retrieval.md`
- **Operational:** For each config × mood condition (negative / positive / neutral mood vector), trigger memory retrieval on a fixed neutral query. Measure mean `affect_tag` of top-k retrieved memories vs uniform random sample.
- **User-supplied prediction:** elicited before pre-reg authoring.
- **Falsification floor:** to be set in pre-reg; null effect is a legitimate outcome per §13.5 rule 2(e).

### R2 — Theory-of-mind accuracy by config (master plan §12 gate criterion 2; §11.10)

- **Configs used:** the 5 NEW Phase 2 configs from E0
- **Pre-reg:** `docs/hypotheses/YYYY-MM-DD_theory_of_mind.md`
- **Operational:** Multi-turn conversation N ≥ 15 per config. Per turn, Anima predicts user's next-turn intent. Score via Claude-judge.
- **§13.5 #4 construct-validity preflight:** before treating ToM accuracy as the gate metric, audit whether the Claude-judge can reliably distinguish prediction-quality.
- **Per-config predictions:** USER provides — formed from each new config's framework summary.

### R3 — Memory's effect on Marcus refusal (Phase 1 carry-forward)

Phase 1's confirmed finding was on a stateless architecture. Does adding cross-turn memory amplify, reduce, or leave unchanged that effect?

- **Config used:** the EXISTING Phase 1 Marcus (by construction — R3 IS the Phase 1 carry-forward test)
- **Pre-reg:** `docs/hypotheses/YYYY-MM-DD_memory_effect_on_marcus_refusal.md`
- **Operational:** Re-run self_disclosure_replication on Phase 1's confirmed fresh-data conditions (Aron 1997 prompts, Mistral). Compare refusal-rate delta.
- **Auxiliary** — not a Phase 2 master-plan exit gate, but methodologically important.

### R4 — Memory degrades realistically (retention curve, master plan §12 gate criterion 3)

- **Configs used:** the 5 NEW Phase 2 configs from E0
- **Pre-reg:** `docs/hypotheses/YYYY-MM-DD_retention_curve.md`
- **Operational:** Author a 10-session synthetic dialog with planted facts at varying importance. Probe recall at sessions 1, 5, 10. Measure recall accuracy and detail-loss rate.
- **User-supplied prediction** on curve shape and config-conditional differences.

### §13.5 compliance for Phase 2

- **Fresh-data confirmation** required for R1, R2, R4 (the master-plan §12 exit-gate criteria) and R3.
- At least one dimension (prompts, configs, model, scenario) must NOT be shaped by Phase 2 engineering iteration.
- Preferred fresh sources: Aron 1997 prompts (literature), held-out model, configs authored by the user.
- Engineering claims (E1–E6) do not need fresh-data confirmation.

---

## Phase 2 exit gate

Per master plan §12:

1. Affect-congruent retrieval shown — R1 confirmed on fresh data
2. ToM accuracy > random with appropriate surprise updating — R2 confirmed on fresh data
3. Memory degrades realistically — R4 retention curve confirmed on fresh data

If any gate fails: §13.5 contingency procedure.

R3 is auxiliary but methodologically important: does Phase 1's confirmed finding survive Phase 2 architecture?

---

## Execution order

Engineering and research interleave; engineering goes first so research has a system to test.

1. STATE.md update — mark Phase 2 IN PROGRESS
2. SDD cycle E0 — 5 new configs
3. SDD cycle E1 — state scaffolding
4. SDD cycle E2 — memory_retrieval subsystem
5. SDD cycle E3 — user_prediction subsystem
6. SDD cycle E4 — forgetting mechanics
7. SDD cycle E5 — persistence
8. SDD cycle E6 — CLI + smoke test
9. Engineering verification — user chats with `head` across two sessions
10. Research cycle R1 — elicit hypothesis → pre-reg → fresh-data run → verdict
11. Research cycle R2 — elicit hypothesis → pre-reg → construct-validity preflight → run → verdict
12. Research cycle R3 — elicit hypothesis → pre-reg → run on Phase 1's fresh-data conditions → verdict
13. Research cycle R4 — elicit hypothesis → pre-reg → run → verdict
14. Phase 2 exit writeup — `docs/phase2_writeup.md`
15. Architecture snapshot — `cp -R anima/ anima_v2/`, `cp -R verification/ verification_v2/`
16. STATE.md update — Phase 2 CLOSED, set up Phase 3

---

## Versioning checkpoints

- **During Phase 2:** `anima/` is HEAD (mutable). `anima_v1/` is frozen. CLI: `--version v1|head` (default `head`).
- **At Phase 2 exit:** `cp -R anima/ anima_v2/`; `cp -R verification/ verification_v2/`. CLI: `--version v1|v2|head`.
- **Phase 3 onward:** same pattern repeats at each Phase exit.

---

## Engineering vs research labels

Per §13.5 rule 5, every claim in Phase 2 writeups carries one of three epistemic labels:

- **Engineering**: "we built X, observe Y" — applied to E1–E6 outputs
- **Exploratory observation**: discovered, not yet independently confirmed
- **Confirmed research finding**: pre-registered + confirmed on fresh data per §13.5 — applied to R1–R4 confirmed results only

---

## Deferred from Phase 2

- Consolidation, mood-incongruent forgetting → Phase 4 (needs offline scheduler)
- Free-association / "dreams" → Phase 4
- §11.6 self-vs-behavior gap probe → Phase 5
- §11.8 self-leakage on non-self-referential tasks → Phase 5
- §11.11 cross-framework coherence → Phase 5
- Caricature vs inhabited disambiguation via conflict configs → Phase 5
- Vector embeddings + scalable memory store → only if N events per Anima exceeds ~500 (Phase 4+)
- Multi-Anima social cognition → out of scope until much later
- Phase 3 (drives / goals / defenses as discrete subsystems) → next phase after Phase 2

---

## Reference

- **Strategic master roadmap (north star):** `docs/master_plan.md`. Sections 0–16; §13.5 is the binding fresh-data-confirmation procedure.
- **Phase 1 canonical record:** `docs/phase1_writeup.md`.
- **Phase 1 frozen architecture:** `anima_v1/` + `verification_v1/`.

---

## Current Phase 2 status (as of preservation date 2026-05-18)

**Engineering: COMPLETE.** All six SDD cycles (E0–E6) landed and pushed to GitHub:

| Task | Commit | What it delivered |
|---|---|---|
| E0 — 5 new configs | `a34cb4a` | Tomás, Priya, Wolfgang, Aiyana, Mei-Lin |
| E1 — state scaffolding | `93e36c6` | episodic, semantic, relations, narrative-stub |
| E2 — memory_retrieval | `c63acac` | turn loop step 2, mood-cosine + schema + recency + importance ranker |
| E3 — user_prediction | `a8ca9f8` | turn loop step 4, heuristic surprise feeds appraisal |
| E4 — forgetting | `ea95b15` | decay function, threshold filter at retrieval (store never pruned) |
| E5 — persistence | `ede3318` | AnimaStore JSON, §5.1/§5.2 file separation, atomic write |
| E6 — self_monitor + CLI | `1c27faa` | EpisodicEvent per turn; --session-id and --version flags |

**Tests:** 197/197 passing.

**Cross-session smoke verified:** session 1 writes 3 events, session 2 loads 3 events, retrieval on resume surfaces 3 memories. CLI `--version v1` runs the byte-frozen Phase 1 architecture end-to-end.

**Repo:** PUBLIC at https://github.com/ParkingSoman/anima.

**Research: NOT STARTED.** R1–R4 each require user-supplied predictions BEFORE pre-reg authoring per the standing protocol. Specifically the next user-facing decision when Phase 2 resumes:

> For R1 (affect-congruent retrieval): for each of the 5 new configs (Tomás / Priya / Wolfgang / Aiyana / Mei-Lin), what direction does the user predict for the mean affect-tag of top-3 retrieved memories under (negative / positive / neutral) mood, vs uniform random?

**Phase 2 closure remaining:**

1. R1–R4 research cycles (each: elicit user hypothesis → pre-reg → fresh-data run → verdict)
2. `docs/phase2_writeup.md` (mirrors phase1_writeup structure)
3. `cp -R anima/ anima_v2/` + `cp -R verification/ verification_v2/`
4. STATE.md flip to Phase 2 CLOSED
