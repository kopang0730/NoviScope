from enum import StrEnum

from pydantic import BaseModel, ConfigDict


class ExperimentGateStatus(StrEnum):
    READY = "ready"
    NEEDS_REVIEW = "needs_review"
    BLOCKED = "blocked"


class ExperimentGateCheckStatus(StrEnum):
    PASS = "pass"
    NEEDS_REVIEW = "needs_review"
    BLOCKED = "blocked"


class ExperimentGateCheck(BaseModel):
    model_config = ConfigDict(frozen=True)

    key: str
    title: str
    status: ExperimentGateCheckStatus
    detail: str
    stage_id: str | None


class ExperimentGateResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    quest_id: str
    gate_status: ExperimentGateStatus
    ready_for_experiment: bool
    checks: list[ExperimentGateCheck]
    blocking_reasons: list[str]
