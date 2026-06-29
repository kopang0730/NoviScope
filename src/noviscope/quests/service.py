from sqlmodel import Session, select

from noviscope.models.quest import Quest, StageCard, StageStatus


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
