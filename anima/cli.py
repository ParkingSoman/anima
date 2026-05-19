"""CLI for interactive sessions and quick smoke tests."""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from pathlib import Path

from rich.columns import Columns
from rich.console import Console
from rich.panel import Panel

from anima.core import Anima
from anima.llm import make_adapter
from anima.llm.retry import EmptyResponseAfterRetries
from anima.persistence.store import AnimaStore
from anima.subsystems.errors import ResponseGenerationFailed
from anima.transcript import TranscriptWriter
from verification.baseline import BaselineAnima


def _resolve_anima_class(version: str, console: Console):
    """Resolve which Anima implementation to instantiate.

    'head' (default) → current code.
    'v1' → frozen Phase-1 snapshot. We import it lazily so a missing/broken
    snapshot doesn't break the head CLI.
    """
    if version == "v1":
        try:
            from anima_v1.core import Anima as AnimaV1  # noqa: WPS433 — lazy
            return AnimaV1
        except Exception as exc:  # pragma: no cover — defensive
            console.print(
                f"[yellow]warning:[/yellow] anima_v1 unavailable ({exc!r}); "
                "falling back to head."
            )
            return Anima
    return Anima


def _persona_name_from_config(config_path: Path) -> str:
    """Derive a stable per-Anima persona name from the config filename.

    e.g. ``anima/config/presets/marcus.yaml`` → ``"marcus"``. This is what the
    AnimaStore directory is keyed on.
    """
    return Path(config_path).stem


