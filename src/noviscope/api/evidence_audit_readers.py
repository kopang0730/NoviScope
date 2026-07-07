from collections.abc import Sequence
from typing import assert_never

from pydantic import JsonValue

from noviscope.api.evidence_ledger import collect_source_refs
from noviscope.core.json_types import JsonObject
from noviscope.models.quest import StageCard, StageStatus


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


def has_selected_idea(stage: StageCard) -> bool:
    evidence_selected = read_payload_refs(stage.evidence_payload, "human_selected_idea_ids")
    output_selected = read_payload_refs(stage.output_payload, "selected_idea_ids")
    return bool(evidence_selected or output_selected)


def has_verified_experiment_result(stage: StageCard) -> bool:
    results = stage.output_payload.get("experiment_results")
    match results:
        case list() as items:
            return any(json_value_is_verified_result(item) for item in items)
        case None | bool() | int() | float() | str() | dict():
            return False
        case unreachable:
            assert_never(unreachable)


def json_value_is_verified_result(value: JsonValue) -> bool:
    match value:
        case dict() as item:
            return (
                item.get("result_status") == "verified"
                and bool(read_string_refs(item.get("artifact_uri")))
                and bool(read_string_refs(item.get("metric_name")))
            )
        case None | bool() | int() | float() | str() | list():
            return False
        case unreachable:
            assert_never(unreachable)


def count_evidence_sources(stages: Sequence[StageCard]) -> int:
    refs = tuple(ref for stage in stages for ref in collect_source_refs(stage))
    return len(tuple(dict.fromkeys(refs)))
