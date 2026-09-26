"""
MinusCorrect Unified Command-Line Interface
"""

from __future__ import annotations

import argparse
import json
import os
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
    run_parser.add_argument("-t", "--timeout", type=float, default=float(os.environ.get("MINUSCORRECT_TIMEOUT", "300.0")), help="Execution timeout in seconds (default: 300.0 or MINUSCORRECT_TIMEOUT)")
    run_parser.add_argument("--isolate-env", action="store_true", help="Sanitize ambient credentials/tokens from test subprocess environment")
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
    incident_parser.add_argument("--no-defang", action="store_true", help="Preserve raw attack payloads bit-exact without prompt injection defanging (for LLM security testing)")

    # Command: patch
    patch_parser = subparsers.add_parser("patch", help="Validate write blast-radius and atomically apply agent diff")
    patch_parser.add_argument("diff_file", nargs="?", default="-", help="Path to unified diff patch file, or '-' for stdin")
    patch_parser.add_argument("--allowed-target", action="append", dest="allowed_targets", help="Whitelisted target files that may be modified")
    patch_parser.add_argument("--check-only", action="store_true", help="Perform dry-run blast radius check without applying")

    # Command: audit
    audit_parser = subparsers.add_parser("audit", help="Run 10-domain pre-launch operational security audit or ingest findings.json")
    audit_parser.add_argument("findings_file", nargs="?", default=None, help="Path to findings.json (optional when using --pre-launch)")
    audit_parser.add_argument("--pre-launch", action="store_true", help="Run 10-domain pre-launch operational and security audit for AI-generated systems")
    audit_parser.add_argument("--target-dir", default=None, help="Target directory for pre-launch audit (default: current workspace)")
    audit_parser.add_argument("--json", action="store_true", help="Output audit results in JSON format")
    audit_parser.add_argument("--output-dir", default="tests/staging", help="Output directory for staged contracts (default: tests/staging)")

    # Command: spec
    spec_parser = subparsers.add_parser("spec", help="Scaffold and manage project specifications (PRD, TRD, Refero DESIGN, APPFLOW, SCHEMA with RLS, Ask-Matt PLAN)")
    spec_subparsers = spec_parser.add_subparsers(dest="spec_action")

    spec_init = spec_subparsers.add_parser("init", help="Scaffold full blueprint specification suite into a directory")
    spec_init.add_argument("--dir", dest="output_dir", default="spec", help="Target directory for specification files (default: spec)")
    spec_init.add_argument("--name", dest="project_name", default="Enterprise Application", help="Project name")
    spec_init.add_argument("--desc", dest="description", default="High-velocity enterprise application", help="Project description")
    spec_init.add_argument("--force", action="store_true", help="Overwrite existing specification files")

    spec_gen = spec_subparsers.add_parser("generate", help="Generate a specific spec artifact")
    spec_gen.add_argument("artifact", choices=["prd", "trd", "design", "appflow", "schema", "plan", "all"], help="Specific artifact to generate")
    spec_gen.add_argument("--dir", dest="output_dir", default="spec", help="Target directory (default: spec)")
    spec_gen.add_argument("--name", dest="project_name", default="Enterprise Application", help="Project name")
    spec_gen.add_argument("--desc", dest="description", default="High-velocity enterprise application", help="Project description")
    spec_gen.add_argument("--force", action="store_true", help="Overwrite existing specification files")

    # Command: pr
    pr_parser = subparsers.add_parser("pr", help="Generate Draft PR proposal and decouple autonomous fixes from main")
    pr_parser.add_argument("--session-id", default="default", help="Session ID to export (default: default)")
    pr_parser.add_argument("--branch", dest="branch_name", help="Target branch name (default: minuscorrect/patch-<session-id>)")
    pr_parser.add_argument("--summary", default="Automated defect repair via MinusCorrect supervisor", help="Summary of changes")
    pr_parser.add_argument("--output-file", help="Path to output markdown file (default: DRAFT-PR-<session-id>.md)")
    pr_parser.add_argument("--commit-and-branch", action="store_true", help="Create isolated git branch and commit modified files")

    # Command: mcp
    subparsers.add_parser("mcp", help="Launch Model Context Protocol (MCP) JSON-RPC 2.0 stdio server")

    # Command: doctor
    doctor_parser = subparsers.add_parser("doctor", help="Run pre-flight environment diagnostics and health checks")
    doctor_parser.add_argument("--json", action="store_true", help="Output diagnostic results in JSON format")

    # Command: council
    council_parser = subparsers.add_parser("council", help="Convene the 5-advisor LLM Council protocol")
    council_parser.add_argument("query", nargs="?", default=None, help="Architectural question, trade-off, or bug triage dilemma")
    council_parser.add_argument("--json", action="store_true", help="Output council prompt schema in JSON")
    council_parser.add_argument("--decision-engine", choices=["auto", "local", "jev", "mock"], default="auto", help="Decision engine for council Stage-2 evaluation (default: auto)")

    # Command: ask-matt
    ask_matt_parser = subparsers.add_parser("ask-matt", help="Generate Matt Pocock Spec-to-Tickets DAG execution plan")
    ask_matt_parser.add_argument("idea", nargs="?", default=None, help="Feature request or bug report to decompose")
    ask_matt_parser.add_argument("--json", action="store_true", help="Output tickets schema in JSON")
    ask_matt_parser.add_argument("--save", action="store_true", help="Save generated tickets directly to .minus/tickets/open/")

    # Command: ticket
    ticket_parser = subparsers.add_parser("ticket", help="Manage .minus/ second-brain tickets and lifecycle states")
    ticket_subparsers = ticket_parser.add_subparsers(dest="ticket_action")

    ticket_list = ticket_subparsers.add_parser("list", help="List tickets in second-brain store")
    ticket_list.add_argument("--status", choices=["open", "completed", "all"], default="all", help="Filter by ticket status (default: all)")
    ticket_list.add_argument("--json", action="store_true", help="Output tickets in JSON format")

    ticket_create = ticket_subparsers.add_parser("create", help="Create a new ticket in .minus/tickets/open/")
    ticket_create.add_argument("-t", "--title", required=True, help="Ticket title")
    ticket_create.add_argument("--role", default="Process Isolation SRE", help="Assigned domain specialist role")
    ticket_create.add_argument("--objective", default="", help="Specific behavioral objective")
    ticket_create.add_argument("--target", action="append", dest="target_files", help="In-scope target files")
    ticket_create.add_argument("--verification", default="minuscorrect verify --fix --strict", help="Verification command")

    ticket_view = ticket_subparsers.add_parser("view", help="View ticket details and frontmatter")
    ticket_view.add_argument("ticket_id", help="Ticket ID (e.g. T-001)")

    ticket_close = ticket_subparsers.add_parser("close", help="Close ticket and record execution receipt")
    ticket_close.add_argument("ticket_id", help="Ticket ID (e.g. T-001)")
    ticket_close.add_argument("--commit", default="HEAD", help="Commit SHA verified by this ticket")
    ticket_close.add_argument("--test-cmd", default="minuscorrect verify", help="Test command executed")
    ticket_close.add_argument("--exit-code", type=int, default=0, help="Test exit code")
    ticket_close.add_argument("--specialist", default="", help="Specialist signing off on ticket")

    ticket_diff = ticket_subparsers.add_parser("diff", help="Inspect unified diff patch for a ticket")
    ticket_diff.add_argument("ticket_id", help="Ticket ID (e.g. T-001)")

    ticket_rollback = ticket_subparsers.add_parser("rollback", help="Safely rollback a completed ticket")
    ticket_rollback.add_argument("ticket_id", help="Ticket ID (e.g. T-001)")
    ticket_rollback.add_argument("--force", action="store_true", help="Force rollback even if tree dirty or verification fails")
    ticket_rollback.add_argument("--no-verify", action="store_true", help="Skip post-rollback verification")
    ticket_rollback.add_argument("--reopen", action="store_true", help="Move ticket back to open/ for repair instead of rolled_back/")
    ticket_rollback.add_argument("--json", action="store_true", help="Output result in JSON format")

    # Command: route
    route_parser = subparsers.add_parser("route", help="Smart Intent Router: classify request into optimal MinusCorrect route")
    route_parser.add_argument("query", help="Natural language request or telemetry text")
    route_parser.add_argument("--json", action="store_true", help="Output routing decision in JSON format")

    # Command: anti-cheat
    anti_cheat_parser = subparsers.add_parser("anti-cheat", help="Audit repository against benchmark overfitting, hardcoded bypasses, and tautologies")
    anti_cheat_parser.add_argument("--source-dir", default="minuscorrect", help="Source code directory (default: minuscorrect)")
    anti_cheat_parser.add_argument("--test-dir", default="tests", help="Tests directory (default: tests)")
    anti_cheat_parser.add_argument("--ban", help="Register a banned benchmark fixture token or anti-pattern literal into .minus/anti_patterns.json")
    anti_cheat_parser.add_argument("--list-banned", action="store_true", help="List all currently registered banned benchmark tokens")
    anti_cheat_parser.add_argument("--json", action="store_true", help="Output audit report in JSON format")

    # Command: research
    research_parser = subparsers.add_parser("research", help="Deep Web Research Swarm & Knowledge Ontology Protocol")
    research_parser.add_argument("topic", nargs="?", default=None, help="Topic or technical architecture to research deeply, or 'list'/'view'")
    research_parser.add_argument("target_id", nargs="?", default=None, help="Target research session ID (e.g. RES-001) when viewing")
    research_parser.add_argument("--waves", type=int, default=3, choices=[1, 2, 3], help="Number of research waves to plan (default: 3)")
    research_parser.add_argument("--save", action="store_true", help="Save complete research report and comparison matrix into .minus/research/")
    research_parser.add_argument("--json", action="store_true", help="Output research plan and agent specs in JSON format")
    research_parser.add_argument("--out", dest="output_file", help="Export research plan to markdown file")

    # Command: plugin
    plugin_parser = subparsers.add_parser("plugin", help="Manage MinusCorrect agent integrations (Antigravity CLI, Claude Code)")
    plugin_parser.add_argument("action", choices=["status", "install"], help="Action to perform: 'status' or 'install'")

    # Command: harness
    harness_parser = subparsers.add_parser("harness", help="Manage SuperQode harness integrations and specs")
    harness_subparsers = harness_parser.add_subparsers(dest="harness_action")
    harness_export = harness_subparsers.add_parser("export", help="Export MinusCorrect SuperQode HarnessSpec")
    harness_export.add_argument("--format", choices=["json", "yaml"], default="json", help="Output format (default: json)")

    # Command: intake (alias: plan)
    intake_parser = subparsers.add_parser("intake", aliases=["plan"], help="Cognitive Intent Ingestion: extract invariants, auto-register rules, convene council, and write Ask-Matt tickets")
    intake_parser.add_argument("prompt", help="Natural language request, instruction, or feature description")
    intake_parser.add_argument("--no-save", action="store_true", help="Dry run without writing tickets or rules to .minus/")
    intake_parser.add_argument("--json", action="store_true", help="Output intake results in JSON format")

    # Command: rule
    rule_parser = subparsers.add_parser("rule", help="Manage .minus/ second-brain project rules and invariants")
    rule_sub = rule_parser.add_subparsers(dest="rule_action")

    rule_list = rule_sub.add_parser("list", help="List rules in second-brain store")
    rule_list.add_argument("--scope", help="Filter by scope (e.g. security, code, research)")
    rule_list.add_argument("--json", action="store_true", help="Output rules in JSON format")

    rule_view = rule_sub.add_parser("view", help="View rule details")
    rule_view.add_argument("rule_id", help="Rule ID (e.g. RULE-001)")

    rule_add = rule_sub.add_parser("add", help="Add custom natural language rule")
    rule_add.add_argument("title", help="Rule title")
    rule_add.add_argument("--instruction", "-i", required=True, help="Natural language instruction for agents")
    rule_add.add_argument("--scope", choices=["general", "code", "security", "research", "database", "frontend", "distributed"], default="general")
    rule_add.add_argument("--enforcement", choices=["strict", "advisory"], default="strict")

    # Command: diff
    diff_parser = subparsers.add_parser("diff", help="Inspect unified diff patch for a Second-Brain ticket")
    diff_parser.add_argument("ticket_id", help="Ticket ID (e.g. T-001)")

    # Command: rollback
    rollback_parser = subparsers.add_parser("rollback", help="Atomic Rollback Engine: safely revert an agent ticket's commit with verification gates")
    rollback_parser.add_argument("ticket_id", help="Ticket ID (e.g. T-001)")
    rollback_parser.add_argument("--force", action="store_true", help="Force rollback even if tree dirty or verification fails")
    rollback_parser.add_argument("--no-verify", action="store_true", help="Skip post-rollback verification")
    rollback_parser.add_argument("--reopen", action="store_true", help="Move ticket back to open/ for repair instead of rolled_back/")
    rollback_parser.add_argument("--json", action="store_true", help="Output result in JSON format")

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
    timeout_val = getattr(args, "timeout", None)
    isolate_env_val = getattr(args, "isolate_env", False)
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
                isolate_env=isolate_env_val,
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
            isolate_env=isolate_env_val,
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

    defang_mode = not getattr(args, "no_defang", False)
    if defang_mode:
        print("[INFO] Sanitizing incident payload (defanging prompt injections & redacting PII)...")
    else:
        print("[INFO] Preserving raw incident payload (--no-defang active, redacting credentials only)...")
    report = parse_incident_payload(raw=raw_content, incident_id=args.incident_id, defang=defang_mode)

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
    if getattr(args, "pre_launch", False):
        from minuscorrect.audit import run_pre_launch_audit
        target_dir = Path(args.target_dir) if getattr(args, "target_dir", None) else Path.cwd()
        report = run_pre_launch_audit(target_dir=target_dir)
        if getattr(args, "json", False):
            print(report.to_json())
        else:
            print(report.format_text())
        return 1 if report.blocks_launch else 0

    from minuscorrect.audit import (
        generate_security_audit_summary,
        generate_staged_security_test,
        parse_audit_findings,
    )

    findings_path = getattr(args, "findings_file", None) or "findings.json"
    audit_file = Path(findings_path)
    if not audit_file.exists():
        print(f"[ERROR] Audit findings file not found: {audit_file}", file=sys.stderr)
        print("[TIP] To execute the 10-domain pre-launch operational security audit, run: minuscorrect audit --pre-launch", file=sys.stderr)
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


