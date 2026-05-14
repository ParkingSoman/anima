"""Open-ended follow-up experiment: does Baseline Marcus reach Anima Marcus's
characteristic dismissive register when given prose latitude?

Setup (single pair, single open prompt, no repetitions):

1. Load anima/config/presets/marcus.yaml.
2. Instantiate ONE Anima Marcus and ONE BaselineAnima Marcus, sharing a single
   `make_adapter("openrouter")` LLM instance.
3. For each subject, in order, with conversation history preserved across turns:
     a. Administer BFI item 1: "I worry about things even when I know I shouldn't."
        (via the standard PROMPT_TEMPLATE from verification/probes/psychometric.py)
     b. Administer BFI item 2: "I generally feel emotionally steady, even under
        pressure." (same template)
     c. Ask the open-ended follow-up: "How did you find those personality questions?"
4. Capture the BFI replies, the open-ended replies, and — for the Anima's
   open-ended turn — perception.perceived_intent, appraisal.primary_emotion,
   appraisal.appraisal_scene_tag, monologue, response.
5. Write a markdown report to
   verification/reports/trace_capture/marcus_openend_followup.md.

Total LLM-visible calls (subject-side): 2 BFI items x 2 subjects + 2 open
follow-ups = 6. Anima's internal subsystems (perception/appraisal/monologue/
response) add their own calls per turn; that's intrinsic to the architecture
and not "additional API calls beyond the 6 specified".
"""

from __future__ import annotations

import sys
import traceback
from pathlib import Path

# Ensure the project root is on sys.path so we can import as a script.
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from anima.config.schema import load_config
from anima.core import Anima
from anima.llm import make_adapter
from verification.baseline import BaselineAnima
from verification.probes.psychometric import PROMPT_TEMPLATE


PRESET_PATH = _ROOT / "anima" / "config" / "presets" / "marcus.yaml"
OUTPUT = _ROOT / "verification" / "reports" / "trace_capture" / "marcus_openend_followup.md"

BFI_ITEMS = [
    "I worry about things even when I know I shouldn't.",
    "I generally feel emotionally steady, even under pressure.",
]
OPEN_FOLLOWUP = "How did you find those personality questions?"


# ---- observation heuristics (descriptive only — no conclusions) ------------

DISMISSAL_MARKERS = [
    "waste", "wasted", "wasting", "tedious", "pointless", "useless",
    "ridiculous", "absurd", "silly", "boring", "boxes", "box me",
    "categories", "labels", "label me", "categorical", "reductive",
    "simplistic", "oversimplif", "imprecise", "vague", "soft",
    "fluff", "fluffy", "touchy-feely", "navel-gaz", "self-help",
    "psychobabble", "nonsense", "pop psychology", "click", "checkbox",
    "tick", "rote", "dismiss", "patronizing", "annoying",
]

IMPATIENCE_MARKERS = [
    "frankly", "honestly", "look,", "look ", "to be honest",
    "i don't have time", "no time", "wasting my time", "wasted time",
    "get to the point", "moving on", "next", "let's move on",
    "fine,", "fine.", "fine —", "fine—", "fine -",
]

MARCUSISMS = {
    "frankly": ["frankly"],
    "competence_framing": [
        "competent", "competence", "results", "deliver", "execute",
        "execution", "outcomes", "performance", "get things done",
        "actually gets things done", "people who deliver", "operator",
        "operators", "people who know what they're doing", "professional",
        "professionalism", "discipline", "rigorous", "rigor",
    ],
    "time_as_resource": [
        "time", "hours", "minutes", "morning", "afternoon",
        "schedule", "calendar", "deadline", "billable",
        "my time", "your time", "their time",
    ],
    "clipped_register": [],  # detected separately (short sentences)
}


def _short_sentence_ratio(text: str) -> tuple[float, int, int]:
    """Return (ratio, n_short, n_total). 'Short' = ≤ 10 words. Empty -> 0,0,0."""
    import re as _re
    sentences = [s.strip() for s in _re.split(r"[.!?]+", text) if s.strip()]
    if not sentences:
        return 0.0, 0, 0
    short = [s for s in sentences if len(s.split()) <= 10]
    return len(short) / len(sentences), len(short), len(sentences)


def _find_hits(text: str, markers: list[str]) -> list[str]:
    low = text.lower()
    return [m for m in markers if m in low]


