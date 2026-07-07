from dataclasses import dataclass
from enum import StrEnum

from pydantic import BaseModel, ConfigDict

from noviscope.agents.stage_runner import StageRunnerRegistry
from noviscope.api.workflow_capabilities import AutomationStatus, ProviderRequirement
from noviscope.models.agent import AgentAssignment
from noviscope.models.provider import ModelProvider, ProviderKind, ProviderScope


class SelectionSource(StrEnum):
    AGENT_ASSIGNMENT = "agent_assignment"
    AUTO_AVAILABLE_PROVIDER = "auto_available_provider"
    SERVER_MANAGED = "server_managed"
    UNAVAILABLE = "unavailable"


class AgentProviderSnapshot(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    name: str
    kind: ProviderKind
    scope: ProviderScope | None
    is_active: bool
    default_model: str


class AgentProviderMatrixEntry(BaseModel):
    model_config = ConfigDict(frozen=True)

    agent_id: str
    automation_status: AutomationStatus
    display_name: str
    provider_requirement: ProviderRequirement
    stage_runner_available: bool
    supported_provider_kinds: tuple[ProviderKind, ...]
    tool_permissions: tuple[str, ...]
    assigned_provider: AgentProviderSnapshot | None
    selected_provider: AgentProviderSnapshot | None
    model_name: str | None
    effective_model: str | None
    available_provider_count: int
    uses_server_managed_provider: bool
    can_run_with_current_config: bool
    selection_source: SelectionSource
    unavailable_reason: str | None
    status_detail: str


class AgentProviderMatrixResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    agents: tuple[AgentProviderMatrixEntry, ...]
    runnable_count: int
    blocked_count: int
    total_count: int


@dataclass(frozen=True, slots=True)
class MatrixBuildContext:
    assignments: dict[str, AgentAssignment]
    providers: list[ModelProvider]
    providers_by_id: dict[str, ModelProvider]
    registry: StageRunnerRegistry
