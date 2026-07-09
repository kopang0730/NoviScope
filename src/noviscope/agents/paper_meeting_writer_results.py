from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum
from math import isfinite
from typing import assert_never

from pydantic import JsonValue

from noviscope.core.json_types import JsonObject

NEEDS_REVIEW_WARNING = (
    "Some experiment result records require human review and were excluded from verified facts."
)
MAX_RESULT_ITEMS_FOR_PROMPT = 10


class ExperimentResultStatus(StrEnum):
    VERIFIED = "verified"
    NEEDS_REVIEW = "needs_review"
    REJECTED = "rejected"


@dataclass(frozen=True, slots=True)
class ExperimentResultsContext:
    verified_facts: list[str]
    human_review_required: list[str]
    verified_count: int
    needs_review_count: int

    @property
    def has_verified_results(self) -> bool:
        return self.verified_count > 0

    def as_prompt_payload(self) -> JsonObject:
        return {
            "needs_review_result_count": self.needs_review_count,
            "result_claim_policy": (
                "Only verified_result_facts may be written as completed experiment "
                "results. Results requiring review must stay in human_review_required."
            ),
            "results_requiring_review": self.human_review_required[:MAX_RESULT_ITEMS_FOR_PROMPT],
            "verified_result_count": self.verified_count,
            "verified_result_facts": self.verified_facts[:MAX_RESULT_ITEMS_FOR_PROMPT],
        }


def experiment_results_context(
    experiment_plan: JsonObject,
    verified_experiment_results: Sequence[JsonObject] = (),
) -> ExperimentResultsContext:
    verified_facts: list[str] = []
    human_review_required: list[str] = []
    for record in experiment_result_records(experiment_plan.get("experiment_results")):
        match experiment_result_status(record):
            case ExperimentResultStatus.VERIFIED | ExperimentResultStatus.NEEDS_REVIEW:
                human_review_required.append(needs_review_note(record))
            case ExperimentResultStatus.REJECTED | None:
                continue
            case unreachable:
                assert_never(unreachable)
    for record in verified_experiment_results:
        match experiment_result_status(record):
            case ExperimentResultStatus.VERIFIED:
                fact = verified_result_fact(record)
                if fact is not None:
                    verified_facts.append(fact)
                else:
                    human_review_required.append(needs_review_note(record))
            case ExperimentResultStatus.NEEDS_REVIEW:
                human_review_required.append(needs_review_note(record))
            case ExperimentResultStatus.REJECTED | None:
                continue
            case unreachable:
                assert_never(unreachable)
    return ExperimentResultsContext(
        human_review_required=human_review_required,
        needs_review_count=len(human_review_required),
        verified_count=len(verified_facts),
        verified_facts=verified_facts,
    )


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


def verified_result_fact(record: JsonObject) -> str | None:
    metric_name = string_field(record, "metric_name")
    metric_value = number_field(record, "metric_value")
    metric_unit = string_field(record, "metric_unit")
    dataset_name = string_field(record, "dataset_name")
    baseline_name = string_field(record, "baseline_name")
    run_id = string_field(record, "run_id")
    artifact_uri = string_field(record, "artifact_uri")
    if (
        metric_name is None
        or metric_value is None
        or metric_unit is None
        or dataset_name is None
        or baseline_name is None
        or run_id is None
        or artifact_uri is None
    ):
        return None
    return (
        f"Verified experiment result: {metric_name} = {metric_value}{metric_unit} "
        f"on {dataset_name} using {baseline_name} "
        f"(run {run_id}; artifact {artifact_uri})."
    )


def needs_review_note(record: JsonObject) -> str:
    metric_name = string_field(record, "metric_name") or "unknown metric"
    run_id = string_field(record, "run_id") or "unknown run"
    return (
        f"Experiment result run {run_id} for {metric_name} requires human review "
        "before paper claims."
    )


def string_field(record: JsonObject, key: str) -> str | None:
    match record.get(key):
        case str() as value:
            return value
        case None | bool() | int() | float() | list() | dict():
            return None
        case unreachable:
            assert_never(unreachable)


def number_field(record: JsonObject, key: str) -> int | float | None:
    match record.get(key):
        case bool() | None | str() | list() | dict():
            return None
        case int() as value:
            return value
        case float() as value:
            return value if isfinite(value) else None
        case unreachable:
            assert_never(unreachable)
