"""
Unit tests for MinusCorrect Model Context Protocol (MCP) Server
"""

import io
import json
import pytest

from minuscorrect.mcp import MCP_TOOLS, handle_tool_call, run_mcp_server


def test_mcp_tools_list_schema():
    assert len(MCP_TOOLS) >= 5
    tool_names = [t["name"] for t in MCP_TOOLS]
    assert "minuscorrect_run" in tool_names
    assert "minuscorrect_verify" in tool_names
    assert "minuscorrect_validate_patch" in tool_names
    assert "minuscorrect_ingest_incident" in tool_names
    assert "minuscorrect_create_draft_pr" in tool_names
    assert "minuscorrect_status" in tool_names


def test_handle_tool_call_validate_patch_clean():
    diff = """diff --git a/app.py b/app.py
--- a/app.py
+++ b/app.py
@@ -1 +1 @@
-def foo(): pass
+def foo(): return 1
"""
    result = handle_tool_call("minuscorrect_validate_patch", {"diff_content": diff})
    assert not result["isError"]
    assert "valid" in result["content"][0]["text"].lower()


def test_handle_tool_call_validate_patch_blocked_conftest():
    diff = """diff --git a/conftest.py b/conftest.py
--- a/conftest.py
+++ b/conftest.py
@@ -1 +1 @@
+# exploit
"""
    result = handle_tool_call("minuscorrect_validate_patch", {"diff_content": diff})
    assert result["isError"]
    assert "conftest.py" in result["content"][0]["text"]


def test_handle_tool_call_status(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = handle_tool_call("minuscorrect_status", {"session_id": "test_mcp_session"})
    assert not result["isError"]
    data = json.loads(result["content"][0]["text"])
    assert data["session_id"] == "test_mcp_session"
    assert data["current_iteration"] == 0


def test_handle_tool_call_unknown():
    result = handle_tool_call("nonexistent_tool", {})
    assert result["isError"]
    assert "Unknown tool" in result["content"][0]["text"]


def test_run_mcp_server_initialize_and_tools_list():
    requests = [
        json.dumps({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {"protocolVersion": "2024-11-05"}
        }),
        json.dumps({
            "jsonrpc": "2.0",
            "method": "notifications/initialized"
        }),
        json.dumps({
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list",
            "params": {}
        }),
        json.dumps({
            "jsonrpc": "2.0",
            "id": 3,
            "method": "ping",
            "params": {}
        }),
    ]

    input_stream = io.StringIO("\n".join(requests) + "\n")
    output_stream = io.StringIO()

    run_mcp_server(stdin=input_stream, stdout=output_stream)

    lines = [line.strip() for line in output_stream.getvalue().splitlines() if line.strip()]
    assert len(lines) == 3  # initialize, tools/list, ping (notification does not generate response)

    init_resp = json.loads(lines[0])
    assert init_resp["id"] == 1
    assert init_resp["result"]["serverInfo"]["name"] == "minuscorrect"

    tools_resp = json.loads(lines[1])
    assert tools_resp["id"] == 2
    assert len(tools_resp["result"]["tools"]) >= 5

    ping_resp = json.loads(lines[2])
    assert ping_resp["id"] == 3
    assert ping_resp["result"] == {}


def test_run_mcp_server_tools_call():
    diff = """diff --git a/main.py b/main.py
--- a/main.py
+++ b/main.py
@@ -1 +1 @@
-pass
+return 42
"""
    req = json.dumps({
        "jsonrpc": "2.0",
        "id": 42,
        "method": "tools/call",
        "params": {
            "name": "minuscorrect_validate_patch",
            "arguments": {"diff_content": diff}
        }
    })

    input_stream = io.StringIO(req + "\n")
    output_stream = io.StringIO()

    run_mcp_server(stdin=input_stream, stdout=output_stream)

    line = output_stream.getvalue().strip()
    resp = json.loads(line)
    assert resp["id"] == 42
    assert not resp["result"]["isError"]
