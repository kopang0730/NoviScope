from dataclasses import dataclass

from pydantic import SecretStr

from noviscope.agents.stage_runner import ModelProviderCredentials, StageRunner
from noviscope.api.stage_run_blocks import StageBlock
from noviscope.models.provider import ModelProvider, ProviderKind
from noviscope.models.user import User
from noviscope.providers.service import ProviderService


@dataclass(frozen=True, slots=True)
class ProviderSelectionContext:
    provider_service: ProviderService
    current_user: User
    provider_id: str | None
    model_name: str | None
    runner: StageRunner


@dataclass(frozen=True, slots=True)
class ProviderSelection:
    provider: ModelProvider | None
    model_name: str | None
    blocking_reason: str
    blocking_detail: str


def select_provider(context: ProviderSelectionContext) -> ProviderSelection:
    if context.provider_id is not None:
        provider = context.provider_service.get_provider_for_user(
            context.provider_id,
            context.current_user,
        )
        if not provider.is_active:
            return ProviderSelection(
                blocking_detail="Activate this provider before running the stage.",
                blocking_reason="inactive_provider",
                model_name=None,
                provider=None,
            )
        if provider.kind not in context.runner.supported_provider_kinds:
            return ProviderSelection(
                blocking_detail="Choose a supported active provider for this stage.",
                blocking_reason="unsupported_provider",
                model_name=None,
                provider=None,
            )
        return ProviderSelection(
            blocking_detail="",
            blocking_reason="",
            model_name=context.model_name,
            provider=provider,
        )

    for provider in context.provider_service.list_providers_for_user(context.current_user):
        if provider.is_active and provider.kind in context.runner.supported_provider_kinds:
            return ProviderSelection(
                blocking_detail="",
                blocking_reason="",
                model_name=None,
                provider=provider,
            )

    return ProviderSelection(
        blocking_detail="Configure an active supported provider before running this stage.",
        blocking_reason="missing_provider",
        model_name=None,
        provider=None,
    )


def build_provider_credentials(
    provider: ModelProvider,
    provider_service: ProviderService,
    model_name: str | None = None,
) -> ModelProviderCredentials:
    return ModelProviderCredentials(
        api_key=SecretStr(provider_service.decrypt_api_key(provider)),
        base_url=provider.base_url,
        id=provider.id,
        kind=provider.kind,
        model=model_name or provider.default_model,
        name=provider.name,
    )


def build_server_managed_provider() -> ModelProviderCredentials:
    return ModelProviderCredentials(
        api_key=SecretStr(""),
        base_url="https://api.openalex.org",
        id="server_openalex",
        kind=ProviderKind.CUSTOM,
        model="openalex-works",
        name="OpenAlex",
    )


def build_provider_block(selection: ProviderSelection) -> StageBlock:
    return StageBlock(
        evidence_payload={
            "blocking_detail": selection.blocking_detail,
            "blocking_reason": selection.blocking_reason,
            "can_run": False,
        },
        summary="No active model provider is available for this user.",
    )


def build_runner_provider(
    runner: StageRunner,
    selection_context: ProviderSelectionContext,
) -> ModelProviderCredentials | StageBlock:
    if not runner.supported_provider_kinds:
        return build_server_managed_provider()
    selection = select_provider(selection_context)
    if selection.provider is None:
        return build_provider_block(selection)
    return build_provider_credentials(
        selection.provider,
        selection_context.provider_service,
        model_name=selection.model_name,
    )