def handle_spec(args: argparse.Namespace) -> int:
    from minuscorrect.spec import (
        generate_prd,
        generate_trd,
        generate_refero_design,
        generate_appflow,
        generate_schema,
        generate_plan,
        scaffold_spec_suite,
    )

    action = getattr(args, "spec_action", "init") or "init"
    out_dir = Path(getattr(args, "output_dir", "spec") or "spec")
    name = getattr(args, "project_name", "Enterprise Application") or "Enterprise Application"
    desc = getattr(args, "description", "") or ""
    force = getattr(args, "force", False)

    if action == "init" or (action == "generate" and getattr(args, "artifact", "all") == "all"):
        out_dir.mkdir(parents=True, exist_ok=True)
        results = scaffold_spec_suite(output_dir=out_dir, project_name=name, description=desc)
        print(f"[SUCCESS] Scaffolded {len(results)} specification files in {out_dir.resolve()}:")
        for filename, path in results.items():
            print(f"  - {filename} ({path.stat().st_size} bytes)")
        return 0

    artifact = getattr(args, "artifact", "all")
    mapping = {
        "prd": ("PRD.md", lambda: generate_prd(name, desc)),
        "trd": ("TRD.md", lambda: generate_trd(name, desc)),
        "design": ("DESIGN.md", lambda: generate_refero_design(name)),
        "appflow": ("APPFLOW.md", lambda: generate_appflow(name)),
        "schema": ("SCHEMA.sql", lambda: generate_schema(name)),
        "plan": ("PLAN.md", lambda: generate_plan(name, desc)),
    }

    if artifact in mapping:
        filename, gen_fn = mapping[artifact]
        out_dir.mkdir(parents=True, exist_ok=True)
        target = out_dir / filename
        if target.exists() and not force:
            print(f"[INFO] {target} already exists. Skipping (use --force to overwrite).")
            return 0
        content = gen_fn()
        target.write_text(content, encoding="utf-8")
        print(f"[SUCCESS] Generated {target.resolve()} ({len(content.encode('utf-8'))} bytes)")
        return 0

    print(f"[ERROR] Unknown spec action or artifact: {artifact}", file=sys.stderr)
    return 1


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
    elif args.command == "spec":
        return handle_spec(args)
    elif args.command == "pr":
        return handle_pr(args)
    elif args.command == "mcp":
        return handle_mcp(args)
    elif args.command == "doctor":
        return handle_doctor(args)
    elif args.command == "council":
        return handle_council(args)
    elif args.command == "ask-matt":
        return handle_ask_matt(args)
    elif args.command == "plugin":
        return handle_plugin(args)
    elif args.command == "harness":
        return handle_harness(args)
    elif args.command == "ticket":
        return handle_ticket(args)
    elif args.command == "route":
        return handle_route(args)
    elif args.command == "anti-cheat":
        return handle_anti_cheat(args)
    elif args.command == "research":
        return handle_research(args)
    elif args.command in ("intake", "plan"):
        return handle_intake(args)
    elif args.command == "rule":
        return handle_rule(args)
    elif args.command == "diff":
        return handle_diff(args)
    elif args.command == "rollback":
        return handle_rollback(args)
    else:
        parser.print_help()
        return 0


