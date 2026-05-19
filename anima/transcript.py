"""Per-session transcript writer for chat sessions.

Writes two co-located files per session:
  * a Markdown narrative (human-readable; inner thoughts in collapsed
    <details> blocks so a casual reader sees only the dialogue)
  * a JSON dump (machine-readable; full per-turn TurnTrace + a
    state_trajectory list of mood/drives at every turn)

Both files are flushed on every ``write_turn`` so a Ctrl-C mid-session
does not lose work. No long-lived file handles are held — each turn
re-opens, writes, and closes.

This is intentionally decoupled from :class:`anima.persistence.store.AnimaStore`
(which is the cross-session state store). Transcripts are session-bound,
per-user, and gitignored.
"""

from __future__ import annotations

import datetime as _dt
import json
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from anima.core import Anima, TurnTrace


def _iso_now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")


def _iso_for_filename() -> str:
    # Filenames can't contain ':' on some platforms; use a compact UTC stamp.
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _delta_table(before: dict[str, Any], after: dict[str, Any]) -> str:
    """Render a `key | before | after | Δ` Markdown table.

    Numeric values only — non-numeric leaves Δ blank. Nested dicts are
    flattened with a `parent.child` key (handles the mood ``discrete``
    sub-dict).
    """
    def _flat(d: dict[str, Any], prefix: str = "") -> dict[str, Any]:
        out: dict[str, Any] = {}
        for k, v in d.items():
            key = f"{prefix}{k}"
            if isinstance(v, dict):
                out.update(_flat(v, prefix=f"{key}."))
            else:
                out[key] = v
        return out

    fb = _flat(before)
    fa = _flat(after)
    keys = sorted(set(fb) | set(fa))
    lines = ["| key | before | after | Δ |", "| --- | --- | --- | --- |"]
    for k in keys:
        b = fb.get(k)
        a = fa.get(k)
        if isinstance(b, (int, float)) and isinstance(a, (int, float)):
            delta = f"{a - b:+.3f}"
            lines.append(f"| {k} | {b:.3f} | {a:.3f} | {delta} |")
        else:
            lines.append(f"| {k} | {b!r} | {a!r} |  |")
    return "\n".join(lines)


