#!/usr/bin/env python3
"""
MinusCorrect Systemic Integrity Verification Script
Checks staged diffs or files for:
1. Unauthorized edits to tests/golden/ (immutable contract specs).
2. Leftover [DEBUG] traces injected during agent debugging loops in source files.
3. Unverified docstring superlatives / claims without test receipts in source files.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Ensure UTF-8 output on Windows consoles
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Ensure minuscorrect package is resolvable
repo_root = Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from minuscorrect.verifier import verify_all


def main():
    auto_fix = "--fix" in sys.argv
    strict = "--strict" in sys.argv or os.environ.get("STRICT_DOCSTRINGS") == "1"
    ok = verify_all(auto_fix=auto_fix, strict_docstrings=strict)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
