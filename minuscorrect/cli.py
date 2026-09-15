"""
MinusCorrect Unified Command-Line Interface
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List

from minuscorrect.supervisor import AgentSupervisor, SessionState
from minuscorrect.verifier import verify_all


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="minuscorrect",
        description="MinusCorrect: Systemic Integrity & Closed-Loop Verification Protocol"
    )
    subparsers = parser.add_subparsers(dest="command")

    # Command: run
    run_parser = subparsers.add_parser("run", help="Run a supervised test cycle with circuit breaker & rollback")
    run_parser.add_argument("--target", help="Target source file being modified")
    run_parser.add_argument("--session-id", default="default", help="Session ID for state persistence")
    run_parser.add_argument("--max-iterations", type=int, default=4, help="Maximum solver iterations before hard abort")
    run_parser.add_argument("--timeout", type=float, default=120.0, help="Execution timeout in seconds (default: 120.0)")
    run_parser.add_argument("--reset", action="store_true", help="Reset session before execution")
    run_parser.add_argument("test_cmd", nargs=argparse.REMAINDER, help="Test command to execute (e.g. pytest tests/golden/)")

    # Command: verify
    verify_parser = subparsers.add_parser("verify", help="Run systemic integrity pre-commit checks")
    verify_parser.add_argument("--fix", action="store_true", help="Auto-strip residual debug logs and re-stage files")
    verify_parser.add_argument("--strict", action="store_true", help="Fail on unverified docstring claims")

    # Command: status
    status_parser = subparsers.add_parser("status", help="Display current supervisor session status")
    status_parser.add_argument("--session-id", default="default", help="Session ID to inspect")

    # Command: reset
    reset_parser = subparsers.add_parser("reset", help="Reset a supervisor session")
    reset_parser.add_argument("--session-id", default="default", help="Session ID to reset")

    return parser


def handle_run(args: argparse.Namespace) -> int:
    cmd = args.test_cmd
    # Strip leading "--" if passed by caller (e.g. minuscorrect run -- pytest)
    if cmd and cmd[0] == "--":
        cmd = cmd[1:]

    if not cmd:
        print("[ERROR] No test command specified. Usage: minuscorrect run [options] -- <command>", file=sys.stderr)
        return 1

    target_path = Path(args.target) if args.target else None
    timeout_val = getattr(args, "timeout", 120.0)
    supervisor = AgentSupervisor(
        session_id=args.session_id,
        max_iterations=args.max_iterations,
        target_file=target_path,
        timeout=timeout_val
    )

    if args.reset:
        supervisor.state.reset()
        print(f"[SUPERVISOR] Reset session '{args.session_id}'.")

    result = supervisor.run_step(test_cmd=cmd)
    if result["status"] == "SUCCESS":
        return 0
    elif result["status"] == "HARD_ABORT":
        return 2
    else:
        return 1


def handle_verify(args: argparse.Namespace) -> int:
    ok = verify_all(auto_fix=args.fix, strict_docstrings=args.strict)
    return 0 if ok else 1


def handle_status(args: argparse.Namespace) -> int:
    state = SessionState.load(args.session_id)
    print(f"MinusCorrect Session Status: '{state.session_id}'")
    print(f"  Created: {state.created_at}")
    print(f"  Status: {state.status}")
    print(f"  Current Iteration: {state.current_iteration} / {state.max_iterations}")
    print(f"  Total History Records: {len(state.history)}")
    if state.history:
        print("  Recent Invocations:")
        for rec in state.history[-3:]:
            print(f"    - Iter {rec.get('iteration')}: Exit {rec.get('exit_code')} (Hash: {rec.get('hash')})")
    return 0


def handle_reset(args: argparse.Namespace) -> int:
    state = SessionState.load(args.session_id)
    state.reset()
    print(f"[SUPERVISOR] Session '{args.session_id}' reset.")
    return 0


def main(argv: List[str] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "run":
        return handle_run(args)
    elif args.command == "verify":
        return handle_verify(args)
    elif args.command == "status":
        return handle_status(args)
    elif args.command == "reset":
        return handle_reset(args)
    else:
        parser.print_help()
        return 0


def supervisor_main() -> int:
    """Entry point for mc-supervisor console script."""
    from minuscorrect.supervisor import AgentSupervisor
    # Forward to handle_run with appropriate arguments
    parser = argparse.ArgumentParser(prog="mc-supervisor", description="MinusCorrect Supervisor Runner")
    parser.add_argument("--target", help="Target source file")
    parser.add_argument("--session-id", default="default")
    parser.add_argument("--max-iterations", type=int, default=4)
    parser.add_argument("--timeout", type=float, default=120.0, help="Execution timeout in seconds")
    parser.add_argument("--reset", action="store_true")
    parser.add_argument("test_cmd", nargs=argparse.REMAINDER)

    args = parser.parse_args()
    return handle_run(args)


if __name__ == "__main__":
    sys.exit(main())
