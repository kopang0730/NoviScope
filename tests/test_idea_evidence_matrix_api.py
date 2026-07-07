from fastapi.testclient import TestClient

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


def create_research_quest(client: TestClient) -> tuple[str, str]:
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
    stages = stages_response.json()["stages"]
    literature_stage_id = next(
        stage["id"] for stage in stages if stage["agent_id"] == "literature_scout"
    )
    idea_stage_id = next(stage["id"] for stage in stages if stage["agent_id"] == "idea_generator")
    return literature_stage_id, idea_stage_id


def complete_literature_stage(client: TestClient, literature_stage_id: str) -> None:
    running_response = client.patch(f"/stages/{literature_stage_id}", json={"status": "running"})
    assert running_response.status_code == 200
    complete_response = client.patch(
        f"/stages/{literature_stage_id}",
        json={
            "output_payload": {
                "papers": [
                    {
                        "abstract_summary": "Badminton action recognition benchmark.",
                        "authors": ["Ada Chen"],
                        "doi": "https://doi.org/10.0000/badminton",
                        "limitations": ["Verify the full paper before citing."],
                        "openalex_id": "https://openalex.org/W123",
                        "publication_type": "proceedings-article",
                        "recency_bucket": "recent_3_years",
                        "relevance_score": 112.5,
                        "reliability_level": "top_conference_or_journal",
                        "source_quality_signals": ["Venue matched cvpr."],
                        "source_type": "conference",
                        "title": "Badminton action recognition benchmark",
                        "url": "https://example.org/badminton",
                        "venue": "CVPR",
                        "why_relevant": "Matches badminton action recognition.",
                        "year": 2025,
                    }
                ],
                "score_basis": "OpenAlex relevance_score with recency boost.",
                "search_query": "badminton action recognition",
                "source": "openalex_works_api",
            },
            "status": "complete",
        },
    )
    assert complete_response.status_code == 200


def complete_idea_stage(
    client: TestClient,
    idea_stage_id: str,
    literature_stage_id: str,
) -> None:
    running_response = client.patch(f"/stages/{idea_stage_id}", json={"status": "running"})
    assert running_response.status_code == 200
    complete_response = client.patch(
        f"/stages/{idea_stage_id}",
        json={
            "output_payload": {
                "confidence": "medium",
                "ideas": [
                    {
                        "application_value": "high",
                        "based_on_which_papers": [
                            "https://openalex.org/W123",
                            "made-up-paper",
                        ],
                        "confidence": "medium",
                        "core_hypothesis": "Temporal cues improve badminton action recognition.",
                        "expected_improvement": "Better frame-level stability.",
                        "experiment_feasibility": "medium",
                        "idea_id": "idea_temporal_cues",
                        "idea_title": "Temporal cue badminton action recognition",
                        "novelty_risk": "medium",
                        "required_baseline": "Pose-based action classifier",
                        "required_data": "Badminton training videos",
                    }
                ],
                "selected_idea_ids": [],
                "selection_status": "pending_human_selection",
                "source_stage_ids": {"literature_scout": literature_stage_id},
                "summary": "Generated one idea for human review.",
            },
            "status": "complete",
        },
    )
    assert complete_response.status_code == 200


def test_idea_evidence_matrix_links_ideas_to_known_literature(
    tmp_path,
    dev_admin_header_enabled: None,
) -> None:
    app = create_app(database_url=f"sqlite:///{tmp_path / 'idea-evidence-matrix.db'}")
    with TestClient(app) as client:
        register_and_login(client, "IDEA-MATRIX", "idea-matrix@example.com")
        literature_stage_id, idea_stage_id = create_research_quest(client)
        complete_literature_stage(client, literature_stage_id)
        complete_idea_stage(client, idea_stage_id, literature_stage_id)

        response = client.get(f"/stages/{idea_stage_id}/idea-evidence-matrix")

    assert response.status_code == 200
    body = response.json()
    assert body["stage_id"] == idea_stage_id
    assert body["source_stage_ids"] == {"literature_scout": literature_stage_id}
    assert body["unavailable_reason"] == ""
    assert body["idea_count"] == 1
    assert body["requires_human_selection"] is True
    assert body["selection_status"] == "pending_human_selection"
    assert body["selected_idea_ids"] == []
    idea = body["ideas"][0]
    assert idea["idea_id"] == "idea_temporal_cues"
    assert idea["source_paper_refs"] == ["https://openalex.org/W123", "made-up-paper"]
    assert idea["recognized_source_count"] == 1
    assert idea["missing_source_refs"] == ["made-up-paper"]
    assert idea["linked_papers"] == [
        {
            "paper_ref": "https://openalex.org/W123",
            "relevance_score": 112.5,
            "reliability_level": "top_conference_or_journal",
            "title": "Badminton action recognition benchmark",
            "venue": "CVPR",
            "why_relevant": "Matches badminton action recognition.",
            "year": 2025,
        }
    ]


def test_idea_evidence_matrix_reports_unavailable_pending_stage(
    tmp_path,
    dev_admin_header_enabled: None,
) -> None:
    app = create_app(database_url=f"sqlite:///{tmp_path / 'idea-evidence-pending.db'}")
    with TestClient(app) as client:
        register_and_login(client, "IDEA-PENDING", "idea-pending@example.com")
        _, idea_stage_id = create_research_quest(client)

        response = client.get(f"/stages/{idea_stage_id}/idea-evidence-matrix")

    assert response.status_code == 200
    body = response.json()
    assert body["ideas"] == []
    assert body["idea_count"] == 0
    assert body["unavailable_reason"] == (
        "Gap & hypothesis generator must complete before idea evidence is available."
    )