def handle_intake(args: argparse.Namespace) -> int:
    from minuscorrect.intake import run_intake_pipeline
    result = run_intake_pipeline(
        prompt=args.prompt,
        auto_save=not getattr(args, "no_save", False),
    )
    if getattr(args, "json", False):
        import json
        payload = {
            "intent": result.intent.to_dict(),
            "registered_rules": result.registered_rules,
            "council_synthesis": result.council_synthesis,
            "generated_tickets": result.generated_tickets,
            "research_id": result.research_id,
        }
        print(json.dumps(payload, indent=2))
    else:
        print(result.render_markdown())
    return 0


def handle_rule(args: argparse.Namespace) -> int:
    from minuscorrect.store import MinusStore
    store = MinusStore()
    action = getattr(args, "rule_action", "list") or "list"

    if action == "list":
        rules = store.list_rules(scope=getattr(args, "scope", None))
        if getattr(args, "json", False):
            import json
            print(json.dumps(rules, indent=2))
        else:
            if not rules:
                print("[INFO] No rules registered in .minus/rules/.")
            else:
                print(f"MinusCorrect Registered Project Rules ({len(rules)} total):")
                print(f"{'ID':<10} {'SCOPE':<12} {'ENFORCEMENT':<14} {'TITLE'}")
                print("-" * 72)
                for r in rules:
                    print(f"{r.get('id', ''):<10} {r.get('scope', '').upper():<12} {r.get('enforcement', '').upper():<14} {r.get('title', '')}")
        return 0

    elif action == "view":
        content = store.get_rule(args.rule_id)
        if not content:
            print(f"[ERROR] Rule '{args.rule_id}' not found in .minus/rules/.", file=sys.stderr)
            return 1
        print(content)
        return 0

    elif action == "add":
        rid = store.save_rule(
            title=args.title,
            instruction=args.instruction,
            scope=args.scope,
            enforcement=args.enforcement,
        )
        print(f"[SUCCESS] Saved rule {rid} in .minus/rules/{rid}.md and registered in index.json")
        return 0

    return 0


