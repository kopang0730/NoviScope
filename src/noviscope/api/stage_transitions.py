from dataclasses import dataclass
from typing import Annotated, ClassVar

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlmodel import Session, select

from noviscope.api.dependencies import get_session
from noviscope.auth.dependencies import get_current_user
from noviscope.models.quest import StageStatus
from noviscope.models.stage_transition import StageTransitionEvent
from noviscope.models.user import User
from noviscope.quests.service import QuestService

router = APIRouter()


@dataclass(frozen=True, slots=True)
class StageTransitionsContext:
    session: Session
    current_user: User


class StageTransitionEventResponse(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    agent_id: str
    blocking_detail: str
    blocking_reason: str
    created_at: str
    from_status: StageStatus | None
    id: str
    provider_id: str
    provider_model: str
    provider_name: str
    quest_id: str
    stage_id: str
    summary: str
    to_status: StageStatus


class QuestStageTransitionsResponse(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    events: tuple[StageTransitionEventResponse, ...]
    quest_id: str
    transition_count: int


def get_stage_transitions_context(
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> StageTransitionsContext:
    return StageTransitionsContext(current_user=current_user, session=session)


def stage_transition_response(event: StageTransitionEvent) -> StageTransitionEventResponse:
    return StageTransitionEventResponse(
        agent_id=event.agent_id,
        blocking_detail=event.blocking_detail,
        blocking_reason=event.blocking_reason,
        created_at=event.created_at,
        from_status=event.from_status,
        id=event.id,
        provider_id=event.provider_id,
        provider_model=event.provider_model,
        provider_name=event.provider_name,
        quest_id=event.quest_id,
        stage_id=event.stage_id,
        summary=event.summary,
        to_status=event.to_status,
    )


def list_stage_transition_events(
    session: Session,
    quest_id: str,
) -> tuple[StageTransitionEvent, ...]:
    statement = (
        select(StageTransitionEvent)
        .where(StageTransitionEvent.quest_id == quest_id)
        .order_by(StageTransitionEvent.created_at, StageTransitionEvent.id)
    )
    return tuple(session.exec(statement).all())


@router.get(
    "/quests/{quest_id}/stage-transitions",
    response_model=QuestStageTransitionsResponse,
)
def get_quest_stage_transitions(
    quest_id: str,
    context: Annotated[StageTransitionsContext, Depends(get_stage_transitions_context)],
) -> QuestStageTransitionsResponse:
    service = QuestService(context.session)
    try:
        _ = service.get_quest_for_user(quest_id, context.current_user)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    events = tuple(
        stage_transition_response(event)
        for event in list_stage_transition_events(context.session, quest_id)
    )
    return QuestStageTransitionsResponse(
        events=events,
        quest_id=quest_id,
        transition_count=len(events),
    )
