"""
MinusCorrect Ephemeral Git Worktree Isolation
Prevents .git/index.lock collisions and concurrency race conditions by providing
isolated, disposable worktree environments for agent operations.
"""

from __future__ import annotations

import atexit
import os
import shutil
import signal
import subprocess
import sys
import time
import uuid
from pathlib import Path
from typing import Any, Dict, Optional


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
        self._prev_signal_handlers: Dict[int, Any] = {}

    def __enter__(self) -> Path:
        self.create()
        return self.worktree_path

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        preserve_branch = (exc_type is None) and self.keep_branch_on_success
        self.cleanup(preserve_branch=preserve_branch)

    def _register_traps(self) -> None:
        """
        Registers exit hook and signal traps for termination handling.
        """
        atexit.register(self._exit_handler)
        self._prev_signal_handlers.clear()

        # Rationale: Trap termination signals to guarantee cleanup of ephemeral worktrees and lockfiles
        for sig_name in ("SIGINT", "SIGTERM"):
            sig = getattr(signal, sig_name, None)
            if sig is None:
                continue
            try:
                # Workaround: signal registration is only supported from the main thread
                prev = signal.signal(sig, self._signal_handler)
                self._prev_signal_handlers[sig] = prev
            except (ValueError, OSError):
                # Workaround: Ignore registration failures in non-main threads or unsupported platforms
                pass

    def _exit_handler(self) -> None:
        """
        Exit handler registered with atexit to clean up active worktree on interpreter shutdown.
        """
        self.cleanup(preserve_branch=False, force=True)

    def _signal_handler(self, signum: int, frame: Any) -> None:
        """
        Signal handler for SIGINT and SIGTERM that guarantees worktree teardown before exit.
        """
        self.cleanup(preserve_branch=False, force=True)
        sys.exit(128 + signum)

    def create(self) -> Path:
        """
        Creates the git worktree and checked-out branch.
        """
        if self._created:
            return self.worktree_path

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
        self._register_traps()
        return self.worktree_path

    def cleanup(self, preserve_branch: bool = False, force: bool = True) -> None:
        """
        Removes the worktree and cleans up the disposable branch.
        # Rationale: Ephemeral worktrees must leave zero residual lockfiles or orphaned trees.
        """
        if not self._created:
            return
        self._created = False

        # Restore previous signal handlers and unregister atexit hook to avoid double execution
        try:
            atexit.unregister(self._exit_handler)
        except Exception:
            # Workaround: Unregistering may fail if atexit state was already finalized
            pass

        for sig, prev in list(self._prev_signal_handlers.items()):
            try:
                signal.signal(sig, prev)
            except (ValueError, OSError):
                # Workaround: Signal restoration only succeeds from the main thread
                pass
        self._prev_signal_handlers.clear()

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
            for attempt in range(3):
                try:
                    if self.worktree_path.exists():
                        shutil.rmtree(self.worktree_path)
                    break
                except (PermissionError, OSError):
                    # Workaround: Windows indexing and antivirus services transiently lock files
                    if attempt < 2:
                        time.sleep(0.1)
                    else:
                        shutil.rmtree(self.worktree_path, ignore_errors=True)

        # 4. Clean up branch if not preserving
        if not preserve_branch and self.branch_name:
            subprocess.run(
                ["git", "branch", "-D", self.branch_name],
                cwd=str(self.repo_root),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )


WorktreeSession = EphemeralWorktree

__all__ = ["EphemeralWorktree", "WorktreeSession"]

