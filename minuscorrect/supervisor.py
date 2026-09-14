"""
MinusCorrect Autonomous Supervisor Engine
Provides out-of-process process supervision, session state persistence,
volatile-token error hash sanitization, and git-tree atomic rollback.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def sanitize_trace(raw: str) -> str:
    """
    Sanitizes volatile tokens (durations, memory pointers, timestamps, PIDs)
    from test output to guarantee deterministic error hashing across runs.
    """
    if not raw:
        return ""

    sanitized = raw

    # 1. Memory addresses (e.g. 0x7f9a1b2c or 0x000001B4)
    sanitized = re.sub(r"0x[0-9a-fA-F]{4,16}\b", "<HEX_ADDR>", sanitized)

    # 2. Durations and execution times (e.g. 0.04s, 150ms, 1.23 seconds)
    sanitized = re.sub(r"\b\d+(\.\d+)?\s*(s|ms|µs|ns|seconds|milliseconds)\b", "<DURATION>", sanitized)

    # 3. ISO timestamps and common date/time formats
    sanitized = re.sub(
        r"\b\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:?\d{2})?\b",
        "<TIMESTAMP>",
        sanitized
    )

    # 4. Process IDs and Thread IDs (e.g. pid: 4892, PID=102, Thread-14)
    sanitized = re.sub(r"\b(pid|PID|process|thread|Thread|tid)[\s:=]+\d+\b", "<PID>", sanitized)

    # 5. Volatile temporary paths (e.g. /tmp/pytest-of-user/..., AppData\Local\Temp\...)
    sanitized = re.sub(r"(\/tmp\/[^\s:]+|[A-Za-z]:\\[^\s:]*Temp\\[^\s:]*)", "<TEMP_PATH>", sanitized)

    return sanitized


def compute_error_hash(stderr: str, stdout: str) -> str:
    """Computes a normalized SHA-256 fingerprint from sanitized test output."""
    clean_err = sanitize_trace(stderr).strip()
    clean_out = sanitize_trace(stdout).strip()
    normalized = f"{clean_err}\n{clean_out}".strip()
    if not normalized:
        return "empty_trace"
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]


def run_git_command(args: List[str], cwd: Optional[Path] = None) -> Tuple[int, str, str]:
    """Runs a git command and returns (returncode, stdout, stderr)."""
    res = subprocess.run(
        ["git"] + args,
        cwd=str(cwd) if cwd else None,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace"
    )
    return res.returncode, res.stdout.strip(), res.stderr.strip()


@dataclass
class SessionState:
    session_id: str = "default"
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    current_iteration: int = 0
    max_iterations: int = 4
    history: List[Dict[str, Any]] = field(default_factory=list)
    status: str = "ACTIVE"  # ACTIVE, SCAFFOLDING_REQUIRED, CONVERGED, HARD_ABORT
    target_files: List[str] = field(default_factory=list)

    @classmethod
    def get_session_dir(cls) -> Path:
        base = Path(".minuscorrect") / "sessions"
        base.mkdir(parents=True, exist_ok=True)
        return base

    @classmethod
    def get_session_file(cls, session_id: str) -> Path:
        safe_id = re.sub(r"[^\w\-.]", "_", session_id)
        return cls.get_session_dir() / f"{safe_id}.json"

    @classmethod
    def load(cls, session_id: str = "default") -> SessionState:
        session_file = cls.get_session_file(session_id)
        if session_file.exists():
            try:
                data = json.loads(session_file.read_text(encoding="utf-8"))
                return cls(**data)
            except Exception:
                pass
        return cls(session_id=session_id)

    def save(self) -> None:
        session_file = self.get_session_file(self.session_id)
        session_file.write_text(json.dumps(asdict(self), indent=2), encoding="utf-8")

    def reset(self) -> None:
        session_file = self.get_session_file(self.session_id)
        if session_file.exists():
            session_file.unlink()
        self.current_iteration = 0
        self.history = []
        self.status = "ACTIVE"


class AgentSupervisor:
    """
    Hardened out-of-process supervisor for autonomous agent test-solve cycles.
    """

    def __init__(
        self,
        session_id: str = "default",
        max_iterations: int = 4,
        target_file: Optional[Path] = None
    ):
        self.session_id = session_id
        self.max_iterations = max_iterations
        self.target_file = target_file.resolve() if target_file else None
        self.state = SessionState.load(session_id)
        self.state.max_iterations = max_iterations
        if self.target_file and str(self.target_file) not in self.state.target_files:
            self.state.target_files.append(str(self.target_file))

    def atomic_rollback(self) -> None:
        """
        Executes a Git-tree atomic rollback:
        Discards all tracked changes and removes all untracked files.
        """
        run_git_command(["checkout", "--", "."])
        run_git_command(["clean", "-fd"])
        print("[SUPERVISOR] Git-tree atomic rollback completed: All changes and untracked files discarded.")

    def write_diagnostic_report(
        self,
        reason: str,
        last_err: str,
        last_out: str,
        error_hash: str,
        test_cmd: List[str]
    ) -> Path:
        """Generates DIAGNOSTIC-REPORT.md so human maintainers spend 2 minutes reviewing root cause."""
        report_path = Path("DIAGNOSTIC-REPORT.md")
        timestamp = datetime.now(timezone.utc).isoformat()
        targets_str = ", ".join(self.state.target_files) if self.state.target_files else "Entire workspace"

        content = f"""# MinusCorrect Diagnostic Escalation Report

