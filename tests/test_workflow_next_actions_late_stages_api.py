from fastapi.testclient import TestClient

from noviscope.agents.literature_scout import LITERATURE_SCOUT_AGENT_ID
from noviscope.core.json_types import JsonObject
from noviscope.core.stage_policy import (
    DEMAND_VALIDATOR_AGENT_ID,
    EXPERIMENT_PLANNER_AGENT_ID,
    IDEA_GENERATOR_AGENT_ID,
    PAPER_MEETING_WRITER_AGENT_ID,
)
from noviscope.main import create_app

DEV_ADMIN_HEADERS = {"X-NoviScope-Dev-Admin": "test-dev-admin-token-0123456789abcdef"}


def register_and_login(client: TestClient, invite_code: str, email: str) -> None:
    invite_response = client.post(
        "/admin/invites",
        headers=DEV_ADMIN_HEADERS,
        json={"code": invite_code, "max_uses": 1},
    )
    assert invite_response.status_code == 201
    register_response = client.post(
        "/auth/register",
        json={
            "display_name": email.split("@")[0],
            "email": email,
            "invite_code": invite_code,
            "password": "password",
        },
    )
    assert register_response.status_code == 201
    login_response = client.post("/auth/login", json={"email": email, "password": "password"})
    assert login_response.status_code == 200


def create_personal_provider(client: TestClient) -> None:
    response = client.post(
        "/providers",
        json={
            "api_key": "sk-test-next-actions-late",
            "base_url": "https://api.example.com/v1",
            "default_model": "example-chat",
            "kind": "openai_compatible",
            "name": "Example Provider",
            "scope": "personal",
        },
    )
    assert response.status_code == 201


def create_quest(client: TestClient) -> str:
    response = client.post(
        "/quests",
        json={
            "initial_direction": "Use computer vision to erase handwritten text.",
            "title": "Handwritten text erasure",
        },
    )
    assert response.status_code == 201
    return response.json()["id"]


def stage_id_for_agent(client: TestClient, quest_id: str, agent_id: str) -> str:
    stages_response = client.get(f"/quests/{quest_id}/stages")
    assert stages_response.status_code == 200
    stage = next(
        stage
        for stage in stages_response.json()["stages"]
        if stage["agent_id"] == agent_id
    )
    return stage["id"]


def update_stage(client: TestClient, stage_id: str, payload: JsonObject) -> None:
    response = client.patch(f"/stages/{stage_id}", json=payload)
    assert response.status_code == 200


def mark_stage_running(client: TestClient, stage_id: str) -> None:
    update_stage(client, stage_id, {"status": "running"})


def approve_demand_stage(client: TestClient, stage_id: str) -> None:
    mark_stage_running(client, stage_id)
    update_stage(
        client,
        stage_id,
        {
            "output_payload": {"confidence": "medium", "demand_assessment": "plausible"},
            "status": "complete",
            "summary": "Demand is plausible.",
        },
    )
    response = client.post(
        f"/stages/{stage_id}/demand-review",
        json={
            "review_notes": "Verified customer demand.",
            "sources": ["Customer worksheet reuse interview"],
            "verdict": "verified",
        },
    )
    assert response.status_code == 200


def complete_literature_stage(client: TestClient, stage_id: str) -> None:
    mark_stage_running(client, stage_id)
    update_stage(
        client,
        stage_id,
        {
            "output_payload": {
                "papers": [{"paper_ref": "P1", "title": "Document cleanup benchmark"}],
                "source": "openalex_works_api",
            },
            "status": "complete",
            "summary": "Found one paper.",
        },
    )


def approve_idea_with_selected_ids_only(client: TestClient, stage_id: str) -> None:
    mark_stage_running(client, stage_id)
    update_stage(
        client,
        stage_id,
        {
            "human_approved": True,
            "output_payload": {
                "ideas": [{"idea_id": "idea-1", "idea_title": "Stroke-aware text erasure"}],
                "selected_idea_ids": ["idea-1"],
                "selection_status": "selected_for_experiment_design",
            },
            "review_notes": "Selected idea-1 for experiment design.",
            "status": "complete",
            "summary": "Selected one idea.",
        },
    )


def approve_idea_with_selected_payload(client: TestClient, stage_id: str) -> None:
    mark_stage_running(client, stage_id)
    update_stage(
        client,
        stage_id,
        {
            "human_approved": True,
            "output_payload": {
                "ideas": [{"idea_id": "idea-1", "idea_title": "Stroke-aware text erasure"}],
                "selected_idea_ids": ["idea-1"],
                "selected_ideas": [
                    {"idea_id": "idea-1", "idea_title": "Stroke-aware text erasure"}
                ],
                "selection_status": "selected_for_experiment_design",
            },
            "review_notes": "Selected idea-1 for experiment design.",
            "status": "complete",
            "summary": "Selected one idea.",
        },
    )


