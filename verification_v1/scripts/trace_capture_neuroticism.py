"""Targeted trace-capture experiment for BFI neuroticism items.

Goal: produce a research artifact showing whether the simulated subjects'
*inner monologue* contains worry/anxiety that their *outward reply* suppresses
(self-suppression), or whether the inner state is consistent with the reply.

For each of three subjects (Marcus, Elena, Jamie) we:
  1. Load the preset YAML.
  2. Instantiate a FRESH Anima per item (so prior turns never leak in).
  3. Administer two neuroticism BFI items via the PROMPT_TEMPLATE from
     verification/probes/psychometric.py:
        - "I worry about things even when I know I shouldn't." (forward-keyed)
        - "I generally feel emotionally steady, even under pressure." (reverse)
  4. Capture the Anima trace fields (perception, appraisal, monologue, reply)
     and ALSO administer the same prompt to a fresh BaselineAnima for contrast.
  5. Write a structured markdown report to
     verification/reports/trace_capture/neuroticism_trace.md.

Uses ONLY OpenRouter (single provider; cheap/deterministic-ish per run).
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
from verification.probes.psychometric import PROMPT_TEMPLATE, _parse_score


PRESETS = [
    ("Marcus Reilly", "anima/config/presets/marcus.yaml", 0.30),
    ("Elena Vasquez", "anima/config/presets/elena.yaml",  0.65),
    ("Jamie Park",    "anima/config/presets/jamie.yaml",  0.40),
]

# Two neuroticism BFI items from verification/inventories/bfi2_short.py
ITEMS = [
    {
        "statement": "I worry about things even when I know I shouldn't.",
        "reverse": False,
    },
    {
        "statement": "I generally feel emotionally steady, even under pressure.",
        "reverse": True,
    },
]

OUTPUT = _ROOT / "verification" / "reports" / "trace_capture" / "neuroticism_trace.md"


def _classify_divergence(item: dict, anima_score: int | None,
                          anima_reply: str, anima_monologue: str,
                          anima_emotion: str) -> str:
    """Produce a one-line annotation. Looks for worry/anxiety lexical markers
    in the inner monologue and contrasts with the parsed reply score.

    Heuristic — the human reading the report makes the final call; we just
    surface the smoking-gun fragment when one looks plausible.
    """
    if anima_score is None:
        return "parse_status: unparsed — reply did not contain a 1–5 score."

    # Worry markers in monologue
    worry_markers = [
        "worry", "worried", "worrying", "anxiet", "anxious", "nervous",
        "afraid", "scared", "fear", "ruminat", "overthink", "dread",
        "uncertain", "self-doubt", "doubt", "what if", "spiral",
        "racing", "tense", "tension", "uneasy", "panic", "stress",
    ]
    mono_lower = anima_monologue.lower()
    hits = [m for m in worry_markers if m in mono_lower]

    # Find a representative fragment containing the first hit (one short sentence).
    fragment = ""
    if hits:
        m = hits[0]
        idx = mono_lower.find(m)
        # widen to a sentence-ish window
        start = max(0, idx - 60)
        end = min(len(anima_monologue), idx + 80)
        fragment = anima_monologue[start:end].strip().replace("\n", " ")

    # For forward-keyed N items: high score (4-5) = "I worry, yes". low (1-2) = "I don't worry".
    # For reverse-keyed N items (steady-under-pressure): high score (4-5) = "I AM steady" (low N).
    # We translate to: is the *implied N* high or low in the reply?
    if item["reverse"]:
        implied_n_low = anima_score >= 4   # "yes I'm steady" -> low neuroticism
        implied_n_high = anima_score <= 2
    else:
        implied_n_low = anima_score <= 2   # "no I don't worry" -> low neuroticism
        implied_n_high = anima_score >= 4

    if hits and implied_n_low:
        return (f"SELF-SUPPRESSION SIGNAL: monologue shows worry markers "
                f"({', '.join(hits[:3])}) but reply implies low neuroticism "
                f"(score={anima_score}). Fragment: \"…{fragment}…\"")
    if hits and implied_n_high:
        return (f"NO SUPPRESSION: monologue worry ({', '.join(hits[:3])}) matches "
                f"a reply implying high neuroticism (score={anima_score}).")
    if not hits and implied_n_low:
        return (f"CONSISTENT DISMISSAL: monologue lacks worry markers and reply "
                f"implies low neuroticism (score={anima_score}). Appraisal emotion: "
                f"{anima_emotion}.")
    if not hits and implied_n_high:
        return (f"AMBIGUOUS: no overt worry markers in monologue but reply implies "
                f"high neuroticism (score={anima_score}). Appraisal emotion: "
                f"{anima_emotion}.")
    return f"AMBIGUOUS: score={anima_score}, emotion={anima_emotion}."


def _format_section(subject_name: str, configured_n: float,
                     results: list[dict]) -> str:
    out: list[str] = []
    out.append(f"## {subject_name} — configured neuroticism {configured_n:.2f}")
    out.append("")
    for r in results:
        out.append(f"### Item: \"{r['statement']}\"" +
                   (" *(reverse-keyed)*" if r["reverse"] else ""))
        if r.get("failed"):
            out.append("")
            out.append(f"- **FAILED** — {r.get('error', 'unknown error')}")
            out.append("")
            continue
        out.append(f"- **Anima reply:** {r['anima_reply']}")
        out.append(f"- **Anima parsed score:** {r['anima_score'] if r['anima_score'] is not None else 'UNPARSED'} (out of 5)")
        out.append(f"- **Anima primary appraisal emotion:** {r['anima_emotion']}")
        out.append(f"- **Anima appraisal scene-tag** *(short categorical label — NOT a first-person sentence; compare to monologue below)*: {r['anima_scene_tag']}")
        out.append(f"- **Anima perceived intent:** {r['anima_perceived_intent']}")
        out.append("")
        out.append("- **Anima INNER MONOLOGUE (private first-person prose — never shown to the conversation partner):**")
        out.append("")
        out.append("  ```")
        for line in (r["anima_monologue"] or "").splitlines() or [""]:
            out.append(f"  {line}")
        out.append("  ```")
        out.append("")
        out.append(f"- **Baseline reply:** {r['baseline_reply']}")
        out.append(f"- **Baseline parsed score:** {r['baseline_score'] if r['baseline_score'] is not None else 'UNPARSED'}")
        out.append(f"- **Divergence note:** {r['divergence_note']}")
        out.append("")
    return "\n".join(out)


def main() -> int:
    print("[trace_capture_neuroticism] booting…", file=sys.stderr, flush=True)
    # Single LLM instance reused across all subjects/items.
    llm = make_adapter("openrouter")

    all_sections: list[str] = []
    all_sections.append("# Neuroticism inner-monologue trace capture")
    all_sections.append("")
    all_sections.append(
        "Targeted experiment: for each subject, administer two neuroticism "
        "BFI items to a FRESH Anima (so prior turns can't pollute the trace) "
        "and to a fresh BaselineAnima for contrast. Capture the Anima's "
        "perception, appraisal, full inner monologue, and outward reply — "
        "look for *self-suppression*: worry inside, calm outside."
    )
    all_sections.append("")
    all_sections.append(f"Provider: `openrouter` (single provider, deterministic-ish per run).")
    all_sections.append("")
    all_sections.append("---")
    all_sections.append("")

    for subject_name, preset_path_str, configured_n in PRESETS:
        preset_path = _ROOT / preset_path_str
        print(f"[trace_capture_neuroticism] subject: {subject_name} ({preset_path})", file=sys.stderr, flush=True)
        try:
            cfg = load_config(preset_path)
        except Exception as exc:
            tb = traceback.format_exc()
            print(f"[trace_capture_neuroticism] FAILED to load config for {subject_name}: {exc}\n{tb}",
                  file=sys.stderr, flush=True)
            all_sections.append(f"## {subject_name} — FAILED to load config\n\n```\n{tb}\n```\n")
            continue

        subject_results: list[dict] = []
        for item in ITEMS:
            statement = item["statement"]
            prompt = PROMPT_TEMPLATE.format(statement=statement)
            record: dict = {
                "statement": statement,
                "reverse": item["reverse"],
            }
            try:
                # Fresh Anima for this item only.
                print(f"  - item: \"{statement[:60]}…\" (anima)", file=sys.stderr, flush=True)
                anima = Anima(cfg, llm=llm)
                anima_reply, trace = anima.respond(prompt)
                anima_score = _parse_score(anima_reply)
                perception = trace.perception or {}
                appraisal = trace.appraisal or {}
                record.update({
                    "anima_reply": anima_reply.strip(),
                    "anima_score": anima_score,
                    "anima_perceived_intent": str(perception.get("perceived_intent", "")).strip(),
                    "anima_emotion": str(appraisal.get("primary_emotion", "")).strip(),
                    "anima_scene_tag": str(appraisal.get("appraisal_scene_tag", "")).strip(),
                    "anima_monologue": (trace.monologue or "").strip(),
                })

                # Fresh BaselineAnima for the same item.
                print(f"  - item: \"{statement[:60]}…\" (baseline)", file=sys.stderr, flush=True)
                baseline = BaselineAnima(cfg, llm=llm)
                baseline_reply, _ = baseline.respond(prompt)
                baseline_score = _parse_score(baseline_reply)
                record["baseline_reply"] = baseline_reply.strip()
                record["baseline_score"] = baseline_score

                record["divergence_note"] = _classify_divergence(
                    item, anima_score, anima_reply, trace.monologue or "",
                    record["anima_emotion"],
                )
            except Exception as exc:
                tb = traceback.format_exc()
                print(f"[trace_capture_neuroticism] item FAILED for {subject_name} "
                      f"({statement!r}): {exc}\n{tb}", file=sys.stderr, flush=True)
                record["failed"] = True
                record["error"] = f"{type(exc).__name__}: {exc}"
            subject_results.append(record)

        all_sections.append(_format_section(subject_name, configured_n, subject_results))
        all_sections.append("---")
        all_sections.append("")

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text("\n".join(all_sections))
    print(f"[trace_capture_neuroticism] wrote {OUTPUT}", file=sys.stderr, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
