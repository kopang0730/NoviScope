from dataclasses import dataclass
from typing import ClassVar, Final, Literal, TypeAlias

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict

from noviscope.agents.literature_scout import LITERATURE_SCOUT_AGENT_ID
from noviscope.agents.registry import AGENT_REGISTRY
from noviscope.core.stage_policy import (
    DEMAND_VALIDATOR_AGENT_ID,
    EXPERIMENT_PLANNER_AGENT_ID,
    IDEA_GENERATOR_AGENT_ID,
    PAPER_MEETING_WRITER_AGENT_ID,
)

router = APIRouter()


CanvasRole: TypeAlias = Literal["audit_gate", "core_stage", "planned_extension"]
EdgeKind: TypeAlias = Literal["audit_feedback", "default_flow", "human_gate", "planned_extension"]


class CanvasNodeResponse(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    agent_id: str
    canvas_role: CanvasRole
    column: int
    display_name: str
    lane_id: str
    row: int


class CanvasEdgeResponse(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    edge_kind: EdgeKind
    from_agent_id: str
    label: str
    to_agent_id: str


class CanvasLaneResponse(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    description: str
    lane_id: str
    title: str


class WorkflowCanvasTemplateResponse(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    core_flow_agent_ids: tuple[str, ...]
    edges: tuple[CanvasEdgeResponse, ...]
    entry_agent_id: str
    lanes: tuple[CanvasLaneResponse, ...]
    nodes: tuple[CanvasNodeResponse, ...]
    terminal_agent_id: str


@dataclass(frozen=True, slots=True)
class CanvasNodeLayout:
    agent_id: str
    canvas_role: CanvasRole
    column: int
    lane_id: str
    row: int


@dataclass(frozen=True, slots=True)
class CanvasEdgeLayout:
    edge_kind: EdgeKind
    from_agent_id: str
    label: str
    to_agent_id: str


CORE_FLOW_AGENT_IDS: Final[tuple[str, ...]] = (
    DEMAND_VALIDATOR_AGENT_ID,
    LITERATURE_SCOUT_AGENT_ID,
    IDEA_GENERATOR_AGENT_ID,
    EXPERIMENT_PLANNER_AGENT_ID,
    PAPER_MEETING_WRITER_AGENT_ID,
)

CANVAS_LANES: Final[tuple[CanvasLaneResponse, ...]] = (
    CanvasLaneResponse(
        description="Demand reality checks and problem framing.",
        lane_id="validation",
        title="Validation",
    ),
    CanvasLaneResponse(
        description="Literature, gaps, hypotheses, and idea selection.",
        lane_id="research",
        title="Research",
    ),
    CanvasLaneResponse(
        description="Experiment planning, future code runs, and evidence audits.",
        lane_id="experiment",
        title="Experiment",
    ),
    CanvasLaneResponse(
        description="Traceable paper and meeting artifacts.",
        lane_id="artifact",
        title="Artifact",
    ),
)

CANVAS_NODE_LAYOUTS: Final[tuple[CanvasNodeLayout, ...]] = (
    CanvasNodeLayout(DEMAND_VALIDATOR_AGENT_ID, "core_stage", 1, "validation", 1),
    CanvasNodeLayout("research_refiner", "planned_extension", 2, "validation", 2),
    CanvasNodeLayout(LITERATURE_SCOUT_AGENT_ID, "core_stage", 2, "research", 1),
    CanvasNodeLayout("gap_analyst", "planned_extension", 3, "research", 2),
    CanvasNodeLayout(IDEA_GENERATOR_AGENT_ID, "core_stage", 3, "research", 1),
    CanvasNodeLayout(EXPERIMENT_PLANNER_AGENT_ID, "core_stage", 4, "experiment", 1),
    CanvasNodeLayout("code_runner", "planned_extension", 5, "experiment", 2),
    CanvasNodeLayout("evidence_auditor", "audit_gate", 6, "experiment", 2),
    CanvasNodeLayout(PAPER_MEETING_WRITER_AGENT_ID, "core_stage", 6, "artifact", 1),
)

CANVAS_EDGE_LAYOUTS: Final[tuple[CanvasEdgeLayout, ...]] = (
    CanvasEdgeLayout(
        "human_gate",
        DEMAND_VALIDATOR_AGENT_ID,
        "Demand review gate",
        LITERATURE_SCOUT_AGENT_ID,
    ),
    CanvasEdgeLayout(
        "default_flow",
        LITERATURE_SCOUT_AGENT_ID,
        "Evidence map",
        IDEA_GENERATOR_AGENT_ID,
    ),
    CanvasEdgeLayout(
        "human_gate",
        IDEA_GENERATOR_AGENT_ID,
        "Idea selection gate",
        EXPERIMENT_PLANNER_AGENT_ID,
    ),
    CanvasEdgeLayout(
        "human_gate",
        EXPERIMENT_PLANNER_AGENT_ID,
        "Experiment review gate",
        PAPER_MEETING_WRITER_AGENT_ID,
    ),
    CanvasEdgeLayout(
        "planned_extension",
        DEMAND_VALIDATOR_AGENT_ID,
        "Optional scoping",
        "research_refiner",
    ),
    CanvasEdgeLayout(
        "planned_extension",
        "research_refiner",
        "Refined query",
        LITERATURE_SCOUT_AGENT_ID,
    ),
    CanvasEdgeLayout(
        "planned_extension",
        LITERATURE_SCOUT_AGENT_ID,
        "Limitation audit",
        "gap_analyst",
    ),
    CanvasEdgeLayout(
        "planned_extension",
        "gap_analyst",
        "Gap evidence",
        IDEA_GENERATOR_AGENT_ID,
    ),
    CanvasEdgeLayout(
        "planned_extension",
        EXPERIMENT_PLANNER_AGENT_ID,
        "Future automated execution",
        "code_runner",
    ),
    CanvasEdgeLayout(
        "audit_feedback",
        "code_runner",
        "Run provenance",
        "evidence_auditor",
    ),
    CanvasEdgeLayout(
        "audit_feedback",
        "evidence_auditor",
        "Claim audit",
        PAPER_MEETING_WRITER_AGENT_ID,
    ),
)


def build_canvas_node(layout: CanvasNodeLayout) -> CanvasNodeResponse:
    return CanvasNodeResponse(
        agent_id=layout.agent_id,
        canvas_role=layout.canvas_role,
        column=layout.column,
        display_name=AGENT_REGISTRY[layout.agent_id].display_name,
        lane_id=layout.lane_id,
        row=layout.row,
    )


def build_canvas_edge(layout: CanvasEdgeLayout) -> CanvasEdgeResponse:
    return CanvasEdgeResponse(
        edge_kind=layout.edge_kind,
        from_agent_id=layout.from_agent_id,
        label=layout.label,
        to_agent_id=layout.to_agent_id,
    )


CANVAS_NODES: Final[tuple[CanvasNodeResponse, ...]] = tuple(
    build_canvas_node(layout) for layout in CANVAS_NODE_LAYOUTS
)
CANVAS_EDGES: Final[tuple[CanvasEdgeResponse, ...]] = tuple(
    build_canvas_edge(layout) for layout in CANVAS_EDGE_LAYOUTS
)


@router.get("/workflow/canvas-template")
def get_workflow_canvas_template() -> WorkflowCanvasTemplateResponse:
    return WorkflowCanvasTemplateResponse(
        core_flow_agent_ids=CORE_FLOW_AGENT_IDS,
        edges=CANVAS_EDGES,
        entry_agent_id=DEMAND_VALIDATOR_AGENT_ID,
        lanes=CANVAS_LANES,
        nodes=CANVAS_NODES,
        terminal_agent_id=PAPER_MEETING_WRITER_AGENT_ID,
    )
