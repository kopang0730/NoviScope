from noviscope.agents.registry import AgentSpec
from noviscope.agents.stage_runner import StageRunner
from noviscope.api.agent_provider_matrix_contract import (
    AgentProviderMatrixEntry,
    AgentProviderSnapshot,
    SelectionSource,
)
from noviscope.api.stage_runs import build_server_managed_provider
from noviscope.api.workflow_capabilities import (
    AutomationStatus,
    ProviderRequirement,
    build_status_detail,
)
from noviscope.models.agent import AgentAssignment
from noviscope.models.provider import ModelProvider, ProviderKind


def provider_snapshot(provider: ModelProvider) -> AgentProviderSnapshot:
    return AgentProviderSnapshot(
        default_model=provider.default_model,
        id=provider.id,
        is_active=provider.is_active,
        kind=provider.kind,
        name=provider.name,
        scope=provider.scope,
    )


def assigned_provider_snapshot(provider: ModelProvider | None) -> AgentProviderSnapshot | None:
    if provider is None:
        return None
    return provider_snapshot(provider)


def server_managed_provider_snapshot() -> AgentProviderSnapshot:
    provider = build_server_managed_provider()
    return AgentProviderSnapshot(
        default_model=provider.model,
        id=provider.id,
        is_active=True,
        kind=provider.kind,
        name=provider.name,
        scope=None,
    )


def tool_permission_values(agent: AgentSpec) -> tuple[str, ...]:
    return tuple(permission.value for permission in agent.tool_permissions)


def supported_provider_kinds(runner: StageRunner | None) -> tuple[ProviderKind, ...]:
    if runner is None:
        return ()
    return tuple(sorted(runner.supported_provider_kinds, key=lambda kind: kind.value))


def active_supported_providers(
    providers: list[ModelProvider],
    supported_kinds: tuple[ProviderKind, ...],
) -> list[ModelProvider]:
    return [
        provider
        for provider in providers
        if provider.is_active and provider.kind in supported_kinds
    ]


def assignment_provider(
    assignment: AgentAssignment | None,
    providers_by_id: dict[str, ModelProvider],
) -> ModelProvider | None:
    if assignment is None or assignment.provider_id is None:
        return None
    return providers_by_id.get(assignment.provider_id)


def unavailable_entry(
    *,
    agent: AgentSpec,
    assigned_provider: ModelProvider | None,
    automation_status: AutomationStatus,
    available_provider_count: int,
    model_name: str | None,
    provider_requirement: ProviderRequirement,
    reason: str,
    stage_runner_available: bool,
    status_detail: str,
    supported_kinds: tuple[ProviderKind, ...],
) -> AgentProviderMatrixEntry:
    return AgentProviderMatrixEntry(
        agent_id=agent.agent_id,
        assigned_provider=assigned_provider_snapshot(assigned_provider),
        automation_status=automation_status,
        available_provider_count=available_provider_count,
        can_run_with_current_config=False,
        display_name=agent.display_name,
        effective_model=None,
        model_name=model_name,
        provider_requirement=provider_requirement,
        selected_provider=None,
        selection_source=SelectionSource.UNAVAILABLE,
        stage_runner_available=stage_runner_available,
        status_detail=status_detail,
        supported_provider_kinds=supported_kinds,
        tool_permissions=tool_permission_values(agent),
        unavailable_reason=reason,
        uses_server_managed_provider=False,
    )


def server_managed_entry(
    agent: AgentSpec,
    automation_status: AutomationStatus,
    assignment: AgentAssignment | None,
    assigned_provider: ModelProvider | None,
) -> AgentProviderMatrixEntry:
    provider = server_managed_provider_snapshot()
    return AgentProviderMatrixEntry(
        agent_id=agent.agent_id,
        assigned_provider=assigned_provider_snapshot(assigned_provider),
        automation_status=automation_status,
        available_provider_count=0,
        can_run_with_current_config=True,
        display_name=agent.display_name,
        effective_model=provider.default_model,
        model_name=assignment.model_name if assignment is not None else None,
        provider_requirement=ProviderRequirement.SERVER_MANAGED,
        selected_provider=provider,
        selection_source=SelectionSource.SERVER_MANAGED,
        stage_runner_available=True,
        status_detail=build_status_detail(ProviderRequirement.SERVER_MANAGED),
        supported_provider_kinds=(),
        tool_permissions=tool_permission_values(agent),
        unavailable_reason=None,
        uses_server_managed_provider=True,
    )


def ready_model_provider_entry(
    *,
    agent: AgentSpec,
    assigned_provider: ModelProvider | None,
    automation_status: AutomationStatus,
    available_provider_count: int,
    model_name: str | None,
    selection_source: SelectionSource,
    selected_provider: ModelProvider,
    supported_kinds: tuple[ProviderKind, ...],
) -> AgentProviderMatrixEntry:
    return AgentProviderMatrixEntry(
        agent_id=agent.agent_id,
        assigned_provider=assigned_provider_snapshot(assigned_provider),
        automation_status=automation_status,
        available_provider_count=available_provider_count,
        can_run_with_current_config=True,
        display_name=agent.display_name,
        effective_model=model_name or selected_provider.default_model,
        model_name=model_name,
        provider_requirement=ProviderRequirement.MODEL_PROVIDER,
        selected_provider=provider_snapshot(selected_provider),
        selection_source=selection_source,
        stage_runner_available=True,
        status_detail="Ready with the current model provider configuration.",
        supported_provider_kinds=supported_kinds,
        tool_permissions=tool_permission_values(agent),
        unavailable_reason=None,
        uses_server_managed_provider=False,
    )
