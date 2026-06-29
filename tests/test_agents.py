import pytest

from noviscope.agents.registry import AGENT_REGISTRY, get_agent_spec
from noviscope.models.agent import ToolPermission


def test_registry_has_nine_agents():
    assert len(AGENT_REGISTRY) == 9


def test_code_runner_is_only_agent_with_run_code_permission():
    runners = [
        spec.agent_id
        for spec in AGENT_REGISTRY.values()
        if ToolPermission.RUN_CODE in spec.tool_permissions
    ]
    assert runners == ["code_runner"]


def test_writer_cannot_run_code_or_freely_search_github():
    writer = get_agent_spec("paper_meeting_writer")
    assert ToolPermission.RUN_CODE not in writer.tool_permissions
    assert ToolPermission.GITHUB_SEARCH not in writer.tool_permissions


def test_registry_keys_match_agent_ids():
    assert [spec.agent_id for spec in AGENT_REGISTRY.values()] == list(AGENT_REGISTRY)


def test_agent_specs_are_immutable():
    writer = get_agent_spec("paper_meeting_writer")

    with pytest.raises(ValueError, match="frozen"):
        writer.tool_permissions = (*writer.tool_permissions, ToolPermission.RUN_CODE)


def test_agent_registry_is_immutable():
    with pytest.raises(TypeError):
        AGENT_REGISTRY["paper_meeting_writer"] = get_agent_spec("code_runner")


def test_agent_permission_json_order_is_stable():
    runner = get_agent_spec("code_runner")

    assert runner.model_dump(mode="json")["tool_permissions"] == [
        "web_search",
        "read_pdf",
        "github_search",
        "write_files",
        "run_code",
        "read_experiment_results",
    ]
