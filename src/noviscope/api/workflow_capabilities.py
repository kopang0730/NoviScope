from enum import StrEnum
from typing import ClassVar, Final, assert_never

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict

from noviscope.agents.literature_scout import LITERATURE_SCOUT_AGENT_ID
from noviscope.agents.registry import AGENT_REGISTRY, AgentSpec
from noviscope.core.stage_policy import (
    DEMAND_VALIDATOR_AGENT_ID,
    EXPERIMENT_PLANNER_AGENT_ID,
    IDEA_GENERATOR_AGENT_ID,
    PAPER_MEETING_WRITER_AGENT_ID,
)

router = APIRouter()

IMPLEMENTED_STAGE_RUNNER_AGENT_IDS: Final[frozenset[str]] = frozenset(
    {
        DEMAND_VALIDATOR_AGENT_ID,
        EXPERIMENT_PLANNER_AGENT_ID,
        IDEA_GENERATOR_AGENT_ID,
        LITERATURE_SCOUT_AGENT_ID,
        PAPER_MEETING_WRITER_AGENT_ID,
    }
)
SERVER_MANAGED_AGENT_IDS: Final[frozenset[str]] = frozenset({LITERATURE_SCOUT_AGENT_ID})


class AutomationStatus(StrEnum):
    IMPLEMENTED = "implemented"
    PLANNED = "planned"


class ProviderRequirement(StrEnum):
    MODEL_PROVIDER = "model_provider"
    NOT_IMPLEMENTED = "not_implemented"
    SERVER_MANAGED = "server_managed"


class WorkflowAgentCapabilityResponse(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    agent_id: str
    automation_status: AutomationStatus
    display_name: str
    provider_requirement: ProviderRequirement
    stage_runner_available: bool
    status_detail: str
    tool_permissions: tuple[str, ...]


class WorkflowCapabilitiesResponse(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    agents: tuple[WorkflowAgentCapabilityResponse, ...]
    implemented_count: int
    planned_count: int
    total_count: int


def build_agent_capability(agent: AgentSpec) -> WorkflowAgentCapabilityResponse:
    stage_runner_available = agent.agent_id in IMPLEMENTED_STAGE_RUNNER_AGENT_IDS
    provider_requirement = determine_provider_requirement(agent.agent_id)
    return WorkflowAgentCapabilityResponse(
        agent_id=agent.agent_id,
        automation_status=automation_status(stage_runner_available),
        display_name=agent.display_name,
        provider_requirement=provider_requirement,
        stage_runner_available=stage_runner_available,
        status_detail=build_status_detail(provider_requirement),
        tool_permissions=tuple(permission.value for permission in agent.tool_permissions),
    )


def automation_status(stage_runner_available: bool) -> AutomationStatus:
    if stage_runner_available:
        return AutomationStatus.IMPLEMENTED
    return AutomationStatus.PLANNED


def determine_provider_requirement(agent_id: str) -> ProviderRequirement:
    if agent_id not in IMPLEMENTED_STAGE_RUNNER_AGENT_IDS:
        return ProviderRequirement.NOT_IMPLEMENTED
    if agent_id in SERVER_MANAGED_AGENT_IDS:
        return ProviderRequirement.SERVER_MANAGED
    return ProviderRequirement.MODEL_PROVIDER


def build_status_detail(provider_requirement: ProviderRequirement) -> str:
    match provider_requirement:
        case ProviderRequirement.MODEL_PROVIDER:
            return "Runnable when a compatible model provider is configured."
        case ProviderRequirement.NOT_IMPLEMENTED:
            return "Planned only; no automated stage runner exists yet."
        case ProviderRequirement.SERVER_MANAGED:
            return "Runnable through server-managed research connectors."
        case unreachable:
            assert_never(unreachable)


@router.get("/workflow/capabilities")
def get_workflow_capabilities() -> WorkflowCapabilitiesResponse:
    agents = tuple(build_agent_capability(agent) for agent in AGENT_REGISTRY.values())
    implemented_count = sum(capability.stage_runner_available for capability in agents)
    return WorkflowCapabilitiesResponse(
        agents=agents,
        implemented_count=implemented_count,
        planned_count=len(agents) - implemented_count,
        total_count=len(agents),
    )
