from sqlalchemy import text
from sqlmodel import Session, select

from noviscope.models.provider import ModelProvider, ProviderKind
from noviscope.models.quest import Quest, QuestStatus, StageCard, StageStatus


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
