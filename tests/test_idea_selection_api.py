from fastapi.testclient import TestClient

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


def create_quest_with_idea_stage(client: TestClient) -> str:
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
    stages = stages_response.json()["stages"]
    idea_stage = next(stage for stage in stages if stage["agent_id"] == "idea_generator")
    return idea_stage["id"]


def complete_idea_stage(client: TestClient, stage_id: str) -> None:
    running_response = client.patch(f"/stages/{stage_id}", json={"status": "running"})
    assert running_response.status_code == 200
    complete_response = client.patch(
        f"/stages/{stage_id}",
        json={
            "output_payload": {
                "confidence": "medium",
                "ideas": [
                    {
                        "application_value": "Coach-facing training feedback.",
                        "based_on_which_papers": ["paper-1"],
                        "confidence": "medium",
                        "core_hypothesis": "Temporal cues improve recognition.",
                        "expected_improvement": "Better frame-level stability.",
                        "experiment_feasibility": "medium",
                        "idea_id": "idea_temporal_cues",
                        "idea_title": "Temporal cue badminton action recognition",
                        "novelty_risk": "medium",
                        "required_baseline": "Pose-based action classifier",
                        "required_data": "Badminton training videos",
                    },
                    {
                        "application_value": "Shuttle tracking analytics.",
                        "based_on_which_papers": ["paper-2"],
                        "confidence": "medium",
                        "core_hypothesis": "Trajectory smoothing improves tracking.",
                        "expected_improvement": "Lower localization jitter.",
                        "experiment_feasibility": "medium",
                        "idea_id": "idea_trajectory_smoothing",
                        "idea_title": "Trajectory smoothing",
                        "novelty_risk": "medium",
                        "required_baseline": "Shuttle detector",
                        "required_data": "Court videos",
                    },
                ],
                "selected_idea_ids": [],
                "selection_status": "pending_human_selection",
                "summary": "Generated two ideas for human review.",
            },
            "status": "complete",
        },
    )
    assert complete_response.status_code == 200


def test_select_ideas_marks_gap_stage_human_approved(
    tmp_path,
    dev_admin_header_enabled: None,
) -> None:
    app = create_app(database_url=f"sqlite:///{tmp_path / 'idea-selection.db'}")
    with TestClient(app) as client:
        register_and_login(client, "IDEA-SELECT", "idea-selector@example.com")
        idea_stage_id = create_quest_with_idea_stage(client)
        complete_idea_stage(client, idea_stage_id)

        response = client.post(
            f"/stages/{idea_stage_id}/select-ideas",
            json={
                "review_notes": "Use the temporal cue idea for the first experiment plan.",
                "selected_idea_ids": ["idea_temporal_cues"],
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["agent_id"] == "idea_generator"
    assert body["status"] == "complete"
    assert body["human_approved"] is True
    assert body["review_notes"] == "Use the temporal cue idea for the first experiment plan."
    assert body["output_payload"]["selected_idea_ids"] == ["idea_temporal_cues"]
    assert body["output_payload"]["selection_status"] == "selected_for_experiment"
    assert body["output_payload"]["selected_ideas"][0]["idea_id"] == "idea_temporal_cues"
    assert body["evidence_payload"]["human_selected_idea_ids"] == ["idea_temporal_cues"]
    assert body["evidence_payload"]["selected_idea_count"] == 1


def test_select_ideas_rejects_unknown_idea_id(
    tmp_path,
    dev_admin_header_enabled: None,
) -> None:
    app = create_app(database_url=f"sqlite:///{tmp_path / 'idea-selection-invalid.db'}")
    with TestClient(app) as client:
        register_and_login(client, "IDEA-INVALID", "idea-invalid@example.com")
        idea_stage_id = create_quest_with_idea_stage(client)
        complete_idea_stage(client, idea_stage_id)

        response = client.post(
            f"/stages/{idea_stage_id}/select-ideas",
            json={"selected_idea_ids": ["missing_idea"]},
        )

    assert response.status_code == 400
    assert response.json()["detail"] == "Selected idea ids were not generated by this stage."