def cmd_chat(args: argparse.Namespace) -> int:
    console = Console()
    AnimaCls = _resolve_anima_class(args.version, console)
    llm = make_adapter(args.provider)

    # E6: per-persona AnimaStore wired in by default. Cross-session memory is
    # the point of Phase 2 — there's no good reason for the chat CLI to be
    # the one entrypoint that DOESN'T persist.
    persona = _persona_name_from_config(args.config)
    store_root = Path(args.store_root)
    store = AnimaStore(persona, root=store_root)

    # Session id: --session-id resumes an existing named session; default
    # mints a fresh UUID4 so a vanilla `anima chat` starts a clean transcript.
    session_id = args.session_id or f"s-{uuid.uuid4().hex[:8]}"

    # Construct via from_config_path to keep config-loading semantics, then
    # rebuild with store wiring. (from_config_path doesn't take store=, so we
    # pass through the long-form ctor.)
    from anima.config import load_config  # local import: cheap, avoids import-order coupling
    cfg = load_config(args.config)
    # Fix 2: branch on architecture version.
    #   * head — full Phase-2 wiring (store, autosave, session id, theory of
    #     mind, retrieval, etc.). The default.
    #   * v1 — frozen Phase-1 Anima. Its constructor accepts only
    #     ``cfg, llm=, ablate_monologue_length=``. No store, no session id,
    #     no rollback. We construct it bare and disable persistence.
    if args.version == "v1":
        anima = AnimaCls(cfg, llm=llm)
        persistence_enabled = False
    else:
        anima = AnimaCls(cfg, llm=llm, store=store, autosave_every=3)
        anima.set_session_id(session_id)
        persistence_enabled = True

    # E7: per-session transcript writer. Always on (the spec asks for the
    # transcript regardless of mode); --blind only changes what the operator
    # is allowed to *see* live.
    transcript = TranscriptWriter(
        persona_name=persona,
        session_id=session_id,
        config_path=Path(args.config),
        provider=args.provider,
        output_dir=Path(args.transcript_dir),
    )
    transcript.write_header(anima, architecture=args.version)

    blind = bool(getattr(args, "blind", False))
    hidden_notice = (
        f"[dim](hidden in blind mode; see transcript at "
        f"{transcript.md_path} when the session ends)[/dim]"
    )

    intro_extra = ""
    if blind:
        intro_extra = (
            "\n[bold yellow]blind mode[/bold yellow] — inner trace is not shown "
            "during the session; full transcript will be written to disk at the end."
        )
    # F-A: surface the retry policy in the banner so users running a CLI
    # session can see at a glance how many retries each subsystem gets before
    # a fallback fires. The adapter default is 3 attempts (= 2 retries);
    # response_generator uses a heavier 5-attempt (= 4-retry) override.
    adapter_retry = getattr(anima.llm, "retry_cfg", None)
    adapter_max = getattr(adapter_retry, "max_attempts", None)
    subsystem_retries = (adapter_max - 1) if isinstance(adapter_max, int) else "?"
    retry_banner = (
        f"\n[dim]retry policy: {subsystem_retries} retries per subsystem + "
        f"4 retries for the response, then graceful fallback[/dim]"
    )
    v1_banner = ""
    if args.version == "v1":
        v1_banner = (
            "\n[dim]running architecture: v1 (Phase 1 frozen snapshot — "
            "no cross-session memory, no theory-of-mind, no surprise)[/dim]"
        )
    # In v1 mode the store directory is created but never written to; show
    # the path anyway so a confused user can see where it *would* live.
    persistence_line = (
        f"persistence root: {store.dir}"
        if persistence_enabled
        else f"persistence: [yellow]disabled (v1)[/yellow]; store dir would be {store.dir}"
    )
    console.print(Panel.fit(
        f"[bold]Talking to {anima.cfg.biography.name}[/bold]\n"
        f"{anima.cfg.biography.one_line}\n\n"
        f"[dim]session id: [bold]{session_id}[/bold] "
        f"(resume: --session-id {session_id})\n"
        f"{persistence_line}\n"
        f"transcript: {transcript.md_path}\n"
        f"Type a message and press enter. Ctrl-D / 'quit' to exit. "
        f"'/trace' shows the most recent inner trace. '/state' prints internal state. "
        f"'/retry' re-sends the last message that failed.[/dim]"
        f"{retry_banner}"
        f"{v1_banner}"
        f"{intro_extra}",
        title="anima"))
    turn_idx = 0
    # F2: when /retry is invoked we remember the turn-index it's a retry OF
    # so the transcript can label it as such. Cleared after the retry runs.
    retry_target_idx: int | None = None
    # E8: holds the most-recent user message that failed to produce a reply.
    # Cleared on the next successful turn (or on a new failure that overwrites
    # it). /retry resends it through the loop.
    last_failed_msg: str | None = None
    try:
        while True:
            try:
                msg = console.input("[bold cyan]you  >[/bold cyan] ").strip()
            except (EOFError, KeyboardInterrupt):
                console.print()
                break
            if not msg:
                continue
            if msg in {"quit", "exit", "/quit"}:
                break
            if msg == "/retry":
                if last_failed_msg is None:
                    console.print("[dim]nothing to retry[/dim]")
                    continue
                # F2: roll back any state changes the failed/degraded turn
                # made, BEFORE the retry runs. This removes the failed user
                # message from conversation_history, undoes any mood/drive
                # mutations, and drops the partial trace + episodic event the
                # turn may have produced. The transcript is intentionally
                # untouched — retries appear as additional turns there.
                # Fix 2: v1 has no rollback_last_turn — it doesn't snapshot
                # per-turn state. Print a friendly note and let the user
                # retype the message instead of crashing on the missing
                # method.
                if not hasattr(anima, "rollback_last_turn"):
                    console.print(
                        "[yellow](retry isn't available in --version v1 — the "
                        "architecture doesn't snapshot per-turn state; "
                        "just retype your message)[/yellow]"
                    )
                    continue
                rolled = anima.rollback_last_turn()
                if rolled:
                    console.print(
                        "[dim]rolled back the failed turn's state — "
                        "retry will run against a clean context[/dim]"
                    )
                # Remember which turn this is a retry OF so the transcript
                # records ``retry_of: N-1``. ``turn_idx`` at this point is the
                # index of the most recent (failed) turn that was written.
                retry_target_idx = turn_idx
                msg = last_failed_msg
                console.print(f"[dim]retrying: {msg[:80]}{'…' if len(msg) > 80 else ''}[/dim]")
            if msg == "/trace":
                if blind:
                    console.print(hidden_notice)
                    continue
                if not anima.traces:
                    console.print("[dim]no turns yet[/dim]")
                    continue
                t = anima.traces[-1]
                console.print(Panel(t.monologue, title="inner monologue", border_style="magenta"))
                console.print(Panel(t.appraisal.get("appraisal_scene_tag", ""), title="appraisal (scene-tag)", border_style="yellow"))
                # E6: surface the retrieval + theory-of-mind side of the trace,
                # so the operator can SEE what the Anima recalled and predicted.
                # Fix 2: in v1 the trace has neither retrieved nor prediction
                # nor surprise — skip those panels entirely so /trace is usable
                # under --version v1.
                retrieved = getattr(t, "retrieved", None)
                if retrieved:
                    body = "\n".join(
                        f"- [{r['score']:.2f}] {r.get('reconstructed_framing') or r.get('retrieval_reason') or r['id']}"
                        for r in retrieved
                    )
                    console.print(Panel(
                        f"{len(retrieved)} memories surfaced:\n{body}",
                        title="retrieved memories", border_style="cyan",
                    ))
                elif retrieved is not None:
                    console.print(Panel("(none surfaced this turn)",
                                        title="retrieved memories", border_style="dim"))
                prediction = getattr(t, "prediction", None)
                if prediction:
                    pred_body = (
                        f"next-intent label: {prediction.get('next_intent_label', '?')}\n"
                        f"content hint:      {prediction.get('content_hint', '?')}\n"
                        f"confidence:        {prediction.get('confidence', 0.0):.2f}"
                    )
                    console.print(Panel(pred_body, title="user prediction (this turn → next)",
                                        border_style="blue"))
                surprise = getattr(t, "surprise_from_last_turn", None)
                if surprise:
                    console.print(Panel(
                        f"surprise score: {surprise.get('surprise_score', 0.0):.2f}\n"
                        f"prior prediction was: "
                        f"{surprise.get('predicted_intent', {}).get('next_intent_label', '?')} / "
                        f"{surprise.get('predicted_intent', {}).get('content_hint', '?')}",
                        title="surprise (from prior turn)", border_style="red",
                    ))
                continue
            if msg == "/state":
                if blind:
                    console.print(hidden_notice)
                    continue
                console.print_json(json.dumps(anima.observe()))
                continue
            # E8: per-turn error handling. ResponseGenerationFailed → log
            # to transcript, preserve message for /retry, keep loop alive.
            # Any OTHER unexpected exception → last-resort catch so the
            # session does not die. The user's input is preserved either way.
            try:
                reply, trace = anima.respond(msg)
            except ResponseGenerationFailed as exc:
                turn_idx += 1
                transcript.write_failed_turn(turn_idx, msg, exc)
                last_failed_msg = msg
                console.print(
                    f"[red]turn failed:[/red] {exc} — your message is preserved."
                )
                snippet = msg if len(msg) <= 60 else msg[:60] + "…"
                console.print(
                    f"[dim]type /retry to re-send {snippet!r} or type a new message[/dim]"
                )
                continue
            except EmptyResponseAfterRetries as exc:
                # v1 (the frozen Phase-1 Anima) does NOT wrap
                # EmptyResponseAfterRetries in ResponseGenerationFailed the
                # way head does, so the exception arrives here unwrapped
                # when running ``--version v1``. Without this clause it
                # falls through to the generic "unexpected error:" catch,
                # which hides the actionable signal (finish_reason=length
                # → probably max_tokens too small / prompt too long). We
                # special-case it so the operator sees a clear diagnosis
                # and a concrete next step.
                turn_idx += 1
                try:
                    transcript.write_failed_turn(turn_idx, msg, exc)
                except Exception as t_exc:  # pragma: no cover — defensive nested
                    console.print(f"[red]transcript write failed:[/red] {t_exc!r}")
                last_failed_msg = msg
                name = anima.cfg.biography.name
                console.print(
                    f"[red]{name} produced no reply this turn — {exc}[/red]"
                )
                console.print(
                    "[dim]The model returned empty text on every retry. "
                    "This usually means the prompt is too long for "
                    "deepseek-flash, or the provider hit an issue. "
                    "Try a shorter input, or switch to a stronger model "
                    "with --strong-model.[/dim]"
                )
                continue
            except Exception as exc:  # noqa: BLE001 — last-resort: never crash the REPL
                turn_idx += 1
                try:
                    transcript.write_failed_turn(turn_idx, msg, exc)
                except Exception as t_exc:  # pragma: no cover — defensive nested
                    console.print(f"[red]transcript write failed:[/red] {t_exc!r}")
                last_failed_msg = msg
                console.print(f"[red]unexpected error:[/red] {exc!r}")
                console.print(
                    "[dim]your message is preserved; conversation state may be inconsistent. "
                    "type /retry to attempt again.[/dim]"
                )
                continue
            turn_idx += 1
            # F2: if this turn was initiated via /retry, stamp the trace with
            # the prior turn-index so the transcript header reads
            # "Turn N — retry of turn N-1" and the JSON entry carries
            # ``retry_of: N-1``. We set this on the live trace right before
            # write_turn so all downstream serialization picks it up.
            if retry_target_idx is not None:
                try:
                    trace.retry_of = retry_target_idx
                except Exception:  # pragma: no cover — defensive
                    pass
                retry_target_idx = None
            transcript.write_turn(turn_idx, msg, reply, trace)
            # Successful reply clears the last-failed message.
            last_failed_msg = None
            console.print(f"[bold green]{anima.cfg.biography.name} >[/bold green] {reply}")
            # --show-trace is silently overridden in blind mode; the operator
            # opted into not seeing the trace, so we honor that even if the
            # flag is also set.
            if args.show_trace and not blind:
                console.print(Panel(trace.monologue, title="(inner)", border_style="magenta"))
            # If the turn used fallbacks, surface that to the operator so they
            # know the reply was assembled with degraded inputs.
            trace_errors = getattr(trace, "subsystem_errors", None) or []
            if trace_errors and not blind:
                warned = ", ".join(e.get("subsystem", "?") for e in trace_errors)
                console.print(
                    f"[yellow]⚠️  generation errors this turn: {warned} — see transcript[/yellow]"
                )
            # F1: also surface model-silences inline. Distinguished from
            # errors: not a glitch, just the model declining to produce
            # content. Still useful for the operator to see.
            silences = getattr(trace, "silences", []) or []
            if silences and not blind:
                silenced = ", ".join(s.get("subsystem", "?") for s in silences)
                console.print(
                    f"[blue]🤐 model chose silence: {silenced} — see transcript[/blue]"
                )
    finally:
        # Always flush state to disk at session end so partial transcripts
        # don't get lost between autosaves.
        # Fix 2: v1 has no save() — guard the call so we don't crash on
        # session exit when running --version v1.
        if persistence_enabled and hasattr(anima, "save"):
            try:
                anima.save()
            except Exception as exc:  # pragma: no cover — defensive
                console.print(f"[red]save failed:[/red] {exc!r}")
        try:
            transcript.finalize(anima)
        except Exception as exc:  # pragma: no cover — defensive
            console.print(f"[red]transcript finalize failed:[/red] {exc!r}")
    return 0


