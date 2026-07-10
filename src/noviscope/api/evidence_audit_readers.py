from collections.abc import Sequence
from pathlib import PurePosixPath
from typing import Final, assert_never

from pydantic import JsonValue

from noviscope.agents.paper_meeting_writer_artifacts import PAPER_ARTIFACT_POLICY_VERSION
from noviscope.agents.paper_meeting_writer_results import (
    ExperimentResultStatus,
    experiment_result_status,
    verified_result_fact,
)
from noviscope.api.artifacts import MARKDOWN_ARTIFACT_KEYS
from noviscope.api.evidence_audit_contract import EVIDENCE_AUDIT_POLICY_VERSION
from noviscope.api.evidence_audit_snapshot import (
    EVIDENCE_AUDIT_FINGERPRINT_KEY,
    evidence_audit_stage_fingerprint,
)
from noviscope.api.evidence_ledger import collect_source_refs
from noviscope.core.json_types import JsonObject
from noviscope.core.stage_policy import CODE_RUNNER_AGENT_ID, EVIDENCE_AUDITOR_AGENT_ID
from noviscope.models.quest import StageCard, StageStatus

ACCEPTED_HUMAN_DEMAND_VERDICTS: Final = frozenset({"plausible", "verified"})
TRUSTED_RESULT_AGENT_IDS: Final = frozenset(
    {CODE_RUNNER_AGENT_ID, EVIDENCE_AUDITOR_AGENT_ID}
)
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
        for stage in trusted_result_stages(stages)
        for record in verified_experiment_result_records(stage)
    )


def trusted_result_stages(stages: Sequence[StageCard]) -> tuple[StageCard, ...]:
    return tuple(
        stage
        for stage in stages
        if (
            stage.agent_id in TRUSTED_RESULT_AGENT_IDS
            and stage.status == StageStatus.COMPLETE
            and stage.human_approved is True
        )
    )


def trusted_result_stage_with_invalid_entries(
    stages: Sequence[StageCard],
) -> StageCard | None:
    for stage in trusted_result_stages(stages):
        if result_collection_has_invalid_entries(
            stage.output_payload.get("experiment_results")
        ):
            return stage
    return None


def result_collection_has_invalid_entries(value: JsonValue | None) -> bool:
    match value:
        case None:
            return False
        case list() as items:
            return any(result_record_is_invalid(item) for item in items)
        case bool() | int() | float() | str() | dict():
            return True
        case unreachable:
            assert_never(unreachable)


def result_record_is_invalid(value: JsonValue) -> bool:
    match value:
        case dict() as record:
            match experiment_result_status(record):
                case ExperimentResultStatus.VERIFIED:
                    return verified_result_fact(record) is None
                case ExperimentResultStatus.NEEDS_REVIEW | ExperimentResultStatus.REJECTED:
                    return False
                case None:
                    return True
                case unreachable:
                    assert_never(unreachable)
        case None | bool() | int() | float() | str() | list():
            return True
        case unreachable:
            assert_never(unreachable)


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


def has_downloadable_paper_artifacts(stage: StageCard) -> bool:
    return all(
        isinstance(content := stage.output_payload.get(key.value), str) and bool(content.strip())
        for key in MARKDOWN_ARTIFACT_KEYS
    )


def has_trusted_paper_artifact_policy(stage: StageCard) -> bool:
    return (
        stage.evidence_payload.get("artifact_policy_version")
        == PAPER_ARTIFACT_POLICY_VERSION
    )


def evidence_auditor_is_approved(
    stage: StageCard | None,
    stages: Sequence[StageCard],
) -> bool:
    complete_stage = completed_stage(stage)
    if complete_stage is None or complete_stage.human_approved is not True:
        return False
    evidence = complete_stage.evidence_payload
    computed_fingerprint = evidence_audit_stage_fingerprint(stages)
    stored_fingerprint = evidence.get(EVIDENCE_AUDIT_FINGERPRINT_KEY)
    return (
        evidence.get("audit_policy_version") == EVIDENCE_AUDIT_POLICY_VERSION
        and evidence.get("claim_reference_alignment") is True
        and evidence.get("experiment_claim_alignment") is True
        and isinstance(computed_fingerprint, str)
        and isinstance(stored_fingerprint, str)
        and stored_fingerprint == computed_fingerprint
        and audit_artifact_uri_is_valid(evidence.get("audit_artifact_uri"))
    )


def audit_artifact_uri_is_valid(value: JsonValue | None) -> bool:
    match value:
        case str() as uri:
            normalized = uri.strip()
            if (
                not normalized.startswith("/")
                or normalized.startswith("//")
                or "\x00" in normalized
            ):
                return False
            path = PurePosixPath(normalized)
            return ".." not in path.parts and bool(path.name)
        case None | bool() | int() | float() | list() | dict():
            return False
        case unreachable:
            assert_never(unreachable)


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
