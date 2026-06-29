from typing import Annotated

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel
from sqlmodel import Session

from noviscope.agents.registry import AGENT_REGISTRY, AgentSpec
from noviscope.models.quest import QuestStatus, StageStatus
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
    summary: str
    created_at: str


class QuestCreateResponse(BaseModel):
    id: str
    title: str
    initial_direction: str
    status: QuestStatus
    first_stage: StageCardResponse


class AgentsResponse(BaseModel):
    agents: list[AgentSpec]


def get_session() -> Session:
    raise RuntimeError("session dependency must be overridden by create_app")


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
) -> QuestCreateResponse:
    service = QuestService(session)
    quest = service.create_quest(
        title=request.title,
        initial_direction=request.initial_direction,
    )
    first_stage = service.list_stage_cards(quest.id)[0]
    return QuestCreateResponse(
        id=quest.id,
        title=quest.title,
        initial_direction=quest.initial_direction,
        status=quest.status,
        first_stage=StageCardResponse.model_validate(first_stage, from_attributes=True),
    )
