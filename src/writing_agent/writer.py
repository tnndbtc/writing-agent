"""Byte-stable JSON output writer."""

from __future__ import annotations

import json
from pathlib import Path


def write_json(data: dict, path: str) -> None:
    """Write *data* to *path* as byte-stable, POSIX-compliant JSON.

    Guarantees:
    - sort_keys=True  → eliminates dict ordering non-determinism
    - ensure_ascii=True → no locale-dependent unicode variation
    - newline="\\n"   → Unix line endings everywhere
    - Single trailing "\\n" → POSIX-compliant text file
    """
    serialized = json.dumps(data, sort_keys=True, indent=2, ensure_ascii=True)
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(serialized + "\n", encoding="utf-8", newline="\n")
