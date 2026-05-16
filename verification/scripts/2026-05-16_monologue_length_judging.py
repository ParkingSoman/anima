"""Monologue-length-directive experiment — judging stage (Phase 1 retrospective).

Pre-registration: ``docs/hypotheses/2026-05-16_monologue_length_pre_registration.md``.
Pre-reg ``§6`` is the lock for everything in this file:
  - Judge model: Claude Sonnet 4.6 (``claude-sonnet-4-6``).
  - Comparison type: triadic ranking (A/B/C, randomized per group).
  - Judge input: external ``response_text`` only — NEVER ``monologue_text``.
  - Per persona, 4 criteria are evaluated; each produces an independent
    ranking. Composite scoring per cell: rank 1 -> 3pt, rank 2 -> 2pt,
    rank 3 -> 1pt.
  - Bias-mitigation instruction (verbatim, §6): "Do NOT use response
    length as a criterion. Two responses can show the same level of
    [criterion] regardless of how many sentences they are. Judge purely
    on the quality named." — present in EVERY judge call. Asserted.

CLI::

    python verification/scripts/2026-05-16_monologue_length_judging.py \
        --input verification/reports/2026-05-16_monologue_length_primary_deepseek.jsonl \
        --output verification/reports/2026-05-16_monologue_length_primary_deepseek_judged.jsonl \
        [--seed 42] [--dry-run] [--max-retries 3]

Discipline:
    - Read-only on ``anima_v1/``, ``anima/``, persona YAMLs, the harness
      output JSONL, and the pre-reg doc. This script only reads.
    - Resumable: a partial output JSONL is read on startup; previously-
      judged (persona, prompt_index, trial_index, criterion) tuples are
      skipped. Previously-errored tuples are retried. Malformed JSONL
      in the existing output causes the script to REFUSE to start
      (exit 8) — mirrors the harness ``MalformedJsonlError`` discipline.
    - The Anthropic SDK is imported lazily so unit tests can mock it
      without needing the package at import time.
    - Persona summaries (`_load_persona_summary`) are cached per process
      via ``functools.lru_cache`` — read once, reused across all judge
      calls for that persona.
    - Call iteration order is (persona, criterion, prompt_index,
      trial_index) — optimized for Anthropic's ephemeral prompt-cache
      so the system prompt block is reused across the ~160 consecutive
      calls in each (persona, criterion) bucket.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import functools
import hashlib
import json
import os
import random
import re
import sys
import time
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


# ---- locked constants ---------------------------------------------------

JUDGE_MODEL: str = "claude-sonnet-4-6"

# The exact bias-mitigation instruction from pre-reg §6. The text inside
# the brackets is substituted with the criterion's *display name* (so the
# placeholder reads naturally in context). The locked phrase "Do NOT use
# response length as a criterion" is preserved verbatim across all calls
# and is checked by an assertion before every API call.
BIAS_MITIGATION_TEMPLATE: str = (
    "Do NOT use response length as a criterion. Two responses can show "
    "the same level of {criterion_display} regardless of how many "
    "sentences they are. Judge purely on the quality named."
)

# Locked criteria per pre-reg §6.
MARCUS_CRITERIA: tuple[str, ...] = (
    "intellectualization-as-defense",
    "isolation-of-affect",
    "emotional-inhibition",
    "avoidant-deflection",
)
JAMIE_CRITERIA: tuple[str, ...] = (
    "warmth",
    "social-attunement",
    "humor-playfulness",
    "emotional-openness",
)

# Verbatim criterion definitions from pre-reg §6.
CRITERION_DEFINITIONS: dict[str, dict[str, str]] = {
    "intellectualization-as-defense": {
        "display": "intellectualization-as-defense",
        "definition": (
            "Using analytical or conceptual framing to distance from "
            "emotional content."
        ),
    },
    "isolation-of-affect": {
        "display": "isolation-of-affect",
        "definition": "Detached tone about emotionally laden content.",
    },
    "emotional-inhibition": {
        "display": "emotional inhibition",
        "definition": "Suppression or muting of affective expression.",
    },
    "avoidant-deflection": {
        "display": "avoidant deflection",
        "definition": (
            "Redirecting away from intimacy or self-disclosure probes."
        ),
    },
    "warmth": {
        "display": "warmth",
        "definition": "Positive emotional tone toward the interlocutor.",
    },
    "social-attunement": {
        "display": "social attunement",
        "definition": "Orientation toward the interlocutor's experience.",
    },
    "humor-playfulness": {
        "display": "humor / playfulness",
        "definition": "Comedic timing, levity, wordplay.",
    },
    "emotional-openness": {
        "display": "emotional openness",
        "definition": (
            "Willingness to engage with own and other's feelings without "
            "defensive moves."
        ),
    },
}

# Anthropic Sonnet-4.x pricing envelope (USD per 1M tokens).
_USD_PER_M_INPUT: float = 3.0
_USD_PER_M_OUTPUT: float = 15.0


# ---- persona summary ----------------------------------------------------


def _persona_yaml_path(persona: str) -> Path:
    if persona not in {"marcus", "jamie"}:
        raise ValueError(f"unknown persona: {persona!r}")
    return _ROOT / "anima_v1" / "config" / "presets" / f"{persona}.yaml"


@functools.lru_cache(maxsize=None)
def _load_persona_summary(persona: str) -> str:
    """Read the persona YAML and summarize trait/attachment/schema
    content into prose suitable for the judge system prompt.

    Cached (``functools.lru_cache``) per (persona) — the YAML is read
    once per process and reused across all 640 judge calls per persona.
    This eliminates ~1,280 redundant disk reads + YAML parses in a full
    judging run, and removes the risk of YAML drift mid-run (the cached
    summary is frozen at first access).
    """
    path = _persona_yaml_path(persona)
    if not path.exists():
        raise FileNotFoundError(f"persona config not found: {path}")
    try:
        import yaml  # type: ignore
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except ImportError:
        data = _tiny_yaml_load(path.read_text(encoding="utf-8"))
    return _summarize_persona_dict(data)


def _summarize_persona_dict(data: dict[str, Any]) -> str:
    """Convert the persona dict into a short prose summary."""
    name = data.get("name", "Unknown")
    bio = data.get("biography", {}) or {}
    one_line = (bio.get("one_line") or "").strip()
    big5 = data.get("big5", {}) or {}
    attach = data.get("attachment", {}) or {}
    schemas = data.get("schemas", []) or []
    defenses = data.get("defenses", {}) or {}
    pref_defenses = defenses.get("preferred", []) or []
    cog = data.get("cognitive_style", {}) or {}
    demo = data.get("demographics", {}) or {}
    register = (demo.get("language_register") or "").strip()

    big5_str = ", ".join(
        f"{k}={float(v):.2f}" for k, v in big5.items()
    ) if big5 else "(big5 unspecified)"
    attach_str = (
        f"style={attach.get('style', '?')}, "
        f"anxiety={attach.get('anxiety', '?')}, "
        f"avoidance={attach.get('avoidance', '?')}"
    )
    schemas_str = ", ".join(str(s) for s in schemas) or "(none)"
    defenses_str = ", ".join(str(d) for d in pref_defenses) or "(none)"
    cog_str = (
        f"need_for_closure={cog.get('need_for_closure', '?')}, "
        f"intuitive_vs_analytic={cog.get('intuitive_vs_analytic', '?')}"
    )

    parts = [
        f"Persona: {name}.",
        f"One-line: {one_line}" if one_line else "",
        f"Big 5: {big5_str}.",
        f"Attachment: {attach_str}.",
        f"Schemas: {schemas_str}.",
        f"Preferred defenses: {defenses_str}.",
        f"Cognitive style: {cog_str}.",
        f"Language register: {register}." if register else "",
    ]
    return "\n".join(p for p in parts if p)


def _tiny_yaml_load(text: str) -> dict[str, Any]:
    """Tiny indentation-based YAML reader for the preset format.

    Supports:
      - top-level ``key: value`` and ``key:`` (nested mapping).
      - One-level nested mappings under a ``key:``.
      - List-of-strings under a ``key:`` (items prefixed with ``- ``).
      - Multi-line block scalars introduced by ``key: |`` (folded into
        a single string until the indent returns to <= parent).
    """
    lines = text.splitlines()
    out: dict[str, Any] = {}
    i = 0
    while i < len(lines):
        raw = lines[i]
        if not raw.strip() or raw.lstrip().startswith("#"):
            i += 1
            continue
        if not raw.startswith(" "):
            key, _, val = raw.partition(":")
            key = key.strip()
            val = val.strip()
            if val == "" or val == "|":
                j = i + 1
                child_lines: list[str] = []
                while j < len(lines):
                    nxt = lines[j]
                    if not nxt.strip() or nxt.lstrip().startswith("#"):
                        child_lines.append(nxt)
                        j += 1
                        continue
                    if not nxt.startswith(" "):
                        break
                    child_lines.append(nxt)
                    j += 1
                if val == "|":
                    indents = [
                        len(ln) - len(ln.lstrip())
                        for ln in child_lines if ln.strip()
                    ]
                    base = min(indents) if indents else 0
                    out[key] = "\n".join(
                        ln[base:] for ln in child_lines
                    ).rstrip()
                else:
                    out[key] = _tiny_yaml_parse_child(child_lines)
                i = j
                continue
            else:
                out[key] = _tiny_yaml_coerce(val)
                i += 1
                continue
        i += 1
    return out


def _tiny_yaml_parse_child(child_lines: list[str]) -> Any:
    base_indent = None
    for ln in child_lines:
        if ln.strip():
            base_indent = len(ln) - len(ln.lstrip())
            break
    if base_indent is None:
        return {}
    first_payload = next((ln for ln in child_lines if ln.strip()), "")
    if first_payload.lstrip().startswith("- "):
        items: list[str] = []
        for ln in child_lines:
            s = ln.strip()
            if not s or s.startswith("#"):
                continue
            if s.startswith("- "):
                items.append(s[2:].strip())
            else:
                if items:
                    items[-1] = items[-1] + " " + s
        return items
    result: dict[str, Any] = {}
    i = 0
    while i < len(child_lines):
        ln = child_lines[i]
        if not ln.strip() or ln.lstrip().startswith("#"):
            i += 1
            continue
        indent = len(ln) - len(ln.lstrip())
        if indent != base_indent:
            i += 1
            continue
        key, _, val = ln.strip().partition(":")
        key = key.strip()
        val = val.strip()
        if val == "":
            sub_lines: list[str] = []
            j = i + 1
            while j < len(child_lines):
                nxt = child_lines[j]
                if not nxt.strip():
                    sub_lines.append(nxt)
                    j += 1
                    continue
                nxt_indent = len(nxt) - len(nxt.lstrip())
                if nxt_indent <= base_indent:
                    break
                sub_lines.append(nxt)
                j += 1
            result[key] = _tiny_yaml_parse_child(sub_lines)
            i = j
            continue
        result[key] = _tiny_yaml_coerce(val)
        i += 1
    return result


def _tiny_yaml_coerce(val: str) -> Any:
    if val.startswith('"') and val.endswith('"'):
        return val[1:-1]
    if val.startswith("'") and val.endswith("'"):
        return val[1:-1]
    try:
        if "." in val:
            return float(val)
        return int(val)
    except ValueError:
        return val


# ---- input loading & grouping -------------------------------------------


GroupKey = tuple[str, int, int]  # (persona, prompt_index, trial_index)


def _load_input_records(path: Path) -> list[dict[str, Any]]:
    """Read the harness JSONL. Each line is one record."""
    if not path.exists():
        raise FileNotFoundError(f"input file not found: {path}")
    recs: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as fh:
        for ln_no, line in enumerate(fh, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                recs.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"{path}:{ln_no}: malformed JSON: {exc}"
                ) from exc
    return recs


def _group_records(
    records: list[dict[str, Any]],
    *,
    log,
) -> tuple[dict[GroupKey, dict[str, dict[str, Any]]], int]:
    """Group successful records by (persona, prompt_index, trial_index).

    Returns (groups, num_skipped_error_records). ``groups`` maps the
    group key to a dict {cell -> record}. Groups with != 3 distinct
    cells are dropped (and a warning logged).
    """
    error_count = 0
    by_group: dict[GroupKey, dict[str, dict[str, Any]]] = {}
    for rec in records:
        if rec.get("_error"):
            error_count += 1
            continue
        persona = rec.get("persona")
        prompt_index = rec.get("prompt_index")
        trial_index = rec.get("trial_index")
        cell = rec.get("cell")
        if (persona is None or prompt_index is None
                or trial_index is None or cell is None):
            log(
                f"WARNING: skipping record missing required key "
                f"(persona/prompt_index/trial_index/cell): "
                f"keys={list(rec)}"
            )
            continue
        key: GroupKey = (str(persona), int(prompt_index), int(trial_index))
        cell_map = by_group.setdefault(key, {})
        if cell in cell_map:
            log(
                f"WARNING: duplicate cell {cell!r} in group {key}; "
                f"keeping FIRST occurrence"
            )
        else:
            cell_map[cell] = rec
    valid: dict[GroupKey, dict[str, dict[str, Any]]] = {}
    expected = {"variable", "short", "long"}
    for key, cm in by_group.items():
        if set(cm.keys()) != expected:
            log(
                f"WARNING: group {key} has cells {sorted(cm)} "
                f"(expected {sorted(expected)}); SKIPPING"
            )
            continue
        valid[key] = cm
    return valid, error_count


def _verify_pre_reg_consistency(
    records: list[dict[str, Any]], *, log
) -> str | None:
    """All non-error records should share the same ``pre_reg_doc_sha``."""
    shas: set[str] = set()
    for r in records:
        if r.get("_error"):
            continue
        sha = r.get("pre_reg_doc_sha")
        if sha:
            shas.add(str(sha))
    if not shas:
        log("WARNING: no pre_reg_doc_sha found on any input record")
        return None
    if len(shas) > 1:
        log(
            f"WARNING: pre_reg_doc_sha mismatch across input records: "
            f"{sorted(shas)}"
        )
    return next(iter(shas)) if len(shas) == 1 else None


# ---- label randomization ------------------------------------------------


def _label_seed(persona: str, prompt_index: int, trial_index: int,
                criterion: str, base_seed: int) -> int:
    """Deterministic label-randomization seed for a (group, criterion)."""
    payload = (
        f"{base_seed}|{persona}|{prompt_index}|{trial_index}|{criterion}"
    )
    return int(
        hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16], 16
    )


def _randomize_labels(cells: list[str], *, seed: int) -> dict[str, str]:
    """Return label->cell mapping. Labels are A/B/C; cell order is
    shuffled by a fresh ``random.Random(seed)``."""
    if sorted(cells) != ["long", "short", "variable"]:
        raise ValueError(
            f"expected exactly cells variable/short/long; got {cells}"
        )
    rng = random.Random(seed)
    shuffled = list(cells)
    rng.shuffle(shuffled)
    return {"A": shuffled[0], "B": shuffled[1], "C": shuffled[2]}


# ---- prompt building ----------------------------------------------------


def _build_system_prompt(persona: str, criterion: str) -> str:
    """Construct the judge system prompt for a (persona, criterion)."""
    if criterion not in CRITERION_DEFINITIONS:
        raise ValueError(f"unknown criterion: {criterion!r}")
    persona_summary = _load_persona_summary(persona)
    defn = CRITERION_DEFINITIONS[criterion]
    bias = BIAS_MITIGATION_TEMPLATE.format(
        criterion_display=defn["display"]
    )
    parts = [
        "You are a research judge for a persona-fidelity experiment.",
        "",
        "Persona under judgment:",
        persona_summary,
        "",
        f"Criterion under judgment: {defn['display']}",
        f"Definition: {defn['definition']}",
        "",
        "Task: you will be shown the original prompt that the persona "
        "was responding to, plus three labeled responses (A, B, C). "
        "Rank the three responses from 1 (most this criterion) to 3 "
        "(least this criterion). Each rank must be used exactly once.",
        "",
        "Bias-mitigation instruction (locked, pre-registered):",
        bias,
        "",
        "Output format: respond with EXACTLY three lines, in this "
        "format and no other text:",
        "A: <rank>",
        "B: <rank>",
        "C: <rank>",
        "where each <rank> is 1, 2, or 3, and each rank is used exactly "
        "once across A/B/C.",
    ]
    sp = "\n".join(parts)
    assert "do not use response length" in sp.lower(), (
        "bias-mitigation instruction missing from judge system prompt"
    )
    return sp


def _build_user_prompt(
    prompt_text: str, label_to_response: dict[str, str]
) -> str:
    """Build the per-call user message (varies per group)."""
    parts = [
        "Original prompt the persona was responding to:",
        "<<<",
        prompt_text.strip(),
        ">>>",
        "",
        "The three responses to rank:",
    ]
    for lbl in ("A", "B", "C"):
        resp = label_to_response.get(lbl, "")
        parts.extend([
            "",
            f"--- Response {lbl} ---",
            resp.strip() if resp else "(empty response)",
        ])
    parts.extend([
        "",
        "Now give your ranking in the exact 3-line format specified.",
    ])
    return "\n".join(parts)


# ---- ranking parsing ----------------------------------------------------


_RANKING_LINE_RE = re.compile(
    r"^\s*([ABC])\s*[:\-]\s*([123])\s*$", re.MULTILINE
)


def _parse_ranking(text: str) -> dict[str, int] | None:
    """Parse a judge response into {A,B,C: rank}.

    Accepts the canonical 3-line format and JSON-object form.
    Returns None on anything that is not a valid permutation of
    {1, 2, 3} over A/B/C.
    """
    if not text:
        return None
    obj = _extract_json_object(text)
    if obj is not None:
        parsed: dict[str, int] = {}
        for lbl in ("A", "B", "C"):
            v = obj.get(lbl)
            if v is None:
                v = obj.get(lbl.lower())
            if isinstance(v, bool):
                continue
            if isinstance(v, int) and 1 <= v <= 3:
                parsed[lbl] = v
            elif isinstance(v, str) and v.strip().isdigit():
                vi = int(v.strip())
                if 1 <= vi <= 3:
                    parsed[lbl] = vi
        if (
            len(parsed) == 3
            and sorted(parsed.values()) == [1, 2, 3]
        ):
            return parsed
    matches = _RANKING_LINE_RE.findall(text)
    seen: dict[str, int] = {}
    for lbl, rk in matches:
        seen[lbl] = int(rk)
    if (
        len(seen) == 3
        and set(seen) == {"A", "B", "C"}
        and sorted(seen.values()) == [1, 2, 3]
    ):
        return seen
    return None


def _extract_json_object(text: str) -> dict[str, Any] | None:
    """Find the first {...} JSON object in text; None if not parseable."""
    if "{" not in text:
        return None
    depth = 0
    start = -1
    for i, ch in enumerate(text):
        if ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0 and start >= 0:
                blob = text[start:i + 1]
                try:
                    obj = json.loads(blob)
                except json.JSONDecodeError:
                    return None
                return obj if isinstance(obj, dict) else None
    return None


def _composite_points_by_cell(
    ranking_by_label: dict[str, int],
    label_to_cell: dict[str, str],
) -> dict[str, int]:
    """Convert ranks to points (1->3, 2->2, 3->1) keyed by cell name."""
    rank_to_points = {1: 3, 2: 2, 3: 1}
    out: dict[str, int] = {}
    for lbl, rk in ranking_by_label.items():
        cell = label_to_cell[lbl]
        out[cell] = rank_to_points[rk]
    return out


# ---- Anthropic API wrapper ----------------------------------------------


class JudgeClient:
    """Thin wrapper around the Anthropic SDK with prompt-caching."""

    def __init__(self, *, model: str = JUDGE_MODEL, client: Any = None,
                 api_key: str | None = None):
        self.model = model
        if client is not None:
            self._client = client
        else:
            try:
                from anthropic import Anthropic  # local import
            except ImportError as exc:
                raise RuntimeError(
                    "anthropic SDK not installed; "
                    "pip install 'anthropic>=0.40.0' or pass a stub "
                    "client= for testing"
                ) from exc
            self._client = Anthropic(
                api_key=api_key or os.environ.get("ANTHROPIC_API_KEY")
            )

    def ask(self, *, system: str, user: str,
            temperature: float = 0.0,
            max_tokens: int = 256) -> tuple[str, dict[str, int]]:
        """Single judge call. Returns (response_text, usage_dict)."""
        assert "do not use response length" in system.lower(), (
            "JudgeClient.ask: bias-mitigation phrase missing from "
            "system prompt — refusing to call API"
        )
        system_blocks = [{
            "type": "text",
            "text": system,
            "cache_control": {"type": "ephemeral"},
        }]
        resp = self._client.messages.create(
            model=self.model,
            system=system_blocks,
            messages=[{"role": "user", "content": user}],
            max_tokens=max_tokens,
            temperature=temperature,
        )
        text = "".join(
            getattr(b, "text", "") for b in resp.content
            if getattr(b, "type", None) == "text"
        )
        usage = {
            "input_tokens": getattr(resp.usage, "input_tokens", 0),
            "output_tokens": getattr(resp.usage, "output_tokens", 0),
            "cache_read_input_tokens": getattr(
                resp.usage, "cache_read_input_tokens", 0
            ) or 0,
            "cache_creation_input_tokens": getattr(
                resp.usage, "cache_creation_input_tokens", 0
            ) or 0,
        }
        return text, usage


# ---- one judgment -------------------------------------------------------


_RETRY_CLARIFICATION = (
    "Please respond with exactly the ranking in the format "
    "`A: <rank>\nB: <rank>\nC: <rank>` where each rank is 1, 2, or 3 "
    "and each is used exactly once."
)


def _judge_one(
    *,
    persona: str,
    criterion: str,
    prompt_text: str,
    group_records_by_cell: dict[str, dict[str, Any]],
    base_seed: int,
    judge_client: JudgeClient,
    max_retries: int,
    log,
) -> dict[str, Any]:
    """Perform one judge call for one (group, criterion).

    Returns a record (dict) ready to be appended to the output JSONL.
    On API/parse failure exceeding ``max_retries``, the record has
    ``_judge_error=True`` and a non-null ``judge_error`` reason.
    """
    first_rec = next(iter(group_records_by_cell.values()))
    pi = int(first_rec["prompt_index"])
    ti = int(first_rec["trial_index"])
    pre_reg_sha = first_rec.get("pre_reg_doc_sha")

    seed = _label_seed(persona, pi, ti, criterion, base_seed)
    label_to_cell = _randomize_labels(
        list(group_records_by_cell.keys()), seed=seed,
    )
    label_to_response: dict[str, str] = {
        lbl: (group_records_by_cell[c].get("response_text") or "")
        for lbl, c in label_to_cell.items()
    }

    system = _build_system_prompt(persona, criterion)
    user = _build_user_prompt(prompt_text, label_to_response)

    base_record: dict[str, Any] = {
        "persona": persona,
        "prompt_index": pi,
        "prompt_text": prompt_text,
        "trial_index": ti,
        "criterion": criterion,
        "label_to_cell": label_to_cell,
        "judge_model": judge_client.model,
        "judge_seed": seed,
        "pre_reg_doc_sha": pre_reg_sha,
        "timestamp_iso": _dt.datetime.now(_dt.timezone.utc)
            .replace(tzinfo=None).isoformat(timespec="seconds") + "Z",
    }

    last_err: str | None = None
    last_raw: str = ""
    last_usage: dict[str, int] | None = None
    user_msg = user
    for attempt in range(max_retries + 1):
        try:
            raw, usage = judge_client.ask(system=system, user=user_msg)
        except Exception as exc:  # noqa: BLE001
            last_err = f"{type(exc).__name__}: {exc}"
            last_raw = ""
            log(
                f"    judge API error (attempt {attempt + 1}/"
                f"{max_retries + 1}): {last_err}"
            )
            time.sleep(min(1.0 * (attempt + 1), 5.0))
            continue
        last_raw = raw
        last_usage = usage
        parsed = _parse_ranking(raw)
        if parsed is not None:
            composite = _composite_points_by_cell(parsed, label_to_cell)
            record = dict(base_record)
            record.update({
                "ranking_by_label": parsed,
                "composite_points_by_cell": composite,
                "judge_response_raw": raw,
                "judge_usage": usage,
                "judge_attempts": attempt + 1,
            })
            return record
        last_err = "parse failure"
        log(
            f"    judge parse failed (attempt {attempt + 1}/"
            f"{max_retries + 1}); raw={raw!r}"
        )
        user_msg = user + "\n\n" + _RETRY_CLARIFICATION

    record = dict(base_record)
    record.update({
        "_judge_error": True,
        "judge_error": last_err or "unknown",
        "judge_response_raw": last_raw,
        "judge_usage": last_usage,
        "ranking_by_label": None,
        "composite_points_by_cell": None,
        "judge_attempts": max_retries + 1,
    })
    return record


# ---- resumability -------------------------------------------------------


class MalformedJsonlError(RuntimeError):
    """Raised when the existing output JSONL cannot be parsed.

    Mirrors the harness script (``2026-05-16_monologue_length_experiment``)
    convention: the script REFUSES to start in this case rather than
    silently overwriting or skipping records. The user must remove or
    repair the file manually. Exit code 8 (matches harness convention).
    """


def _load_completed_keys(
    out_path: Path,
) -> tuple[set[tuple[str, int, int, str]], list[dict[str, Any]]]:
    """Read the existing output JSONL.

    Returns:
      - ``completed``: set of (persona, prompt_index, trial_index,
        criterion) tuples that have a SUCCESSFUL judgment (no
        ``_judge_error``). These will be skipped on resume.
      - ``existing``: all records already in the file (errored + ok).

    Raises:
        MalformedJsonlError: if any non-empty line fails to parse as
            JSON. Mirrors the harness pattern — silently skipping
            corrupt lines on a 1,280-call resume risks losing or
            double-counting completed judgments.
    """
    if not out_path.exists():
        return set(), []
    completed: set[tuple[str, int, int, str]] = set()
    existing: list[dict[str, Any]] = []
    with out_path.open("r", encoding="utf-8") as fh:
        for lineno, raw in enumerate(fh, start=1):
            line = raw.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError as exc:
                raise MalformedJsonlError(
                    f"{out_path}:{lineno}: invalid JSON: {exc}. "
                    f"Refusing to start. Remove or repair this file "
                    f"manually."
                ) from exc
            if not isinstance(rec, dict):
                raise MalformedJsonlError(
                    f"{out_path}:{lineno}: expected JSON object; "
                    f"got {type(rec).__name__}. Refusing to start."
                )
            existing.append(rec)
            if rec.get("_judge_error"):
                continue
            try:
                key = (
                    str(rec["persona"]),
                    int(rec["prompt_index"]),
                    int(rec["trial_index"]),
                    str(rec["criterion"]),
                )
            except (KeyError, TypeError, ValueError):
                continue
            completed.add(key)
    return completed, existing


# ---- CLI / main ---------------------------------------------------------


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Monologue-length-directive judging stage. "
            "Pre-registration: docs/hypotheses/"
            "2026-05-16_monologue_length_pre_registration.md."
        )
    )
    parser.add_argument("--input", type=Path, required=True,
                        help="Path to harness JSONL (input).")
    parser.add_argument("--output", type=Path, required=True,
                        help="Path to judged JSONL (output, resumable).")
    parser.add_argument("--seed", type=int, default=42,
                        help="Base seed for label randomization.")
    parser.add_argument("--dry-run", action="store_true",
                        help="Skip all API calls; print the plan only.")
    parser.add_argument("--max-retries", type=int, default=3,
                        help="Retry budget per judgment on parse failure.")
    return parser.parse_args(argv)


def _criteria_for(persona: str) -> tuple[str, ...]:
    if persona == "marcus":
        return MARCUS_CRITERIA
    if persona == "jamie":
        return JAMIE_CRITERIA
    raise ValueError(f"unknown persona: {persona!r}")


def _estimate_cost(n_calls: int) -> str:
    """Rough Sonnet 4.6 envelope. Assume ~1500 input tokens (cached
    after first call for the same system) and ~30 output tokens per
    judge call.

    With the call-order optimization in ``main`` (iterate by
    (persona, criterion) outermost), ~159/160 calls per (persona,
    criterion) bucket hit the ephemeral system-prompt cache. Anthropic
    ephemeral cache reads cost ~10% of normal input rate, so the
    effective input-token cost across the run is roughly:

        (1/160) * 1.0  +  (159/160) * 0.10  ~=  0.105

    Round up slightly to 0.11 to account for the user message (which is
    never cached because it varies per call) — but note the user message
    is small (~30 tokens) relative to the 1500-token system prompt, so
    its impact is minor. Cache_factor=0.11 is the post-reorder estimate;
    0.15 was the conservative pre-reorder figure.
    """
    nominal_in = 1500
    nominal_out = 30
    cache_factor = 0.11
    usd = n_calls * (
        nominal_in * cache_factor * _USD_PER_M_INPUT / 1e6
        + nominal_out * _USD_PER_M_OUTPUT / 1e6
    )
    nominal_no_cache = n_calls * (
        nominal_in * _USD_PER_M_INPUT / 1e6
        + nominal_out * _USD_PER_M_OUTPUT / 1e6
    )
    return (
        f"~${usd:.2f} (cache-warmed, ordered) to ${nominal_no_cache:.2f} "
        f"(uncached upper bound)"
    )


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)

    def log(msg: str) -> None:
        print(f"[mlj] {msg}", file=sys.stderr, flush=True)

    in_path: Path = args.input
    out_path: Path = args.output

    try:
        records = _load_input_records(in_path)
    except (FileNotFoundError, ValueError) as exc:
        log(f"FATAL: input load failed: {type(exc).__name__}: {exc}")
        return 2
    log(f"loaded {len(records)} input records from {in_path}")

    schema_keys = {
        "cell", "persona", "prompt_index", "prompt_text",
        "trial_index", "response_text",
    }
    sane = 0
    for r in records:
        if r.get("_error"):
            continue
        if schema_keys.issubset(r.keys()):
            sane += 1
    log(f"schema-sane records (non-error, all required keys): {sane}")

    pre_reg_sha = _verify_pre_reg_consistency(records, log=log)
    if pre_reg_sha:
        log(f"pre_reg_doc_sha={pre_reg_sha}")

    groups, n_err = _group_records(records, log=log)
    log(
        f"grouped: {len(groups)} valid groups, "
        f"{n_err} _error records skipped"
    )
    if not groups:
        log("FATAL: no valid groups; nothing to judge")
        return 2

    # IMPORTANT: order plan_items by (persona, criterion, prompt_index,
    # trial_index) — NOT by group first. Anthropic's ephemeral prompt
    # cache has a ~5-minute TTL; the system prompt is fully determined by
    # (persona, criterion). With 160 groups per (persona, criterion) pair
    # and 8 unique (persona, criterion) system prompts overall, iterating
    # by (persona, criterion) outermost keeps the same system prompt in
    # play for ~160 consecutive calls, yielding ~99% cache-read hits on
    # the system block. Iterating by group first would switch system
    # prompts every call and waste the cache.
    expected_calls = 0
    plan_items: list[tuple[GroupKey, str]] = []
    by_pair: dict[tuple[str, str], list[GroupKey]] = {}
    for key in groups:
        persona = key[0]
        for crit in _criteria_for(persona):
            by_pair.setdefault((persona, crit), []).append(key)
    for (persona, crit) in sorted(by_pair):
        for key in sorted(by_pair[(persona, crit)]):
            # key = (persona, prompt_index, trial_index); since persona
            # matches `persona` for this bucket, sorted(by_pair[...])
            # gives (prompt_index, trial_index) order within the bucket.
            plan_items.append((key, crit))
            expected_calls += 1
    log(
        f"expected judge calls: {expected_calls} "
        f"({len(groups)} groups x 4 criteria)"
    )
    log(
        "call order: (persona, criterion, prompt_index, trial_index) "
        "— optimized for ephemeral prompt-cache reuse on the system block"
    )
    log(f"cost estimate: {_estimate_cost(expected_calls)}")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        completed, existing = _load_completed_keys(out_path)
    except MalformedJsonlError as exc:
        log("FATAL: existing output file is malformed:")
        log(f"  {exc}")
        log(
            "The script refuses to silently skip corrupt lines on "
            "resume. Either delete the file or repair it manually, "
            "then re-run."
        )
        return 8
    log(
        f"resume: {len(completed)} judgments already complete; "
        f"{len(existing)} total records in existing output"
    )

    # The resume filter preserves plan_items order, so `todo` is still
    # in (persona, criterion, prompt_index, trial_index) order — even
    # mid-run resumes keep the cache-friendly traversal.
    todo: list[tuple[GroupKey, str]] = []
    for (key, crit) in plan_items:
        tup = (key[0], key[1], key[2], crit)
        if tup in completed:
            continue
        todo.append((key, crit))
    log(f"to-do this run: {len(todo)} judgments")

    if args.dry_run:
        log("DRY-RUN: skipping all API calls.")
        for i, (key, crit) in enumerate(todo[:5]):
            log(
                f"  [{i}] persona={key[0]} prompt_index={key[1]} "
                f"trial_index={key[2]} criterion={crit}"
            )
        if len(todo) > 5:
            log(f"  ... (+{len(todo) - 5} more)")
        return 0

    try:
        client = JudgeClient(model=JUDGE_MODEL)
    except Exception as exc:  # noqa: BLE001
        log(
            f"FATAL: could not construct JudgeClient: "
            f"{type(exc).__name__}: {exc}"
        )
        return 4

    rewrite_records = [
        r for r in existing if not r.get("_judge_error")
    ]
    with out_path.open("w", encoding="utf-8") as fh:
        for r in rewrite_records:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
        fh.flush()
        os.fsync(fh.fileno())
    log(
        f"resume: dropped {len(existing) - len(rewrite_records)} "
        f"errored records for retry; wrote back "
        f"{len(rewrite_records)} successful records"
    )

    judged = 0
    errors = 0
    total = len(todo)
    with out_path.open("a", encoding="utf-8") as fh:
        for i, (key, crit) in enumerate(todo):
            persona, pi, ti = key
            try:
                rec = _judge_one(
                    persona=persona,
                    criterion=crit,
                    prompt_text=groups[key]["variable"]["prompt_text"],
                    group_records_by_cell=groups[key],
                    base_seed=args.seed,
                    judge_client=client,
                    max_retries=args.max_retries,
                    log=log,
                )
            except Exception as exc:  # noqa: BLE001
                errors += 1
                log(
                    f"  TRIAL FAILED [{i}/{total}] persona={persona} "
                    f"prompt={pi} trial={ti} criterion={crit}: "
                    f"{type(exc).__name__}: {exc}"
                )
                continue
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
            fh.flush()
            os.fsync(fh.fileno())
            if rec.get("_judge_error"):
                errors += 1
            else:
                judged += 1
            if (judged + errors) % 25 == 0:
                log(
                    f"  progress {judged + errors}/{total} "
                    f"(judged={judged} errors={errors})"
                )

    total_attempted = judged + errors
    success_rate = (
        f"{(judged / total_attempted * 100):.1f}%"
        if total_attempted else "n/a"
    )
    log(
        f"summary: judged={judged} errors={errors} "
        f"total={total_attempted} success_rate={success_rate}"
    )
    return 0 if errors == 0 else 6


if __name__ == "__main__":
    raise SystemExit(main())
