"""Tests for the evolution (cross-run learning) system."""

import json
import tempfile
from pathlib import Path

from researchclaw.evolution import extract_lessons, format_evolution_overlay, load_relevant_lessons, save_lessons


def test_extract_lessons_empty():
    """No summary file should return empty lessons."""
    with tempfile.TemporaryDirectory() as tmp:
        lessons = extract_lessons(Path(tmp))
        assert lessons == []


def test_extract_lessons_with_failure():
    """Failed stages should produce lessons."""
    with tempfile.TemporaryDirectory() as tmp:
        run_dir = Path(tmp)
        summary = {
            "stages": [
                {"name": "TOPIC_INIT", "status": "done", "error": "", "duration_sec": 5},
                {"name": "LITERATURE_COLLECT", "status": "failed", "error": "API timeout", "duration_sec": 30},
            ]
        }
        (run_dir / "pipeline_summary.json").write_text(json.dumps(summary))
        lessons = extract_lessons(run_dir)
        assert len(lessons) >= 1
        assert any("failure" in l["type"] for l in lessons)


def test_save_and_load_lessons():
    """Lessons should round-trip through save/load."""
    from datetime import datetime, timezone
    now_iso = datetime.now(timezone.utc).isoformat()
    with tempfile.TemporaryDirectory() as tmp:
        evo_dir = Path(tmp) / "evolution"
        lessons = [{"type": "test", "lesson": "This is a test", "timestamp": now_iso}]
        save_lessons(lessons, evo_dir)
        loaded = load_relevant_lessons(evo_dir)
        assert len(loaded) == 1


def test_format_evolution_overlay():
    """Overlay should format lessons into a prompt string."""
    lessons = [{"type": "failure", "lesson": "Stage X failed"}]
    overlay = format_evolution_overlay(lessons)
    assert "Lessons from Prior Runs" in overlay
    assert "Stage X failed" in overlay


def test_format_empty_overlay():
    """Empty lessons should produce empty overlay."""
    assert format_evolution_overlay([]) == ""
