"""
Unit tests for Ephemeral Git Worktree Isolation
"""

import subprocess
from pathlib import Path
import pytest

from minuscorrect.worktree import EphemeralWorktree


@pytest.fixture
def temp_git_repo(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init"], cwd=str(repo), check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    subprocess.run(["git", "config", "user.name", "MinusCorrect Tester"], cwd=str(repo), check=True)
    subprocess.run(["git", "config", "user.email", "test@minuscorrect.org"], cwd=str(repo), check=True)

    # Initial commit
    readme = repo / "README.md"
    readme.write_text("Hello Worktree", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=str(repo), check=True)
    subprocess.run(["git", "commit", "-m", "chore: initial commit"], cwd=str(repo), check=True)

    return repo


def test_ephemeral_worktree_lifecycle(temp_git_repo):
    branch_name = "minuscorrect/wt-test-1"
    worktree_target = temp_git_repo / ".minuscorrect" / "worktrees" / "wt-test-1"

    with EphemeralWorktree(
        repo_root=temp_git_repo,
        branch_name=branch_name,
        worktree_path=worktree_target,
    ) as wt_path:
        assert wt_path.exists()
        assert (wt_path / "README.md").exists()

        # Check git branch in worktree
        res = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=str(wt_path),
            stdout=subprocess.PIPE,
            text=True,
            check=True
        )
        assert res.stdout.strip() == branch_name

    # After exit, worktree directory and branch should be cleaned up
    assert not worktree_target.exists()

    branches_res = subprocess.run(
        ["git", "branch", "--list", branch_name],
        cwd=str(temp_git_repo),
        stdout=subprocess.PIPE,
        text=True,
        check=True
    )
    assert branch_name not in branches_res.stdout


def test_ephemeral_worktree_preserve_branch_on_success(temp_git_repo):
    branch_name = "minuscorrect/wt-preserve-1"

    with EphemeralWorktree(
        repo_root=temp_git_repo,
        branch_name=branch_name,
        keep_branch_on_success=True,
    ) as wt_path:
        assert wt_path.exists()

    # Worktree should be removed, but branch preserved
    branches_res = subprocess.run(
        ["git", "branch", "--list", branch_name],
        cwd=str(temp_git_repo),
        stdout=subprocess.PIPE,
        text=True,
        check=True
    )
    assert branch_name in branches_res.stdout

    # Clean up preserved branch
    subprocess.run(["git", "branch", "-D", branch_name], cwd=str(temp_git_repo), check=True)


def test_worktree_session_alias():
    from minuscorrect.worktree import WorktreeSession
    assert WorktreeSession is EphemeralWorktree


def test_ephemeral_worktree_idempotent_double_cleanup(temp_git_repo):
    wt = EphemeralWorktree(repo_root=temp_git_repo)
    wt.create()
    assert wt._created is True

    wt.cleanup()
    assert wt._created is False

    # Second cleanup call should return immediately without error
    wt.cleanup()
    assert wt._created is False


def test_atexit_and_signal_traps_lifecycle(temp_git_repo, monkeypatch):
    registered_atexit = []
    unregistered_atexit = []

    monkeypatch.setattr("atexit.register", lambda fn: registered_atexit.append(fn))
    monkeypatch.setattr("atexit.unregister", lambda fn: unregistered_atexit.append(fn))

    wt = EphemeralWorktree(repo_root=temp_git_repo)
    wt.create()

    assert wt._exit_handler in registered_atexit
    assert wt._created is True

    # Check signal handler behavior
    import signal
    import pytest

    with pytest.raises(SystemExit) as exc_info:
        wt._signal_handler(signal.SIGINT, None)

    assert exc_info.value.code == 128 + signal.SIGINT
    assert wt._created is False
    assert wt._exit_handler in unregistered_atexit


def test_cleanup_retry_on_permission_error(temp_git_repo, monkeypatch):
    import shutil

    wt = EphemeralWorktree(repo_root=temp_git_repo)
    wt.create()

    orig_run = subprocess.run

    def mock_run(cmd, *args, **kwargs):
        if isinstance(cmd, list) and "remove" in cmd:
            # Simulate git removing worktree from git tracking but leaving folder on disk
            return subprocess.CompletedProcess(cmd, 0, "", "")
        return orig_run(cmd, *args, **kwargs)

    monkeypatch.setattr("subprocess.run", mock_run)

    attempts = []
    original_rmtree = shutil.rmtree

    def mock_rmtree(path, ignore_errors=False):
        attempts.append(ignore_errors)
        if len(attempts) < 2:
            raise PermissionError("Simulated Windows file lock")
        original_rmtree(path, ignore_errors=ignore_errors)

    monkeypatch.setattr("shutil.rmtree", mock_rmtree)

    wt.cleanup()
    assert wt._created is False
    assert len(attempts) >= 2


