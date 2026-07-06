from fastapi.testclient import TestClient

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
            "initial_direction": "Use computer vision for badminton action recognition.",
            "title": "Badminton action recognition",
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


def test_save_experiment_setup_records_runner_inputs(
    tmp_path,
    dev_admin_header_enabled: None,
) -> None:
    app = create_app(database_url=f"sqlite:///{tmp_path / 'experiment-setup.db'}")
    with TestClient(app) as client:
        register_and_login(client, "EXPERIMENT-SETUP", "experiment@example.com")
        stage_id = create_quest_with_experiment_stage(client)

        response = client.post(
            f"/stages/{stage_id}/experiment-setup",
            json={
                "code_repository": "https://github.com/lab/badminton-baseline",
                "data_path": "/data/badminton/train-videos",
                "environment_notes": "A800 server, CUDA 12.4, PyTorch environment prepared.",
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["agent_id"] == EXPERIMENT_PLANNER_AGENT_ID
    assert body["status"] == "pending"
    assert body["input_payload"]["code_repository"] == ("https://github.com/lab/badminton-baseline")
    assert body["input_payload"]["data_path"] == "/data/badminton/train-videos"
    assert body["input_payload"]["environment_notes"] == (
        "A800 server, CUDA 12.4, PyTorch environment prepared."
    )
    assert body["evidence_payload"]["experiment_setup_recorded"] is True
    assert body["evidence_payload"]["required_input_fields"] == [
        "data_path",
        "code_repository",
        "environment_notes",
    ]
    assert body["summary"] == "Experiment setup inputs are recorded for Experiment Planner."


def test_save_experiment_setup_unblocks_missing_input_stage(
    tmp_path,
    dev_admin_header_enabled: None,
) -> None:
    app = create_app(database_url=f"sqlite:///{tmp_path / 'experiment-setup-blocked.db'}")
    with TestClient(app) as client:
        register_and_login(client, "EXPERIMENT-UNBLOCK", "experiment-unblock@example.com")
        stage_id = create_quest_with_experiment_stage(client)
        blocked_response = client.patch(
            f"/stages/{stage_id}",
            json={
                "evidence_payload": {
                    "blocking_reason": "missing_experiment_inputs",
                    "can_run": False,
                    "missing_inputs": ["data_path", "code_repository", "environment_notes"],
                },
                "status": "blocked",
            },
        )
        assert blocked_response.status_code == 200

        response = client.post(
            f"/stages/{stage_id}/experiment-setup",
            json={
                "code_repository": "https://github.com/lab/badminton-baseline",
                "data_path": "/data/badminton/train-videos",
                "environment_notes": "Use the existing conda environment.",
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "pending"
    assert "blocking_reason" not in body["evidence_payload"]
    assert body["evidence_payload"]["experiment_setup_recorded"] is True


def test_save_experiment_setup_rejects_wrong_stage(
    tmp_path,
    dev_admin_header_enabled: None,
) -> None:
    app = create_app(database_url=f"sqlite:///{tmp_path / 'experiment-setup-wrong.db'}")
    with TestClient(app) as client:
        register_and_login(client, "EXPERIMENT-WRONG", "experiment-wrong@example.com")
        quest_response = client.post(
            "/quests",
            json={
                "initial_direction": "Badminton action recognition.",
                "title": "Badminton action recognition",
            },
        )
        assert quest_response.status_code == 201
        stages_response = client.get(f"/quests/{quest_response.json()['id']}/stages")
        demand_stage = next(
            stage
            for stage in stages_response.json()["stages"]
            if stage["agent_id"] == "demand_validator"
        )

        response = client.post(
            f"/stages/{demand_stage['id']}/experiment-setup",
            json={
                "code_repository": "https://github.com/lab/badminton-baseline",
                "data_path": "/data/badminton/train-videos",
                "environment_notes": "Use the existing conda environment.",
            },
        )

    assert response.status_code == 400
    assert response.json()["detail"] == "Experiment setup is only available for Experiment Planner."
