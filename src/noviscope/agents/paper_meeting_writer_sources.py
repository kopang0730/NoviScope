from noviscope.agents.literature_scout import LITERATURE_SCOUT_AGENT_ID
from noviscope.agents.paper_meeting_writer_results import experiment_result_records
from noviscope.agents.paper_meeting_writer_types import PaperMeetingWriterRunError
from noviscope.core.json_types import JsonObject
from noviscope.core.stage_policy import (
    CODE_RUNNER_AGENT_ID,
    CODE_RUNNER_METRIC_RECORDS_KEY,
    DEMAND_VALIDATOR_AGENT_ID,
    EVIDENCE_AUDITOR_AGENT_ID,
    EXPERIMENT_PLANNER_AGENT_ID,
    IDEA_GENERATOR_AGENT_ID,
)
from noviscope.models.quest import StageCard, StageStatus


def find_stage(stages: tuple[StageCard, ...], agent_id: str) -> StageCard | None:
    return next((stage for stage in stages if stage.agent_id == agent_id), None)


def require_complete_experiment_stage(stages: tuple[StageCard, ...]) -> StageCard:
    stage = find_stage(stages, EXPERIMENT_PLANNER_AGENT_ID)
    if stage is None or stage.status != StageStatus.COMPLETE:
        raise PaperMeetingWriterRunError(
            "Experiment Planner must complete before Paper & Meeting Writer runs."
        )
    return stage


def build_source_stage_ids(stages: tuple[StageCard, ...]) -> JsonObject:
    source_stage_keys = (
        (DEMAND_VALIDATOR_AGENT_ID, "demand_validation"),
        (EXPERIMENT_PLANNER_AGENT_ID, "experiment_planner"),
        (IDEA_GENERATOR_AGENT_ID, "idea_generator"),
        (LITERATURE_SCOUT_AGENT_ID, "literature_scout"),
        (CODE_RUNNER_AGENT_ID, "code_runner"),
        (EVIDENCE_AUDITOR_AGENT_ID, "evidence_auditor"),
    )
    return {
        key: stage.id if (stage := find_stage(stages, agent_id)) is not None else ""
        for agent_id, key in source_stage_keys
    }


def trusted_experiment_result_records(stages: tuple[StageCard, ...]) -> list[JsonObject]:
    records: list[JsonObject] = []
    for stage in stages:
        if (
            stage.agent_id != CODE_RUNNER_AGENT_ID
            or stage.status != StageStatus.COMPLETE
            or stage.human_approved is not True
        ):
            continue
        records.extend(
            experiment_result_records(stage.output_payload.get(CODE_RUNNER_METRIC_RECORDS_KEY))
        )
    return records
