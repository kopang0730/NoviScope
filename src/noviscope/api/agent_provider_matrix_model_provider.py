from noviscope.agents.registry import AgentSpec
from noviscope.agents.stage_runner import StageRunner
from noviscope.api.agent_provider_matrix_contract import (
    AgentProviderMatrixEntry,
    SelectionSource,
)
from noviscope.api.agent_provider_matrix_entries import (
    active_supported_providers,
    ready_model_provider_entry,
    supported_provider_kinds,
    unavailable_entry,
)
from noviscope.api.workflow_capabilities import (
    AutomationStatus,
    ProviderRequirement,
    build_status_detail,
)
from noviscope.models.agent import AgentAssignment
from noviscope.models.provider import ModelProvider, ProviderKind


def blocked_assignment_entry(
    *,
    agent: AgentSpec,
    assigned_provider: ModelProvider | None,
    automation_status: AutomationStatus,
    available_provider_count: int,
    model_name: str | None,
    reason: str,
    status_detail: str,
    supported_kinds: tuple[ProviderKind, ...],
) -> AgentProviderMatrixEntry:
    return unavailable_entry(
        agent=agent,
        assigned_provider=assigned_provider,
        automation_status=automation_status,
        available_provider_count=available_provider_count,
        model_name=model_name,
        provider_requirement=ProviderRequirement.MODEL_PROVIDER,
        reason=reason,
        stage_runner_available=True,
        status_detail=status_detail,
        supported_kinds=supported_kinds,
    )


def assigned_model_provider_entry(
    *,
    agent: AgentSpec,
    assigned_provider: ModelProvider | None,
    automation_status: AutomationStatus,
    available_provider_count: int,
    model_name: str | None,
    supported_kinds: tuple[ProviderKind, ...],
) -> AgentProviderMatrixEntry:
    if assigned_provider is None:
        return blocked_assignment_entry(
            agent=agent,
            assigned_provider=None,
            automation_status=automation_status,
            available_provider_count=available_provider_count,
            model_name=model_name,
            reason="assigned_provider_unavailable",
            status_detail=(
                "The assigned provider is not accessible to this user. Ask an admin to "
                "reassign this agent."
            ),
            supported_kinds=supported_kinds,
        )
    if not assigned_provider.is_active:
        return blocked_assignment_entry(
            agent=agent,
            assigned_provider=assigned_provider,
            automation_status=automation_status,
            available_provider_count=available_provider_count,
            model_name=model_name,
            reason="inactive_assigned_provider",
            status_detail="Activate the assigned provider before running this agent.",
            supported_kinds=supported_kinds,
        )
    if assigned_provider.kind not in supported_kinds:
        return blocked_assignment_entry(
            agent=agent,
            assigned_provider=assigned_provider,
            automation_status=automation_status,
            available_provider_count=available_provider_count,
            model_name=model_name,
            reason="unsupported_assigned_provider",
            status_detail="Assign an active provider kind supported by this agent.",
            supported_kinds=supported_kinds,
        )
    return ready_model_provider_entry(
        agent=agent,
        assigned_provider=assigned_provider,
        automation_status=automation_status,
        available_provider_count=available_provider_count,
        model_name=model_name,
        selection_source=SelectionSource.AGENT_ASSIGNMENT,
        selected_provider=assigned_provider,
        supported_kinds=supported_kinds,
    )


def model_provider_entry(
    agent: AgentSpec,
    automation_status: AutomationStatus,
    assignment: AgentAssignment | None,
    assigned_provider: ModelProvider | None,
    providers: list[ModelProvider],
    runner: StageRunner | None,
) -> AgentProviderMatrixEntry:
    supported_kinds = supported_provider_kinds(runner)
    active_providers = active_supported_providers(providers, supported_kinds)
    model_name = assignment.model_name if assignment is not None else None
    available_provider_count = len(active_providers)

    if runner is None:
        return unavailable_entry(
            agent=agent,
            assigned_provider=assigned_provider,
            automation_status=automation_status,
            available_provider_count=available_provider_count,
            model_name=model_name,
            provider_requirement=ProviderRequirement.MODEL_PROVIDER,
            reason="stage_runner_not_implemented",
            stage_runner_available=False,
            status_detail=build_status_detail(ProviderRequirement.NOT_IMPLEMENTED),
            supported_kinds=supported_kinds,
        )
    if assignment is not None and assignment.provider_id is not None:
        return assigned_model_provider_entry(
            agent=agent,
            assigned_provider=assigned_provider,
            automation_status=automation_status,
            available_provider_count=available_provider_count,
            model_name=model_name,
            supported_kinds=supported_kinds,
        )
    if not active_providers:
        return unavailable_entry(
            agent=agent,
            assigned_provider=None,
            automation_status=automation_status,
            available_provider_count=0,
            model_name=model_name,
            provider_requirement=ProviderRequirement.MODEL_PROVIDER,
            reason="missing_provider",
            stage_runner_available=True,
            status_detail="Configure an active supported provider before running this agent.",
            supported_kinds=supported_kinds,
        )
    return ready_model_provider_entry(
        agent=agent,
        assigned_provider=None,
        automation_status=automation_status,
        available_provider_count=available_provider_count,
        model_name=None,
        selection_source=SelectionSource.AUTO_AVAILABLE_PROVIDER,
        selected_provider=active_providers[0],
        supported_kinds=supported_kinds,
    )
