from dataclasses import dataclass
from typing import assert_never

from pydantic import JsonValue
from sqlmodel import Session

from noviscope.models.quest import StageCard, StageStatus
from noviscope.models.stage_transition import StageTransitionEvent


@dataclass(frozen=True, slots=True)
class StageTransitionRecord:
    stage: StageCard
    from_status: StageStatus
    to_status: StageStatus


def read_string_value(value: JsonValue | None) -> str:
    match value:
        case str() as text:
            return text.strip()
        case None | bool() | int() | float() | list() | dict():
            return ""
        case unreachable:
            assert_never(unreachable)


def stage_payload_value(stage: StageCard, key: str) -> str:
    evidence_value = read_string_value(stage.evidence_payload.get(key))
    if evidence_value:
        return evidence_value
    return read_string_value(stage.input_payload.get(key))


def build_stage_transition_event(record: StageTransitionRecord) -> StageTransitionEvent:
    stage = record.stage
    return StageTransitionEvent(
        agent_id=stage.agent_id,
        blocking_detail=stage_payload_value(stage, "blocking_detail"),
        blocking_reason=stage_payload_value(stage, "blocking_reason"),
        from_status=record.from_status,
        provider_id=stage_payload_value(stage, "provider_id"),
        provider_model=stage_payload_value(stage, "provider_model"),
        provider_name=stage_payload_value(stage, "provider_name"),
        quest_id=stage.quest_id,
        stage_id=stage.id,
        summary=stage.summary,
        to_status=record.to_status,
    )


def record_stage_transition(session: Session, record: StageTransitionRecord) -> None:
    if record.from_status == record.to_status:
        return
    session.add(build_stage_transition_event(record))
