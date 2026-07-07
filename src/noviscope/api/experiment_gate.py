from dataclasses import dataclass
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from noviscope.api.dependencies import get_session
from noviscope.api.experiment_gate_rules import build_experiment_gate
from noviscope.api.experiment_gate_types import ExperimentGateResponse
from noviscope.auth.dependencies import get_current_user
from noviscope.models.user import User
from noviscope.quests.service import QuestService

router = APIRouter()


@dataclass(frozen=True, slots=True)
class ExperimentGateContext:
    session: Session
    current_user: User


def get_experiment_gate_context(
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> ExperimentGateContext:
    return ExperimentGateContext(current_user=current_user, session=session)


@router.get("/quests/{quest_id}/experiment-gate", response_model=ExperimentGateResponse)
def get_experiment_gate(
    quest_id: str,
    context: Annotated[ExperimentGateContext, Depends(get_experiment_gate_context)],
) -> ExperimentGateResponse:
    service = QuestService(context.session)
    try:
        quest = service.get_quest_for_user(quest_id, context.current_user)
        return build_experiment_gate(quest.id, service.list_stage_cards(quest.id))
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
