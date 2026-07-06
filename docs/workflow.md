# NoviScope Workflow

NoviScope is organized around a quest. A quest starts as a rough research
direction and moves through explicit stage cards. Each stage must either produce
structured evidence or explain why it is blocked.

## User Flow

1. Register with an invitation code.
2. Create a quest from the research intake form, including any demand evidence
   sources that a human can verify before experiments.
3. Configure at least one model provider if running provider-backed stages.
4. Run Demand Validation.
5. Review the demand output and decide whether the problem is worth continuing.
6. Run Literature Scout after demand validation completes.
7. Run Gap & Hypothesis Generator after demand and literature outputs exist.
8. Select one or more ideas for experiment design.
9. Record experiment setup context: data path, code repository, and environment
   notes.
10. Run Experiment Planner.
11. Run Paper & Meeting Writer after experiment planning completes.
12. Download or copy the generated Markdown artifacts after human review.

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

## Review Rules

Human approval has meaning. Use `human_approved` and `review_notes` for decisions
that affect downstream work:

- approve or reject demand validity;
- record selected ideas;
- confirm experiment readiness;
- approve generated writing only after checking sources and claims.

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
