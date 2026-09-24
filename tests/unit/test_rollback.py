"""
Unit tests for MinusCorrect Rollback Engine (minuscorrect/rollback.py).
Verifies working tree cleanliness checks, atomic revert execution,
post-rollback verification gates, and Second-Brain ticket lifecycle transitions.
"""

from pathlib import Path
import subprocess
import pytest

from minuscorrect.rollback import RollbackEngine, RollbackResult
from minuscorrect.store import MinusStore


def init_test_git_repo(repo_path: Path) -> None:
    """Helper to initialize a bare-bones git repo with user configuration."""
    subprocess.run(["git", "init"], cwd=str(repo_path), capture_output=True, check=True)
    subprocess.run(["git", "config", "user.name", "MinusTest"], cwd=str(repo_path), capture_output=True, check=True)
    subprocess.run(["git", "config", "user.email", "test@minuscorrect.org"], cwd=str(repo_path), capture_output=True, check=True)


def test_rollback_clean_tree_check(tmp_path: Path) -> None:
    init_test_git_repo(tmp_path)
    engine = RollbackEngine(root_dir=tmp_path)

    # Clean initial state
    assert engine.check_working_tree_clean(cwd=tmp_path) is True

    # Dirty with untracked file
    dirty_file = tmp_path / "scratch.txt"
    dirty_file.write_text("uncommitted work", encoding="utf-8")
    assert engine.check_working_tree_clean(cwd=tmp_path) is False

    # Clean after git add and commit
    subprocess.run(["git", "add", "scratch.txt"], cwd=str(tmp_path), capture_output=True, check=True)
    subprocess.run(["git", "commit", "-m", "add scratch"], cwd=str(tmp_path), capture_output=True, check=True)
    assert engine.check_working_tree_clean(cwd=tmp_path) is True


def test_rollback_aborts_on_dirty_tree(tmp_path: Path) -> None:
    init_test_git_repo(tmp_path)
    store = MinusStore(root_dir=tmp_path)
    engine = RollbackEngine(store=store, root_dir=tmp_path)

    # Initial commit
    f = tmp_path / "main.py"
    f.write_text("print('base')\n", encoding="utf-8")
    subprocess.run(["git", "add", "main.py"], cwd=str(tmp_path), capture_output=True, check=True)
    subprocess.run(["git", "commit", "-m", "base commit"], cwd=str(tmp_path), capture_output=True, check=True)

    t = store.create_ticket("Feature X", role="Distributed Systems Engineer")
    store.close_ticket(t.id, commit_sha="HEAD", test_command="echo ok", cwd=tmp_path)

    # Make working tree dirty
    dirty = tmp_path / "untracked.py"
    dirty.write_text("untracked", encoding="utf-8")

    result = engine.rollback_ticket(t.id, cwd=tmp_path, verify=False)
    assert result.success is False
    assert result.status == "ABORTED_DIRTY_TREE"
    assert "Working tree has uncommitted modifications" in result.message


def test_rollback_not_found(tmp_path: Path) -> None:
    init_test_git_repo(tmp_path)
    engine = RollbackEngine(root_dir=tmp_path)
    res = engine.rollback_ticket("T-999", cwd=tmp_path)
    assert res.success is False
    assert res.status == "NOT_FOUND"


def test_rollback_success_lifecycle(tmp_path: Path) -> None:
    init_test_git_repo(tmp_path)
    store = MinusStore(root_dir=tmp_path)
    engine = RollbackEngine(store=store, root_dir=tmp_path)

    # Commit 1
    f = tmp_path / "feature.py"
    f.write_text("VERSION = 1\n", encoding="utf-8")
    subprocess.run(["git", "add", "feature.py"], cwd=str(tmp_path), capture_output=True, check=True)
    subprocess.run(["git", "commit", "-m", "version 1"], cwd=str(tmp_path), capture_output=True, check=True)

    # Commit 2 (ticket work)
    f.write_text("VERSION = 2\n", encoding="utf-8")
    subprocess.run(["git", "add", "feature.py"], cwd=str(tmp_path), capture_output=True, check=True)
    subprocess.run(["git", "commit", "-m", "bump to version 2"], cwd=str(tmp_path), capture_output=True, check=True)

    ticket_commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(tmp_path), capture_output=True, text=True, check=True).stdout.strip()

    t = store.create_ticket("Bump Version", role="Distributed Systems Engineer", verification="python -c \"import sys; sys.exit(0)\"")
    closed = store.close_ticket(t.id, commit_sha=ticket_commit, test_command="echo ok", cwd=tmp_path)
    assert closed.status == "completed"

    # Now execute rollback
    result = engine.rollback_ticket(t.id, cwd=tmp_path, verify=True)
    assert result.success is True
    assert result.status == "ROLLED_BACK"
    assert result.revert_commit is not None

    # Check file content reverted
    assert f.read_text(encoding="utf-8") == "VERSION = 1\n"

    # Check ticket moved to rolled_back folder
    assert not (store.tickets_completed / f"{t.id}.md").exists()
    assert (store.tickets_rolled_back / f"{t.id}.md").exists()

    # Check index entry
    idx = store._read_index()
    assert idx["tickets"][t.id]["status"] == "rolled_back"
    assert idx["tickets"][t.id]["revert_commit"] == result.revert_commit


