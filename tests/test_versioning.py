import subprocess

from noviscope import versioning
from noviscope.core.config import Settings


def test_local_dirty_returns_false_when_git_status_is_clean(monkeypatch):
    def fake_run(*args, **kwargs) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(versioning.subprocess, "run", fake_run)

    assert versioning.local_dirty() is False


def test_local_commit_uses_running_commit_when_build_commit_is_absent(monkeypatch):
    monkeypatch.setattr(versioning, "RUNNING_GIT_COMMIT", "running1234567890", raising=False)
    monkeypatch.setattr(versioning, "_git_output", lambda *args: "newdisk1234567890")

    assert versioning.local_commit(Settings(_env_file=None)) == "running1234567890"


def test_update_available_only_when_local_commit_is_behind_remote():
    assert versioning.is_update_available("abc1234", "abc1234ffff", "identical") is False
    assert versioning.is_update_available("localhotfix", "remotecommit", "behind") is False
    assert versioning.is_update_available("localhotfix", "remotecommit", "diverged") is False
    assert versioning.is_update_available("oldcommit", "newcommit", "ahead") is True