def handle_research(args: argparse.Namespace) -> int:
    import json
    from minuscorrect.research import (
        DeepResearchCoordinator,
        ResearchFinding,
        ResearchWave,
    )
    from minuscorrect.store import MinusStore

    store = MinusStore()
    topic = (args.topic or "").strip()

    if topic == "list":
        sessions = store.list_research()
        if getattr(args, "json", False):
            print(json.dumps(sessions, indent=2))
        else:
            if not sessions:
                print("[INFO] No research sessions found in .minus/research/.")
            else:
                print(f"MinusCorrect Saved Web Research Sessions ({len(sessions)} total):")
                print(f"{'ID':<10} {'CONSENSUS':<18} {'FINDINGS':<10} {'DATE':<22} {'TOPIC'}")
                print("-" * 84)
                for s in sessions:
                    date_str = s.get('created_at', '')[:19].replace('T', ' ')
                    print(f"{s.get('id', ''):<10} {s.get('consensus_verdict', 'Consensus')[:16]:<18} {s.get('findings_count', 0):<10} {date_str:<22} {s.get('topic', '')}")
        return 0

    if topic in ("view", "compare"):
        target_id = args.target_id
        if not target_id:
            print("[ERROR] Missing research ID. Usage: minuscorrect research view <RES-ID>", file=sys.stderr)
            return 1
        content = store.get_research(target_id)
        if not content:
            print(f"[ERROR] Research session '{target_id}' not found in .minus/research/.", file=sys.stderr)
            return 1
        print(content)
        return 0

    if not topic:
        print("[ERROR] Missing research topic. Usage: minuscorrect research \"<topic>\" [--waves 3] [--save]", file=sys.stderr)
        return 1

    coordinator = DeepResearchCoordinator(topic)

    w0_queries = coordinator.plan_wave_0()
    w1_queries = coordinator.plan_wave_1() if args.waves >= 2 else []
    w2_queries = coordinator.plan_wave_2() if args.waves >= 3 else []

    all_queries = w0_queries + w1_queries + w2_queries
    subagent_specs = coordinator.generate_subagent_specs(all_queries)

    if getattr(args, "json", False):
        payload = {
            "topic": topic,
            "waves": {
                "wave_0_scout": [q.to_dict() for q in w0_queries],
                "wave_1_expansion": [q.to_dict() for q in w1_queries],
                "wave_2_deep_swarm": [q.to_dict() for q in w2_queries],
            },
            "subagent_specs": subagent_specs,
        }
        print(json.dumps(payload, indent=2))
        return 0

    print("=" * 76)
    print(f"       MinusCorrect Deep Research Swarm: '{topic}'")
    print("=" * 76)
    print(f"Wave 0 (Scout):       {len(w0_queries)} Agent (Landscape Reconnaissance & Unknowns)")
    if args.waves >= 2:
        print(f"Wave 1 (Expansion):   {len(w1_queries)} Agents (Orthogonal Architecture & Failure Modes)")
    if args.waves >= 3:
        print(f"Wave 2 (Deep Swarm):  {len(w2_queries)} Agents (Parallel Specialized Deep Dives)")
    print(f"Total Research Nodes: {len(all_queries)} Dispatched Subagents")
    print("-" * 76)
    print("Agent Dispatch Plan:")
    for idx, q in enumerate(all_queries, 1):
        print(f"  {idx:02d}. [{q.wave.value:<17}] {q.role:<38} -> {q.angle}")
    print("=" * 76)

    # If --save requested, synthesize full report with comparative analysis and store in .minus/research/
    if getattr(args, "save", False):
        baseline_findings = []
        for q in all_queries:
            domain = q.target_domains[0] if q.target_domains else "authoritative-docs.org"
            baseline_findings.append(
                ResearchFinding(
                    query=q,
                    source_url=f"https://{domain}/spec/{topic.lower().replace(' ', '-')}",
                    title=f"{q.role} - Technical Specification & Analysis",
                    summary=f"Analysis of {topic} covering {q.angle}.",
                    sub_topics=[w.strip() for w in q.angle.split(",") if w.strip()][:4],
                )
            )

        analysis = coordinator.analyze_and_compare(baseline_findings)
        ontology = coordinator.synthesize_ontology(baseline_findings)
        report_md = coordinator.render_full_report(baseline_findings, analysis=analysis, ontology=ontology)

        rid = store.save_research(
            topic=topic,
            report_markdown=report_md,
            metadata={
                "findings_count": len(baseline_findings),
                "sources_count": ontology.sources_count,
                "consensus_score": analysis.consensus_score,
                "consensus_verdict": analysis.consensus_verdict,
                "contradictions_count": len(analysis.contradictions),
            },
        )
        print(f"[SUCCESS] Complete research report saved to .minus/research/{rid}.md")
        print(f"          Registered in .minus/index.json (Consensus: {analysis.consensus_verdict})")

    if args.output_file:
        out_path = Path(args.output_file)
        lines = [
            f"# Deep Research Swarm Plan: {topic}",
            "",
            "- **Protocol**: Recursive 3-Wave Multi-Agent Ontology (1 -> 3 -> 8)",
            f"- **Total Swarm Size**: {len(all_queries)} Agents",
            "",
            "## Wave 0: Foundational Scout",
        ]
        for q in w0_queries:
            lines.append(f"- **{q.role}**: {q.angle} (Domains: {', '.join(q.target_domains)})")
        if w1_queries:
            lines.append("")
            lines.append("## Wave 1: Orthogonal Expansion")
            for q in w1_queries:
                lines.append(f"- **{q.role}**: {q.angle} (Domains: {', '.join(q.target_domains)})")
        if w2_queries:
            lines.append("")
            lines.append("## Wave 2: Specialized Deep Swarm")
            for q in w2_queries:
                lines.append(f"- **{q.role}**: {q.angle} (Domains: {', '.join(q.target_domains)})")
        out_path.write_text("\n".join(lines), encoding="utf-8")
        print(f"[SUCCESS] Research plan exported to {out_path}")
    return 0


