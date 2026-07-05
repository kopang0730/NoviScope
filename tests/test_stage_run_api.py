from fastapi.testclient import TestClient

from noviscope.agents.demand_validation import (
    DemandValidationOutput,
    DemandValidationRequest,
    DemandValidationRunner,
    get_demand_validation_runner,
)
from noviscope.agents.gap_hypothesis import (
    GapHypothesisOutput,
    GapHypothesisRequest,
    GapHypothesisRunner,
    get_gap_hypothesis_runner,
)
from noviscope.agents.literature_scout import (
    LITERATURE_SCOUT_AGENT_ID,
    LiteratureScoutStageRunner,
    get_literature_scout_runner,
)
from noviscope.agents.openalex_client import (
    OpenAlexLocation,
    OpenAlexSource,
    OpenAlexWork,
)
from noviscope.core.stage_policy import NO_EXTERNAL_VERIFICATION_RISK
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
            evidence_for_demand=[
                "Coach feedback workflows create a real user-facing need.",
            ],
            go_or_no_go_recommendation="go_with_human_review",
            missing_evidence=[
                "Confirm whether annotated badminton video data is already available.",
            ],
            next_step="Ask the user to confirm data availability before experiment planning.",
            raw_response="fake response",
            real_world_scenario="Badminton training sessions with coach feedback.",
            risks=[
                "The current evidence is self-reported and still needs source validation.",
            ],
            suggested_human_checklist=[
                "Confirm data ownership and annotation availability.",
            ],
            summary="Demand appears plausible but requires user confirmation.",
            target_user_or_customer="Badminton coaches and athletes.",
        )


class FakeOpenAlexClient:
    def search(self, query: str, *, current_year: int) -> list[OpenAlexWork]:
        return [
            OpenAlexWork(
                abstract_inverted_index={"badminton": [0], "recognition": [1]},
                id="https://openalex.org/W123",
                primary_location=OpenAlexLocation(
                    landing_page_url="https://example.org/openalex-paper",
                    source=OpenAlexSource(display_name="CVPR", type="conference"),
                ),
                publication_year=2025,
                relevance_score=80.0,
                title="Badminton recognition benchmark",
                type="proceedings-article",
            )
        ]


class FakeGapHypothesisRunner:
    def run(self, request: GapHypothesisRequest) -> GapHypothesisOutput:
        paper_ref = request.papers[0]["paper_ref"]
        return GapHypothesisOutput(
            confidence="medium",
            gaps=[
                {
                    "description": "Fast rallies remain difficult in the retrieved literature.",
                    "evidence_type": "paper_limitations",
                    "gap_title": "Fast rally robustness",
                    "severity": "medium",
                    "supporting_papers": [paper_ref],
                }
            ],
            ideas=[
                {
                    "application_value": "high",
                    "based_on_which_papers": [paper_ref],
                    "confidence": "medium",
                    "core_hypothesis": (
                        "Adding temporal consistency can reduce missed badminton actions."
                    ),
                    "expected_improvement": "Better action labels on fast rallies.",
                    "experiment_feasibility": "medium",
                    "idea_id": "idea_1",
                    "idea_title": "Temporal consistency for fast rallies",
                    "novelty_risk": "medium",
                    "required_baseline": "Badminton recognition benchmark.",
                    "required_data": "Annotated badminton rally clips.",
                }
            ],
            raw_response="fake gap response",
            selected_idea_ids=[],
            selection_status="pending_human_selection",
            source_stage_ids=request.source_stage_ids,
            summary="Generated one evidence-linked idea.",
            warnings=[],
        )


def get_fake_runner() -> DemandValidationRunner:
    return FakeDemandValidationRunner()


def get_fake_literature_runner() -> LiteratureScoutStageRunner:
    return LiteratureScoutStageRunner(FakeOpenAlexClient(), current_year=2026)


def get_fake_gap_runner() -> GapHypothesisRunner:
    return FakeGapHypothesisRunner()


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


