from fastapi.testclient import TestClient

from noviscope.agents.demand_validation import (
    DemandValidationOutput,
    DemandValidationRequest,
    DemandValidationRunner,
    get_demand_validation_runner,
)
from noviscope.main import create_app

DEV_ADMIN_HEADERS = {"X-NoviScope-Dev-Admin": "test-dev-admin-token-0123456789abcdef"}


class FakeDemandValidationRunner:
    def run(self, request: DemandValidationRequest) -> DemandValidationOutput:
        return DemandValidationOutput(
            confidence="medium",
            demand_assessment="plausible",
            evidence=[
                "The direction names a concrete sports-training user and measurable outputs.",
            ],
            next_step="Ask the user to confirm data availability before experiment planning.",
            raw_response="fake response",
            risks=[
                "The current evidence is self-reported and still needs source validation.",
            ],
            summary="Demand appears plausible but requires user confirmation.",
        )


def get_fake_runner() -> DemandValidationRunner:
    return FakeDemandValidationRunner()


def register_and_login(client: TestClient, invite_code: str, email: str) -> None:
    invite_response = client.post(
        "/admin/invites",
        json={"code": invite_code, "max_uses": 1},
        headers=DEV_ADMIN_HEADERS,
    )
    assert invite_response.status_code == 201

    register_response = client.post(
        "/auth/register",
        json={
            "invite_code": invite_code,
            "email": email,
            "display_name": email.split("@")[0],
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
            "api_key": "sk-test",
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
            "initial_direction": (
                "# NoviScope Quest Intake\n"
                "- Research direction: Badminton action recognition"
            ),
            "title": "Badminton action recognition",
        },
    )
    assert response.status_code == 201
    return response.json()["first_stage"]["id"]


def test_run_demand_validation_stage_completes_with_provider(
    tmp_path,
    dev_admin_header_enabled: None,
) -> None:
    app = create_app(database_url=f"sqlite:///{tmp_path / 'stage-run.db'}")
    app.dependency_overrides[get_demand_validation_runner] = get_fake_runner

    with TestClient(app) as client:
        register_and_login(client, "RUN-STAGE", "runner@example.com")
        create_personal_provider(client)
        stage_id = create_quest(client)

        response = client.post(f"/stages/{stage_id}/run", json={})

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "complete"
    assert body["summary"] == "Demand appears plausible but requires user confirmation."
    assert body["output_payload"]["demand_assessment"] == "plausible"
    assert body["output_payload"]["confidence"] == "medium"
    assert body["evidence_payload"]["provider_name"] == "Example Provider"
    assert body["input_payload"]["agent_id"] == "demand_validator"


def test_run_demand_validation_stage_blocks_without_provider(
    tmp_path,
    dev_admin_header_enabled: None,
) -> None:
    app = create_app(database_url=f"sqlite:///{tmp_path / 'stage-run-no-provider.db'}")

    with TestClient(app) as client:
        register_and_login(client, "RUN-STAGE-NO-PROVIDER", "blocked@example.com")
        stage_id = create_quest(client)

        response = client.post(f"/stages/{stage_id}/run", json={})

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "blocked"
    assert body["summary"] == "No active model provider is available for this user."
    assert body["evidence_payload"]["blocking_reason"] == "missing_provider"
