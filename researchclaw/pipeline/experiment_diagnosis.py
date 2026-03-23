"""Experiment diagnosis — assess experiment quality and detect issues."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def diagnose_experiment(runs_dir: Path) -> dict[str, Any]:
    """Assess experiment quality from run results."""
    if not runs_dir.exists():
        return {"status": "no_runs", "issues": ["No runs directory found"]}

    results = []
    for result_file in sorted(runs_dir.rglob("result.json")):
        try:
            data = json.loads(result_file.read_text(encoding="utf-8"))
            results.append(data)
        except (json.JSONDecodeError, OSError):
            continue

    if not results:
        return {"status": "no_results", "issues": ["No result files found"]}

    issues: list[str] = []
    total = len(results)
    successful = sum(1 for r in results if r.get("success", False))
    failed = total - successful

    if failed > 0:
        issues.append(f"{failed}/{total} experiment runs failed")

    # Check for empty metrics
    empty_metrics = sum(1 for r in results if not r.get("metrics"))
    if empty_metrics == total:
        issues.append("All runs produced empty metrics")

    # Check for very short durations (possible crash)
    short_runs = sum(1 for r in results if r.get("duration_sec", 0) < 1.0 and r.get("success"))
    if short_runs > 0:
        issues.append(f"{short_runs} runs completed suspiciously fast (<1s)")

    status = "good" if not issues else "needs_attention"
    return {
        "status": status,
        "total_runs": total,
        "successful": successful,
        "failed": failed,
        "issues": issues,
    }
