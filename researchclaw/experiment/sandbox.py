"""Sandbox experiment runner — safe local Python execution."""

from __future__ import annotations

import json
import logging
import math
import subprocess
import time
from pathlib import Path
from typing import Any

from researchclaw.config import RCConfig
from researchclaw.hardware import is_metric_name

logger = logging.getLogger(__name__)


def run_sandbox_experiment(
    *,
    experiment_dir: Path,
    runs_dir: Path,
    config: RCConfig,
) -> list[dict[str, Any]]:
    """Run experiment scripts in a sandboxed Python environment."""
    sandbox_cfg = config.experiment.sandbox
    python_path = sandbox_cfg.python_path
    time_budget = sandbox_cfg.time_budget_sec

    results: list[dict[str, Any]] = []

    # Find experiment scripts
    scripts = sorted(experiment_dir.glob("*.py"))
    if not scripts:
        logger.warning("No Python scripts found in %s", experiment_dir)
        return results

    for script in scripts:
        logger.info("Running experiment: %s", script.name)
        result = _run_single_script(
            script=script,
            python_path=python_path,
            time_budget=time_budget,
            runs_dir=runs_dir,
        )
        results.append(result)

    return results


def _run_single_script(
    *,
    script: Path,
    python_path: str,
    time_budget: int,
    runs_dir: Path,
) -> dict[str, Any]:
    """Run a single Python script and collect results."""
    run_name = script.stem
    run_dir = runs_dir / run_name
    run_dir.mkdir(parents=True, exist_ok=True)

    t0 = time.monotonic()

    try:
        result = subprocess.run(
            [python_path, str(script)],
            capture_output=True,
            text=True,
            timeout=time_budget,
            cwd=str(script.parent),
            check=False,
        )
        duration = time.monotonic() - t0
        stdout = result.stdout
        stderr = result.stderr

        # Check for NaN/Inf in output (fast-failure detection)
        if _has_nan_inf(stdout):
            logger.warning("NaN/Inf detected in output of %s", script.name)

        # Parse metrics from stdout
        metrics = _parse_metrics(stdout)

        run_result = {
            "name": run_name,
            "script": str(script),
            "exit_code": result.returncode,
            "duration_sec": round(duration, 2),
            "metrics": metrics,
            "stdout_lines": len(stdout.splitlines()),
            "success": result.returncode == 0,
        }

        # Save results
        (run_dir / "stdout.txt").write_text(stdout, encoding="utf-8")
        (run_dir / "stderr.txt").write_text(stderr, encoding="utf-8")
        (run_dir / "result.json").write_text(
            json.dumps(run_result, indent=2) + "\n", encoding="utf-8"
        )

        return run_result

    except subprocess.TimeoutExpired:
        duration = time.monotonic() - t0
        logger.warning("Script %s timed out after %ds", script.name, time_budget)
        run_result = {
            "name": run_name,
            "script": str(script),
            "exit_code": -1,
            "duration_sec": round(duration, 2),
            "metrics": {},
            "success": False,
            "error": f"Timeout after {time_budget}s",
        }
        (run_dir / "result.json").write_text(
            json.dumps(run_result, indent=2) + "\n", encoding="utf-8"
        )
        return run_result

    except (FileNotFoundError, OSError) as exc:
        logger.error("Failed to run %s: %s", script.name, exc)
        return {
            "name": run_name,
            "script": str(script),
            "exit_code": -1,
            "duration_sec": 0,
            "metrics": {},
            "success": False,
            "error": str(exc),
        }


def _parse_metrics(stdout: str) -> dict[str, float]:
    """Parse metric_name: value lines from stdout."""
    metrics: dict[str, float] = {}
    for line in stdout.splitlines():
        line = line.strip()
        if ":" not in line:
            continue
        parts = line.split(":", 1)
        if len(parts) != 2:
            continue
        name = parts[0].strip()
        value_str = parts[1].strip()

        if not is_metric_name(name):
            continue

        try:
            value = float(value_str)
            if not (math.isnan(value) or math.isinf(value)):
                metrics[name] = value
        except ValueError:
            continue

    return metrics


def _has_nan_inf(text: str) -> bool:
    """Check if output contains NaN or Inf values."""
    lower = text.lower()
    return "nan" in lower or "inf" in lower
