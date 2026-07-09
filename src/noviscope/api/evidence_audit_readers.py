from collections.abc import Sequence
from math import isfinite
from typing import Final, assert_never

from pydantic import JsonValue

from noviscope.api.artifacts import MARKDOWN_ARTIFACT_KEYS
from noviscope.api.evidence_ledger import collect_source_refs
from noviscope.core.json_types import JsonObject
from noviscope.models.quest import StageCard, StageStatus

ACCEPTED_HUMAN_DEMAND_VERDICTS: Final = frozenset({"plausible", "verified"})
TRUSTED_RESULT_AGENT_IDS: Final = frozenset({"code_runner", "evidence_auditor"})
VERIFIED_RESULT_FACT_PREFIX: Final = "Verified experiment result:"


def completed_stage(stage: StageCard | None) -> StageCard | None:
    if stage is None:
        return None
    match stage.status:
        case StageStatus.COMPLETE:
            return stage
        case StageStatus.PENDING | StageStatus.RUNNING | StageStatus.BLOCKED:
            return None
        case unreachable:
            assert_never(unreachable)


def stage_is_complete(stage: StageCard | None) -> bool:
    return completed_stage(stage) is not None


def find_stage(stages: Sequence[StageCard], agent_id: str) -> StageCard | None:
    for stage in stages:
        if stage.agent_id == agent_id:
            return stage
    return None


def read_string_refs(value: JsonValue | None) -> tuple[str, ...]:
    match value:
        case str() as text:
            stripped_text = text.strip()
            return (stripped_text,) if stripped_text else ()
        case list() as values:
            refs: list[str] = []
            for item in values:
                refs.extend(read_string_refs(item))
            return tuple(refs)
        case None | bool() | int() | float() | dict():
            return ()
        case unreachable:
            assert_never(unreachable)


def read_payload_refs(payload: JsonObject, key: str) -> tuple[str, ...]:
    return read_string_refs(payload.get(key))


def has_recorded_human_demand_evidence(stage: StageCard) -> bool:
    verdict = stage.evidence_payload.get("human_demand_verdict")
    if not isinstance(verdict, str) or verdict not in ACCEPTED_HUMAN_DEMAND_VERDICTS:
        return False
    return bool(read_payload_refs(stage.evidence_payload, "human_demand_sources"))


def verified_experiment_result_records(stage: StageCard) -> tuple[JsonObject, ...]:
    results = stage.output_payload.get("experiment_results")
    match results:
        case list() as items:
            return tuple(
                item
                for item in items
                if isinstance(item, dict) and json_value_is_verified_result(item)
            )
        case None | bool() | int() | float() | str() | dict():
            return ()
        case unreachable:
            assert_never(unreachable)


def trusted_verified_experiment_result_records(
    stages: Sequence[StageCard],
) -> tuple[JsonObject, ...]:
    return tuple(
        record
        for stage in stages
        if (
            stage.agent_id in TRUSTED_RESULT_AGENT_IDS
            and stage.status == StageStatus.COMPLETE
            and stage.human_approved is True
        )
        for record in verified_experiment_result_records(stage)
    )


def json_value_is_verified_result(value: JsonValue) -> bool:
    match value:
        case dict() as item:
            return (
                item.get("result_status") == "verified"
                and verified_result_fact(item) is not None
            )
        case None | bool() | int() | float() | str() | list():
            return False
        case unreachable:
            assert_never(unreachable)


def is_finite_number(value: JsonValue | None) -> bool:
    match value:
        case bool() | None | str() | list() | dict():
            return False
        case int():
            return True
        case float() as number:
            return isfinite(number)
        case unreachable:
            assert_never(unreachable)


def has_downloadable_paper_artifacts(stage: StageCard) -> bool:
    return all(
        isinstance(content := stage.output_payload.get(key.value), str) and bool(content.strip())
        for key in MARKDOWN_ARTIFACT_KEYS
    )


def paper_results_are_aligned(
    paper_stage: StageCard,
    verified_results: Sequence[JsonObject],
) -> bool:
    no_results = read_payload_refs(
        paper_stage.output_payload,
        "experiment_results_not_available",
    )
    if no_results:
        return False
    expected_facts = frozenset(
        fact
        for record in verified_results
        if (fact := verified_result_fact(record)) is not None
    )
    if not expected_facts:
        return False
    verified_facts = frozenset(
        read_payload_refs(paper_stage.output_payload, "verified_facts")
    )
    if verified_facts != expected_facts:
        return False
    return all(
        artifact_verified_facts(str(paper_stage.output_payload[key.value])) == expected_facts
        for key in MARKDOWN_ARTIFACT_KEYS
    )


def verified_result_fact(record: JsonObject) -> str | None:
    metric_name = read_single_string(record.get("metric_name"))
    run_id = read_single_string(record.get("run_id"))
    artifact_uri = read_single_string(record.get("artifact_uri"))
    metric_unit_valid, metric_unit = read_optional_single_string(record.get("metric_unit"))
    dataset_name_valid, dataset_name = read_optional_single_string(
        record.get("dataset_name")
    )
    baseline_name_valid, baseline_name = read_optional_single_string(
        record.get("baseline_name")
    )
    metric_value = record.get("metric_value")
    if (
        metric_name is None
        or run_id is None
        or artifact_uri is None
        or not metric_unit_valid
        or not dataset_name_valid
        or not baseline_name_valid
        or not is_finite_number(metric_value)
    ):
        return None
    measurement = f"{metric_value}{metric_unit}"
    dataset_context = f" on {dataset_name}" if dataset_name else ""
    baseline_context = f" using {baseline_name}" if baseline_name else ""
    return (
        f"{VERIFIED_RESULT_FACT_PREFIX} {metric_name} = {measurement}"
        f"{dataset_context}{baseline_context} "
        f"(run {run_id}; artifact {artifact_uri})."
    )


def read_single_string(value: JsonValue | None) -> str | None:
    if not isinstance(value, str):
        return None
    stripped_value = value.strip()
    return stripped_value or None


def read_optional_single_string(value: JsonValue | None) -> tuple[bool, str]:
    if value is None:
        return True, ""
    if not isinstance(value, str):
        return False, ""
    return True, value.strip()


def artifact_verified_facts(markdown: str) -> frozenset[str]:
    facts: set[str] = set()
    for line in markdown.splitlines():
        normalized = line.strip().removeprefix("- ").strip()
        marker_index = normalized.find(VERIFIED_RESULT_FACT_PREFIX)
        if marker_index >= 0:
            facts.add(normalized[marker_index:])
    return frozenset(facts)


def count_evidence_sources(stages: Sequence[StageCard]) -> int:
    refs = tuple(ref for stage in stages for ref in collect_source_refs(stage))
    return len(tuple(dict.fromkeys(refs)))
