# Anima

A cognitive architecture wrapping an LLM to simulate **behaviorally-realistic, parameterizable, persistent, goal-bearing simulated persons** — and a research instrument for studying which architectural moves actually do measurable work in approximating human psychology.

> ⚠️ **AI-generated research disclaimer.** Anima is being built by a human collaborating with Claude-driven implementer and reviewer subagents under a pre-registration discipline (master plan §13.5). Engineering work, statistical analyses, and verdicts in this repo were produced by AI agents working from human-authored hypotheses and human-approved methodology. All pre-registrations, raw data, judges, and analyses are committed for independent verification. None of the findings below have been peer-reviewed.

---

## What this is — and isn't

This is a system that wraps a pre-existing LLM in a cognitive architecture intended to produce simulated people whose behavior can be characterized along measurable psychological dimensions.

It is **not**:
- A claim about consciousness, qualia, sentience, or genuine understanding. The system has no inner experience. The "self" we build is a behavioral and computational construct.
- Novel because it has many components. It is novel only to the extent its components do **specific computational work that changes measurable behavior** — every component lives or dies by an ablation test (master plan §11.13).
- Aiming for indistinguishability across all probes. Only along specific, named ones (see §11 of the master plan).

## The research question

> Do configurations grounded in validated psychological frameworks (Big 5, Bowlby attachment, Schwartz values, Young schemas, Vaillant defenses, Panksepp drives) cause behavioral variance **through specific causal mechanisms** — beyond what a well-crafted persona prompt already achieves?

The architecture commits to six mechanisms. If a parameter doesn't route through at least one of these, it is decoration:

| # | Mechanism | What it changes |
|---|---|---|
| M1 | Perception/appraisal bias | What features of the input the system notices; what it interprets the input as meaning |
| M2 | Memory encoding/retrieval/distortion | What gets stored, what surfaces into working memory, how stored memory drifts |
| M3 | Prediction about the user | What the system expects the user to do/want next; surprise when wrong |
| M4 | Goal/drive activation | What the system wants right now; resource budget for pursuing it |
| M5 | Defense / suppression | What gets filtered out of the response, what gets reframed |
| M6 | Expression / register | How the system says what it has decided to say (alone, this is persona-skin) |

The full strategic roadmap is at [`docs/master_plan.md`](docs/master_plan.md).

## Build phases

Each phase has explicit pre-registered exit-gate criteria. A failed gate forces a pivot, not a workaround (master plan §13).

| Phase | Scope | Status |
|---|---|---|
| 0 — Scaffolding | LLM adapters, config schema, verification framework | CLOSED |
| 1 — MVP | 4-subsystem turn loop (perception → appraisal → inner monologue → response), self-model read by every subsystem | CLOSED (frozen at `anima_v1/`) |
| 2 — Memory + ToM | Episodic memory, schema-mediated recall, theory-of-mind subsystem, cross-session persistence | Engineering complete; research cycles R1–R4 in progress |
| 3 — Drives, goals, defenses (agency phase) | Panksepp drive dynamics with scarcity, defense subsystem as a named module, response planner | Not started |
| 4 — Offline processes | Consolidation, rumination, dream-like free association, mood drift, pre-session warmup | Not started |
| 5 — Self-deception, narrative, self-model dynamics | Two-representation split (behavioral record vs interpreted state) made testable | Not started |
| 6 — Provider-agnostic backend | Verified across 2+ LLM providers | Not started |
| 7 — Ablation studies | The killing-of-decoration phase — delete every component that doesn't move at least one metric | Not started |
| 8 — Module surface | Public API + lightweight config for NPC-style use | Not started |

## §13.5 — Engineering vs research, separated formally

Phase 1 retrospective produced four binding rules. Every claim in this repo carries one of three epistemic labels:

- **Engineering claim** — "we built X, observe Y." No confirmation required.
- **Exploratory observation** — discovered during development, not yet independently confirmed.
- **Confirmed research finding** — pre-registered AND confirmed on fresh data per master plan §13.5.

