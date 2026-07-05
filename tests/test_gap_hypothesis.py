import json

from pydantic import SecretStr

from noviscope.agents.gap_hypothesis import (
    GapHypothesisRequest,
    GapHypothesisStageRunner,
    build_no_paper_output,
    parse_gap_hypothesis_output,
)
from noviscope.agents.stage_runner import ModelProviderCredentials, StageRunContext
from noviscope.models.provider import ProviderKind
from noviscope.models.quest import Quest, StageCard, StageStatus


class UnexpectedGapRunner:
    def run(self, request: GapHypothesisRequest):
        raise AssertionError("model runner should not be called without papers")


def test_parse_gap_hypothesis_output_caps_confidence_and_removes_unknown_refs() -> None:
    request = GapHypothesisRequest(
        api_key=SecretStr("sk-test"),
        base_url="https://api.example.com/v1",
        demand_validation={"demand_assessment": "plausible"},
        initial_direction="Badminton action recognition",
        model="example-chat",
        papers=[{"paper_ref": "https://openalex.org/W123", "title": "Badminton benchmark"}],
        provider_id="provider_1",
        provider_kind=ProviderKind.OPENAI_COMPATIBLE,
        provider_name="Example Provider",
        quest_title="Badminton action recognition",
        source_stage_ids={"demand_validation": "stage_demand", "literature_scout": "stage_lit"},
        stage_id="stage_gap",
    )
    raw_content = json.dumps(
        {
            "confidence": "high",
            "gaps": [
                {
                    "description": "Fast shuttlecock motion remains hard to track.",
                    "evidence_type": "paper_limitations",
                    "gap_title": "Fast motion gap",
                    "severity": "high",
                    "supporting_papers": ["https://openalex.org/W123", "made-up-paper"],
                }
            ],
            "ideas": [
                {
                    "application_value": "high",
                    "based_on_which_papers": ["https://openalex.org/W123", "made-up-paper"],
                    "confidence": "high",
                    "core_hypothesis": "Temporal consistency can reduce shuttlecock misses.",
                    "expected_improvement": "Lower missed detections in fast rallies.",
                    "experiment_feasibility": "medium",
                    "idea_id": "idea_1",
                    "idea_title": "Temporal shuttlecock recovery",
                    "novelty_risk": "medium",
                    "required_baseline": "Badminton benchmark detector.",
                    "required_data": "Annotated rally videos.",
                }
            ],
            "summary": "One evidence-linked idea was generated.",
        }
    )

    output = parse_gap_hypothesis_output(raw_content, request)

    assert output.confidence == "medium"
    assert output.gaps[0].supporting_papers == ["https://openalex.org/W123"]
    assert output.ideas[0].confidence == "medium"
    assert output.ideas[0].based_on_which_papers == ["https://openalex.org/W123"]
    assert output.selection_status == "pending_human_selection"
    assert output.warnings


def test_gap_stage_runner_does_not_generate_ideas_without_papers() -> None:
    quest = Quest(id="quest_1", title="No papers", initial_direction="No literature available")
    demand_stage = StageCard(
        id="stage_demand",
        agent_id="demand_validator",
        output_payload={"demand_assessment": "plausible"},
        quest_id=quest.id,
        status=StageStatus.COMPLETE,
        title="Demand validation",
    )
    literature_stage = StageCard(
        id="stage_lit",
        agent_id="literature_scout",
        output_payload={"papers": []},
        quest_id=quest.id,
        status=StageStatus.COMPLETE,
        title="Literature scout",
    )
    gap_stage = StageCard(
        id="stage_gap",
        agent_id="idea_generator",
        quest_id=quest.id,
        title="Gap & hypothesis generator",
    )
    runner = GapHypothesisStageRunner(UnexpectedGapRunner())

    result = runner.run(
        StageRunContext(
            provider=ModelProviderCredentials(
                api_key=SecretStr("sk-test"),
                base_url="https://api.example.com/v1",
                id="provider_1",
                kind=ProviderKind.OPENAI_COMPATIBLE,
                model="example-chat",
                name="Example Provider",
            ),
            quest=quest,
            stage=gap_stage,
            workflow_stages=(demand_stage, literature_stage, gap_stage),
        )
    )

    assert result.confidence == "low"
    assert result.output_payload["ideas"] == []
    assert result.output_payload["warnings"] == [
        "Literature Scout returned no papers; NoviScope did not fabricate ideas."
    ]


def test_build_no_paper_output_preserves_selection_gate() -> None:
    output = build_no_paper_output(
        {"demand_validation": "stage_demand", "literature_scout": "stage_lit"}
    )

    assert output.ideas == []
    assert output.selected_idea_ids == []
    assert output.selection_status == "pending_human_selection"
