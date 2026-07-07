from fastapi.testclient import TestClient

from noviscope.core.stage_policy import (
    DEMAND_VALIDATOR_AGENT_ID,
    EXPERIMENT_PLANNER_AGENT_ID,
    IDEA_GENERATOR_AGENT_ID,
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


def create_quest_with_stage_ids(client: TestClient) -> tuple[str, dict[str, str]]:
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
    return quest_id, {
        stage["agent_id"]: stage["id"] for stage in stages_response.json()["stages"]
    }


def complete_demand_review(client: TestClient, stage_id: str) -> None:
    running_response = client.patch(f"/stages/{stage_id}", json={"status": "running"})
    assert running_response.status_code == 200
    complete_response = client.patch(
        f"/stages/{stage_id}",
        json={
            "output_payload": {
                "confidence": "medium",
                "demand_assessment": "plausible",
                "summary": "Badminton training feedback is a plausible demand.",
            },
            "status": "complete",
        },
    )
    assert complete_response.status_code == 200
    review_response = client.post(
        f"/stages/{stage_id}/demand-review",
        json={
            "review_notes": "Confirmed with a coach-facing training workflow.",
            "sources": ["Coach interview notes 2026-07-07"],
            "verdict": "plausible",
        },
    )
    assert review_response.status_code == 200


def complete_idea_selection(client: TestClient, stage_id: str) -> None:
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
                    }
                ],
                "selection_status": "pending_human_selection",
            },
            "status": "complete",
        },
    )
    assert complete_response.status_code == 200
    selection_response = client.post(
        f"/stages/{stage_id}/select-ideas",
        json={
            "review_notes": "Use temporal cues for the first experiment plan.",
            "selected_idea_ids": ["idea_temporal_cues"],
        },
    )
    assert selection_response.status_code == 200


def record_experiment_setup(client: TestClient, stage_id: str) -> None:
    setup_response = client.post(
        f"/stages/{stage_id}/experiment-setup",
        json={
            "code_repository": "https://github.com/example/badminton-baseline",
            "data_path": "/data/badminton/videos",
            "environment_notes": "A800 CUDA environment, Python 3.12.",
        },
    )
    assert setup_response.status_code == 200


def complete_experiment_plan(client: TestClient, stage_id: str, approved: bool | None) -> None:
    running_response = client.patch(f"/stages/{stage_id}", json={"status": "running"})
    assert running_response.status_code == 200
    complete_response = client.patch(
        f"/stages/{stage_id}",
        json={
            "human_approved": approved,
            "output_payload": {
                "baselines_to_reproduce": ["Pose-based action classifier"],
                "confidence": "medium",
                "datasets_needed": ["Badminton training videos"],
                "first_runnable_script_plan": "Run train.py with the recorded data path.",
                "metrics": ["top-1 accuracy", "frame consistency"],
                "summary": "Experiment plan is ready for human-controlled execution.",
            },
            "review_notes": "Plan reviewed for a first run." if approved is True else "",
            "status": "complete",
        },
    )
    assert complete_response.status_code == 200


def check_statuses(body: dict) -> dict[str, str]:
    return {check["key"]: check["status"] for check in body["checks"]}


def test_experiment_gate_blocks_new_quest(
    tmp_path,
    dev_admin_header_enabled: None,
) -> None:
    app = create_app(database_url=f"sqlite:///{tmp_path / 'experiment-gate-blocked.db'}")

    with TestClient(app) as client:
        register_and_login(client, "GATE-BLOCK", "gate-block@example.com")
        quest_id, _ = create_quest_with_stage_ids(client)

        response = client.get(f"/quests/{quest_id}/experiment-gate")

    assert response.status_code == 200
    body = response.json()
    assert body["gate_status"] == "blocked"
    assert body["ready_for_experiment"] is False
    assert check_statuses(body) == {
        "demand_validation": "blocked",
        "experiment_plan": "blocked",
        "experiment_setup": "blocked",
        "idea_selection": "blocked",
    }
    assert len(body["blocking_reasons"]) == 4


def test_experiment_gate_is_ready_after_required_reviews(
    tmp_path,
    dev_admin_header_enabled: None,
) -> None:
    app = create_app(database_url=f"sqlite:///{tmp_path / 'experiment-gate-ready.db'}")

    with TestClient(app) as client:
        register_and_login(client, "GATE-READY", "gate-ready@example.com")
        quest_id, stage_ids = create_quest_with_stage_ids(client)
        complete_demand_review(client, stage_ids[DEMAND_VALIDATOR_AGENT_ID])
        complete_idea_selection(client, stage_ids[IDEA_GENERATOR_AGENT_ID])
        record_experiment_setup(client, stage_ids[EXPERIMENT_PLANNER_AGENT_ID])
        complete_experiment_plan(client, stage_ids[EXPERIMENT_PLANNER_AGENT_ID], True)

        response = client.get(f"/quests/{quest_id}/experiment-gate")

    assert response.status_code == 200
    body = response.json()
    assert body["gate_status"] == "ready"
    assert body["ready_for_experiment"] is True
    assert set(check_statuses(body).values()) == {"pass"}
    assert body["blocking_reasons"] == []


def test_experiment_gate_requires_human_plan_review(
    tmp_path,
    dev_admin_header_enabled: None,
) -> None:
    app = create_app(database_url=f"sqlite:///{tmp_path / 'experiment-gate-review.db'}")

    with TestClient(app) as client:
        register_and_login(client, "GATE-REVIEW", "gate-review@example.com")
        quest_id, stage_ids = create_quest_with_stage_ids(client)
        complete_demand_review(client, stage_ids[DEMAND_VALIDATOR_AGENT_ID])
        complete_idea_selection(client, stage_ids[IDEA_GENERATOR_AGENT_ID])
        record_experiment_setup(client, stage_ids[EXPERIMENT_PLANNER_AGENT_ID])
        complete_experiment_plan(client, stage_ids[EXPERIMENT_PLANNER_AGENT_ID], None)

        response = client.get(f"/quests/{quest_id}/experiment-gate")

    assert response.status_code == 200
    body = response.json()
    assert body["gate_status"] == "needs_review"
    assert body["ready_for_experiment"] is False
    assert check_statuses(body)["experiment_plan"] == "needs_review"
    assert body["blocking_reasons"] == ["Experiment plan is complete but needs human approval."]


def test_experiment_gate_rejects_other_users_quest(
    tmp_path,
    dev_admin_header_enabled: None,
) -> None:
    app = create_app(database_url=f"sqlite:///{tmp_path / 'experiment-gate-permission.db'}")

    with TestClient(app) as client:
        register_and_login(client, "GATE-OWNER", "gate-owner@example.com")
        quest_id, _ = create_quest_with_stage_ids(client)
        logout_response = client.post("/auth/logout")
        assert logout_response.status_code == 204
        register_and_login(client, "GATE-OTHER", "gate-other@example.com")

        response = client.get(f"/quests/{quest_id}/experiment-gate")

    assert response.status_code == 403
