from sqlalchemy import Enum as SAEnum
from sqlmodel import Field, SQLModel

from noviscope.models.common import new_id, utc_now
from noviscope.models.quest import StageStatus


class StageTransitionEvent(SQLModel, table=True):
    id: str = Field(default_factory=lambda: new_id("stage_event"), primary_key=True)
    quest_id: str = Field(index=True, foreign_key="quest.id")
    stage_id: str = Field(index=True, foreign_key="stagecard.id")
    agent_id: str = Field(index=True)
    from_status: StageStatus | None = Field(
        default=None,
        sa_type=SAEnum(StageStatus, values_callable=lambda enum: [item.value for item in enum]),
    )
    to_status: StageStatus = Field(
        sa_type=SAEnum(StageStatus, values_callable=lambda enum: [item.value for item in enum]),
    )
    provider_id: str = ""
    provider_model: str = ""
    provider_name: str = ""
    blocking_reason: str = ""
    blocking_detail: str = ""
    summary: str = ""
    created_at: str = Field(default_factory=lambda: utc_now().isoformat(), index=True)