def add_experiment_setup_inputs(client: TestClient, stage_id: str) -> None:
    update_stage(
        client,
        stage_id,
        {
            "input_payload": {
                "code_repository": "https://github.com/example/text-erasure",
                "data_path": "/datasets/handwritten-erasure",
                "environment_notes": "Use the shared A800 environment.",
            },
        },
    )


def approve_experiment_plan(client: TestClient, stage_id: str) -> None:
    mark_stage_running(client, stage_id)
    update_stage(
        client,
        stage_id,
        {
            "human_approved": True,
            "output_payload": {"experiment_plan": "Baseline plus stroke-aware ablation."},
            "review_notes": "Experiment plan approved.",
            "status": "complete",
            "summary": "Experiment plan is ready for writing.",
        },
    )


def complete_unreviewed_paper_stage(client: TestClient, stage_id: str) -> None:
    mark_stage_running(client, stage_id)
    update_stage(
        client,
        stage_id,
        {
            "output_payload": {
                "human_review_required": ["Confirm no unsupported claims before sharing."],
                "ieee_paper_skeleton_markdown": "# Paper Skeleton",
            },
            "status": "complete",
            "summary": "Generated paper and meeting artifacts.",
        },
    )


def test_workflow_next_actions_runs_experiment_after_selected_idea_ids(
    tmp_path,
    dev_admin_header_enabled: None,
) -> None:
    app = create_app(database_url=f"sqlite:///{tmp_path / 'next-actions-selected-ids.db'}")
    with TestClient(app) as client:
        # Given: the frontend PATCH shape saved selected_idea_ids without selected_ideas.
        register_and_login(client, "NEXT-ACTIONS-IDEA", "next-actions-idea@example.com")
        create_personal_provider(client)
        quest_id = create_quest(client)
        demand_stage_id = stage_id_for_agent(client, quest_id, DEMAND_VALIDATOR_AGENT_ID)
        literature_stage_id = stage_id_for_agent(client, quest_id, LITERATURE_SCOUT_AGENT_ID)
        approve_demand_stage(client, demand_stage_id)
        complete_literature_stage(client, literature_stage_id)
        approve_idea_with_selected_ids_only(
            client,
            stage_id_for_agent(client, quest_id, IDEA_GENERATOR_AGENT_ID),
        )
        experiment_stage_id = stage_id_for_agent(client, quest_id, EXPERIMENT_PLANNER_AGENT_ID)
        add_experiment_setup_inputs(client, experiment_stage_id)

        # When: the workbench asks for the next workflow action.
        response = client.get(f"/quests/{quest_id}/workflow-next-actions")

    # Then: it skips idea re-review and offers to run Experiment Planner.
    assert response.status_code == 200
    action = response.json()["actions"][0]
    assert action["action_type"] == "run_stage"
    assert action["agent_id"] == EXPERIMENT_PLANNER_AGENT_ID
    assert action["stage_id"] == experiment_stage_id


def test_workflow_next_actions_surfaces_final_paper_review(
    tmp_path,
    dev_admin_header_enabled: None,
) -> None:
    app = create_app(database_url=f"sqlite:///{tmp_path / 'next-actions-paper-review.db'}")
    with TestClient(app) as client:
        # Given: every prerequisite is complete and paper artifacts await human review.
        register_and_login(client, "NEXT-ACTIONS-PAPER", "next-actions-paper@example.com")
        create_personal_provider(client)
        quest_id = create_quest(client)
        demand_stage_id = stage_id_for_agent(client, quest_id, DEMAND_VALIDATOR_AGENT_ID)
        literature_stage_id = stage_id_for_agent(client, quest_id, LITERATURE_SCOUT_AGENT_ID)
        experiment_stage_id = stage_id_for_agent(client, quest_id, EXPERIMENT_PLANNER_AGENT_ID)
        approve_demand_stage(client, demand_stage_id)
        complete_literature_stage(client, literature_stage_id)
        approve_idea_with_selected_payload(
            client,
            stage_id_for_agent(client, quest_id, IDEA_GENERATOR_AGENT_ID),
        )
        approve_experiment_plan(client, experiment_stage_id)
        paper_stage_id = stage_id_for_agent(client, quest_id, PAPER_MEETING_WRITER_AGENT_ID)
        complete_unreviewed_paper_stage(client, paper_stage_id)

        # When: the workbench asks for the next workflow action.
        response = client.get(f"/quests/{quest_id}/workflow-next-actions")

    # Then: the terminal paper artifacts are surfaced for human review.
    assert response.status_code == 200
    action = response.json()["actions"][0]
    assert action["action_type"] == "review_stage"
    assert action["agent_id"] == PAPER_MEETING_WRITER_AGENT_ID
    assert action["stage_id"] == paper_stage_id
