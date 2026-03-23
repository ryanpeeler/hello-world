"""Cross-run evolution — learns from prior pipeline runs.

Extracts lessons from pipeline failures and successes, stores them
as reusable "skills", and injects relevant ones into subsequent runs.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_DECAY_DAYS = 30


def extract_lessons(run_dir: Path) -> list[dict[str, Any]]:
    """Extract lessons from a completed pipeline run."""
    lessons: list[dict[str, Any]] = []
    summary_path = run_dir / "pipeline_summary.json"

    if not summary_path.exists():
        return lessons

    summary = json.loads(summary_path.read_text(encoding="utf-8"))

    for stage in summary.get("stages", []):
        if stage.get("error"):
            lessons.append({
                "type": "failure",
                "stage": stage["name"],
                "error": stage["error"],
                "lesson": f"Stage {stage['name']} failed: {stage['error']}",
                "timestamp": summary.get("timestamp", ""),
            })

        if stage.get("status") == "done" and stage.get("duration_sec", 0) > 120:
            lessons.append({
                "type": "slow_stage",
                "stage": stage["name"],
                "duration_sec": stage["duration_sec"],
                "lesson": f"Stage {stage['name']} took {stage['duration_sec']:.0f}s — consider optimization",
                "timestamp": summary.get("timestamp", ""),
            })

    # Check decision history
    decision_path = run_dir / "decision_history.json"
    if decision_path.exists():
        decisions = json.loads(decision_path.read_text(encoding="utf-8"))
        for d in decisions:
            lessons.append({
                "type": "decision",
                "stage": d.get("stage_name", ""),
                "decision": d.get("decision", ""),
                "lesson": f"Research decision: {d.get('decision', '')} at stage {d.get('stage_name', '')}",
                "timestamp": d.get("timestamp", ""),
            })

    return lessons


def save_lessons(lessons: list[dict[str, Any]], evolution_dir: Path) -> None:
    """Save lessons to the evolution directory."""
    evolution_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    out_path = evolution_dir / f"lessons_{ts}.json"
    out_path.write_text(json.dumps(lessons, indent=2) + "\n", encoding="utf-8")
    logger.info("Saved %d lessons to %s", len(lessons), out_path)


def load_relevant_lessons(
    evolution_dir: Path, max_age_days: int = _DECAY_DAYS
) -> list[dict[str, Any]]:
    """Load recent lessons within the decay window."""
    if not evolution_dir.exists():
        return []

    all_lessons: list[dict[str, Any]] = []
    now = datetime.now(timezone.utc)

    for lesson_file in sorted(evolution_dir.glob("lessons_*.json")):
        try:
            lessons = json.loads(lesson_file.read_text(encoding="utf-8"))
            for lesson in lessons:
                ts_str = lesson.get("timestamp", "")
                if ts_str:
                    try:
                        ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                        age = (now - ts).days
                        if age <= max_age_days:
                            all_lessons.append(lesson)
                    except ValueError:
                        all_lessons.append(lesson)
                else:
                    all_lessons.append(lesson)
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Failed to load lessons from %s: %s", lesson_file, exc)

    return all_lessons


def format_evolution_overlay(lessons: list[dict[str, Any]]) -> str:
    """Format lessons into a prompt overlay string."""
    if not lessons:
        return ""

    lines = ["## Lessons from Prior Runs", ""]
    for lesson in lessons[:10]:
        lines.append(f"- [{lesson.get('type', 'info')}] {lesson.get('lesson', '')}")

    return "\n".join(lines)
