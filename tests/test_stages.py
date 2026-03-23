"""Tests for the 23-stage pipeline state machine."""

from researchclaw.pipeline.stages import (
    GATE_STAGES,
    NONCRITICAL_STAGES,
    PHASE_MAP,
    STAGE_SEQUENCE,
    Stage,
    StageStatus,
    TransitionEvent,
    advance,
    default_rollback_stage,
    gate_required,
)
from researchclaw.pipeline.contracts import CONTRACTS as CONTRACTS_MAP


def test_stage_count():
    """Pipeline must have exactly 23 stages."""
    assert len(Stage) == 23
    assert len(STAGE_SEQUENCE) == 23


def test_stage_sequence_is_monotonic():
    """Stages must be numbered 1..23 in order."""
    values = [int(s) for s in STAGE_SEQUENCE]
    assert values == list(range(1, 24))


def test_gate_stages():
    """Gate stages must be 5, 9, 20."""
    gate_numbers = sorted(int(s) for s in GATE_STAGES)
    assert gate_numbers == [5, 9, 20]


def test_all_stages_have_contracts():
    """Every stage must have a contract."""
    for stage in Stage:
        assert stage in CONTRACTS_MAP, f"Missing contract for {stage.name}"


def test_contract_output_files_not_empty():
    """Every contract must produce at least one output file."""
    for stage, contract in CONTRACTS_MAP.items():
        assert len(contract.output_files) > 0, f"{stage.name} has no output_files"


def test_phase_map_covers_all_stages():
    """Phase map must cover all 23 stages."""
    all_in_phases = set()
    for stages in PHASE_MAP.values():
        all_in_phases.update(stages)
    assert all_in_phases == set(Stage)


def test_advance_start():
    """Starting a pending stage should move to RUNNING."""
    result = advance(Stage.TOPIC_INIT, StageStatus.PENDING, TransitionEvent.START)
    assert result.status == StageStatus.RUNNING


def test_advance_succeed_non_gate():
    """Succeeding a non-gate stage should move to DONE."""
    result = advance(Stage.TOPIC_INIT, StageStatus.RUNNING, TransitionEvent.SUCCEED)
    assert result.status == StageStatus.DONE
    assert result.next_stage == Stage.PROBLEM_DECOMPOSE


def test_advance_succeed_gate():
    """Succeeding a gate stage should block for approval."""
    result = advance(Stage.LITERATURE_SCREEN, StageStatus.RUNNING, TransitionEvent.SUCCEED)
    assert result.status == StageStatus.BLOCKED_APPROVAL


def test_advance_approve():
    """Approving a blocked stage should move to DONE."""
    result = advance(
        Stage.LITERATURE_SCREEN,
        StageStatus.BLOCKED_APPROVAL,
        TransitionEvent.APPROVE,
    )
    assert result.status == StageStatus.DONE


def test_advance_reject_rollback():
    """Rejecting a gate should roll back."""
    result = advance(
        Stage.LITERATURE_SCREEN,
        StageStatus.BLOCKED_APPROVAL,
        TransitionEvent.REJECT,
    )
    assert result.stage == Stage.LITERATURE_COLLECT
    assert result.status == StageStatus.PENDING


def test_advance_fail():
    """Failing a running stage should move to FAILED."""
    result = advance(Stage.TOPIC_INIT, StageStatus.RUNNING, TransitionEvent.FAIL)
    assert result.status == StageStatus.FAILED


def test_advance_retry():
    """Retrying a failed stage should move to RETRYING."""
    result = advance(Stage.TOPIC_INIT, StageStatus.FAILED, TransitionEvent.RETRY)
    assert result.status == StageStatus.RETRYING


def test_gate_required_with_hitl():
    """Gate required should respect HITL stage list."""
    assert gate_required(Stage.LITERATURE_SCREEN, [5, 9, 20]) is True
    assert gate_required(Stage.LITERATURE_SCREEN, [9, 20]) is False


def test_default_rollback():
    """Default rollback for gates should be configured."""
    assert default_rollback_stage(Stage.LITERATURE_SCREEN) == Stage.LITERATURE_COLLECT
    assert default_rollback_stage(Stage.EXPERIMENT_DESIGN) == Stage.HYPOTHESIS_GEN
    assert default_rollback_stage(Stage.QUALITY_GATE) == Stage.PAPER_OUTLINE


def test_noncritical_stages():
    """Noncritical stages should include QUALITY_GATE and KNOWLEDGE_ARCHIVE."""
    assert Stage.QUALITY_GATE in NONCRITICAL_STAGES
    assert Stage.KNOWLEDGE_ARCHIVE in NONCRITICAL_STAGES
    assert Stage.CITATION_VERIFY not in NONCRITICAL_STAGES