def create_quest_with_stages(client: TestClient) -> tuple[str, str, str, str]:
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
    quest_id = response.json()["id"]
    stages_response = client.get(f"/quests/{quest_id}/stages")
    assert stages_response.status_code == 200
    stages = stages_response.json()["stages"]
    demand_stage = next(stage for stage in stages if stage["agent_id"] == "demand_validator")
    literature_stage = next(
        stage for stage in stages if stage["agent_id"] == LITERATURE_SCOUT_AGENT_ID
    )
    idea_stage = next(stage for stage in stages if stage["agent_id"] == "idea_generator")
    return quest_id, demand_stage["id"], literature_stage["id"], idea_stage["id"]


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
    assert body["confidence"] == "medium"
    assert body["summary"] == "Demand appears plausible but requires user confirmation."
    assert body["output_payload"]["demand_assessment"] == "plausible"
    assert body["output_payload"]["confidence"] == "medium"
    assert body["output_payload"]["real_world_scenario"] == (
        "Badminton training sessions with coach feedback."
    )
    assert body["output_payload"]["target_user_or_customer"] == (
        "Badminton coaches and athletes."
    )
    assert body["output_payload"]["evidence_for_demand"] == [
        "Coach feedback workflows create a real user-facing need.",
    ]
    assert body["output_payload"]["missing_evidence"] == [
        "Confirm whether annotated badminton video data is already available.",
    ]
    assert body["output_payload"]["suggested_human_checklist"] == [
        "Confirm data ownership and annotation availability.",
    ]
    assert body["output_payload"]["go_or_no_go_recommendation"] == "go_with_human_review"
    assert body["evidence_payload"]["provider_name"] == "Example Provider"
    assert body["evidence_payload"]["can_run"] is True
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
    assert body["confidence"] == "unknown"
    assert body["summary"] == "No active model provider is available for this user."
    assert body["evidence_payload"]["can_run"] is False
    assert body["evidence_payload"]["blocking_reason"] == "missing_provider"
    assert body["evidence_payload"]["blocking_detail"] == (
        "Configure an active OpenAI-compatible or custom provider before running this stage."
    )


def test_run_literature_scout_blocks_until_demand_validation_completes(
    tmp_path,
    dev_admin_header_enabled: None,
) -> None:
    app = create_app(database_url=f"sqlite:///{tmp_path / 'literature-blocked.db'}")
    app.dependency_overrides[get_literature_scout_runner] = get_fake_literature_runner

    with TestClient(app) as client:
        register_and_login(client, "RUN-LIT-BLOCK", "lit-blocked@example.com")
        _, _, literature_stage_id, _ = create_quest_with_stages(client)

        response = client.post(f"/stages/{literature_stage_id}/run", json={})

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "blocked"
    assert body["summary"] == "Literature Scout is blocked until Demand validation is complete."
    assert body["evidence_payload"]["blocking_reason"] == "demand_validation_incomplete"
    assert body["evidence_payload"]["blocking_detail"] == (
        "Complete Demand validation before running Literature Scout."
    )


def test_run_literature_scout_completes_without_model_provider(
    tmp_path,
    dev_admin_header_enabled: None,
) -> None:
    app = create_app(database_url=f"sqlite:///{tmp_path / 'literature-run.db'}")
    app.dependency_overrides[get_literature_scout_runner] = get_fake_literature_runner

    with TestClient(app) as client:
        register_and_login(client, "RUN-LIT", "lit-runner@example.com")
        _, demand_stage_id, literature_stage_id, _ = create_quest_with_stages(client)
        running_response = client.patch(
            f"/stages/{demand_stage_id}",
            json={"status": "running"},
        )
        assert running_response.status_code == 200
        complete_response = client.patch(
            f"/stages/{demand_stage_id}",
            json={
                "human_approved": True,
                "output_payload": {"confidence": "medium"},
                "status": "complete",
                "summary": "Demand validation complete.",
            },
        )
        assert complete_response.status_code == 200

        response = client.post(f"/stages/{literature_stage_id}/run", json={})

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "complete"
    assert body["confidence"] == "medium"
    assert body["output_payload"]["confidence"] == "medium"
    assert body["input_payload"]["source"] == "openalex_works_api"
    assert body["output_payload"]["source"] == "openalex_works_api"
    assert body["output_payload"]["papers"][0]["openalex_id"] == "https://openalex.org/W123"
    assert body["evidence_payload"]["can_run"] is True


def test_run_gap_hypothesis_blocks_until_literature_scout_completes(
    tmp_path,
    dev_admin_header_enabled: None,
) -> None:
    app = create_app(database_url=f"sqlite:///{tmp_path / 'gap-blocked.db'}")
    app.dependency_overrides[get_gap_hypothesis_runner] = get_fake_gap_runner

    with TestClient(app) as client:
        register_and_login(client, "RUN-GAP-BLOCK", "gap-blocked@example.com")
        _, demand_stage_id, _, idea_stage_id = create_quest_with_stages(client)
        running_response = client.patch(
            f"/stages/{demand_stage_id}",
            json={"status": "running"},
        )
        assert running_response.status_code == 200
        complete_response = client.patch(
            f"/stages/{demand_stage_id}",
            json={
                "output_payload": {"confidence": "medium"},
                "status": "complete",
                "summary": "Demand validation complete.",
            },
        )
        assert complete_response.status_code == 200

        response = client.post(f"/stages/{idea_stage_id}/run", json={})

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "blocked"
    assert body["evidence_payload"]["blocking_reason"] == "gap_prerequisites_incomplete"
    assert body["evidence_payload"]["missing_prerequisites"] == ["Literature Scout"]


