"""
Unit tests for MinusCorrect Autonomous Supervisor and Volatile-Token Sanitizer.
"""

from __future__ import annotations

import json
from pathlib import Path
from minuscorrect.supervisor import (
    SessionState,
    sanitize_trace,
    compute_error_hash,
    AgentSupervisor
)


def test_sanitize_trace_memory_addresses():
    trace_a = "AssertionError: object failed at 0x7f9a1b2c4d5e"
    trace_b = "AssertionError: object failed at 0x104b2a"
    assert sanitize_trace(trace_a) == "AssertionError: object failed at <HEX_ADDR>"
    assert sanitize_trace(trace_b) == "AssertionError: object failed at <HEX_ADDR>"


def test_sanitize_trace_durations():
    trace_a = "Test completed in 0.04s with 12 failures"
    trace_b = "Test completed in 150ms with 12 failures"
    assert sanitize_trace(trace_a) == "Test completed in <DURATION> with 12 failures"
    assert sanitize_trace(trace_b) == "Test completed in <DURATION> with 12 failures"


def test_sanitize_trace_timestamps():
    trace_a = "[2026-09-14T10:15:30.123Z] Fatal error in worker"
    trace_b = "[2026-09-15 04:22:11+00:00] Fatal error in worker"
    assert sanitize_trace(trace_a) == "[<TIMESTAMP>] Fatal error in worker"
    assert sanitize_trace(trace_b) == "[<TIMESTAMP>] Fatal error in worker"


def test_compute_error_hash_deterministic():
    # Two traces differing only in dynamic memory pointers and execution timings
    trace_run_1 = "AssertionError: <Worker at 0x7f01> failed in 0.04s\nTimestamp: 2026-09-14T12:00:00Z"
    trace_run_2 = "AssertionError: <Worker at 0x10b9> failed in 0.12s\nTimestamp: 2026-09-15T09:30:00Z"

    hash_1 = compute_error_hash(stderr=trace_run_1, stdout="")
    hash_2 = compute_error_hash(stderr=trace_run_2, stdout="")

    assert hash_1 == hash_2
    assert len(hash_1) == 16


