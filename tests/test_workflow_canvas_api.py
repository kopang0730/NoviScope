from fastapi.testclient import TestClient

from noviscope.api.workflow_canvas import get_workflow_canvas_template
from noviscope.main import create_app

DEV_ADMIN_HEADERS = {"X-NoviScope-Dev-Admin": "test-dev-admin-token-0123456789abcdef"}


def register_and_login(client: TestClient) -> None:
    invite_response = client.post(
        "/admin/invites",
        headers=DEV_ADMIN_HEADERS,
        json={"code": "workflow-canvas-state-invite", "max_uses": 1},
    )
    assert invite_response.status_code == 201

    register_response = client.post(
        "/auth/register",
        json={
            "display_name": "Canvas Tester",
            "email": "canvas@example.com",
            "invite_code": "workflow-canvas-state-invite",
            "password": "password",
        },
    )
    assert register_response.status_code == 201

    login_response = client.post(
        "/auth/login",
        json={"email": "canvas@example.com", "password": "password"},
    )
    assert login_response.status_code == 200


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


def test_quest_workflow_canvas_state_merges_layout_with_stage_state(
    dev_admin_header_enabled: None,
    tmp_path,
) -> None:
    app = create_app(database_url=f"sqlite:///{tmp_path / 'workflow-canvas-state.db'}")

    with TestClient(app) as client:
        # Given: a user has created a Quest with the default research workflow stages.
        register_and_login(client)
        create_response = client.post(
            "/quests",
            json={
                "initial_direction": "Use computer vision to erase handwritten text.",
                "title": "Handwritten text erasure",
            },
        )
        assert create_response.status_code == 201
        quest_id = create_response.json()["id"]

        # When: the frontend requests the render-ready canvas state.
        response = client.get(f"/quests/{quest_id}/workflow-canvas")

    # Then: layout, dynamic stage state, and planned extension nodes are in one payload.
    assert response.status_code == 200
    body = response.json()
    assert body["quest"]["id"] == quest_id
    assert len(body["lanes"]) == 4
    assert len(body["nodes"]) == 9
    demand_node = next(
        node for node in body["nodes"] if node["layout"]["agent_id"] == "demand_validator"
    )
    assert demand_node["is_planned"] is False
    assert demand_node["layout"]["column"] == 1
    assert demand_node["stage"]["agent_id"] == "demand_validator"
    assert demand_node["stage"]["can_run"] is False
    assert demand_node["stage"]["blocking_reason"] == "missing_provider"
    code_runner_node = next(
        node for node in body["nodes"] if node["layout"]["agent_id"] == "code_runner"
    )
    assert code_runner_node["is_planned"] is True
    assert code_runner_node["stage"] is None
    first_gate = next(
        edge
        for edge in body["edges"]
        if edge["layout"]["from_agent_id"] == "demand_validator"
        and edge["layout"]["to_agent_id"] == "literature_scout"
    )
    assert first_gate["workflow_edge"]["gate_status"] == "waiting_for_completion"
    planned_edge = next(
        edge
        for edge in body["edges"]
        if edge["layout"]["from_agent_id"] == "experiment_planner"
        and edge["layout"]["to_agent_id"] == "code_runner"
    )
    assert planned_edge["workflow_edge"] is None


def test_quest_workflow_canvas_state_requires_authentication(tmp_path) -> None:
    app = create_app(database_url=f"sqlite:///{tmp_path / 'workflow-canvas-state-auth.db'}")

    with TestClient(app) as client:
        # Given: no user session is authenticated.

        # When: the frontend requests a Quest-specific workflow canvas state.
        response = client.get("/quests/quest_missing/workflow-canvas")

    # Then: Quest stage state is not exposed anonymously.
    assert response.status_code == 401
