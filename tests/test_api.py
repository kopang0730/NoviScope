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
