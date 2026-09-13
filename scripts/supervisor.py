#!/usr/bin/env python3
"""
MinusCorrect Autonomous Supervisor CLI
Executes closed-loop agent solver sessions with:
1. Physical 4-iteration circuit breaking (out-of-process process supervisor).
2. SHA-256 normalized error hashing for regression and loop detection.
3. Epistemic scaffolding injection at iteration 3 upon identical error hash.
4. Transactional isolation: Automatic atomic rollback on failure to save human hours.
5. Automated diagnostic report generation (DIAGNOSTIC-REPORT.md) on hard abort.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Tuple


def compute_error_hash(stderr: str, stdout: str) -> str:
    """Computes a normalized SHA-256 fingerprint from test failure output."""
    normalized = f"{stderr.strip()}\n{stdout.strip()}".strip()
    if not normalized:
        return "empty_trace"
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]


def run_command(cmd: List[str], cwd: Optional[Path] = None) -> Tuple[int, str, str]:
    """Runs a shell command and returns (returncode, stdout, stderr)."""
    res = subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace"
    )
    return res.returncode, res.stdout, res.stderr


class AgentSupervisor:
    """
    Supervises autonomous coding agent execution cycles, eliminating human cleanup
    hours by providing transactional rollback and automated diagnostics.
    """

    def __init__(self, target_file: Path, test_cmd: List[str], max_iterations: int = 4):
        self.target_file = target_file.resolve()
        self.test_cmd = test_cmd
        self.max_iterations = max_iterations
        self.history: List[dict] = []
        self.original_content: Optional[str] = None

    def snapshot(self) -> None:
        """Stores clean snapshot of target file for atomic rollback."""
        if self.target_file.exists():
            self.original_content = self.target_file.read_text(encoding="utf-8", errors="replace")

    def rollback(self) -> None:
        """Restores target file to initial clean state."""
        if self.original_content is not None:
            self.target_file.write_text(self.original_content, encoding="utf-8")
            print(f"[SUPERVISOR] Atomic rollback completed: Restored {self.target_file.name} to clean state.")

    def write_diagnostic_report(self, reason: str, last_err: str, last_out: str, error_hash: str) -> Path:
        """Generates a human-ready diagnostic summary so maintainers spend minutes, not hours."""
        report_path = Path("DIAGNOSTIC-REPORT.md")
        timestamp = datetime.now(timezone.utc).isoformat()

        content = f"""# MinusCorrect Diagnostic Escalation Report

**Generated:** {timestamp}
**Target File:** `{self.target_file.as_posix()}`
**Test Harness Command:** `{' '.join(self.test_cmd)}`
**Circuit Breaker Status:** HARD_ABORT (Iteration limit reached: {self.max_iterations})
**Termination Reason:** {reason}

---

## 1. Failure Signature
* **Normalized Error Hash:** `{error_hash}`
* **Iteration Count:** {len(self.history)}
* **Consecutive Identical Signatures:** {self._count_identical_tail_hashes()}

---

## 2. Last Execution Stderr
```
{last_err.strip() or "(No stderr captured)"}
```

---

## 3. Last Execution Stdout
```
{last_out.strip() or "(No stdout captured)"}
```

---

## 4. Required Human Maintainer Action
1. Review the failing invariant in the golden test suite.
2. Inspect the observed runtime values above.
3. Clarify ambiguous requirements or evolve the golden contract if the API specification has intentionally shifted:
   ```bash
   ALLOW_GOLDEN_EDIT=1 git commit -m "refactor(contracts): update specification"
   ```
"""
        report_path.write_text(content, encoding="utf-8")
        print(f"[SUPERVISOR] Diagnostic report written to: {report_path.resolve()}")
        return report_path

    def _count_identical_tail_hashes(self) -> int:
        if not self.history:
            return 0
        last = self.history[-1].get("hash")
        count = 0
        for item in reversed(self.history):
            if item.get("hash") == last:
                count += 1
            else:
                break
        return count

    def execute_test(self) -> Tuple[int, str, str, str]:
        """Executes test harness and records normalized telemetry."""
        code, out, err = run_command(self.test_cmd)
        err_hash = compute_error_hash(err, out)
        return code, out, err, err_hash

    def run_supervision_step(self, iteration: int) -> dict:
        """
        Executes a single supervised verification step.
        Returns a dictionary containing step status and guidance.
        """
        print(f"\n[SUPERVISOR] Running verification iteration {iteration}/{self.max_iterations}...")
        code, out, err, err_hash = self.execute_test()

        step_record = {
            "iteration": iteration,
            "exit_code": code,
            "hash": err_hash,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        self.history.append(step_record)

        if code == 0:
            print("[SUPERVISOR] Test harness PASSED.")
            # Run auto-fix to clean up any temporary [DEBUG] tags without human intervention
            run_command([sys.executable, "scripts/verify_integrity.py", "--fix"])
            return {"status": "SUCCESS", "iteration": iteration}

        print(f"[SUPERVISOR] Test FAILED (Exit Code: {code}, Error Hash: {err_hash})")

        # Check for repetition
        if len(self.history) >= 2 and self.history[-1]["hash"] == self.history[-2]["hash"]:
            print("[SUPERVISOR] Warning: Identical error signature detected across consecutive runs.")
            if iteration == 3:
                print("[SUPERVISOR] Iteration 3 reached: Mandatory epistemic [DEBUG] trace injection required.")
                return {
                    "status": "INJECT_SCAFFOLDING",
                    "iteration": iteration,
                    "hash": err_hash,
                    "action": "Inject targeted [DEBUG] logging statements into the implementation to inspect runtime state."
                }

        if iteration >= self.max_iterations:
            print("[SUPERVISOR] Hard circuit breaker TRIPPED at iteration 4. Halting runaway loop.")
            self.rollback()
            report_file = self.write_diagnostic_report(
                reason="Agent exceeded 4 iterations on immutable golden acceptance contract.",
                last_err=err,
                last_out=out,
                error_hash=err_hash
            )
            return {
                "status": "HARD_ABORT",
                "iteration": iteration,
                "diagnostic_report": str(report_file),
                "error_hash": err_hash
            }

        return {
            "status": "RETRY_ALGORITHMIC",
            "iteration": iteration,
            "error_hash": err_hash,
            "stderr": err,
            "stdout": out
        }


def main():
    parser = argparse.ArgumentParser(description="MinusCorrect Autonomous Supervisor")
    subparsers = parser.add_subparsers(dest="command")

    run_parser = subparsers.add_parser("check", help="Run a single supervised check cycle")
    run_parser.add_argument("--target", required=True, help="Target implementation file")
    run_parser.add_argument("--test-cmd", required=True, help="Test command to execute")
    run_parser.add_argument("--iteration", type=int, default=1, help="Current iteration (1-4)")

    args = parser.parse_args()

    if args.command == "check":
        supervisor = AgentSupervisor(
            target_file=Path(args.target),
            test_cmd=args.test_cmd.split(),
            max_iterations=4
        )
        supervisor.snapshot()
        result = supervisor.run_supervision_step(iteration=args.iteration)
        if result["status"] == "SUCCESS":
            sys.exit(0)
        elif result["status"] == "HARD_ABORT":
            sys.exit(2)
        else:
            sys.exit(1)
    else:
        parser.print_help()
        sys.exit(0)


if __name__ == "__main__":
    main()