def cmd_compare(args: argparse.Namespace) -> int:
    console = Console()
    llm = make_adapter(args.provider)
    anima = Anima.from_config_path(args.config, llm=llm)
    baseline = BaselineAnima.from_config_path(args.config, llm=llm)
    config_name = Path(args.config).stem
    console.print(Panel.fit(
        f"[bold]Side-by-side comparison: {anima.cfg.biography.name}[/bold]\n"
        f"{anima.cfg.biography.one_line}\n\n"
        f"[dim]Same input is sent to BOTH the Anima (full architecture) "
        f"and the BaselineAnima (single-prompt persona).\n"
        f"Type a message and press enter. Ctrl-D / '/quit' to exit. "
        f"'/trace' shows the Anima's most recent inner trace. "
        f"'/state' prints Anima internal state.[/dim]",
        title="anima compare"))
    while True:
        try:
            msg = console.input("[bold cyan]you  >[/bold cyan] ").strip()
        except (EOFError, KeyboardInterrupt):
            console.print()
            break
        if not msg:
            continue
        if msg in {"quit", "exit", "/quit"}:
            break
        if msg == "/trace":
            if not anima.traces:
                console.print("[dim]no turns yet[/dim]")
                continue
            t = anima.traces[-1]
            console.print(Panel(t.monologue, title="anima inner monologue", border_style="magenta"))
            console.print(Panel(t.appraisal["appraisal_scene_tag"], title="anima appraisal (scene-tag)", border_style="yellow"))
            console.print(Panel("(no monologue — baseline)", title="baseline inner monologue", border_style="dim"))
            continue
        if msg == "/state":
            console.print_json(json.dumps(anima.observe()))
            continue
        anima_reply, anima_trace = anima.respond(msg)
        baseline_reply, _ = baseline.respond(msg)
        left = Panel(anima_reply, title=f"Anima ({config_name})", border_style="green")
        right = Panel(baseline_reply, title=f"Baseline ({config_name})", border_style="yellow")
        console.print(Columns([left, right], equal=True, expand=True))
        if args.show_trace:
            console.print(Panel(
                f"[dim italic]{anima_trace.monologue}[/dim italic]",
                title=f"Anima inner monologue ({config_name})",
                border_style="magenta",
            ))
    return 0