def handle_harness(args: argparse.Namespace) -> int:
    from minuscorrect.harness import export_superqode_harness_spec
    action = getattr(args, "harness_action", "export") or "export"
    if action == "export":
        fmt = getattr(args, "format", "json")
        print(export_superqode_harness_spec(format_type=fmt))
        return 0
    return 0


def handle_council(args: argparse.Namespace) -> int:
    from minuscorrect.orchestrator import generate_council_protocol
    output = generate_council_protocol(query=args.query, as_json=getattr(args, "json", False))
    print(output)
    return 0


def handle_ask_matt(args: argparse.Namespace) -> int:
    from minuscorrect.orchestrator import generate_ask_matt_plan
    output = generate_ask_matt_plan(
        idea=args.idea,
        as_json=getattr(args, "json", False),
        save_to_store=getattr(args, "save", False),
    )
    print(output)
    if getattr(args, "save", False):
        print("[SUCCESS] Tickets saved directly into .minus/tickets/open/ and registered in index.json")
    return 0


def handle_ticket(args: argparse.Namespace) -> int:
    from minuscorrect.store import MinusStore
    store = MinusStore()
    action = getattr(args, "ticket_action", "list") or "list"

    if action == "list":
        status_filter = None if args.status == "all" else args.status
        tickets = store.list_tickets(status=status_filter)
        if getattr(args, "json", False):
            print(json.dumps(tickets, indent=2))
        else:
            if not tickets:
                print(f"[INFO] No tickets found matching status '{args.status}'.")
            else:
                print(f"MinusCorrect Second-Brain Tickets ({len(tickets)} total):")
                print(f"{'ID':<10} {'STATUS':<12} {'ROLE':<30} {'TITLE'}")
                print("-" * 78)
                for t in tickets:
                    print(f"{t.get('id', ''):<10} {t.get('status', '').upper():<12} {t.get('role', ''):<30} {t.get('title', '')}")
        return 0

    elif action == "create":
        ticket = store.create_ticket(
            title=args.title,
            role=args.role,
            objective=args.objective or args.title,
            target_files=args.target_files,
            verification=args.verification,
        )
        print(f"[SUCCESS] Created ticket {ticket.id} in .minus/tickets/open/{ticket.id}.md")
        return 0

    elif action == "view":
        ticket = store.get_ticket(args.ticket_id)
        if not ticket:
            print(f"[ERROR] Ticket '{args.ticket_id}' not found.", file=sys.stderr)
            return 1
        print(ticket.to_markdown())
        return 0

    elif action == "close":
        try:
            ticket = store.close_ticket(
                ticket_id=args.ticket_id,
                commit_sha=args.commit,
                test_command=args.test_cmd,
                exit_code=args.exit_code,
                specialist=args.specialist,
            )
            print(f"[SUCCESS] Closed ticket {ticket.id}. Transitioned to .minus/tickets/completed/{ticket.id}.md")
            print(f"          Recorded receipt: Commit {args.commit}, Exit Code {args.exit_code}")
            return 0
        except FileNotFoundError as exc:
            print(f"[ERROR] {exc}", file=sys.stderr)
            return 1

    elif action == "diff":
        return handle_diff(args)

    elif action == "rollback":
        return handle_rollback(args)

    print(f"[ERROR] Unknown ticket action: {action}", file=sys.stderr)
    return 1


