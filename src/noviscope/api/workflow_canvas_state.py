from typing import Annotated

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
    CORE_FLOW_AGENT_IDS,
    CanvasEdgeResponse,
    CanvasLaneResponse,
    CanvasNodeResponse,
)
from noviscope.api.workflow_graph import (
    WorkflowEdgeResponse,
    WorkflowNodeResponse,
    WorkflowQuestResponse,
    build_workflow_graph,
)
from noviscope.core.stage_policy import (
    DEMAND_VALIDATOR_AGENT_ID,
    PAPER_MEETING_WRITER_AGENT_ID,
)
from noviscope.models.quest import Quest, StageCard
from noviscope.quests.service import QuestService

router = APIRouter()
EdgeKey = tuple[str, str]


class WorkflowCanvasStateNodeResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    is_planned: bool
    layout: CanvasNodeResponse
    stage: WorkflowNodeResponse | None


class WorkflowCanvasStateEdgeResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    layout: CanvasEdgeResponse
    workflow_edge: WorkflowEdgeResponse | None


class WorkflowCanvasStateResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    core_flow_agent_ids: tuple[str, ...]
    edges: list[WorkflowCanvasStateEdgeResponse]
    entry_agent_id: str
    lanes: tuple[CanvasLaneResponse, ...]
    nodes: list[WorkflowCanvasStateNodeResponse]
    quest: WorkflowQuestResponse
    terminal_agent_id: str


def build_workflow_canvas_state(
    quest: Quest,
    stages: list[StageCard],
    context: StageReadinessRequestContext,
) -> WorkflowCanvasStateResponse:
    workflow_graph = build_workflow_graph(quest, stages, context)
    nodes_by_agent_id = {node.agent_id: node for node in workflow_graph.nodes}
    edges_by_agent_pair = {
        edge_key(edge.source_agent_id, edge.target_agent_id): edge
        for edge in workflow_graph.edges
    }
    return WorkflowCanvasStateResponse(
        core_flow_agent_ids=CORE_FLOW_AGENT_IDS,
        edges=[
            build_canvas_state_edge(edge, edges_by_agent_pair) for edge in CANVAS_EDGES
        ],
        entry_agent_id=DEMAND_VALIDATOR_AGENT_ID,
        lanes=CANVAS_LANES,
        nodes=[build_canvas_state_node(node, nodes_by_agent_id) for node in CANVAS_NODES],
        quest=workflow_graph.quest,
        terminal_agent_id=PAPER_MEETING_WRITER_AGENT_ID,
    )


def build_canvas_state_node(
    layout: CanvasNodeResponse,
    nodes_by_agent_id: dict[str, WorkflowNodeResponse],
) -> WorkflowCanvasStateNodeResponse:
    stage = nodes_by_agent_id.get(layout.agent_id)
    return WorkflowCanvasStateNodeResponse(
        is_planned=stage is None,
        layout=layout,
        stage=stage,
    )


def build_canvas_state_edge(
    layout: CanvasEdgeResponse,
    edges_by_agent_pair: dict[EdgeKey, WorkflowEdgeResponse],
) -> WorkflowCanvasStateEdgeResponse:
    return WorkflowCanvasStateEdgeResponse(
        layout=layout,
        workflow_edge=edges_by_agent_pair.get(
            edge_key(layout.from_agent_id, layout.to_agent_id)
        ),
    )


def edge_key(from_agent_id: str, to_agent_id: str) -> EdgeKey:
    return (from_agent_id, to_agent_id)


@router.get("/quests/{quest_id}/workflow-canvas", response_model=WorkflowCanvasStateResponse)
def get_quest_workflow_canvas_state(
    quest_id: str,
    context: Annotated[StageReadinessRequestContext, Depends(get_stage_readiness_context)],
) -> WorkflowCanvasStateResponse:
    service = QuestService(context.session)
    try:
        quest = service.get_quest_for_user(quest_id, context.current_user)
        return build_workflow_canvas_state(quest, service.list_stage_cards(quest.id), context)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
