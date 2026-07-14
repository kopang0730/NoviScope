from dataclasses import dataclass
from typing import Annotated, Final, assert_never

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, StringConstraints
from sqlmodel import Session

from noviscope.agents.experiment_planner import read_experiment_setup_inputs
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


class ExperimentSetupStatusResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    stage_id: str
    agent_id: str
    status: StageStatus
    required_fields: list[str]
    missing_fields: list[str]
    is_complete: bool
    can_edit: bool
    blocking_reason: str
    data_path: str
    code_repository: str
    environment_notes: str


@dataclass(frozen=True, slots=True)
class ExperimentSetupValues:
    data_path: str
    code_repository: str
    environment_notes: str


@router.get(
    "/stages/{stage_id}/experiment-setup",
    response_model=ExperimentSetupStatusResponse,
)
def get_experiment_setup(
    stage_id: str,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> ExperimentSetupStatusResponse:
    service = QuestService(session)
    try:
        stage = service.get_stage_card_for_user(stage_id, current_user)
        ensure_experiment_setup_readable_stage(stage)
        return experiment_setup_status(stage)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except ExperimentSetupError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=exc.detail,
        ) from exc


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


def ensure_experiment_setup_readable_stage(stage: StageCard) -> None:
    if stage.agent_id != EXPERIMENT_PLANNER_AGENT_ID:
        raise ExperimentSetupError("Experiment setup is only available for Experiment Planner.")


def ensure_experiment_setup_stage(stage: StageCard) -> None:
    ensure_experiment_setup_readable_stage(stage)
    if not can_edit_experiment_setup(stage.status):
        raise ExperimentSetupError(
            "Experiment setup cannot be changed while this stage is running or complete."
        )


def experiment_setup_status(stage: StageCard) -> ExperimentSetupStatusResponse:
    values = experiment_setup_values(stage.input_payload)
    missing_fields = missing_experiment_setup_fields(values)
    return ExperimentSetupStatusResponse(
        stage_id=stage.id,
        agent_id=stage.agent_id,
        status=stage.status,
        required_fields=list(REQUIRED_INPUT_FIELDS),
        missing_fields=missing_fields,
        is_complete=not missing_fields,
        can_edit=can_edit_experiment_setup(stage.status),
        blocking_reason=experiment_setup_blocking_reason(stage.status, missing_fields),
        data_path=values.data_path,
        code_repository=values.code_repository,
        environment_notes=values.environment_notes,
    )


def experiment_setup_values(payload: JsonObject) -> ExperimentSetupValues:
    setup = read_experiment_setup_inputs(payload)
    return ExperimentSetupValues(
        data_path=f"{setup['data_path']}",
        code_repository=f"{setup['code_repository']}",
        environment_notes=f"{setup['environment_notes']}",
    )


def missing_experiment_setup_fields(values: ExperimentSetupValues) -> list[str]:
    missing_fields: list[str] = []
    if not values.data_path:
        missing_fields.append("data_path")
    if not values.code_repository:
        missing_fields.append("code_repository")
    if not values.environment_notes:
        missing_fields.append("environment_notes")
    return missing_fields


def can_edit_experiment_setup(stage_status: StageStatus) -> bool:
    match stage_status:
        case StageStatus.PENDING | StageStatus.BLOCKED:
            return True
        case StageStatus.RUNNING | StageStatus.COMPLETE:
            return False
        case unreachable:
            assert_never(unreachable)


def experiment_setup_blocking_reason(
    stage_status: StageStatus,
    missing_fields: list[str],
) -> str:
    if missing_fields:
        return (
            "Record data_path, code_repository, and environment_notes before running "
            "Experiment Planner."
        )
    if can_edit_experiment_setup(stage_status):
        return ""
    return "Experiment setup cannot be changed while this stage is running or complete."


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