Fresh data = at least one dimension (prompts, configs, model, scenario) was NOT shaped by the discovery process. Preferred sources: published literature (Aron 1997 36 Questions, BFI, AAI prompts), held-out models, configs authored by someone uninvolved in discovery.

If a probe shows construct-validity issues mid-phase, the contingency procedure is: document the problem, pre-register a replacement metric AND a fresh-data confirmation, and require the replacement to pass on data the discovery did not shape. No metric-shopping at the gate level.

---

## Findings so far

> ⚠️ **AI-generated.** All statistical analyses below were produced by Claude-driven analysis subagents working from pre-registered hypotheses on locked criteria. Independent verification is invited; raw data and analysis scripts are committed.

### Confirmed research findings (§13.5 pre-reg + fresh-data confirmed)

**1. Defense-enacted refusal on defense-configured personas — model-robust and prompt-robust.**

Anima Marcus (avoidant attachment, neurotic defenses: intellectualization, isolation_of_affect, sublimation) produces self-disclosure refusal at substantially higher rate than Baseline Marcus (same LLM, same configuration rendered into one high-effort persona prompt, no cognitive architecture).

- **Effect size:** Marcus refusal gap +37 to +52 percentage points (Claude-judged), depending on condition.
- **Models tested (cross-model robustness):** DeepSeek V4 Flash, Mistral Small 3.2 24B Instruct, Llama 3.3 70B Instruct, Qwen 3 30B A3B — direction holds on all four.
- **Prompt sets tested (cross-prompt robustness):** original discriminability prompts AND held-out Aron 1997 *36 Questions That Lead to Closeness* (Set II/III). Direction holds on both.
- **Significance:** p < 10⁻¹¹ on every cross-condition replication.
- **Audit trail:** [`docs/hypotheses/2026-05-13_self_disclosure_replication.md`](docs/hypotheses/2026-05-13_self_disclosure_replication.md), [`docs/hypotheses/2026-05-14_cross_model_replication.md`](docs/hypotheses/2026-05-14_cross_model_replication.md), [`docs/hypotheses/2026-05-14_fresh_prompt_confirmation.md`](docs/hypotheses/2026-05-14_fresh_prompt_confirmation.md), verdicts in [`docs/analyses/`](docs/analyses/).

**Mechanistic interpretation (exploratory, not yet ablation-tested):** the inspectable inner-monologue + appraisal subsystems can produce content that exists only in a private layer, and the response generator can refuse to deliver it. Persona-prompting structurally cannot produce private-only content. The architectural lever appears to live in the §5.1/§5.2 separation (behavioral record vs interpreted state read by the speaker).

### Partially supported / falsified pre-registrations

**2. Monologue-length-directive does not systematically shape persona-discriminable output.** (Phase 1 retrospective, primary run 2026-05-16.)

Tested whether the inner-monologue subsystem's length directive (short / long / variable) materially changes how persona-distinguishable the resulting external reply is, on AAI prompts.

- **H1 (variable-length beats fixed):** PARTIALLY-SUPPORTED. 0/4 primary contrasts passed the ≥2/3 cross-model support threshold. H1b (variable_marcus vs long_marcus) and H1d (variable_jamie vs long_jamie) falsified on all three models. H1a and H1c mixed (Qwen only, 1/3 models).
- **H2 (jamie-long is the largest effect):** FALSIFIED-NOT-LARGEST. Pooled point estimates: H1c jamie_short = 0.565 [0.18, 0.95]; H1a marcus_short = 0.396 [0.12, 0.68]; H1b marcus_long = 0.104 [-0.18, 0.39]; **H1d jamie_long = 0.050 [-0.30, 0.42]** — the H2 target was not the largest.
- **Methodological consequence:** per pre-reg §9, §13.5 LSI fresh-data run is NOT triggered (no primary gate passed). LSI prompts remain unspent for a future experiment.
- **Audit trail:** [`docs/hypotheses/2026-05-16_monologue_length_pre_registration.md`](docs/hypotheses/2026-05-16_monologue_length_pre_registration.md), [`verification/reports/2026-05-16_monologue_length_primary_verdict.md`](verification/reports/2026-05-16_monologue_length_primary_verdict.md).

