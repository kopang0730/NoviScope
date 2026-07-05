from dataclasses import dataclass
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, SecretStr
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
    has_selected_idea,
    missing_experiment_setup_inputs,
)
from noviscope.agents.gap_hypothesis import (
    GapHypothesisRunError,
    GapHypothesisRunner,
    GapHypothesisStageRunner,
    get_gap_hypothesis_runner,
)
from noviscope.agents.literature_scout import (
    LITERATURE_SCOUT_AGENT_ID,
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
    ModelProviderCredentials,
    StageRunContext,
    StageRunner,
    StageRunnerRegistry,
)
from noviscope.api.dependencies import get_session
from noviscope.api.routes import StageCardResponse, get_provider_service, stage_response
from noviscope.auth.dependencies import get_current_user
from noviscope.core.json_types import JsonObject
from noviscope.core.stage_policy import (
    DEMAND_VALIDATOR_AGENT_ID,
    EXPERIMENT_PLANNER_AGENT_ID,
    IDEA_GENERATOR_AGENT_ID,
    PAPER_MEETING_WRITER_AGENT_ID,
    normalize_stage_output_payload,
)
from noviscope.models.provider import ModelProvider, ProviderKind
from noviscope.models.quest import StageCard, StageStatus
from noviscope.models.user import User
from noviscope.providers.service import ProviderService
from noviscope.quests.service import QuestService

router = APIRouter()


class StageRunRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    provider_id: str | None = None


@dataclass(frozen=True, slots=True)
class ProviderSelectionContext:
    provider_service: ProviderService
    current_user: User
    provider_id: str | None
    model_name: str | None
    runner: StageRunner


@dataclass(frozen=True, slots=True)
class ProviderSelection:
    provider: ModelProvider | None
    model_name: str | None
    blocking_reason: str
    blocking_detail: str


@dataclass(frozen=True, slots=True)
class StageBlock:
    summary: str
    evidence_payload: JsonObject


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


def select_provider(context: ProviderSelectionContext) -> ProviderSelection:
    if context.provider_id is not None:
        provider = context.provider_service.get_provider_for_user(
            context.provider_id,
            context.current_user,
        )
        if not provider.is_active:
            return ProviderSelection(
                blocking_detail="Activate this provider before running the stage.",
                blocking_reason="inactive_provider",
                model_name=None,
                provider=None,
            )
        if provider.kind not in context.runner.supported_provider_kinds:
            return ProviderSelection(
                blocking_detail="Choose an OpenAI-compatible or custom provider for this stage.",
                blocking_reason="unsupported_provider",
                model_name=None,
                provider=None,
            )
        return ProviderSelection(
            blocking_detail="",
            blocking_reason="",
            model_name=context.model_name,
            provider=provider,
        )

    for provider in context.provider_service.list_providers_for_user(context.current_user):
        if provider.is_active and provider.kind in context.runner.supported_provider_kinds:
            return ProviderSelection(
                blocking_detail="",
                blocking_reason="",
                model_name=None,
                provider=provider,
            )

    return ProviderSelection(
        blocking_detail=(
            "Configure an active OpenAI-compatible or custom provider before running this stage."
        ),
        blocking_reason="missing_provider",
        model_name=None,
        provider=None,
    )


def build_provider_credentials(
    provider: ModelProvider,
    provider_service: ProviderService,
    model_name: str | None = None,
) -> ModelProviderCredentials:
    return ModelProviderCredentials(
        api_key=SecretStr(provider_service.decrypt_api_key(provider)),
        base_url=provider.base_url,
        id=provider.id,
        kind=provider.kind,
        model=model_name or provider.default_model,
        name=provider.name,
    )


def build_server_managed_provider() -> ModelProviderCredentials:
    return ModelProviderCredentials(
        api_key=SecretStr(""),
        base_url="https://api.openalex.org",
        id="server_openalex",
        kind=ProviderKind.CUSTOM,
        model="openalex-works",
        name="OpenAlex",
    )


def build_provider_block(selection: ProviderSelection) -> StageBlock:
    return StageBlock(
        evidence_payload={
            "blocking_detail": selection.blocking_detail,
            "blocking_reason": selection.blocking_reason,
            "can_run": False,
        },
        summary="No active model provider is available for this user.",
    )


def build_literature_dependency_block() -> StageBlock:
    return StageBlock(
        evidence_payload={
            "blocking_detail": "Complete Demand validation before running Literature Scout.",
            "blocking_reason": "demand_validation_incomplete",
            "can_run": False,
        },
        summary="Literature Scout is blocked until Demand validation is complete.",
    )


def build_demand_review_block(stage_title: str) -> StageBlock:
    return StageBlock(
        evidence_payload={
            "blocking_detail": (
                f"Approve Demand validation before running {stage_title}. If the demand was "
                "rejected, revise or rerun Demand validation first."
            ),
            "blocking_reason": "demand_validation_review_required",
            "can_run": False,
        },
        summary=f"{stage_title} is blocked until Demand validation is human-approved.",
    )


