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
