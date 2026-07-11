from paper_meeting_writer_model_outputs import model_output_without_result_guardrails
from paper_meeting_writer_result_helpers import request_with_trusted_result
from pydantic import SecretStr

from noviscope.agents.paper_meeting_writer import parse_paper_meeting_writer_output
from noviscope.agents.paper_meeting_writer_output import build_stage_evidence_payload
from noviscope.agents.stage_runner import ModelProviderCredentials, StageRunContext
from noviscope.models.provider import ProviderKind
from noviscope.models.quest import Quest, StageCard


def test_stage_evidence_marks_verified_results_without_trusting_review_needed_results() -> None:
    output = parse_paper_meeting_writer_output(
        model_output_without_result_guardrails(),
        request_with_trusted_result(),
    )
    context = StageRunContext(
        provider=ModelProviderCredentials(
            api_key=SecretStr("sk-test"),
            base_url="https://api.example.com/v1",
            id="provider_1",
            kind=ProviderKind.OPENAI_COMPATIBLE,
            model="example-chat",
            name="Example Provider",
        ),
        quest=Quest(
            initial_direction="Badminton action recognition",
            title="Badminton action recognition",
        ),
        stage=StageCard(
            agent_id="paper_meeting_writer",
            quest_id="quest_1",
            title="Paper & meeting writer",
        ),
    )

    evidence_payload = build_stage_evidence_payload(context, output)

    assert evidence_payload["no_experiment_results"] is False
    assert evidence_payload["experiment_results_require_review"] is True
