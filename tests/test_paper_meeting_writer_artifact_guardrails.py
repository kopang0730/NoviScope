from fastapi.testclient import TestClient
from paper_meeting_writer_model_outputs import model_output_with_untrusted_result_sentinel
from paper_meeting_writer_result_helpers import (
    build_request_with_experiment_results,
    request_with_trusted_result,
)
from test_stage_run_api import (
    create_personal_provider,
    create_quest_with_stages,
    register_and_login,
)

from noviscope.agents.paper_meeting_writer import (
    HUMAN_REVIEW_NOTICE,
    NO_RESULTS_NOTICE,
    PaperMeetingWriterOutput,
    PaperMeetingWriterRequest,
    get_paper_meeting_writer_runner,
    parse_paper_meeting_writer_output,
)
from noviscope.agents.paper_meeting_writer_output import build_stage_output_payload
from noviscope.main import create_app

ARTIFACT_KEYS = (
    "chinese_research_brief_markdown",
    "english_research_brief_markdown",
    "meeting_outline_markdown",
    "ieee_paper_skeleton_markdown",
)
UNTRUSTED_SENTINEL = "UNTRUSTED_RESULT_99_7_F1"


def test_untrusted_model_result_text_never_enters_downloadable_artifacts() -> None:
    request = build_request_with_experiment_results().model_copy(
        update={"experiment_plan": {"summary": "Plan only."}}
    )

    output = parse_paper_meeting_writer_output(
        model_output_with_untrusted_result_sentinel(),
        request,
    )
    payload = build_stage_output_payload(output)

    assert all(UNTRUSTED_SENTINEL not in str(payload[key]) for key in ARTIFACT_KEYS)
    assert output.verified_facts == []
    assert all(NO_RESULTS_NOTICE in str(payload[key]) for key in ARTIFACT_KEYS)
    assert HUMAN_REVIEW_NOTICE in output.human_review_required


def test_downloadable_artifacts_render_only_trusted_result_facts() -> None:
    output = parse_paper_meeting_writer_output(
        model_output_with_untrusted_result_sentinel(),
        request_with_trusted_result(),
    )
    payload = build_stage_output_payload(output)

    for key in ARTIFACT_KEYS:
        content = str(payload[key])
        assert UNTRUSTED_SENTINEL not in content
        assert "run-20260707-baseline" in content
        assert "/data/noviscope/runs/run-20260707/metrics.json" in content
    assert output.verified_facts == [
        "Verified experiment result: Action classification accuracy = 78.4% "
        "on Badminton training clips v1 using Pose-based action classifier "
        "(run run-20260707-baseline; artifact "
        "/data/noviscope/runs/run-20260707/metrics.json)."
    ]


class SentinelPaperRunner:
    def run(self, request: PaperMeetingWriterRequest) -> PaperMeetingWriterOutput:
        return PaperMeetingWriterOutput(
            chinese_research_brief_markdown=UNTRUSTED_SENTINEL,
            confidence="high",
            english_research_brief_markdown=UNTRUSTED_SENTINEL,
            experiment_results_not_available=[],
            human_review_required=[],
            ieee_paper_skeleton_markdown=UNTRUSTED_SENTINEL,
            meeting_outline_markdown=UNTRUSTED_SENTINEL,
            model_generated_hypotheses=[],
            raw_response=UNTRUSTED_SENTINEL,
            source_stage_ids=request.source_stage_ids,
            summary="Generated untrusted output.",
            verified_facts=[UNTRUSTED_SENTINEL],
            warnings=[],
        )


def get_sentinel_paper_runner() -> SentinelPaperRunner:
    return SentinelPaperRunner()


def test_stage_run_and_download_never_publish_runner_markdown(
    tmp_path,
    dev_admin_header_enabled: None,
) -> None:
    app = create_app(database_url=f"sqlite:///{tmp_path / 'artifact-guardrail.db'}")
    app.dependency_overrides[get_paper_meeting_writer_runner] = get_sentinel_paper_runner

    with TestClient(app) as client:
        register_and_login(client, "ARTIFACT-GUARDRAIL", "artifact-guard@example.com")
        create_personal_provider(client)
        _, _, _, _, experiment_stage_id, paper_stage_id = create_quest_with_stages(client)
        assert (
            client.patch(f"/stages/{experiment_stage_id}", json={"status": "running"}).status_code
            == 200
        )
        assert (
            client.patch(
                f"/stages/{experiment_stage_id}",
                json={
                    "human_approved": True,
                    "output_payload": {"summary": "Experiment plan completed."},
                    "status": "complete",
                },
            ).status_code
            == 200
        )
        run_response = client.post(f"/stages/{paper_stage_id}/run", json={})
        download_response = client.get(
            f"/stages/{paper_stage_id}/artifacts/ieee_paper_skeleton_markdown/download"
        )

    assert run_response.status_code == 200
    output_payload = run_response.json()["output_payload"]
    assert all(UNTRUSTED_SENTINEL not in output_payload[key] for key in ARTIFACT_KEYS)
    assert output_payload["verified_facts"] == []
    assert output_payload["raw_response"] == UNTRUSTED_SENTINEL
    assert download_response.status_code == 200
    assert UNTRUSTED_SENTINEL not in download_response.text
