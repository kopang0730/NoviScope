from dataclasses import dataclass

from noviscope.core.json_types import JsonObject
from noviscope.core.stage_policy import PAPER_MEETING_WRITER_AGENT_ID
from noviscope.models.quest import StageCard


@dataclass(frozen=True, slots=True)
class PaperWriterExecutionPatch:
    fields: frozenset[str]
    evidence_payload: JsonObject | None
    input_payload: JsonObject | None
    output_payload: JsonObject | None
    summary: str | None


def paper_writer_execution_content_changed(
    stage: StageCard,
    patch: PaperWriterExecutionPatch,
) -> bool:
    if stage.agent_id != PAPER_MEETING_WRITER_AGENT_ID:
        return False
    return (
        "evidence_payload" in patch.fields
        and patch.evidence_payload != stage.evidence_payload
    ) or (
        "input_payload" in patch.fields and patch.input_payload != stage.input_payload
    ) or (
        "output_payload" in patch.fields and patch.output_payload != stage.output_payload
    ) or (
        "summary" in patch.fields and patch.summary != stage.summary
    )
