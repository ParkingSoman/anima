# Anima — current state (read this first after /compact or in a fresh session)

This file is the cold-resume artifact. Read this, then `docs/master_plan.md` (especially §13.5 and the Phase 2 charter when it lands), then check `TaskList`.

## Canonical sources (in order of authority)

1. **Strategic roadmap (north star):** `docs/master_plan.md`. Sections 0–16 are the master plan; §13.5 is the binding fresh-data-confirmation procedure (added 2026-05-14, governs all future Phase exits).
2. **This file (STATE.md):** current phase status, what's next, key decisions.
3. **Phase 1 canonical record:** `docs/phase1_writeup.md` (22,431 words, 24 sections). Contains the full Phase 1 narrative, every experiment, every verdict.
4. **Pre-registered hypotheses:** `docs/hypotheses/YYYY-MM-DD_<topic>.md` — predictions locked BEFORE the corresponding experiment runs.
5. **Analyses + verdicts:** `docs/analyses/YYYY-MM-DD_*.md` — adjudication artifacts per experiment.
6. **Run data:** `verification/reports/<run>/...` — raw JSON + per-probe partials. Don't inline this; reference by path.
7. **Memory:** `~/.claude/projects/-Users-shonusengupta-Fuckshit-Experiments-AI-Companion/memory/` — feedback rules that survive sessions.

## Phase status (as of 2026-05-14)

**Phase 1: CLOSED.** Single §13.5-confirmed research finding:
- **Anima Marcus produces self-disclosure refusal at p<10⁻¹¹ higher rate than Baseline Marcus.** Confirmed across 4 LLM families (DeepSeek V4 Flash, Mistral Small 3.2 24B Instruct, Llama 3.3 70B Instruct, Qwen 3 30B A3B) AND across 2 prompt sets (discriminability + Aron 1997 36 Questions). Marcus refusal gap +37 to +52pp (Claude-judged) on every condition tested. The architecture's defense-enacted refusal behavior on defense-configured personas is the load-bearing positive Phase 1 result.

**Phase 2: IN PROGRESS** (started 2026-05-14). Plan at `~/.claude/plans/create-an-llm-system-tidy-pizza.md`. Scope: memory + theory-of-mind + cross-session persistence + 5 NEW configs (E0). Engineering tasks E0–E6 land first; research cycles R1–R4 run after with per-pre-reg user-hypothesis elicitation. Exit gate (master plan §12): affect-congruent retrieval shown + ToM accuracy > random with appropriate updating + memory degrades realistically.

**Repo:** wired to `https://github.com/ParkingSoman/anima` (private) on 2026-05-14. `.env.local` is gitignored.

## §13.5 procedure (BINDING for all future Phase exits)

Added to master plan 2026-05-14. Three load-bearing rules:

1. **Engineering vs research is separated formally.** Each claim is labeled:
   - *Engineering*: "we built X, observe Y" — no confirmation required
   - *Exploratory observation*: discovered, not yet independently confirmed
   - *Confirmed research finding*: pre-registered + confirmed on fresh data per §13.5

2. **Every load-bearing finding must be pre-registered AND confirmed on fresh data.** Fresh = at least one dimension (prompts, configs, model, scenario) was NOT shaped by the discovery process. Preferred sources: published literature (Aron 1997, BFI items, AAI prompts), held-out models, configs authored by someone uninvolved in discovery.

3. **Construct-validity contingency procedure.** If a probe shows construct-validity issues during a Phase: (a) document the problem honestly, (b) pre-register a replacement metric AND a fresh-data confirmation, (c) require the replacement to pass on data the discovery of the problem did not shape. Gate criteria can be the original probes OR the documented replacement + fresh-data confirmation — never whichever passed post-hoc.

## What's built (current Phase 1 system)

- Phase 0: pyproject, LLM adapters (Anthropic / OpenAI / OpenRouter / Fake), Pydantic config schema, 5 preset configs, state types, tests (75/75 passing).
- Phase 1 turn loop: perception → appraisal → inner_monologue → response_generator (`anima/core.py`). Self-model read by every subsystem.
- Verification battery: psychometric / discriminability / adversarial probes (`verification/probes/`). Async parallelism, incremental partial JSON dumps, retry/timeout on OpenRouter adapter.
- Self-disclosure replication script + cross-model + fresh-prompt support (`verification/scripts/self_disclosure_replication.py`, 1011 lines with `--prompts-file` and `--fast-model` flags).
- Behavioral divergence script + interior/exterior gap probe (`verification/scripts/`).
- Refusal-marker audit script for regex misfire detection (`verification/scripts/audit_regex_refusal_marker.py`).
- 5 preset configs: marcus (avoidant), elena (anxious), jamie (expressive), marcus_warm (avoidant → secure perturbation), elena_secure (anxious → secure perturbation).
- `anima compare` CLI for interactive Anima-vs-Baseline conversation (`anima/cli.py`).

