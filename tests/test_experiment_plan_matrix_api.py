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


def create_experiment_stage(client: TestClient) -> str:
    quest_response = client.post(
        "/quests",
        json={
            "initial_direction": "Use computer vision for badminton action recognition.",
            "title": "Badminton action recognition",
        },
    )
    assert quest_response.status_code == 201
    stages_response = client.get(f"/quests/{quest_response.json()['id']}/stages")
    assert stages_response.status_code == 200
    return next(
        stage["id"]
        for stage in stages_response.json()["stages"]
        if stage["agent_id"] == EXPERIMENT_PLANNER_AGENT_ID
    )


def complete_experiment_stage(client: TestClient, stage_id: str) -> None:
    setup_response = client.post(
        f"/stages/{stage_id}/experiment-setup",
        json={
            "code_repository": "https://github.com/lab/badminton-baseline",
            "data_path": "/data/badminton/train-videos",
            "environment_notes": "A800 server, CUDA 12.4, PyTorch environment prepared.",
        },
    )
    assert setup_response.status_code == 200
    running_response = client.patch(f"/stages/{stage_id}", json={"status": "running"})
    assert running_response.status_code == 200
    complete_response = client.patch(
        f"/stages/{stage_id}",
        json={
            "evidence_payload": {
                "data_availability_status": "ready",
                "no_experiment_results": True,
                "plan_only": True,
                "requires_human_review": True,
                "source_stage_ids": {"idea_generator": "stage_idea"},
            },
            "output_payload": {
                "ablation_variables": ["temporal window size", "pose smoothing"],
                "baselines_to_reproduce": ["Pose-based action classifier"],
                "compute_requirements": "One A800 GPU for baseline and ablation runs.",
                "confidence": "medium",
                "data_availability_status": "ready",
                "datasets_needed": ["/data/badminton/train-videos"],
                "expected_figures": ["Failure case grid"],
                "expected_tables": ["Baseline and ablation table"],
                "failure_risks": ["Video labels may be noisy."],
                "first_runnable_script_plan": ["Build manifest", "Run baseline inference"],
                "metrics": ["Action accuracy", "Frame consistency"],
                "source_stage_ids": {"idea_generator": "stage_idea"},
                "summary": "Plan the first baseline and ablation run.",
                "warnings": [
                    "No experiment has run. This output is an executable plan only."
                ],
            },
            "status": "complete",
        },
    )
    assert complete_response.status_code == 200


def test_experiment_plan_matrix_exposes_plan_sections_without_results_claims(
    tmp_path,
    dev_admin_header_enabled: None,
) -> None:
    app = create_app(database_url=f"sqlite:///{tmp_path / 'experiment-plan-matrix.db'}")
    with TestClient(app) as client:
        register_and_login(client, "PLAN-MATRIX", "plan-matrix@example.com")
        stage_id = create_experiment_stage(client)
        complete_experiment_stage(client, stage_id)

        response = client.get(f"/stages/{stage_id}/experiment-plan-matrix")

    assert response.status_code == 200
    body = response.json()
    assert body["stage_id"] == stage_id
    assert body["unavailable_reason"] == ""
    assert body["plan_only"] is True
    assert body["no_experiment_results"] is True
    assert body["requires_human_review"] is True
    assert body["data_availability_status"] == "ready"
    assert body["setup_inputs"] == {
        "code_repository": "https://github.com/lab/badminton-baseline",
        "data_path": "/data/badminton/train-videos",
        "environment_notes": "A800 server, CUDA 12.4, PyTorch environment prepared.",
    }
    sections = {section["section_id"]: section for section in body["plan_sections"]}
    assert sections["datasets_needed"]["items"] == ["/data/badminton/train-videos"]
    assert sections["baselines_to_reproduce"]["items"] == ["Pose-based action classifier"]
    assert sections["metrics"]["items"] == ["Action accuracy", "Frame consistency"]
    assert sections["first_runnable_script_plan"]["items"] == [
        "Build manifest",
        "Run baseline inference",
    ]
    assert body["human_review_checklist"] == [
        "Verify dataset paths are accessible on the lab server before running experiments.",
        "Confirm baseline code, license, commit, and environment notes are reproducible.",
        "Check that metrics, ablations, expected tables, and figures match the selected idea.",
        "Treat every listed failure risk as unresolved until a human reviews it.",
    ]


def test_experiment_plan_matrix_reports_unavailable_pending_stage(
    tmp_path,
    dev_admin_header_enabled: None,
) -> None:
    app = create_app(database_url=f"sqlite:///{tmp_path / 'experiment-plan-pending.db'}")
    with TestClient(app) as client:
        register_and_login(client, "PLAN-PENDING", "plan-pending@example.com")
        stage_id = create_experiment_stage(client)

        response = client.get(f"/stages/{stage_id}/experiment-plan-matrix")

    assert response.status_code == 200
    body = response.json()
    assert body["plan_sections"] == []
    assert body["plan_only"] is True
    assert body["no_experiment_results"] is True
    assert body["unavailable_reason"] == (
        "Experiment Planner must complete before experiment plan matrix rows are available."
    )
