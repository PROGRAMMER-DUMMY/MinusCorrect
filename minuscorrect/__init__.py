"""
MinusCorrect: Systemic Integrity & Closed-Loop Verification Protocol
"""

__version__ = "0.2.0"

from minuscorrect.supervisor import AgentSupervisor, compute_error_hash, sanitize_trace
from minuscorrect.verifier import verify_all

__all__ = [
    "AgentSupervisor",
    "compute_error_hash",
    "sanitize_trace",
    "verify_all",
    "__version__",
]
