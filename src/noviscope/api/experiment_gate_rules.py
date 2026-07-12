from noviscope.api.experiment_gate_stage_checks import (
    demand_validation_check,
    experiment_plan_check,
    experiment_setup_check,
    idea_selection_check,
)
from noviscope.api.experiment_gate_types import (
    ExperimentGateCheck,
    ExperimentGateCheckStatus,
    ExperimentGateResponse,
    ExperimentGateStatus,
)
from noviscope.core.stage_policy import (
    DEMAND_VALIDATOR_AGENT_ID,
    EXPERIMENT_PLANNER_AGENT_ID,
    IDEA_GENERATOR_AGENT_ID,
)
from noviscope.models.quest import StageCard


def stage_lookup(stages: list[StageCard]) -> dict[str, StageCard]:
    return {stage.agent_id: stage for stage in stages}


def gate_status(checks: list[ExperimentGateCheck]) -> ExperimentGateStatus:
    if any(check.status == ExperimentGateCheckStatus.BLOCKED for check in checks):
        return ExperimentGateStatus.BLOCKED
    if any(check.status == ExperimentGateCheckStatus.NEEDS_REVIEW for check in checks):
        return ExperimentGateStatus.NEEDS_REVIEW
    return ExperimentGateStatus.READY


def build_experiment_gate(quest_id: str, stages: list[StageCard]) -> ExperimentGateResponse:
    stages_by_agent = stage_lookup(stages)
    checks = [
        demand_validation_check(stages_by_agent.get(DEMAND_VALIDATOR_AGENT_ID)),
        idea_selection_check(stages_by_agent.get(IDEA_GENERATOR_AGENT_ID)),
        experiment_setup_check(stages_by_agent.get(EXPERIMENT_PLANNER_AGENT_ID)),
        experiment_plan_check(stages_by_agent.get(EXPERIMENT_PLANNER_AGENT_ID)),
    ]
    status_value = gate_status(checks)
    return ExperimentGateResponse(
        blocking_reasons=[
            check.detail for check in checks if check.status != ExperimentGateCheckStatus.PASS
        ],
        checks=checks,
        gate_status=status_value,
        quest_id=quest_id,
        ready_for_experiment=status_value == ExperimentGateStatus.READY,
    )