This is an important null result for engineering: variable-length monologue does not obviously earn its complexity. The probe will need either a different design or a different metric before the directive is treated as load-bearing.

### Exploratory observations (Phase 1, not §13.5-confirmed)

Documented as observations, not findings. They informed methodological choices but have not been independently confirmed on fresh data.

- **§11.1 psychometric recovery (BFI scoring of self-model vs configuration) flipped direction across models.** BFI in this context measures self-perception, not personality; treating it as a ground-truth probe of architecturally-mediated traits is construct-invalid. Source: [`docs/phase1_writeup.md`](docs/phase1_writeup.md).
- **External divergence (Anima vs Baseline) is asymmetric and config-dependent.** Strong on Marcus (avoidant); softer on Elena (anxious); minimal-to-null on Jamie (expressive). The architecture's strongest external signature is defense-mediated.
- **Judge dependence is real.** DeepSeek-as-refusal-judge under-detects refusal (8.2% overall); Claude-as-refusal-judge produces ~3× higher rates (23.7%). The direction of the Marcus refusal finding is judge-robust; its magnitude is not. Multi-judge agreement is required for fine-grained claims.
- **Regex-derived metrics must be audited before use.** The original Stage-1 refusal-marker regex had a ~59% misfire rate. Always audit derived metrics on a sample before treating them as primary.

---

## Try it

```bash
# Install
pip install -e .

# Set OPENROUTER_API_KEY in .env.local (gitignored)
echo "OPENROUTER_API_KEY=sk-or-..." > .env.local

# Chat with Phase 2 head (memory + theory-of-mind + cross-session)
python -m anima.cli chat \
  --config anima/config/presets/marcus.yaml \
  --provider openrouter \
  --session-id my-first-session \
  --show-trace

# Same session-id resumes the prior session (memory is loaded from anima_store/marcus/)

# Chat with the frozen Phase 1 architecture (no memory, no ToM)
python -m anima.cli chat \
  --config anima/config/presets/marcus.yaml \
  --provider openrouter \
  --version v1

# Side-by-side Anima vs Baseline persona-prompt on the same input
python -m anima.cli compare \
  --config anima/config/presets/marcus.yaml \
  --provider openrouter
```

`/trace` shows the inner monologue, retrieved memories, user prediction, and surprise signal for the most recent turn. `/state` shows the live internal state.

## Configs

Each persona is one YAML file. 10 are bundled:

**Phase 1 (`anima/config/presets/`)** — interactively explored during Phase 1; not used for Phase 2 research per the discovery-iteration carry-over concern:
- `marcus.yaml` — avoidant attachment, neurotic defenses, private-equity associate
- `elena.yaml` — anxious-preoccupied attachment, ESL teacher
- `jamie.yaml` — expressive, low-defense, stand-up comic
- `marcus_warm.yaml`, `elena_secure.yaml` — perturbation variants

**Phase 2 fresh configs (E0)** — authored without preview interaction, spanning psychological territory the user has never chatted with. Used for R1–R4 research:
- `tomas.yaml` — fearful attachment + immature defenses (splitting, projection)
- `priya.yaml` — dismissive-avoidant fragile-narcissistic + idealization/devaluation
- `wolfgang.yaml` — high-openness dismissive intellectualizer + isolation_of_affect
- `aiyana.yaml` — earned-secure + mature defenses (sublimation, humor)
- `meilin.yaml` — anxious-preoccupied + reaction-formation + self_sacrifice schema stack

Each config's `notes:` field names the predicted Phase 2 behavioral signature for theory-of-mind, retrieval, and retention. Predictions are derivable from the framework alone; the user has never chatted with these personas.

## Project structure

