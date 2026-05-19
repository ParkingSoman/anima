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


def _format_subsystem_errors_md(errors: list[dict]) -> str:
    """Render a per-turn generation-errors block.

    Returns empty string when ``errors`` is empty (no block printed). Each
    error explicitly states WHICH subsystem in the pipeline failed (full
    subsystem name, not a four-step collapse), the exception type, the full
    error message (no truncation beyond the upstream 500-char cap), and the
    number of attempts the adapter made before giving up.
    """
    if not errors:
        return ""
    lines = ["", "⚠️ **Generation errors this turn:**", ""]
    for e in errors:
        sub = e.get("subsystem", "?")
        et = e.get("error_type", "?")
        attempts = e.get("attempts", 0)
        msg = (e.get("message") or "").strip() or "(no message provided)"
        lines.append(f"- **{sub}** failed after {attempts} attempts → fallback used")
        lines.append(f"    - error type: `{et}`")
        lines.append(f"    - error message: {msg}")
        lines.append(f"    - attempts: {attempts}")
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

    def write_header(self, anima: "Anima") -> None:
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

        scene_tag = trace.appraisal.get("appraisal_scene_tag", "")
        primary_emotion = trace.appraisal.get("primary_emotion", "")

        retrieved_lines: list[str] = []
        for r in trace.retrieved:
            score = r.get("score", 0.0)
            label = (
                r.get("reconstructed_framing")
                or r.get("retrieval_reason")
                or r.get("id", "?")
            )
            retrieved_lines.append(f"- [{score:.2f}] {label}")
        retrieved_block = "\n".join(retrieved_lines) if retrieved_lines else "_(none surfaced)_"

        pred = trace.prediction or {}
        pred_block = (
            f"- next_intent_label: `{pred.get('next_intent_label', '?')}`\n"
            f"- content_hint: {pred.get('content_hint', '?')}\n"
            f"- confidence: {float(pred.get('confidence', 0.0)):.2f}"
        )

        surprise_block = ""
        s = trace.surprise_from_last_turn or {}
        if s:
            prior = s.get("predicted_intent") or {}
            surprise_block = (
                f"\n**Surprise (from prior turn):**\n"
                f"- surprise_score: {float(s.get('surprise_score', 0.0)):.2f}\n"
                f"- prior predicted intent: "
                f"`{prior.get('next_intent_label', '?')}` / "
                f"{prior.get('content_hint', '?')}\n"
            )

        mood_tbl = _delta_table(trace.mood_before, trace.mood_after)
        drives_tbl = _delta_table(trace.drives_before, trace.drives_after)

        # E8 / F1: surface generation errors AND model-silence flags inline
        # (above the inner trace) so the casual reader can see at a glance
        # whether the turn was clean, glitched, or chosen-silent.
        warning_block = _format_subsystem_errors_md(trace.subsystem_errors)
        silence_block = _format_silences_md(getattr(trace, "silences", []) or [])

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
        md_lines += [
            "<details><summary>inner trace</summary>",
            "",
            "**Inner monologue:**",
            "",
            "```",
            trace.monologue,
            "```",
            "",
            f"**Appraisal:** scene-tag = `{scene_tag}` · primary emotion = `{primary_emotion}`",
            "",
            "**Retrieved memories:**",
            "",
            retrieved_block,
            "",
            "**User prediction (this turn → next):**",
            "",
            pred_block,
            "",
            surprise_block,
            "**Mood Δ:**",
            "",
            mood_tbl,
            "",
            "**Drives Δ:**",
            "",
            drives_tbl,
            "",
            "</details>",
            "",
        ]
        with self.md_path.open("a", encoding="utf-8") as fh:
            fh.write("\n".join(md_lines) + "\n")

        turn_entry = trace.to_jsonable()
        # The JSON view adds top-level conveniences to the per-turn record so
        # consumers don't have to dig into the trace:
        #   * ``status``    — "ok" or "failed"
        #   * ``errors``    — duplicate of ``subsystem_errors`` at the top level
        #   * ``silences``  — model-silence flags (see F1)
        #   * ``retry_of``  — when this turn is a /retry, the prior turn's idx
        turn_entry["status"] = "ok"
        turn_entry["errors"] = list(trace.subsystem_errors)
        turn_entry["silences"] = list(getattr(trace, "silences", []) or [])
        turn_entry["retry_of"] = getattr(trace, "retry_of", None)
        self._json["turns"].append(turn_entry)
        self._json["state_trajectory"].append({
            "turn": turn_idx,
            "mood_after": dict(trace.mood_after),
            "drives_after": dict(trace.drives_after),
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
