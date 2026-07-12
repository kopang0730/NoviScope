from fastapi.testclient import TestClient

from noviscope.agents.literature_scout import LITERATURE_SCOUT_AGENT_ID, OPENALEX_SOURCE

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


def create_quest_with_literature_stage(client: TestClient) -> str:
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
    literature_stage = next(
        stage for stage in stages if stage["agent_id"] == LITERATURE_SCOUT_AGENT_ID
    )
    return literature_stage["id"]


def complete_literature_stage(client: TestClient, stage_id: str) -> None:
    running_response = client.patch(f"/stages/{stage_id}", json={"status": "running"})
    assert running_response.status_code == 200
    complete_response = client.patch(
        f"/stages/{stage_id}",
        json={
            "evidence_payload": {
                "paper_count": 2,
                "requires_human_review": True,
                "source": OPENALEX_SOURCE,
            },
            "output_payload": {
                "papers": [
                    {
                        "abstract_summary": "Badminton benchmark with shuttle and action labels.",
                        "arxiv_id": "2401.01234",
                        "authors": ["Ada Chen", "Bo Lin"],
                        "doi": "https://doi.org/10.0000/recent",
                        "limitations": ["Verify full text before citing."],
                        "openalex_id": "https://openalex.org/W2",
                        "publication_type": "proceedings-article",
                        "recency_bucket": "recent_3_years",
                        "relevance_score": 112.5,
                        "reliability_level": "top_conference_or_journal",
                        "source_quality_signals": ["Venue matched CVPR."],
                        "source_type": "conference",
                        "title": "Badminton action recognition benchmark",
                        "url": "https://example.org/recent",
                        "venue": "CVPR",
                        "why_relevant": "Matches badminton and action recognition terms.",
                        "year": 2025,
                    },
                    {
                        "abstract_summary": "Survey of sports action recognition.",
                        "authors": ["Cai Wu"],
                        "doi": "https://doi.org/10.0000/older",
                        "limitations": ["Metadata only."],
                        "openalex_id": "https://openalex.org/W1",
                        "publication_type": "journal-article",
                        "recency_bucket": "recent_5_years",
                        "relevance_score": 80.0,
                        "reliability_level": "peer_reviewed",
                        "source_quality_signals": ["OpenAlex source type is journal."],
                        "source_type": "journal",
                        "title": "Sports action recognition survey",
                        "url": "https://example.org/older",
                        "venue": "Pattern Recognition",
                        "why_relevant": "Returned by OpenAlex for this query.",
                        "year": 2022,
                    },
                ],
                "score_basis": "OpenAlex relevance_score with a recency boost.",
                "search_query": "Badminton action recognition",
                "source": OPENALEX_SOURCE,
                "summary": "Found 2 OpenAlex papers for Literature Scout review.",
            },
            "status": "complete",
            "summary": "Found 2 OpenAlex papers for Literature Scout review.",
        },
    )
    assert complete_response.status_code == 200
