"""
MinusCorrect Blast-Radius Patch Validator
Enforces zero-trust execution boundaries on agent-generated patches:
1. Rejects path traversal and attempts to modify forbidden files (conftest.py, tests/, root configs).
2. Restricts write blast-radius strictly to designated target source files.
3. Tests applicability atomically via git apply --check before committing to disk.
"""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path
from typing import List, Optional, Set, Tuple


# Critical files that untrusted agent patches are strictly forbidden from touching
FORBIDDEN_PATCH_PATTERNS = [
    r"(^|/)conftest\.py$",
    r"(^|/)\.github/",
    r"(^|/)\.pre-commit",
    r"^pyproject\.toml$",
    r"^setup\.(py|cfg)$",
    r"^requirements.*\.txt$",
    r"(^|/)\.env.*",
    r"(^|/)\.venv.*",
]


def extract_diff_targets(diff_text: str) -> Set[str]:
    """Extracts all target file paths modified by a unified diff."""
    targets: Set[str] = set()
    for line in diff_text.splitlines():
        if line.startswith("+++ b/"):
            path = line[6:].strip()
            if path and path != "/dev/null":
                targets.add(path)
        elif line.startswith("--- a/") and not line.startswith("--- /dev/null"):
            path = line[6:].strip()
            if path and path != "/dev/null":
                targets.add(path)
    return targets


def validate_patch_blast_radius(
    diff_text: str,
    allowed_targets: Optional[List[str]] = None,
    allow_golden_edit: bool = False
) -> Tuple[bool, List[str], str]:
    """
    Validates a patch against write blast-radius rules:
    - No forbidden files (conftest.py, build manifests, CI workflows).
    - No path traversal ('..').
    - No golden tests (tests/golden/) unless ALLOW_GOLDEN_EDIT=1.
    - If allowed_targets is set, all touched files must belong to allowed_targets.
    """
    if not diff_text or not diff_text.strip():
        return False, [], "[ERROR] Empty diff provided."

    targets = extract_diff_targets(diff_text)
    if not targets:
        return False, [], "[ERROR] No valid target files found in diff header."

    violations: List[str] = []

    # Check for path traversal and forbidden targets
    for target in targets:
        # 1. Path traversal check
        if ".." in target.split("/") or ".." in target.split("\\"):
            violations.append(f"Path traversal attempt detected in '{target}'")
            continue

        # 2. Forbidden files (conftest.py, CI, setup.py)
        normalized = target.replace("\\", "/")
        for pattern in FORBIDDEN_PATCH_PATTERNS:
            if re.search(pattern, normalized, re.IGNORECASE):
                violations.append(
                    f"Forbidden file modification detected: '{target}' matches protected pattern '{pattern}'"
                )
                break

        # 3. Golden contract modification check
        if normalized.startswith("tests/golden/"):
            env_override = os.environ.get("ALLOW_GOLDEN_EDIT") == "1" or allow_golden_edit
            if not env_override:
                violations.append(
                    f"Golden contract tampering: '{target}' cannot be modified without ALLOW_GOLDEN_EDIT=1"
                )

        # 4. Scope restriction check if allowed_targets is provided
        if allowed_targets:
            normalized_allowed = {p.replace("\\", "/").strip("./") for p in allowed_targets}
            if normalized.strip("./") not in normalized_allowed:
                violations.append(
                    f"Out-of-bounds mutation: '{target}' is not in allowed target scope {allowed_targets}"
                )

    if violations:
        msg = "[ERROR] Patch blast-radius validation FAILED:\n  - " + "\n  - ".join(violations)
        return False, list(targets), msg

    return True, list(targets), "Patch blast-radius valid."


def apply_patch_atomically(
    diff_text: str,
    cwd: Optional[Path] = None
) -> Tuple[bool, str]:
    """
    Applies a patch atomically using git apply --check first, then git apply.
    """
    base_cmd = ["git", "apply", "--ignore-whitespace", "--recount"]
    target_cwd = str(cwd) if cwd else None

    # Step 1: Pre-flight dry run
    check_res = subprocess.run(
        base_cmd + ["--check", "-"],
        input=diff_text,
        cwd=target_cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace"
    )

    if check_res.returncode != 0:
        err = check_res.stderr.strip() or check_res.stdout.strip() or "Patch conflict or corrupted diff."
        return False, f"[ERROR] Dry-run 'git apply --check' failed:\n{err}"

    # Step 2: Real application
    apply_res = subprocess.run(
        base_cmd + ["-"],
        input=diff_text,
        cwd=target_cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace"
    )

    if apply_res.returncode != 0:
        err = apply_res.stderr.strip() or apply_res.stdout.strip()
        return False, f"[ERROR] 'git apply' failed:\n{err}"

    return True, "Patch successfully applied."


# Alias for concise import
validate_patch = validate_patch_blast_radius