**Generated:** {timestamp}
**Session ID:** `{self.session_id}`
**Target Scope:** `{targets_str}`
**Test Command:** `{' '.join(test_cmd)}`
**Circuit Breaker Status:** HARD_ABORT (Iteration limit reached: {self.max_iterations})
**Termination Reason:** {reason}

---

## 1. Failure Signature
* **Normalized Error Hash:** `{error_hash}`
* **Total Iterations Attempted:** {len(self.state.history)}
* **Consecutive Identical Signatures:** {self._count_identical_tail_hashes()}

---

## 2. Sanitized Last Stderr
```
{sanitize_trace(last_err).strip() or "(No stderr captured)"}
```

---

## 3. Sanitized Last Stdout
```
{sanitize_trace(last_out).strip() or "(No stdout captured)"}
```

---

## 4. Required Human Maintainer Action
1. Review the failing invariant in the golden acceptance test suite.
2. Inspect observed runtime states and error signatures above.
3. If the specification has intentionally changed, update the contract with explicit override:
   ```bash
   ALLOW_GOLDEN_EDIT=1 git commit -m "refactor(contracts): update specification"
   ```
"""
        report_path.write_text(content, encoding="utf-8")
        print(f"[SUPERVISOR] Diagnostic report written to: {report_path.resolve()}")
        return report_path

    def _count_identical_tail_hashes(self) -> int:
        if not self.state.history:
            return 0
        last = self.state.history[-1].get("hash")
        count = 0
        for item in reversed(self.state.history):
            if item.get("hash") == last:
                count += 1
            else:
                break
        return count

    def run_step(self, test_cmd: List[str]) -> Dict[str, Any]:
        """
        Executes a supervised test run, updating persistent session state.
        """
        self.state.current_iteration += 1
        iteration = self.state.current_iteration

        print(f"\n[SUPERVISOR] Executing verification iteration {iteration}/{self.max_iterations} (Session: '{self.session_id}')...")

        # Execute test command
        res = subprocess.run(
            test_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace"
        )
        code, out, err = res.returncode, res.stdout, res.stderr
        err_hash = compute_error_hash(err, out)

        step_record = {
            "iteration": iteration,
            "exit_code": code,
            "hash": err_hash,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        self.state.history.append(step_record)

        if code == 0:
            print("[SUPERVISOR] Test harness PASSED.")
            self.state.status = "CONVERGED"
            self.state.save()

            from minuscorrect.verifier import check_debug_tags
            check_debug_tags(auto_fix=True)

            return {"status": "SUCCESS", "iteration": iteration}

        print(f"[SUPERVISOR] Test FAILED (Exit Code: {code}, Normalized Hash: {err_hash})")

        # Repetition detection on identical hashes
        if len(self.state.history) >= 2 and self.state.history[-1]["hash"] == self.state.history[-2]["hash"]:
            print("[SUPERVISOR] Warning: Identical normalized error signature detected across consecutive runs.")
            if iteration == 3:
                self.state.status = "SCAFFOLDING_REQUIRED"
                self.state.save()
                return {
                    "status": "INJECT_SCAFFOLDING",
                    "iteration": iteration,
                    "hash": err_hash,
                    "action": "Inject targeted [DEBUG] logging statements into implementation to inspect runtime state.",
                }

        if iteration >= self.max_iterations:
            print("[SUPERVISOR] Hard circuit breaker TRIPPED at iteration 4. Halting runaway loop.")
            self.state.status = "HARD_ABORT"
            self.state.save()
            self.atomic_rollback()
            report_file = self.write_diagnostic_report(
                reason="Agent exceeded 4 iterations on immutable golden acceptance contract.",
                last_err=err,
                last_out=out,
                error_hash=err_hash,
                test_cmd=test_cmd
            )
            return {
                "status": "HARD_ABORT",
                "iteration": iteration,
                "diagnostic_report": str(report_file),
                "error_hash": err_hash
            }

        self.state.status = "ACTIVE"
        self.state.save()
        return {
            "status": "RETRY_ALGORITHMIC",
            "iteration": iteration,
            "error_hash": err_hash,
            "stderr": err,
            "stdout": out
        }