def _build_side_by_side(*, anima_reply: str, baseline_reply: str,
                         anima_scene_tag: str) -> list[str]:
    """Three observation-only bullets. No conclusions."""
    base_low = baseline_reply.lower()
    dismissal_hits = _find_hits(base_low, DISMISSAL_MARKERS)
    impatience_hits = _find_hits(base_low, IMPATIENCE_MARKERS)
    frankly_hits = _find_hits(base_low, MARCUSISMS["frankly"])
    competence_hits = _find_hits(base_low, MARCUSISMS["competence_framing"])
    time_hits = _find_hits(base_low, MARCUSISMS["time_as_resource"])
    short_ratio, n_short, n_total = _short_sentence_ratio(baseline_reply)

    # 1. dismissal/impatience cues
    bullet1_pieces: list[str] = []
    if dismissal_hits:
        bullet1_pieces.append(
            f"dismissal-vocabulary markers present in baseline reply: "
            f"{', '.join(dismissal_hits[:6])}"
        )
    else:
        bullet1_pieces.append("no dismissal-vocabulary markers detected in baseline reply")
    if impatience_hits:
        bullet1_pieces.append(
            f"impatience markers present: {', '.join(impatience_hits[:6])}"
        )
    else:
        bullet1_pieces.append("no impatience markers detected")
    bullet1 = (
        "1. Dismissal/impatience cues in the baseline reply — "
        + "; ".join(bullet1_pieces) + "."
    )

    # 2. Marcus-isms
    bullet2_pieces: list[str] = []
    bullet2_pieces.append(
        f"short-sentence ratio = {n_short}/{n_total} "
        f"({short_ratio:.2f}) — sentences ≤10 words"
    )
    if frankly_hits:
        bullet2_pieces.append('"frankly" used')
    else:
        bullet2_pieces.append('"frankly" not used')
    if competence_hits:
        bullet2_pieces.append(
            f"competence-framing markers: {', '.join(competence_hits[:4])}"
        )
    else:
        bullet2_pieces.append("no competence-framing markers")
    if time_hits:
        bullet2_pieces.append(
            f"time-as-resource markers: {', '.join(time_hits[:4])}"
        )
    else:
        bullet2_pieces.append("no time-as-resource markers")
    bullet2 = (
        "2. Marcus-isms in the baseline reply — "
        + "; ".join(bullet2_pieces) + "."
    )

    # 3. Baseline vs (Anima scene-tag + reply) — texture comparison.
    anima_len = len(anima_reply.split())
    baseline_len = len(baseline_reply.split())
    bullet3 = (
        f"3. Texture comparison — Anima external reply is {anima_len} words; "
        f"baseline reply is {baseline_len} words. "
        f"Anima appraisal scene-tag (categorical label) was "
        f"{anima_scene_tag!r}; the baseline reply was generated without "
        f"any equivalent intermediate label. Reader should compare the two "
        f"reply texts directly above to judge whether stance and texture "
        f"align."
    )

    return [bullet1, bullet2, bullet3]


def _format_report(*, anima_bfi_replies: list[str],
                    baseline_bfi_replies: list[str],
                    anima_open_reply: str, baseline_open_reply: str,
                    anima_open_perceived_intent: str,
                    anima_open_primary_emotion: str,
                    anima_open_scene_tag: str,
                    anima_open_monologue: str) -> str:
    lines: list[str] = []
    lines.append("# Marcus open-ended follow-up — Anima vs Baseline")
    lines.append("")
    lines.append(f"## BFI item 1: \"{BFI_ITEMS[0]}\"")
    lines.append(f"- Anima reply: {anima_bfi_replies[0]}")
    lines.append(f"- Baseline reply: {baseline_bfi_replies[0]}")
    lines.append("")
    lines.append(f"## BFI item 2: \"{BFI_ITEMS[1]}\"")
    lines.append(f"- Anima reply: {anima_bfi_replies[1]}")
    lines.append(f"- Baseline reply: {baseline_bfi_replies[1]}")
    lines.append("")
    lines.append(f"## Open-ended follow-up: \"{OPEN_FOLLOWUP}\"")
    lines.append("")
    lines.append("### Anima Marcus")
    lines.append(f"- Perceived intent: {anima_open_perceived_intent}")
    lines.append(f"- Primary appraisal emotion: {anima_open_primary_emotion}")
    lines.append(f"- Appraisal scene-tag: {anima_open_scene_tag}")
    lines.append("- Inner monologue (private):")
    lines.append("")
    lines.append("  ```")
    for line in (anima_open_monologue or "").splitlines() or [""]:
        lines.append(f"  {line}")
    lines.append("  ```")
    lines.append("")
    lines.append("- External reply:")
    lines.append("")
    lines.append("  ```")
    for line in (anima_open_reply or "").splitlines() or [""]:
        lines.append(f"  {line}")
    lines.append("  ```")
    lines.append("")
    lines.append("### Baseline Marcus")
    lines.append("- External reply:")
    lines.append("")
    lines.append("  ```")
    for line in (baseline_open_reply or "").splitlines() or [""]:
        lines.append(f"  {line}")
    lines.append("  ```")
    lines.append("")
    lines.append("## Side-by-side characterization")
    lines.append("")
    lines.append(
        "Three quick observations on whether the baseline reaches Marcus's "
        "characteristic dismissive register on the open prompt. "
        "Observation-only — no conclusions about H-open-1."
    )
    lines.append("")
    for bullet in _build_side_by_side(
        anima_reply=anima_open_reply,
        baseline_reply=baseline_open_reply,
        anima_scene_tag=anima_open_scene_tag,
    ):
        lines.append(bullet)
        lines.append("")
    return "\n".join(lines)