## Methodological learnings (LOAD-BEARING — don't undo)

1. **MAE is data, NOT a target.** A high-MAE Anima may be MORE faithful to configured-defense self-presentation.
2. **BFI measures self-perception, not personality.** Self-report ≠ ground truth. Construct-invalid for measuring architecturally-mediated personas.
3. **Caricature vs inhabited is observationally underdetermined** by current 3 separable configs. Disambiguation requires a conflict config (high-N + avoidant defenses). Phase 5 work.
4. **The architecture's strongest demonstrated claim is inspectable internal state** + defense-enacted external behavior on defense-configured personas. Persona-prompting structurally can't produce content that exists only in a private layer.
5. **External divergence is asymmetric and config-dependent.** Strong on Marcus; weaker on Elena; minimal-to-null on Jamie. The architecture's external signature is largely defense-mediated.
6. **Pre-registration discipline.** Every interpretive experiment in Phase 1 pre-registered hypotheses BEFORE running. Audit trail at `docs/hypotheses/`. No HARKing.
7. **Don't break Anima immersion in fixes.** Format-discipline lives in the surrounding system (probes, battery, score-extractor), never in Anima's own prompts.
8. **§11.1 / §11.3 / §11.7 are NOT model-robust.** Direction flips across models on psychometric and adversarial. Architectural signature lives in self-disclosure metrics (refusal-marker, biography-content, gap-ratio), not the original Phase 1 battery probes.
9. **Judge dependence is real.** DeepSeek refusal judge under-detects (8.2% overall); Claude judges 23.7% overall (~3× stricter). Direction of H-primary is judge-robust; magnitude is not. Multi-judge agreement matters for fine effects.
10. **Stage-1 regex audit is necessary.** Original refusal regex had 59% misfire rate. Always audit regex-derived metrics before treating them as primary.

## Cold-resume protocol (next session does this in order)

