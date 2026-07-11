from sqlmodel import Session, create_engine

from noviscope.core.json_types import JsonObject
from noviscope.models.quest import StageStatus
from noviscope.quests.service import QuestService


def complete_stage_in_database(
    database_url: str,
    stage_id: str,
    *,
    output_payload: JsonObject,
    evidence_payload: JsonObject | None = None,
    human_approved: bool | None = None,
    review_notes: str | None = None,
    summary: str = "Completed by a server-side test fixture.",
) -> None:
    engine = create_engine(database_url)
    try:
        with Session(engine) as session:
            service = QuestService(session)
            service.update_stage_card(stage_id, status=StageStatus.RUNNING)
            service.update_stage_card(
                stage_id,
                evidence_payload=evidence_payload,
                human_approved=human_approved,
                human_approved_set=human_approved is not None,
                output_payload=output_payload,
                review_notes=review_notes,
                status=StageStatus.COMPLETE,
                summary=summary,
            )
    finally:
        engine.dispose()
