"""Auto-load .env.local on package import. Tiny dependency-free loader."""

from __future__ import annotations

import os
from pathlib import Path


def load_dotenv(path: str | Path = ".env.local", override: bool = False) -> dict[str, str]:
    """Load KEY=VALUE pairs from path into os.environ. Returns dict of loaded keys."""
    p = Path(path)
    if not p.exists():
        return {}
    loaded = {}
    for raw in p.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        val = val.strip().strip('"').strip("'")
        if not override and key in os.environ:
            continue
        os.environ[key] = val
        loaded[key] = val
    return loaded


load_dotenv()