def cmd_one_shot(args: argparse.Namespace) -> int:
    llm = make_adapter(args.provider)
    anima = Anima.from_config_path(args.config, llm=llm)
    for msg in args.messages:
        reply, _ = anima.respond(msg)
        print(reply)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="anima")
    sub = parser.add_subparsers(dest="command", required=True)

    p_chat = sub.add_parser("chat", help="interactive session")
    p_chat.add_argument("--config", required=True, type=Path)
    p_chat.add_argument("--provider", default="anthropic", choices=["anthropic", "openai", "openrouter", "fake"])
    p_chat.add_argument("--show-trace", action="store_true")
    p_chat.add_argument(
        "--session-id",
        default=None,
        help="resume an existing named session (any string); default = fresh UUID",
    )
    p_chat.add_argument(
        "--store-root",
        default="anima_store",
        help="root directory for per-Anima JSON stores (default: ./anima_store)",
    )
    p_chat.add_argument(
        "--version",
        default="head",
        choices=["head", "v1"],
        help="which Anima implementation to load: 'head' (current) or 'v1' (frozen Phase-1 snapshot)",
    )
    p_chat.add_argument(
        "--blind",
        action="store_true",
        help="hide /trace, /state, and the inline (--show-trace) panel during the session; "
             "the full transcript (including inner thoughts + state trajectory) is still written "
             "to disk and available after the session ends",
    )
    p_chat.add_argument(
        "--transcript-dir",
        default="transcripts",
        help="directory to write per-session transcript files into (default: ./transcripts; gitignored)",
    )
    p_chat.set_defaults(func=cmd_chat)

    p_one = sub.add_parser("ask", help="send one or more messages noninteractively")
    p_one.add_argument("--config", required=True, type=Path)
    p_one.add_argument("--provider", default="anthropic", choices=["anthropic", "openai", "openrouter", "fake"])
    p_one.add_argument("messages", nargs="+")
    p_one.set_defaults(func=cmd_one_shot)

    p_cmp = sub.add_parser("compare", help="side-by-side: Anima vs BaselineAnima on the same input")
    p_cmp.add_argument("--config", required=True, type=Path)
    p_cmp.add_argument("--provider", default="anthropic", choices=["anthropic", "openai", "openrouter", "fake"])
    p_cmp.add_argument("--show-trace", action="store_true")
    p_cmp.set_defaults(func=cmd_compare)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
