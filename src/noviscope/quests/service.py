from dataclasses import dataclass
from datetime import timedelta

from sqlmodel import Session, select

from noviscope.agents.literature_scout import LITERATURE_SCOUT_AGENT_ID
from noviscope.core.json_types import JsonObject
from noviscope.core.stage_policy import (
    DEMAND_VALIDATOR_AGENT_ID,
    EXPERIMENT_PLANNER_AGENT_ID,
    IDEA_GENERATOR_AGENT_ID,
    PAPER_MEETING_WRITER_AGENT_ID,
)
from noviscope.models.common import utc_now
from noviscope.models.quest import Quest, QuestStatus, StageCard, StageStatus
from noviscope.models.user import User, UserRole
from noviscope.quests.intake import (
    QuestCreateSpec,
    QuestIntakeUpdateSpec,
    quest_intake_payload,
    resolve_initial_direction,
    resolve_updated_initial_direction,
)

ALLOWED_STAGE_TRANSITIONS: dict[StageStatus, set[StageStatus]] = {
    StageStatus.PENDING: {StageStatus.RUNNING, StageStatus.BLOCKED},
    StageStatus.RUNNING: {StageStatus.COMPLETE, StageStatus.BLOCKED},
    StageStatus.BLOCKED: {StageStatus.PENDING, StageStatus.RUNNING},
    StageStatus.COMPLETE: set(),
}


@dataclass(frozen=True, slots=True)
class StageTransitionError(ValueError):
    current: StageStatus
    target: StageStatus

    def __str__(self) -> str:
        return f"Cannot transition stage from {self.current.value} to {self.target.value}"


