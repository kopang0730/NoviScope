from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field, SecretStr
from sqlmodel import Session

from noviscope.api.dependencies import get_session
from noviscope.auth.dependencies import get_current_user
from noviscope.core.config import get_settings
from noviscope.core.crypto import SecretBox
from noviscope.model_gateway.adapters import (
    AnthropicAdapter,
    ConfigurationOnlyAdapter,
    OpenAICompatibleAdapter,
)
from noviscope.model_gateway.service import ConnectionTestResult, ModelGateway, ProviderProfile
from noviscope.models.provider import ProviderKind
from noviscope.models.user import User
from noviscope.providers.service import ProviderService

router = APIRouter()


class ProviderPreviewTestRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    kind: ProviderKind
    base_url: str
    default_model: str
    api_key: SecretStr = Field(repr=False)


def build_model_gateway() -> ModelGateway:
    gateway = ModelGateway()
    gateway.register_adapter(ProviderKind.OPENAI_COMPATIBLE.value, OpenAICompatibleAdapter())
    gateway.register_adapter(ProviderKind.ANTHROPIC.value, AnthropicAdapter())
    gateway.register_adapter(ProviderKind.CUSTOM.value, ConfigurationOnlyAdapter("custom"))
    return gateway


def get_provider_service(session: Session) -> ProviderService:
    settings = get_settings()
    return ProviderService(session, SecretBox(settings.provider_secret_key))


@router.post("/provider-tests/preview", response_model=ConnectionTestResult)
def test_provider_preview_connection(
    request: ProviderPreviewTestRequest,
    current_user: Annotated[User, Depends(get_current_user)],
) -> ConnectionTestResult:
    return build_model_gateway().test_connection(
        ProviderProfile(
            api_key=request.api_key,
            base_url=request.base_url,
            default_model=request.default_model,
            kind=request.kind.value,
            provider_id="preview",
        )
    )


@router.post("/providers/{provider_id}/test", response_model=ConnectionTestResult)
def test_provider_connection(
    provider_id: str,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> ConnectionTestResult:
    service = get_provider_service(session)
    try:
        provider = service.get_provider_for_user(provider_id, current_user)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

    if not provider.is_active:
        return ConnectionTestResult(
            ok=False,
            provider_id=provider.id,
            model=provider.default_model,
            message="Provider is inactive. Enable it before running stages.",
        )

    result = build_model_gateway().test_connection(
        ProviderProfile(
            provider_id=provider.id,
            kind=provider.kind.value,
            base_url=provider.base_url,
            api_key=SecretStr(service.decrypt_api_key(provider)),
            default_model=provider.default_model,
        )
    )
    return result
