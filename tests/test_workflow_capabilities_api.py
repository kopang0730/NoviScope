from fastapi.testclient import TestClient

from noviscope.api.workflow_capabilities import get_workflow_capabilities
from noviscope.main import create_app


def test_workflow_capabilities_exposes_implemented_and_planned_agents() -> None:
    # Given: the NoviScope workflow capability contract.

    # When: the frontend asks which workflow agents can actually run.
    body = get_workflow_capabilities()

    # Then: the contract separates implemented runners from planned agents.
    assert body.total_count == 9
    assert body.implemented_count == 5
    assert body.planned_count == 4

    agents_by_id = {agent.agent_id: agent for agent in body.agents}
    assert set(agents_by_id) == {
        "code_runner",
        "demand_validator",
        "evidence_auditor",
        "experiment_planner",
        "gap_analyst",
        "idea_generator",
        "literature_scout",
        "paper_meeting_writer",
        "research_refiner",
    }
    assert agents_by_id["demand_validator"].model_dump(mode="json") == {
        "agent_id": "demand_validator",
        "automation_status": "implemented",
        "display_name": "Demand Validator",
        "provider_requirement": "model_provider",
        "stage_runner_available": True,
        "status_detail": "Runnable when a compatible model provider is configured.",
        "tool_permissions": [
            "web_search",
            "read_pdf",
            "github_search",
            "write_files",
        ],
    }
    assert agents_by_id["literature_scout"].automation_status == "implemented"
    assert agents_by_id["literature_scout"].provider_requirement == "server_managed"
    assert agents_by_id["literature_scout"].stage_runner_available is True
    assert agents_by_id["code_runner"].automation_status == "planned"
    assert agents_by_id["code_runner"].provider_requirement == "not_implemented"
    assert agents_by_id["code_runner"].stage_runner_available is False
    assert agents_by_id["code_runner"].status_detail == (
        "Planned only; no automated stage runner exists yet."
    )


def test_workflow_capabilities_endpoint_exposes_frontend_contract(tmp_path) -> None:
    app = create_app(database_url=f"sqlite:///{tmp_path / 'workflow-capabilities.db'}")

    with TestClient(app) as client:
        response = client.get("/workflow/capabilities")

    assert response.status_code == 200
    body = response.json()
    assert body["implemented_count"] == 5
    assert body["planned_count"] == 4
    assert body["total_count"] == 9
    code_runner = next(agent for agent in body["agents"] if agent["agent_id"] == "code_runner")
    assert code_runner["automation_status"] == "planned"
    assert code_runner["stage_runner_available"] is False
    literature_scout = next(
        agent for agent in body["agents"] if agent["agent_id"] == "literature_scout"
    )
    assert literature_scout["provider_requirement"] == "server_managed"