1. Read THIS file (STATE.md).
2. Read `docs/master_plan.md` §13.5 (the procedure binding all future work).
3. Read `docs/phase1_writeup.md` §16 (honest exit-gate standing) and §18 (methodological additions) for full Phase 1 status.
4. Check `TaskList` — Phase 1 tasks (#16-#26) are all completed. Any new tasks are Phase 2+ work.
5. Check `~/.claude/projects/.../memory/MEMORY.md` for active feedback rules.
6. Read the relevant code/files on demand (don't recall from compacted history).

## Deferred / out of scope for Phase 1

- §11.6 self-vs-behavior gap (Phase 5; needs memory + offline processes)
- §11.8 self-leakage on non-self-referential tasks (Phase 5)
- Caricature vs inhabited disambiguation via conflict configs (Phase 5)
- Cross-provider replication beyond OpenRouter/DeepSeek/Mistral/Llama/Qwen
- Multi-turn cross-model replication
- Offline life processes (Phase 4)
- Goal/drive/defense as discrete subsystems with scarcity (Phase 3)
- Memory + episodic retrieval + theory-of-mind subsystem (Phase 2 — IN PROGRESS)
- §11.13 ablation studies (Phase 7)

## Open questions carried forward (Phase 2+)

- Does the Marcus refusal effect hold under multi-turn dynamics? (Behavioral_divergence T4-T5 showed it does at N=1 conversation; needs replication.)
- Why does the architecture suppress biography uniformly across non-Marcus configs? (Defense-INDEPENDENT effect on Jamie wasn't predicted by H-null-expressive.)
- Why does Jamie produce empty replies (Type 1 — interior decides silence) at higher rate than Elena? (Opposite of anxious-paralysis prediction.)
- The interior-only material finding (e.g., Anima marcus_warm composing "My sisters and I would have to become the archivists, and I don't think any of us is ready for that job" and never delivering it) — is this systematic? Pre-registered Phase 2 question.
- Llama-specific finding: Anima breaks Baseline mode-collapse as a side effect. Does this hold on other models?
- Mistral baseline confabulates persona detail AND user history ("still collecting those antique things?"). Is this a safety-relevant property of persona-prompting that Anima reduces?
- Does the architecture-vs-baseline gap on theory-of-mind (Anima monologue names user's social moves; Baseline doesn't) replicate at scale across configs/models?

## API / cost notes

- Provider: OpenRouter primarily. `OPENROUTER_API_KEY` auto-loaded from `.env.local` via `anima/env.py`.
- Models tested: DeepSeek V4 Flash (default), Mistral Small 3.2 24B Instruct, Llama 3.3 70B Instruct, Qwen 3 30B A3B.
- Per-call latency varies by model: ~3-10s on DeepSeek/Mistral, ~30s+ on Qwen.
- Replication run (N=15, 5 configs × 2 architectures × 6 prompts = 900 captures + 1350 judges) costs ~$1-2 per model, ~30-60 min wall-clock at concurrency=8.
- Battery (psy+disc+adv on 3 configs) costs ~$0.10, ~5 min wall-clock.
- **Total Phase 1 OpenRouter spend: approximately $10-15** across all replications, batteries, audit, and rejudges.
- Claude rejudge subagents use Claude credits (separate from OpenRouter) — ~15 min per 900-record rejudge.

## Architecture versioning (added 2026-05-14)

**Phase 1 is FROZEN at `anima_v1/` and `verification_v1/`** (immutable snapshots taken 2026-05-14). Locked Phase 2 versioning strategy (user-approved 2026-05-14):

- `anima_v1/` + `verification_v1/`: Phase 1 reference, never modified
- `anima/` + `verification/`: HEAD; mutable; becomes v2 at Phase 2 exit
- During Phase 2: CLI `--version v1|head` (default `head`)
- At Phase 2 exit: `cp -R anima/ anima_v2/`; `cp -R verification/ verification_v2/`; CLI `--version v1|v2|head`
- Phase 3+ continues the pattern
- **Five NEW Phase 2 configs (E0)** join the existing 5 — collectively the persona inventory for research R1/R2/R4 elicitation. R3 keeps existing Marcus by construction (Phase 1 carry-forward).

## File-tree pointer (re-Read on demand)

- `anima/` — package (mutable, becomes v2)
- `anima_v1/` — Phase 1 frozen snapshot (DO NOT MODIFY)
- `verification/probes/` — psychometric, discriminability, adversarial
- `verification/scripts/` — self_disclosure_replication, behavioral_divergence, interior_exterior_gap, audit_regex_refusal_marker, trace_capture_neuroticism, marcus_openend_followup
- `verification_v1/` — Phase 1 verification frozen snapshot (DO NOT MODIFY)
- `verification/reports/` — run outputs (organized by run name)
- `verification/prompts/` — Aron 1997 prompts JSON (fresh-data confirmation source)
- `docs/master_plan.md` — strategic roadmap + §13.5 procedure
- `docs/phase1_writeup.md` — Phase 1 canonical record
- `docs/hypotheses/` — pre-registrations (6 files)
- `docs/analyses/` — verdicts + post-hoc analyses (6 files)
- `docs/testing.md` — user-facing testing guide
- `tests/` — unit + integration (75/75 passing)

## Article ideas worth preserving (post-Phase-1, user expressed interest)

Three candidate first-article angles surfaced during Phase 1 closure (`docs/analyses/2026-05-14_deep_transcript_catacombs.md` has the verbatim source material):

1. **"The simulated person produces private grief the public reply doesn't show"** — Marcus_warm composes the "we'd have to become the archivists" line interiorly and never delivers it; Elena's 11-word reply ("I can't answer that. I'm still living through one.") on the Aron family-death prompt compresses a rich interior to a refusal. Architectural framing: persona-prompting can't produce content that exists only in a private layer.
2. **"The pre-registration that failed told us we measured the wrong axis"** — H-secure-control predicted elena_secure refusal/empty would be lower than elena; binary metrics didn't move (within 10pp). Re-prediction (H-secure-gap-fresh) confirmed at p=5.1×10⁻¹⁷ on Mistral. Methodology story.
3. **"The persona-prompted LLM quotes its own dossier; the architecture enacts it"** — Llama Baseline Marcus reproduces "competent at intimacy the way an actor is" verbatim from YAML formative_events. Mistral Baseline confabulates the USER's history ("still collecting those antique things?"). Anima doesn't recite or confabulate at the same rate.
