from fastapi.testclient import TestClient

from noviscope.api.workflow_canvas import get_workflow_canvas_template
from noviscope.main import create_app


def test_workflow_canvas_template_exposes_agent_nodes_and_edges() -> None:
    # Given: the default NoviScope workflow canvas contract.

    # When: the frontend requests the default workflow canvas template.
    body = get_workflow_canvas_template()

    # Then: the response can render the research team graph without guessing.
    assert body.entry_agent_id == "demand_validator"
    assert body.terminal_agent_id == "paper_meeting_writer"
    assert body.core_flow_agent_ids == (
        "demand_validator",
        "literature_scout",
        "idea_generator",
        "experiment_planner",
        "paper_meeting_writer",
    )
    assert len(body.nodes) == 9
    assert body.nodes[0].model_dump(mode="json") == {
        "agent_id": "demand_validator",
        "canvas_role": "core_stage",
        "column": 1,
        "display_name": "Demand Validator",
        "lane_id": "validation",
        "row": 1,
    }
    edge_payloads = [edge.model_dump(mode="json") for edge in body.edges]
    assert {
        "edge_kind": "human_gate",
        "from_agent_id": "demand_validator",
        "label": "Demand review gate",
        "to_agent_id": "literature_scout",
    } in edge_payloads
    assert {
        "edge_kind": "planned_extension",
        "from_agent_id": "experiment_planner",
        "label": "Future automated execution",
        "to_agent_id": "code_runner",
    } in edge_payloads
    assert [lane.model_dump(mode="json") for lane in body.lanes] == [
        {
            "description": "Demand reality checks and problem framing.",
            "lane_id": "validation",
            "title": "Validation",
        },
        {
            "description": "Literature, gaps, hypotheses, and idea selection.",
            "lane_id": "research",
            "title": "Research",
        },
        {
            "description": "Experiment planning, future code runs, and evidence audits.",
            "lane_id": "experiment",
            "title": "Experiment",
        },
        {
            "description": "Traceable paper and meeting artifacts.",
            "lane_id": "artifact",
            "title": "Artifact",
        },
    ]


def test_workflow_canvas_template_endpoint_exposes_frontend_contract(tmp_path) -> None:
    app = create_app(database_url=f"sqlite:///{tmp_path / 'workflow-canvas.db'}")

    with TestClient(app) as client:
        # Given: the NoviScope API is running with the default workflow canvas.

        # When: the frontend requests the static canvas template.
        response = client.get("/workflow/canvas-template")

    # Then: the endpoint returns layout lanes, nodes, and edges without auth-specific state.
    assert response.status_code == 200
    body = response.json()
    assert body["entry_agent_id"] == "demand_validator"
    assert body["terminal_agent_id"] == "paper_meeting_writer"
    assert len(body["nodes"]) == 9
    assert len(body["edges"]) == 11
    assert body["nodes"][6] == {
        "agent_id": "code_runner",
        "canvas_role": "planned_extension",
        "column": 5,
        "display_name": "Code Runner",
        "lane_id": "experiment",
        "row": 2,
    }
