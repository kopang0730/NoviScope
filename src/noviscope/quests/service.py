from sqlmodel import Session, select

from noviscope.models.common import utc_now
from noviscope.models.quest import Quest, QuestStatus, StageCard, StageStatus

ALLOWED_STAGE_TRANSITIONS: dict[StageStatus, set[StageStatus]] = {
    StageStatus.PENDING: {StageStatus.RUNNING, StageStatus.BLOCKED},
    StageStatus.RUNNING: {StageStatus.COMPLETE, StageStatus.BLOCKED},
    StageStatus.BLOCKED: {StageStatus.PENDING, StageStatus.RUNNING},
    StageStatus.COMPLETE: set(),
}


class QuestService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create_quest(self, *, title: str, initial_direction: str) -> Quest:
        quest = Quest(title=title, initial_direction=initial_direction)
        stage = StageCard(
            quest_id=quest.id,
            agent_id="demand_validator",
            title="Demand validation",
            status=StageStatus.PENDING,
            summary="Validate real-world demand before literature and experiment stages.",
        )
        self.session.add(quest)
        self.session.add(stage)
        self.session.commit()
        self.session.refresh(quest)
        return quest

    def list_stage_cards(self, quest_id: str) -> list[StageCard]:
        statement = select(StageCard).where(StageCard.quest_id == quest_id)
        return list(self.session.exec(statement).all())

    def get_stage_card(self, stage_id: str) -> StageCard:
        stage = self.session.get(StageCard, stage_id)
        if stage is None:
            raise LookupError(f"Stage {stage_id} not found")
        return stage

    def update_stage_card(
        self,
        stage_id: str,
        *,
        status: StageStatus | None = None,
        summary: str | None = None,
        input_payload: dict[str, object] | None = None,
        output_payload: dict[str, object] | None = None,
        evidence_payload: dict[str, object] | None = None,
        human_approved: bool | None = None,
        review_notes: str | None = None,
    ) -> StageCard:
        stage = self.get_stage_card(stage_id)
        if status is not None:
            self._assert_transition_allowed(stage.status, status)
            stage.status = status
        if summary is not None:
            stage.summary = summary
        if input_payload is not None:
            stage.input_payload = input_payload
        if output_payload is not None:
            stage.output_payload = output_payload
        if evidence_payload is not None:
            stage.evidence_payload = evidence_payload
        if human_approved is not None:
            stage.human_approved = human_approved
        if review_notes is not None:
            stage.review_notes = review_notes
        stage.updated_at = utc_now().isoformat()
        self._sync_quest_after_stage_update(stage)
        self.session.add(stage)
        self.session.commit()
        self.session.refresh(stage)
        return stage

    def _assert_transition_allowed(self, current: StageStatus, target: StageStatus) -> None:
        if current == target:
            return
        if target not in ALLOWED_STAGE_TRANSITIONS[current]:
            raise ValueError(f"Cannot transition stage from {current.value} to {target.value}")

    def _sync_quest_after_stage_update(self, stage: StageCard) -> None:
        if stage.agent_id != "demand_validator" or stage.status != StageStatus.COMPLETE:
            return
        quest = self.session.get(Quest, stage.quest_id)
        if quest is None:
            return
        quest.status = (
            QuestStatus.IDEA_SELECTION if stage.human_approved else QuestStatus.DEMAND_REVIEW
        )
        quest.updated_at = utc_now().isoformat()
        self.session.add(quest)
