"""Pipeline utility helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def read_json(path: Path) -> Any:
    """Read a JSON file, returning None if it doesn't exist."""
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    """Write data as JSON to a file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def read_text(path: Path) -> str:
    """Read a text file, returning empty string if it doesn't exist."""
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")
