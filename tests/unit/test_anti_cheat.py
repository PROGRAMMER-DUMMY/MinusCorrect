"""
Unit tests for MinusCorrect Anti-Cheating Guardian (minuscorrect/anti_cheat.py).
"""

from pathlib import Path
from minuscorrect.anti_cheat import (
    audit_against_benchmark_cheats,
    detect_hardcoded_overfitting,
    detect_tautological_assertions,
)


def test_detect_hardcoded_overfitting_positive() -> None:
    source_code = """
def calculate_discount(tier, amount):
    if tier == "BENCHMARK_SPECIAL_USER":
        return 999.0
    return amount * 0.1
"""
    test_code = """
def test_calculate_discount():
    assert calculate_discount("BENCHMARK_SPECIAL_USER", 100) == 999.0
"""
    violations = detect_hardcoded_overfitting(source_code, test_code)
    assert len(violations) >= 1
    assert violations[0].violation_type == "HARDCODED_TEST_BYPASS"
    assert "BENCHMARK_SPECIAL_USER" in violations[0].description


def test_detect_hardcoded_overfitting_negative() -> None:
    source_code = """
def calculate_discount(tier, amount):
    rate = 0.2 if tier == "gold" else 0.1
    return amount * rate
"""
    test_code = """
def test_calculate_discount():
    assert calculate_discount("standard", 100) == 10.0
"""
    violations = detect_hardcoded_overfitting(source_code, test_code)
    assert len(violations) == 0


def test_detect_tautological_assertions() -> None:
    test_code = """
def test_mock():
    assert True
    x = 10
    assert x == x
"""
    violations = detect_tautological_assertions(test_code)
    assert len(violations) == 2
    assert all(v.violation_type == "TAUTOLOGICAL_ASSERTION" for v in violations)


def test_detect_tautological_assertions_clean() -> None:
    test_code = """
def test_valid():
    x = compute(5)
    assert x == 25
"""
    violations = detect_tautological_assertions(test_code)
    assert len(violations) == 0


def test_full_anti_cheat_audit(tmp_path: Path) -> None:
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    (src_dir / "math.py").write_text("def add(a, b): return a + b\n", encoding="utf-8")

    test_dir = tmp_path / "tests"
    test_dir.mkdir()
    (test_dir / "test_math.py").write_text("def test_add(): assert add(1, 2) == 3\n", encoding="utf-8")

    report = audit_against_benchmark_cheats(src_dir, test_dir)
    assert report.passed
    assert len(report.violations) == 0
