from dataclasses import dataclass
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlmodel import Session

from noviscope.agents.demand_validation import (
    DemandValidationOutput,
    DemandValidationRequest,
    DemandValidationRunError,
    DemandValidationRunner,
    get_demand_validation_runner,
)
from noviscope.api.dependencies import get_session
from noviscope.api.routes import StageCardResponse, get_provider_service, stage_response
from noviscope.auth.dependencies import get_current_user
from noviscope.models.provider import ModelProvider, ProviderKind
from noviscope.models.quest import Quest, StageCard, StageStatus
from noviscope.models.user import User
from noviscope.providers.service import ProviderService
from noviscope.quests.service import QuestService

router = APIRouter()

DEMAND_VALIDATOR_AGENT_ID = "demand_validator"


@dataclass(frozen=True, slots=True)
class DemandValidationRunContext:
    stage: StageCard
    quest: Quest
    provider: ModelProvider


class StageRunRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    provider_id: str | None = None


def is_supported_demand_validation_provider(provider: ModelProvider) -> bool:
    return provider.kind in {ProviderKind.OPENAI_COMPATIBLE, ProviderKind.CUSTOM}


def select_provider(
    provider_service: ProviderService,
    current_user: User,
    provider_id: str | None,
) -> ModelProvider | None:
    if provider_id is not None:
        provider = provider_service.get_provider_for_user(provider_id, current_user)
        if provider.is_active:
            return provider
        return None

    for provider in provider_service.list_providers_for_user(current_user):
        if provider.is_active and is_supported_demand_validation_provider(provider):
            return provider
    return None


def build_runner_request(
    context: DemandValidationRunContext,
    provider_service: ProviderService,
) -> DemandValidationRequest:
    return DemandValidationRequest(
        api_key=provider_service.decrypt_api_key(context.provider),
        base_url=context.provider.base_url,
        initial_direction=context.quest.initial_direction,
        model=context.provider.default_model,
        provider_id=context.provider.id,
        provider_kind=context.provider.kind,
        provider_name=context.provider.name,
        quest_title=context.quest.title,
        stage_id=context.stage.id,
    )


def build_input_payload(stage: StageCard, provider: ModelProvider) -> dict[str, object]:
    return {
        "agent_id": stage.agent_id,
        "provider_id": provider.id,
        "provider_name": provider.name,
        "provider_model": provider.default_model,
    }


def build_output_payload(output: DemandValidationOutput) -> dict[str, object]:
    return {
        "confidence": output.confidence,
        "demand_assessment": output.demand_assessment,
        "evidence": output.evidence,
        "next_step": output.next_step,
        "raw_response": output.raw_response,
        "risks": output.risks,
    }


def build_evidence_payload(
    provider: ModelProvider,
    output: DemandValidationOutput,
) -> dict[str, object]:
    return {
        "provider_id": provider.id,
        "provider_name": provider.name,
        "provider_model": provider.default_model,
        "risk_count": len(output.risks),
    }


@router.post("/stages/{stage_id}/run", response_model=StageCardResponse)
def run_stage(
    stage_id: str,
    request: StageRunRequest,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
    runner: Annotated[DemandValidationRunner, Depends(get_demand_validation_runner)],
) -> StageCardResponse:
    quest_service = QuestService(session)
    provider_service = get_provider_service(session)
    try:
        stage = quest_service.get_stage_card_for_user(stage_id, current_user)
        if stage.agent_id != DEMAND_VALIDATOR_AGENT_ID:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only demand validation stages can be run in this MVP.",
            )
        quest = quest_service.get_quest_for_user(stage.quest_id, current_user)
        provider = select_provider(provider_service, current_user, request.provider_id)
        if provider is None:
            blocked_stage = quest_service.update_stage_card(
                stage_id,
                evidence_payload={"blocking_reason": "missing_provider"},
                summary="No active model provider is available for this user.",
                status=StageStatus.BLOCKED,
            )
            return stage_response(blocked_stage)

        running_stage = quest_service.update_stage_card(
            stage_id,
            input_payload=build_input_payload(stage, provider),
            status=StageStatus.RUNNING,
        )
        run_context = DemandValidationRunContext(
            provider=provider,
            quest=quest,
            stage=running_stage,
        )
        output = runner.run(build_runner_request(run_context, provider_service))
        completed_stage = quest_service.update_stage_card(
            stage_id,
            evidence_payload=build_evidence_payload(provider, output),
            output_payload=build_output_payload(output),
            summary=output.summary,
            status=StageStatus.COMPLETE,
        )
        return stage_response(completed_stage)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except DemandValidationRunError as exc:
        blocked_stage = quest_service.update_stage_card(
            stage_id,
            evidence_payload={"blocking_reason": "runner_error", "message": str(exc)},
            summary=str(exc),
            status=StageStatus.BLOCKED,
        )
        return stage_response(blocked_stage)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
