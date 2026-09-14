#!/usr/bin/env python3
"""
MinusCorrect Autonomous Supervisor CLI Wrapper
Delegates to minuscorrect.cli / minuscorrect.supervisor with full state persistence,
volatile-token error hash sanitization, and git-tree atomic rollback.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure package is resolvable when executing directly from scripts/
repo_root = Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from minuscorrect.cli import build_parser, handle_run, handle_status, handle_reset


def main():
    parser = build_parser()
    # If run without subcommand (e.g. legacy: python scripts/supervisor.py check --target ...), map it
    if len(sys.argv) > 1 and sys.argv[1] == "check":
        # Legacy compatibility: translate 'check' to 'run'
        args_list = ["run"] + sys.argv[2:]
    else:
        args_list = sys.argv[1:]

    args = parser.parse_args(args_list)

    if args.command == "run":
        sys.exit(handle_run(args))
    elif args.command == "status":
        sys.exit(handle_status(args))
    elif args.command == "reset":
        sys.exit(handle_reset(args))
    else:
        parser.print_help()
        sys.exit(0)


if __name__ == "__main__":
    main()
