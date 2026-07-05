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

## Pull Request Size

Prefer PRs that can be reviewed in one focused pass:

- one API behavior;
- one agent runner or output view;
- one workflow gate;
- one provider/configuration improvement;
- one documentation area.

Avoid PRs that mix frontend redesign, database changes, runner logic, and docs
unless the change cannot be reviewed safely in isolation.

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
python -m ruff check .
python -m pytest
```

Frontend behavior:

```bash
cd web
npm run build
```

User-facing web behavior:

- run the API locally with `NOVISCOPE_SESSION_COOKIE_SECURE=false`;
- run the Vite dev server;
- drive the changed workflow in a browser;
- verify desktop and a mobile-sized viewport when layout changed.

Documentation-only changes:

- inspect every changed Markdown link and command for accuracy;
- run the backend/frontend build only when docs describe commands or behavior
  that can drift from code.

## AI-Assisted Contributions

AI tools are allowed, but the human contributor owns the result.

- Keep AI-generated changes small enough to review.
- Do not paste unverifiable generated claims into docs or papers.
- Do not accept code that stores secrets, private datasets, or unpublished drafts in git.
- Record important assumptions in the issue or PR.
- Prefer deterministic tests over screenshots or vague manual claims.
- Keep generated code small enough to review line by line.
- Rewrite or delete AI output that cannot be explained by the contributor.
- Do not let generated docs claim implemented capabilities without checking the
  current code and UI.

## Research Output Rules

Any contribution that changes generated research content must preserve these
rules:

- citations must come from source APIs or user-provided references;
- missing evidence must be visible, not hidden in raw JSON;
- confidence should be capped when evidence is weak;
- generated hypotheses must be labeled as hypotheses;
- unrun experiments must stay out of Results claims;
- `raw_response` can be stored for audit but should not be the primary UI.

## Local Verification

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
python -m ruff check .
python -m pytest
cd web && npm install && npm run build
```

## Security

Never commit secrets. Provider API keys must go through the configured provider API
and must be stored encrypted, not in source files or documentation.
