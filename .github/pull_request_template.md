## Summary

- 

## Trust Boundary

- Verified facts:
- Model-generated or inferred content:
- Human review still required:

## Verification

- [ ] `uv run ruff check .`
- [ ] `uv run pytest`
- [ ] `npm --prefix web run build`, if frontend or shared API behavior changed
- [ ] Manual/API/browser smoke, if user-facing behavior changed:

## Risk Checklist

- [ ] No secrets, private datasets, checkpoints, logs, or unpublished drafts committed.
- [ ] Agent permissions remain least-privilege.
- [ ] Quest/stage state transitions remain explicit and test-covered.
- [ ] Research claims are backed by sources or marked as unverified.
- [ ] `verified` experiment results include run/artifact provenance before becoming claims.
- [ ] `needs_review` experiment results remain in human-review sections.
- [ ] External network or file-system behavior is documented and constrained.

## AI Assistance

- [ ] I used AI assistance and reviewed the generated output.
- [ ] I did not use AI assistance.

If AI assistance was used, describe what was checked by a human:

-
