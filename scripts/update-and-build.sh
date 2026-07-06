#!/usr/bin/env bash
set -euo pipefail

REMOTE="${NOVISCOPE_UPDATE_REMOTE:-origin}"
BRANCH="${NOVISCOPE_UPDATE_BRANCH:-main}"
FORCE_BUILD="${NOVISCOPE_FORCE_BUILD:-false}"

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

CURRENT_BRANCH="$(git rev-parse --abbrev-ref HEAD)"
if [[ "$CURRENT_BRANCH" != "$BRANCH" ]]; then
  echo "Refusing to update branch '$CURRENT_BRANCH'. Checkout '$BRANCH' first or set NOVISCOPE_UPDATE_BRANCH."
  exit 1
fi

if [[ -n "$(git status --porcelain)" ]]; then
  echo "Refusing to update because the worktree has uncommitted changes."
  git status --short
  exit 1
fi

echo "Checking $REMOTE/$BRANCH..."
git fetch "$REMOTE" "$BRANCH"

LOCAL_SHA="$(git rev-parse HEAD)"
REMOTE_SHA="$(git rev-parse "$REMOTE/$BRANCH")"

if [[ "$LOCAL_SHA" == "$REMOTE_SHA" && "$FORCE_BUILD" != "true" ]]; then
  echo "NoviScope is already up to date at ${LOCAL_SHA:0:7}. Nothing to build."
  exit 0
fi

if [[ "$LOCAL_SHA" != "$REMOTE_SHA" ]]; then
  echo "Updating NoviScope ${LOCAL_SHA:0:7} -> ${REMOTE_SHA:0:7}..."
  git merge --ff-only "$REMOTE/$BRANCH"
else
  echo "Forcing rebuild at ${LOCAL_SHA:0:7}..."
fi

if [[ -x ".venv/bin/python" ]]; then
  .venv/bin/python -m pip install -e .
else
  echo "Skipping backend reinstall because .venv/bin/python was not found."
fi

cd web
if [[ -f package-lock.json ]]; then
  npm ci
else
  npm install
fi
npm run build
cd "$ROOT"

export NOVISCOPE_BUILD_COMMIT
NOVISCOPE_BUILD_COMMIT="$(git rev-parse HEAD)"
export NOVISCOPE_BUILD_VERSION
NOVISCOPE_BUILD_VERSION="$(
  .venv/bin/python -c 'from importlib.metadata import version; print(version("noviscope"))' 2>/dev/null || true
)"

if [[ -n "${NOVISCOPE_RESTART_COMMAND:-}" ]]; then
  echo "Running restart command..."
  bash -lc "$NOVISCOPE_RESTART_COMMAND"
else
  echo "Build complete. Restart the API/web serving process if it is not managed by your runner."
fi
