"""
Unit tests for MinusCorrect Pre-Flight Doctor Diagnostic Command.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from minuscorrect.doctor import (
    DiagnosticCheck,
    check_configuration_environment,
    check_git_binary,
    check_git_index_lock,
    check_git_repository,
    check_golden_tests,
    check_pytest_installed,
    check_python_runtime,
    check_session_storage,
    check_worktree_capability,
    format_diagnostic_json,
    format_diagnostic_text,
    run_diagnostics,
)
from minuscorrect.cli import build_parser, handle_doctor, main


def test_check_python_runtime_success():
    check = check_python_runtime()
    assert check.category == "Runtime"
    assert check.status == "PASS"
    assert "compatible" in check.message


def test_check_python_runtime_failure(monkeypatch):
    from collections import namedtuple
    VersionInfo = namedtuple("VersionInfo", ["major", "minor", "micro"])
    monkeypatch.setattr(sys, "version_info", VersionInfo(3, 8, 10))
    check = check_python_runtime()
    assert check.status == "FAIL"
    assert "Python 3.9+ is required" in check.message


def test_check_pytest_installed():
    check = check_pytest_installed()
    assert check.category == "Runtime"
    assert check.status == "PASS"
    assert "pytest" in check.message


def test_check_pytest_installed_missing(monkeypatch):
    import builtins
    orig_import = builtins.__import__

    def mock_import(name, *args, **kwargs):
        if name == "pytest":
            raise ImportError("No module named 'pytest'")
        return orig_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", mock_import)
    check = check_pytest_installed()
    assert check.status == "FAIL"
    assert "pytest is not installed" in check.message


def test_check_git_binary_success():
    check = check_git_binary()
    assert check.category == "Git"
    assert check.status == "PASS"
    assert "git version" in check.message


def test_check_git_binary_missing(monkeypatch):
    monkeypatch.setattr("shutil.which", lambda _: None)
    check = check_git_binary()
    assert check.status == "FAIL"
    assert "not found on system PATH" in check.message


def test_check_git_repository_clean():
    check = check_git_repository()
    assert check.status == "PASS"
    assert "Repository root detected" in check.message


def test_check_git_repository_failure():
    with patch("subprocess.run") as mock_run:
        mock_res = MagicMock()
        mock_res.returncode = 128
        mock_res.stderr = "fatal: not a git repository"
        mock_run.return_value = mock_res
        check = check_git_repository()
        assert check.status == "FAIL"
        assert "Not inside a valid git repository" in check.message


def test_check_git_index_lock_clean(tmp_path):
    git_dir = tmp_path / ".git"
    git_dir.mkdir()
    check = check_git_index_lock(cwd=tmp_path)
    assert check.status == "PASS"
    assert "No git index lockfile detected" in check.message


def test_check_git_index_lock_detected(tmp_path):
    git_dir = tmp_path / ".git"
    git_dir.mkdir()
    lock_file = git_dir / "index.lock"
    lock_file.write_text("locked", encoding="utf-8")
    check = check_git_index_lock(cwd=tmp_path)
    assert check.status == "FAIL"
    assert "Stale git index lockfile detected" in check.message


def test_check_worktree_capability():
    check = check_worktree_capability()
    assert check.status == "PASS"
    assert "active worktree" in check.message


def test_check_golden_tests_clean():
    check = check_golden_tests()
    assert check.status == "PASS"
    assert "tests/golden/ is clean" in check.message


def test_check_golden_tests_missing(tmp_path):
    check = check_golden_tests(cwd=tmp_path)
    assert check.status == "WARN"
    assert "does not exist" in check.message


def test_check_golden_tests_modified_blocks_without_override(monkeypatch):
    with patch("subprocess.run") as mock_run:
        mock_res = MagicMock()
        mock_res.returncode = 0
        mock_res.stdout = " M tests/golden/test_sample.py\n"
        mock_run.return_value = mock_res

        monkeypatch.delenv("ALLOW_GOLDEN_EDIT", raising=False)
        check = check_golden_tests()
        assert check.status == "FAIL"
        assert "ALLOW_GOLDEN_EDIT=1" in check.message


def test_check_golden_tests_modified_warns_with_override(monkeypatch):
    with patch("subprocess.run") as mock_run:
        mock_res = MagicMock()
        mock_res.returncode = 0
        mock_res.stdout = " M tests/golden/test_sample.py\n"
        mock_run.return_value = mock_res

        monkeypatch.setenv("ALLOW_GOLDEN_EDIT", "1")
        check = check_golden_tests()
        assert check.status == "WARN"
        assert "ALLOW_GOLDEN_EDIT=1 active" in check.message


def test_check_session_storage(tmp_path):
    check = check_session_storage(cwd=tmp_path)
    assert check.status == "PASS"
    assert "Session storage writable" in check.message


def test_check_configuration_environment(monkeypatch):
    # Test with custom environment
    monkeypatch.setenv("MINUSCORRECT_TIMEOUT", "45.0")
    monkeypatch.setenv("MINUSCORRECT_WEBHOOK_URL", "https://hooks.slack.com/services/T00/B00/X00")
    monkeypatch.setenv("MINUSCORRECT_PASSTHROUGH_ENV", "TOKEN_A, TOKEN_B")

    checks = check_configuration_environment()
    timeout_chk = next(c for c in checks if c.name == "Execution Timeout")
    alert_chk = next(c for c in checks if c.name == "Operational Alerts")
    env_chk = next(c for c in checks if c.name == "Env Whitelist Passthrough")

    assert timeout_chk.status == "PASS"
    assert "45.0s" in timeout_chk.message
    assert alert_chk.status == "PASS"
    assert "Slack Webhook" in alert_chk.message
    assert env_chk.status == "PASS"
    assert "2 environment variables" in env_chk.message


def test_run_diagnostics_and_formatting():
    checks = run_diagnostics()
    assert len(checks) >= 8

    text = format_diagnostic_text(checks)
    assert "MinusCorrect Pre-Flight Environment Doctor" in text
    assert "Summary:" in text

    json_str = format_diagnostic_json(checks)
    data = json.loads(json_str)
    assert "healthy" in data
    assert "checks" in data
    assert len(data["checks"]) == len(checks)


def test_cli_doctor_dispatch(capsys):
    parser = build_parser()
    args = parser.parse_args(["doctor"])
    exit_code = handle_doctor(args)
    captured = capsys.readouterr()
    assert exit_code == 0
    assert "MinusCorrect Pre-Flight Environment Doctor" in captured.out


def test_cli_doctor_json_dispatch(capsys):
    parser = build_parser()
    args = parser.parse_args(["doctor", "--json"])
    exit_code = handle_doctor(args)
    captured = capsys.readouterr()
    assert exit_code == 0
    data = json.loads(captured.out)
    assert data["healthy"] is True
    assert data["summary"]["total"] >= 8


def test_cli_doctor_failure_exit_code():
    with patch("minuscorrect.doctor.run_diagnostics") as mock_diag:
        mock_diag.return_value = [
            DiagnosticCheck(
                category="Runtime",
                name="Python Version",
                status="FAIL",
                message="Critical Python version failure"
            )
        ]
        parser = build_parser()
        args = parser.parse_args(["doctor"])
        exit_code = handle_doctor(args)
        assert exit_code == 1
