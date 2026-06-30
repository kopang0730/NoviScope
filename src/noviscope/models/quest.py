from enum import StrEnum
from typing import Any

from sqlalchemy import JSON, Column
from sqlalchemy import Enum as SAEnum
from sqlmodel import Field, SQLModel

from noviscope.models.common import new_id, utc_now


class QuestStatus(StrEnum):
    DRAFT = "draft"
    DEMAND_REVIEW = "demand_review"
    IDEA_SELECTION = "idea_selection"
    LIGHTWEIGHT_EXPERIMENT = "lightweight_experiment"
    FULL_EXPERIMENT = "full_experiment"
    WRITING = "writing"
    COMPLETE = "complete"
    ARCHIVED = "archived"


class StageStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    BLOCKED = "blocked"
    COMPLETE = "complete"


class Quest(SQLModel, table=True):
    id: str = Field(default_factory=lambda: new_id("quest"), primary_key=True)
    title: str
    initial_direction: str
    status: QuestStatus = Field(
        default=QuestStatus.DRAFT,
        index=True,
        sa_type=SAEnum(QuestStatus, values_callable=lambda enum: [item.value for item in enum]),
    )
    created_at: str = Field(default_factory=lambda: utc_now().isoformat())
    updated_at: str = Field(default_factory=lambda: utc_now().isoformat())


class StageCard(SQLModel, table=True):
    id: str = Field(default_factory=lambda: new_id("stage"), primary_key=True)
    quest_id: str = Field(index=True, foreign_key="quest.id")
    agent_id: str = Field(index=True)
    title: str
    status: StageStatus = Field(
        default=StageStatus.PENDING,
        sa_type=SAEnum(StageStatus, values_callable=lambda enum: [item.value for item in enum]),
    )
    summary: str = ""
    input_payload: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    output_payload: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    evidence_payload: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    human_approved: bool | None = None
    review_notes: str = ""
    created_at: str = Field(default_factory=lambda: utc_now().isoformat())
    updated_at: str = Field(default_factory=lambda: utc_now().isoformat())
