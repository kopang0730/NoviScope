from collections.abc import Mapping
from types import MappingProxyType

from pydantic import BaseModel, ConfigDict, field_serializer

from noviscope.models.agent import ToolPermission


class AgentSpec(BaseModel):
    model_config = ConfigDict(frozen=True)

    agent_id: str
    display_name: str
    goal: str
    outputs: tuple[str, ...]
    tool_permissions: tuple[ToolPermission, ...]
    constraints: tuple[str, ...]

    @field_serializer("tool_permissions")
    def serialize_tool_permissions(self, value: tuple[ToolPermission, ...]) -> list[str]:
        return [permission.value for permission in value]


AGENT_REGISTRY: Mapping[str, AgentSpec] = MappingProxyType(
    {
        "demand_validator": AgentSpec(
            agent_id="demand_validator",
            display_name="Demand Validator",
            goal="Validate whether a direction reflects a real application demand.",
            outputs=("demand_validation_report", "demand_confidence", "source_risk_list"),
            tool_permissions=(
                ToolPermission.WEB_SEARCH,
                ToolPermission.READ_PDF,
                ToolPermission.GITHUB_SEARCH,
                ToolPermission.WRITE_FILES,
            ),
            constraints=(
                "Weak sources must be marked low_confidence.",
                "Experiment stages require a user demand-review decision.",
            ),
        ),
        "research_refiner": AgentSpec(
            agent_id="research_refiner",
            display_name="Research Refiner",
            goal="Convert a broad direction into a scoped computer-vision research question.",
            outputs=("research_question_brief", "scope", "keywords"),
            tool_permissions=(ToolPermission.READ_PDF, ToolPermission.WRITE_FILES),
            constraints=("Do not produce paper conclusions.",),
        ),
        "literature_scout": AgentSpec(
            agent_id="literature_scout",
            display_name="Literature Scout",
            goal="Build a paper, code, dataset, and baseline map.",
            outputs=("bibliography_matrix", "method_taxonomy", "baseline_candidates"),
            tool_permissions=(
                ToolPermission.WEB_SEARCH,
                ToolPermission.READ_PDF,
                ToolPermission.GITHUB_SEARCH,
                ToolPermission.WRITE_FILES,
            ),
            constraints=("Every core paper requires URL or DOI, venue, and year.",),
        ),
        "gap_analyst": AgentSpec(
            agent_id="gap_analyst",
            display_name="Gap Analyst",
            goal="Identify limitations, uncovered scenarios, and improvement space.",
            outputs=("gap_matrix", "limitation_map", "application_constraint_map"),
            tool_permissions=(
                ToolPermission.WEB_SEARCH,
                ToolPermission.READ_PDF,
                ToolPermission.GITHUB_SEARCH,
                ToolPermission.WRITE_FILES,
            ),
            constraints=("Separate cited limitations from system inferences.",),
        ),
        "idea_generator": AgentSpec(
            agent_id="idea_generator",
            display_name="Idea Generator",
            goal="Generate evidence-linked research hypotheses and candidate ideas.",
            outputs=("candidate_ideas", "idea_risk_table"),
            tool_permissions=(ToolPermission.READ_PDF, ToolPermission.WRITE_FILES),
            constraints=("Every idea must include an experiment that could falsify it.",),
        ),
        "experiment_planner": AgentSpec(
            agent_id="experiment_planner",
            display_name="Experiment Planner",
            goal="Turn selected ideas into lightweight and full experiment plans.",
            outputs=("experiment_plan", "ablation_plan", "metric_plan"),
            tool_permissions=(
                ToolPermission.WEB_SEARCH,
                ToolPermission.READ_PDF,
                ToolPermission.GITHUB_SEARCH,
                ToolPermission.WRITE_FILES,
                ToolPermission.READ_EXPERIMENT_RESULTS,
            ),
            constraints=("Do not execute code.",),
        ),
        "code_runner": AgentSpec(
            agent_id="code_runner",
            display_name="Code Runner",
            goal="Run local reproduction, training, evaluation, and ablation jobs.",
            outputs=("experiment_provenance", "run_logs", "metric_records"),
            tool_permissions=(
                ToolPermission.WEB_SEARCH,
                ToolPermission.READ_PDF,
                ToolPermission.GITHUB_SEARCH,
                ToolPermission.WRITE_FILES,
                ToolPermission.RUN_CODE,
                ToolPermission.READ_EXPERIMENT_RESULTS,
            ),
            constraints=("Private code, data, logs, and checkpoints must not be uploaded.",),
        ),
        "evidence_auditor": AgentSpec(
            agent_id="evidence_auditor",
            display_name="Evidence Auditor",
            goal="Audit source truth, claim-reference alignment, and experiment-claim alignment.",
            outputs=("source_verification_report", "claim_alignment_report", "blocking_issues"),
            tool_permissions=(
                ToolPermission.WEB_SEARCH,
                ToolPermission.READ_PDF,
                ToolPermission.GITHUB_SEARCH,
                ToolPermission.WRITE_FILES,
                ToolPermission.READ_EXPERIMENT_RESULTS,
            ),
            constraints=("Read-only audit; do not rewrite experiment outcomes.",),
        ),
        "paper_meeting_writer": AgentSpec(
            agent_id="paper_meeting_writer",
            display_name="Paper & Meeting Writer",
            goal="Generate English IEEE draft, Chinese draft, and Chinese meeting slides.",
            outputs=("english_ieee_draft", "chinese_draft", "chinese_meeting_deck"),
            tool_permissions=(
                ToolPermission.READ_PDF,
                ToolPermission.WRITE_FILES,
                ToolPermission.READ_EXPERIMENT_RESULTS,
                ToolPermission.WRITE_PAPER,
                ToolPermission.WRITE_PPT,
            ),
            constraints=(
                "Use only verified or weak evidence; weak evidence cannot enter conclusions.",
            ),
        ),
    }
)


def get_agent_spec(agent_id: str) -> AgentSpec:
    return AGENT_REGISTRY[agent_id]
