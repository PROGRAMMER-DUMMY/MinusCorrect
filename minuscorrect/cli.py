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
    run_parser.add_argument("--webhook-url", help="Webhook endpoint for operational alert notifications")
    run_parser.add_argument("--worktree", action="store_true", help="Execute test run inside an isolated ephemeral git worktree")
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

    # Command: incident
    incident_parser = subparsers.add_parser("incident", help="Defensively ingest incident crash telemetry and synthesize reproduction tests")
    incident_parser.add_argument("payload", nargs="?", default="-", help="Path to crash payload file, or '-' for stdin")
    incident_parser.add_argument("--id", dest="incident_id", help="Explicit incident ID (e.g. INC-1042)")
    incident_parser.add_argument("--promote", action="store_true", help="Promote directly to tests/golden/ (requires ALLOW_GOLDEN_EDIT=1)")
    incident_parser.add_argument("--output-dir", default="tests/staging", help="Output directory for staged test (default: tests/staging)")

    # Command: patch
    patch_parser = subparsers.add_parser("patch", help="Validate write blast-radius and atomically apply agent diff")
    patch_parser.add_argument("diff_file", nargs="?", default="-", help="Path to unified diff patch file, or '-' for stdin")
    patch_parser.add_argument("--allowed-target", action="append", dest="allowed_targets", help="Whitelisted target files that may be modified")
    patch_parser.add_argument("--check-only", action="store_true", help="Perform dry-run blast radius check without applying")

    # Command: audit
    audit_parser = subparsers.add_parser("audit", help="Ingest findings.json from cloudflare/security-audit-skill")
    audit_parser.add_argument("findings_file", nargs="?", default="findings.json", help="Path to findings.json (default: findings.json)")
    audit_parser.add_argument("--output-dir", default="tests/staging", help="Output directory for staged contracts (default: tests/staging)")

    # Command: pr
    pr_parser = subparsers.add_parser("pr", help="Generate Draft PR proposal and decouple autonomous fixes from main")
    pr_parser.add_argument("--session-id", default="default", help="Session ID to export (default: default)")
    pr_parser.add_argument("--branch", dest="branch_name", help="Target branch name (default: minuscorrect/patch-<session-id>)")
    pr_parser.add_argument("--summary", default="Automated defect repair via MinusCorrect supervisor", help="Summary of changes")
    pr_parser.add_argument("--output-file", help="Path to output markdown file (default: DRAFT-PR-<session-id>.md)")
    pr_parser.add_argument("--commit-and-branch", action="store_true", help="Create isolated git branch and commit modified files")

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
    webhook_url = getattr(args, "webhook_url", None)
    use_worktree = getattr(args, "worktree", False)

    if use_worktree:
        from minuscorrect.worktree import EphemeralWorktree
        with EphemeralWorktree() as wt_path:
            print(f"[SUPERVISOR] Executing within isolated ephemeral worktree: {wt_path}")
            supervisor = AgentSupervisor(
                session_id=args.session_id,
                max_iterations=args.max_iterations,
                target_file=target_path,
                timeout=timeout_val,
                webhook_url=webhook_url,
                cwd=wt_path,
            )
            if args.reset:
                supervisor.state.reset()
                print(f"[SUPERVISOR] Reset session '{args.session_id}'.")
            result = supervisor.run_step(test_cmd=cmd)
    else:
        supervisor = AgentSupervisor(
            session_id=args.session_id,
            max_iterations=args.max_iterations,
            target_file=target_path,
            timeout=timeout_val,
            webhook_url=webhook_url,
        )
        if args.reset:
            supervisor.state.reset()
            print(f"[SUPERVISOR] Reset session '{args.session_id}'.")
        result = supervisor.run_step(test_cmd=cmd)

    if result["status"] == "SUCCESS":
        return 0
    elif result["status"] == "HARD_ABORT":
        return 2
    elif result["status"] == "TAMPERING_DETECTED":
        return 3
    else:
        return 1