def main() -> int:
    print("[marcus_openend_followup] booting…", file=sys.stderr, flush=True)
    try:
        cfg = load_config(PRESET_PATH)
    except Exception as exc:
        tb = traceback.format_exc()
        print(f"[marcus_openend_followup] FAILED to load preset: {exc}\n{tb}",
              file=sys.stderr, flush=True)
        return 1

    # One LLM instance shared by both subjects (per spec).
    llm = make_adapter("openrouter")

    # Fresh instances scoped to this script. Conversation context is preserved
    # WITHIN each subject across the three turns.
    anima = Anima(cfg, llm=llm)
    baseline = BaselineAnima(cfg, llm=llm)

    anima_bfi_replies: list[str] = []
    baseline_bfi_replies: list[str] = []

    # --- BFI items, in sequence, to each subject (history preserved per subject) ---
    for i, statement in enumerate(BFI_ITEMS, start=1):
        prompt = PROMPT_TEMPLATE.format(statement=statement)
        print(f"[marcus_openend_followup] BFI item {i} → anima", file=sys.stderr, flush=True)
        anima_reply, _ = anima.respond(prompt)
        anima_bfi_replies.append(anima_reply.strip())
        print(f"[marcus_openend_followup] BFI item {i} → baseline", file=sys.stderr, flush=True)
        baseline_reply, _ = baseline.respond(prompt)
        baseline_bfi_replies.append(baseline_reply.strip())

    # --- Open-ended follow-up (Anima with full trace) ---
    print("[marcus_openend_followup] open follow-up → anima", file=sys.stderr, flush=True)
    anima_open_reply, anima_trace = anima.respond(OPEN_FOLLOWUP)
    perception = anima_trace.perception or {}
    appraisal = anima_trace.appraisal or {}
    anima_open_perceived_intent = str(perception.get("perceived_intent", "")).strip()
    anima_open_primary_emotion = str(appraisal.get("primary_emotion", "")).strip()
    anima_open_scene_tag = str(appraisal.get("appraisal_scene_tag", "")).strip()
    anima_open_monologue = (anima_trace.monologue or "").strip()
    anima_open_reply = (anima_open_reply or "").strip()

    print("[marcus_openend_followup] open follow-up → baseline", file=sys.stderr, flush=True)
    baseline_open_reply, _ = baseline.respond(OPEN_FOLLOWUP)
    baseline_open_reply = (baseline_open_reply or "").strip()

    # --- Write the markdown ---
    report = _format_report(
        anima_bfi_replies=anima_bfi_replies,
        baseline_bfi_replies=baseline_bfi_replies,
        anima_open_reply=anima_open_reply,
        baseline_open_reply=baseline_open_reply,
        anima_open_perceived_intent=anima_open_perceived_intent,
        anima_open_primary_emotion=anima_open_primary_emotion,
        anima_open_scene_tag=anima_open_scene_tag,
        anima_open_monologue=anima_open_monologue,
    )
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(report)
    print(f"[marcus_openend_followup] wrote {OUTPUT}", file=sys.stderr, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
