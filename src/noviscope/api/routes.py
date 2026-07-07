from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlmodel import Session

from noviscope.agents.registry import AGENT_REGISTRY, AgentSpec
from noviscope.api.dependencies import get_session
from noviscope.auth.dependencies import get_current_user
from noviscope.core.config import get_settings
from noviscope.core.crypto import SecretBox
from noviscope.core.json_types import JsonObject
from noviscope.core.stage_policy import (
    StageConfidence,
    normalize_stage_output_payload,
    stage_confidence,
)
from noviscope.models.quest import Quest, QuestStatus, StageCard, StageStatus
from noviscope.models.user import User
from noviscope.providers.service import ProviderService
from noviscope.quests.service import QuestService

router = APIRouter()

class QuestCreateRequest(BaseModel):
    title: str
    initial_direction: str


class StageCardResponse(BaseModel):
    id: str
    quest_id: str
    agent_id: str
    title: str
    status: StageStatus
    confidence: StageConfidence
    summary: str
    input_payload: JsonObject
    output_payload: JsonObject
    evidence_payload: JsonObject
    human_approved: bool | None
    review_notes: str
    created_at: str
    updated_at: str


class QuestCreateResponse(BaseModel):
    id: str
    owner_user_id: str | None
    title: str
    initial_direction: str
    status: QuestStatus
    first_stage: StageCardResponse


class QuestResponse(BaseModel):
    id: str
    owner_user_id: str | None
    title: str
    initial_direction: str
    status: QuestStatus
    created_at: str
    updated_at: str


class QuestsResponse(BaseModel):
    quests: list[QuestResponse]


class AgentsResponse(BaseModel):
    agents: list[AgentSpec]


class StagesResponse(BaseModel):
    stages: list[StageCardResponse]


class StageUpdateRequest(BaseModel):
    status: StageStatus | None = None
    summary: str | None = None
    input_payload: JsonObject | None = None
    output_payload: JsonObject | None = None
    evidence_payload: JsonObject | None = None
    human_approved: bool | None = None
    review_notes: str | None = None


def stage_response(stage: StageCard) -> StageCardResponse:
    output_payload = normalize_stage_output_payload(stage.agent_id, stage.output_payload)
    return StageCardResponse.model_validate(
        {
            **stage.model_dump(),
            "confidence": stage_confidence(stage.agent_id, output_payload),
            "output_payload": output_payload,
        }
    )


def quest_response(quest: Quest) -> QuestResponse:
    return QuestResponse.model_validate(quest, from_attributes=True)


def get_provider_service(session: Session) -> ProviderService:
    settings = get_settings()
    return ProviderService(session, SecretBox(settings.provider_secret_key))


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/agents")
def list_agents() -> AgentsResponse:
    return AgentsResponse(agents=list(AGENT_REGISTRY.values()))


@router.post("/quests", status_code=status.HTTP_201_CREATED, response_model=QuestCreateResponse)
def create_quest(
    request: QuestCreateRequest,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> QuestCreateResponse:
    service = QuestService(session)
    quest = service.create_quest(
        title=request.title,
        initial_direction=request.initial_direction,
        owner_user_id=current_user.id,
    )
    first_stage = service.list_stage_cards(quest.id)[0]
    return QuestCreateResponse(
        id=quest.id,
        owner_user_id=quest.owner_user_id,
        title=quest.title,
        initial_direction=quest.initial_direction,
        status=quest.status,
        first_stage=stage_response(first_stage),
    )


@router.get("/quests", response_model=QuestsResponse)
def list_quests(
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> QuestsResponse:
    service = QuestService(session)
    return QuestsResponse(
        quests=[quest_response(quest) for quest in service.list_quests_for_user(current_user)]
    )


@router.get("/quests/{quest_id}", response_model=QuestResponse)
def get_quest(
    quest_id: str,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> QuestResponse:
    service = QuestService(session)
    try:
        return quest_response(service.get_quest_for_user(quest_id, current_user))
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


@router.get("/quests/{quest_id}/stages", response_model=StagesResponse)
def list_quest_stages(
    quest_id: str,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> StagesResponse:
    service = QuestService(session)
    try:
        service.get_quest_for_user(quest_id, current_user)
        return StagesResponse(
            stages=[stage_response(stage) for stage in service.list_stage_cards(quest_id)]
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


@router.patch("/stages/{stage_id}", response_model=StageCardResponse)
def update_stage(
    stage_id: str,
    request: StageUpdateRequest,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> StageCardResponse:
    service = QuestService(session)
    try:
        existing_stage = service.get_stage_card_for_user(stage_id, current_user)
        output_payload = (
            normalize_stage_output_payload(existing_stage.agent_id, request.output_payload)
            if request.output_payload is not None
            else None
        )
        stage = service.update_stage_card(
            stage_id,
            status=request.status,
            summary=request.summary,
            input_payload=request.input_payload,
            output_payload=output_payload,
            evidence_payload=request.evidence_payload,
            human_approved=request.human_approved,
            human_approved_set="human_approved" in request.model_fields_set,
            review_notes=request.review_notes,
        )
        return stage_response(stage)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
