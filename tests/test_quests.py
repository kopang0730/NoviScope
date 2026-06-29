import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from noviscope.db.session import create_db_engine, create_schema
from noviscope.models.provider import ModelProvider, ProviderKind
from noviscope.models.quest import Quest, QuestStatus, StageCard, StageStatus
from noviscope.quests.service import QuestService


def test_provider_and_quest_persist(db_session: Session):
    provider = ModelProvider(
        name="primary-deepseek",
        kind=ProviderKind.OPENAI_COMPATIBLE,
        base_url="https://api.deepseek.com",
        default_model="deepseek-chat",
        api_key_ciphertext="encrypted-value",
    )
    quest = Quest(title="AI+Sports Badminton", initial_direction="AI+体育，羽毛球")
    stage = StageCard(
        quest_id=quest.id,
        agent_id="demand_validator",
        title="Demand validation",
        status=StageStatus.PENDING,
    )
    db_session.add(provider)
    db_session.add(quest)
    db_session.add(stage)
    db_session.commit()

    saved_quest = db_session.exec(select(Quest)).one()
    saved_stage = db_session.exec(select(StageCard)).one()
    saved_provider = db_session.exec(select(ModelProvider)).one()

    assert saved_quest.status == QuestStatus.DRAFT
    assert saved_stage.agent_id == "demand_validator"
    assert saved_provider.kind == ProviderKind.OPENAI_COMPATIBLE
    assert (
        db_session.execute(text("SELECT kind FROM modelprovider")).scalar_one()
        == "openai_compatible"
    )
    assert db_session.execute(text("SELECT status FROM quest")).scalar_one() == "draft"
    assert db_session.execute(text("SELECT status FROM stagecard")).scalar_one() == "pending"


def test_create_quest_adds_demand_validation_stage(db_session: Session):
    service = QuestService(db_session)

    quest = service.create_quest(
        title="AI+Sports Badminton",
        initial_direction="AI+体育，偏羽毛球相关",
    )

    stages = service.list_stage_cards(quest.id)

    assert quest.status == QuestStatus.DRAFT
    assert len(stages) == 1
    assert stages[0].agent_id == "demand_validator"
    assert stages[0].title == "Demand validation"


def test_stage_card_requires_existing_quest(tmp_path):
    engine = create_db_engine(f"sqlite:///{tmp_path / 'foreign-keys.db'}")
    create_schema(engine)

    with Session(engine) as session:
        session.add(
            StageCard(
                quest_id="quest_missing",
                agent_id="demand_validator",
                title="Demand validation",
            )
        )

        with pytest.raises(IntegrityError):
            session.commit()
