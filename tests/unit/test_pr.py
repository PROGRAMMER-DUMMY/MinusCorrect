"""
Unit tests for Autonomous PR Decoupling Engine
"""

import subprocess
from pathlib import Path
import pytest

from minuscorrect.cli import main
from minuscorrect.pr import DraftPRMetadata, create_draft_pr_artifact, generate_draft_pr_markdown


@pytest.fixture
def temp_git_repo(tmp_path):
    repo = tmp_path / "pr_repo"
    repo.mkdir()
    subprocess.run(["git", "init"], cwd=str(repo), check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    subprocess.run(["git", "config", "user.name", "PR Tester"], cwd=str(repo), check=True)
    subprocess.run(["git", "config", "user.email", "pr@minuscorrect.org"], cwd=str(repo), check=True)

    app_file = repo / "app.py"
    app_file.write_text("def solve():\n    return 1\n", encoding="utf-8")
    subprocess.run(["git", "add", "app.py"], cwd=str(repo), check=True)
    subprocess.run(["git", "commit", "-m", "feat: initial app"], cwd=str(repo), check=True)

    return repo


def test_generate_draft_pr_markdown():
    metadata = DraftPRMetadata(
        session_id="session-pr-01",
        branch_name="minuscorrect/patch-session-pr-01",
        title="fix(minuscorrect): autonomous repair [session-pr-01]",
        summary="Fixed off-by-one boundary defect",
        modified_files=["app.py", "utils.py"],
        tests_passed=["tests/golden/test_boundary.py"],
        iteration_count=2,
        rca_reference="INCIDENT-RCA-1042.md",
        diff_stat="app.py | 2 +-\n1 file changed, 1 insertion(+), 1 deletion(-)",
    )
    md = generate_draft_pr_markdown(metadata)
    assert "# fix(minuscorrect): autonomous repair [session-pr-01]" in md
    assert "session-pr-01" in md
    assert "`app.py`" in md
    assert "`utils.py`" in md
    assert "INCIDENT-RCA-1042.md" in md
    assert "git checkout minuscorrect/patch-session-pr-01" in md


def test_create_draft_pr_artifact(temp_git_repo):
    # Modify a file to create a diff
    app_file = temp_git_repo / "app.py"
    app_file.write_text("def solve():\n    return 42\n", encoding="utf-8")

    out_md = temp_git_repo / "DRAFT-PR-test.md"
    result_path = create_draft_pr_artifact(
        repo_root=temp_git_repo,
        session_id="test_pr_session",
        summary="Updated solve function",
        output_file=out_md,
    )

    assert result_path.exists()
    content = result_path.read_text(encoding="utf-8")
    assert "test_pr_session" in content
    assert "`app.py`" in content


def test_cli_pr_command(temp_git_repo, monkeypatch):
    monkeypatch.chdir(temp_git_repo)
    app_file = temp_git_repo / "app.py"
    app_file.write_text("def solve():\n    return 100\n", encoding="utf-8")

    exit_code = main(["pr", "--session-id", "cli-session", "--summary", "CLI PR test"])
    assert exit_code == 0

    expected_file = temp_git_repo / "DRAFT-PR-cli-session.md"
    assert expected_file.exists()
    assert "cli-session" in expected_file.read_text(encoding="utf-8")
