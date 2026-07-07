from fastapi.testclient import TestClient

from noviscope.agents.stage_runner import StageRunContext, StageRunnerRegistry, StageRunResult
from noviscope.api.stage_runs import get_stage_runner_registry
from noviscope.core.stage_policy import DEMAND_VALIDATOR_AGENT_ID
from noviscope.main import create_app
from noviscope.models.provider import ProviderKind

DEV_ADMIN_HEADERS = {"X-NoviScope-Dev-Admin": "test-dev-admin-token-0123456789abcdef"}


class InputTraceStageRunner:
    @property
    def agent_id(self) -> str:
        return DEMAND_VALIDATOR_AGENT_ID

    @property
    def supported_provider_kinds(self) -> frozenset[ProviderKind]:
        return frozenset({ProviderKind.OPENAI_COMPATIBLE})

    def build_input_payload(self, context: StageRunContext) -> dict[str, str]:
        return {
            "phase": "queued",
            "provider_model": context.provider.model,
        }

    def run(self, context: StageRunContext) -> StageRunResult:
        return StageRunResult(
            confidence="medium",
            evidence_payload={"can_run": True},
            input_payload={
                "audit_query": context.quest.initial_direction,
                "phase": "final",
                "provider_model": context.provider.model,
            },
            output_payload={
                "confidence": "medium",
                "summary": "Final input payload was produced.",
            },
            summary="Final input payload was produced.",
        )


def get_input_trace_registry() -> StageRunnerRegistry:
    runner = InputTraceStageRunner()
    return StageRunnerRegistry(runners={runner.agent_id: runner})


def register_and_login(client: TestClient) -> None:
    invite_response = client.post(
        "/admin/invites",
        headers=DEV_ADMIN_HEADERS,
        json={"code": "INPUT-PAYLOAD", "max_uses": 1},
    )
    assert invite_response.status_code == 201
    register_response = client.post(
        "/auth/register",
        json={
            "display_name": "input",
            "email": "input@example.com",
            "invite_code": "INPUT-PAYLOAD",
            "password": "password",
        },
    )
    assert register_response.status_code == 201
    login_response = client.post(
        "/auth/login",
        json={"email": "input@example.com", "password": "password"},
    )
    assert login_response.status_code == 200


def create_provider(client: TestClient) -> None:
    response = client.post(
        "/providers",
        json={
            "api_key": "sk-test",
            "base_url": "https://api.example.com/v1",
            "default_model": "trace-model",
            "kind": "openai_compatible",
            "name": "Trace Provider",
            "scope": "personal",
        },
    )
    assert response.status_code == 201


def test_stage_run_persists_runner_final_input_payload(
    tmp_path,
    dev_admin_header_enabled: None,
) -> None:
    app = create_app(database_url=f"sqlite:///{tmp_path / 'stage-run-input.db'}")
    app.dependency_overrides[get_stage_runner_registry] = get_input_trace_registry

    with TestClient(app) as client:
        # Given
        register_and_login(client)
        create_provider(client)
        quest_response = client.post(
            "/quests",
            json={
                "initial_direction": "Use camera clips to recognize badminton actions.",
                "title": "Badminton action recognition",
            },
        )
        assert quest_response.status_code == 201
        stage_id = quest_response.json()["first_stage"]["id"]

        # When
        response = client.post(f"/stages/{stage_id}/run", json={})

    # Then
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "complete"
    assert body["input_payload"] == {
        "audit_query": "Use camera clips to recognize badminton actions.",
        "phase": "final",
        "provider_model": "trace-model",
    }