def _format_raw_message_md(raw: dict | None) -> list[str]:
    """Render a raw model-output block under an EmptyResponseAfterRetries entry.

    Investigation aid: when DeepSeek-flash (or any provider) returns
    .content="" + finish_reason="length", we want to see what the model
    ACTUALLY produced — the answer is almost always "reasoning_content
    overflowed and content stayed empty", but it could also be
    tool_calls, refusal text, or genuinely empty all the way down.

    The full untruncated raw_message dict is preserved in the JSON
    transcript; here we render a compact, operator-readable summary
    with reasoning_content truncated to ~400 chars.
    """
    if not isinstance(raw, dict):
        return ["    - **raw model output (last attempt):** _(not captured)_"]

    lines: list[str] = ["    - **raw model output (last attempt):**"]

    # Anthropic-shape: content_blocks list rather than scalar content.
    if "content_blocks" in raw:
        blocks = raw.get("content_blocks") or []
        if not blocks:
            lines.append("        - content_blocks: `(none)`")
        else:
            for i, b in enumerate(blocks):
                btype = b.get("type") if isinstance(b, dict) else None
                btext = b.get("text") if isinstance(b, dict) else None
                btext_s = (btext or "").strip()
                if btext_s and len(btext_s) > 400:
                    btext_s = btext_s[:400] + "... [truncated, full content in JSON parallel]"
                lines.append(
                    f"        - block[{i}] type=`{btype}` text=`{btext_s or '(empty)'}`"
                )
        sr = raw.get("stop_reason")
        lines.append(f"        - role: `{raw.get('role', '?')}`")
        if sr is not None:
            lines.append(f"        - stop_reason: `{sr}`")
        return lines

    # OpenAI/OpenRouter-shape. NOTE: OpenRouter returns DeepSeek's
    # reasoning under the ``reasoning`` field (not ``reasoning_content``
    # — that was an early-spec name). We check BOTH so this code works
    # against any OpenAI-compat provider that exposes either spelling.
    rc = raw.get("reasoning_content") or raw.get("reasoning")
    rc_field_name = "reasoning_content" if raw.get("reasoning_content") else "reasoning"
    if isinstance(rc, str) and rc.strip():
        n = len(rc)
        rc_show = rc.strip()
        if len(rc_show) > 400:
            rc_show = rc_show[:400] + "... [truncated, full content in JSON parallel]"
        # Escape backticks in the rendered content so the inline code
        # span doesn't get broken; replace with a similar glyph.
        rc_show = rc_show.replace("`", "ʼ")
        lines.append(f"        - {rc_field_name} ({n} chars): `{rc_show}`")
    else:
        lines.append("        - reasoning: `(none)`")

    content = raw.get("content")
    if isinstance(content, str) and content.strip():
        c_show = content.strip()
        if len(c_show) > 400:
            c_show = c_show[:400] + "... [truncated, full content in JSON parallel]"
        c_show = c_show.replace("`", "ʼ")
        lines.append(f"        - content: `{c_show}`")
    else:
        lines.append("        - content: `(empty)`")

    tc = raw.get("tool_calls")
    if tc:
        lines.append(f"        - tool_calls: `{tc}`")
    else:
        lines.append("        - tool_calls: `None`")

    fc = raw.get("function_call")
    if fc:
        lines.append(f"        - function_call: `{fc}`")

    refusal = raw.get("refusal")
    if refusal:
        lines.append(f"        - refusal: `{refusal}`")

    annotations = raw.get("annotations")
    if annotations:
        lines.append(f"        - annotations: `{annotations}`")

    lines.append(f"        - role: `{raw.get('role', '?')}`")

    # If everything substantive was empty, say so explicitly. ``rc``
    # collapses both spellings (reasoning_content / reasoning) so the
    # check is single-line.
    has_any = bool(
        (isinstance(rc, str) and rc.strip())
        or (isinstance(content, str) and content.strip())
        or tc or fc or refusal
    )
    if not has_any:
        lines.append("        - (model produced nothing in any inspected field)")

    return lines


def _format_subsystem_errors_md(errors: list[dict]) -> str:
    """Render a per-turn generation-errors block.

    Returns empty string when ``errors`` is empty (no block printed). Each
    error explicitly states WHICH subsystem in the pipeline failed (full
    subsystem name, not a four-step collapse), the exception type, the full
    error message (no truncation beyond the upstream 500-char cap), and the
    number of attempts the adapter made before giving up.

    Fix 1: when ``error_type == 'EmptyResponseAfterRetries'``, swap the
    leading sentence to "returned empty response on all N attempts" so a
    transcript reader can immediately distinguish "the LLM produced
    nothing despite retries" from "the call raised an exception". Format
    chosen to mirror the spec exactly so transcripts are grep-able for
    the EmptyResponseAfterRetries signature.

    Investigation: for EmptyResponseAfterRetries entries that carry a
    ``raw_message`` dict, render a compact summary of what the model
    actually produced (reasoning_content / tool_calls / etc.). Full
    untruncated raw_message is in the JSON sidecar.
    """
    if not errors:
        return ""
    lines = ["", "⚠️ **Generation errors this turn:**", ""]
    for e in errors:
        sub = e.get("subsystem", "?")
        et = e.get("error_type", "?")
        attempts = e.get("attempts", 0)
        msg = (e.get("message") or "").strip() or "(no message provided)"
        if et == "EmptyResponseAfterRetries":
            lines.append(
                f"- **{sub}** returned empty response on all {attempts} attempts → fallback used"
            )
        else:
            lines.append(f"- **{sub}** failed after {attempts} attempts → fallback used")
        lines.append(f"    - error type: `{et}`")
        lines.append(f"    - error message: {msg}")
        lines.append(f"    - attempts: {attempts}")
        if et == "EmptyResponseAfterRetries":
            lines.extend(_format_raw_message_md(e.get("raw_message")))
    lines.append("")
    return "\n".join(lines)


