from dataclasses import dataclass
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, SecretStr
from sqlmodel import Session

from noviscope.agents.demand_validation import (
    DemandValidationRunError,
    DemandValidationRunner,
    DemandValidationStageRunner,
    get_demand_validation_runner,
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
from noviscope.core.stage_policy import normalize_stage_output_payload
from noviscope.models.provider import ModelProvider
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
    runner: StageRunner


@dataclass(frozen=True, slots=True)
class ProviderSelection:
    provider: ModelProvider | None
    blocking_reason: str
    blocking_detail: str


@dataclass(frozen=True, slots=True)
class StageBlock:
    summary: str
    evidence_payload: JsonObject


def get_stage_runner_registry(
    demand_runner: Annotated[DemandValidationRunner, Depends(get_demand_validation_runner)],
) -> StageRunnerRegistry:
    demand_stage_runner = DemandValidationStageRunner(demand_runner)
    return StageRunnerRegistry(runners={demand_stage_runner.agent_id: demand_stage_runner})


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
                provider=None,
            )
        if provider.kind not in context.runner.supported_provider_kinds:
            return ProviderSelection(
                blocking_detail="Choose an OpenAI-compatible or custom provider for this stage.",
                blocking_reason="unsupported_provider",
                provider=None,
            )
        return ProviderSelection(blocking_detail="", blocking_reason="", provider=provider)

    for provider in context.provider_service.list_providers_for_user(context.current_user):
        if provider.is_active and provider.kind in context.runner.supported_provider_kinds:
            return ProviderSelection(blocking_detail="", blocking_reason="", provider=provider)

    return ProviderSelection(
        blocking_detail=(
            "Configure an active OpenAI-compatible or custom provider before running this stage."
        ),
        blocking_reason="missing_provider",
        provider=None,
    )


def build_provider_credentials(
    provider: ModelProvider,
    provider_service: ProviderService,
) -> ModelProviderCredentials:
    return ModelProviderCredentials(
        api_key=SecretStr(provider_service.decrypt_api_key(provider)),
        base_url=provider.base_url,
        id=provider.id,
        kind=provider.kind,
        model=provider.default_model,
        name=provider.name,
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
    try:
        stage = quest_service.get_stage_card_for_user(stage_id, current_user)
        runner = registry.get_runner(stage.agent_id)
        if runner is None:
            return apply_stage_block(quest_service, stage_id, build_runner_block(stage))

        quest = quest_service.get_quest_for_user(stage.quest_id, current_user)
        selection = select_provider(
            ProviderSelectionContext(
                current_user=current_user,
                provider_id=request.provider_id,
                provider_service=provider_service,
                runner=runner,
            )
        )
        if selection.provider is None:
            return apply_stage_block(quest_service, stage_id, build_provider_block(selection))

        provider = build_provider_credentials(selection.provider, provider_service)
        queued_context = StageRunContext(provider=provider, quest=quest, stage=stage)
        running_stage = quest_service.update_stage_card(
            stage_id,
            input_payload=runner.build_input_payload(queued_context),
            status=StageStatus.RUNNING,
        )
        running_context = StageRunContext(
            provider=provider,
            quest=quest,
            stage=running_stage,
        )
        result = runner.run(running_context)
        completed_stage = quest_service.update_stage_card(
            stage_id,
            evidence_payload=result.evidence_payload,
            output_payload=normalize_stage_output_payload(stage.agent_id, result.output_payload),
            summary=result.summary,
            status=StageStatus.COMPLETE,
        )
        return stage_response(completed_stage)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except DemandValidationRunError as exc:
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
