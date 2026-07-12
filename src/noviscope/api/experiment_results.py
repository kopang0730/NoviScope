from enum import StrEnum
from typing import Annotated, ClassVar, assert_never

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, JsonValue, StringConstraints
from sqlmodel import Session

from noviscope.api.dependencies import get_session
from noviscope.auth.dependencies import get_current_user
from noviscope.core.json_types import JsonObject
from noviscope.core.stage_policy import EXPERIMENT_PLANNER_AGENT_ID
from noviscope.models.common import utc_now
from noviscope.models.quest import StageCard, StageStatus
from noviscope.models.user import User
from noviscope.quests.service import QuestService

router = APIRouter()

NonEmptyStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class ExperimentResultStatus(StrEnum):
    VERIFIED = "verified"
    NEEDS_REVIEW = "needs_review"
    REJECTED = "rejected"


class ExperimentResultsError(Exception):
    def __init__(self, detail: str) -> None:
        self.detail = detail
        super().__init__(detail)


class ExperimentResultsConflict(Exception):
    def __init__(self, detail: str) -> None:
        self.detail = detail
        super().__init__(detail)


class ExperimentResultRecordRequest(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    artifact_uri: NonEmptyStr
    baseline_name: NonEmptyStr
    dataset_name: NonEmptyStr
    higher_is_better: bool | None = None
    metric_name: NonEmptyStr
    metric_unit: NonEmptyStr
    metric_value: float
    provenance_note: NonEmptyStr
    result_status: ExperimentResultStatus
    review_notes: str = ""
    run_id: NonEmptyStr


class ExperimentResultRecordResponse(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    artifact_uri: str
    baseline_name: str
    dataset_name: str
    higher_is_better: bool | None
    metric_name: str
    metric_unit: str
    metric_value: float
    provenance_note: str
    recorded_at: str
    result_status: ExperimentResultStatus
    review_notes: str
    run_id: str


class ExperimentResultsResponse(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    agent_id: str
    experiment_results_available: bool
    latest_result: ExperimentResultRecordResponse
    needs_review_count: int
    quest_id: str
    recorded_result_count: int
    stage_id: str
    stage_summary: str
    verified_result_count: int


@router.post("/stages/{stage_id}/experiment-results", response_model=ExperimentResultsResponse)
def record_experiment_result(
    stage_id: str,
    request: ExperimentResultRecordRequest,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> ExperimentResultsResponse:
    service = QuestService(session)
    try:
        stage = service.get_stage_card_for_user(stage_id, current_user)
        ensure_experiment_result_stage(stage)
        ensure_verified_result_has_review(request)
        record = experiment_result_record(request)
        existing_records = experiment_result_records(
            stage.output_payload.get("experiment_results")
        )
        records = [*existing_records, record]
        updated_stage = service.update_stage_card(
            stage_id,
            evidence_payload=experiment_result_evidence(stage.evidence_payload, records),
            output_payload=experiment_result_output(stage.output_payload, records),
            review_notes=request.review_notes or stage.review_notes,
            summary=experiment_result_summary(records),
        )
        return experiment_results_response(updated_stage, record)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except ExperimentResultsConflict as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=exc.detail) from exc
    except ExperimentResultsError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.detail) from exc


def ensure_experiment_result_stage(stage: StageCard) -> None:
    if stage.agent_id != EXPERIMENT_PLANNER_AGENT_ID:
        raise ExperimentResultsError(
            "Experiment results can only be recorded on Experiment Planner stages."
        )
    if stage.status != StageStatus.COMPLETE or stage.human_approved is not True:
        raise ExperimentResultsConflict(
            "Approve a completed Experiment Planner stage before recording experiment results."
        )


def ensure_verified_result_has_review(request: ExperimentResultRecordRequest) -> None:
    match request.result_status:
        case ExperimentResultStatus.VERIFIED:
            if not request.review_notes.strip():
                raise ExperimentResultsError(
                    "Verified experiment results require human review notes."
                )
        case ExperimentResultStatus.NEEDS_REVIEW | ExperimentResultStatus.REJECTED:
            return
        case unreachable:
            assert_never(unreachable)


def experiment_result_record(request: ExperimentResultRecordRequest) -> JsonObject:
    return {
        "artifact_uri": request.artifact_uri,
        "baseline_name": request.baseline_name,
        "dataset_name": request.dataset_name,
        "higher_is_better": request.higher_is_better,
        "metric_name": request.metric_name,
        "metric_unit": request.metric_unit,
        "metric_value": request.metric_value,
        "provenance_note": request.provenance_note,
        "recorded_at": utc_now().isoformat(),
        "result_status": request.result_status.value,
        "review_notes": request.review_notes,
        "run_id": request.run_id,
    }


def experiment_result_records(value: JsonValue | None) -> list[JsonObject]:
    match value:
        case list() as items:
            records: list[JsonObject] = []
            for item in items:
                match item:
                    case dict() as record:
                        records.append(record)
                    case None | bool() | int() | float() | str() | list():
                        continue
                    case unreachable:
                        assert_never(unreachable)
            return records
        case None | bool() | int() | float() | str() | dict():
            return []
        case unreachable:
            assert_never(unreachable)


def experiment_result_status(record: JsonObject) -> ExperimentResultStatus | None:
    match record.get("result_status"):
        case "verified":
            return ExperimentResultStatus.VERIFIED
        case "needs_review":
            return ExperimentResultStatus.NEEDS_REVIEW
        case "rejected":
            return ExperimentResultStatus.REJECTED
        case None | bool() | int() | float() | str() | list() | dict():
            return None
        case unreachable:
            assert_never(unreachable)


def verified_result_count(records: list[JsonObject]) -> int:
    return sum(
        1
        for record in records
        if experiment_result_status(record) == ExperimentResultStatus.VERIFIED
    )


def needs_review_count(records: list[JsonObject]) -> int:
    return sum(
        1
        for record in records
        if experiment_result_status(record) == ExperimentResultStatus.NEEDS_REVIEW
    )


def provenance_refs(records: list[JsonObject]) -> list[str]:
    refs: list[str] = []
    for record in records:
        match record.get("artifact_uri"):
            case str() as artifact_uri:
                refs.append(artifact_uri)
            case None | bool() | int() | float() | list() | dict():
                continue
            case unreachable:
                assert_never(unreachable)
    return refs


def experiment_result_evidence(
    existing_evidence: JsonObject,
    records: list[JsonObject],
) -> JsonObject:
    verified_count = verified_result_count(records)
    review_count = needs_review_count(records)
    return {
        **existing_evidence,
        "experiment_result_count": len(records),
        "experiment_result_provenance_refs": provenance_refs(records),
        "experiment_results_require_review": review_count > 0,
        "verified_experiment_result_count": verified_count,
    }


def experiment_result_output(existing_output: JsonObject, records: list[JsonObject]) -> JsonObject:
    verified_count = verified_result_count(records)
    return {
        **existing_output,
        "experiment_results": records,
        "experiment_results_available": verified_count > 0,
        "verified_experiment_result_count": verified_count,
    }


def experiment_result_summary(records: list[JsonObject]) -> str:
    verified_count = verified_result_count(records)
    review_count = needs_review_count(records)
    return (
        f"Experiment Planner has {len(records)} recorded result(s): "
        f"{verified_count} verified, {review_count} needing review."
    )


def experiment_results_response(
    stage: StageCard,
    latest_record: JsonObject,
) -> ExperimentResultsResponse:
    records = experiment_result_records(stage.output_payload.get("experiment_results"))
    return ExperimentResultsResponse(
        agent_id=stage.agent_id,
        experiment_results_available=verified_result_count(records) > 0,
        latest_result=ExperimentResultRecordResponse.model_validate(latest_record),
        needs_review_count=needs_review_count(records),
        quest_id=stage.quest_id,
        recorded_result_count=len(records),
        stage_id=stage.id,
        stage_summary=stage.summary,
        verified_result_count=verified_result_count(records),
    )
