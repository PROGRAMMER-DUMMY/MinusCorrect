"""
MinusCorrect Atomic Rollback & Git-Pointer Time Machine Engine.

Provides deterministic, verified rollback capabilities for agent tickets:
1. Validates working-tree cleanliness precondition to prevent clobbering uncommitted work.
2. Performs atomic git revert operations for closed ticket commits.
3. Enforces post-rollback closed-loop verification (test passing requirement).
4. Transitions ticket states in .minus/ Second Brain from completed to rolled_back.
# verifies: tests/unit/test_rollback.py
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shlex
import subprocess
from typing import Any, Dict, List, Optional

from minuscorrect.store import MinusStore, Ticket


@dataclass
class RollbackResult:
    """Represents the outcome of a ticket rollback operation."""
    success: bool
    ticket_id: str
    status: str  # "ROLLED_BACK", "ABORTED_DIRTY_TREE", "VERIFICATION_FAILED", "REVERT_CONFLICT", "NOT_FOUND", "ERROR"
    message: str
    revert_commit: Optional[str] = None
    verification_exit_code: Optional[int] = None
    verification_output: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class RollbackEngine:
    """
    Autonomous rollback supervisor.
    Ensures safe reversion of agent ticket modifications with pre- and post-flight safety gates.
    # verifies: tests/unit/test_rollback.py
    """

    def __init__(self, store: Optional[MinusStore] = None, root_dir: Optional[Path] = None):
        self.root_dir = root_dir or Path.cwd()
        self.store = store or MinusStore(root_dir=self.root_dir)

    def check_working_tree_clean(self, cwd: Optional[Path] = None) -> bool:
        """
        Check whether git working tree has uncommitted tracked or untracked changes.
        Ignores .minus/ Second-Brain store directory changes.
        # Rationale: Rollbacks must not clobber in-progress human or agent edits,
        # but internal store metadata in .minus/ should not block rollbacks.
        """
        target_dir = cwd or self.root_dir
        try:
            res = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=str(target_dir),
                capture_output=True,
                text=True,
                check=False,
            )
            if res.returncode != 0:
                return False
            # Filter out entries inside .minus/
            dirty_lines = []
            for raw_line in res.stdout.splitlines():
                line = raw_line.strip()
                if not line:
                    continue
                # Line format in porcelain: XY <path> or XY -> <path>
                # Extract path component after status code
                parts = line.split(maxsplit=1)
                if len(parts) >= 2:
                    rel_path = parts[1].strip().strip('"\'')
                    if rel_path.startswith(".minus/") or rel_path == ".minus" or rel_path.startswith(".minus\\"):
                        continue
                dirty_lines.append(line)

            return len(dirty_lines) == 0
        except (OSError, subprocess.SubprocessError):
            return False

    def inspect_diff(self, ticket_id: str) -> Optional[str]:
        """Retrieve unified diff patch for ticket from .minus/diffs/ or dynamic git diff."""
        patch_text = self.store.get_ticket_diff(ticket_id)
        if patch_text:
            return patch_text

        ticket = self.store.get_ticket(ticket_id)
        if not ticket or not ticket.receipt:
            return None

        base = ticket.receipt.base_commit_sha
        head = ticket.receipt.head_commit_sha or ticket.receipt.commit_sha
        if not head or head == "HEAD":
            return None

        try:
            diff_cmd = ["git", "diff", f"{base}..{head}"] if base else ["git", "show", "--format=", head]
            res = subprocess.run(
                diff_cmd,
                cwd=str(self.root_dir),
                capture_output=True,
                text=True,
                check=False,
            )
            return res.stdout if res.returncode == 0 and res.stdout.strip() else None
        except (OSError, subprocess.SubprocessError):
            return None

    def rollback_ticket(
        self,
        ticket_id: str,
        force: bool = False,
        verify: bool = True,
        reopen: bool = False,
        cwd: Optional[Path] = None,
    ) -> RollbackResult:
        """
        Atomically revert a ticket's commit and transition state in .minus/ Second Brain.
        # verifies: tests/unit/test_rollback.py
        """
        target_dir = cwd or self.root_dir

        ticket = self.store.get_ticket(ticket_id)
        if not ticket:
            return RollbackResult(
                success=False,
                ticket_id=ticket_id,
                status="NOT_FOUND",
                message=f"Ticket '{ticket_id}' not found in .minus/ store.",
            )

        if ticket.status != "completed" and not force:
            return RollbackResult(
                success=False,
                ticket_id=ticket_id,
                status="INVALID_STATUS",
                message=f"Ticket '{ticket_id}' has status '{ticket.status}'. Only 'completed' tickets can be rolled back without --force.",
            )

        # Precondition Gate: Clean working tree
        if not force and not self.check_working_tree_clean(cwd=target_dir):
            return RollbackResult(
                success=False,
                ticket_id=ticket_id,
                status="ABORTED_DIRTY_TREE",
                message="Working tree has uncommitted modifications. Commit or stash changes before rolling back.",
            )

        # Resolve commit to revert
        head_commit = (
            ticket.receipt.head_commit_sha
            if ticket.receipt and ticket.receipt.head_commit_sha
            else (ticket.receipt.commit_sha if ticket.receipt else None)
        )

        if not head_commit or head_commit in ("HEAD", ""):
            return RollbackResult(
                success=False,
                ticket_id=ticket_id,
                status="ERROR",
                message=f"Ticket '{ticket_id}' does not have a resolvable commit SHA in its execution receipt.",
            )

        # Execute git revert
        revert_cmd = ["git", "revert", "--no-edit", head_commit]
        revert_res = subprocess.run(
            revert_cmd,
            cwd=str(target_dir),
            capture_output=True,
            text=True,
            check=False,
        )

        if revert_res.returncode != 0:
            # Revert failed, abort git revert to restore index cleanliness
            subprocess.run(["git", "revert", "--abort"], cwd=str(target_dir), capture_output=True, check=False)
            return RollbackResult(
                success=False,
                ticket_id=ticket_id,
                status="REVERT_CONFLICT",
                message=f"Reverting commit {head_commit[:8]} produced merge conflicts. Revert operation was cleanly aborted.\n{revert_res.stderr}",
            )

        revert_commit = self.store.resolve_commit_sha("HEAD", cwd=target_dir)

        # Closed-Loop Verification Gate
        verification_exit_code = 0
        verification_output = ""
        if verify:
            verify_cmd_str = ticket.verification or "minuscorrect verify --fix --strict"
            # In test environments without minuscorrect in PATH, fallback to pytest
            try:
                use_shell = os.name == "nt" or '"' in verify_cmd_str or "'" in verify_cmd_str
                if use_shell:
                    v_res = subprocess.run(
                        verify_cmd_str,
                        shell=True,
                        cwd=str(target_dir),
                        capture_output=True,
                        text=True,
                        check=False,
                    )
                else:
                    cmd_parts = shlex.split(verify_cmd_str)
                    v_res = subprocess.run(
                        cmd_parts,
                        cwd=str(target_dir),
                        capture_output=True,
                        text=True,
                        check=False,
                    )
                verification_exit_code = v_res.returncode
                verification_output = v_res.stdout + "\n" + v_res.stderr

                if verification_exit_code != 0:
                    if not force:
                        # Revert the revert to restore clean state
                        subprocess.run(["git", "reset", "--hard", "HEAD~1"], cwd=str(target_dir), capture_output=True, check=False)
                        return RollbackResult(
                            success=False,
                            ticket_id=ticket_id,
                            status="VERIFICATION_FAILED",
                            message=f"Post-rollback verification failed with exit code {verification_exit_code}. Revert was undone to preserve codebase integrity.",
                            revert_commit=None,
                            verification_exit_code=verification_exit_code,
                            verification_output=verification_output[:1000],
                        )
            except (OSError, subprocess.SubprocessError) as exc:
                if not force:
                    subprocess.run(["git", "reset", "--hard", "HEAD~1"], cwd=str(target_dir), capture_output=True, check=False)
                    return RollbackResult(
                        success=False,
                        ticket_id=ticket_id,
                        status="VERIFICATION_FAILED",
                        message=f"Verification command could not be executed: {exc}. Revert undone.",
                    )

        # Transition ticket state in Second Brain
        completed_file = self.store.tickets_completed / f"{ticket_id}.md"
        rolled_back_file = self.store.tickets_rolled_back / f"{ticket_id}.md"
        open_file = self.store.tickets_open / f"{ticket_id}.md"

        target_status = "open" if reopen else "rolled_back"
        dest_file = open_file if reopen else rolled_back_file

        ticket.status = target_status
        ticket.body += f"\n\n## Rollback Audit Note\nRolled back in commit `{revert_commit}` at {datetime.now(timezone.utc).isoformat()}."
        dest_file.write_text(ticket.to_markdown(), encoding="utf-8")

        if completed_file.exists():
            try:
                completed_file.unlink()
            except OSError:
                pass

        # Update index
        idx = self.store._read_index()
        t_entry = idx.setdefault("tickets", {}).setdefault(ticket_id, {})
        t_entry["status"] = target_status
        t_entry["file"] = f"tickets/{'open' if reopen else 'rolled_back'}/{ticket_id}.md"
        t_entry["revert_commit"] = revert_commit
        t_entry["rolled_back_at"] = datetime.now(timezone.utc).isoformat()
        self.store._write_index(idx)

        # Update Git ref if needed
        self.store.create_git_ref(f"{ticket_id}-revert", revert_commit, cwd=target_dir)

        action_word = "reopened for repair" if reopen else "moved to rolled_back store"
        return RollbackResult(
            success=True,
            ticket_id=ticket_id,
            status="ROLLED_BACK",
            revert_commit=revert_commit,
            verification_exit_code=verification_exit_code,
            verification_output=verification_output,
            message=f"Ticket {ticket_id} successfully rolled back in commit {revert_commit[:8]} and {action_word}.",
        )
