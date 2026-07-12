from dataclasses import dataclass
from typing import Annotated, ClassVar, Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict

from noviscope.api.stage_readiness import (
    StageReadinessRequestContext,
    get_stage_readiness_context,
)
from noviscope.api.workflow_canvas import (
    CANVAS_EDGES,
    CANVAS_LANES,
    CANVAS_NODES,
    CanvasEdgeResponse,
    CanvasLaneResponse,
    CanvasNodeResponse,
    CanvasRole,
    EdgeKind,
)
from noviscope.api.workflow_graph import (
    GateStatus,
    WorkflowEdgeResponse,
    WorkflowGraphResponse,
    WorkflowNodeResponse,
    WorkflowQuestResponse,
    build_workflow_graph,
)
from noviscope.core.stage_policy import StageConfidence
from noviscope.models.provider import ProviderKind, ProviderScope
from noviscope.models.quest import StageStatus
from noviscope.quests.service import QuestService

router = APIRouter()

ImplementationStatus = Literal["implemented_stage", "planned_extension"]


class WorkflowCanvasStateNodeResponse(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    agent_id: str
    blocking_detail: str
    blocking_reason: str
    can_run: bool
    canvas_role: CanvasRole
    column: int
    confidence: StageConfidence | None
    display_name: str
    human_approved: bool | None
    human_review_required: bool
    implementation_status: ImplementationStatus
    lane_id: str
    provider_id: str | None
    provider_kind: ProviderKind | None
    provider_model: str | None
    provider_name: str | None
    provider_scope: ProviderScope | None
    review_state: GateStatus
    row: int
    stage_id: str | None
    status: StageStatus | None
    summary: str
    title: str
    uses_server_managed_provider: bool


class WorkflowCanvasStateEdgeResponse(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    edge_kind: EdgeKind
    from_agent_id: str
    gate_required: bool
    gate_status: GateStatus
    label: str
    source_stage_id: str | None
    target_stage_id: str | None
    to_agent_id: str


class WorkflowCanvasStateResponse(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    quest: WorkflowQuestResponse
    lanes: tuple[CanvasLaneResponse, ...]
    nodes: tuple[WorkflowCanvasStateNodeResponse, ...]
    edges: tuple[WorkflowCanvasStateEdgeResponse, ...]
    next_action_agent_id: str | None
    next_action_stage_id: str | None
    planned_node_count: int
    runnable_node_count: int
    stage_node_count: int
    total_node_count: int


@dataclass(frozen=True, slots=True)
class CanvasStateBuildContext:
    graph: WorkflowGraphResponse
    graph_edges_by_agent_pair: dict[tuple[str, str], WorkflowEdgeResponse]
    graph_nodes_by_agent_id: dict[str, WorkflowNodeResponse]


def implemented_node(
    canvas_node: CanvasNodeResponse,
    graph_node: WorkflowNodeResponse,
) -> WorkflowCanvasStateNodeResponse:
    return WorkflowCanvasStateNodeResponse(
        agent_id=graph_node.agent_id,
        blocking_detail=graph_node.blocking_detail,
        blocking_reason=graph_node.blocking_reason,
        can_run=graph_node.can_run,
        canvas_role=canvas_node.canvas_role,
        column=canvas_node.column,
        confidence=graph_node.confidence,
        display_name=canvas_node.display_name,
        human_approved=graph_node.human_approved,
        human_review_required=graph_node.human_review_required,
        implementation_status="implemented_stage",
        lane_id=canvas_node.lane_id,
        provider_id=graph_node.provider_id,
        provider_kind=graph_node.provider_kind,
        provider_model=graph_node.provider_model,
        provider_name=graph_node.provider_name,
        provider_scope=graph_node.provider_scope,
        review_state=graph_node.review_state,
        row=canvas_node.row,
        stage_id=graph_node.stage_id,
        status=graph_node.status,
        summary=graph_node.summary,
        title=graph_node.title,
        uses_server_managed_provider=graph_node.uses_server_managed_provider,
    )


def planned_node(canvas_node: CanvasNodeResponse) -> WorkflowCanvasStateNodeResponse:
    return WorkflowCanvasStateNodeResponse(
        agent_id=canvas_node.agent_id,
        blocking_detail="This canvas agent does not have an automated stage yet.",
        blocking_reason="planned_agent",
        can_run=False,
        canvas_role=canvas_node.canvas_role,
        column=canvas_node.column,
        confidence=None,
        display_name=canvas_node.display_name,
        human_approved=None,
        human_review_required=False,
        implementation_status="planned_extension",
        lane_id=canvas_node.lane_id,
        provider_id=None,
        provider_kind=None,
        provider_model=None,
        provider_name=None,
        provider_scope=None,
        review_state="not_required",
        row=canvas_node.row,
        stage_id=None,
        status=None,
        summary="Planned canvas agent; no workflow stage is created yet.",
        title=canvas_node.display_name,
        uses_server_managed_provider=False,
    )


def build_canvas_state_node(
    canvas_node: CanvasNodeResponse,
    context: CanvasStateBuildContext,
) -> WorkflowCanvasStateNodeResponse:
    graph_node = context.graph_nodes_by_agent_id.get(canvas_node.agent_id)
    if graph_node is not None:
        return implemented_node(canvas_node, graph_node)
    return planned_node(canvas_node)


def build_canvas_state_edge(
    canvas_edge: CanvasEdgeResponse,
    context: CanvasStateBuildContext,
) -> WorkflowCanvasStateEdgeResponse:
    graph_edge = context.graph_edges_by_agent_pair.get(
        (canvas_edge.from_agent_id, canvas_edge.to_agent_id)
    )
    return WorkflowCanvasStateEdgeResponse(
        edge_kind=canvas_edge.edge_kind,
        from_agent_id=canvas_edge.from_agent_id,
        gate_required=graph_edge.gate_required if graph_edge is not None else False,
        gate_status=graph_edge.gate_status if graph_edge is not None else "not_required",
        label=canvas_edge.label,
        source_stage_id=graph_edge.source_stage_id if graph_edge is not None else None,
        target_stage_id=graph_edge.target_stage_id if graph_edge is not None else None,
        to_agent_id=canvas_edge.to_agent_id,
    )


def first_next_action(
    nodes: tuple[WorkflowCanvasStateNodeResponse, ...],
) -> WorkflowCanvasStateNodeResponse | None:
    for node in nodes:
        if node.can_run:
            return node
    return None


def build_workflow_canvas_state(graph: WorkflowGraphResponse) -> WorkflowCanvasStateResponse:
    context = CanvasStateBuildContext(
        graph=graph,
        graph_edges_by_agent_pair={
            (edge.source_agent_id, edge.target_agent_id): edge for edge in graph.edges
        },
        graph_nodes_by_agent_id={node.agent_id: node for node in graph.nodes},
    )
    nodes = tuple(build_canvas_state_node(node, context) for node in CANVAS_NODES)
    edges = tuple(build_canvas_state_edge(edge, context) for edge in CANVAS_EDGES)
    next_action = first_next_action(nodes)
    return WorkflowCanvasStateResponse(
        edges=edges,
        lanes=CANVAS_LANES,
        next_action_agent_id=next_action.agent_id if next_action is not None else None,
        next_action_stage_id=next_action.stage_id if next_action is not None else None,
        nodes=nodes,
        planned_node_count=sum(
            node.implementation_status == "planned_extension" for node in nodes
        ),
        quest=graph.quest,
        runnable_node_count=sum(node.can_run for node in nodes),
        stage_node_count=sum(node.implementation_status == "implemented_stage" for node in nodes),
        total_node_count=len(nodes),
    )


@router.get("/quests/{quest_id}/workflow-canvas-state", response_model=WorkflowCanvasStateResponse)
def get_quest_workflow_canvas_state(
    quest_id: str,
    context: Annotated[StageReadinessRequestContext, Depends(get_stage_readiness_context)],
) -> WorkflowCanvasStateResponse:
    service = QuestService(context.session)
    try:
        quest = service.get_quest_for_user(quest_id, context.current_user)
        graph = build_workflow_graph(quest, service.list_stage_cards(quest.id), context)
        return build_workflow_canvas_state(graph)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
