"""
Unit tests for MinusCorrect 10-Domain Pre-Launch Security & Operational Audit.
"""

from pathlib import Path
import json
import pytest
from minuscorrect.audit import run_pre_launch_audit
from minuscorrect.cli import main


def test_clean_directory_audit(tmp_path: Path) -> None:
    # Scaffold minimal valid files
    spec_dir = tmp_path / "spec"
    spec_dir.mkdir()
    (spec_dir / "TRD.md").write_text("# TRD\nRTO: 15m\nRPO: 1m", encoding="utf-8")
    sql_file = spec_dir / "schema.sql"
    sql_file.write_text(
        "CREATE TABLE users (id UUID PRIMARY KEY);\n"
        "ALTER TABLE users ENABLE ROW LEVEL SECURITY;\n",
        encoding="utf-8"
    )

    report = run_pre_launch_audit(target_dir=tmp_path)
    assert len(report.checks) == 10
    assert not report.blocks_launch
    assert report.fail_count == 0


def test_dom01_secret_leakage_detection(tmp_path: Path) -> None:
    env_file = tmp_path / ".env.production"
    env_file.write_text("NEXT_PUBLIC_SUPABASE_SERVICE_ROLE_KEY=eyJh...", encoding="utf-8")

    report = run_pre_launch_audit(target_dir=tmp_path)
    dom1 = next(c for c in report.checks if c.check_id == "DOM-01")
    assert dom1.status == "FAIL"
    assert ".env.production" in dom1.details
    assert report.blocks_launch


def test_dom02_missing_rls_detection(tmp_path: Path) -> None:
    sql_file = tmp_path / "bad_schema.sql"
    sql_file.write_text("CREATE TABLE customers (id INT, email TEXT);\n", encoding="utf-8")

    report = run_pre_launch_audit(target_dir=tmp_path)
    dom2 = next(c for c in report.checks if c.check_id == "DOM-02")
    assert dom2.status == "FAIL"
    assert "customers" in dom2.details
    assert report.blocks_launch


def test_dom07_unindexed_foreign_key_detection(tmp_path: Path) -> None:
    sql_file = tmp_path / "unindexed.sql"
    sql_file.write_text(
        "CREATE TABLE orders (\n"
        "    id UUID PRIMARY KEY,\n"
        "    user_id UUID REFERENCES users(id)\n"
        ");\n"
        "ALTER TABLE orders ENABLE ROW LEVEL SECURITY;\n",
        encoding="utf-8"
    )

    report = run_pre_launch_audit(target_dir=tmp_path)
    dom7 = next(c for c in report.checks if c.check_id == "DOM-07")
    assert dom7.status == "WARN"
    assert "user_id" in dom7.details


def test_dom08_staging_robots_txt_detection(tmp_path: Path) -> None:
    robots = tmp_path / "public" / "robots.txt"
    robots.parent.mkdir()
    robots.write_text("User-agent: *\nDisallow: /\n", encoding="utf-8")

    report = run_pre_launch_audit(target_dir=tmp_path)
    dom8 = next(c for c in report.checks if c.check_id == "DOM-08")
    assert dom8.status == "FAIL"
    assert "Disallow: /" in dom8.details


def test_dom09_plaintext_logging_detection(tmp_path: Path) -> None:
    code_file = tmp_path / "handler.ts"
    code_file.write_text("console.error('Request failed:', req.body);", encoding="utf-8")

    report = run_pre_launch_audit(target_dir=tmp_path)
    dom9 = next(c for c in report.checks if c.check_id == "DOM-09")
    assert dom9.status == "FAIL"
    assert "handler.ts" in dom9.details


def test_cli_pre_launch_audit(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    code = main(["audit", "--pre-launch", "--target-dir", str(tmp_path)])
    assert code in (0, 1)
    captured = capsys.readouterr()
    assert "MinusCorrect 10-Domain Pre-Launch Security & Operational Audit" in captured.out


def test_cli_pre_launch_audit_json(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    code = main(["audit", "--pre-launch", "--target-dir", str(tmp_path), "--json"])
    assert code in (0, 1)
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert "checks" in data
    assert len(data["checks"]) == 10