def handle_diff(args: argparse.Namespace) -> int:
    from minuscorrect.rollback import RollbackEngine
    engine = RollbackEngine()
    diff_text = engine.inspect_diff(args.ticket_id)
    if not diff_text:
        print(f"[ERROR] No diff patch found for ticket '{args.ticket_id}'.", file=sys.stderr)
        return 1
    print(f"=== Unified Diff Snapshot: {args.ticket_id} ===")
    print(diff_text)
    return 0


def handle_rollback(args: argparse.Namespace) -> int:
    from minuscorrect.rollback import RollbackEngine
    engine = RollbackEngine()
    result = engine.rollback_ticket(
        ticket_id=args.ticket_id,
        force=getattr(args, "force", False),
        verify=not getattr(args, "no_verify", False),
        reopen=getattr(args, "reopen", False),
    )
    if getattr(args, "json", False):
        print(json.dumps(result.to_dict(), indent=2))
    else:
        if result.success:
            print(f"[SUCCESS] {result.message}")
            if result.revert_commit:
                print(f"          Revert Commit: {result.revert_commit}")
        else:
            print(f"[ERROR] Rollback failed ({result.status}): {result.message}", file=sys.stderr)
            if result.verification_output:
                print(f"[VERIFICATION TRACE]\n{result.verification_output[:500]}", file=sys.stderr)
    return 0 if result.success else 1


