from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, SecretStr
from sqlmodel import Session

from noviscope.api.dependencies import get_session
from noviscope.api.routes import get_provider_service
from noviscope.auth.dependencies import get_current_user
from noviscope.models.provider import ModelProvider, ProviderKind, ProviderScope
from noviscope.models.user import User, UserRole

router = APIRouter()


class ProviderCreateRequest(BaseModel):
    name: str
    kind: ProviderKind
    base_url: str
    default_model: str
    api_key: SecretStr = Field(repr=False)
    scope: ProviderScope = ProviderScope.PERSONAL


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
    scope: ProviderScope
    owner_user_id: str | None
    base_url: str
    default_model: str
    is_active: bool
    created_at: str
    updated_at: str


class ProvidersResponse(BaseModel):
    providers: list[ProviderResponse]


def provider_response(provider: ModelProvider) -> ProviderResponse:
    return ProviderResponse.model_validate(provider, from_attributes=True)


@router.post("/providers", status_code=status.HTTP_201_CREATED, response_model=ProviderResponse)
def create_provider(
    request: ProviderCreateRequest,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> ProviderResponse:
    service = get_provider_service(session)
    scope = request.scope
    if scope == ProviderScope.SHARED and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    provider = service.create_provider(
        name=request.name,
        kind=request.kind,
        base_url=request.base_url,
        default_model=request.default_model,
        api_key=request.api_key.get_secret_value(),
        scope=scope,
        owner_user_id=None if scope == ProviderScope.SHARED else current_user.id,
        created_by_user_id=current_user.id,
    )
    return provider_response(provider)


@router.get("/providers", response_model=ProvidersResponse)
def list_providers(
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> ProvidersResponse:
    service = get_provider_service(session)
    providers = service.list_providers_for_user(current_user)
    return ProvidersResponse(providers=[provider_response(provider) for provider in providers])


@router.get("/providers/{provider_id}", response_model=ProviderResponse)
def get_provider(
    provider_id: str,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> ProviderResponse:
    service = get_provider_service(session)
    try:
        return provider_response(service.get_provider_for_user(provider_id, current_user))
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


@router.patch("/providers/{provider_id}", response_model=ProviderResponse)
def update_provider(
    provider_id: str,
    request: ProviderUpdateRequest,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> ProviderResponse:
    service = get_provider_service(session)
    try:
        provider = service.update_provider_for_user(
            provider_id,
            current_user,
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
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


@router.delete("/providers/{provider_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_provider(
    provider_id: str,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> None:
    service = get_provider_service(session)
    try:
        service.delete_provider_for_user(provider_id, current_user)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