def test_session_state_persistence(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    session = SessionState(session_id="test_sess_01", max_iterations=4)
    session.current_iteration = 2
    session.history.append({"iteration": 1, "hash": "abc12345"})
    session.save()

    loaded = SessionState.load("test_sess_01")
    assert loaded.session_id == "test_sess_01"
    assert loaded.current_iteration == 2
    assert len(loaded.history) == 1
    assert loaded.history[0]["hash"] == "abc12345"

    session.reset()
    assert session.current_iteration == 0
    assert len(session.history) == 0


def test_supervisor_epistemic_scaffolding_injection(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    supervisor = AgentSupervisor(session_id="test_loop", max_iterations=4)

    # Simulate 2 identical failures
    step_1 = supervisor.run_step(["python", "-c", "import sys; sys.stderr.write('fatal bug'); sys.exit(1)"])
    assert step_1["status"] == "RETRY_ALGORITHMIC"
    assert supervisor.state.current_iteration == 1

    step_2 = supervisor.run_step(["python", "-c", "import sys; sys.stderr.write('fatal bug'); sys.exit(1)"])
    assert step_2["status"] == "RETRY_ALGORITHMIC"
    assert supervisor.state.current_iteration == 2

    # Iteration 3: Consecutive identical error hash must trigger scaffolding injection
    step_3 = supervisor.run_step(["python", "-c", "import sys; sys.stderr.write('fatal bug'); sys.exit(1)"])
    assert step_3["status"] == "INJECT_SCAFFOLDING"
    assert supervisor.state.current_iteration == 3
    assert "Inject targeted" in step_3["action"]


def test_supervisor_hard_abort_and_diagnostic_report(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    supervisor = AgentSupervisor(session_id="test_abort", max_iterations=4)

    # Run through to iteration 4
    for i in range(3):
        supervisor.run_step(["python", "-c", "import sys; sys.stderr.write('persistent defect'); sys.exit(1)"])

    step_4 = supervisor.run_step(["python", "-c", "import sys; sys.stderr.write('persistent defect'); sys.exit(1)"])
    assert step_4["status"] == "HARD_ABORT"
    assert supervisor.state.current_iteration == 4

    report_path = Path("DIAGNOSTIC-REPORT.md")
    assert report_path.exists()
    content = report_path.read_text(encoding="utf-8")
    assert "HARD_ABORT" in content
    assert "persistent defect" in content
    assert "<untrusted_execution_trace>" in content


def test_supervisor_execution_timeout(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    # Supervisor with a 0.2s timeout
    supervisor = AgentSupervisor(session_id="test_timeout", max_iterations=4, timeout=0.2)

    # Command that sleeps for 2 seconds (must trigger timeout)
    res = supervisor.run_step(["python", "-c", "import time; time.sleep(2)"])

    assert supervisor.state.current_iteration == 1
    assert len(supervisor.state.history) == 1
    record = supervisor.state.history[0]
    assert record["exit_code"] == 124  # Timeout code
    assert record["hash"] is not None


def test_supervisor_safe_rollback_preserves_env(tmp_path, monkeypatch):
    import subprocess
    monkeypatch.chdir(tmp_path)

    # Initialize a temporary git repo
    subprocess.run(["git", "init"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run(["git", "config", "user.email", "test@test.com"], check=True)
    subprocess.run(["git", "config", "user.name", "Tester"], check=True)

    tracked = tmp_path / "main.py"
    tracked.write_text("initial_code = True", encoding="utf-8")
    subprocess.run(["git", "add", "main.py"], check=True)
    subprocess.run(["git", "commit", "-m", "initial commit"], check=True, stdout=subprocess.DEVNULL)

    # Agent creates untracked scratch file and modifies tracked file
    tracked.write_text("corrupted_code = True", encoding="utf-8")
    scratch = tmp_path / "agent_scratch.tmp"
    scratch.write_text("temporary scratch", encoding="utf-8")

    # Developer has an untracked .env file and .env.local
    env_file = tmp_path / ".env"
    env_file.write_text("SECRET_KEY=12345", encoding="utf-8")
    env_local = tmp_path / ".env.local"
    env_local.write_text("LOCAL_CONFIG=true", encoding="utf-8")

    supervisor = AgentSupervisor(session_id="test_rollback", max_iterations=4)
    supervisor.atomic_rollback()

    # Verify tracked file was restored
    assert tracked.read_text(encoding="utf-8") == "initial_code = True"
    # Verify agent scratch was cleaned
    assert not scratch.exists()
    # Verify developer .env and .env.local were preserved
    assert env_file.exists()
    assert env_file.read_text(encoding="utf-8") == "SECRET_KEY=12345"
    assert env_local.exists()
    assert env_local.read_text(encoding="utf-8") == "LOCAL_CONFIG=true"


def test_supervisor_configurable_timeout_default_and_env(monkeypatch):
    monkeypatch.delenv("MINUSCORRECT_TIMEOUT", raising=False)
    sup_default = AgentSupervisor(session_id="test_timeout_default")
    assert sup_default.timeout == 300.0

    monkeypatch.setenv("MINUSCORRECT_TIMEOUT", "45.5")
    sup_env = AgentSupervisor(session_id="test_timeout_env")
    assert sup_env.timeout == 45.5

    # Explicit timeout parameter overrides environment variable
    sup_override = AgentSupervisor(session_id="test_timeout_override", timeout=12.0)
    assert sup_override.timeout == 12.0


def test_sanitize_environment_filters_sensitive_credentials():
    from minuscorrect.supervisor import sanitize_environment

    env = {
        "PATH": "/usr/bin;C:\\Windows",
        "SYSTEMROOT": "C:\\Windows",
        "SAFE_KEY": "public-val",
        "GITHUB_TOKEN": "ghp_secret_token",
        "GH_TOKEN": "gh_secret_token",
        "AWS_ACCESS_KEY_ID": "AKIAIOSFODNN7EXAMPLE",
        "AWS_SECRET_ACCESS_KEY": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
        "AZURE_CLIENT_SECRET": "azure_secret",
        "AZURE_SUBSCRIPTION_ID": "azure_sub",
        "OPENAI_API_KEY": "sk-openai-12345",
        "ANTHROPIC_API_KEY": "sk-ant-12345",
        "GEMINI_API_KEY": "AIzaSyFakeGeminiKey",
        "DATABASE_URL": "postgresql://user:pass@localhost:5432/db",
        "APP_SECRET": "super_secret_hash",
        "DB_PASSWORD": "db_password_123",
        "SSL_PRIVATE_KEY": "-----BEGIN PRIVATE KEY-----",
    }

    sanitized = sanitize_environment(env)

    # Safe keys are retained
    assert sanitized["PATH"] == "/usr/bin;C:\\Windows"
    assert sanitized["SYSTEMROOT"] == "C:\\Windows"
    assert sanitized["SAFE_KEY"] == "public-val"

    # All sensitive keys are filtered out
    assert "GITHUB_TOKEN" not in sanitized
    assert "GH_TOKEN" not in sanitized
    assert "AWS_ACCESS_KEY_ID" not in sanitized
    assert "AWS_SECRET_ACCESS_KEY" not in sanitized
    assert "AZURE_CLIENT_SECRET" not in sanitized
    assert "AZURE_SUBSCRIPTION_ID" not in sanitized
    assert "OPENAI_API_KEY" not in sanitized
    assert "ANTHROPIC_API_KEY" not in sanitized
    assert "GEMINI_API_KEY" not in sanitized
    assert "DATABASE_URL" not in sanitized
    assert "APP_SECRET" not in sanitized
    assert "DB_PASSWORD" not in sanitized
    assert "SSL_PRIVATE_KEY" not in sanitized


def test_sanitize_environment_passthrough_whitelist():
    from minuscorrect.supervisor import sanitize_environment

    env = {
        "GITHUB_TOKEN": "ghp_secret_token",
        "DATABASE_URL": "postgresql://user:pass@localhost:5432/db",
        "OPENAI_API_KEY": "sk-openai-12345",
        "AWS_REGION": "us-east-1",
        "MINUSCORRECT_PASSTHROUGH_ENV": "GITHUB_TOKEN, DATABASE_URL",
    }

    sanitized = sanitize_environment(env)

    # Whitelisted keys are preserved
    assert sanitized["GITHUB_TOKEN"] == "ghp_secret_token"
    assert sanitized["DATABASE_URL"] == "postgresql://user:pass@localhost:5432/db"

    # Non-whitelisted sensitive keys remain stripped
    assert "OPENAI_API_KEY" not in sanitized
    assert "AWS_REGION" not in sanitized


def test_supervisor_run_step_isolate_env(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("GITHUB_TOKEN", "should_not_leak")
    monkeypatch.setenv("OPENAI_API_KEY", "should_not_leak_either")

    # With isolate_env=True: subprocess cannot see sensitive variables
    sup_isolated = AgentSupervisor(session_id="test_iso_true", isolate_env=True)
    check_code = (
        "import os, sys; "
        "has_leak = 'GITHUB_TOKEN' in os.environ or 'OPENAI_API_KEY' in os.environ; "
        "sys.exit(1 if has_leak else 0)"
    )
    res_iso = sup_isolated.run_step(["python", "-c", check_code])
    assert res_iso["status"] == "SUCCESS"
    assert sup_isolated.state.history[-1]["exit_code"] == 0

    # With isolate_env=False: ambient environment is preserved
    sup_ambient = AgentSupervisor(session_id="test_iso_false", isolate_env=False)
    check_ambient_code = (
        "import os, sys; "
        "present = 'GITHUB_TOKEN' in os.environ and 'OPENAI_API_KEY' in os.environ; "
        "sys.exit(0 if present else 1)"
    )
    res_amb = sup_ambient.run_step(["python", "-c", check_ambient_code])
    assert res_amb["status"] == "SUCCESS"
    assert sup_ambient.state.history[-1]["exit_code"] == 0




