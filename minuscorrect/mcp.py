"""
MinusCorrect Model Context Protocol (MCP) Server
Exposes MinusCorrect execution containment, verification gates, and blast-radius
validators as standard MCP tools over stdio (JSON-RPC 2.0).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from minuscorrect.patch import validate_patch
from minuscorrect.pr import create_draft_pr_artifact
from minuscorrect.supervisor import AgentSupervisor, SessionState
from minuscorrect.verifier import verify_all


MCP_TOOLS = [
    {
        "name": "minuscorrect_run",
        "description": "Execute a test command under the 4-iteration circuit breaker supervisor with atomic rollback, timeout protection, and volatile error hashing.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "test_cmd": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Test command to execute, e.g. ['pytest', 'tests/staging/']",
                },
                "session_id": {"type": "string", "default": "default"},
                "timeout": {"type": "number", "default": 120.0},
                "target": {"type": "string", "description": "Target source file being repaired"},
            },
            "required": ["test_cmd"],
        },
    },
    {
        "name": "minuscorrect_verify",
        "description": "Run systemic integrity pre-commit checks (golden contract protection, anti-swallowing AST rules, debug tag purge).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "auto_fix": {
                    "type": "boolean",
                    "default": False,
                    "description": "Automatically strip leftover [DEBUG] logging statements",
                },
                "strict": {
                    "type": "boolean",
                    "default": False,
                    "description": "Fail on unverified docstring claims without receipts",
                },
            },
        },
    },
    {
        "name": "minuscorrect_validate_patch",
        "description": "Validate a proposed unified diff against zero-trust write boundaries (blocks conftest.py, pyproject.toml, and path traversal).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "diff_content": {
                    "type": "string",
                    "description": "Unified diff patch string to validate",
                },
                "allowed_targets": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional list of whitelisted file paths permitted to change",
                },
            },
            "required": ["diff_content"],
        },
    },
    {
        "name": "minuscorrect_ingest_incident",
        "description": "Defensively ingest crash telemetry (Sentry/Datadog/traceback), defang PII and prompt injections, and synthesize a staged reproduction contract.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "payload": {"type": "string", "description": "Raw crash JSON or traceback"},
                "incident_id": {"type": "string", "description": "Explicit incident ID (e.g. INC-1042)"},
                "output_dir": {"type": "string", "default": "tests/staging"},
            },
            "required": ["payload"],
        },
    },
    {
        "name": "minuscorrect_create_draft_pr",
        "description": "Generate a decoupled Draft PR proposal artifact (DRAFT-PR-<id>.md) with blast-radius stats and test receipts.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "session_id": {"type": "string", "default": "default"},
                "summary": {"type": "string", "default": "Automated defect repair via MinusCorrect supervisor"},
                "commit_and_branch": {"type": "boolean", "default": False},
            },
        },
    },
    {
        "name": "minuscorrect_status",
        "description": "Inspect active supervisor session state, iteration count, and error hash history.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "session_id": {"type": "string", "default": "default"},
            },
        },
    },
]


def handle_tool_call(name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """
    Executes an MCP tool call and returns a structured result.
    # Rationale: Standardized dispatch decouples AI clients from Python runtime internals.
    """
    try:
        if name == "minuscorrect_run":
            test_cmd = arguments.get("test_cmd", [])
            session_id = arguments.get("session_id", "default")
            timeout_val = float(arguments.get("timeout", 120.0))
            target_str = arguments.get("target")
            target_path = Path(target_str) if target_str else None

            supervisor = AgentSupervisor(
                session_id=session_id,
                target_file=target_path,
                timeout=timeout_val,
            )
            result = supervisor.run_step(test_cmd=test_cmd)
            return {"content": [{"type": "text", "text": json.dumps(result, indent=2)}], "isError": result.get("status") in ("HARD_ABORT", "TAMPERING_DETECTED")}

        elif name == "minuscorrect_verify":
            auto_fix = bool(arguments.get("auto_fix", False))
            strict = bool(arguments.get("strict", False))
            ok = verify_all(auto_fix=auto_fix, strict_docstrings=strict)
            return {
                "content": [{"type": "text", "text": f"Systemic Integrity Verification: {'PASSED' if ok else 'FAILED'}"}],
                "isError": not ok,
            }

        elif name == "minuscorrect_validate_patch":
            diff_content = arguments.get("diff_content", "")
            allowed = arguments.get("allowed_targets")
            ok, targets, msg = validate_patch(diff_content, allowed_targets=allowed)
            return {
                "content": [{"type": "text", "text": msg}],
                "isError": not ok,
            }

        elif name == "minuscorrect_ingest_incident":
            from minuscorrect.incident import (
                generate_rca_report,
                generate_staged_test,
                parse_incident_payload,
            )
            payload_str = arguments.get("payload", "")
            inc_id = arguments.get("incident_id")
            out_dir = Path(arguments.get("output_dir", "tests/staging"))

            sanitized_data, inferred_id = parse_incident_payload(payload_str, explicit_id=inc_id)
            test_path = generate_staged_test(sanitized_data, inferred_id, output_dir=out_dir)
            rca_path = generate_rca_report(sanitized_data, inferred_id)
            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"Staged reproduction test created: {test_path}\nRCA report generated: {rca_path}",
                    }
                ],
                "isError": False,
            }

        elif name == "minuscorrect_create_draft_pr":
            session_id = arguments.get("session_id", "default")
            summary = arguments.get("summary", "Automated defect repair via MinusCorrect supervisor")
            commit_branch = bool(arguments.get("commit_and_branch", False))

            pr_file = create_draft_pr_artifact(
                session_id=session_id,
                summary=summary,
                commit_and_branch=commit_branch,
            )
            return {
                "content": [{"type": "text", "text": f"Draft PR proposal artifact created: {pr_file}"}],
                "isError": False,
            }

        elif name == "minuscorrect_status":
            session_id = arguments.get("session_id", "default")
            state = SessionState.load(session_id)
            status_data = {
                "session_id": state.session_id,
                "status": state.status,
                "current_iteration": state.current_iteration,
                "max_iterations": state.max_iterations,
                "history_length": len(state.history),
                "recent_history": state.history[-3:],
            }
            return {
                "content": [{"type": "text", "text": json.dumps(status_data, indent=2)}],
                "isError": False,
            }

        else:
            return {
                "content": [{"type": "text", "text": f"Unknown tool: {name}"}],
                "isError": True,
            }

    except Exception as exc:
        return {
            "content": [{"type": "text", "text": f"Tool execution failed: {exc}"}],
            "isError": True,
        }


def run_mcp_server(stdin=sys.stdin, stdout=sys.stdout) -> None:
    """
    Runs the stdio JSON-RPC 2.0 loop for Model Context Protocol (MCP).
    """
    for line in stdin:
        line = line.strip()
        if not line:
            continue

        try:
            req = json.loads(line)
        except json.JSONDecodeError:
            continue

        msg_id = req.get("id")
        method = req.get("method")
        params = req.get("params", {})

        if method == "initialize":
            res = {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": "minuscorrect", "version": "1.0.0"},
                },
            }
        elif method == "notifications/initialized":
            # Acknowledgement notification; no response required
            continue
        elif method == "ping":
            res = {"jsonrpc": "2.0", "id": msg_id, "result": {}}
        elif method == "tools/list":
            res = {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {"tools": MCP_TOOLS},
            }
        elif method == "tools/call":
            tool_name = params.get("name", "")
            tool_args = params.get("arguments", {})
            call_res = handle_tool_call(tool_name, tool_args)
            res = {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": call_res,
            }
        else:
            res = {
                "jsonrpc": "2.0",
                "id": msg_id,
                "error": {"code": -32601, "message": f"Method not found: {method}"},
            }

        stdout.write(json.dumps(res) + "\n")
        stdout.flush()


if __name__ == "__main__":
    run_mcp_server()
