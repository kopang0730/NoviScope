from noviscope.api.workflow_canvas import get_workflow_canvas_template


def test_workflow_canvas_template_exposes_agent_nodes_and_edges() -> None:
    # Given: the default NoviScope workflow canvas contract.

    # When: the frontend requests the default workflow canvas template.
    body = get_workflow_canvas_template()

    # Then: the response can render the research team graph without guessing.
    assert body.entry_agent_id == "demand_validator"
    assert body.terminal_agent_id == "paper_meeting_writer"
    assert body.core_flow_agent_ids == (
        "demand_validator",
        "literature_scout",
        "idea_generator",
        "experiment_planner",
        "paper_meeting_writer",
    )
    assert len(body.nodes) == 9
    assert body.nodes[0].model_dump(mode="json") == {
        "agent_id": "demand_validator",
        "canvas_role": "core_stage",
        "column": 1,
        "display_name": "Demand Validator",
        "lane_id": "validation",
        "row": 1,
    }
    edge_payloads = [edge.model_dump(mode="json") for edge in body.edges]
    assert {
        "edge_kind": "human_gate",
        "from_agent_id": "demand_validator",
        "label": "Demand review gate",
        "to_agent_id": "literature_scout",
    } in edge_payloads
    assert {
        "edge_kind": "planned_extension",
        "from_agent_id": "experiment_planner",
        "label": "Future automated execution",
        "to_agent_id": "code_runner",
    } in edge_payloads
    assert [lane.model_dump(mode="json") for lane in body.lanes] == [
        {
            "description": "Demand reality checks and problem framing.",
            "lane_id": "validation",
            "title": "Validation",
        },
        {
            "description": "Literature, gaps, hypotheses, and idea selection.",
            "lane_id": "research",
            "title": "Research",
        },
        {
            "description": "Experiment planning, future code runs, and evidence audits.",
            "lane_id": "experiment",
            "title": "Experiment",
        },
        {
            "description": "Traceable paper and meeting artifacts.",
            "lane_id": "artifact",
            "title": "Artifact",
        },
    ]
