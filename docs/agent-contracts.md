# Agent Contracts

NoviScope separates the long-term agent registry from the currently executable
stage runners. The registry describes the intended research team. The stage
runner registry describes what the Web MVP can actually execute now.

## Shared Stage Contract

Every persisted stage card has:

- `agent_id`
- `status`
- `summary`
- `input_payload`
- `output_payload`
- `evidence_payload`
- `human_approved`
- `review_notes`
- `created_at`
- `updated_at`

Every executable runner implements:

```python
class StageRunner(Protocol):
    @property
    def agent_id(self) -> str: ...

    @property
    def supported_provider_kinds(self) -> frozenset[ProviderKind]: ...

    def build_input_payload(self, context: StageRunContext) -> JsonObject: ...

    def run(self, context: StageRunContext) -> StageRunResult: ...
```

`StageRunResult` must contain `summary`, `confidence`, `input_payload`,
`output_payload`, and `evidence_payload`.

## Current Executable Stages

| Stage | Runner | Provider needed | Current source of truth | Human gate |
| --- | --- | --- | --- | --- |
| Demand validation | `DemandValidationStageRunner` | OpenAI-compatible/custom | model response plus raw response | Review demand validity before relying on it |
| Literature scout | `LiteratureScoutStageRunner` | No | OpenAlex API metadata | Review relevance and missing sources |
| Gap & hypothesis | `GapHypothesisStageRunner` | OpenAI-compatible/custom | demand + literature payloads + model response | Select ideas before experiments |
| Experiment planner | `ExperimentPlannerStageRunner` | OpenAI-compatible/custom | selected ideas + experiment setup notes + model response | Review missing inputs and feasibility |
| Paper & meeting writer | `PaperMeetingWriterStageRunner` | OpenAI-compatible/custom | previous stage payloads + model response | Review all generated artifacts |

`research_refiner`, `gap_analyst`, `code_runner`, and `evidence_auditor` remain
registered long-term agents. They are not created as default quest stages in the
current MVP and do not have executable web-stage runners yet.

## Provider Rules

Provider-backed runners currently support:

- `openai_compatible`
- `custom`

Anthropic-specific execution is not implemented in the current stage runners.
Anthropic providers may exist in configuration, but unsupported stage runs should
block rather than silently using the wrong protocol.

`Literature Scout` has an empty supported-provider set because it does not call a
model provider. It uses OpenAlex metadata and should not invent citations.

## Output Rules

Agent outputs must follow these rules:

- Keep raw model responses in payloads for audit.
- Do not display raw responses as the primary UI.
- Use `confidence` conservatively.
- Put source identifiers, provider names, model names, and blocking reasons in
  `evidence_payload`.
- Put user-facing structured content in `output_payload`.
- Do not claim experiment results unless execution provenance exists.

## Adding a Runner

When adding a new runner:

1. Add or update the agent id in `src/noviscope/core/stage_policy.py` if needed.
2. Implement the runner under `src/noviscope/agents/`.
3. Register the runner in `src/noviscope/api/stage_runs.py`.
4. Add dependency gates before execution.
5. Add structured frontend rendering for the output payload.
6. Add tests for success, missing provider, unsupported provider, and blocked
   prerequisites.
7. Update this document and `docs/workflow.md`.

Do not add a runner that pretends to execute experiments without code, data,
logs, and metrics provenance.