def test_rollback_with_reopen_flag(tmp_path: Path) -> None:
    init_test_git_repo(tmp_path)
    store = MinusStore(root_dir=tmp_path)
    engine = RollbackEngine(store=store, root_dir=tmp_path)

    # Commit 1
    f = tmp_path / "module.py"
    f.write_text("x = 10\n", encoding="utf-8")
    subprocess.run(["git", "add", "module.py"], cwd=str(tmp_path), capture_output=True, check=True)
    subprocess.run(["git", "commit", "-m", "init module"], cwd=str(tmp_path), capture_output=True, check=True)

    # Commit 2
    f.write_text("x = 20\n", encoding="utf-8")
    subprocess.run(["git", "add", "module.py"], cwd=str(tmp_path), capture_output=True, check=True)
    subprocess.run(["git", "commit", "-m", "modify module"], cwd=str(tmp_path), capture_output=True, check=True)

    t = store.create_ticket("Modify Module", role="Process Isolation SRE", verification="python -c \"import sys; sys.exit(0)\"")
    store.close_ticket(t.id, commit_sha="HEAD", test_command="echo ok", cwd=tmp_path)

    # Rollback with reopen=True
    result = engine.rollback_ticket(t.id, reopen=True, cwd=tmp_path, verify=True)
    assert result.success is True
    assert (store.tickets_open / f"{t.id}.md").exists()
    assert not (store.tickets_completed / f"{t.id}.md").exists()

    fetched = store.get_ticket(t.id)
    assert fetched is not None
    assert fetched.status == "open"


def test_rollback_verification_gate_reverts_on_failure(tmp_path: Path) -> None:
    init_test_git_repo(tmp_path)
    store = MinusStore(root_dir=tmp_path)
    engine = RollbackEngine(store=store, root_dir=tmp_path)

    # Commit 1
    f = tmp_path / "calc.py"
    f.write_text("val = 1\n", encoding="utf-8")
    subprocess.run(["git", "add", "calc.py"], cwd=str(tmp_path), capture_output=True, check=True)
    subprocess.run(["git", "commit", "-m", "c1"], cwd=str(tmp_path), capture_output=True, check=True)

    # Commit 2
    f.write_text("val = 2\n", encoding="utf-8")
    subprocess.run(["git", "add", "calc.py"], cwd=str(tmp_path), capture_output=True, check=True)
    subprocess.run(["git", "commit", "-m", "c2"], cwd=str(tmp_path), capture_output=True, check=True)

    # Ticket with verification command that intentionally fails
    t = store.create_ticket("Bad Ticket", role="TDD Lead", verification="python -c \"import sys; sys.exit(1)\"")
    store.close_ticket(t.id, commit_sha="HEAD", test_command="echo ok", cwd=tmp_path)

    # Attempt rollback without force
    result = engine.rollback_ticket(t.id, cwd=tmp_path, verify=True, force=False)
    assert result.success is False
    assert result.status == "VERIFICATION_FAILED"

    # Working tree should still have val = 2 because failed rollback was aborted
    assert f.read_text(encoding="utf-8") == "val = 2\n"
    # Ticket should still be completed (not rolled_back)
    assert (store.tickets_completed / f"{t.id}.md").exists()


def test_inspect_diff(tmp_path: Path) -> None:
    init_test_git_repo(tmp_path)
    store = MinusStore(root_dir=tmp_path)
    engine = RollbackEngine(store=store, root_dir=tmp_path)

    f = tmp_path / "hello.py"
    f.write_text("a = 1\n", encoding="utf-8")
    subprocess.run(["git", "add", "hello.py"], cwd=str(tmp_path), capture_output=True, check=True)
    subprocess.run(["git", "commit", "-m", "init hello"], cwd=str(tmp_path), capture_output=True, check=True)

    f.write_text("a = 2\n", encoding="utf-8")
    subprocess.run(["git", "add", "hello.py"], cwd=str(tmp_path), capture_output=True, check=True)
    subprocess.run(["git", "commit", "-m", "update hello"], cwd=str(tmp_path), capture_output=True, check=True)

    t = store.create_ticket("Hello Ticket", role="Distributed Systems Engineer")
    store.close_ticket(t.id, commit_sha="HEAD", test_command="echo ok", cwd=tmp_path)

    diff_content = engine.inspect_diff(t.id)
    assert diff_content is not None
    assert "+a = 2" in diff_content


def test_cli_diff_and_rollback_commands(tmp_path: Path, monkeypatch) -> None:
    from minuscorrect.cli import main as cli_main
    monkeypatch.chdir(tmp_path)

    init_test_git_repo(tmp_path)
    store = MinusStore(root_dir=tmp_path)

    f = tmp_path / "service.py"
    f.write_text("SERVICE_NAME = 'v1'\n", encoding="utf-8")
    subprocess.run(["git", "add", "service.py"], cwd=str(tmp_path), capture_output=True, check=True)
    subprocess.run(["git", "commit", "-m", "v1 commit"], cwd=str(tmp_path), capture_output=True, check=True)

    f.write_text("SERVICE_NAME = 'v2'\n", encoding="utf-8")
    subprocess.run(["git", "add", "service.py"], cwd=str(tmp_path), capture_output=True, check=True)
    subprocess.run(["git", "commit", "-m", "v2 commit"], cwd=str(tmp_path), capture_output=True, check=True)

    t = store.create_ticket("Service V2", role="Process Isolation SRE", verification="echo verified")
    store.close_ticket(t.id, commit_sha="HEAD", cwd=tmp_path)

    # Test top-level diff
    code = cli_main(["diff", t.id])
    assert code == 0

    # Test ticket diff subcommand
    code = cli_main(["ticket", "diff", t.id])
    assert code == 0

    # Test top-level rollback with JSON output
    code = cli_main(["rollback", t.id, "--no-verify", "--json"])
    assert code == 0

    # Verify service.py rolled back to v1
    assert f.read_text(encoding="utf-8") == "SERVICE_NAME = 'v1'\n"

    # Verify ticket state is rolled_back
    fetched = store.get_ticket(t.id)
    assert fetched.status == "rolled_back"

