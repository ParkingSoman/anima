#!/usr/bin/env python3
"""PreToolUse hook: block controller-initiated edits to source files.

When Claude Code attempts Edit/Write/NotebookEdit on a file inside
`anima/`, `verification/`, or `tests/`, this hook blocks the call and
tells the controller to dispatch a subagent instead. This enforces the
subagent-driven-development discipline at the tool-call layer rather
than relying on advisory memory rules that the controller keeps
forgetting.

Allowed (hook passes through):
  - Any file outside the three protected directories (STATE.md, docs/,
    .gitignore, plan files, .claude/, ~/.claude/, etc.)
  - Anywhere when dispatched from a subagent (we cannot reliably detect
    this from inside the hook; we trust the matcher scope instead)

Blocked (hook exits 2):
  - anima/**, verification/**, tests/** — any file at any depth, any
    extension. Subagent dispatch is the only path to edit these.

Exit codes:
  0 — allow tool call
  2 — block; stderr is surfaced back to Claude
  1 — hook error (Claude treats this as a soft warning, allows the call)
"""

from __future__ import annotations

import json
import re
import sys


# Match any path that contains /anima/, /verification/, or /tests/ as a
# directory segment (so we don't accidentally match arbitrary strings).
PROTECTED_RE = re.compile(r"(?:^|/)(anima|verification|tests)/")


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        # If we can't parse the hook input, fail open so we don't break
        # the user's session.
        return 1

    tool_input = payload.get("tool_input") or {}
    file_path = tool_input.get("file_path") or ""

    if not file_path:
        # Edits that don't carry a file_path aren't ours to block.
        return 0

    if not PROTECTED_RE.search(file_path):
        return 0

    sys.stderr.write(
        "BLOCKED: controller-initiated edits to source files under "
        "anima/, verification/, or tests/ are forbidden by the project's "
        "subagent-driven-development discipline. "
        "Path attempted: " + file_path + "\n\n"
        "Dispatch a subagent (Agent tool with general-purpose subagent_type) "
        "and have it perform the edit. If a reviewer flagged the issue, "
        "SendMessage to the ORIGINAL implementer subagent (preserves context). "
        "If you genuinely need to edit a doc, plan, or config file outside the "
        "protected tree, the hook will not fire.\n"
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