def test_run_gap_hypothesis_completes_and_selection_advances_quest(
    tmp_path,
    dev_admin_header_enabled: None,
) -> None:
    app = create_app(database_url=f"sqlite:///{tmp_path / 'gap-run.db'}")
    app.dependency_overrides[get_gap_hypothesis_runner] = get_fake_gap_runner

    with TestClient(app) as client:
        register_and_login(client, "RUN-GAP", "gap-runner@example.com")
        create_personal_provider(client)
        quest_id, demand_stage_id, literature_stage_id, idea_stage_id = create_quest_with_stages(
            client
        )
        demand_running_response = client.patch(
            f"/stages/{demand_stage_id}",
            json={"status": "running"},
        )
        assert demand_running_response.status_code == 200
        demand_complete_response = client.patch(
            f"/stages/{demand_stage_id}",
            json={
                "output_payload": {"confidence": "medium"},
                "status": "complete",
                "summary": "Demand validation complete.",
            },
        )
        assert demand_complete_response.status_code == 200
        literature_running_response = client.patch(
            f"/stages/{literature_stage_id}",
            json={"status": "running"},
        )
        assert literature_running_response.status_code == 200
        literature_complete_response = client.patch(
            f"/stages/{literature_stage_id}",
            json={
                "output_payload": {
                    "confidence": "medium",
                    "papers": [
                        {
                            "abstract_summary": "badminton recognition",
                            "authors": ["Researcher"],
                            "doi": "",
                            "limitations": ["Fast rallies remain difficult."],
                            "openalex_id": "https://openalex.org/W123",
                            "relevance_score": 100.0,
                            "reliability_level": "top_conference_or_journal",
                            "title": "Badminton recognition benchmark",
                            "url": "https://example.org/paper",
                            "venue": "CVPR",
                            "why_relevant": "Matches badminton recognition.",
                            "year": 2025,
                        }
                    ],
                },
                "status": "complete",
                "summary": "Literature scout complete.",
            },
        )
        assert literature_complete_response.status_code == 200

        run_response = client.post(f"/stages/{idea_stage_id}/run", json={})
        assert run_response.status_code == 200
        run_body = run_response.json()
        selected_payload = {
            **run_body["output_payload"],
            "selected_idea_ids": ["idea_1"],
            "selection_status": "selected_for_experiment_design",
        }
        selection_response = client.patch(
            f"/stages/{idea_stage_id}",
            json={
                "human_approved": True,
                "output_payload": selected_payload,
                "review_notes": "Selected idea_1 for experiment planning.",
            },
        )
        quest_response = client.get(f"/quests/{quest_id}")

    assert run_body["status"] == "complete"
    assert run_body["confidence"] == "medium"
    assert run_body["output_payload"]["ideas"][0]["idea_id"] == "idea_1"
    assert run_body["output_payload"]["ideas"][0]["based_on_which_papers"] == [
        "https://openalex.org/W123"
    ]
    assert run_body["evidence_payload"]["provider_name"] == "Example Provider"
    assert selection_response.status_code == 200
    selected_body = selection_response.json()
    assert selected_body["human_approved"] is True
    assert selected_body["output_payload"]["selected_idea_ids"] == ["idea_1"]
    assert quest_response.status_code == 200
    assert quest_response.json()["status"] == "lightweight_experiment"


def test_update_idea_stage_downgrades_manual_high_confidence(
    tmp_path,
    dev_admin_header_enabled: None,
) -> None:
    app = create_app(database_url=f"sqlite:///{tmp_path / 'idea-update-confidence.db'}")

    with TestClient(app) as client:
        register_and_login(client, "PATCH-IDEA-HIGH", "idea-patcher@example.com")
        _, _, _, idea_stage_id = create_quest_with_stages(client)

        response = client.patch(
            f"/stages/{idea_stage_id}",
            json={
                "output_payload": {
                    "confidence": "high",
                    "ideas": [],
                    "warnings": ["Existing warning."],
                },
                "summary": "Manual edit attempted high confidence.",
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["confidence"] == "medium"
    assert body["output_payload"]["confidence"] == "medium"
    assert body["output_payload"]["warnings"] == [
        "Existing warning.",
        "High confidence was downgraded because hypotheses have not been experimentally verified.",
    ]


def test_update_demand_validation_stage_downgrades_manual_high_confidence(
    tmp_path,
    dev_admin_header_enabled: None,
) -> None:
    app = create_app(database_url=f"sqlite:///{tmp_path / 'stage-update-confidence.db'}")

    with TestClient(app) as client:
        register_and_login(client, "PATCH-STAGE-HIGH", "patcher@example.com")
        stage_id = create_quest(client)

        response = client.patch(
            f"/stages/{stage_id}",
            json={
                "output_payload": {
                    "confidence": "high",
                    "demand_assessment": "strong",
                    "raw_response": "model-only response",
                    "risks": ["Existing risk."],
                },
                "summary": "Manual edit attempted high confidence.",
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["confidence"] == "medium"
    assert body["output_payload"]["confidence"] == "medium"
    assert body["output_payload"]["risks"] == ["Existing risk.", NO_EXTERNAL_VERIFICATION_RISK]
