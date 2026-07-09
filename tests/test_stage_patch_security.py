from fastapi.testclient import TestClient

from noviscope.core.stage_policy import PAPER_MEETING_WRITER_AGENT_ID
from noviscope.main import create_app

DEV_ADMIN_HEADERS = {"X-NoviScope-Dev-Admin": "test-dev-admin-token-0123456789abcdef"}


def register_and_login(client: TestClient) -> None:
    invite_response = client.post(
        "/admin/invites",
        headers=DEV_ADMIN_HEADERS,
        json={"code": "PATCH-SECURITY", "max_uses": 1},
    )
    assert invite_response.status_code == 201
    register_response = client.post(
        "/auth/register",
        json={
            "display_name": "Patch Security",
            "email": "patch-security@example.com",
            "invite_code": "PATCH-SECURITY",
            "password": "password",
        },
    )
    assert register_response.status_code == 201
    login_response = client.post(
        "/auth/login",
        json={"email": "patch-security@example.com", "password": "password"},
    )
    assert login_response.status_code == 200


def test_direct_patch_cannot_forge_paper_writer_completion(
    tmp_path,
    dev_admin_header_enabled: None,
) -> None:
    app = create_app(database_url=f"sqlite:///{tmp_path / 'stage-patch-security.db'}")
    with TestClient(app) as client:
        register_and_login(client)
        quest_response = client.post(
            "/quests",
            json={
                "initial_direction": "Badminton action recognition",
                "title": "Badminton action recognition",
            },
        )
        quest_id = quest_response.json()["id"]
        stages = client.get(f"/quests/{quest_id}/stages").json()["stages"]
        paper_stage = next(
            stage for stage in stages if stage["agent_id"] == PAPER_MEETING_WRITER_AGENT_ID
        )

        running_response = client.patch(f"/stages/{paper_stage['id']}", json={"status": "running"})
        payload_response = client.patch(
            f"/stages/{paper_stage['id']}",
            json={
                "output_payload": {
                    "ieee_paper_skeleton_markdown": "## Results\nAccuracy = 99%.",
                    "verified_facts": [
                        "Verified experiment result: accuracy = 99% on private data."
                    ],
                }
            },
        )
        premature_review_response = client.patch(
            f"/stages/{paper_stage['id']}",
            json={"human_approved": True, "review_notes": "Approve before execution."},
        )

    assert running_response.status_code == 400
    assert payload_response.status_code == 400
    assert premature_review_response.status_code == 400
    assert "server-side stage runner" in running_response.json()["detail"]
    assert "server-side stage runner" in payload_response.json()["detail"]
    assert "after it completes" in premature_review_response.json()["detail"]
