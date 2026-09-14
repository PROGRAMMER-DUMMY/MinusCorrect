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
