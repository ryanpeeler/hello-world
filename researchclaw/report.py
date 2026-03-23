"""Human-readable run report generation."""

from __future__ import annotations

import json
from pathlib import Path


def generate_report(run_dir: Path) -> str:
    """Generate a human-readable report from a pipeline run."""
    if not run_dir.exists():
        raise FileNotFoundError(f"Run directory not found: {run_dir}")

    summary_path = run_dir / "pipeline_summary.json"
    if not summary_path.exists():
        raise ValueError(f"No pipeline_summary.json found in {run_dir}")

    summary = json.loads(summary_path.read_text(encoding="utf-8"))

    lines = [
        f"# ResearchClaw Run Report",
        f"",
        f"**Run ID:** {summary.get('run_id', 'unknown')}",
        f"**Timestamp:** {summary.get('timestamp', 'unknown')}",
        f"**Stages completed:** {summary.get('completed', 0)}/{summary.get('total_stages', 0)}",
        f"**Failed stages:** {summary.get('failed', 0)}",
        f"**Total duration:** {summary.get('total_duration_sec', 0):.1f}s",
        f"",
        f"## Stage Details",
        f"",
    ]

    for stage in summary.get("stages", []):
        status_icon = "DONE" if stage["status"] == "done" else stage["status"].upper()
        lines.append(
            f"- Stage {stage['stage']:2d} ({stage['name']}): "
            f"{status_icon} ({stage['duration_sec']:.1f}s)"
        )
        if stage.get("error"):
            lines.append(f"  Error: {stage['error']}")

    # Check for deliverables
    lines.append("")
    lines.append("## Deliverables")
    lines.append("")

    deliverables = [
        ("paper_final.md", "Final Paper (Markdown)"),
        ("paper.tex", "LaTeX Source"),
        ("references.bib", "BibTeX References"),
        ("references_verified.bib", "Verified References"),
        ("verification_report.json", "Citation Verification Report"),
        ("quality_report.json", "Quality Report"),
    ]

    for filename, label in deliverables:
        path = run_dir / filename
        if path.exists():
            size = path.stat().st_size
            lines.append(f"- {label}: {filename} ({size:,} bytes)")

    return "\n".join(lines)


def write_report(run_dir: Path, output_path: Path) -> None:
    """Write the report to a file."""
    report = generate_report(run_dir)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report, encoding="utf-8")
