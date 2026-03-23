"""Verified artifact registry — tracks produced artifacts per stage."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class ArtifactRegistry:
    """Track and verify artifacts produced by pipeline stages."""

    def __init__(self, run_dir: Path) -> None:
        self.run_dir = run_dir
        self._registry_path = run_dir / "artifact_registry.json"
        self._registry: dict[str, list[str]] = {}
        if self._registry_path.exists():
            self._registry = json.loads(self._registry_path.read_text(encoding="utf-8"))

    def register(self, stage_name: str, artifacts: list[str]) -> None:
        """Register artifacts produced by a stage."""
        self._registry[stage_name] = artifacts
        self._save()

    def verify(self, stage_name: str) -> tuple[bool, list[str]]:
        """Verify that all registered artifacts for a stage exist."""
        artifacts = self._registry.get(stage_name, [])
        missing = [a for a in artifacts if not (self.run_dir / a).exists()]
        return len(missing) == 0, missing

    def get_artifacts(self, stage_name: str) -> list[str]:
        """Get registered artifacts for a stage."""
        return self._registry.get(stage_name, [])

    def _save(self) -> None:
        self._registry_path.write_text(
            json.dumps(self._registry, indent=2) + "\n", encoding="utf-8"
        )
