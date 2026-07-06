import json

import httpx
from pydantic import SecretStr

from noviscope.agents.experiment_planner import (
    PLAN_ONLY_WARNING,
    ExperimentPlannerRequest,
    ExperimentPlannerStageRunner,
    OpenAICompatibleExperimentPlannerRunner,
    has_selected_idea,
    parse_experiment_plan_output,
)
from noviscope.agents.provider_chat import DEFAULT_MAX_TOKENS, ProviderChatClient
from noviscope.models.provider import ProviderKind
from noviscope.models.quest import StageCard, StageStatus


def build_request() -> ExperimentPlannerRequest:
    return ExperimentPlannerRequest(
        api_key=SecretStr("sk-test"),
        base_url="https://api.example.com/v1",
        code_repository="https://github.com/example/badminton-baseline",
        data_path="/data/badminton",
        environment_notes="Python 3.11, CUDA 12.1, one A800.",
        idea_stage_output={"selected_idea_ids": ["idea_1"]},
        initial_direction="Badminton action recognition",
        model="example-chat",
        provider_id="provider_1",
        provider_kind=ProviderKind.OPENAI_COMPATIBLE,
        provider_name="Example Provider",
        quest_title="Badminton action recognition",
        selected_ideas=[
            {
                "core_hypothesis": "Temporal consistency can reduce missed actions.",
                "idea_id": "idea_1",
                "idea_title": "Temporal consistency",
            }
        ],
        source_stage_ids={"idea_generator": "stage_idea"},
        stage_id="stage_experiment",
    )


def test_parse_experiment_plan_output_caps_confidence_and_marks_plan_only() -> None:
    raw_content = json.dumps(
        {
            "ablation_variables": ["temporal window size"],
            "baselines_to_reproduce": ["Baseline action recognizer"],
            "compute_requirements": "One A800 GPU.",
            "confidence": "high",
            "data_availability_status": "ready",
            "datasets_needed": ["/data/badminton"],
            "expected_figures": ["Failure case grid"],
            "expected_tables": ["Baseline and ablation table"],
            "failure_risks": ["Data labels may be noisy."],
            "first_runnable_script_plan": ["Build manifest", "Run baseline inference"],
            "metrics": ["Action accuracy"],
            "summary": "Plan the first baseline and ablation run.",
        }
    )

    output = parse_experiment_plan_output(raw_content, build_request())

    assert output.confidence == "medium"
    assert output.source_stage_ids == {"idea_generator": "stage_idea"}
    assert output.datasets_needed == ["/data/badminton"]
    assert output.first_runnable_script_plan == ["Build manifest", "Run baseline inference"]
    assert output.warnings == [PLAN_ONLY_WARNING]


def test_parse_experiment_plan_output_fails_closed_on_invalid_json() -> None:
    output = parse_experiment_plan_output("not json", build_request())

    assert output.confidence == "low"
    assert output.datasets_needed == []
    assert output.first_runnable_script_plan == []
    assert "not valid structured JSON" in output.summary
    assert PLAN_ONLY_WARNING in output.warnings


def test_experiment_runner_executes_anthropic_messages_api() -> None:
    captured_payload: dict[str, object] = {}
    model_response = {
        "ablation_variables": ["temporal window size"],
        "baselines_to_reproduce": ["Baseline action recognizer"],
        "compute_requirements": "One A800 GPU.",
        "confidence": "medium",
        "data_availability_status": "ready",
        "datasets_needed": ["/data/badminton"],
        "expected_figures": ["Failure case grid"],
        "expected_tables": ["Baseline and ablation table"],
        "failure_risks": ["Data labels may be noisy."],
        "first_runnable_script_plan": ["Build manifest", "Run baseline inference"],
        "metrics": ["Action accuracy"],
        "summary": "Plan the first baseline and ablation run.",
    }

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url == httpx.URL("https://api.anthropic.com/v1/messages")
        assert request.headers["x-api-key"] == "sk-test"
        assert request.headers["anthropic-version"] == "2023-06-01"
        captured_payload.update(json.loads(request.content))
        return httpx.Response(
            200,
            json={"content": [{"text": json.dumps(model_response), "type": "text"}]},
        )

    runner = OpenAICompatibleExperimentPlannerRunner(
        chat_client=ProviderChatClient(
            client_factory=lambda: httpx.Client(transport=httpx.MockTransport(handler))
        )
    )
    request = build_request().model_copy(
        update={
            "base_url": "https://api.anthropic.com/v1",
            "model": "claude-test-model",
            "provider_kind": ProviderKind.ANTHROPIC,
            "provider_name": "Anthropic",
        }
    )

    output = runner.run(request)

    assert output.summary == "Plan the first baseline and ablation run."
    assert PLAN_ONLY_WARNING in output.warnings
    assert captured_payload["model"] == "claude-test-model"
    assert captured_payload["max_tokens"] == DEFAULT_MAX_TOKENS
    assert "temperature" not in captured_payload


def test_experiment_stage_runner_supports_anthropic_provider() -> None:
    runner = ExperimentPlannerStageRunner(OpenAICompatibleExperimentPlannerRunner())

    assert ProviderKind.ANTHROPIC in runner.supported_provider_kinds


def test_has_selected_idea_requires_matching_idea_payload() -> None:
    stage = StageCard(
        agent_id="idea_generator",
        human_approved=True,
        output_payload={
            "ideas": [{"idea_id": "idea_2", "idea_title": "Different idea"}],
            "selected_idea_ids": ["idea_1"],
        },
        quest_id="quest_1",
        status=StageStatus.COMPLETE,
        title="Gap & hypothesis generator",
    )

    assert has_selected_idea(stage) is False
