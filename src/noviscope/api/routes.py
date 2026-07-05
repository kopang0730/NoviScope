from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, Field, SecretStr
from sqlmodel import Session

from noviscope.agents.registry import AGENT_REGISTRY, AgentSpec
from noviscope.api.dependencies import get_session
from noviscope.auth.dependencies import (
    clear_session_cookie,
    create_session_token,
    get_admin_or_dev_header,
    get_current_user,
    set_session_cookie,
)
from noviscope.auth.service import AuthService
from noviscope.core.config import get_settings
from noviscope.core.crypto import SecretBox
from noviscope.models.provider import ModelProvider, ProviderKind
from noviscope.models.quest import Quest, QuestStatus, StageCard, StageStatus
from noviscope.models.user import InviteCode, InviteStatus, User, UserRole
from noviscope.providers.service import ProviderService
from noviscope.quests.service import QuestService

router = APIRouter()


class QuestCreateRequest(BaseModel):
    title: str
    initial_direction: str


class UserResponse(BaseModel):
    id: str
    email: str
    display_name: str
    role: UserRole
    is_active: bool
    created_at: str
    updated_at: str


class RegisterRequest(BaseModel):
    invite_code: str
    email: str
    display_name: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


class InviteCreateRequest(BaseModel):
    code: str
    max_uses: int = 1
    expires_at: str | None = None


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


class StageCardResponse(BaseModel):
    id: str
    quest_id: str
    agent_id: str
    title: str
    status: StageStatus
    summary: str
    input_payload: dict[str, object]
    output_payload: dict[str, object]
    evidence_payload: dict[str, object]
    human_approved: bool | None
    review_notes: str
    created_at: str
    updated_at: str


class QuestCreateResponse(BaseModel):
    id: str
    owner_user_id: str | None
    title: str
    initial_direction: str
    status: QuestStatus
    first_stage: StageCardResponse


class QuestResponse(BaseModel):
    id: str
    owner_user_id: str | None
    title: str
    initial_direction: str
    status: QuestStatus
    created_at: str
    updated_at: str


class QuestsResponse(BaseModel):
    quests: list[QuestResponse]


class AgentsResponse(BaseModel):
    agents: list[AgentSpec]


class StagesResponse(BaseModel):
    stages: list[StageCardResponse]


class StageUpdateRequest(BaseModel):
    status: StageStatus | None = None
    summary: str | None = None
    input_payload: dict[str, object] | None = None
    output_payload: dict[str, object] | None = None
    evidence_payload: dict[str, object] | None = None
    human_approved: bool | None = None
    review_notes: str | None = None


class ProviderCreateRequest(BaseModel):
    name: str
    kind: ProviderKind
    base_url: str
    default_model: str
    api_key: SecretStr = Field(repr=False)


class ProviderUpdateRequest(BaseModel):
    name: str | None = None
    kind: ProviderKind | None = None
    base_url: str | None = None
    default_model: str | None = None
    api_key: SecretStr | None = Field(default=None, repr=False)
    is_active: bool | None = None


class ProviderResponse(BaseModel):
    id: str
    name: str
    kind: ProviderKind
    base_url: str
    default_model: str
    is_active: bool
    created_at: str
    updated_at: str


class ProvidersResponse(BaseModel):
    providers: list[ProviderResponse]


def user_response(user: User) -> UserResponse:
    return UserResponse.model_validate(user, from_attributes=True)


def invite_response(invite: InviteCode) -> InviteResponse:
    return InviteResponse.model_validate(invite, from_attributes=True)


def provider_response(provider: ModelProvider) -> ProviderResponse:
    return ProviderResponse.model_validate(provider, from_attributes=True)


def stage_response(stage: StageCard) -> StageCardResponse:
    return StageCardResponse.model_validate(stage, from_attributes=True)


def quest_response(quest: Quest) -> QuestResponse:
    return QuestResponse.model_validate(quest, from_attributes=True)


def get_provider_service(session: Session) -> ProviderService:
    settings = get_settings()
    return ProviderService(session, SecretBox(settings.provider_secret_key))


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/agents")
def list_agents() -> AgentsResponse:
    return AgentsResponse(agents=list(AGENT_REGISTRY.values()))


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
    invite = AuthService(session).create_invite(
        code=request.code,
        created_by_user_id=admin_id,
        max_uses=request.max_uses,
        expires_at=request.expires_at,
    )
    return invite_response(invite)


