"""
Unit and Integration Tests for MinusCorrect CLI Interface
Verifies command line parsing, execution dispatch, session status, reset,
and end-to-end circuit breaker integration.
"""

from __future__ import annotations

import sys
from pathlib import Path
import pytest

from minuscorrect.cli import build_parser, handle_run, handle_status, handle_reset, handle_verify, main
from minuscorrect.supervisor import SessionState


def test_cli_parser_commands():
    parser = build_parser()
    
    # Subcommand: run
    args_run = parser.parse_args(["run", "--session-id", "test-s1", "--timeout", "30.0", "--", "pytest", "tests/"])
    assert args_run.command == "run"
    assert args_run.session_id == "test-s1"
    assert args_run.timeout == 30.0
    assert args_run.test_cmd == ["--", "pytest", "tests/"]

    # Subcommand: status
    args_status = parser.parse_args(["status", "--session-id", "test-s1"])
    assert args_status.command == "status"
    assert args_status.session_id == "test-s1"

    # Subcommand: reset
    args_reset = parser.parse_args(["reset", "--session-id", "test-s1"])
    assert args_reset.command == "reset"
    assert args_reset.session_id == "test-s1"

    # Subcommand: verify
    args_verify = parser.parse_args(["verify", "--fix", "--strict"])
    assert args_verify.command == "verify"
    assert args_verify.fix is True
    assert args_verify.strict is True

    # Subcommand: doctor
    args_doctor = parser.parse_args(["doctor", "--json"])
    assert args_doctor.command == "doctor"
    assert args_doctor.json is True


def test_cli_run_missing_command(capsys):
    parser = build_parser()
    args = parser.parse_args(["run"])
    code = handle_run(args)
    assert code == 1
    err = capsys.readouterr().err
    assert "No test command specified" in err


def test_cli_run_success_cycle(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    session_id = "test_cli_success"

    parser = build_parser()
    args = parser.parse_args([
        "run",
        "--session-id", session_id,
        "--", "python", "-c", "import sys; sys.exit(0)"
    ])

    code = handle_run(args)
    assert code == 0

    state = SessionState.load(session_id)
    assert state.status == "CONVERGED"
    assert state.current_iteration == 1


def test_cli_status_and_reset(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    session_id = "test_cli_status"

    # Run once with a failure
    parser = build_parser()
    args_run = parser.parse_args([
        "run",
        "--session-id", session_id,
        "--", "python", "-c", "import sys; sys.exit(1)"
    ])
    code = handle_run(args_run)
    assert code == 1

    # Check status
    args_status = parser.parse_args(["status", "--session-id", session_id])
    status_code = handle_status(args_status)
    assert status_code == 0
    out = capsys.readouterr().out
    assert session_id in out
    assert "Current Iteration: 1 / 4" in out

    # Reset
    args_reset = parser.parse_args(["reset", "--session-id", session_id])
    reset_code = handle_reset(args_reset)
    assert reset_code == 0

    state = SessionState.load(session_id)
    assert state.current_iteration == 0
    assert state.status == "ACTIVE"


def test_cli_e2e_full_circuit_breaker(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    session_id = "test_cli_e2e_circuit"

    parser = build_parser()

    # Step 1: Failing test
    code1 = handle_run(parser.parse_args([
        "run", "--session-id", session_id,
        "--", "python", "-c", "import sys; sys.stderr.write('fault'); sys.exit(1)"
    ]))
    assert code1 == 1

    # Step 2: Consecutive failure
    code2 = handle_run(parser.parse_args([
        "run", "--session-id", session_id,
        "--", "python", "-c", "import sys; sys.stderr.write('fault'); sys.exit(1)"
    ]))
    assert code2 == 1

    # Step 3: Repeated error triggers scaffolding required
    code3 = handle_run(parser.parse_args([
        "run", "--session-id", session_id,
        "--", "python", "-c", "import sys; sys.stderr.write('fault'); sys.exit(1)"
    ]))
    assert code3 == 1
    state3 = SessionState.load(session_id)
    assert state3.status == "SCAFFOLDING_REQUIRED"

    # Step 4: Circuit breaker trips on iteration 4
    code4 = handle_run(parser.parse_args([
        "run", "--session-id", session_id,
        "--", "python", "-c", "import sys; sys.stderr.write('fault'); sys.exit(1)"
    ]))
    assert code4 == 2  # Hard abort exit code is 2
    state4 = SessionState.load(session_id)
    assert state4.status == "HARD_ABORT"

    # Confirm diagnostic report was written
    report = tmp_path / "DIAGNOSTIC-REPORT.md"
    assert report.exists()
    report_text = report.read_text(encoding="utf-8")
    assert "HARD_ABORT" in report_text
    assert "fault" in report_text


def test_cli_main_entry_point(monkeypatch):
    # Test main dispatch with no arguments displays help and returns 0
    exit_code = main([])
    assert exit_code == 0


def test_cli_parser_timeout_and_isolate_env(monkeypatch):
    monkeypatch.delenv("MINUSCORRECT_TIMEOUT", raising=False)
    parser = build_parser()

    # Default timeout and isolate_env
    args_default = parser.parse_args(["run", "--", "pytest"])
    assert args_default.timeout == 300.0
    assert args_default.isolate_env is False

    # Explicit --timeout
    args_long = parser.parse_args(["run", "--timeout", "45.0", "--", "pytest"])
    assert args_long.timeout == 45.0

    # Explicit -t flag
    args_short = parser.parse_args(["run", "-t", "60.0", "--", "pytest"])
    assert args_short.timeout == 60.0

    # Explicit --isolate-env
    args_iso = parser.parse_args(["run", "--isolate-env", "--", "pytest"])
    assert args_iso.isolate_env is True

    # MINUSCORRECT_TIMEOUT environment variable changes default
    monkeypatch.setenv("MINUSCORRECT_TIMEOUT", "150.0")
    parser_env = build_parser()
    args_env = parser_env.parse_args(["run", "--", "pytest"])
    assert args_env.timeout == 150.0


def test_cli_handle_run_forwards_timeout_and_isolate_env(monkeypatch):
    from unittest.mock import patch, MagicMock

    parser = build_parser()
    args = parser.parse_args(["run", "-t", "75.0", "--isolate-env", "--", "pytest"])

    mock_sup = MagicMock()
    mock_sup.state.reset = MagicMock()
    mock_sup.run_step.return_value = {"status": "SUCCESS"}

    with patch("minuscorrect.cli.AgentSupervisor", return_value=mock_sup) as mock_class:
        code = handle_run(args)
        assert code == 0
        mock_class.assert_called_once()
        _, kwargs = mock_class.call_args
        assert kwargs["timeout"] == 75.0
        assert kwargs["isolate_env"] is True

