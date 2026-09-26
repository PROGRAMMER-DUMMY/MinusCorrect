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

# Patterns for ephemeral agent debug logs that must not leak to production
DEBUG_PATTERNS = re.compile(r"(\[DEBUG\]|console\.log\(\"__DEBUG__\"\)|__DEBUG__)")


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
    """Verify that immutable tests in tests/golden/ are not modified or added without ALLOW_GOLDEN_EDIT=1."""
    if os.environ.get("ALLOW_GOLDEN_EDIT") == "1":
        return True, "Golden test edit explicitly allowed via ALLOW_GOLDEN_EDIT=1."

    status_output = run_git_command(["status", "--porcelain"])
    violations = []
    for line in status_output.splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split(None, 1)
        if len(parts) == 2:
            status, path = parts[0], parts[1]
            if path.startswith("tests/golden/"):
                violations.append(f"{status} {path}")

    if violations:
        return False, (
            "[ERROR] Violation: Immutable golden tests modified in tests/golden/:\n  "
            + "\n  ".join(violations)
            + "\n  -> If contract change was approved, run: ALLOW_GOLDEN_EDIT=1 git commit"
        )

    return True, "Golden tests clean."


def check_anti_swallowing(staged_only: bool = True) -> Tuple[bool, str]:
    """
    Detect the 'fix-by-swallowing' anti-pattern in added source lines.
    Flags empty except blocks (e.g. 'except: pass' or 'except Exception: return None')
    introduced without an explicit '# Rationale:' explanation.
    """
    code_files = get_staged_code_files()
    if not code_files:
        return True, "No staged code files to check."

    violations = []
    # Pattern detecting except followed directly by pass or return None/empty
    swallow_inline_pattern = re.compile(
        r"^\+\s*except.*:\s*(pass|return(\s+(None|\{\}|\[\]|''|\"\"|0))?)\s*(#.*)?$",
        re.MULTILINE
    )

    for f in code_files:
        diff_output = run_git_command(["diff", "--cached", "--", f])
        lines = diff_output.splitlines()
        for idx, line in enumerate(lines):
            if not line.startswith("+") or line.startswith("+++"):
                continue

            # Check inline swallow: "except ...: pass"
            if swallow_inline_pattern.match(line):
                # Check if rationale is provided on the same line or adjacent lines
                surrounding = "\n".join(lines[max(0, idx - 3):min(len(lines), idx + 4)])
                if "# Rationale:" not in surrounding and "# Workaround:" not in surrounding:
                    violations.append(
                        f"{f}: Line '{line.strip()}' silently swallows exception without '# Rationale: <reason>'."
                    )
                    continue

            # Check multiline swallow:
            # + except ...:
            # +     pass  OR  +     return None
            if re.match(r"^\+\s*except(\s+[\w\s,()]+)?:\s*$", line):
                next_idx = idx + 1
                while next_idx < len(lines) and lines[next_idx].startswith("+") and not lines[next_idx].strip():
                    next_idx += 1
                if next_idx < len(lines) and lines[next_idx].startswith("+"):
                    next_line = lines[next_idx]
                    if re.match(r"^\+\s*(pass|return(\s+(None|\{\}|\[\]|''|\"\"|0))?)\s*(#.*)?$", next_line):
                        surrounding = "\n".join(lines[max(0, idx - 3):min(len(lines), next_idx + 4)])
                        if "# Rationale:" not in surrounding and "# Workaround:" not in surrounding:
                            violations.append(
                                f"{f}: Lines '{line.strip()}' -> '{next_line.strip()}' silently swallow exception without '# Rationale: <reason>'."
                            )

    if violations:
        return False, (
            "[ERROR] Violation: Fix-by-swallowing detected in staged source code:\n  "
            + "\n  ".join(violations)
            + "\n  -> Address the root cause or document explicit business reason: '# Rationale: <reason>'."
        )

    return True, "No silent exception swallowing detected."



def check_debug_tags(auto_fix: bool = False) -> Tuple[bool, str]:
    code_files = get_staged_code_files()
    if not code_files:
        return True, "No staged code files to check."

    violations = []

    for f in code_files:
        diff_output = run_git_command(["diff", "--cached", "--", f])
        matches = DEBUG_PATTERNS.findall(diff_output)
        if matches:
            if auto_fix:
                try:
                    p = Path(f)
                    if p.exists():
                        lines = p.read_text(encoding="utf-8", errors="replace").splitlines(keepends=True)
                        cleaned_lines = [line for line in lines if not DEBUG_PATTERNS.search(line)]
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


def check_anti_cheat(strict: bool = False) -> Tuple[bool, str]:
    """
    Audit tests against benchmark cheating, empty tests, tautologies, and overfitting.
    # verifies: tests/unit/test_anti_cheat.py
    """
    from minuscorrect.anti_cheat import audit_against_benchmark_cheats
    repo_root = Path.cwd()
    src_dir = repo_root / "minuscorrect" if (repo_root / "minuscorrect").is_dir() else repo_root / "src"
    test_dir = repo_root / "tests"
    if not test_dir.is_dir():
        return True, "No tests directory found."

    report = audit_against_benchmark_cheats(src_dir, test_dir)
    if not report.passed:
        violations_text = "\n  ".join(
            f"[{v.violation_type}] {v.file_path}:{v.line_number} - {v.description}"
            for v in report.violations
        )
        return False, f"[ERROR] Anti-Cheat Audit Failed ({len(report.violations)} violation(s)):\n  {violations_text}"
    return True, "Anti-cheat audit clean."


def verify_all(auto_fix: bool = False, strict_docstrings: bool = False, enforce_anti_cheat: bool = False) -> bool:
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

    swallow_ok, swallow_msg = check_anti_swallowing()
    if not swallow_ok:
        print(swallow_msg, file=sys.stderr)
        return False

    claims_ok, claims_msg = check_unverified_claims(strict=strict_docstrings)
    if not claims_ok:
        print(claims_msg, file=sys.stderr)
        return False

    if enforce_anti_cheat or strict_docstrings or os.environ.get("STRICT_ANTI_CHEAT") == "1":
        cheat_ok, cheat_msg = check_anti_cheat(strict=True)
        if not cheat_ok:
            print(cheat_msg, file=sys.stderr)
            return False

    print("[SUCCESS] Systemic Integrity Verification Passed!")
    return True

