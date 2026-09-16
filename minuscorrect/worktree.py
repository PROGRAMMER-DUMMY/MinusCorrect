"""
MinusCorrect Ephemeral Git Worktree Isolation
Prevents .git/index.lock collisions and concurrency race conditions by providing
isolated, disposable worktree environments for agent operations.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import uuid
from pathlib import Path
from typing import Optional


class EphemeralWorktree:
    """
    Context manager that creates an isolated git worktree for a session and
    guarantees clean tear-down upon exit.
    """

    def __init__(
        self,
        repo_root: Optional[Path] = None,
        branch_name: Optional[str] = None,
        worktree_path: Optional[Path] = None,
        keep_branch_on_success: bool = False,
    ) -> None:
        self.repo_root = (repo_root or Path.cwd()).resolve()
        unique_id = uuid.uuid4().hex[:8]
        self.branch_name = branch_name or f"minuscorrect/wt-{unique_id}"
        self.worktree_path = (
            worktree_path.resolve()
            if worktree_path
            else self.repo_root / ".minuscorrect" / "worktrees" / f"wt-{unique_id}"
        )
        self.keep_branch_on_success = keep_branch_on_success
        self._created = False

    def __enter__(self) -> Path:
        self.create()
        return self.worktree_path

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        preserve_branch = (exc_type is None) and self.keep_branch_on_success
        self.cleanup(preserve_branch=preserve_branch)

    def create(self) -> Path:
        """
        Creates the git worktree and checked-out branch.
        """
        self.worktree_path.parent.mkdir(parents=True, exist_ok=True)

        cmd = [
            "git",
            "worktree",
            "add",
            "-b",
            self.branch_name,
            str(self.worktree_path),
            "HEAD",
        ]
        res = subprocess.run(
            cmd,
            cwd=str(self.repo_root),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if res.returncode != 0:
            raise RuntimeError(
                f"Failed to create git worktree at {self.worktree_path}: {res.stderr.strip()}"
            )

        self._created = True
        return self.worktree_path

    def cleanup(self, preserve_branch: bool = False, force: bool = True) -> None:
        """
        Removes the worktree and cleans up the disposable branch.
        # Rationale: Ephemeral worktrees must leave zero residual lockfiles or orphaned trees.
        """
        if not self._created and not self.worktree_path.exists():
            return

        # 1. git worktree remove
        remove_cmd = ["git", "worktree", "remove"]
        if force:
            remove_cmd.append("--force")
        remove_cmd.append(str(self.worktree_path))

        subprocess.run(
            remove_cmd,
            cwd=str(self.repo_root),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        # 2. Prune worktrees
        subprocess.run(
            ["git", "worktree", "prune"],
            cwd=str(self.repo_root),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        # 3. If directory remains on disk (e.g. untracked files on Windows)
        if self.worktree_path.exists():
            try:
                shutil.rmtree(self.worktree_path, ignore_errors=True)
            except OSError:
                # Rationale: Windows file locking may briefly delay rmtree
                pass

        # 4. Clean up branch if not preserving
        if not preserve_branch and self.branch_name:
            subprocess.run(
                ["git", "branch", "-D", self.branch_name],
                cwd=str(self.repo_root),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

        self._created = False