def handle_route(args: argparse.Namespace) -> int:
    from minuscorrect.router import route_intent
    decision = route_intent(args.query)
    if getattr(args, "json", False):
        print(decision.to_json())
    else:
        print(decision.format_text())
    return 0


def handle_anti_cheat(args: argparse.Namespace) -> int:
    from minuscorrect.anti_cheat import (
        add_banned_anti_pattern,
        audit_against_benchmark_cheats,
        load_banned_anti_patterns,
    )

    if getattr(args, "ban", None):
        literal = args.ban.strip()
        added = add_banned_anti_pattern(literal)
        if added:
            print(f"[SUCCESS] Registered banned anti-pattern '{literal}' in .minus/anti_patterns.json")
        else:
            print(f"[INFO] Banned anti-pattern '{literal}' already present in .minus/anti_patterns.json")
        return 0

    if getattr(args, "list_banned", False):
        banned = load_banned_anti_patterns()
        if not banned:
            print("[INFO] No banned anti-patterns registered in .minus/anti_patterns.json")
        else:
            print(f"Registered Banned Benchmark Fixture Tokens ({len(banned)} total):")
            for token in sorted(banned):
                print(f"  - \"{token}\"")
        return 0

    src_dir = Path(args.source_dir)
    test_dir = Path(args.test_dir)
    if not src_dir.exists():
        src_dir = Path.cwd() / "minuscorrect"
    if not test_dir.exists():
        test_dir = Path.cwd() / "tests"

    report = audit_against_benchmark_cheats(src_dir, test_dir)
    if getattr(args, "json", False):
        print(json.dumps(report.to_dict(), indent=2))
    else:
        print(report.format_text())
    return 0 if report.passed else 1


