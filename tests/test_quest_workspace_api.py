from typing import TypedDict

from fastapi.testclient import TestClient

from noviscope.core.json_types import JsonObject
from noviscope.core.stage_policy import (
    DEMAND_VALIDATOR_AGENT_ID,
    PAPER_MEETING_WRITER_AGENT_ID,
)
from noviscope.main import create_app

DEV_ADMIN_HEADERS = {"X-NoviScope-Dev-Admin": "test-dev-admin-token-0123456789abcdef"}


class WorkspaceStageItem(TypedDict):
    artifact_manifest: JsonObject | None
    card: JsonObject
    display_output: JsonObject


class WorkspaceBody(TypedDict):
    canvas_template: JsonObject
    quest: JsonObject
    stages: list[WorkspaceStageItem]


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


def create_workspace_quest(client: TestClient) -> tuple[str, dict[str, str]]:
    quest_response = client.post(
        "/quests",
        json={
            "initial_direction": "Use computer vision for badminton action recognition.",
            "title": "Badminton action recognition",
        },
    )
    assert quest_response.status_code == 201
    quest_id = quest_response.json()["id"]
    stages_response = client.get(f"/quests/{quest_id}/stages")
    assert stages_response.status_code == 200
    stage_ids = {
        stage["agent_id"]: stage["id"] for stage in stages_response.json()["stages"]
    }
    return quest_id, stage_ids


def complete_demand_stage_with_raw_response(client: TestClient, stage_id: str) -> None:
    running_response = client.patch(f"/stages/{stage_id}", json={"status": "running"})
    assert running_response.status_code == 200
    complete_response = client.patch(
        f"/stages/{stage_id}",
        json={
            "output_payload": {
                "confidence": "medium",
                "evidence_for_demand": ["Coaches need repeatable badminton feedback."],
                "raw_response": "provider trace hidden from workspace panels",
                "summary": "Demand is plausible and needs human review.",
            },
            "status": "complete",
            "summary": "Demand is plausible and needs human review.",
        },
    )
    assert complete_response.status_code == 200


def complete_paper_stage_with_artifacts(client: TestClient, stage_id: str) -> None:
    running_response = client.patch(f"/stages/{stage_id}", json={"status": "running"})
    assert running_response.status_code == 200
    complete_response = client.patch(
        f"/stages/{stage_id}",
        json={
            "output_payload": {
                "chinese_research_brief_markdown": "# 中文研究 Brief",
                "confidence": "medium",
                "english_research_brief_markdown": "# Research Brief",
                "ieee_paper_skeleton_markdown": "# IEEE Paper Skeleton",
                "meeting_outline_markdown": "# Group Meeting Outline",
                "summary": "Generated traceable Markdown artifacts.",
            },
            "status": "complete",
        },
    )
    assert complete_response.status_code == 200


def stage_workspace_item(body: WorkspaceBody, agent_id: str) -> WorkspaceStageItem:
    return next(stage for stage in body["stages"] if stage["card"]["agent_id"] == agent_id)


def test_get_quest_workspace_returns_stage_outputs_and_unavailable_artifacts(
    tmp_path,
    dev_admin_header_enabled: None,
) -> None:
    app = create_app(database_url=f"sqlite:///{tmp_path / 'quest-workspace.db'}")

    with TestClient(app) as client:
        # Given
        register_and_login(client, "WORKSPACE", "workspace@example.com")
        quest_id, stage_ids = create_workspace_quest(client)
        complete_demand_stage_with_raw_response(
            client,
            stage_ids[DEMAND_VALIDATOR_AGENT_ID],
        )

        # When
        response = client.get(f"/quests/{quest_id}/workspace")

    # Then
    assert response.status_code == 200
    body: WorkspaceBody = response.json()
    assert body["quest"]["id"] == quest_id
    assert body["canvas_template"]["entry_agent_id"] == DEMAND_VALIDATOR_AGENT_ID
    assert len(body["stages"]) == 5
    demand_stage = stage_workspace_item(body, DEMAND_VALIDATOR_AGENT_ID)
    assert demand_stage["display_output"]["output_available"] is True
    assert demand_stage["display_output"]["raw_response_available"] is True
    assert "raw_response" not in demand_stage["display_output"]["display_payload"]
    assert demand_stage["artifact_manifest"] is None
    paper_stage = stage_workspace_item(body, PAPER_MEETING_WRITER_AGENT_ID)
    assert paper_stage["display_output"]["output_available"] is False
    artifact_manifest = paper_stage["artifact_manifest"]
    assert artifact_manifest is not None
    assert {artifact["available"] for artifact in artifact_manifest["artifacts"]} == {False}


def test_get_quest_workspace_marks_completed_paper_artifacts_available(
    tmp_path,
    dev_admin_header_enabled: None,
) -> None:
    app = create_app(database_url=f"sqlite:///{tmp_path / 'quest-workspace-artifacts.db'}")

    with TestClient(app) as client:
        # Given
        register_and_login(client, "WORKSPACE-ARTIFACTS", "workspace-artifacts@example.com")
        quest_id, stage_ids = create_workspace_quest(client)
        complete_paper_stage_with_artifacts(
            client,
            stage_ids[PAPER_MEETING_WRITER_AGENT_ID],
        )

        # When
        response = client.get(f"/quests/{quest_id}/workspace")

    # Then
    assert response.status_code == 200
    body: WorkspaceBody = response.json()
    paper_stage = stage_workspace_item(body, PAPER_MEETING_WRITER_AGENT_ID)
    artifacts = paper_stage["artifact_manifest"]["artifacts"]
    assert [artifact["key"] for artifact in artifacts] == [
        "chinese_research_brief_markdown",
        "english_research_brief_markdown",
        "meeting_outline_markdown",
        "ieee_paper_skeleton_markdown",
    ]
    assert {artifact["available"] for artifact in artifacts} == {True}
    assert artifacts[0]["download_url"] == (
        f"/stages/{stage_ids[PAPER_MEETING_WRITER_AGENT_ID]}/artifacts/"
        "chinese_research_brief_markdown/download"
    )


def test_get_quest_workspace_rejects_other_user(
    tmp_path,
    dev_admin_header_enabled: None,
) -> None:
    app = create_app(database_url=f"sqlite:///{tmp_path / 'quest-workspace-permission.db'}")

    with TestClient(app) as client:
        # Given
        register_and_login(client, "WORKSPACE-OWNER", "workspace-owner@example.com")
        quest_id, _stage_ids = create_workspace_quest(client)
        logout_response = client.post("/auth/logout")
        assert logout_response.status_code == 204
        register_and_login(client, "WORKSPACE-OTHER", "workspace-other@example.com")

        # When
        response = client.get(f"/quests/{quest_id}/workspace")

    # Then
    assert response.status_code == 403
