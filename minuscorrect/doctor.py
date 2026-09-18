"""
MinusCorrect Pre-Flight Environment Diagnostic Engine
Performs comprehensive diagnostic checks on git environment, worktrees,
golden test contracts, session storage, and Python runtime dependencies.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class DiagnosticCheck:
    category: str
    name: str
    status: str  # "PASS", "WARN", "FAIL"
    message: str
    details: Optional[str] = None


def check_python_runtime() -> DiagnosticCheck:
    """
    Validates that the active Python runtime meets version requirements (>= 3.9).
    # Rationale: MinusCorrect requires Python 3.9+ for modern typing, dataclasses, and AST capabilities.
    """
    major = getattr(sys.version_info, "major", sys.version_info[0])
    minor = getattr(sys.version_info, "minor", sys.version_info[1])
    micro = getattr(sys.version_info, "micro", sys.version_info[2])
    if (major, minor) < (3, 9):
        return DiagnosticCheck(
            category="Runtime",
            name="Python Version",
            status="FAIL",
            message=f"Python {major}.{minor} is unsupported. Python 3.9+ is required.",
            details=f"Active executable: {sys.executable}"
        )
    return DiagnosticCheck(
        category="Runtime",
        name="Python Version",
        status="PASS",
        message=f"Python {major}.{minor}.{micro} (compatible)",
        details=f"Executable: {sys.executable}"
    )


def check_pytest_installed() -> DiagnosticCheck:
    """
    Validates that pytest is installed and resolvable in the current environment.
    # Rationale: MinusCorrect drives verification loops through pytest test execution.
    """
    try:
        import pytest
        pytest_ver = getattr(pytest, "__version__", "unknown")
        return DiagnosticCheck(
            category="Runtime",
            name="Pytest Availability",
            status="PASS",
            message=f"pytest {pytest_ver} installed and importable",
        )
    except ImportError:
        return DiagnosticCheck(
            category="Runtime",
            name="Pytest Availability",
            status="FAIL",
            message="pytest is not installed in the active Python environment.",
            details="Run: pip install pytest"
        )


def check_git_binary() -> DiagnosticCheck:
    """
    Checks that the git command line binary is accessible on PATH.
    # Rationale: Git porcelain and plumbing are required for atomic rollback and worktrees.
    """
    git_bin = shutil.which("git")
    if not git_bin:
        return DiagnosticCheck(
            category="Git",
            name="Git Binary",
            status="FAIL",
            message="git executable not found on system PATH.",
            details="Install git and ensure it is available in system PATH."
        )
    try:
        res = subprocess.run(
            ["git", "--version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=5.0
        )
        ver_str = res.stdout.strip() if res.returncode == 0 else "version check failed"
        return DiagnosticCheck(
            category="Git",
            name="Git Binary",
            status="PASS",
            message=f"{ver_str} located at {git_bin}",
        )
    except Exception as exc:
        return DiagnosticCheck(
            category="Git",
            name="Git Binary",
            status="FAIL",
            message=f"Failed to execute git: {exc}",
        )


def check_git_repository(cwd: Optional[Path] = None) -> DiagnosticCheck:
    """
    Validates that the working directory is inside a valid git repository.
    # Rationale: Autonomous supervision relies on git history and index isolation.
    """
    target_dir = str(cwd) if cwd else None
    try:
        res = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=target_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=5.0
        )
        if res.returncode != 0:
            return DiagnosticCheck(
                category="Git",
                name="Repository Root",
                status="FAIL",
                message="Not inside a valid git repository.",
                details=res.stderr.strip() or "Run 'git init' to initialize a repository."
            )
        root = res.stdout.strip()
        return DiagnosticCheck(
            category="Git",
            name="Repository Root",
            status="PASS",
            message=f"Repository root detected: {root}",
        )
    except Exception as exc:
        return DiagnosticCheck(
            category="Git",
            name="Repository Root",
            status="FAIL",
            message=f"Git check failed: {exc}",
        )


def check_git_index_lock(cwd: Optional[Path] = None) -> DiagnosticCheck:
    """
    Validates that no stale .git/index.lock file exists that would block git operations.
    # Rationale: Stale lockfiles from aborted processes cause atomic rollbacks and commits to fail.
    """
    target_dir = cwd or Path.cwd()
    # Find .git directory
    git_dir = target_dir / ".git"
    if git_dir.is_file():
        # Submodule or worktree git link
        try:
            link_content = git_dir.read_text(encoding="utf-8").strip()
            if link_content.startswith("gitdir:"):
                git_dir = Path(link_content.split(":", 1)[1].strip())
        except Exception:
            pass

    lock_file = git_dir / "index.lock"
    if lock_file.exists():
        return DiagnosticCheck(
            category="Git",
            name="Index Lock",
            status="FAIL",
            message=f"Stale git index lockfile detected at {lock_file}.",
            details="Remove .git/index.lock if no concurrent git process is running."
        )
    return DiagnosticCheck(
        category="Git",
        name="Index Lock",
        status="PASS",
        message="No git index lockfile detected.",
    )


def check_worktree_capability(cwd: Optional[Path] = None) -> DiagnosticCheck:
    """
    Verifies that git worktree command is operational.
    # Rationale: Ephemeral worktree isolation is used to execute tests safely without dirtying main index.
    """
    target_dir = str(cwd) if cwd else None
    try:
        res = subprocess.run(
            ["git", "worktree", "list"],
            cwd=target_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=5.0
        )
        if res.returncode == 0:
            count = len(res.stdout.strip().splitlines())
            return DiagnosticCheck(
                category="Git",
                name="Worktree Support",
                status="PASS",
                message=f"Git worktrees supported ({count} active worktree{'s' if count != 1 else ''})",
            )
        return DiagnosticCheck(
            category="Git",
            name="Worktree Support",
            status="WARN",
            message="Git worktree check returned non-zero exit code.",
            details=res.stderr.strip()
        )
    except Exception as exc:
        return DiagnosticCheck(
            category="Git",
            name="Worktree Support",
            status="WARN",
            message=f"Git worktree command check failed: {exc}",
        )


def check_golden_tests(cwd: Optional[Path] = None) -> DiagnosticCheck:
    """
    Verifies the existence and clean git status of tests/golden/ contracts.
    # Rationale: Protects immutable acceptance contracts from tampering.
    """
    target_dir = cwd or Path.cwd()
    golden_dir = target_dir / "tests" / "golden"
    if not golden_dir.exists():
        return DiagnosticCheck(
            category="Contracts",
            name="Golden Test Directory",
            status="WARN",
            message="tests/golden/ directory does not exist.",
            details="Create tests/golden/ with immutable acceptance test files."
        )

    # Check git status of tests/golden
    try:
        res = subprocess.run(
            ["git", "status", "--porcelain", "--", "tests/golden"],
            cwd=str(target_dir),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=5.0
        )
        if res.returncode == 0:
            modified = res.stdout.strip()
            allow_override = os.environ.get("ALLOW_GOLDEN_EDIT") == "1"
            if modified:
                if allow_override:
                    return DiagnosticCheck(
                        category="Contracts",
                        name="Golden Test Immutability",
                        status="WARN",
                        message="tests/golden/ has local modifications (ALLOW_GOLDEN_EDIT=1 active).",
                        details=modified
                    )
                else:
                    return DiagnosticCheck(
                        category="Contracts",
                        name="Golden Test Immutability",
                        status="FAIL",
                        message="tests/golden/ contains modified or untracked files without ALLOW_GOLDEN_EDIT=1.",
                        details=modified
                    )
            return DiagnosticCheck(
                category="Contracts",
                name="Golden Test Immutability",
                status="PASS",
                message="tests/golden/ is clean and strictly unmodified.",
            )
        return DiagnosticCheck(
            category="Contracts",
            name="Golden Test Immutability",
            status="WARN",
            message="Could not inspect tests/golden git porcelain status.",
            details=res.stderr.strip()
        )
    except Exception as exc:
        return DiagnosticCheck(
            category="Contracts",
            name="Golden Test Immutability",
            status="WARN",
            message=f"Failed to check golden git status: {exc}",
        )


def check_session_storage(cwd: Optional[Path] = None) -> DiagnosticCheck:
    """
    Validates read and write accessibility of supervisor session storage directory.
    # Rationale: Supervisor relies on session persistence for circuit breaking and history tracking.
    """
    target_dir = cwd or Path.cwd()
    session_dir = target_dir / ".minuscorrect_sessions"
    try:
        session_dir.mkdir(parents=True, exist_ok=True)
        test_file = session_dir / ".health_check.tmp"
        test_file.write_text("health_ok", encoding="utf-8")
        read_back = test_file.read_text(encoding="utf-8")
        test_file.unlink()
        if read_back == "health_ok":
            return DiagnosticCheck(
                category="Storage",
                name="Session Persistence",
                status="PASS",
                message=f"Session storage writable at {session_dir.name}/",
            )
        return DiagnosticCheck(
            category="Storage",
            name="Session Persistence",
            status="FAIL",
            message="Session storage readback mismatch.",
        )
    except Exception as exc:
        return DiagnosticCheck(
            category="Storage",
            name="Session Persistence",
            status="FAIL",
            message=f"Session storage is not writable: {exc}",
        )


def check_configuration_environment() -> List[DiagnosticCheck]:
    """
    Validates optional runtime environment configuration (timeouts, webhooks, passthrough).
    # Rationale: Provides operator visibility into environment variables and egress channels.
    """
    checks: List[DiagnosticCheck] = []

    # Timeout
    timeout_str = os.environ.get("MINUSCORRECT_TIMEOUT")
    if timeout_str:
        try:
            val = float(timeout_str)
            checks.append(DiagnosticCheck(
                category="Config",
                name="Execution Timeout",
                status="PASS",
                message=f"Configured via MINUSCORRECT_TIMEOUT={val}s",
            ))
        except ValueError:
            checks.append(DiagnosticCheck(
                category="Config",
                name="Execution Timeout",
                status="WARN",
                message=f"Invalid MINUSCORRECT_TIMEOUT='{timeout_str}', will fallback to 300.0s default.",
            ))
    else:
        checks.append(DiagnosticCheck(
            category="Config",
            name="Execution Timeout",
            status="PASS",
            message="Default timeout active (300.0s). Set MINUSCORRECT_TIMEOUT to customize.",
        ))

    # Webhook
    webhook_url = os.environ.get("MINUSCORRECT_WEBHOOK_URL")
    if webhook_url:
        is_slack = "hooks.slack.com" in webhook_url
        kind = "Slack Webhook" if is_slack else "Generic Webhook"
        checks.append(DiagnosticCheck(
            category="Config",
            name="Operational Alerts",
            status="PASS",
            message=f"{kind} configured for failure & circuit breaker egress.",
        ))
    else:
        checks.append(DiagnosticCheck(
            category="Config",
            name="Operational Alerts",
            status="WARN",
            message="MINUSCORRECT_WEBHOOK_URL is unset. Circuit breaker alerts will log to console only.",
            details="Set MINUSCORRECT_WEBHOOK_URL=https://hooks.slack.com/services/... to enable team notifications."
        ))

    # Passthrough Env
    passthrough = os.environ.get("MINUSCORRECT_PASSTHROUGH_ENV")
    if passthrough:
        keys = [k.strip() for k in passthrough.split(",") if k.strip()]
        checks.append(DiagnosticCheck(
            category="Config",
            name="Env Whitelist Passthrough",
            status="PASS",
            message=f"{len(keys)} environment variable{'s' if len(keys) != 1 else ''} whitelisted for isolated execution: {', '.join(keys)}",
        ))

    return checks


def run_diagnostics(cwd: Optional[Path] = None) -> List[DiagnosticCheck]:
    """
    Executes all pre-flight diagnostic checks and returns the complete result list.
    """
    checks: List[DiagnosticCheck] = [
        check_python_runtime(),
        check_pytest_installed(),
        check_git_binary(),
        check_git_repository(cwd),
        check_git_index_lock(cwd),
        check_worktree_capability(cwd),
        check_golden_tests(cwd),
        check_session_storage(cwd),
    ]
    checks.extend(check_configuration_environment())
    return checks


def format_diagnostic_text(checks: List[DiagnosticCheck]) -> str:
    """Formats diagnostic check results for human-readable terminal presentation."""
    lines: List[str] = [
        "============================================================",
        "          MinusCorrect Pre-Flight Environment Doctor        ",
        "============================================================",
    ]

    current_cat = None
    pass_count = sum(1 for c in checks if c.status == "PASS")
    warn_count = sum(1 for c in checks if c.status == "WARN")
    fail_count = sum(1 for c in checks if c.status == "FAIL")

    for c in checks:
        if c.category != current_cat:
            current_cat = c.category
            lines.append(f"\n[{current_cat}]")

        status_tag = f"[{c.status}]"
        lines.append(f"  {status_tag:<8} {c.name}: {c.message}")
        if c.details and c.status != "PASS":
            lines.append(f"           -> Details: {c.details}")

    lines.append("\n" + "-" * 60)
    summary = f"Summary: {len(checks)} checks | {pass_count} passed | {warn_count} warnings | {fail_count} failures"
    lines.append(summary)
    if fail_count > 0:
        lines.append("[RESULT] Environment health check FAILED. Resolve errors before running supervisor.")
    elif warn_count > 0:
        lines.append("[RESULT] Environment health check PASSED with non-critical warnings.")
    else:
        lines.append("[RESULT] Environment health check PASSED. System is ready for production execution.")
    lines.append("-" * 60)

    return "\n".join(lines)


def format_diagnostic_json(checks: List[DiagnosticCheck]) -> str:
    """Formats diagnostic check results as structured JSON."""
    pass_count = sum(1 for c in checks if c.status == "PASS")
    warn_count = sum(1 for c in checks if c.status == "WARN")
    fail_count = sum(1 for c in checks if c.status == "FAIL")

    payload = {
        "healthy": fail_count == 0,
        "summary": {
            "total": len(checks),
            "passed": pass_count,
            "warnings": warn_count,
            "failures": fail_count,
        },
        "checks": [asdict(c) for c in checks],
    }
    return json.dumps(payload, indent=2)
