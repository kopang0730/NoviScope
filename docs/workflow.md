# NoviScope Workflow

NoviScope is organized around a quest. A quest starts as a rough research
direction and moves through explicit stage cards. Each stage must either produce
structured evidence or explain why it is blocked.

## User Flow

1. Register with an invitation code.
2. Open the Research Canvas. It is the default workspace after login and shows
   the selected quest, stage map, next action, evidence trail, and human review
   gates.
3. Create a quest from the research intake form, including any demand evidence
   sources that a human can verify before experiments.
4. Configure at least one model provider if running provider-backed stages.
5. Run Demand Validation.
6. Review the demand output and decide whether the problem is worth continuing.
7. Run Literature Scout after demand validation completes.
8. Run Gap & Hypothesis Generator after demand and literature outputs exist.
9. Select one or more ideas for experiment design.
10. Record experiment setup context: data path, code repository, and environment
   notes.
11. Run Experiment Planner.
12. Run Paper & Meeting Writer after experiment planning completes.
13. Download or copy the generated Markdown artifacts after human review.

## Stage Gates

### Demand Validation

Purpose: determine whether the direction appears grounded in a real application
scenario.

Output must separate:

- `demand_assessment`
- `confidence`
- `real_world_scenario`
- `target_user_or_customer`
- `evidence_for_demand`
- `missing_evidence`
- `risks`
- `suggested_human_checklist`
- `go_or_no_go_recommendation`

If the stage has no external evidence, high confidence is not appropriate.
User-provided demand evidence sources from Quest intake are treated as
unverified leads until a human records the review result.
Humans should review the scenario before continuing to expensive experiment
planning.
The frontend should use `POST /stages/{stage_id}/demand-review` on the completed
Demand Validation stage. `verified` and `plausible` verdicts require at least
one human evidence source; `unclear` and `rejected` keep the stage from being
treated as approved for downstream work.

### Literature Scout

Purpose: retrieve real paper metadata and show it in a sortable, inspectable
table.

Current source: OpenAlex. OpenAlex can be used without a model provider and
without an API key; `NOVISCOPE_OPENALEX_API_KEY` is optional for deployments that
want authenticated OpenAlex requests. If the source returns no useful papers, the
UI should show that clearly rather than inventing citations.

Each paper should include:

- title, authors, year, venue;
- URL, DOI, or source identifier when available;
- abstract summary;
- relevance score;
- reliability level;
- why it is relevant;
- limitations.

The frontend can read saved paper rows through
`GET /stages/{stage_id}/literature-papers`. The endpoint returns only papers
already stored in the completed Literature Scout stage. It supports
`reliability_level=top_conference_or_journal|peer_reviewed|arxiv_preprint|unknown`
and `sort=relevance_desc|year_desc|year_asc`. If the stage is pending, running,
or blocked, the endpoint returns an empty table plus `unavailable_reason`; it
does not synthesize placeholder papers.

The frontend can open a single saved paper through
`GET /stages/{stage_id}/literature-papers/detail?paper_ref=...`. `paper_ref`
must come from the table response. Unknown references return `404` instead of a
fabricated detail. Pending, running, or blocked stages return an empty detail
with `unavailable_reason`. The response includes review warnings reminding the
reader to verify metadata and full text before citing.

### Gap & Hypothesis Generator

Purpose: generate candidate research ideas based on demand and literature
outputs. It must not invent novelty disconnected from existing work.

Each idea should include:

- title and core hypothesis;
- supporting papers;
- expected improvement;
- required data and baseline;
- feasibility;
- novelty risk;
- application value;
- confidence.

The user must select an idea before experiment planning continues.
The frontend should use `POST /stages/{stage_id}/select-ideas` on the completed
Gap & Hypothesis Generator stage. The request accepts `selected_idea_ids` and
optional `review_notes`; the response marks the stage as human approved and sets
`selection_status=selected_for_experiment_design`. Unknown idea ids are rejected
instead of being stored as downstream experiment inputs.

### Experiment Planner

Purpose: turn selected ideas into a runnable plan. It does not execute code.

Expected output:

