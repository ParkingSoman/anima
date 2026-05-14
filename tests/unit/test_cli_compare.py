"""Unit test for the `compare` CLI subcommand.

This test only verifies argparse wiring — it does not actually run the
compare loop and does not make any LLM calls. It patches `cmd_compare`
to a no-op and confirms that `main(["compare", "--config", "foo.yaml"])`
dispatches to that callable with the parsed args.
"""

from __future__ import annotations

from pathlib import Path
from unittest import mock

from anima import cli as anima_cli


def test_compare_subcommand_is_registered_and_dispatches():
    """`anima compare --config foo.yaml` must parse and dispatch to cmd_compare."""
    captured: dict = {}

    def fake_cmd_compare(args):
        captured["args"] = args
        return 0

    with mock.patch.object(anima_cli, "cmd_compare", fake_cmd_compare):
        rc = anima_cli.main(["compare", "--config", "foo.yaml"])

    assert rc == 0
    assert "args" in captured, "cmd_compare was not dispatched"
    args = captured["args"]
    # The parser stores --config as a Path and exposes --provider / --show-trace.
    assert args.config == Path("foo.yaml")
    assert args.provider in {"anthropic", "openai", "openrouter"}
    assert hasattr(args, "show_trace")
    assert args.show_trace is False  # default


def test_compare_subcommand_accepts_provider_and_show_trace_flags():
    """All three documented flags must be accepted by the compare subparser."""
    captured: dict = {}

    def fake_cmd_compare(args):
        captured["args"] = args
        return 0

    with mock.patch.object(anima_cli, "cmd_compare", fake_cmd_compare):
        rc = anima_cli.main([
            "compare",
            "--config", "bar.yaml",
            "--provider", "openrouter",
            "--show-trace",
        ])

    assert rc == 0
    args = captured["args"]
    assert args.config == Path("bar.yaml")
    assert args.provider == "openrouter"
    assert args.show_trace is True


def test_cmd_compare_is_a_real_callable():
    """`cmd_compare` must exist in anima.cli as a callable (not just a string)."""
    assert hasattr(anima_cli, "cmd_compare")
    assert callable(anima_cli.cmd_compare)
