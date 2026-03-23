"""Pipeline runner — executes the 23-stage research pipeline sequentially."""

from __future__ import annotations

import json
import logging
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from researchclaw.adapters import AdapterBundle
from researchclaw.config import RCConfig
from researchclaw.pipeline.contracts import CONTRACTS
from researchclaw.pipeline.stages import (
    DECISION_ROLLBACK,
    GATE_STAGES,
    MAX_DECISION_PIVOTS,
    NONCRITICAL_STAGES,
    STAGE_SEQUENCE,
    Stage,
    StageStatus,
)

logger = logging.getLogger(__name__)


@dataclass
class StageResult:
    stage: Stage
    status: StageStatus
    duration_sec: float = 0.0
    error: str = ""
    artifacts: list[str] | None = None


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _write_checkpoint(run_dir: Path, stage: Stage) -> None:
    """Atomically save stage completion checkpoint."""
    checkpoint = run_dir / "checkpoint.json"
    data = {"last_completed_stage": int(stage), "stage_name": stage.name, "timestamp": _utcnow_iso()}
    tmp = checkpoint.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    tmp.rename(checkpoint)


def _write_heartbeat(run_dir: Path, stage: Stage) -> None:
    """Write watchdog heartbeat."""
    hb = run_dir / "heartbeat.json"
    data = {"stage": int(stage), "stage_name": stage.name, "timestamp": _utcnow_iso()}
    hb.write_text(json.dumps(data) + "\n", encoding="utf-8")


def read_checkpoint(run_dir: Path) -> Stage | None:
    """Retrieve last completed stage from checkpoint."""
    checkpoint = run_dir / "checkpoint.json"
    if not checkpoint.exists():
        return None
    try:
        data = json.loads(checkpoint.read_text(encoding="utf-8"))
        stage_num = data.get("last_completed_stage")
        if stage_num is not None:
            return Stage(stage_num)
    except (json.JSONDecodeError, ValueError, KeyError):
        pass
    return None


def resume_from_checkpoint(run_dir: Path) -> Stage:
    """Resolve which stage to start from when resuming."""
    last = read_checkpoint(run_dir)
    if last is None:
        return Stage.TOPIC_INIT
    # Resume from the stage AFTER the last completed one
    idx = list(Stage).index(last)
    if idx + 1 < len(Stage):
        return list(Stage)[idx + 1]
    return last


def _should_start(stage: Stage, from_stage: Stage) -> bool:
    return int(stage) >= int(from_stage)


def _read_pivot_count(run_dir: Path) -> int:
    """Count previous decision pivots."""
    history_file = run_dir / "decision_history.json"
    if not history_file.exists():
        return 0
    try:
        data = json.loads(history_file.read_text(encoding="utf-8"))
        return sum(1 for entry in data if entry.get("decision") == "pivot")
    except (json.JSONDecodeError, ValueError):
        return 0


def _record_decision_history(run_dir: Path, decision: str, stage: Stage) -> None:
    """Log a rollback decision."""
    history_file = run_dir / "decision_history.json"
    history: list[dict[str, Any]] = []
    if history_file.exists():
        try:
            history = json.loads(history_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, ValueError):
            pass
    history.append({
        "decision": decision,
        "stage": int(stage),
        "stage_name": stage.name,
        "timestamp": _utcnow_iso(),
    })
    history_file.write_text(json.dumps(history, indent=2) + "\n", encoding="utf-8")


def _version_rollback_stages(run_dir: Path, stage: Stage) -> None:
    """Version artifact directories before retry."""
    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    for name in ("experiment", "runs", "experiment_final"):
        src = run_dir / name
        if src.exists():
            dst = run_dir / f"{name}_v{ts}"
            shutil.copytree(src, dst, dirs_exist_ok=True)
            logger.info("Versioned %s → %s", src, dst)


