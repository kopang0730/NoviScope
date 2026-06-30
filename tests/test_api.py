from fastapi.testclient import TestClient

from noviscope.main import create_app


def test_health_endpoint():
    with TestClient(create_app(database_url="sqlite:///:memory:")) as client:
        response = client.get("/health")

        assert response.status_code == 200
        assert response.json()["status"] == "ok"


def test_agents_endpoint_lists_nine_agents():
    with TestClient(create_app(database_url="sqlite:///:memory:")) as client:
        response = client.get("/agents")

        assert response.status_code == 200
        body = response.json()
        assert len(body["agents"]) == 9
        assert body["agents"][0]["agent_id"] == "demand_validator"
        assert body["agents"][0]["tool_permissions"] == [
            "web_search",
            "read_pdf",
            "github_search",
            "write_files",
        ]


def test_provider_crud_endpoints_do_not_return_api_key():
    with TestClient(create_app(database_url="sqlite:///:memory:")) as client:
        create_response = client.post(
            "/providers",
            json={
                "name": "primary-openai",
                "kind": "openai_compatible",
                "base_url": "https://api.openai.com/v1",
                "default_model": "gpt-4.1",
                "api_key": "sk-realistic-test-key",
            },
        )

        assert create_response.status_code == 201
        provider = create_response.json()
        assert provider["name"] == "primary-openai"
        assert "api_key" not in provider
        assert "api_key_ciphertext" not in provider

        provider_id = provider["id"]
        list_response = client.get("/providers")
        assert list_response.status_code == 200
        assert list_response.json()["providers"][0]["id"] == provider_id

        get_response = client.get(f"/providers/{provider_id}")
        assert get_response.status_code == 200
        assert get_response.json()["default_model"] == "gpt-4.1"

        update_response = client.patch(
            f"/providers/{provider_id}",
            json={"default_model": "gpt-4.1-mini", "is_active": False},
        )
        assert update_response.status_code == 200
        assert update_response.json()["default_model"] == "gpt-4.1-mini"
        assert update_response.json()["is_active"] is False

        delete_response = client.delete(f"/providers/{provider_id}")
        assert delete_response.status_code == 204

        missing_response = client.get(f"/providers/{provider_id}")
        assert missing_response.status_code == 404


def test_create_quest_endpoint():
    with TestClient(create_app(database_url="sqlite:///:memory:")) as client:
        response = client.post(
            "/quests",
            json={"title": "AI+Sports Badminton", "initial_direction": "AI+体育，羽毛球"},
        )

        assert response.status_code == 201
        body = response.json()
        assert body["title"] == "AI+Sports Badminton"
        assert body["status"] == "draft"
        assert body["first_stage"]["agent_id"] == "demand_validator"
        assert body["first_stage"]["status"] == "pending"


def test_stage_flow_endpoints_record_review_payloads():
    with TestClient(create_app(database_url="sqlite:///:memory:")) as client:
        quest_response = client.post(
            "/quests",
            json={"title": "Handwritten Text Erasure", "initial_direction": "手写文本擦除"},
        )
        quest = quest_response.json()
        stage_id = quest["first_stage"]["id"]

        stages_response = client.get(f"/quests/{quest['id']}/stages")
        assert stages_response.status_code == 200
        assert stages_response.json()["stages"][0]["id"] == stage_id

        running_response = client.patch(
            f"/stages/{stage_id}",
            json={
                "status": "running",
                "input_payload": {"direction": "手写文本擦除"},
            },
        )
        assert running_response.status_code == 200
        assert running_response.json()["status"] == "running"

        complete_response = client.patch(
            f"/stages/{stage_id}",
            json={
                "status": "complete",
                "summary": "Demand has concrete education scenario evidence.",
                "output_payload": {"confidence": 0.82},
                "evidence_payload": {"sources": ["enterprise-demand-note"]},
                "human_approved": True,
                "review_notes": "Proceed to idea generation.",
            },
        )
        body = complete_response.json()
        assert complete_response.status_code == 200
        assert body["status"] == "complete"
        assert body["output_payload"] == {"confidence": 0.82}
        assert body["evidence_payload"] == {"sources": ["enterprise-demand-note"]}
        assert body["human_approved"] is True


def test_stage_endpoint_rejects_invalid_transition():
    with TestClient(create_app(database_url="sqlite:///:memory:")) as client:
        quest_response = client.post(
            "/quests",
            json={"title": "Badminton", "initial_direction": "AI+体育"},
        )
        stage_id = quest_response.json()["first_stage"]["id"]

        response = client.patch(f"/stages/{stage_id}", json={"status": "complete"})

        assert response.status_code == 400
        assert "pending to complete" in response.json()["detail"]


def test_create_quest_endpoint_rejects_missing_direction():
    with TestClient(create_app(database_url="sqlite:///:memory:")) as client:
        response = client.post("/quests", json={"title": "AI+Sports Badminton"})

        assert response.status_code == 422


def test_openapi_has_quest_response_schema():
    with TestClient(create_app(database_url="sqlite:///:memory:")) as client:
        response = client.get("/openapi.json")

        quest_schema = response.json()["paths"]["/quests"]["post"]["responses"]["201"]
        assert quest_schema["content"]["application/json"]["schema"]["$ref"].endswith(
            "QuestCreateResponse"
        )