def handle_plugin(args: argparse.Namespace) -> int:
    from minuscorrect.orchestrator import inspect_plugin_status, install_plugin
    if args.action == "status":
        status = inspect_plugin_status()
        print("MinusCorrect Plugin Status:")
        print(f"  Installed: {status['plugin_installed']}")
        print(f"  Location:  {status['plugin_directory']}")
        print(f"  Imported in agy: {status['agy_imported']}")
        print("  Skills Registered:")
        for name, present in status["skills_registered"].items():
            mark = "[OK]" if present else "[MISSING]"
            print(f"    {mark:<10} {name}")
        return 0
    elif args.action == "install":
        ok, msg = install_plugin()
        print(msg)
        return 0 if ok else 1
    return 1


def handle_doctor(args: argparse.Namespace) -> int:
    from minuscorrect.doctor import format_diagnostic_json, format_diagnostic_text, run_diagnostics
    checks = run_diagnostics()
    if getattr(args, "json", False):
        print(format_diagnostic_json(checks))
    else:
        print(format_diagnostic_text(checks))

    has_failure = any(c.status == "FAIL" for c in checks)
    return 1 if has_failure else 0


def handle_mcp(args: argparse.Namespace) -> int:
    from minuscorrect.mcp import run_mcp_server
    run_mcp_server()
    return 0


def mcp_main() -> int:
    """Entry point for mc-mcp console script."""
    from minuscorrect.mcp import run_mcp_server
    run_mcp_server()
    return 0


def supervisor_main() -> int:
    """Entry point for mc-supervisor console script."""
    from minuscorrect.supervisor import AgentSupervisor
    # Forward to handle_run with appropriate arguments
    parser = argparse.ArgumentParser(prog="mc-supervisor", description="MinusCorrect Supervisor Runner")
    parser.add_argument("--target", help="Target source file")
    parser.add_argument("--session-id", default="default")
    parser.add_argument("--max-iterations", type=int, default=4)
    parser.add_argument("-t", "--timeout", type=float, default=float(os.environ.get("MINUSCORRECT_TIMEOUT", "300.0")), help="Execution timeout in seconds (default: 300.0 or MINUSCORRECT_TIMEOUT)")
    parser.add_argument("--isolate-env", action="store_true", help="Sanitize ambient credentials/tokens from test subprocess environment")
    parser.add_argument("--reset", action="store_true")
    parser.add_argument("test_cmd", nargs=argparse.REMAINDER)

    args = parser.parse_args()
    return handle_run(args)


if __name__ == "__main__":
    sys.exit(main())
