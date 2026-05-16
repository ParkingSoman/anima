"""Personal-use chat wrapper for animas, with a monologue-length toggle.

Lets you chat with any Anima YAML config while optionally overriding the
persona-scaled inner-monologue length. Reuses the experiment's
LengthControlledInnerMonologue subclass so it doesn't modify the frozen
anima_v1 tree.

Usage:
    .venv/bin/python personal_personas/chat.py --config <path> [options]

    (Or: source .venv/bin/activate first, then use 'python' directly.
    The project's venv has rich + pydantic + yaml; system Python doesn't.)

Examples:
    # Default — persona-scaled monologue (architecture's normal behavior):
    .venv/bin/python personal_personas/chat.py --config personal_personas/ophelia.yaml --provider openrouter

    # Variable — let the model choose monologue length freely (no directive):
    .venv/bin/python personal_personas/chat.py --config personal_personas/vesper.yaml --provider openrouter --monologue variable

    # Forced short (1–2 sentence monologue, 120 token cap):
    .venv/bin/python personal_personas/chat.py --config personal_personas/roisin.yaml --provider openrouter --monologue short

    # Forced long (8–12 sentence monologue, 720 token cap):
    .venv/bin/python personal_personas/chat.py --config personal_personas/wren.yaml --provider openrouter --monologue long

In-session commands:
    /trace      show the most recent inner monologue
    /state      dump internal state (mood, drives, self-model)
    quit | /quit | exit | Ctrl-D    exit
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Project root on sys.path so we can import anima_v1 and verification as packages.
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from rich.console import Console
from rich.panel import Panel

from anima_v1.core import Anima
from anima_v1.llm import make_adapter
from verification.probes.monologue_length_directives import LengthControlledInnerMonologue


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="personal-chat",
        description="Chat with an Anima, with an optional monologue-length toggle.",
    )
    parser.add_argument("--config", required=True, type=Path,
                        help="Path to a persona YAML file.")
    parser.add_argument("--provider", default="openrouter",
                        choices=["anthropic", "openai", "openrouter", "fake"],
                        help="LLM provider. Default 'openrouter' (uses OPENROUTER_API_KEY).")
    parser.add_argument(
        "--monologue", default="default",
        choices=["default", "variable", "short", "long"],
        help=(
            "Inner-monologue length mode. "
            "'default' = persona-scaled (architecture's normal behavior — depth derived from Big 5 + attachment). "
            "'variable' = no length directive at all; model chooses freely. "
            "'short' = forced 1-2 sentence monologue, 120 token cap. "
            "'long' = forced 8-12 sentence monologue, 720 token cap."
        ),
    )
    parser.add_argument("--show-trace", action="store_true",
                        help="Print the inner monologue after every reply.")
    args = parser.parse_args(argv)

    console = Console()
    llm = make_adapter(args.provider)
    anima = Anima.from_config_path(args.config, llm=llm)

    # Override the monologue subsystem if requested.
    if args.monologue != "default":
        anima._monologue = LengthControlledInnerMonologue(llm, cell=args.monologue)
        mode_desc = {
            "variable": "VARIABLE — no length directive, model chooses freely",
            "short": "SHORT — forced 1-2 sentences, 120 token cap",
            "long": "LONG — forced 8-12 sentences, 720 token cap",
        }[args.monologue]
    else:
        mode_desc = "default — persona-scaled depth"

    console.print(Panel.fit(
        f"[bold]Talking to {anima.cfg.biography.name}[/bold]\n"
        f"Monologue: [yellow]{mode_desc}[/yellow]\n\n"
        f"[dim]Type a message and press enter. Ctrl-D / 'quit' to exit. "
        f"'/trace' shows the most recent inner monologue. '/state' prints internal state.[/dim]",
        title="anima (personal)"))

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
            console.print(Panel(t.appraisal["appraisal_scene_tag"],
                                title="appraisal (scene-tag)", border_style="yellow"))
            continue
        if msg == "/state":
            console.print_json(json.dumps(anima.observe()))
            continue
        reply, trace = anima.respond(msg)
        console.print(f"[bold green]{anima.cfg.biography.name} >[/bold green] {reply}")
        if args.show_trace:
            console.print(Panel(trace.monologue, title="(inner)", border_style="magenta"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