- datasets needed;
- data availability status;
- baselines to reproduce;
- metrics;
- ablation variables;
- expected tables and figures;
- compute requirements;
- first runnable script plan;
- failure risks.

If required data, code, or environment context is missing, the stage should be
blocked or clearly marked as incomplete.
The frontend should use `POST /stages/{stage_id}/experiment-setup` on the
Experiment Planner stage to record `data_path`, `code_repository`, and
`environment_notes`. Saving setup inputs resets a blocked missing-input stage
back to `pending`, but it does not claim that any experiment has run.

### Paper & Meeting Writer

Purpose: produce review-only Markdown artifacts from prior stages.

Current artifacts:

- Chinese research brief;
- English research brief;
- meeting outline;
- IEEE-style paper skeleton.

The generated text must label:

- verified facts;
- model-generated hypotheses;
- experiment results not yet available;
- human review required.

The writer must not present unrun experiments as completed results.

## Stage Output Display

Stage APIs still store complete `output_payload` values, including raw provider
responses needed for debugging. Main web views should use
`GET /stages/{stage_id}/display-output` instead of rendering full payloads by
default.

The display-output endpoint returns:

- `display_payload`: structured output with raw model responses and
  secret-like fields removed recursively;
- `hidden_fields`: JSON paths that were hidden from the default view;
- `output_available` and `raw_response_available`;
- normalized `confidence`, `summary`, `status`, `agent_id`, and `stage_id`.

This preserves traceability while keeping raw LLM text out of the normal review
surface.

## Workflow Graph Display

Canvas and timeline views should use `GET /quests/{quest_id}/workflow-graph`
for the selected quest. The endpoint returns ordered stage nodes, dependency
edges, human-gate states, provider/model readiness, blocking reasons, and
confidence values in one frontend-friendly contract. It reuses the same
readiness rules as `GET /stages/{stage_id}/readiness`, so the canvas should not
show a stage as runnable when provider configuration, prerequisites, status, or
human review gates block it.

For default canvas layout, the frontend can call
`GET /workflow/canvas-template`. This endpoint returns static lanes, node
coordinates, core-flow ids, planned-extension nodes, and edge labels. It does
not contain user quest state; combine it with the quest workflow graph when
rendering a selected quest.

For feature gating and empty states, the frontend can call
`GET /workflow/capabilities`. This endpoint lists every registered workflow
agent and separates implemented stage runners from planned-only agents. Use it
to avoid presenting future automation, such as code execution or evidence
auditing, as if it were already available.

For source audit panels, the frontend can call
`GET /quests/{quest_id}/evidence-ledger`. This endpoint returns one entry per
workflow stage with saved source references, provider id, provider model,
confidence, human approval state, review notes, output keys, and evidence keys.
It does not create new citations or infer missing evidence. Stages without saved
source references are counted as missing evidence and should remain visible as
review gaps in canvas and timeline views.

## Review Rules

Human approval has meaning. Use `human_approved` and `review_notes` for decisions
that affect downstream work:

- approve or reject demand validity;
- record selected ideas;
- confirm experiment readiness;
- approve generated writing only after checking sources and claims.

The read-only endpoint `GET /stages/{stage_id}/review-guidance` gives the web UI
a structured review card:

- `approval_state`: pending stage completion, ready for review, approved, or
  rejected;
- `review_required` and `can_approve`;
- `blocking_reason` when approval is not actionable;
- `checklist` built from structured review, missing evidence, risk, and
  human-review fields;
- `evidence_summary`, `warnings`, and normalized `confidence`.

This endpoint does not approve or reject a stage. It only explains what a human
should inspect before using `human_approved` and `review_notes`.

Do not use review notes as a place to store secrets, private dataset paths that
should not be visible to other users, or unpublished paper text that should not
be committed.

## Blocked States

Blocked is a useful state, not a failure. A stage should become blocked when:

- no compatible provider is configured;
- the provider is inactive;
- prerequisites are incomplete;
- required experiment inputs are missing;
- the model provider returns invalid structured output;
- a source API cannot provide reliable metadata.

The UI should show the blocking reason and a concrete next action.
