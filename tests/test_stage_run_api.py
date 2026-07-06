from fastapi.testclient import TestClient
from sqlmodel import Session, select

from noviscope.agents.demand_validation import (
    DemandValidationOutput,
    DemandValidationRequest,
    DemandValidationRunner,
    get_demand_validation_runner,
)
from noviscope.agents.experiment_planner import (
    ExperimentPlannerRequest,
    ExperimentPlannerRunner,
    ExperimentPlanOutput,
    get_experiment_planner_runner,
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
from noviscope.agents.paper_meeting_writer import (
    PaperMeetingWriterOutput,
    PaperMeetingWriterRequest,
    PaperMeetingWriterRunner,
    get_paper_meeting_writer_runner,
)
from noviscope.core.stage_policy import (
    EXPERIMENT_PLANNER_AGENT_ID,
    NO_EXPERIMENT_VERIFICATION_RISK,
    NO_EXTERNAL_VERIFICATION_RISK,
    PAPER_MEETING_WRITER_AGENT_ID,
)
from noviscope.db.session import create_db_engine
from noviscope.main import create_app
from noviscope.models.user import User, UserRole

DEV_ADMIN_HEADERS = {"X-NoviScope-Dev-Admin": "test-dev-admin-token-0123456789abcdef"}
HUMAN_DEMAND_EVIDENCE_PAYLOAD = {
    "human_demand_sources": ["Interview note: coaches need objective badminton feedback."],
    "human_demand_verdict": "verified",
}


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


class FakeExperimentPlannerRunner:
    def run(self, request: ExperimentPlannerRequest) -> ExperimentPlanOutput:
        return ExperimentPlanOutput(
            ablation_variables=[
                "Temporal consistency window size",
                "Detection confidence threshold",
            ],
            baselines_to_reproduce=[
                "Reproduce the selected paper baseline on the provided badminton clips.",
            ],
            compute_requirements="One A800 GPU is enough for the first reproducibility run.",
            confidence="medium",
            data_availability_status="ready",
            datasets_needed=[request.data_path],
            expected_figures=[
                "Failure case grid for fast rallies.",
            ],
            expected_tables=[
                "Baseline versus temporal consistency ablation table.",
            ],
            failure_risks=[
                "Annotation quality may limit action classification accuracy.",
            ],
            first_runnable_script_plan=[
                "Create a dataset manifest from the provided data path.",
                "Run baseline inference from the provided code repository.",
                "Log metrics and failure cases without claiming paper-level results yet.",
            ],
            metrics=["Action classification accuracy", "Frame-level temporal consistency"],
            raw_response="fake experiment plan response",
            source_stage_ids=request.source_stage_ids,
            summary="Generated a plan-only experiment design for the selected idea.",
            warnings=[],
        )


class FakePaperMeetingWriterRunner:
    def run(self, request: PaperMeetingWriterRequest) -> PaperMeetingWriterOutput:
        return PaperMeetingWriterOutput(
            chinese_research_brief_markdown=(
                "# 中文研究 Brief\n\n"
                "## 已验证事实\n- 需求场景来自羽毛球训练反馈。\n\n"
                "## 未完成实验\n- 当前还没有真实实验结果。"
            ),
            confidence="medium",
            english_research_brief_markdown=(
                "# Research Brief\n\n"
                "## Verified Facts\n- The demand scenario is badminton coach feedback.\n\n"
                "## Experiment Results\n- Not available yet."
            ),
            experiment_results_not_available=["Baseline and ablation metrics are not available."],
            human_review_required=["Confirm whether the selected idea is worth writing up."],
            ieee_paper_skeleton_markdown=(
                "# IEEE Paper Skeleton\n\n"
                "## Abstract\nTBD after experiments.\n\n"
                "## Results\nNo experiment results are available yet."
            ),
            meeting_outline_markdown=(
                "# Group Meeting Outline\n\n"
                "1. Real demand\n2. Literature evidence\n3. Experiment plan"
            ),
            model_generated_hypotheses=[
                "Temporal consistency may reduce missed badminton actions.",
            ],
            raw_response="fake paper writer response",
            source_stage_ids=request.source_stage_ids,
            summary="Generated four traceable Markdown artifacts.",
            verified_facts=[
                "The retrieved paper metadata includes a badminton benchmark.",
            ],
            warnings=[],
        )


def get_fake_runner() -> DemandValidationRunner:
    return FakeDemandValidationRunner()


def get_fake_literature_runner() -> LiteratureScoutStageRunner:
    return LiteratureScoutStageRunner(FakeOpenAlexClient(), current_year=2026)


def get_fake_gap_runner() -> GapHypothesisRunner:
    return FakeGapHypothesisRunner()


def get_fake_experiment_runner() -> ExperimentPlannerRunner:
    return FakeExperimentPlannerRunner()


def get_fake_paper_runner() -> PaperMeetingWriterRunner:
    return FakePaperMeetingWriterRunner()


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


def promote_user_to_admin(database_url: str, email: str) -> None:
    engine = create_db_engine(database_url)
    with Session(engine) as session:
        user = session.exec(select(User).where(User.email == email)).one()
        user.role = UserRole.ADMIN
        session.add(user)
        session.commit()


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


def create_personal_anthropic_provider(client: TestClient) -> str:
    response = client.post(
        "/providers",
        json={
            "api_key": "sk-ant-test",
            "base_url": "https://api.anthropic.com/v1",
            "default_model": "claude-test-model",
            "kind": "anthropic",
            "name": "Anthropic Provider",
            "scope": "personal",
        },
    )
    assert response.status_code == 201
    return response.json()["id"]


def create_shared_provider(client: TestClient) -> str:
    response = client.post(
        "/providers",
        json={
            "api_key": "sk-shared",
            "base_url": "https://api.example.com/v1",
            "default_model": "example-chat",
            "kind": "openai_compatible",
            "name": "Shared Provider",
            "scope": "shared",
        },
    )
    assert response.status_code == 201
    return response.json()["id"]


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


def create_quest_with_stages(client: TestClient) -> tuple[str, str, str, str, str, str]:
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
    experiment_stage = next(
        stage for stage in stages if stage["agent_id"] == EXPERIMENT_PLANNER_AGENT_ID
    )
    paper_stage = next(
        stage for stage in stages if stage["agent_id"] == PAPER_MEETING_WRITER_AGENT_ID
    )
    return (
        quest_id,
        demand_stage["id"],
        literature_stage["id"],
        idea_stage["id"],
        experiment_stage["id"],
        paper_stage["id"],
    )


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


def test_run_demand_validation_stage_completes_with_anthropic_provider(
    tmp_path,
    dev_admin_header_enabled: None,
) -> None:
    app = create_app(database_url=f"sqlite:///{tmp_path / 'stage-run-anthropic.db'}")
    app.dependency_overrides[get_demand_validation_runner] = get_fake_runner

    with TestClient(app) as client:
        register_and_login(client, "RUN-STAGE-ANTHROPIC", "anthropic@example.com")
        provider_id = create_personal_anthropic_provider(client)
        stage_id = create_quest(client)

        response = client.post(f"/stages/{stage_id}/run", json={"provider_id": provider_id})

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "complete"
    assert body["input_payload"]["provider_id"] == provider_id
    assert body["input_payload"]["provider_name"] == "Anthropic Provider"
    assert body["input_payload"]["provider_model"] == "claude-test-model"


def test_run_demand_validation_uses_agent_default_provider_model(
    tmp_path,
    dev_admin_header_enabled: None,
) -> None:
    database_url = f"sqlite:///{tmp_path / 'stage-run-assignment.db'}"
    app = create_app(database_url=database_url)
    app.dependency_overrides[get_demand_validation_runner] = get_fake_runner

    with TestClient(app) as client:
        register_and_login(client, "RUN-ASSIGN-ADMIN", "admin@example.com")
        promote_user_to_admin(database_url, "admin@example.com")
        provider_id = create_shared_provider(client)
        assignment_response = client.put(
            "/agent-assignments/demand_validator",
            json={"model_name": "assigned-model", "provider_id": provider_id},
        )
        assert assignment_response.status_code == 200
        client.post("/auth/logout")

        register_and_login(client, "RUN-ASSIGN-MEMBER", "member@example.com")
        stage_id = create_quest(client)

        response = client.post(f"/stages/{stage_id}/run", json={})

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "complete"
    assert body["input_payload"]["provider_id"] == provider_id
    assert body["input_payload"]["provider_name"] == "Shared Provider"
    assert body["input_payload"]["provider_model"] == "assigned-model"
    assert body["evidence_payload"]["provider_model"] == "assigned-model"


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
        "Configure an active supported provider before running this stage."
    )


