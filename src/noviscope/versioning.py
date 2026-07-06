import subprocess
from datetime import UTC, datetime
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Final, Literal, assert_never

import httpx
from pydantic import BaseModel, ConfigDict, ValidationError

from noviscope.core.config import Settings

GitHubCompareStatus = Literal["ahead", "behind", "diverged", "identical"]
GITHUB_ACCEPT_HEADER: Final = "application/vnd.github+json"


class RemoteVersion(BaseModel):
    model_config = ConfigDict(frozen=True)

    check_error: str | None
    remote_commit: str | None
    update_available: bool


class VersionStatus(BaseModel):
    model_config = ConfigDict(frozen=True)

    app_version: str
    local_branch: str | None
    local_commit: str | None
    local_commit_short: str | None
    local_dirty: bool | None
    github_repo: str
    github_branch: str
    remote_commit: str | None
    remote_commit_short: str | None
    update_available: bool
    check_error: str | None
    checked_at: str


class GitHubCommitResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    sha: str


class GitHubCompareResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    status: GitHubCompareStatus


def package_version() -> str:
    try:
        return version("noviscope")
    except PackageNotFoundError:
        return "0.0.0"


def deployed_version(settings: Settings) -> str:
    return _normalize_optional(settings.build_version) or package_version()


def short_commit(commit: str | None) -> str | None:
    if not commit:
        return None
    stripped_commit = commit.strip()
    return stripped_commit[:7] if stripped_commit else None


def _normalize_optional(value: str | None) -> str | None:
    if value is None:
        return None
    stripped_value = value.strip()
    return stripped_value or None


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _git_output(*args: str, preserve_empty: bool = False) -> str | None:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=_repo_root(),
            check=True,
            capture_output=True,
            text=True,
            timeout=2,
        )
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return None
    output = result.stdout.strip()
    if preserve_empty:
        return output
    return output or None


RUNNING_GIT_COMMIT: Final = _git_output("rev-parse", "HEAD")
RUNNING_GIT_BRANCH: Final = _git_output("rev-parse", "--abbrev-ref", "HEAD")


def local_commit(settings: Settings) -> str | None:
    return _normalize_optional(settings.build_commit) or RUNNING_GIT_COMMIT


def local_branch() -> str | None:
    return RUNNING_GIT_BRANCH


def local_dirty() -> bool | None:
    status = _git_output("status", "--porcelain", preserve_empty=True)
    if status is None:
        return None
    return bool(status)


def sha_matches(local_sha: str | None, remote_sha: str | None) -> bool:
    local = _normalize_optional(local_sha)
    remote = _normalize_optional(remote_sha)
    if local is None or remote is None:
        return False
    if local == remote:
        return True
    if len(local) < 7 or len(remote) < 7:
        return False
    return local.startswith(remote) or remote.startswith(local)


def is_update_available(
    local_sha: str | None,
    remote_sha: str | None,
    compare_status: GitHubCompareStatus,
) -> bool:
    if local_sha is None or remote_sha is None or sha_matches(local_sha, remote_sha):
        return False

    match compare_status:
        case "ahead":
            return True
        case "behind" | "diverged" | "identical":
            return False
        case unreachable:
            assert_never(unreachable)


def fetch_remote_commit(client: httpx.Client, repo: str, branch: str) -> str:
    response = client.get(
        f"https://api.github.com/repos/{repo}/commits/{branch}",
        headers={"Accept": GITHUB_ACCEPT_HEADER},
    )
    response.raise_for_status()
    return GitHubCommitResponse.model_validate(response.json()).sha


def fetch_compare_status(
    client: httpx.Client,
    repo: str,
    local_sha: str,
    branch: str,
) -> GitHubCompareStatus:
    response = client.get(
        f"https://api.github.com/repos/{repo}/compare/{local_sha}...{branch}",
        headers={"Accept": GITHUB_ACCEPT_HEADER},
    )
    response.raise_for_status()
    return GitHubCompareResponse.model_validate(response.json()).status


def remote_version(settings: Settings, local_sha: str | None) -> RemoteVersion:
    repo = settings.github_repo.strip()
    branch = settings.github_branch.strip()
    if not repo or not branch:
        return RemoteVersion(
            check_error="GitHub repo or branch is not configured.",
            remote_commit=None,
            update_available=False,
        )

    try:
        with httpx.Client(
            follow_redirects=True,
            timeout=settings.version_check_timeout_seconds,
        ) as client:
            remote_sha = fetch_remote_commit(client, repo, branch)
            if local_sha is None or sha_matches(local_sha, remote_sha):
                return RemoteVersion(
                    check_error=None,
                    remote_commit=remote_sha,
                    update_available=False,
                )
            compare_status = fetch_compare_status(client, repo, local_sha, branch)
    except (httpx.HTTPError, ValidationError, ValueError) as exc:
        return RemoteVersion(
            check_error=f"Unable to check GitHub version: {exc}",
            remote_commit=None,
            update_available=False,
        )

    return RemoteVersion(
        check_error=None,
        remote_commit=remote_sha,
        update_available=is_update_available(local_sha, remote_sha, compare_status),
    )


def version_status(settings: Settings) -> VersionStatus:
    local_sha = local_commit(settings)
    remote = remote_version(settings, local_sha)

    return VersionStatus(
        app_version=deployed_version(settings),
        local_branch=local_branch(),
        local_commit=local_sha,
        local_commit_short=short_commit(local_sha),
        local_dirty=local_dirty(),
        github_repo=settings.github_repo,
        github_branch=settings.github_branch,
        remote_commit=remote.remote_commit,
        remote_commit_short=short_commit(remote.remote_commit),
        update_available=remote.update_available,
        check_error=remote.check_error,
        checked_at=datetime.now(UTC).isoformat(),
    )
