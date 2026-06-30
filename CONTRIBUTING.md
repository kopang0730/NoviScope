# Contributing to NoviScope

NoviScope is a research workflow system, so maintainability and traceability matter
more than fast feature accumulation. Every contribution should make the workflow
easier to inspect, test, and trust.

## Contribution Workflow

1. Open or pick a GitHub issue before starting non-trivial work.
2. Keep each pull request focused on one behavior or one documentation area.
3. Add or update tests for backend behavior changes.
4. Run `ruff check .` and `pytest` before requesting review.
5. Explain user-facing behavior, data model changes, and safety implications in the PR.

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

## AI-Assisted Contributions

AI tools are allowed, but the human contributor owns the result.

- Keep AI-generated changes small enough to review.
- Do not paste unverifiable generated claims into docs or papers.
- Do not accept code that stores secrets, private datasets, or unpublished drafts in git.
- Record important assumptions in the issue or PR.
- Prefer deterministic tests over screenshots or vague manual claims.

## Local Verification

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
ruff check .
pytest
```

## Security

Never commit secrets. Provider API keys must go through the configured provider API
and must be stored encrypted, not in source files or documentation.