def test_run_literature_scout_blocks_until_demand_validation_completes(
    tmp_path,
    dev_admin_header_enabled: None,
) -> None:
    app = create_app(database_url=f"sqlite:///{tmp_path / 'literature-blocked.db'}")
    app.dependency_overrides[get_literature_scout_runner] = get_fake_literature_runner

    with TestClient(app) as client:
        register_and_login(client, "RUN-LIT-BLOCK", "lit-blocked@example.com")
        _, _, literature_stage_id, _, _, _ = create_quest_with_stages(client)

        response = client.post(f"/stages/{literature_stage_id}/run", json={})

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "blocked"
    assert body["summary"] == "Literature Scout is blocked until Demand validation is complete."
    assert body["evidence_payload"]["blocking_reason"] == "demand_validation_incomplete"
    assert body["evidence_payload"]["blocking_detail"] == (
        "Complete Demand validation before running Literature Scout."
    )


def test_run_literature_scout_blocks_until_demand_validation_is_approved(
    tmp_path,
    dev_admin_header_enabled: None,
) -> None:
    app = create_app(database_url=f"sqlite:///{tmp_path / 'literature-review-blocked.db'}")
    app.dependency_overrides[get_demand_validation_runner] = get_fake_runner
    app.dependency_overrides[get_literature_scout_runner] = get_fake_literature_runner

    with TestClient(app) as client:
        register_and_login(client, "RUN-LIT-REVIEW-BLOCK", "lit-review@example.com")
        create_personal_provider(client)
        _, demand_stage_id, literature_stage_id, _, _, _ = create_quest_with_stages(client)
        complete_response = client.post(f"/stages/{demand_stage_id}/run", json={})
        assert complete_response.status_code == 200
        assert complete_response.json()["status"] == "complete"
        assert complete_response.json()["human_approved"] is None

        response = client.post(f"/stages/{literature_stage_id}/run", json={})

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "blocked"
    assert body["summary"] == (
        "Literature scout is blocked until Demand validation is human-approved."
    )
    assert body["evidence_payload"]["blocking_reason"] == "demand_validation_review_required"
    assert body["evidence_payload"]["blocking_detail"] == (
        "Approve Demand validation before running Literature scout. If the demand was "
        "rejected, revise or rerun Demand validation first."
    )


