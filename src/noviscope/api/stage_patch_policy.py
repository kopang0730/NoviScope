from dataclasses import dataclass
from typing import Final

from pydantic import JsonValue

from noviscope.core.json_types import JsonObject
from noviscope.core.stage_policy import (
    CODE_RUNNER_AGENT_ID,
    EVIDENCE_AUDITOR_AGENT_ID,
    PAPER_MEETING_WRITER_AGENT_ID,
)
from noviscope.models.quest import StageCard, StageStatus

RUNNER_REVIEW_FIELDS: Final = frozenset({"human_approved", "review_notes"})
RUNNER_MANAGED_AGENT_IDS: Final = frozenset(
    {
        CODE_RUNNER_AGENT_ID,
        EVIDENCE_AUDITOR_AGENT_ID,
        PAPER_MEETING_WRITER_AGENT_ID,
    }
)


@dataclass(frozen=True, slots=True)
class StagePatchPolicyError(Exception):
    detail: str

    def __str__(self) -> str:
        return self.detail


@dataclass(frozen=True, slots=True)
class RunnerManagedStagePatch:
    fields: frozenset[str]
    evidence_payload: JsonObject | None
    input_payload: JsonObject | None
    output_payload: JsonObject | None
    summary: str | None
    target_status: StageStatus | None


def ensure_runner_managed_stage_patch_is_review_only(
    stage: StageCard,
    *,
    patch: RunnerManagedStagePatch,
) -> None:
    if stage.agent_id not in RUNNER_MANAGED_AGENT_IDS:
        return
    if runner_content_changed(stage, patch):
        raise StagePatchPolicyError(
            "Trusted execution fields can only be changed by the server-side stage runner."
        )
    if patch.fields & RUNNER_REVIEW_FIELDS and stage.status != StageStatus.COMPLETE:
        raise StagePatchPolicyError(
            "A runner-managed stage can only be reviewed after it completes."
        )
    if (
        "status" in patch.fields
        and patch.target_status is not None
        and patch.target_status != stage.status
    ):
        raise StagePatchPolicyError(
            "Trusted stage status can only be changed by the server-side stage runner."
        )


def runner_content_changed(stage: StageCard, patch: RunnerManagedStagePatch) -> bool:
    return (
        "evidence_payload" in patch.fields
        and not json_values_are_type_strict_equal(
            patch.evidence_payload,
            stage.evidence_payload,
        )
    ) or (
        "input_payload" in patch.fields
        and not json_values_are_type_strict_equal(
            patch.input_payload,
            stage.input_payload,
        )
    ) or (
        "output_payload" in patch.fields
        and not json_values_are_type_strict_equal(
            patch.output_payload,
            stage.output_payload,
        )
    ) or ("summary" in patch.fields and patch.summary != stage.summary)


def json_values_are_type_strict_equal(
    left: JsonValue | None,
    right: JsonValue | None,
) -> bool:
    if type(left) is not type(right):
        return False
    if isinstance(left, dict) and isinstance(right, dict):
        return left.keys() == right.keys() and all(
            json_values_are_type_strict_equal(left[key], right[key]) for key in left
        )
    if isinstance(left, list) and isinstance(right, list):
        return len(left) == len(right) and all(
            json_values_are_type_strict_equal(left_item, right_item)
            for left_item, right_item in zip(left, right, strict=True)
        )
    return left == right