def build_gap_dependency_block(missing_stage_names: list[str]) -> StageBlock:
    missing = ", ".join(missing_stage_names)
    return StageBlock(
        evidence_payload={
            "blocking_detail": (
                f"Complete {missing} before running Gap & hypothesis generator."
            ),
            "blocking_reason": "gap_prerequisites_incomplete",
            "can_run": False,
            "missing_prerequisites": missing_stage_names,
        },
        summary="Gap & hypothesis generator is blocked until prerequisite stages complete.",
    )


def build_experiment_dependency_block() -> StageBlock:
    return StageBlock(
        evidence_payload={
            "blocking_detail": (
                "Complete Gap & hypothesis generator, then select and approve one idea before "
                "running Experiment Planner."
            ),
            "blocking_reason": "experiment_prerequisites_incomplete",
            "can_run": False,
        },
        summary="Experiment Planner is blocked until a generated idea is selected.",
    )


def build_experiment_setup_block(missing_inputs: list[str]) -> StageBlock:
    return StageBlock(
        evidence_payload={
            "blocking_detail": (
                "Add data path, code repository, and environment notes before generating an "
                "experiment plan."
            ),
            "blocking_reason": "missing_experiment_inputs",
            "can_run": False,
            "missing_inputs": missing_inputs,
        },
        summary="Experiment Planner needs experiment setup inputs before it can run.",
    )


def build_paper_dependency_block() -> StageBlock:
    return StageBlock(
        evidence_payload={
            "blocking_detail": "Complete Experiment Planner before generating paper artifacts.",
            "blocking_reason": "paper_prerequisites_incomplete",
            "can_run": False,
        },
        summary="Paper & Meeting Writer is blocked until Experiment Planner completes.",
    )


def build_paper_review_block() -> StageBlock:
    return StageBlock(
        evidence_payload={
            "blocking_detail": (
                "Approve Experiment Planner before generating paper or meeting artifacts. "
                "Drafts must not rely on an unreviewed experiment plan."
            ),
            "blocking_reason": "experiment_planner_review_required",
            "can_run": False,
        },
        summary="Paper & Meeting Writer is blocked until Experiment Planner is human-approved.",
    )


def build_runner_block(stage: StageCard) -> StageBlock:
    return StageBlock(
        evidence_payload={
            "blocking_detail": "No runner has been implemented for this workflow stage yet.",
            "blocking_reason": "runner_not_implemented",
            "can_run": False,
        },
        summary=f"{stage.title} is not automated in this MVP yet.",
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


def build_dependency_block_if_needed(
    stage: StageCard,
    stages: list[StageCard],
) -> StageBlock | None:
    demand_stage = find_workflow_stage(stages, DEMAND_VALIDATOR_AGENT_ID)
    completed_agent_ids = {
        workflow_stage.agent_id
        for workflow_stage in stages
        if workflow_stage.status == StageStatus.COMPLETE
    }
    if (
        stage.agent_id == LITERATURE_SCOUT_AGENT_ID
        and DEMAND_VALIDATOR_AGENT_ID not in completed_agent_ids
    ):
        return build_literature_dependency_block()
    if stage.agent_id != DEMAND_VALIDATOR_AGENT_ID and demand_stage is not None:
        if demand_stage.status == StageStatus.COMPLETE and demand_stage.human_approved is not True:
            return build_demand_review_block(stage.title)
    if stage.agent_id == IDEA_GENERATOR_AGENT_ID:
        missing_stage_names: list[str] = []
        if DEMAND_VALIDATOR_AGENT_ID not in completed_agent_ids:
            missing_stage_names.append("Demand validation")
        if LITERATURE_SCOUT_AGENT_ID not in completed_agent_ids:
            missing_stage_names.append("Literature Scout")
        if missing_stage_names:
            return build_gap_dependency_block(missing_stage_names)
    if stage.agent_id == EXPERIMENT_PLANNER_AGENT_ID:
        idea_stage = find_workflow_stage(stages, IDEA_GENERATOR_AGENT_ID)
        if (
            idea_stage is None
            or idea_stage.status != StageStatus.COMPLETE
            or not has_selected_idea(idea_stage)
        ):
            return build_experiment_dependency_block()
        missing_inputs = missing_experiment_setup_inputs(stage.input_payload)
        if missing_inputs:
            return build_experiment_setup_block(missing_inputs)
    if stage.agent_id == PAPER_MEETING_WRITER_AGENT_ID:
        experiment_stage = find_workflow_stage(stages, EXPERIMENT_PLANNER_AGENT_ID)
        if experiment_stage is None or experiment_stage.status != StageStatus.COMPLETE:
            return build_paper_dependency_block()
        if experiment_stage.human_approved is not True:
            return build_paper_review_block()
    return None


def find_workflow_stage(stages: list[StageCard], agent_id: str) -> StageCard | None:
    return next(
        (workflow_stage for workflow_stage in stages if workflow_stage.agent_id == agent_id),
        None,
    )


def build_runner_provider(
    runner: StageRunner,
    selection_context: ProviderSelectionContext,
) -> ModelProviderCredentials | StageBlock:
    if not runner.supported_provider_kinds:
        return build_server_managed_provider()
    selection = select_provider(selection_context)
    if selection.provider is None:
        return build_provider_block(selection)
    return build_provider_credentials(
        selection.provider,
        selection_context.provider_service,
        model_name=selection.model_name,
    )


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