def _format_silences_md(silences: list[dict]) -> str:
    """Render a per-turn "model chose silence" block.

    Distinct from generation errors: these are subsystem calls that SUCCEEDED
    but returned empty/trivial content. The reader needs to see which
    silences happened so a flat dialogue isn't mis-attributed to a glitch.
    Returns empty string when no silences fired.
    """
    if not silences:
        return ""
    lines = ["", "🤐 **Model chose silence this turn:**", ""]
    for s in silences:
        sub = s.get("subsystem", "?")
        detail = (s.get("detail") or "").strip() or "(no detail)"
        lines.append(f"- **{sub}** {detail}")
    lines.append("")
    return "\n".join(lines)


class TranscriptWriter:
    def __init__(
        self,
        persona_name: str,
        session_id: str,
        config_path: Path,
        provider: str,
        output_dir: Path = Path("transcripts"),
    ) -> None:
        self.persona_name = persona_name
        self.session_id = session_id
        self.config_path = Path(config_path)
        self.provider = provider
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        stamp = _iso_for_filename()
        stem = f"{persona_name}_{session_id}_{stamp}"
        self.md_path: Path = self.output_dir / f"{stem}.md"
        self.json_path: Path = self.output_dir / f"{stem}.json"

        # In-memory JSON model. Flushed to disk on every write_turn so a
        # crash leaves a complete record up to the last completed turn.
        self._json: dict[str, Any] = {
            "meta": {},
            "turns": [],
            "state_trajectory": [],
        }
        self._header_written = False
        self._initial_mood: dict[str, Any] | None = None
        self._initial_drives: dict[str, Any] | None = None

    # ---------- header

    def write_header(self, anima: "Anima", *, architecture: str = "head") -> None:
        bio = anima.cfg.biography
        start_ts = _iso_now()
        # The Anima exposes model identity only via the LLM adapter; we keep
        # it loose because not every adapter (e.g. FakeAdapter) defines model.
        model = getattr(anima.llm, "model", None) or getattr(anima.llm, "name", "unknown")
        # F-A: record the adapter-level retry policy + the response_generator's
        # heavier per-call override so a transcript reader can see exactly how
        # tolerant the session was to transient LLM glitches. The default
        # adapter retry config is ``max_attempts=3`` (= initial + 2 retries).
        adapter_retry = getattr(anima.llm, "retry_cfg", None)
        adapter_max_attempts = getattr(adapter_retry, "max_attempts", None)
        # The response_generator override is hard-coded in core.py; we mirror
        # the literal here rather than reach into core to keep the writer
        # decoupled. If the constant ever changes there, this is the only
        # place the transcript header needs to follow.
        response_generator_max_attempts = 5
        retry_policy = {
            "adapter_max_attempts": adapter_max_attempts,
            "subsystem_retries": (
                (adapter_max_attempts - 1) if isinstance(adapter_max_attempts, int) else None
            ),
            "response_generator_max_attempts": response_generator_max_attempts,
            "response_generator_retries": response_generator_max_attempts - 1,
            "policy_summary": (
                f"{(adapter_max_attempts - 1) if isinstance(adapter_max_attempts, int) else '?'} "
                f"retries per subsystem + "
                f"{response_generator_max_attempts - 1} retries for the response, "
                f"then graceful fallback"
            ),
        }
        meta: dict[str, Any] = {
            "persona_name": bio.name,
            "config_persona_key": self.persona_name,
            "session_id": self.session_id,
            "config_path": str(self.config_path),
            "provider": self.provider,
            "model": model,
            "biography_one_line": bio.one_line,
            "started_at": start_ts,
            "retry_policy": retry_policy,
            "architecture": architecture,
        }
        self._json["meta"] = meta

        md_lines = [
            "---",
            f"persona: {bio.name}",
            f"session_id: {self.session_id}",
            f"config_path: {self.config_path}",
            f"provider: {self.provider}",
            f"model: {model}",
            f"started_at: {start_ts}",
            f"retry_policy: {retry_policy['policy_summary']}",
            f"architecture: {architecture}",
            "---",
            "",
            f"# Transcript — {bio.name} ({self.session_id})",
            "",
            f"> {bio.one_line}",
            "",
        ]
        with self.md_path.open("w", encoding="utf-8") as fh:
            fh.write("\n".join(md_lines) + "\n")
        self._flush_json()
        self._header_written = True

    # ---------- per-turn

    def write_turn(
        self,
        turn_idx: int,
        user_msg: str,
        anima_reply: str,
        trace: "TurnTrace",
    ) -> None:
        # Capture turn-0 baselines for the finalize() trajectory summary.
        if self._initial_mood is None:
            self._initial_mood = dict(trace.mood_before)
        if self._initial_drives is None:
            self._initial_drives = dict(trace.drives_before)

        # Fix 2 (v1 compatibility): every TurnTrace field below uses
        # ``getattr(trace, ..., default)`` so the writer accepts both
        # head's larger TurnTrace and v1's smaller one. Sections that
        # depend on absent v1 fields (retrieved memories, prediction,
        # surprise) are conditionally OMITTED from the markdown — not
        # rendered as "(none surfaced)" placeholders — to keep v1
        # transcripts free of cognitive-architecture noise that
        # isn't real on that architecture.
        appraisal = getattr(trace, "appraisal", {}) or {}
        scene_tag = appraisal.get("appraisal_scene_tag", "")
        primary_emotion = appraisal.get("primary_emotion", "")

        retrieved = getattr(trace, "retrieved", None)
        retrieved_lines: list[str] = []
        for r in (retrieved or []):
            score = r.get("score", 0.0)
            label = (
                r.get("reconstructed_framing")
                or r.get("retrieval_reason")
                or r.get("id", "?")
            )
            retrieved_lines.append(f"- [{score:.2f}] {label}")
        # ``retrieved is None`` means the trace doesn't carry the field at all
        # (v1). ``retrieved == []`` means head ran and surfaced zero memories.
        # We distinguish the two: omit the heading entirely on v1, but show
        # "(none surfaced)" on head when retrieval ran and returned nothing.
        has_retrieved_section = retrieved is not None
        retrieved_block = "\n".join(retrieved_lines) if retrieved_lines else "_(none surfaced)_"

        prediction = getattr(trace, "prediction", None)
        has_prediction_section = bool(prediction)
        pred_block = ""
        if prediction:
            pred_block = (
                f"- next_intent_label: `{prediction.get('next_intent_label', '?')}`\n"
                f"- content_hint: {prediction.get('content_hint', '?')}\n"
                f"- confidence: {float(prediction.get('confidence', 0.0)):.2f}"
            )

        surprise_block = ""
        s = getattr(trace, "surprise_from_last_turn", None) or {}
        if s:
            prior = s.get("predicted_intent") or {}
            surprise_block = (
                f"\n**Surprise (from prior turn):**\n"
                f"- surprise_score: {float(s.get('surprise_score', 0.0)):.2f}\n"
                f"- prior predicted intent: "
                f"`{prior.get('next_intent_label', '?')}` / "
                f"{prior.get('content_hint', '?')}\n"
            )

        mood_before = getattr(trace, "mood_before", {}) or {}
        mood_after = getattr(trace, "mood_after", {}) or {}
        drives_before = getattr(trace, "drives_before", {}) or {}
        drives_after = getattr(trace, "drives_after", {}) or {}
        mood_tbl = _delta_table(mood_before, mood_after)
        drives_tbl = _delta_table(drives_before, drives_after)

        # E8 / F1: surface generation errors AND model-silence flags inline
        # (above the inner trace) so the casual reader can see at a glance
        # whether the turn was clean, glitched, or chosen-silent.
        subsystem_errors = list(getattr(trace, "subsystem_errors", None) or [])
        silences = list(getattr(trace, "silences", None) or [])
        warning_block = _format_subsystem_errors_md(subsystem_errors)
        silence_block = _format_silences_md(silences)

        # F2: retry-labeled turn header — when this turn is a /retry of an
        # earlier turn, the markdown header says so. The JSON entry carries
        # the structured ``retry_of`` field.
        retry_of = getattr(trace, "retry_of", None)
        header = (
            f"### Turn {turn_idx} — retry of turn {retry_of}"
            if retry_of is not None
            else f"### Turn {turn_idx}"
        )
        md_lines = [
            header,
            "",
            f"**you:** {user_msg}",
            "",
            f"**{self._json['meta'].get('persona_name', self.persona_name)}:** {anima_reply}",
            "",
        ]
        if warning_block:
            md_lines.append(warning_block)
        if silence_block:
            md_lines.append(silence_block)
        monologue = getattr(trace, "monologue", "") or ""

        # Fix 1 (user-requested expansion): render the FULL output of every
        # subsystem, not just a one-line appraisal summary. We pull from the
        # raw trace dicts so v1 (smaller Appraisal/Perception) and head both
        # work — missing fields are silently skipped via dict.get with None
        # defaults, not rendered as None/0.0.
        perception_dict = getattr(trace, "perception", {}) or {}

        def _fmt_float(v: Any) -> str:
            try:
                return f"{float(v):+.2f}" if isinstance(v, (int, float)) else str(v)
            except Exception:
                return str(v)

        # PERCEPTION block — built from the full perception dict.
        perception_lines: list[str] = []
        if perception_dict:
            literal = perception_dict.get("literal_content")
            intent = perception_dict.get("perceived_intent")
            valence = perception_dict.get("perceived_valence")
            demands = perception_dict.get("perceived_demands")
            salient = perception_dict.get("salient_features")
            if literal is not None:
                perception_lines.append(f"- literal_content: {literal}")
            if intent is not None:
                perception_lines.append(f"- perceived_intent: {intent}")
            if isinstance(valence, (int, float)):
                perception_lines.append(f"- perceived_valence: {float(valence):+.2f}")
            if demands is not None:
                demands_str = "; ".join(demands) if demands else "—"
                perception_lines.append(f"- perceived_demands: {demands_str}")
            if salient is not None:
                salient_str = "; ".join(salient) if salient else "—"
                perception_lines.append(f"- salient_features: {salient_str}")

        # APPRAISAL block — full field expansion. Numeric fields are rendered
        # with sign; string scalars verbatim. Missing fields are silently
        # skipped so v1's smaller Appraisal dataclass still renders cleanly.
        appraisal_lines: list[str] = []
        appraisal_scalar_keys = [
            ("appraisal_scene_tag", "appraisal_scene_tag", str),
            ("primary_emotion", "primary_emotion", str),
            ("relevance", "relevance", float),
            ("goal_congruence", "goal_congruence", float),
            ("ego_relevance", "ego_relevance", float),
            ("coping_potential", "coping_potential", float),
            ("future_expectancy", "future_expectancy", float),
        ]
        for label, key, kind in appraisal_scalar_keys:
            v = appraisal.get(key)
            if v is None:
                continue
            if kind is float and isinstance(v, (int, float)):
                appraisal_lines.append(f"- {label}: {float(v):+.2f}")
            else:
                appraisal_lines.append(f"- {label}: `{v}`")
        # Appraisal also carries mood/drive perturbation deltas. Render the
        # scalar mood deltas inline, plus the discrete-emotion and drive-delta
        # dicts as small tables when non-empty.
        mood_dv = appraisal.get("mood_dv")
        mood_da = appraisal.get("mood_da")
        mood_dd = appraisal.get("mood_dd")
        if any(isinstance(v, (int, float)) for v in (mood_dv, mood_da, mood_dd)):
            parts = []
            if isinstance(mood_dv, (int, float)):
                parts.append(f"Δv={float(mood_dv):+.2f}")
            if isinstance(mood_da, (int, float)):
                parts.append(f"Δa={float(mood_da):+.2f}")
            if isinstance(mood_dd, (int, float)):
                parts.append(f"Δd={float(mood_dd):+.2f}")
            appraisal_lines.append("- mood perturbation: " + ", ".join(parts))
        discrete_deltas = appraisal.get("discrete_deltas") or {}
        if isinstance(discrete_deltas, dict) and discrete_deltas:
            appraisal_lines.append("- discrete emotion deltas:")
            for k, v in discrete_deltas.items():
                vfmt = f"{float(v):+.2f}" if isinstance(v, (int, float)) else str(v)
                appraisal_lines.append(f"    - {k}: {vfmt}")
        drive_deltas_a = appraisal.get("drive_deltas") or {}
        if isinstance(drive_deltas_a, dict) and drive_deltas_a:
            appraisal_lines.append("- drive deltas:")
            for k, v in drive_deltas_a.items():
                vfmt = f"{float(v):+.2f}" if isinstance(v, (int, float)) else str(v)
                appraisal_lines.append(f"    - {k}: {vfmt}")

        # SELF-MONITOR block — Phase 2+ encoding writes an EpisodicEvent at the
        # end of each turn. The TurnTrace today doesn't expose those encoded
        # fields directly, so we look for any of a few plausible attribute
        # names and render whatever's present. If the trace carries nothing,
        # we leave a small placeholder note so it's clear this section is
        # intentional and just empty for this architecture/turn.
        self_monitor_lines: list[str] = []
        for attr in ("self_monitor", "self_monitor_deltas", "encoding", "encoded_event"):
            sm = getattr(trace, attr, None)
            if sm:
                if isinstance(sm, dict):
                    for k, v in sm.items():
                        self_monitor_lines.append(f"- {k}: {v}")
                else:
                    self_monitor_lines.append(f"- {attr}: {sm}")
                break

        md_lines += [
            "<details><summary>inner trace</summary>",
            "",
        ]
        # Stable order: perception → appraisal → memory → prediction → surprise
        # → mood/drives → monologue → response.
        if perception_lines:
            md_lines += ["**Perception:**", ""] + perception_lines + [""]
        if appraisal_lines:
            md_lines += ["**Appraisal:**", ""] + appraisal_lines + [""]
        else:
            # Backwards-compatible one-liner when the trace carries no
            # appraisal at all (shouldn't happen in practice).
            md_lines += [
                f"**Appraisal:** scene-tag = `{scene_tag}` · primary emotion = `{primary_emotion}`",
                "",
            ]
        if has_retrieved_section:
            md_lines += [
                "**Retrieved memories:**",
                "",
                retrieved_block,
                "",
            ]
        if has_prediction_section:
            md_lines += [
                "**User prediction (this turn → next):**",
                "",
                pred_block,
                "",
            ]
        if surprise_block:
            md_lines.append(surprise_block)
        md_lines += [
            "**Mood Δ:**",
            "",
            mood_tbl,
            "",
            "**Drives Δ:**",
            "",
            drives_tbl,
            "",
        ]
        if self_monitor_lines:
            md_lines += ["**Self-monitor:**", ""] + self_monitor_lines + [""]
        else:
            md_lines += [
                "**Self-monitor:** _(no self-monitor fields on this trace)_",
                "",
            ]
        md_lines += [
            "**Inner monologue:**",
            "",
            "```",
            monologue,
            "```",
            "",
            "</details>",
            "",
        ]
        with self.md_path.open("a", encoding="utf-8") as fh:
            fh.write("\n".join(md_lines) + "\n")

        # Build a JSON turn entry that's resilient to traces without
        # to_jsonable (v1's TurnTrace doesn't define one). When available,
        # use it; otherwise serialize the known fields by hand.
        to_jsonable = getattr(trace, "to_jsonable", None)
        if callable(to_jsonable):
            turn_entry = to_jsonable()
        else:
            turn_entry = {
                "user_msg": getattr(trace, "user_msg", user_msg),
                "perception": dict(getattr(trace, "perception", {}) or {}),
                "appraisal": dict(appraisal),
                "monologue": monologue,
                "mood_before": dict(mood_before),
                "mood_after": dict(mood_after),
                "drives_before": dict(drives_before),
                "drives_after": dict(drives_after),
                "response": getattr(trace, "response", anima_reply),
                "usage": dict(getattr(trace, "usage", {}) or {}),
            }
        # The JSON view adds top-level conveniences to the per-turn record so
        # consumers don't have to dig into the trace:
        #   * ``status``    — "ok" or "failed"
        #   * ``errors``    — duplicate of ``subsystem_errors`` at the top level
        #   * ``silences``  — model-silence flags (see F1)
        #   * ``retry_of``  — when this turn is a /retry, the prior turn's idx
        turn_entry["status"] = "ok"
        turn_entry["errors"] = list(subsystem_errors)
        turn_entry["silences"] = list(silences)
        turn_entry["retry_of"] = retry_of
        self._json["turns"].append(turn_entry)
        self._json["state_trajectory"].append({
            "turn": turn_idx,
            "mood_after": dict(mood_after),
            "drives_after": dict(drives_after),
        })
        self._flush_json()

    def write_failed_turn(
        self,
        turn_idx: int,
        user_msg: str,
        exception: BaseException,
    ) -> None:
        """Record a turn where response generation failed completely.

        The user's message is preserved verbatim (the whole point of
        ``/retry``); the persona reply slot carries a generated-failure
        placeholder. The markdown block uses a ❌ marker so the reader
        cannot mistake a failed turn for a successful one with a strange
        reply. The full exception message is included so the reader can see
        WHY the turn failed without consulting logs.
        """
        persona_name = self._json["meta"].get("persona_name", self.persona_name)
        err_type = type(exception).__name__
        err_msg = str(exception) or err_type
        # ResponseGenerationFailed exposes the underlying cause and attempts;
        # surface both so the reader has full context. Defensively duck-typed:
        # any exception that wraps a last_error / attempts is supported.
        attempts = getattr(exception, "attempts", None)
        last_error = getattr(exception, "last_error", None)
        last_error_type = type(last_error).__name__ if last_error is not None else None
        last_error_msg = str(last_error) if last_error is not None else None
        md_lines = [
            f"### Turn {turn_idx} — ❌ FAILED",
            "",
            f"**you:** {user_msg}",
            "",
            f"**{persona_name}:** [generation failed: {err_msg}]",
            "",
            "⚠️ **Generation errors this turn:**",
            "",
            f"- **response_generator** failed completely → no reply produced",
            f"    - error type: `{err_type}`",
            f"    - error message: {err_msg}",
        ]
        if attempts is not None:
            md_lines.append(f"    - attempts: {attempts}")
        if last_error_type is not None:
            md_lines.append(f"    - underlying error type: `{last_error_type}`")
        if last_error_msg:
            md_lines.append(f"    - underlying error message: {last_error_msg}")
        md_lines += [
            "",
            "> Your message is preserved and can be retried with `/retry`.",
            "",
        ]
        with self.md_path.open("a", encoding="utf-8") as fh:
            fh.write("\n".join(md_lines) + "\n")

        self._json["turns"].append({
            "turn": turn_idx,
            "user_msg": user_msg,
            "status": "failed",
            "error": {
                "type": err_type,
                "message": err_msg,
                "attempts": attempts,
                "last_error_type": last_error_type,
                "last_error_message": last_error_msg,
            },
        })
        # state_trajectory is intentionally NOT appended on a failed turn —
        # there's no post-turn state delta to record.
        self._flush_json()

    # ---------- finalize

    def finalize(self, anima: "Anima") -> None:
        traj = self._json["state_trajectory"]
        total = len(traj)
        first_mood = self._initial_mood or {}
        first_drives = self._initial_drives or {}
        last_mood = traj[-1]["mood_after"] if traj else {}
        last_drives = traj[-1]["drives_after"] if traj else {}

        snapshot = anima.observe()
        snapshot_json = json.dumps(snapshot, indent=2, default=str)

        md_lines = [
            "",
            "## State trajectory summary",
            "",
            f"- total turns: **{total}**",
            "",
            "**Mood (first → last):**",
            "",
            _delta_table(first_mood, last_mood) if traj else "_(no turns recorded)_",
            "",
            "**Drives (first → last):**",
            "",
            _delta_table(first_drives, last_drives) if traj else "_(no turns recorded)_",
            "",
            "**Final state snapshot:**",
            "",
            "```json",
            snapshot_json,
            "```",
            "",
        ]
        with self.md_path.open("a", encoding="utf-8") as fh:
            fh.write("\n".join(md_lines) + "\n")

        self._json["finalized_at"] = _iso_now()
        self._flush_json()

    # ---------- internal

    def _flush_json(self) -> None:
        with self.json_path.open("w", encoding="utf-8") as fh:
            json.dump(self._json, fh, indent=2, default=str)
