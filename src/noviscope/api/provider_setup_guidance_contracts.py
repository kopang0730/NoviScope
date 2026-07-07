from dataclasses import dataclass
from enum import StrEnum

from pydantic import BaseModel, ConfigDict
from sqlmodel import Session

from noviscope.agents.stage_runner import StageRunner, StageRunnerRegistry
from noviscope.models.provider import ProviderKind, ProviderScope
from noviscope.models.user import User
from noviscope.providers.service import ProviderService

MISSING_PROVIDER_ACTIONS: tuple[str, ...] = (
    "Create a personal provider or ask an admin to configure a shared provider.",
    "Set the provider base URL, model, and API key.",
    "Keep the provider active before running this stage.",
)
INACTIVE_PROVIDER_ACTIONS: tuple[str, ...] = (
    "Activate the assigned provider or choose another active provider.",
)
MISSING_ASSIGNED_PROVIDER_ACTIONS: tuple[str, ...] = (
    "Ask an admin to choose an accessible shared provider for this agent.",
)
UNSUPPORTED_PROVIDER_ACTIONS: tuple[str, ...] = (
    "Choose a provider kind supported by this stage.",
)
RUNNER_MISSING_ACTIONS: tuple[str, ...] = (
    "This stage is not wired to a runnable agent yet.",
)


class ProviderSetupStatus(StrEnum):
    READY = "ready"
    BLOCKED = "blocked"
    SERVER_MANAGED = "server_managed"


class ProviderSetupReason(StrEnum):
    AGENT_DEFAULT_READY = "agent_default_ready"
    ASSIGNED_PROVIDER_INACTIVE = "assigned_provider_inactive"
    ASSIGNED_PROVIDER_MISSING = "assigned_provider_missing"
    ASSIGNED_PROVIDER_UNSUPPORTED = "assigned_provider_unsupported"
    AUTO_SELECT_READY = "auto_select_ready"
    MISSING_PROVIDER = "missing_provider"
    RUNNER_NOT_IMPLEMENTED = "runner_not_implemented"
    SERVER_MANAGED = "server_managed"


class ProviderSetupSource(StrEnum):
    AGENT_DEFAULT = "agent_default"
    AUTO_SELECT = "auto_select"
    SERVER_MANAGED = "server_managed"


class ProviderSetupGuidanceResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    stage_id: str
    agent_id: str
    provider_status: ProviderSetupStatus
    reason: ProviderSetupReason
    can_run: bool
    setup_actions: list[str]
    provider_id: str | None = None
    provider_name: str | None = None
    provider_kind: ProviderKind | None = None
    provider_model: str | None = None
    provider_scope: ProviderScope | None = None
    provider_source: ProviderSetupSource | None = None
    uses_server_managed_provider: bool = False


@dataclass(frozen=True, slots=True)
class ProviderGuidanceDeps:
    session: Session
    current_user: User
    registry: StageRunnerRegistry


@dataclass(frozen=True, slots=True)
class StageGuidanceSubject:
    stage_id: str
    agent_id: str


@dataclass(frozen=True, slots=True)
class ProviderGuidanceContext:
    stage: StageGuidanceSubject
    current_user: User
    provider_service: ProviderService
    runner: StageRunner


@dataclass(frozen=True, slots=True)
class ProviderUsage:
    source: ProviderSetupSource
    model_name: str | None
