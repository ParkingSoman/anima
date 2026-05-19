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
from anima.persistence.store import AnimaStore
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
    anima = AnimaCls(cfg, llm=llm, store=store, autosave_every=3)
    anima.set_session_id(session_id)

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
    transcript.write_header(anima)

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
    console.print(Panel.fit(
        f"[bold]Talking to {anima.cfg.biography.name}[/bold]\n"
        f"{anima.cfg.biography.one_line}\n\n"
        f"[dim]session id: [bold]{session_id}[/bold] "
        f"(resume: --session-id {session_id})\n"
        f"persistence root: {store.dir}\n"
        f"transcript: {transcript.md_path}\n"
        f"Type a message and press enter. Ctrl-D / 'quit' to exit. "
        f"'/trace' shows the most recent inner trace. '/state' prints internal state.[/dim]"
        f"{intro_extra}",
        title="anima"))
    turn_idx = 0
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
            if msg == "/trace":
                if blind:
                    console.print(hidden_notice)
                    continue
                if not anima.traces:
                    console.print("[dim]no turns yet[/dim]")
                    continue
                t = anima.traces[-1]
                console.print(Panel(t.monologue, title="inner monologue", border_style="magenta"))
                console.print(Panel(t.appraisal["appraisal_scene_tag"], title="appraisal (scene-tag)", border_style="yellow"))
                # E6: surface the retrieval + theory-of-mind side of the trace,
                # so the operator can SEE what the Anima recalled and predicted.
                if t.retrieved:
                    body = "\n".join(
                        f"- [{r['score']:.2f}] {r.get('reconstructed_framing') or r.get('retrieval_reason') or r['id']}"
                        for r in t.retrieved
                    )
                    console.print(Panel(
                        f"{len(t.retrieved)} memories surfaced:\n{body}",
                        title="retrieved memories", border_style="cyan",
                    ))
                else:
                    console.print(Panel("(none surfaced this turn)",
                                        title="retrieved memories", border_style="dim"))
                if t.prediction:
                    pred_body = (
                        f"next-intent label: {t.prediction.get('next_intent_label', '?')}\n"
                        f"content hint:      {t.prediction.get('content_hint', '?')}\n"
                        f"confidence:        {t.prediction.get('confidence', 0.0):.2f}"
                    )
                    console.print(Panel(pred_body, title="user prediction (this turn → next)",
                                        border_style="blue"))
                if t.surprise_from_last_turn:
                    s = t.surprise_from_last_turn
                    console.print(Panel(
                        f"surprise score: {s.get('surprise_score', 0.0):.2f}\n"
                        f"prior prediction was: "
                        f"{s.get('predicted_intent', {}).get('next_intent_label', '?')} / "
                        f"{s.get('predicted_intent', {}).get('content_hint', '?')}",
                        title="surprise (from prior turn)", border_style="red",
                    ))
                continue
            if msg == "/state":
                if blind:
                    console.print(hidden_notice)
                    continue
                console.print_json(json.dumps(anima.observe()))
                continue
            reply, trace = anima.respond(msg)
            turn_idx += 1
            transcript.write_turn(turn_idx, msg, reply, trace)
            console.print(f"[bold green]{anima.cfg.biography.name} >[/bold green] {reply}")
            # --show-trace is silently overridden in blind mode; the operator
            # opted into not seeing the trace, so we honor that even if the
            # flag is also set.
            if args.show_trace and not blind:
                console.print(Panel(trace.monologue, title="(inner)", border_style="magenta"))
    finally:
        # Always flush state to disk at session end so partial transcripts
        # don't get lost between autosaves.
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
