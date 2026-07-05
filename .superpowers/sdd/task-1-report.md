# Task 1 Report: Add Auth Dependencies and User Models

## What I implemented

Added the auth-related dependencies to `pyproject.toml`:
- `passlib[bcrypt]>=1.7.4`
- `psycopg[binary]>=3.2.0`
- `python-jose[cryptography]>=3.3.0`

Created `src/noviscope/models/user.py` with:
- `UserRole`
- `InviteStatus`
- `User`
- `InviteCode`

Registered the new models in:
- `src/noviscope/db/session.py`
- `tests/conftest.py`

Added `tests/test_auth.py` to verify `User` and `InviteCode` persistence.

I also added a SQLModel relationship between `User` and `InviteCode` so the foreign-key insert order is handled correctly during flush/commit.

## Tests and output summary

Focused auth test:
- `.venv/bin/python -m pytest tests/test_auth.py::test_user_and_invite_persist -q`
- Result: `1 passed`

Lint:
- `.venv/bin/python -m ruff check .`
- Result: `All checks passed!`

Full backend test suite:
- `.venv/bin/python -m pytest -q`
- Result: `33 passed, 1 warning`

The warning is the existing Starlette/httpx deprecation warning already present before this task.

## Files changed

- `pyproject.toml`
- `src/noviscope/models/user.py`
- `src/noviscope/db/session.py`
- `tests/conftest.py`
- `tests/test_auth.py`

## Self-review findings

- The initial version of the auth persistence test hit a foreign-key ordering failure when `InviteCode.created_by_user_id` was populated before the parent `User` row was flushed.
- Adding the ORM relationship resolved the insert ordering without changing the schema or the test assertions.
- The new models follow the existing project pattern for IDs and timestamps.

## Concerns

- The repo still has the pre-existing Starlette/httpx deprecation warning in the test suite.
- The auth dependency additions are in `pyproject.toml`; the virtual environment’s installed packages were not modified by this task.
