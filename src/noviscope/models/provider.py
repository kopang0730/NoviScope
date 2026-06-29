from enum import StrEnum

from sqlalchemy import Enum as SAEnum
from sqlmodel import Field, SQLModel

from noviscope.models.common import new_id, utc_now


class ProviderKind(StrEnum):
    OPENAI_COMPATIBLE = "openai_compatible"
    ANTHROPIC = "anthropic"
    CUSTOM = "custom"


class ModelProvider(SQLModel, table=True):
    id: str = Field(default_factory=lambda: new_id("provider"), primary_key=True)
    name: str = Field(index=True, unique=True)
    kind: ProviderKind = Field(
        sa_type=SAEnum(ProviderKind, values_callable=lambda enum: [item.value for item in enum])
    )
    base_url: str
    default_model: str
    api_key_ciphertext: str
    is_active: bool = True
    created_at: str = Field(default_factory=lambda: utc_now().isoformat())