def handle_pr(args: argparse.Namespace) -> int:
    from minuscorrect.pr import create_draft_pr_artifact
    out_file = Path(args.output_file) if args.output_file else None
    try:
        pr_artifact = create_draft_pr_artifact(
            session_id=args.session_id,
            branch_name=args.branch_name,
            summary=args.summary,
            output_file=out_file,
            commit_and_branch=args.commit_and_branch,
        )
        print(f"[SUCCESS] Draft PR proposal artifact generated: {pr_artifact.resolve()}")
        return 0
    except Exception as exc:
        print(f"[ERROR] Failed to generate Draft PR artifact: {exc}", file=sys.stderr)
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


def handle_incident(args: argparse.Namespace) -> int:
    from minuscorrect.incident import (
        generate_rca_report,
        generate_staged_test,
        parse_incident_payload,
        promote_incident_to_golden,
    )

    if args.payload == "-" or not args.payload:
        if sys.stdin.isatty():
            print("[INFO] Paste crash payload JSON or traceback (press Ctrl+D or Ctrl+Z when done):", file=sys.stderr)
        raw_content = sys.stdin.read()
    else:
        payload_file = Path(args.payload)
        if not payload_file.exists():
            print(f"[ERROR] Payload file not found: {payload_file}", file=sys.stderr)
            return 1
        raw_content = payload_file.read_text(encoding="utf-8", errors="replace")

    if not raw_content.strip():
        print("[ERROR] Empty incident payload received.", file=sys.stderr)
        return 1

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
            return 1
        print(f"[SUCCESS] {msg}")

    return 0


def handle_patch(args: argparse.Namespace) -> int:
    from minuscorrect.patch import apply_patch_atomically, validate_patch_blast_radius

    if args.diff_file == "-" or not args.diff_file:
        if sys.stdin.isatty():
            print("[INFO] Paste unified diff patch (press Ctrl+D or Ctrl+Z when done):", file=sys.stderr)
        diff_text = sys.stdin.read()
    else:
        patch_path = Path(args.diff_file)
        if not patch_path.exists():
            print(f"[ERROR] Patch file not found: {patch_path}", file=sys.stderr)
            return 1
        diff_text = patch_path.read_text(encoding="utf-8", errors="replace")

    if not diff_text.strip():
        print("[ERROR] Empty diff received.", file=sys.stderr)
        return 1

    valid, targets, msg = validate_patch_blast_radius(
        diff_text=diff_text,
        allowed_targets=args.allowed_targets
    )

    if not valid:
        print(msg, file=sys.stderr)
        return 1

    print(f"[SUCCESS] Blast-radius check PASSED. Touched targets: {', '.join(targets)}")

    if args.check_only:
        print("[INFO] Dry-run check requested. Patch was NOT applied to working tree.")
        return 0

    applied, apply_msg = apply_patch_atomically(diff_text=diff_text)
    if not applied:
        print(apply_msg, file=sys.stderr)
        return 1

    print(f"[SUCCESS] {apply_msg}")
    return 0


def handle_audit(args: argparse.Namespace) -> int:
    from minuscorrect.audit import (
        generate_security_audit_summary,
        generate_staged_security_test,
        parse_audit_findings,
    )

    audit_file = Path(args.findings_file)
    if not audit_file.exists():
        print(f"[ERROR] Audit findings file not found: {audit_file}", file=sys.stderr)
        return 1

    raw_json = audit_file.read_text(encoding="utf-8", errors="replace")
    confirmed, needs_val, rejected = parse_audit_findings(raw_json)

    print(f"[INFO] Ingested {len(confirmed)} confirmed, {len(needs_val)} unvalidated, {len(rejected)} rejected findings.")

    staged_tests = []
    for finding in confirmed:
        test_path = generate_staged_security_test(finding, output_dir=Path(args.output_dir))
        staged_tests.append(test_path)
        print(f"[SUCCESS] Staged security reproduction contract: {test_path.resolve()}")

    summary_path = generate_security_audit_summary(confirmed, needs_val, rejected)
    print(f"[SUCCESS] Audit summary generated: {summary_path.resolve()}")

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
    elif args.command == "incident":
        return handle_incident(args)
    elif args.command == "patch":
        return handle_patch(args)
    elif args.command == "audit":
        return handle_audit(args)
    elif args.command == "pr":
        return handle_pr(args)
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
