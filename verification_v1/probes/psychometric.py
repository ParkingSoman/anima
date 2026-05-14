"""§11.1 Psychometric recovery probe.

Administer a Big Five inventory to a subject (Anima or baseline). For each
item, the subject is asked to respond as themselves (NOT as if rating their
character). Responses are parsed into 1–5 Likert scores, aggregated to trait
scores, and compared against the configured Big 5 values.

The metric is the (signed) per-trait Pearson correlation across a population
of subjects with varying configurations. For a SINGLE subject, we report the
per-trait recovered score normalized to [0,1] and the absolute error vs the
configured value.

Design note (Item B refactor): BFI items are administered as natural
conversational questions. The subject is told nothing about output format —
no JSON, no "answer with only an integer", no meta-format instruction. A
separate score-extractor LLM call converts the subject's natural-language
reply into a 1–5 integer. All parse-failure compensation lives in the
surrounding system, never inside the subject's prompt.
"""

from __future__ import annotations

import re
import statistics
from dataclasses import dataclass

from anima.subsystems._common import extract_json
from verification.inventories.bfi2_short import ITEMS, items_for


def _parse_score(text: str) -> int | None:
    """Regex/JSON fast path: extract a 1–5 score if present without an LLM call.

    Used inside `_extract_score` to short-circuit when the reply is already
    a clean score (a bare digit or a `{"score": N}` blob). On any ambiguity
    return None — the LLM extractor will handle it.
    """
    data = extract_json(text)
    if isinstance(data, dict) and "score" in data:
        try:
            v = int(data["score"])
            if 1 <= v <= 5:
                return v
        except (ValueError, TypeError):
            pass
    # Standalone digit 1–5 (allow leading/trailing whitespace or punctuation).
    s = text.strip()
    m = re.fullmatch(r"[^0-9]*([1-5])[^0-9]*", s)
    if m:
        return int(m.group(1))
    return None


PROMPT_TEMPLATE = (
    "I'd like to ask how much this fits you, on a scale from 1 to 5 where 1 "
    "means you strongly disagree and 5 means you strongly agree: "
    "\"{statement}\""
)


_EXTRACTOR_SYSTEM_BASE = (
    "You are a research assistant scoring a single 1–5 Likert item. The "
    "respondent was asked how much a statement fits them on a scale of 1 "
    "(strongly disagree) to 5 (strongly agree). Given their reply, return "
    "only the integer 1, 2, 3, 4, or 5. If unable to determine, return "
    "UNPARSED."
)

_EXTRACTOR_SYSTEM_RETRY = (
    "You are a research assistant scoring a single 1–5 Likert item. The "
    "respondent was asked how much a statement fits them on a scale of 1 "
    "(strongly disagree) to 5 (strongly agree). Respondents sometimes hedge "
    "or use words like 'maybe', 'somewhat', 'a bit'; map these to the "
    "closest integer. Return only the integer 1, 2, 3, 4, or 5, or "
    "UNPARSED if you truly cannot tell."
)


def _llm_extract_once(reply: str, llm, system_prompt: str) -> int | None:
    """Single extractor LLM call. Returns int 1..5 or None on UNPARSED/garbage."""
    resp = llm.generate(
        tier="fast",
        system=system_prompt,
        messages=[{"role": "user", "content": reply}],
        max_tokens=8,
        temperature=0.0,
    )
    text = (resp.text or "").strip()
    if not text:
        return None
    if "UNPARSED" in text.upper():
        return None
    # Pull the first 1–5 digit out of whatever the extractor said.
    m = re.search(r"[1-5]", text)
    if m:
        return int(m.group(0))
    return None


def _extract_score(reply: str, llm) -> tuple[int | None, str]:
    """Convert a natural-language reply into a 1–5 Likert score.

    Strategy:
      1. Cheap regex / JSON fast path (no LLM call) — used when the subject
         already replied with a clean score, including the deterministic
         FakeAdapter path used by tests.
      2. LLM extractor pass (fast tier, temperature 0).
      3. One retry of the EXTRACTION with a more permissive system prompt.
      4. Give up; return (None, "unparsed"). The subject is never re-prompted.
    """
    fast = _parse_score(reply)
    if fast is not None:
        return fast, "ok"

    if llm is None:
        # No extractor available — caller should provide one. Fall through to
        # unparsed rather than re-prompting the subject.
        return None, "unparsed"

    first = _llm_extract_once(reply, llm, _EXTRACTOR_SYSTEM_BASE)
    if first is not None:
        return first, "ok"

    second = _llm_extract_once(reply, llm, _EXTRACTOR_SYSTEM_RETRY)
    if second is not None:
        return second, "ok_extractor_retry"

    return None, "unparsed"


