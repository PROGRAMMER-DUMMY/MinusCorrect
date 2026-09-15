"""
Unit Tests for Local Golden Immutability and Anti-Swallowing Verification
"""

import os
from unittest.mock import patch
import pytest

from minuscorrect.verifier import (
    check_golden_tests,
    check_anti_swallowing,
    verify_all
)
from minuscorrect.supervisor import AgentSupervisor


def test_check_golden_tests_clean():
    with patch("minuscorrect.verifier.run_git_command", return_value=""):
        ok, msg = check_golden_tests()
        assert ok is True
        assert "clean" in msg.lower()


def test_check_golden_tests_tampering_blocked(monkeypatch):
    monkeypatch.delenv("ALLOW_GOLDEN_EDIT", raising=False)
    fake_porcelain = " M tests/golden/test_contract.py\n?? tests/golden/test_new.py"
    with patch("minuscorrect.verifier.run_git_command", return_value=fake_porcelain):
        ok, msg = check_golden_tests()
        assert ok is False
        assert "Immutable golden tests modified in tests/golden/" in msg
        assert "ALLOW_GOLDEN_EDIT=1" in msg


def test_check_golden_tests_allow_override(monkeypatch):
    monkeypatch.setenv("ALLOW_GOLDEN_EDIT", "1")
    fake_porcelain = " M tests/golden/test_contract.py"
    with patch("minuscorrect.verifier.run_git_command", return_value=fake_porcelain):
        ok, msg = check_golden_tests()
        assert ok is True
        assert "ALLOW_GOLDEN_EDIT=1" in msg


def test_supervisor_blocks_golden_tampering_locally(monkeypatch, tmp_path):
    monkeypatch.delenv("ALLOW_GOLDEN_EDIT", raising=False)
    with patch("minuscorrect.verifier.check_golden_tests", return_value=(False, "Tampering detected")):
        supervisor = AgentSupervisor(session_id="test_tamper", target_file=tmp_path / "dummy.py")
        result = supervisor.run_step(test_cmd=["pytest"])
        assert result["status"] == "TAMPERING_DETECTED"
        assert supervisor.state.status == "TAMPERING_DETECTED"


def test_anti_swallowing_detects_naked_pass():
    with patch("minuscorrect.verifier.get_staged_code_files", return_value=["src/calc.py"]):
        diff = """--- a/src/calc.py
+++ b/src/calc.py
@@ -10,3 +10,5 @@
+    try:
+        do_work()
+    except Exception:
+        pass
"""
        with patch("minuscorrect.verifier.run_git_command", return_value=diff):
            ok, msg = check_anti_swallowing()
            assert ok is False
            assert "Fix-by-swallowing detected" in msg


def test_anti_swallowing_detects_inline_pass():
    with patch("minuscorrect.verifier.get_staged_code_files", return_value=["src/calc.py"]):
        diff = """--- a/src/calc.py
+++ b/src/calc.py
@@ -10,2 +10,3 @@
+    except ValueError: pass
"""
        with patch("minuscorrect.verifier.run_git_command", return_value=diff):
            ok, msg = check_anti_swallowing()
            assert ok is False
            assert "Fix-by-swallowing detected" in msg


def test_anti_swallowing_allows_annotated_rationale():
    with patch("minuscorrect.verifier.get_staged_code_files", return_value=["src/calc.py"]):
        diff = """--- a/src/calc.py
+++ b/src/calc.py
@@ -10,4 +10,6 @@
+    try:
+        do_work()
+    except TimeoutError:
+        # Rationale: Best-effort retry handled by upstream gateway
+        return None
"""
        with patch("minuscorrect.verifier.run_git_command", return_value=diff):
            ok, msg = check_anti_swallowing()
            assert ok is True
            assert "No silent exception swallowing" in msg
