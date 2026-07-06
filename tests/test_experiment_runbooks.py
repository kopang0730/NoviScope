from fastapi.testclient import TestClient

from noviscope.core.json_types import JsonObject
from noviscope.core.stage_policy import EXPERIMENT_PLANNER_AGENT_ID
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


def create_quest_with_experiment_stage(client: TestClient) -> str:
    quest_response = client.post(
        "/quests",
        json={
            "initial_direction": "Use computer vision for badminton trajectory recognition.",
            "title": "Badminton trajectory recognition",
        },
    )
    assert quest_response.status_code == 201
    quest_id = quest_response.json()["id"]
    stages_response = client.get(f"/quests/{quest_id}/stages")
    assert stages_response.status_code == 200
    stages = stages_response.json()["stages"]
    experiment_stage = next(
        stage for stage in stages if stage["agent_id"] == EXPERIMENT_PLANNER_AGENT_ID
    )
    return experiment_stage["id"]


def experiment_plan_output() -> JsonObject:
    return {
        "ablation_variables": ["Temporal window", "Confidence threshold"],
        "baselines_to_reproduce": ["TrackNet shuttle trajectory baseline"],
        "compute_requirements": "One A800 GPU for the first reproducibility run.",
        "confidence": "medium",
        "data_availability_status": "ready",
        "datasets_needed": ["/data/badminton/train"],
        "expected_figures": ["Trajectory overlay qualitative examples"],
        "expected_tables": ["Baseline vs proposed comparison"],
        "failure_risks": ["Annotations may be noisy"],
        "first_runnable_script_plan": [
            "Create dataset manifest",
            "Run baseline inference",
        ],
        "metrics": ["Trajectory localization error", "Action classification accuracy"],
        "raw_response": "fake experiment plan response with no secret values",
        "source_stage_ids": {"idea_generator": "stage_idea"},
        "summary": "Plan baseline reproduction and ablations.",
        "warnings": ["No experiment has run. This output is an executable plan only."],
    }


def complete_experiment_stage(client: TestClient, stage_id: str) -> None:
    running_response = client.patch(f"/stages/{stage_id}", json={"status": "running"})
    assert running_response.status_code == 200
    complete_response = client.patch(
        f"/stages/{stage_id}",
        json={
            "evidence_payload": {
                "no_experiment_results": True,
                "plan_only": True,
                "requires_human_review": True,
            },
            "input_payload": {
                "code_repository": "https://github.com/example/badminton-baseline",
                "data_path": "/data/badminton/train",
                "environment_notes": "Python 3.11, CUDA 12.1, A800 GPU.",
            },
            "output_payload": experiment_plan_output(),
            "status": "complete",
            "summary": "Plan baseline reproduction and ablations.",
        },
    )
    assert complete_response.status_code == 200


def test_download_experiment_runbook_returns_plan_only_attachment(
    tmp_path,
    dev_admin_header_enabled: None,
) -> None:
    app = create_app(database_url=f"sqlite:///{tmp_path / 'experiment-runbook.db'}")

    with TestClient(app) as client:
        # Given an owner with a completed Experiment Planner stage.
        register_and_login(client, "RUNBOOK-DOWNLOAD", "runbook@example.com")
        experiment_stage_id = create_quest_with_experiment_stage(client)
        complete_experiment_stage(client, experiment_stage_id)

        # When the owner downloads the Experiment Planner runbook.
        response = client.get(f"/stages/{experiment_stage_id}/experiment-runbook/download")

    # Then the Markdown attachment preserves plan boundaries and reproducibility details.
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/markdown")
    assert response.headers["content-disposition"] == (
        'attachment; filename="experiment-planner-runbook.md"'
    )
    assert "# NoviScope Experiment Runbook" in response.text
    assert "Plan-only export" in response.text
    assert "No experiment results" in response.text
    assert "TrackNet shuttle trajectory baseline" in response.text
    assert "Trajectory localization error" in response.text
    assert "Create dataset manifest" in response.text
    assert "One A800 GPU for the first reproducibility run." in response.text
    assert "api_key" not in response.text


def test_download_experiment_runbook_blocks_until_stage_complete(
    tmp_path,
    dev_admin_header_enabled: None,
) -> None:
    app = create_app(database_url=f"sqlite:///{tmp_path / 'experiment-runbook-block.db'}")

    with TestClient(app) as client:
        # Given an owner with an incomplete Experiment Planner stage.
        register_and_login(client, "RUNBOOK-BLOCK", "runbook-block@example.com")
        experiment_stage_id = create_quest_with_experiment_stage(client)

        # When the owner downloads the runbook before the planner completes.
        response = client.get(f"/stages/{experiment_stage_id}/experiment-runbook/download")

    # Then the API refuses to imply an experiment plan exists.
    assert response.status_code == 409
    assert response.json()["detail"] == (
        "Experiment Planner must complete before a runbook can be downloaded."
    )


def test_download_experiment_runbook_rejects_other_users_stage(
    tmp_path,
    dev_admin_header_enabled: None,
) -> None:
    app = create_app(database_url=f"sqlite:///{tmp_path / 'experiment-runbook-permission.db'}")

    with TestClient(app) as client:
        # Given one user owns a completed Experiment Planner stage.
        register_and_login(client, "RUNBOOK-OWNER", "runbook-owner@example.com")
        experiment_stage_id = create_quest_with_experiment_stage(client)
        complete_experiment_stage(client, experiment_stage_id)
        logout_response = client.post("/auth/logout")
        assert logout_response.status_code == 204
        register_and_login(client, "RUNBOOK-OTHER", "runbook-other@example.com")

        # When another user attempts to download the runbook.
        response = client.get(f"/stages/{experiment_stage_id}/experiment-runbook/download")

    # Then ownership rules prevent cross-user access.
    assert response.status_code == 403