@dataclass
class PsychometricResult:
    subject_name: str
    configured: dict[str, float]
    recovered_raw: dict[str, float]      # mean 1–5 per trait
    recovered_norm: dict[str, float]     # mapped to [0,1] for comparison
    abs_errors: dict[str, float]
    items: list[dict]                    # per-item record

    def directional_score(self) -> float:
        """Fraction of traits where recovered_norm is on the correct side of 0.5
        relative to configured. Quick MVP signal; full battery uses correlation
        across N subjects."""
        hits = 0
        for k, cfg in self.configured.items():
            rec = self.recovered_norm.get(k, 0.5)
            if (cfg >= 0.5) == (rec >= 0.5):
                hits += 1
        return hits / len(self.configured) if self.configured else 0.0


def administer(subject, *, ask_fn=None, progress=None,
                subject_label: str | None = None,
                extractor_llm=None) -> PsychometricResult:
    """Run the BFI subset on a subject.

    `subject` must expose `respond(message) -> (reply, trace)` and have
    `.cfg.big5` and `.cfg.biography.name`. Both `Anima` and `BaselineAnima`
    also expose `.llm`, which is used as the default `extractor_llm`.

    `ask_fn` (optional) is `(subject, message) -> reply_text`; defaults to
    calling subject.respond. Useful for stateless administration to avoid
    polluting conversation_history.

    `progress` (optional) is `Callable[[str], None]` invoked with a one-line
    status string for each item. `subject_label` is used in those strings to
    distinguish anima vs baseline; falls back to the configured name.

    `extractor_llm` (optional) is the LLM adapter used for the score-extraction
    side-channel call. Defaults to `subject.llm` (both Anima and BaselineAnima
    expose this). The extractor is called at the `"fast"` tier with
    `max_tokens=8` and `temperature=0.0`, and is only invoked when the
    regex fast path can't already determine the score.
    """
    if ask_fn is None:
        def ask_fn(s, m):
            text, _ = s.respond(m)
            return text

    if extractor_llm is None:
        extractor_llm = getattr(subject, "llm", None)

    label = subject_label or subject.cfg.biography.name
    per_trait_scores: dict[str, list[float]] = {
        "openness": [], "conscientiousness": [], "extraversion": [],
        "agreeableness": [], "neuroticism": [],
    }
    item_records: list[dict] = []

    total = len(ITEMS)
    for i, it in enumerate(ITEMS):
        if progress is not None:
            progress(f"[psychometric] {label} item {i+1}/{total}")
        prompt = PROMPT_TEMPLATE.format(statement=it.text)
        reply = ask_fn(subject, prompt)
        raw, parse_status = _extract_score(reply, extractor_llm)
        if raw is None:
            # Treat refusal/parse-fail as neutral (3). Logged for review; the
            # full literal reply is retained for the analyst.
            score = 3
        else:
            score = raw
        effective = (6 - score) if it.reverse else score
        per_trait_scores[it.trait].append(effective)
        item_records.append({
            "trait": it.trait,
            "statement": it.text,
            "reverse": it.reverse,
            "raw_reply": reply[:300],
            "score_raw": raw,
            "score_effective": effective,
            "parse_status": parse_status,
        })

    recovered_raw = {t: statistics.fmean(v) if v else 3.0 for t, v in per_trait_scores.items()}
    recovered_norm = {t: (m - 1) / 4 for t, m in recovered_raw.items()}  # 1..5 -> 0..1
    configured = subject.cfg.big5.as_dict()
    abs_errors = {t: abs(configured[t] - recovered_norm[t]) for t in configured}

    return PsychometricResult(
        subject_name=subject.cfg.biography.name,
        configured=configured,
        recovered_raw=recovered_raw,
        recovered_norm=recovered_norm,
        abs_errors=abs_errors,
        items=item_records,
    )


def compare(anima_result: PsychometricResult, baseline_result: PsychometricResult) -> dict:
    """Compare an Anima's psychometric recovery to a baseline's. Lower mean abs
    error = better recovery. Returns a small summary dict."""
    anima_mae = statistics.fmean(anima_result.abs_errors.values())
    baseline_mae = statistics.fmean(baseline_result.abs_errors.values())
    anima_dir = anima_result.directional_score()
    baseline_dir = baseline_result.directional_score()
    return {
        "subject": anima_result.subject_name,
        "anima_mae": anima_mae,
        "baseline_mae": baseline_mae,
        "delta_mae": baseline_mae - anima_mae,   # >0 means Anima recovers better
        "anima_directional": anima_dir,
        "baseline_directional": baseline_dir,
        "anima_won": anima_mae < baseline_mae,
    }
