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


def create_quest_with_stages(client: TestClient) -> list[dict[str, str]]:
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
    return stages_response.json()["stages"]


def experiment_stage_id(stages: list[dict[str, str]]) -> str:
    experiment_stage = next(
        stage for stage in stages if stage["agent_id"] == EXPERIMENT_PLANNER_AGENT_ID
    )
    return experiment_stage["id"]


def approve_experiment_stage(client: TestClient, stage_id: str) -> None:
    running_response = client.patch(f"/stages/{stage_id}", json={"status": "running"})
    assert running_response.status_code == 200
    complete_response = client.patch(
        f"/stages/{stage_id}",
        json={
            "human_approved": True,
            "output_payload": {
                "confidence": "medium",
                "first_runnable_script_plan": [
                    "Run the baseline on badminton clips and save logs.",
                ],
                "metrics": ["Action classification accuracy"],
                "summary": "Experiment plan only; no verified results yet.",
            },
            "review_notes": "Plan approved for a first reproducibility run.",
            "status": "complete",
            "summary": "Experiment Planner produced a plan-only design.",
        },
    )
    assert complete_response.status_code == 200


def verified_result_payload() -> dict[str, str | float | bool]:
    return {
        "artifact_uri": "/data/noviscope/runs/run-20260707/metrics.json",
        "baseline_name": "Pose-based action classifier",
        "dataset_name": "Badminton training clips v1",
        "higher_is_better": True,
        "metric_name": "Action classification accuracy",
        "metric_unit": "%",
        "metric_value": 78.4,
        "provenance_note": "Recorded from local run log metrics.json on the lab A800 server.",
        "result_status": "verified",
        "review_notes": "Human checked the metric file and matching run id.",
        "run_id": "run-20260707-baseline",
    }


def test_record_experiment_result_requires_login(tmp_path, dev_admin_header_enabled: None) -> None:
    app = create_app(database_url=f"sqlite:///{tmp_path / 'experiment-results-auth.db'}")
    with TestClient(app) as client:
        response = client.post(
            "/stages/stage_missing/experiment-results",
            json=verified_result_payload(),
        )

    assert response.status_code == 401


def test_record_experiment_result_rejects_wrong_stage(
    tmp_path,
    dev_admin_header_enabled: None,
) -> None:
    app = create_app(database_url=f"sqlite:///{tmp_path / 'experiment-results-wrong.db'}")
    with TestClient(app) as client:
        register_and_login(client, "RESULT-WRONG", "result-wrong@example.com")
        stages = create_quest_with_stages(client)
        demand_stage = next(stage for stage in stages if stage["agent_id"] == "demand_validator")

        response = client.post(
            f"/stages/{demand_stage['id']}/experiment-results",
            json=verified_result_payload(),
        )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "Experiment results can only be recorded on Experiment Planner stages."
    )


def test_record_experiment_result_blocks_unapproved_experiment_plan(
    tmp_path,
    dev_admin_header_enabled: None,
) -> None:
    app = create_app(database_url=f"sqlite:///{tmp_path / 'experiment-results-gate.db'}")
    with TestClient(app) as client:
        register_and_login(client, "RESULT-GATE", "result-gate@example.com")
        stage_id = experiment_stage_id(create_quest_with_stages(client))

        response = client.post(
            f"/stages/{stage_id}/experiment-results",
            json=verified_result_payload(),
        )

    assert response.status_code == 409
    assert response.json()["detail"] == (
        "Approve a completed Experiment Planner stage before recording experiment results."
    )


def test_record_verified_experiment_result_updates_stage_trace(
    tmp_path,
    dev_admin_header_enabled: None,
) -> None:
    app = create_app(database_url=f"sqlite:///{tmp_path / 'experiment-results.db'}")
    with TestClient(app) as client:
        register_and_login(client, "RESULT-OK", "result-ok@example.com")
        stages = create_quest_with_stages(client)
        stage_id = experiment_stage_id(stages)
        approve_experiment_stage(client, stage_id)

        response = client.post(
            f"/stages/{stage_id}/experiment-results",
            json=verified_result_payload(),
        )
        stages_response = client.get(f"/quests/{response.json()['quest_id']}/stages")

    assert response.status_code == 200
    body = response.json()
    assert body["stage_id"] == stage_id
    assert body["agent_id"] == EXPERIMENT_PLANNER_AGENT_ID
    assert body["recorded_result_count"] == 1
    assert body["verified_result_count"] == 1
    assert body["needs_review_count"] == 0
    assert body["experiment_results_available"] is True
    assert body["latest_result"]["metric_name"] == "Action classification accuracy"
    assert body["latest_result"]["run_id"] == "run-20260707-baseline"

    assert stages_response.status_code == 200
    updated_stage = next(
        stage
        for stage in stages_response.json()["stages"]
        if stage["agent_id"] == EXPERIMENT_PLANNER_AGENT_ID
    )
    assert updated_stage["status"] == "complete"
    assert updated_stage["human_approved"] is True
    assert updated_stage["output_payload"]["experiment_results_available"] is True
    assert updated_stage["output_payload"]["experiment_results"][0]["artifact_uri"] == (
        "/data/noviscope/runs/run-20260707/metrics.json"
    )
    assert updated_stage["evidence_payload"]["experiment_result_count"] == 1
    assert updated_stage["evidence_payload"]["verified_experiment_result_count"] == 1
    assert updated_stage["evidence_payload"]["experiment_results_require_review"] is False
    assert updated_stage["evidence_payload"]["experiment_result_provenance_refs"] == [
        "/data/noviscope/runs/run-20260707/metrics.json",
    ]
    assert updated_stage["review_notes"] == "Human checked the metric file and matching run id."


def test_record_needs_review_result_does_not_create_verified_claim(
    tmp_path,
    dev_admin_header_enabled: None,
) -> None:
    app = create_app(database_url=f"sqlite:///{tmp_path / 'experiment-results-review.db'}")
    with TestClient(app) as client:
        register_and_login(client, "RESULT-REVIEW", "result-review@example.com")
        stage_id = experiment_stage_id(create_quest_with_stages(client))
        approve_experiment_stage(client, stage_id)
        payload = {
            **verified_result_payload(),
            "result_status": "needs_review",
            "run_id": "run-20260707-unchecked",
            "review_notes": "Metric file exists but has not been independently checked.",
        }

        response = client.post(f"/stages/{stage_id}/experiment-results", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert body["recorded_result_count"] == 1
    assert body["verified_result_count"] == 0
    assert body["needs_review_count"] == 1
    assert body["experiment_results_available"] is False
