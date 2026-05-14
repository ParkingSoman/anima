"""Shared helpers for subsystems: structured-output extraction, prompt blocks."""

from __future__ import annotations

import json
import re
from typing import Any

_JSON_BLOCK_RE = re.compile(r"\{[\s\S]*\}")


def extract_json(text: str) -> dict[str, Any] | None:
    """Extract the first JSON object found in the text. Tolerant of fenced
    code blocks and trailing prose."""
    fenced = re.search(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", text)
    candidate = fenced.group(1) if fenced else None
    if candidate is None:
        m = _JSON_BLOCK_RE.search(text)
        candidate = m.group(0) if m else None
    if candidate is None:
        return None
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        return None
