# Feature Status and Trust Gates

This document is the product-status contract for NoviScope. Use it when planning
frontend screens, agent work, PRs, and demos. A feature marked `planned` must not
be presented in the Web UI as runnable automation.

## Status Labels

| Label | Meaning | UI rule |
| --- | --- | --- |
| `implemented` | Exists on `main`, has tests, and can be exercised without manual database edits. | May be shown as available. |
| `partial` | Exists, but depends on a narrow source, manual review, or limited artifact shape. | Show caveats and review gates. |
| `planned` | Described by the product design or agent registry, but not executable in the Web MVP. | Show as coming soon, blocked, or hidden from action flows. |
| `external` | Requires real API keys, source quota, GPU access, datasets, or private code paths. | Show setup requirements before allowing a run. |

## Current MVP Capability Matrix

| Area | Status | Current behavior | Trust gate |
| --- | --- | --- | --- |
| Invitation registration and login | implemented | Members register with invite codes and log in with session cookies. | Admin controls invite issuance. |
| Quest creation | implemented | A member can create a quest from a title and initial research direction. | User must provide enough context for meaningful review. |
| Stage card persistence | implemented | Stages persist `agent_id`, status, payloads, summary, confidence source, review fields, and timestamps. | Stage output is not trusted until reviewed. |
| Shared and personal providers | implemented | API keys are encrypted at rest and scoped as shared or personal. | Never expose raw API keys in responses, logs, or UI state. |
| Provider connection test | partial | The backend can test model-provider connectivity. | Failures should block stage runs with a setup message. |
| Agent registry | implemented | The 9-agent research team is registered and serialized in deterministic order. | Registry membership does not imply runnable automation. |
| Demand Validation runner | implemented | Uses a configured model provider and returns structured demand assessment, missing evidence, risks, checklist, and raw response. | No external source verification means high confidence must be downgraded. |
| Demand review | partial | The stage stores `human_approved` and `review_notes`; downstream work should respect the human gate. | A human must approve or reject demand validity before relying on it. |
| Literature Scout runner | partial | Retrieves real paper metadata from OpenAlex. | Relevance, venue quality, and missing sources require review. |
| Source adapters beyond OpenAlex | planned | arXiv, Semantic Scholar, IEEE, ACM, CVF, and dataset/source crawlers are not implemented. | Do not claim comprehensive literature coverage. |
| Gap & Hypothesis runner | partial | Generates evidence-linked candidate ideas from demand and literature payloads. | Ideas are hypotheses, not verified contributions. |
| Idea selection | partial | Selected ideas can be represented in stage payloads and should gate experiment planning. | User selection is required before planning experiments. |
| Experiment Planner runner | partial | Produces datasets, baselines, metrics, ablations, compute notes, and first-script plans. | Missing data/code/environment context must block or caveat the plan. |
| Code Runner | planned | The agent exists in the registry and is the only agent with `run_code`. | Do not show GPU or baseline execution as available yet. |
| Experiment artifact registry | planned | No durable registry for logs, checkpoints, tables, figures, or metric files exists yet. | Do not write untracked experiment outputs into paper claims. |
| Evidence Auditor | planned | The agent exists in the registry, but no execution logic exists yet. | Source and claim audits must remain manual or explicitly marked pending. |
| Paper & Meeting Writer runner | partial | Generates review-only Markdown artifacts from prior stage payloads. | Must label missing experiment results and human-review requirements. |
| PPT generation | planned | PPT generation is not implemented in the Web MVP. | Do not promise downloadable slides yet. |
| Web research workspace | partial | The web app supports auth, quest list/detail, stage review, artifacts, and provider settings. | UI should show blocked/needs review instead of implying all agents can run. |
| Version and update visibility | partial | The app can expose version information and admin update checks when configured. | Only admins may initiate update/build actions. |

## Claim Safety Rules

1. Do not fabricate papers, citations, datasets, metric values, benchmark results,
   or company evidence.
2. If a stage has no external evidence, the UI and generated text must not show
   `high` confidence.
3. If an experiment has not run, paper artifacts must use language such as
   `planned`, `hypothesized`, or `not yet verified`, not `we show` or `we prove`.
4. If a source is user-provided, treat it as a lead until a human records review
   notes or attaches verifiable provenance.
5. If a provider, source API, dataset path, or repository is missing, return a
   blocked state with the setup requirement instead of silently producing output.
6. Raw model responses may be stored for audit, but the primary UI should render
   structured fields and review warnings.

## Human Gates

| Gate | Required before | Reviewer decision |
| --- | --- | --- |
| Demand review | Literature and experiment work that assumes the demand is real. | Approve, reject, or request more evidence. |
| Literature review | Treating papers as core references. | Confirm relevance, venue/source quality, and missing sources. |
| Idea selection | Experiment planning. | Select one or more ideas and record why. |
| Experiment setup review | Experiment planning or future code execution. | Confirm data path, code repository, environment, and metrics. |
| Experiment result review | Paper claims. | Confirm logs, metrics, tables, and failure cases. |
| Artifact review | Sharing drafts or meeting materials. | Confirm facts, citations, caveats, and unverified claims. |

## PR Review Checklist

Before merging a feature that affects the research workflow, reviewers should
check:

- Does the feature expose whether it is implemented, partial, planned, or blocked?
- Does every generated claim have a source, confidence, or review warning?
- Does the feature preserve private API keys, data paths, logs, and checkpoints?
- Does the feature keep human gates before demand validity, idea selection,
  experiment execution, and paper claims?
- Does the PR include tests for the contract it adds?
- Does the PR update this document if it changes the status matrix?