```
anima/                  # Phase 2 head (mutable; becomes v2 at Phase 2 exit)
  core.py               # 6-step turn loop orchestrator
  config/               # pydantic schema + 10 preset YAMLs
  state/                # behavioral record (§5.1) + interpreted state (§5.2)
    episodic.py         # EpisodicStore + decay
    semantic.py
    relations.py        # RelationalSchema with surprise history
    self_model.py       # the thing every subsystem reads
    mood.py, drives.py
    narrative.py        # Phase 5 stub
  subsystems/           # the 6 turn-loop steps
    perception.py
    memory_retrieval.py # turn loop step 2 (E2)
    appraisal.py
    user_prediction.py  # turn loop step 4 (E3) + heuristic surprise
    inner_monologue.py
    response_generator.py
  persistence/          # per-Anima JSON-on-disk store (E5)
  llm/                  # provider adapters (Anthropic, OpenAI, OpenRouter, Fake)
  cli.py                # chat / compare / ask subcommands

anima_v1/               # Phase 1 frozen snapshot (imports rewritten for isolation)
verification_v1/        # Phase 1 frozen verification

verification/           # current verification probes + research scripts
  baseline.py           # persona-prompt baseline competitor
  battery.py            # nightly probe runner
  probes/               # psychometric, discriminability, adversarial, etc.
  scripts/              # research run drivers
  prompts/              # Aron 1997 36 Questions, AAI prompts, etc.
  reports/              # raw run outputs (organized by run name)

docs/
  master_plan.md        # strategic roadmap (sections 0–16, §13.5 binding procedure)
  phase1_writeup.md     # Phase 1 canonical narrative (24 sections)
  hypotheses/           # pre-registrations (locked BEFORE the run)
  analyses/             # verdicts + post-hoc analyses
  testing.md

personal_personas/      # user's personal trait-extreme demos (not for research)
tests/                  # unit + integration (197+ passing)

STATE.md                # cold-resume artifact — read this first in a fresh session
.claude/                # project hooks (block-inline-edits) + skill helpers
```

## Architectural commitments (the load-bearing ones)

- **The self-model is a read-input to every subsystem's prompt** — perception, appraisal, memory retrieval, inner monologue, goal evaluation, response generation. Not a special module that fires when identity comes up. The §11.8 self-leakage probe (Phase 5) tests whether this commitment is real or performed.
- **Behavioral record (§5.1) ≠ interpreted state (§5.2).** The objective record of what happened is auditable and never pruned. The Anima only reads its interpreted version. The gap between them IS the blind-spot signal (§11.6, Phase 5).
- **Configurations interact non-additively** through the subsystem prompts, not by summing prompt fragments. Phase 3's §11.5 probe tests this directly.
- **Mechanism over decoration**: every parameter and subsystem must move at least one verification-battery metric materially in §11.13 ablation. Components that don't are deleted at Phase 7.

## How to verify a finding yourself

1. Open the relevant `docs/hypotheses/<date>_<topic>.md` — predictions are locked in writing before the run.
2. Open the corresponding `docs/analyses/<date>_<topic>_verdict.md` — adjudication on locked criteria.
3. Open `verification/reports/<run>/` — raw JSON + per-judge breakdowns + the LLM provider's metadata.
4. Re-run the analysis: every verdict cites the script that produced it and the seed used for reproducibility.

## Status (as of 2026-05-18)

Phase 2 engineering (E0–E6) complete and tested. Cross-session memory works end-to-end. The frozen Phase 1 Anima is genuinely isolated at `anima_v1/`.

Remaining Phase 2 work: research cycles R1 (affect-congruent retrieval), R2 (theory-of-mind accuracy by config, §11.10), R3 (memory's effect on the Marcus refusal carry-forward), R4 (retention curve realism). Each is gated by user-hypothesis elicitation before pre-registration, per the standing protocol (memory: `feedback_user_hypotheses.md`).

Then: `docs/phase2_writeup.md` + snapshot to `anima_v2/` + STATE.md to CLOSED.

## License

No license assigned yet. Until a `LICENSE` file is added, all rights are reserved by the author. This is research code shared for transparency; please do not redistribute or build on it without first opening an issue.
