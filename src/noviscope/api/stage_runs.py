from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlmodel import Session

from noviscope.agents.assignments import AgentAssignmentService
from noviscope.agents.demand_validation import (
    DemandValidationRunError,
    DemandValidationRunner,
    DemandValidationStageRunner,
    get_demand_validation_runner,
)
from noviscope.agents.experiment_planner import (
    ExperimentPlannerRunError,
    ExperimentPlannerRunner,
    ExperimentPlannerStageRunner,
    get_experiment_planner_runner,
)
from noviscope.agents.gap_hypothesis import (
    GapHypothesisRunError,
    GapHypothesisRunner,
    GapHypothesisStageRunner,
    get_gap_hypothesis_runner,
)
from noviscope.agents.literature_scout import (
    LiteratureScoutStageRunner,
    get_literature_scout_runner,
)
from noviscope.agents.openalex_client import LiteratureScoutRunError
from noviscope.agents.paper_meeting_writer import (
    PaperMeetingWriterRunError,
    PaperMeetingWriterRunner,
    PaperMeetingWriterStageRunner,
    get_paper_meeting_writer_runner,
)
from noviscope.agents.stage_runner import (
    StageRunContext,
    StageRunnerRegistry,
)
from noviscope.api.dependencies import get_session
from noviscope.api.routes import StageCardResponse, get_provider_service, stage_response
from noviscope.api.stage_provider_selection import (
    ProviderSelectionContext,
    build_runner_provider,
)
from noviscope.api.stage_run_blocks import (
    StageBlock,
    build_dependency_block_if_needed,
    build_runner_block,
)
from noviscope.auth.dependencies import get_current_user
from noviscope.core.stage_policy import normalize_stage_output_payload
from noviscope.models.quest import StageStatus
from noviscope.models.user import User
from noviscope.quests.service import QuestService

router = APIRouter()


class StageRunRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    provider_id: str | None = None


def get_stage_runner_registry(
    demand_runner: Annotated[DemandValidationRunner, Depends(get_demand_validation_runner)],
    experiment_runner: Annotated[ExperimentPlannerRunner, Depends(get_experiment_planner_runner)],
    gap_runner: Annotated[GapHypothesisRunner, Depends(get_gap_hypothesis_runner)],
    literature_runner: Annotated[LiteratureScoutStageRunner, Depends(get_literature_scout_runner)],
    paper_runner: Annotated[PaperMeetingWriterRunner, Depends(get_paper_meeting_writer_runner)],
) -> StageRunnerRegistry:
    demand_stage_runner = DemandValidationStageRunner(demand_runner)
    experiment_stage_runner = ExperimentPlannerStageRunner(experiment_runner)
    gap_stage_runner = GapHypothesisStageRunner(gap_runner)
    paper_stage_runner = PaperMeetingWriterStageRunner(paper_runner)
    return StageRunnerRegistry(
        runners={
            demand_stage_runner.agent_id: demand_stage_runner,
            experiment_stage_runner.agent_id: experiment_stage_runner,
            gap_stage_runner.agent_id: gap_stage_runner,
            literature_runner.agent_id: literature_runner,
            paper_stage_runner.agent_id: paper_stage_runner,
        }
    )


def apply_stage_block(
    quest_service: QuestService,
    stage_id: str,
    block: StageBlock,
) -> StageCardResponse:
    blocked_stage = quest_service.update_stage_card(
        stage_id,
        evidence_payload=block.evidence_payload,
        summary=block.summary,
        status=StageStatus.BLOCKED,
    )
    return stage_response(blocked_stage)


@router.post("/stages/{stage_id}/run", response_model=StageCardResponse)
def run_stage(
    stage_id: str,
    request: StageRunRequest,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
    registry: Annotated[StageRunnerRegistry, Depends(get_stage_runner_registry)],
) -> StageCardResponse:
    quest_service = QuestService(session)
    provider_service = get_provider_service(session)
    assignment_service = AgentAssignmentService(session)
    try:
        stage = quest_service.get_stage_card_for_user(stage_id, current_user)
        runner = registry.get_runner(stage.agent_id)
        if runner is None:
            return apply_stage_block(quest_service, stage_id, build_runner_block(stage))

        quest = quest_service.get_quest_for_user(stage.quest_id, current_user)
        workflow_stages = quest_service.list_stage_cards(quest.id)
        dependency_block = build_dependency_block_if_needed(stage, workflow_stages)
        if dependency_block is not None:
            return apply_stage_block(quest_service, stage_id, dependency_block)

        assignment = assignment_service.get_assignment(stage.agent_id)
        configured_provider_id = assignment.provider_id if assignment is not None else None
        configured_model_name = assignment.model_name if assignment is not None else None
        effective_provider_id = (
            request.provider_id if request.provider_id is not None else configured_provider_id
        )
        effective_model_name = (
            None if request.provider_id is not None else configured_model_name
        )

        provider_or_block = build_runner_provider(
            runner,
            ProviderSelectionContext(
                current_user=current_user,
                model_name=effective_model_name,
                provider_id=effective_provider_id,
                provider_service=provider_service,
                runner=runner,
            ),
        )
        if isinstance(provider_or_block, StageBlock):
            return apply_stage_block(quest_service, stage_id, provider_or_block)

        provider = provider_or_block
        queued_context = StageRunContext(
            provider=provider,
            quest=quest,
            stage=stage,
            workflow_stages=tuple(workflow_stages),
        )
        running_stage = quest_service.update_stage_card(
            stage_id,
            input_payload=runner.build_input_payload(queued_context),
            status=StageStatus.RUNNING,
        )
        running_context = StageRunContext(
            provider=provider,
            quest=quest,
            stage=running_stage,
            workflow_stages=tuple(workflow_stages),
        )
        result = runner.run(running_context)
        output_payload = normalize_stage_output_payload(
            stage.agent_id,
            {**result.output_payload, "confidence": result.confidence},
        )
        completed_stage = quest_service.update_stage_card(
            stage_id,
            evidence_payload=result.evidence_payload | provider.provenance_payload(),
            input_payload=result.input_payload,
            output_payload=output_payload,
            summary=result.summary,
            status=StageStatus.COMPLETE,
        )
        return stage_response(completed_stage)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except (
        DemandValidationRunError,
        ExperimentPlannerRunError,
        GapHypothesisRunError,
        LiteratureScoutRunError,
        PaperMeetingWriterRunError,
    ) as exc:
        return apply_stage_block(
            quest_service,
            stage_id,
            StageBlock(
                evidence_payload={
                    "blocking_detail": str(exc),
                    "blocking_reason": "runner_error",
                    "can_run": False,
                },
                summary=str(exc),
            ),
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
