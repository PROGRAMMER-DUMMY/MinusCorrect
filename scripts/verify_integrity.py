#!/usr/bin/env python3
"""
Systemic Integrity Verification Script
Checks staged diffs or files for:
1. Unauthorized edits to tests/golden/ (immutable contract specs).
2. Leftover [DEBUG] traces injected during agent debugging loops in source files.
3. Unverified docstring superlatives / claims without test receipts in source files.
"""

import sys
import subprocess
import os
import re

# Ensure UTF-8 output on Windows consoles
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

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

def run_git_command(args):
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

def get_staged_code_files():
    """Get all staged files that are source code files."""
    staged = run_git_command(["diff", "--cached", "--name-only"]).splitlines()
    code_files = []
    for f in staged:
        ext = os.path.splitext(f)[1].lower()
        # Exclude verification harness scripts and documentation files
        if ext in CODE_EXTENSIONS and not f.startswith("scripts/"):
            code_files.append(f)
    return code_files

def check_golden_tests():
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
            return False, f"[ERROR] Violation: Immutable golden tests modified in tests/golden/:\n  " + "\n  ".join(violations) + "\n  -> If contract change was approved, run: ALLOW_GOLDEN_EDIT=1 git commit"
            
    return True, "Golden tests clean."

def check_debug_tags(auto_fix=False):
    """Verify that temporary [DEBUG] traces injected during agent loops are stripped from source code."""
    code_files = get_staged_code_files()
    if not code_files:
        return True, "No staged code files to check."
        
    debug_pattern = re.compile(r"^\+\s*.*(\[DEBUG\]|console\.log\(\"__DEBUG__|print\(\"\[DEBUG\])", re.MULTILINE)
    violations = []
    
    for f in code_files:
        diff_output = run_git_command(["diff", "--cached", "--", f])
        matches = debug_pattern.findall(diff_output)
        if matches:
            if auto_fix:
                # Automatically strip [DEBUG] lines and re-stage to save human hours
                try:
                    with open(f, "r", encoding="utf-8", errors="replace") as fp:
                        lines = fp.readlines()
                    cleaned_lines = [l for l in lines if "[DEBUG]" not in l and "__DEBUG__" not in l]
                    with open(f, "w", encoding="utf-8") as fp:
                        fp.writelines(cleaned_lines)
                    run_git_command(["add", f])
                    print(f"[AUTO-FIX] Stripped residual [DEBUG] logs from {f} and re-staged.")
                except Exception as e:
                    violations.append(f"{f} (Auto-fix failed: {e})")
            else:
                violations.append(f)
            
    if violations:
        return False, f"[ERROR] Violation: Temporary agent debug logs detected in staged source files:\n  " + "\n  ".join(violations) + "\n  -> Run 'python scripts/verify_integrity.py --fix' to auto-clean and re-stage."
        
    return True, "No leftover debug tags in code files."

def check_unverified_claims():
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
                    # Check surrounding lines for verified test link (# verifies: tests/... or @verifies tests/...)
                    surrounding = "\n".join(lines[max(0, idx - 5):min(len(lines), idx + 6)])
                    if not re.search(r"(verifies|receipt):\s*tests?/", surrounding, re.IGNORECASE):
                        violations.append(f"{f}: Line '{line.strip()}' makes unverified claim '{pattern}' without a linked test receipt (# verifies: tests/...).")
                        break

    if violations:
        msg = "[WARNING] Unverified docstring claim(s) detected without test receipts:\n  " + "\n  ".join(violations)
        msg += "\n\n  -> Action required: Either add '# verifies: tests/<path_to_test>' or strip the superlative claim."
        if os.environ.get("STRICT_DOCSTRINGS") == "1":
            return False, "[ERROR] " + msg
        else:
            print(msg, file=sys.stderr)

    return True, "Docstring claims clean."

def main():
    auto_fix = "--fix" in sys.argv
    print(f"[INFO] Running Systemic Integrity Pre-Commit Verification...{' (Auto-Fix Enabled)' if auto_fix else ''}")
    
    golden_ok, golden_msg = check_golden_tests()
    if not golden_ok:
        print(golden_msg, file=sys.stderr)
        sys.exit(1)
        
    debug_ok, debug_msg = check_debug_tags(auto_fix=auto_fix)
    if not debug_ok:
        print(debug_msg, file=sys.stderr)
        sys.exit(1)

    claims_ok, claims_msg = check_unverified_claims()
    if not claims_ok:
        print(claims_msg, file=sys.stderr)
        sys.exit(1)
        
    print("[SUCCESS] Systemic Integrity Verification Passed!")
    sys.exit(0)

if __name__ == "__main__":
    main()
