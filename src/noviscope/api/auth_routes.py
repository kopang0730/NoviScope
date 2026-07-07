from datetime import UTC, datetime
from email.utils import parseaddr
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, Field, StringConstraints, field_validator
from sqlmodel import Session

from noviscope.api.dependencies import get_session
from noviscope.auth.dependencies import (
    clear_session_cookie,
    create_session_token,
    get_admin_or_dev_header,
    get_current_admin,
    get_current_user,
    set_session_cookie,
)
from noviscope.auth.service import AuthService, DuplicateResourceError
from noviscope.models.user import InviteCode, InviteStatus, User, UserRole

router = APIRouter()

NonEmptyStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
LoginPasswordStr = Annotated[str, StringConstraints(min_length=1)]
PasswordStr = Annotated[str, StringConstraints(min_length=8)]


class UserResponse(BaseModel):
    id: str
    email: str
    display_name: str
    role: UserRole
    is_active: bool
    created_at: str
    updated_at: str


class RegisterRequest(BaseModel):
    invite_code: NonEmptyStr
    email: NonEmptyStr
    display_name: NonEmptyStr
    password: PasswordStr

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        return normalize_email(value)

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Password must contain a non-whitespace character")
        return value


class LoginRequest(BaseModel):
    email: NonEmptyStr
    password: LoginPasswordStr

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        return normalize_email(value)


class InviteCreateRequest(BaseModel):
    code: NonEmptyStr
    max_uses: int = Field(default=1, ge=1)
    expires_at: datetime | None = None

    @field_validator("expires_at")
    @classmethod
    def validate_expires_at(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            raise ValueError("expires_at must include a timezone")
        return value.astimezone(UTC)


class InviteResponse(BaseModel):
    id: str
    code: str
    status: InviteStatus
    max_uses: int
    used_count: int
    expires_at: str | None
    created_at: str
    updated_at: str


class InvitesResponse(BaseModel):
    invites: list[InviteResponse]


def normalize_email(value: str) -> str:
    email = value.strip()
    parsed_name, parsed_email = parseaddr(email)
    if parsed_name or parsed_email != email or "@" not in email:
        raise ValueError("Invalid email")
    local_part, domain = email.rsplit("@", 1)
    if not local_part or "." not in domain or domain.startswith(".") or domain.endswith("."):
        raise ValueError("Invalid email")
    return email.lower()


def user_response(user: User) -> UserResponse:
    return UserResponse.model_validate(user, from_attributes=True)


def invite_response(invite: InviteCode) -> InviteResponse:
    return InviteResponse.model_validate(invite, from_attributes=True)


@router.post("/auth/register", status_code=status.HTTP_201_CREATED, response_model=UserResponse)
def register_user(
    request: RegisterRequest,
    session: Annotated[Session, Depends(get_session)],
) -> UserResponse:
    service = AuthService(session)
    try:
        user = service.register_member(
            invite_code=request.invite_code,
            email=request.email,
            display_name=request.display_name,
            password=request.password,
        )
    except DuplicateResourceError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return user_response(user)


@router.post("/auth/login", response_model=UserResponse)
def login_user(
    request: LoginRequest,
    response: Response,
    session: Annotated[Session, Depends(get_session)],
) -> UserResponse:
    service = AuthService(session)
    try:
        user = service.authenticate(email=request.email, password=request.password)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    set_session_cookie(response, create_session_token(user))
    return user_response(user)


@router.post("/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout_user(response: Response) -> None:
    clear_session_cookie(response)


@router.get("/auth/me", response_model=UserResponse)
def get_me(current_user: Annotated[User, Depends(get_current_user)]) -> UserResponse:
    return user_response(current_user)


@router.post("/admin/invites", status_code=status.HTTP_201_CREATED, response_model=InviteResponse)
def create_invite(
    request: InviteCreateRequest,
    session: Annotated[Session, Depends(get_session)],
    current_admin: Annotated[User | None, Depends(get_admin_or_dev_header)],
) -> InviteResponse:
    admin_id = current_admin.id if current_admin is not None else None
    try:
        invite = AuthService(session).create_invite(
            code=request.code,
            created_by_user_id=admin_id,
            max_uses=request.max_uses,
            expires_at=request.expires_at.isoformat() if request.expires_at is not None else None,
        )
    except DuplicateResourceError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return invite_response(invite)


@router.get("/admin/invites", response_model=InvitesResponse)
def list_invites(
    session: Annotated[Session, Depends(get_session)],
    _: Annotated[User, Depends(get_current_admin)],
) -> InvitesResponse:
    invites = AuthService(session).list_invites()
    return InvitesResponse(invites=[invite_response(invite) for invite in invites])
