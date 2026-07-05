from enum import StrEnum

from sqlalchemy import Enum as SAEnum
from sqlmodel import Field, Relationship, SQLModel

from noviscope.models.common import new_id, utc_now


class UserRole(StrEnum):
    ADMIN = "admin"
    MEMBER = "member"


class InviteStatus(StrEnum):
    ACTIVE = "active"
    DISABLED = "disabled"
    EXHAUSTED = "exhausted"


class User(SQLModel, table=True):
    id: str = Field(default_factory=lambda: new_id("user"), primary_key=True)
    email: str = Field(index=True, unique=True)
    display_name: str
    password_hash: str
    role: UserRole = Field(
        default=UserRole.MEMBER,
        sa_type=SAEnum(UserRole, values_callable=lambda enum: [item.value for item in enum]),
    )
    is_active: bool = True
    created_at: str = Field(default_factory=lambda: utc_now().isoformat())
    updated_at: str = Field(default_factory=lambda: utc_now().isoformat())
    invite_codes: list["InviteCode"] = Relationship(back_populates="created_by_user")


class InviteCode(SQLModel, table=True):
    id: str = Field(default_factory=lambda: new_id("invite"), primary_key=True)
    code: str = Field(index=True, unique=True)
    status: InviteStatus = Field(
        default=InviteStatus.ACTIVE,
        sa_type=SAEnum(InviteStatus, values_callable=lambda enum: [item.value for item in enum]),
    )
    created_by_user_id: str | None = Field(default=None, foreign_key="user.id")
    max_uses: int = 1
    used_count: int = 0
    expires_at: str | None = None
    created_at: str = Field(default_factory=lambda: utc_now().isoformat())
    updated_at: str = Field(default_factory=lambda: utc_now().isoformat())
    created_by_user: User | None = Relationship(back_populates="invite_codes")
