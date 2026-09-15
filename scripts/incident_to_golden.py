#!/usr/bin/env python3
"""
MinusCorrect Incident-to-Golden Pipeline CLI Utility
Accepts crash JSON or stack trace via file argument or stdin, defangs PII/injections,
creates staged test in tests/staging/, generates RCA markdown, and optionally executes supervisor.
"""

from __future__ import annotations

import argparse
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

# Ensure minuscorrect package is importable
repo_root = Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from minuscorrect.incident import (
    generate_rca_report,
    generate_staged_test,
    parse_incident_payload,
    promote_incident_to_golden,
)


def main():
    parser = argparse.ArgumentParser(
        prog="incident_to_golden",
        description="Ingest production crash telemetry, defang PII & injections, and synthesize reproduction tests."
    )
    parser.add_argument("payload", nargs="?", default="-", help="Path to crash payload file, or '-' for stdin")
    parser.add_argument("--id", dest="incident_id", help="Explicit incident ID (e.g. INC-1042)")
    parser.add_argument("--promote", action="store_true", help="Promote directly to tests/golden/ (requires ALLOW_GOLDEN_EDIT=1)")
    parser.add_argument("--output-dir", default="tests/staging", help="Output directory for staged test (default: tests/staging)")

    args = parser.parse_args()

    # Read payload
    if args.payload == "-" or not args.payload:
        if sys.stdin.isatty():
            print("[INFO] Paste crash payload JSON or traceback (press Ctrl+D or Ctrl+Z when done):", file=sys.stderr)
        raw_content = sys.stdin.read()
    else:
        payload_file = Path(args.payload)
        if not payload_file.exists():
            print(f"[ERROR] Payload file not found: {payload_file}", file=sys.stderr)
            sys.exit(1)
        raw_content = payload_file.read_text(encoding="utf-8", errors="replace")

    if not raw_content.strip():
        print("[ERROR] Empty incident payload received.", file=sys.stderr)
        sys.exit(1)

    print("[INFO] Sanitizing incident payload (defanging prompt injections & redacting PII)...")
    report = parse_incident_payload(raw=raw_content, incident_id=args.incident_id)

    staged_test = generate_staged_test(report, output_dir=Path(args.output_dir))
    print(f"[SUCCESS] Staged reproduction contract created: {staged_test.resolve()}")

    rca_path = generate_rca_report(report)
    print(f"[SUCCESS] Incident Root Cause Analysis (RCA) generated: {rca_path.resolve()}")

    if args.promote:
        ok, msg = promote_incident_to_golden(staged_test)
        if not ok:
            print(msg, file=sys.stderr)
            sys.exit(1)
        print(f"[SUCCESS] {msg}")

    print("\nNext Steps:")
    print("1. Review reproduction test and inputs in tests/staging/.")
    print(f"2. When verified, promote contract: ALLOW_GOLDEN_EDIT=1 git mv {staged_test.as_posix()} tests/golden/")
    print(f"3. Unleash MinusCorrect supervisor: minuscorrect run -- pytest tests/golden/{staged_test.name}")
    sys.exit(0)


if __name__ == "__main__":
    main()
