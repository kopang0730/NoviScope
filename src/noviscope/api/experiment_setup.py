from typing import Annotated, Final

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, StringConstraints
from sqlmodel import Session

from noviscope.api.dependencies import get_session
from noviscope.api.routes import StageCardResponse, stage_response
from noviscope.auth.dependencies import get_current_user
from noviscope.core.json_types import JsonObject
from noviscope.core.stage_policy import EXPERIMENT_PLANNER_AGENT_ID
from noviscope.models.quest import StageCard, StageStatus
from noviscope.models.user import User
from noviscope.quests.service import QuestService

router = APIRouter()

NonEmptyStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
REQUIRED_INPUT_FIELDS: Final = ("data_path", "code_repository", "environment_notes")


class ExperimentSetupError(Exception):
    def __init__(self, detail: str) -> None:
        self.detail = detail
        super().__init__(detail)


class ExperimentSetupRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    data_path: NonEmptyStr
    code_repository: NonEmptyStr
    environment_notes: NonEmptyStr


@router.post("/stages/{stage_id}/experiment-setup", response_model=StageCardResponse)
def save_experiment_setup(
    stage_id: str,
    request: ExperimentSetupRequest,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> StageCardResponse:
    service = QuestService(session)
    try:
        stage = service.get_stage_card_for_user(stage_id, current_user)
        ensure_experiment_setup_stage(stage)
        updated_stage = service.update_stage_card(
            stage_id,
            evidence_payload=experiment_setup_evidence(),
            input_payload={**stage.input_payload, **experiment_setup_payload(request)},
            status=StageStatus.PENDING if stage.status == StageStatus.BLOCKED else None,
            summary="Experiment setup inputs are recorded for Experiment Planner.",
        )
        return stage_response(updated_stage)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except ExperimentSetupError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=exc.detail,
        ) from exc


def ensure_experiment_setup_stage(stage: StageCard) -> None:
    if stage.agent_id != EXPERIMENT_PLANNER_AGENT_ID:
        raise ExperimentSetupError("Experiment setup is only available for Experiment Planner.")
    if stage.status in {StageStatus.RUNNING, StageStatus.COMPLETE}:
        raise ExperimentSetupError(
            "Experiment setup cannot be changed while this stage is running or complete."
        )


def experiment_setup_payload(request: ExperimentSetupRequest) -> JsonObject:
    return {
        "code_repository": request.code_repository,
        "data_path": request.data_path,
        "environment_notes": request.environment_notes,
    }


def experiment_setup_evidence() -> JsonObject:
    return {
        "experiment_setup_recorded": True,
        "required_input_fields": list(REQUIRED_INPUT_FIELDS),
    }