@router.post("/providers", status_code=status.HTTP_201_CREATED, response_model=ProviderResponse)
def create_provider(
    request: ProviderCreateRequest,
    session: Annotated[Session, Depends(get_session)],
) -> ProviderResponse:
    service = get_provider_service(session)
    provider = service.create_provider(
        name=request.name,
        kind=request.kind,
        base_url=request.base_url,
        default_model=request.default_model,
        api_key=request.api_key.get_secret_value(),
    )
    return provider_response(provider)


@router.get("/providers", response_model=ProvidersResponse)
def list_providers(session: Annotated[Session, Depends(get_session)]) -> ProvidersResponse:
    service = get_provider_service(session)
    return ProvidersResponse(
        providers=[provider_response(provider) for provider in service.list_providers()]
    )


@router.get("/providers/{provider_id}", response_model=ProviderResponse)
def get_provider(
    provider_id: str,
    session: Annotated[Session, Depends(get_session)],
) -> ProviderResponse:
    service = get_provider_service(session)
    try:
        return provider_response(service.get_provider(provider_id))
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.patch("/providers/{provider_id}", response_model=ProviderResponse)
def update_provider(
    provider_id: str,
    request: ProviderUpdateRequest,
    session: Annotated[Session, Depends(get_session)],
) -> ProviderResponse:
    service = get_provider_service(session)
    try:
        provider = service.update_provider(
            provider_id,
            name=request.name,
            kind=request.kind,
            base_url=request.base_url,
            default_model=request.default_model,
            api_key=request.api_key.get_secret_value() if request.api_key is not None else None,
            is_active=request.is_active,
        )
        return provider_response(provider)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.delete("/providers/{provider_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_provider(
    provider_id: str,
    session: Annotated[Session, Depends(get_session)],
) -> None:
    service = get_provider_service(session)
    try:
        service.delete_provider(provider_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("/quests", status_code=status.HTTP_201_CREATED, response_model=QuestCreateResponse)
def create_quest(
    request: QuestCreateRequest,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> QuestCreateResponse:
    service = QuestService(session)
    quest = service.create_quest(
        title=request.title,
        initial_direction=request.initial_direction,
        owner_user_id=current_user.id,
    )
    first_stage = service.list_stage_cards(quest.id)[0]
    return QuestCreateResponse(
        id=quest.id,
        owner_user_id=quest.owner_user_id,
        title=quest.title,
        initial_direction=quest.initial_direction,
        status=quest.status,
        first_stage=stage_response(first_stage),
    )


@router.get("/quests", response_model=QuestsResponse)
def list_quests(
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> QuestsResponse:
    service = QuestService(session)
    return QuestsResponse(
        quests=[quest_response(quest) for quest in service.list_quests_for_user(current_user)]
    )


@router.get("/quests/{quest_id}", response_model=QuestResponse)
def get_quest(
    quest_id: str,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> QuestResponse:
    service = QuestService(session)
    try:
        return quest_response(service.get_quest_for_user(quest_id, current_user))
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


@router.get("/quests/{quest_id}/stages", response_model=StagesResponse)
def list_quest_stages(
    quest_id: str,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> StagesResponse:
    service = QuestService(session)
    try:
        service.get_quest_for_user(quest_id, current_user)
        return StagesResponse(
            stages=[stage_response(stage) for stage in service.list_stage_cards(quest_id)]
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


@router.patch("/stages/{stage_id}", response_model=StageCardResponse)
def update_stage(
    stage_id: str,
    request: StageUpdateRequest,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> StageCardResponse:
    service = QuestService(session)
    try:
        service.get_stage_card_for_user(stage_id, current_user)
        stage = service.update_stage_card(
            stage_id,
            status=request.status,
            summary=request.summary,
            input_payload=request.input_payload,
            output_payload=request.output_payload,
            evidence_payload=request.evidence_payload,
            human_approved=request.human_approved,
            review_notes=request.review_notes,
        )
        return stage_response(stage)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
