from fastapi.testclient import TestClient

from noviscope.main import create_app

DEV_ADMIN_HEADERS = {"X-NoviScope-Dev-Admin": "test-dev-admin-token-0123456789abcdef"}


def register_and_login(client: TestClient) -> None:
    invite_response = client.post(
        "/admin/invites",
        headers=DEV_ADMIN_HEADERS,
        json={"code": "workflow-graph-invite", "max_uses": 1},
    )
    assert invite_response.status_code == 201

    register_response = client.post(
        "/auth/register",
        json={
            "display_name": "Workflow Tester",
            "email": "workflow@example.com",
            "invite_code": "workflow-graph-invite",
            "password": "password",
        },
    )
    assert register_response.status_code == 201

    login_response = client.post(
        "/auth/login",
        json={"email": "workflow@example.com", "password": "password"},
    )
    assert login_response.status_code == 200


def create_personal_provider(client: TestClient) -> dict[str, str]:
    response = client.post(
        "/providers",
        json={
            "api_key": "sk-test-workflow-graph",
            "base_url": "https://api.example.com/v1",
            "default_model": "example-chat",
            "kind": "openai_compatible",
            "name": "Example Provider",
            "scope": "personal",
        },
    )
    assert response.status_code == 201
    return response.json()


def test_get_quest_workflow_graph_returns_canvas_contract(
    dev_admin_header_enabled: None,
    tmp_path,
) -> None:
    app = create_app(database_url=f"sqlite:///{tmp_path / 'workflow-graph.db'}")
    with TestClient(app) as client:
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

        response = client.get(f"/quests/{quest_id}/workflow-graph")

    assert response.status_code == 200
    body = response.json()
    assert body["quest"]["id"] == quest_id
    assert body["quest"]["title"] == "Handwritten text erasure"
    assert [node["agent_id"] for node in body["nodes"]] == [
        "demand_validator",
        "literature_scout",
        "idea_generator",
        "experiment_planner",
        "paper_meeting_writer",
    ]
    assert body["nodes"][0]["order"] == 1
    assert body["nodes"][0]["can_run"] is False
    assert body["nodes"][0]["blocking_reason"] == "missing_provider"
    assert body["nodes"][0]["provider_id"] is None
    assert body["nodes"][0]["human_review_required"] is True
    assert body["nodes"][1]["can_run"] is False
    assert body["nodes"][1]["blocking_reason"] == "demand_validation_incomplete"
    assert [(edge["source_agent_id"], edge["target_agent_id"]) for edge in body["edges"]] == [
        ("demand_validator", "literature_scout"),
        ("demand_validator", "idea_generator"),
        ("literature_scout", "idea_generator"),
        ("idea_generator", "experiment_planner"),
        ("experiment_planner", "paper_meeting_writer"),
    ]
    assert body["edges"][0]["gate_required"] is True
    assert body["edges"][0]["gate_status"] == "waiting_for_completion"
    assert body["edges"][2]["gate_required"] is False
    assert body["edges"][2]["gate_status"] == "not_required"


def test_get_quest_workflow_graph_reports_selected_provider(
    dev_admin_header_enabled: None,
    tmp_path,
) -> None:
    app = create_app(database_url=f"sqlite:///{tmp_path / 'workflow-graph-provider.db'}")
    with TestClient(app) as client:
        register_and_login(client)
        provider = create_personal_provider(client)
        create_response = client.post(
            "/quests",
            json={
                "initial_direction": "Use computer vision for badminton training.",
                "title": "Badminton training",
            },
        )
        assert create_response.status_code == 201
        quest_id = create_response.json()["id"]

        response = client.get(f"/quests/{quest_id}/workflow-graph")

    assert response.status_code == 200
    first_node = response.json()["nodes"][0]
    assert first_node["can_run"] is True
    assert first_node["blocking_reason"] == ""
    assert first_node["provider_id"] == provider["id"]
    assert first_node["provider_kind"] == "openai_compatible"
    assert first_node["provider_model"] == "example-chat"
    assert first_node["provider_name"] == "Example Provider"
    assert first_node["next_human_action"] == "run_stage"
    assert "sk-test-workflow-graph" not in str(first_node)


def test_get_quest_workflow_graph_reports_next_human_action_for_demand_review(
    dev_admin_header_enabled: None,
    tmp_path,
) -> None:
    app = create_app(database_url=f"sqlite:///{tmp_path / 'workflow-graph-action.db'}")
    with TestClient(app) as client:
        # Given: Demand Validation has completed but still waits for human review.
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
        stages_response = client.get(f"/quests/{quest_id}/stages")
        assert stages_response.status_code == 200
        demand_stage = next(
            stage
            for stage in stages_response.json()["stages"]
            if stage["agent_id"] == "demand_validator"
        )
        running_response = client.patch(
            f"/stages/{demand_stage['id']}",
            json={"status": "running"},
        )
        assert running_response.status_code == 200
        complete_response = client.patch(
            f"/stages/{demand_stage['id']}",
            json={
                "evidence_payload": {"requires_human_review": True},
                "output_payload": {
                    "confidence": "medium",
                    "demand_assessment": "plausible",
                    "evidence_for_demand": [
                        "The task names a concrete document cleanup workflow."
                    ],
                    "missing_evidence": ["Need a real customer or dataset proof point."],
                    "risks": ["Demand source still needs external verification."],
                    "summary": "Demand is plausible but needs human review.",
                },
                "status": "complete",
                "summary": "Demand is plausible but needs human review.",
            },
        )
        assert complete_response.status_code == 200, complete_response.text

        # When: the frontend requests the workflow graph for the Quest canvas.
        response = client.get(f"/quests/{quest_id}/workflow-graph")

    # Then: the demand node tells the Canvas which human action to surface.
    assert response.status_code == 200
    demand_node = next(
        node for node in response.json()["nodes"] if node["agent_id"] == "demand_validator"
    )
    assert demand_node["review_state"] == "pending_review"
    assert demand_node["next_human_action"] == "review_demand"


def test_get_quest_workflow_graph_requires_authentication(tmp_path) -> None:
    app = create_app(database_url=f"sqlite:///{tmp_path / 'workflow-graph-auth.db'}")
    with TestClient(app) as client:
        response = client.get("/quests/quest_missing/workflow-graph")

    assert response.status_code == 401