def test_run_literature_scout_blocks_until_human_demand_evidence_is_recorded(
    tmp_path,
    dev_admin_header_enabled: None,
) -> None:
    app = create_app(database_url=f"sqlite:///{tmp_path / 'literature-evidence-blocked.db'}")
    app.dependency_overrides[get_literature_scout_runner] = get_fake_literature_runner

    with TestClient(app) as client:
        register_and_login(client, "RUN-LIT-EVIDENCE-BLOCK", "lit-evidence@example.com")
        _, demand_stage_id, literature_stage_id, _, _, _ = create_quest_with_stages(client)
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
    assert body["status"] == "blocked"
    assert body["summary"] == (
        "Literature scout is blocked until human demand evidence is recorded."
    )
    assert body["evidence_payload"]["blocking_reason"] == "demand_evidence_review_required"
    assert body["evidence_payload"]["blocking_detail"] == (
        "Record at least one plausible or verified human demand evidence source before "
        "running Literature scout."
    )


def test_run_literature_scout_completes_without_model_provider(
    tmp_path,
    dev_admin_header_enabled: None,
) -> None:
    app = create_app(database_url=f"sqlite:///{tmp_path / 'literature-run.db'}")
    app.dependency_overrides[get_literature_scout_runner] = get_fake_literature_runner

    with TestClient(app) as client:
        register_and_login(client, "RUN-LIT", "lit-runner@example.com")
        _, demand_stage_id, literature_stage_id, _, _, _ = create_quest_with_stages(client)
        running_response = client.patch(
            f"/stages/{demand_stage_id}",
            json={"status": "running"},
        )
        assert running_response.status_code == 200
        complete_response = client.patch(
            f"/stages/{demand_stage_id}",
            json={
                "human_approved": True,
                "evidence_payload": HUMAN_DEMAND_EVIDENCE_PAYLOAD,
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
    assert body["evidence_payload"]["provider_id"] == "server_openalex"
    assert body["evidence_payload"]["provider_model"] == "openalex-works"
    assert body["evidence_payload"]["provider_name"] == "OpenAlex"


def test_run_gap_hypothesis_blocks_until_literature_scout_completes(
    tmp_path,
    dev_admin_header_enabled: None,
) -> None:
    app = create_app(database_url=f"sqlite:///{tmp_path / 'gap-blocked.db'}")
    app.dependency_overrides[get_gap_hypothesis_runner] = get_fake_gap_runner

    with TestClient(app) as client:
        register_and_login(client, "RUN-GAP-BLOCK", "gap-blocked@example.com")
        _, demand_stage_id, _, idea_stage_id, _, _ = create_quest_with_stages(client)
        running_response = client.patch(
            f"/stages/{demand_stage_id}",
            json={"status": "running"},
        )
        assert running_response.status_code == 200
        complete_response = client.patch(
            f"/stages/{demand_stage_id}",
            json={
                "human_approved": True,
                "evidence_payload": HUMAN_DEMAND_EVIDENCE_PAYLOAD,
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
        (
            quest_id,
            demand_stage_id,
            literature_stage_id,
            idea_stage_id,
            _,
            _,
        ) = create_quest_with_stages(client)
        demand_running_response = client.patch(
            f"/stages/{demand_stage_id}",
            json={"status": "running"},
        )
        assert demand_running_response.status_code == 200
        demand_complete_response = client.patch(
            f"/stages/{demand_stage_id}",
            json={
                "human_approved": True,
                "evidence_payload": HUMAN_DEMAND_EVIDENCE_PAYLOAD,
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


def test_run_experiment_planner_blocks_until_idea_selection(
    tmp_path,
    dev_admin_header_enabled: None,
) -> None:
    app = create_app(database_url=f"sqlite:///{tmp_path / 'experiment-prereq-block.db'}")

    with TestClient(app) as client:
        register_and_login(client, "RUN-EXP-BLOCK", "exp-blocked@example.com")
        _, _, _, _, experiment_stage_id, _ = create_quest_with_stages(client)

        response = client.post(f"/stages/{experiment_stage_id}/run", json={})

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "blocked"
    assert body["summary"] == "Experiment Planner is blocked until a generated idea is selected."
    assert body["evidence_payload"]["blocking_reason"] == (
        "experiment_prerequisites_incomplete"
    )


def test_run_experiment_planner_blocks_without_setup_inputs(
    tmp_path,
    dev_admin_header_enabled: None,
) -> None:
    app = create_app(database_url=f"sqlite:///{tmp_path / 'experiment-input-block.db'}")

    with TestClient(app) as client:
        register_and_login(client, "RUN-EXP-INPUT-BLOCK", "exp-input@example.com")
        _, _, _, idea_stage_id, experiment_stage_id, _ = create_quest_with_stages(client)
        running_response = client.patch(
            f"/stages/{idea_stage_id}",
            json={"status": "running"},
        )
        assert running_response.status_code == 200
        complete_response = client.patch(
            f"/stages/{idea_stage_id}",
            json={
                "human_approved": True,
                "output_payload": {
                    "confidence": "medium",
                    "ideas": [{"idea_id": "idea_1", "idea_title": "Temporal idea"}],
                    "selected_idea_ids": ["idea_1"],
                    "selection_status": "selected_for_experiment_design",
                },
                "status": "complete",
                "summary": "Idea selected.",
            },
        )
        assert complete_response.status_code == 200

        response = client.post(f"/stages/{experiment_stage_id}/run", json={})

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "blocked"
    assert body["summary"] == "Experiment Planner needs experiment setup inputs before it can run."
    assert body["evidence_payload"]["blocking_reason"] == "missing_experiment_inputs"
    assert body["evidence_payload"]["missing_inputs"] == [
        "data_path",
        "code_repository",
        "environment_notes",
    ]


def test_run_experiment_planner_completes_with_setup_inputs_and_advances_after_review(
    tmp_path,
    dev_admin_header_enabled: None,
) -> None:
    app = create_app(database_url=f"sqlite:///{tmp_path / 'experiment-run.db'}")
    app.dependency_overrides[get_experiment_planner_runner] = get_fake_experiment_runner

    with TestClient(app) as client:
        register_and_login(client, "RUN-EXP", "exp-runner@example.com")
        create_personal_provider(client)
        quest_id, _, _, idea_stage_id, experiment_stage_id, _ = create_quest_with_stages(client)
        idea_running_response = client.patch(
            f"/stages/{idea_stage_id}",
            json={"status": "running"},
        )
        assert idea_running_response.status_code == 200
        idea_complete_response = client.patch(
            f"/stages/{idea_stage_id}",
            json={
                "human_approved": True,
                "output_payload": {
                    "confidence": "medium",
                    "ideas": [
                        {
                            "application_value": "high",
                            "based_on_which_papers": ["https://openalex.org/W123"],
                            "confidence": "medium",
                            "core_hypothesis": (
                                "Temporal consistency can reduce missed badminton actions."
                            ),
                            "expected_improvement": "Better action labels.",
                            "experiment_feasibility": "medium",
                            "idea_id": "idea_1",
                            "idea_title": "Temporal consistency for fast rallies",
                            "novelty_risk": "medium",
                            "required_baseline": "Badminton benchmark.",
                            "required_data": "Annotated badminton clips.",
                        }
                    ],
                    "selected_idea_ids": ["idea_1"],
                    "selection_status": "selected_for_experiment_design",
                },
                "status": "complete",
                "summary": "Idea selected.",
            },
        )
        assert idea_complete_response.status_code == 200
        setup_response = client.patch(
            f"/stages/{experiment_stage_id}",
            json={
                "input_payload": {
                    "code_repository": "https://github.com/example/badminton-baseline",
                    "data_path": "/data/badminton/train",
                    "environment_notes": "Python 3.11, CUDA 12.1, two A800 GPUs available.",
                }
            },
        )
        assert setup_response.status_code == 200

        run_response = client.post(f"/stages/{experiment_stage_id}/run", json={})
        assert run_response.status_code == 200
        run_body = run_response.json()
        review_response = client.patch(
            f"/stages/{experiment_stage_id}",
            json={
                "human_approved": True,
                "review_notes": "Plan is ready for the first baseline reproduction.",
            },
        )
        quest_response = client.get(f"/quests/{quest_id}")

    assert run_body["status"] == "complete"
    assert run_body["confidence"] == "medium"
    assert run_body["output_payload"]["data_availability_status"] == "ready"
    assert run_body["output_payload"]["datasets_needed"] == ["/data/badminton/train"]
    assert run_body["output_payload"]["first_runnable_script_plan"]
    assert run_body["evidence_payload"]["plan_only"] is True
    assert run_body["evidence_payload"]["no_experiment_results"] is True
    assert review_response.status_code == 200
    assert quest_response.status_code == 200
    assert quest_response.json()["status"] == "full_experiment"


def test_run_paper_writer_blocks_until_experiment_planner_completes(
    tmp_path,
    dev_admin_header_enabled: None,
) -> None:
    app = create_app(database_url=f"sqlite:///{tmp_path / 'paper-writer-block.db'}")

    with TestClient(app) as client:
        register_and_login(client, "RUN-PAPER-BLOCK", "paper-blocked@example.com")
        _, _, _, _, _, paper_stage_id = create_quest_with_stages(client)

        response = client.post(f"/stages/{paper_stage_id}/run", json={})

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "blocked"
    assert body["summary"] == (
        "Paper & Meeting Writer is blocked until Experiment Planner completes."
    )
    assert body["evidence_payload"]["blocking_reason"] == "paper_prerequisites_incomplete"


def test_run_paper_writer_blocks_until_experiment_planner_is_approved(
    tmp_path,
    dev_admin_header_enabled: None,
) -> None:
    app = create_app(database_url=f"sqlite:///{tmp_path / 'paper-writer-review.db'}")

    with TestClient(app) as client:
        register_and_login(client, "RUN-PAPER-REVIEW", "paper-review@example.com")
        _, _, _, _, experiment_stage_id, paper_stage_id = create_quest_with_stages(client)
        experiment_running_response = client.patch(
            f"/stages/{experiment_stage_id}",
            json={"status": "running"},
        )
        assert experiment_running_response.status_code == 200
        experiment_complete_response = client.patch(
            f"/stages/{experiment_stage_id}",
            json={
                "output_payload": {
                    "confidence": "medium",
                    "data_availability_status": "ready",
                    "first_runnable_script_plan": ["Run baseline inference."],
                    "summary": "Experiment plan completed.",
                },
                "status": "complete",
                "summary": "Experiment plan completed.",
            },
        )
        assert experiment_complete_response.status_code == 200

        response = client.post(f"/stages/{paper_stage_id}/run", json={})

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "blocked"
    assert body["summary"] == (
        "Paper & Meeting Writer is blocked until Experiment Planner is human-approved."
    )
    assert body["evidence_payload"]["blocking_reason"] == (
        "experiment_planner_review_required"
    )


def test_run_paper_writer_completes_with_markdown_artifacts_and_advances_after_review(
    tmp_path,
    dev_admin_header_enabled: None,
) -> None:
    app = create_app(database_url=f"sqlite:///{tmp_path / 'paper-writer-run.db'}")
    app.dependency_overrides[get_paper_meeting_writer_runner] = get_fake_paper_runner

    with TestClient(app) as client:
        register_and_login(client, "RUN-PAPER", "paper-runner@example.com")
        create_personal_provider(client)
        quest_id, _, _, _, experiment_stage_id, paper_stage_id = create_quest_with_stages(
            client
        )
        experiment_running_response = client.patch(
            f"/stages/{experiment_stage_id}",
            json={"status": "running"},
        )
        assert experiment_running_response.status_code == 200
        experiment_complete_response = client.patch(
            f"/stages/{experiment_stage_id}",
            json={
                "output_payload": {
                    "confidence": "medium",
                    "data_availability_status": "ready",
                    "first_runnable_script_plan": ["Run baseline inference."],
                    "summary": "Experiment plan completed.",
                },
                "status": "complete",
                "summary": "Experiment plan completed.",
            },
        )
        assert experiment_complete_response.status_code == 200
        experiment_review_response = client.patch(
            f"/stages/{experiment_stage_id}",
            json={
                "human_approved": True,
                "review_notes": "Experiment plan is ready for draft artifact generation.",
            },
        )
        assert experiment_review_response.status_code == 200

        run_response = client.post(f"/stages/{paper_stage_id}/run", json={})
        assert run_response.status_code == 200
        run_body = run_response.json()
        review_response = client.patch(
            f"/stages/{paper_stage_id}",
            json={
                "human_approved": True,
                "review_notes": "Draft package is ready for group discussion.",
            },
        )
        quest_response = client.get(f"/quests/{quest_id}")

    assert run_body["status"] == "complete"
    assert run_body["confidence"] == "medium"
    assert run_body["output_payload"]["chinese_research_brief_markdown"].startswith(
        "# 中文研究 Brief"
    )
    assert run_body["output_payload"]["english_research_brief_markdown"].startswith(
        "# Research Brief"
    )
    assert run_body["output_payload"]["meeting_outline_markdown"].startswith(
        "# Group Meeting Outline"
    )
    assert run_body["output_payload"]["ieee_paper_skeleton_markdown"].startswith(
        "# IEEE Paper Skeleton"
    )
    assert run_body["output_payload"]["experiment_results_not_available"]
    assert run_body["output_payload"]["human_review_required"]
    assert run_body["evidence_payload"]["artifact_count"] == 4
    assert run_body["evidence_payload"]["download_format"] == "markdown"
    assert run_body["evidence_payload"]["no_experiment_results"] is True
    assert review_response.status_code == 200
    assert quest_response.status_code == 200
    assert quest_response.json()["status"] == "writing"


def test_update_idea_stage_downgrades_manual_high_confidence(
    tmp_path,
    dev_admin_header_enabled: None,
) -> None:
    app = create_app(database_url=f"sqlite:///{tmp_path / 'idea-update-confidence.db'}")

    with TestClient(app) as client:
        register_and_login(client, "PATCH-IDEA-HIGH", "idea-patcher@example.com")
        _, _, _, idea_stage_id, _, _ = create_quest_with_stages(client)

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


def test_update_experiment_planner_stage_downgrades_manual_high_confidence(
    tmp_path,
    dev_admin_header_enabled: None,
) -> None:
    app = create_app(database_url=f"sqlite:///{tmp_path / 'experiment-update-confidence.db'}")

    with TestClient(app) as client:
        register_and_login(client, "PATCH-EXP-HIGH", "experiment-patcher@example.com")
        _, _, _, _, experiment_stage_id, _ = create_quest_with_stages(client)

        response = client.patch(
            f"/stages/{experiment_stage_id}",
            json={
                "output_payload": {
                    "confidence": "high",
                    "summary": "Manual edit attempted high confidence.",
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
        NO_EXPERIMENT_VERIFICATION_RISK,
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