def execute_pipeline(
    *,
    run_dir: Path,
    run_id: str,
    config: RCConfig,
    adapters: AdapterBundle,
    from_stage: Stage = Stage.TOPIC_INIT,
    auto_approve_gates: bool = False,
    stop_on_gate: bool = False,
    skip_noncritical: bool = False,
    kb_root: Path | None = None,
) -> list[StageResult]:
    """Execute the 23-stage pipeline sequentially."""
    from researchclaw.pipeline.executor import execute_stage

    results: list[StageResult] = []
    current_stage = from_stage

    while current_stage is not None:
        if not _should_start(current_stage, from_stage):
            current_stage = Stage(int(current_stage) + 1) if int(current_stage) < 23 else None
            continue

        _write_heartbeat(run_dir, current_stage)

        contract = CONTRACTS.get(current_stage)
        is_gate = current_stage in GATE_STAGES
        is_noncritical = current_stage in NONCRITICAL_STAGES

        print(f"  Stage {int(current_stage):2d}: {current_stage.name} ...", end=" ", flush=True)

        import time
        t0 = time.monotonic()

        try:
            result = execute_stage(
                stage=current_stage,
                run_dir=run_dir,
                run_id=run_id,
                config=config,
                adapters=adapters,
                kb_root=kb_root,
            )

            duration = time.monotonic() - t0

            # Handle gate stages
            if is_gate and not auto_approve_gates:
                if stop_on_gate:
                    print(f"BLOCKED (gate — waiting for approval)")
                    results.append(StageResult(
                        stage=current_stage,
                        status=StageStatus.BLOCKED_APPROVAL,
                        duration_sec=duration,
                    ))
                    break

            print(f"DONE ({duration:.1f}s)")
            results.append(StageResult(
                stage=current_stage, status=StageStatus.DONE, duration_sec=duration,
            ))
            _write_checkpoint(run_dir, current_stage)

            # Handle RESEARCH_DECISION stage
            if current_stage == Stage.RESEARCH_DECISION:
                decision_file = run_dir / "decision.md"
                decision = "proceed"
                if decision_file.exists():
                    content = decision_file.read_text(encoding="utf-8").lower()
                    if "pivot" in content:
                        decision = "pivot"
                    elif "refine" in content:
                        decision = "refine"

                if decision in ("pivot", "refine"):
                    pivot_count = _read_pivot_count(run_dir)
                    if pivot_count >= MAX_DECISION_PIVOTS:
                        logger.warning(
                            "Max pivots (%d) reached — forcing PROCEED", MAX_DECISION_PIVOTS
                        )
                    else:
                        _record_decision_history(run_dir, decision, current_stage)
                        _version_rollback_stages(run_dir, current_stage)
                        rollback_target = DECISION_ROLLBACK.get(decision, Stage.HYPOTHESIS_GEN)
                        print(f"  Decision: {decision.upper()} → rolling back to {rollback_target.name}")
                        current_stage = rollback_target
                        from_stage = rollback_target
                        continue

            # Advance to next stage
            idx = list(Stage).index(current_stage)
            current_stage = list(Stage)[idx + 1] if idx + 1 < len(Stage) else None

        except Exception as exc:
            duration = time.monotonic() - t0

            if is_noncritical and skip_noncritical:
                print(f"SKIPPED (noncritical: {exc})")
                results.append(StageResult(
                    stage=current_stage, status=StageStatus.DONE,
                    duration_sec=duration, error=str(exc),
                ))
                _write_checkpoint(run_dir, current_stage)
                idx = list(Stage).index(current_stage)
                current_stage = list(Stage)[idx + 1] if idx + 1 < len(Stage) else None
            else:
                # Retry logic
                retries = contract.max_retries if contract else 1
                retried = False
                for attempt in range(retries):
                    print(f"RETRY {attempt + 1}/{retries}...", end=" ", flush=True)
                    try:
                        result = execute_stage(
                            stage=current_stage,
                            run_dir=run_dir,
                            run_id=run_id,
                            config=config,
                            adapters=adapters,
                            kb_root=kb_root,
                        )
                        print("DONE")
                        results.append(StageResult(
                            stage=current_stage, status=StageStatus.DONE,
                            duration_sec=time.monotonic() - t0,
                        ))
                        _write_checkpoint(run_dir, current_stage)
                        retried = True
                        break
                    except Exception as retry_exc:
                        logger.warning("Retry %d failed: %s", attempt + 1, retry_exc)

                if not retried:
                    print(f"FAILED ({exc})")
                    results.append(StageResult(
                        stage=current_stage, status=StageStatus.FAILED,
                        duration_sec=duration, error=str(exc),
                    ))
                    break
                else:
                    idx = list(Stage).index(current_stage)
                    current_stage = list(Stage)[idx + 1] if idx + 1 < len(Stage) else None

    # Write pipeline summary
    _write_pipeline_summary(run_dir, run_id, results)
    return results


def _write_pipeline_summary(
    run_dir: Path, run_id: str, results: list[StageResult]
) -> None:
    """Write summary JSON."""
    summary = {
        "run_id": run_id,
        "timestamp": _utcnow_iso(),
        "total_stages": len(results),
        "completed": sum(1 for r in results if r.status == StageStatus.DONE),
        "failed": sum(1 for r in results if r.status == StageStatus.FAILED),
        "total_duration_sec": sum(r.duration_sec for r in results),
        "stages": [
            {
                "stage": int(r.stage),
                "name": r.stage.name,
                "status": r.status.value,
                "duration_sec": round(r.duration_sec, 2),
                "error": r.error,
            }
            for r in results
        ],
    }
    out = run_dir / "pipeline_summary.json"
    out.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
