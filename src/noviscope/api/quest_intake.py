from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlmodel import Session

from noviscope.api.dependencies import get_session
from noviscope.auth.dependencies import get_current_user
from noviscope.models.quest import Quest
from noviscope.models.user import User
from noviscope.quests.intake import QuestIntake, QuestIntakeUpdateSpec
from noviscope.quests.service import QuestService

router = APIRouter()


class QuestIntakeUpdateRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    intake_payload: QuestIntake
    initial_direction: str | None = None


class QuestIntakeResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    quest_id: str
    initial_direction: str
    intake_payload: QuestIntake


def quest_intake_response(quest: Quest) -> QuestIntakeResponse:
    return QuestIntakeResponse(
        initial_direction=quest.initial_direction,
        intake_payload=QuestIntake.model_validate(quest.intake_payload or {}),
        quest_id=quest.id,
    )


@router.get("/quests/{quest_id}/intake", response_model=QuestIntakeResponse)
def get_quest_intake(
    quest_id: str,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> QuestIntakeResponse:
    service = QuestService(session)
    try:
        return quest_intake_response(service.get_quest_for_user(quest_id, current_user))
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


@router.put("/quests/{quest_id}/intake", response_model=QuestIntakeResponse)
def update_quest_intake(
    quest_id: str,
    request: QuestIntakeUpdateRequest,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> QuestIntakeResponse:
    service = QuestService(session)
    try:
        service.get_quest_for_user(quest_id, current_user)
        quest = service.update_quest_intake(
            QuestIntakeUpdateSpec(
                initial_direction=request.initial_direction,
                intake=request.intake_payload,
                quest_id=quest_id,
            )
        )
        return quest_intake_response(quest)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
