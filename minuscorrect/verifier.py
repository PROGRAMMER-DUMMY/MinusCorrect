"""
MinusCorrect Systemic Integrity Verifier Engine
Checks staged diffs or files for:
1. Unauthorized edits to tests/golden/ (immutable contract specs).
3. Unverified docstring superlatives / claims without test receipts in source files.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path
from typing import List, Tuple

# Source code extensions to audit
CODE_EXTENSIONS = {
    ".py", ".ts", ".js", ".tsx", ".jsx", ".go", ".rs", ".java", ".cpp", ".c", ".rb", ".php"
}

# High-risk claim keywords that require verified test receipts
HIGH_RISK_CLAIM_PATTERNS = [
    r"\bthread-safe\b",
    r"\bO\(1\)\b",
    r"\buniversal\b",
    r"\bbulletproof\b",
    r"\bzero-dependency\b",
    r"\bblazing fast\b",
    r"\bdomain-agnostic\b",
]


def run_git_command(args: List[str]) -> str:
    result = subprocess.run(
        ["git"] + args,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace"
    )
    if result.returncode != 0:
        return ""
    return result.stdout.strip()


def get_staged_code_files() -> List[str]:
    """Get all staged files that are source code files."""
    staged = run_git_command(["diff", "--cached", "--name-only"]).splitlines()
    code_files = []
    for f in staged:
        ext = os.path.splitext(f)[1].lower()
        # Exclude verification harness scripts, testing tools, and test suites
        if ext in CODE_EXTENSIONS and not f.startswith(("scripts/", "tests/", "minuscorrect/")):
            code_files.append(f)
    return code_files


def check_golden_tests() -> Tuple[bool, str]:
    """Verify that immutable tests in tests/golden/ are not modified during implementation."""
    if os.environ.get("ALLOW_GOLDEN_EDIT") == "1":
        return True, "Golden test edit explicitly allowed via ALLOW_GOLDEN_EDIT=1."

    staged_files = run_git_command(["diff", "--cached", "--name-only"]).splitlines()
    modified_golden = [f for f in staged_files if f.startswith("tests/golden/")]

    if modified_golden:
        status_output = run_git_command(["status", "--porcelain"])
        violations = []
        for line in status_output.splitlines():
            parts = line.strip().split(None, 1)
            if len(parts) == 2:
                status, path = parts[0], parts[1]
                if path.startswith("tests/golden/") and "M" in status:
                    violations.append(path)

        if violations:
            return False, (
                "[ERROR] Violation: Immutable golden tests modified in tests/golden/:\n  "
                + "\n  ".join(violations)
                + "\n  -> If contract change was approved, run: ALLOW_GOLDEN_EDIT=1 git commit"
            )

    return True, "Golden tests clean."


def check_debug_tags(auto_fix: bool = False) -> Tuple[bool, str]:
    code_files = get_staged_code_files()
    if not code_files:
        return True, "No staged code files to check."

    violations = []

    for f in code_files:
        diff_output = run_git_command(["diff", "--cached", "--", f])
        matches = debug_pattern.findall(diff_output)
        if matches:
            if auto_fix:
                try:
                    p = Path(f)
                    if p.exists():
                        lines = p.read_text(encoding="utf-8", errors="replace").splitlines(keepends=True)
                        p.write_text("".join(cleaned_lines), encoding="utf-8")
                        run_git_command(["add", f])
                except Exception as e:
                    violations.append(f"{f} (Auto-fix failed: {e})")
            else:
                violations.append(f)

    if violations:
        return False, (
            "[ERROR] Violation: Temporary agent debug logs detected in staged source files:\n  "
            + "\n  ".join(violations)
            + "\n  -> Run 'python scripts/verify_integrity.py --fix' to auto-clean and re-stage."
        )

    return True, "No leftover debug tags in code files."


def check_unverified_claims(strict: bool = False) -> Tuple[bool, str]:
    """Verify that docstrings with high-risk operational claims include an explicit test receipt (# verifies: ...)."""
    code_files = get_staged_code_files()
    if not code_files:
        return True, "No staged code files to check."

    violations = []
    for f in code_files:
        diff_output = run_git_command(["diff", "--cached", "--", f])
        lines = diff_output.splitlines()
        for idx, line in enumerate(lines):
            if not line.startswith("+") or line.startswith("+++"):
                continue

            lower_line = line.lower()
            for pattern in HIGH_RISK_CLAIM_PATTERNS:
                if re.search(pattern, lower_line, re.IGNORECASE):
                    surrounding = "\n".join(lines[max(0, idx - 5):min(len(lines), idx + 6)])
                    if not re.search(r"(verifies|receipt):\s*tests?/", surrounding, re.IGNORECASE):
                        violations.append(
                            f"{f}: Line '{line.strip()}' makes unverified claim '{pattern}' "
                            f"without a linked test receipt (# verifies: tests/...)."
                        )
                        break

    if violations:
        msg = "[WARNING] Unverified docstring claim(s) detected without test receipts:\n  " + "\n  ".join(violations)
        msg += "\n\n  -> Action required: Either add '# verifies: tests/<path_to_test>' or strip the superlative claim."
        if strict or os.environ.get("STRICT_DOCSTRINGS") == "1":
            return False, "[ERROR] " + msg
        else:
            print(msg, file=sys.stderr)

    return True, "Docstring claims clean."


def verify_all(auto_fix: bool = False, strict_docstrings: bool = False) -> bool:
    """Executes full verification suite. Returns True if all checks pass."""
    print(f"[INFO] Running Systemic Integrity Pre-Commit Verification...{' (Auto-Fix Enabled)' if auto_fix else ''}")

    golden_ok, golden_msg = check_golden_tests()
    if not golden_ok:
        print(golden_msg, file=sys.stderr)
        return False

    debug_ok, debug_msg = check_debug_tags(auto_fix=auto_fix)
    if not debug_ok:
        print(debug_msg, file=sys.stderr)
        return False

    claims_ok, claims_msg = check_unverified_claims(strict=strict_docstrings)
    if not claims_ok:
        print(claims_msg, file=sys.stderr)
        return False

    print("[SUCCESS] Systemic Integrity Verification Passed!")
    return True
