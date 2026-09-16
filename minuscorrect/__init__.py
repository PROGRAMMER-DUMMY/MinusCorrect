"""
MinusCorrect: Systemic Integrity & Closed-Loop Verification Protocol
"""

__version__ = "1.0.0"

from minuscorrect.notify import NotificationEvent, dispatch_notification
from minuscorrect.pr import DraftPRMetadata, create_draft_pr_artifact, generate_draft_pr_markdown
from minuscorrect.supervisor import AgentSupervisor, compute_error_hash, sanitize_trace
from minuscorrect.verifier import verify_all
from minuscorrect.worktree import EphemeralWorktree

__all__ = [
    "AgentSupervisor",
    "DraftPRMetadata",
    "EphemeralWorktree",
    "NotificationEvent",
    "compute_error_hash",
    "create_draft_pr_artifact",
    "dispatch_notification",
    "generate_draft_pr_markdown",
    "sanitize_trace",
    "verify_all",
    "__version__",
]
