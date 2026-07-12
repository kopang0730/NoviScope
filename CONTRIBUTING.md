# Contributing to NoviScope

NoviScope is a research workflow system, so maintainability and traceability matter
more than fast feature accumulation. Every contribution should make the workflow
easier to inspect, test, and trust.

## Contribution Workflow

1. Open or pick a GitHub issue before starting non-trivial work.
2. Keep each pull request focused on one behavior or one documentation area.
3. Describe the research-trust boundary before implementing agent behavior:
   what is verified, what is inferred, and what remains human review.
4. Add or update tests for backend behavior changes.
5. Run the relevant verification commands before requesting review.
6. Explain user-facing behavior, data model changes, and safety implications in the PR.

For AI-assisted work, the contributor must still inspect the current repository
state before changing files. Do not rely on a model's memory of how the project
"probably" works.

## Pull Request Size

Prefer PRs that can be reviewed in one focused pass:

- one API behavior;
- one agent runner or output view;
- one workflow gate;
- one provider/configuration improvement;
- one documentation area.

Avoid PRs that mix frontend redesign, database changes, runner logic, and docs
unless the change cannot be reviewed safely in isolation.

Use this risk scale when deciding PR size and review depth:

| Risk | Examples | Required review depth |
| --- | --- | --- |
| Low | Documentation wording, copy changes, small test-only changes | One reviewer can verify commands and links |
| Medium | API response shape, provider settings, UI state, artifact exports | Tests plus manual/API smoke |
| High | Agent prompts, stage gates, auth, secret handling, research-claim logic | Tests, explicit trust-boundary review, and maintainer approval |
| Critical | Code execution, data upload/download, GPU jobs, database migrations | Design issue first, least-privilege review, rollback plan |

## Branches and Commits

- Use short branch names such as `feat/provider-crud` or `docs/collaboration-guide`.
- Prefer small commits that can be reviewed independently.
- Do not mix unrelated refactors with feature work.
- Do not commit local files, API keys, datasets, checkpoints, experiment logs, or drafts.

## Review Standard

Reviewers should prioritize:

- correctness and reproducibility
- evidence provenance and trust boundaries
- API and data model compatibility
- tests that prove behavior rather than implementation details
- whether agent permissions remain least-privilege

Large generated changes should be rejected unless the author can explain the design,
risks, and verification result.

## Verification Matrix

Use the smallest verification set that proves the changed behavior, but do not
skip a gate that the change affects.

Backend behavior:

```bash
uv run ruff check .
uv run pytest
```

Frontend behavior:

```bash
npm --prefix web run build
```

User-facing web behavior:

- run the API locally with `NOVISCOPE_SESSION_COOKIE_SECURE=false`;
- run the Vite dev server;
- drive the changed workflow in a browser;
- verify desktop and a mobile-sized viewport when layout changed.

Research agent or prompt behavior:

- add tests that assert parsed structures, safety rules, and review gates;
- do not snapshot entire prompts unless the exact text is the product;
- verify that generated outputs cannot promote unverified citations or
  experiment results into formal claims.

Experiment, code-runner, or artifact behavior:

- use local paths and fake artifacts in tests;
- do not require private datasets or real API keys in CI;
- document the real-lab verification path in the PR;
- keep uploads disabled unless the feature explicitly needs them and has a
  security review.

Documentation-only changes:

- inspect every changed Markdown link and command for accuracy;
- run the backend/frontend build only when docs describe commands or behavior
  that can drift from code.

## AI-Assisted Contributions

AI tools are allowed, but the human contributor owns the result.

- State in the PR whether AI assistance was used and what was reviewed.
- Keep AI-generated changes small enough to review.
- Do not paste unverifiable generated claims into docs or papers.
- Do not accept code that stores secrets, private datasets, or unpublished drafts in git.
- Record important assumptions in the issue or PR.
- Prefer deterministic tests over screenshots or vague manual claims.
- Keep generated code small enough to review line by line.
- Rewrite or delete AI output that cannot be explained by the contributor.
- Do not let generated docs claim implemented capabilities without checking the
  current code and UI.
- Do not use "the AI ran it" as verification. Verification means a command,
  API response, browser observation, or reviewed artifact that another developer
  can reproduce.

AI-generated code should be treated as untrusted until it passes normal review:

- read every changed file;
- check whether it widens agent permissions;
- check whether it adds hidden network calls or file-system writes;
- check whether it stores raw provider responses, secrets, private data, or
  experiment artifacts in the wrong location;
- check whether it invents sources, metrics, benchmark names, or result claims.

## Research Output Rules

Any contribution that changes generated research content must preserve these
rules:

- citations must come from source APIs or user-provided references;
- missing evidence must be visible, not hidden in raw JSON;
- confidence should be capped when evidence is weak;
- generated hypotheses must be labeled as hypotheses;
- unrun experiments must stay out of Results claims;
- `raw_response` can be stored for audit but should not be the primary UI.
- `verified` experiment results must include run/artifact provenance before
  they can be used as facts.
- `needs_review` experiment records must stay in human-review sections until a
  human approves them.

## Data and Secret Boundaries

Never commit:

- provider API keys, session secrets, database passwords, or bootstrap tokens;
- private datasets, raw student/user submissions, exam papers, or medical/legal
  source data;
- experiment checkpoints, logs, tensorboard runs, or full result artifacts;
- generated paper drafts that contain unpublished research claims unless the
  repository owner explicitly chooses to publish them.

Use `.env`, encrypted provider storage, configured artifact directories, and
local server paths instead of source control for sensitive material.

## Local Verification

```bash
uv sync --extra dev
uv run ruff check .
uv run pytest
npm --prefix web install
npm --prefix web run build
```

## Security

Never commit secrets. Provider API keys must go through the configured provider API
and must be stored encrypted, not in source files or documentation.
