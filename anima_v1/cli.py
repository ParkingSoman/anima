"""CLI for interactive sessions and quick smoke tests."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from rich.columns import Columns
from rich.console import Console
from rich.panel import Panel

from anima_v1.core import Anima
from anima_v1.llm import make_adapter
from verification.baseline import BaselineAnima


def cmd_chat(args: argparse.Namespace) -> int:
    console = Console()
    llm = make_adapter(args.provider)
    anima = Anima.from_config_path(args.config, llm=llm)
    console.print(Panel.fit(
        f"[bold]Talking to {anima.cfg.biography.name}[/bold]\n"
        f"{anima.cfg.biography.one_line}\n\n"
        f"[dim]Type a message and press enter. Ctrl-D / 'quit' to exit. "
        f"'/trace' shows the most recent inner trace. '/state' prints internal state.[/dim]",
        title="anima"))
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
            console.print(Panel(t.monologue, title="inner monologue", border_style="magenta"))
            console.print(Panel(t.appraisal["appraisal_scene_tag"], title="appraisal (scene-tag)", border_style="yellow"))
            continue
        if msg == "/state":
            console.print_json(json.dumps(anima.observe()))
            continue
        reply, trace = anima.respond(msg)
        console.print(f"[bold green]{anima.cfg.biography.name} >[/bold green] {reply}")
        if args.show_trace:
            console.print(Panel(trace.monologue, title="(inner)", border_style="magenta"))
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