class QuestService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create_quest(
        self,
        *,
        title: str,
        initial_direction: str,
        owner_user_id: str | None = None,
    ) -> Quest:
        return self.create_quest_from_intake(
            QuestCreateSpec(
                title=title,
                initial_direction=initial_direction,
                owner_user_id=owner_user_id,
            )
        )

    def create_quest_from_intake(self, spec: QuestCreateSpec) -> Quest:
        quest = Quest(
            title=spec.title,
            initial_direction=resolve_initial_direction(spec),
            intake_payload=quest_intake_payload(spec.intake),
            owner_user_id=spec.owner_user_id,
        )
        stage_created_at = utc_now()
        demand_stage = StageCard(
            quest_id=quest.id,
            agent_id=DEMAND_VALIDATOR_AGENT_ID,
            created_at=stage_created_at.isoformat(),
            title="Demand validation",
            status=StageStatus.PENDING,
            summary="Validate real-world demand before literature and experiment stages.",
        )
        literature_stage = StageCard(
            quest_id=quest.id,
            agent_id=LITERATURE_SCOUT_AGENT_ID,
            created_at=(stage_created_at + timedelta(microseconds=1)).isoformat(),
            title="Literature scout",
            status=StageStatus.PENDING,
            summary="Find recent papers from OpenAlex after demand validation is complete.",
        )
        idea_stage = StageCard(
            quest_id=quest.id,
            agent_id=IDEA_GENERATOR_AGENT_ID,
            created_at=(stage_created_at + timedelta(microseconds=2)).isoformat(),
            title="Gap & hypothesis generator",
            status=StageStatus.PENDING,
            summary=(
                "Generate evidence-linked research gaps and hypotheses after literature scouting."
            ),
        )
        experiment_stage = StageCard(
            quest_id=quest.id,
            agent_id=EXPERIMENT_PLANNER_AGENT_ID,
            created_at=(stage_created_at + timedelta(microseconds=3)).isoformat(),
            title="Experiment planner",
            status=StageStatus.PENDING,
            summary=(
                "Design datasets, baselines, metrics, ablations, and the first runnable "
                "script plan after an idea is selected."
            ),
        )
        paper_stage = StageCard(
            quest_id=quest.id,
            agent_id=PAPER_MEETING_WRITER_AGENT_ID,
            created_at=(stage_created_at + timedelta(microseconds=4)).isoformat(),
            title="Paper & meeting writer",
            status=StageStatus.PENDING,
            summary=(
                "Generate traceable research briefs, a meeting outline, and an IEEE-style "
                "paper skeleton after experiment planning."
            ),
        )
        self.session.add(quest)
        self.session.add(demand_stage)
        self.session.add(literature_stage)
        self.session.add(idea_stage)
        self.session.add(experiment_stage)
        self.session.add(paper_stage)
        self.session.commit()
        self.session.refresh(quest)
        return quest

    def update_quest_intake(self, spec: QuestIntakeUpdateSpec) -> Quest:
        quest = self.session.get(Quest, spec.quest_id)
        if quest is None:
            raise LookupError(f"Quest {spec.quest_id} not found")
        quest.intake_payload = quest_intake_payload(spec.intake)
        quest.initial_direction = resolve_updated_initial_direction(
            quest.initial_direction,
            spec,
        )
        quest.updated_at = utc_now().isoformat()
        self.session.add(quest)
        self.session.commit()
        self.session.refresh(quest)
        return quest

    def list_quests_for_user(self, user: User) -> list[Quest]:
        statement = select(Quest)
        if user.role != UserRole.ADMIN:
            statement = statement.where(Quest.owner_user_id == user.id)
        statement = statement.order_by(Quest.updated_at)
        return list(self.session.exec(statement).all())

    def get_quest_for_user(self, quest_id: str, user: User) -> Quest:
        quest = self.session.get(Quest, quest_id)
        if quest is None:
            raise LookupError(f"Quest {quest_id} not found")
        if user.role != UserRole.ADMIN and quest.owner_user_id != user.id:
            raise PermissionError(f"Quest {quest_id} is not accessible")
        return quest

    def list_stage_cards(self, quest_id: str) -> list[StageCard]:
        statement = (
            select(StageCard)
            .where(StageCard.quest_id == quest_id)
            .order_by(StageCard.created_at, StageCard.id)
        )
        return list(self.session.exec(statement).all())

    def get_stage_card(self, stage_id: str) -> StageCard:
        stage = self.session.get(StageCard, stage_id)
        if stage is None:
            raise LookupError(f"Stage {stage_id} not found")
        return stage

    def get_stage_card_for_user(self, stage_id: str, user: User) -> StageCard:
        stage = self.get_stage_card(stage_id)
        self.get_quest_for_user(stage.quest_id, user)
        return stage

    def update_stage_card(
        self,
        stage_id: str,
        *,
        status: StageStatus | None = None,
        summary: str | None = None,
        input_payload: JsonObject | None = None,
        output_payload: JsonObject | None = None,
        evidence_payload: JsonObject | None = None,
        human_approved: bool | None = None,
        human_approved_set: bool = False,
        review_notes: str | None = None,
    ) -> StageCard:
        stage = self.get_stage_card(stage_id)
        if status is not None:
            self._assert_transition_allowed(stage, status)
            stage.status = status
        if summary is not None:
            stage.summary = summary
        if input_payload is not None:
            stage.input_payload = input_payload
        if output_payload is not None:
            stage.output_payload = output_payload
        if evidence_payload is not None:
            stage.evidence_payload = evidence_payload
        if human_approved is not None or human_approved_set:
            stage.human_approved = human_approved
        if review_notes is not None:
            stage.review_notes = review_notes
        stage.updated_at = utc_now().isoformat()
        self._sync_quest_after_stage_update(stage)
        self.session.add(stage)
        self.session.commit()
        self.session.refresh(stage)
        return stage

    def _assert_transition_allowed(self, stage: StageCard, target: StageStatus) -> None:
        current = stage.status
        if current == target:
            return
        if (
            current == StageStatus.COMPLETE
            and target == StageStatus.BLOCKED
            and stage.human_approved is False
        ):
            return
        if target not in ALLOWED_STAGE_TRANSITIONS[current]:
            raise StageTransitionError(current=current, target=target)

    def _sync_quest_after_stage_update(self, stage: StageCard) -> None:
        if stage.status != StageStatus.COMPLETE:
            return
        quest = self.session.get(Quest, stage.quest_id)
        if quest is None:
            return
        status_by_agent = {
            DEMAND_VALIDATOR_AGENT_ID: (
                QuestStatus.IDEA_SELECTION if stage.human_approved else QuestStatus.DEMAND_REVIEW
            ),
            IDEA_GENERATOR_AGENT_ID: (
                QuestStatus.LIGHTWEIGHT_EXPERIMENT
                if stage.human_approved
                else QuestStatus.IDEA_SELECTION
            ),
            EXPERIMENT_PLANNER_AGENT_ID: (
                QuestStatus.FULL_EXPERIMENT
                if stage.human_approved
                else QuestStatus.LIGHTWEIGHT_EXPERIMENT
            ),
            PAPER_MEETING_WRITER_AGENT_ID: (
                QuestStatus.WRITING if stage.human_approved else QuestStatus.FULL_EXPERIMENT
            ),
        }
        quest_status = status_by_agent.get(stage.agent_id)
        if quest_status is None:
            return
        quest.status = quest_status
        quest.updated_at = utc_now().isoformat()
        self.session.add(quest)
