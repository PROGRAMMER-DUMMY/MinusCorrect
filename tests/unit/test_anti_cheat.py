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


def test_detect_assert_free_tests() -> None:
    from minuscorrect.anti_cheat import detect_assert_free_tests

    test_code = """
def test_no_asserts():
    x = 10
    y = x + 20

def test_with_asserts():
    assert 1 == 1
"""
    violations = detect_assert_free_tests(test_code)
    assert len(violations) == 1
    assert violations[0].violation_type == "ASSERT_FREE_TEST"
    assert "test_no_asserts" in violations[0].description


def test_detect_test_exception_swallowing() -> None:
    from minuscorrect.anti_cheat import detect_test_exception_swallowing

    test_code = """
def test_swallow():
    try:
        dangerous_call()
    except Exception:
        pass

def test_reraise():
    try:
        dangerous_call()
    except Exception:
        raise
"""
    violations = detect_test_exception_swallowing(test_code)
    assert len(violations) == 1
    assert violations[0].violation_type == "TEST_EXCEPTION_SWALLOWING"
    assert "test_swallow" in violations[0].description


def test_detect_vacuous_assertions() -> None:
    from minuscorrect.anti_cheat import detect_vacuous_assertions

    test_code = """
def test_vacuous():
    items = [1, 2, 3]
    assert len(items) >= 0
    assert isinstance(items, object)

def test_valid():
    items = [1, 2, 3]
    assert len(items) == 3
"""
    violations = detect_vacuous_assertions(test_code)
    assert len(violations) == 2
    assert all(v.violation_type == "VACUOUS_ASSERTION" for v in violations)


def test_check_anti_cheat_verifier() -> None:
    from minuscorrect.verifier import check_anti_cheat

    ok, msg = check_anti_cheat(strict=True)
    assert ok
    assert "clean" in msg


def test_load_custom_checkers(tmp_path: Path) -> None:
    from minuscorrect.anti_cheat import audit_against_benchmark_cheats, load_custom_checkers

    checkers_dir = tmp_path / "checkers"
    checkers_dir.mkdir()

    # Create a custom checker that flags any test containing 'banned_helper'
    custom_checker_code = """
from minuscorrect.anti_cheat import CheatViolation

def check_banned_helper(content, path):
    violations = []
    if 'banned_helper' in content:
        violations.append(CheatViolation(
            violation_type='BANNED_HELPER',
            file_path=path,
            line_number=1,
            severity='Blocks launch',
            description='Use of banned_helper is prohibited in this repository.',
            snippet='banned_helper()',
        ))
    return violations
"""
    (checkers_dir / "check_helpers.py").write_text(custom_checker_code, encoding="utf-8")

    checkers = load_custom_checkers(checkers_dir)
    assert len(checkers) == 1

    src_dir = tmp_path / "src"
    src_dir.mkdir()
    test_dir = tmp_path / "tests"
    test_dir.mkdir()

    # Test file violating custom checker
    (test_dir / "test_custom.py").write_text("def test_x(): banned_helper(); assert 1 == 1\n", encoding="utf-8")

    report = audit_against_benchmark_cheats(src_dir, test_dir, checkers_dir=checkers_dir)
    assert not report.passed
    assert any(v.violation_type == "BANNED_HELPER" for v in report.violations)


def test_detect_banned_benchmark_fixtures_catches_user_pattern() -> None:
    from minuscorrect.anti_cheat import detect_banned_benchmark_fixtures

    source_code = '''
def parse_financial_report(doc_name: str):
    # Benchmark cheat: hardcoding answers for sec_10k_p3_cash_flows
    if doc_name == "sec_10k_p3_cash_flows":
        return [
            ("Cash generated by operating activities", 110543.0, 122151.0, 1),
            ("Payments for property, plant and equipment", -10959.0, -10708.0, 6),
            ("Cash used in investing activities", -3705.0, -22354.0, 4),
            ("Repurchases of common stock", -77550.0, -89402.0, 10),
            ("Payments for dividends and dividend equivalents", -15025.0, -14841.0, 10),
            ("Cash used in financing activities", -108488.0, -110749.0, 8),
            ("Increase (decrease) in cash and cash equivalents", -1650.0, -10952.0, 1),
        ]
    return []
'''
    banned = {"sec_10k_p3_cash_flows"}
    violations = detect_banned_benchmark_fixtures(source_code, banned, source_path="extractor.py")
    assert len(violations) >= 1
    assert violations[0].violation_type == "BANNED_BENCHMARK_FIXTURE_LEAK"
    assert "sec_10k_p3_cash_flows" in violations[0].description
    assert violations[0].severity == "Blocks launch"


def test_add_and_load_banned_anti_pattern(tmp_path: Path) -> None:
    from minuscorrect.anti_cheat import add_banned_anti_pattern, load_banned_anti_patterns

    cfg = tmp_path / "anti_patterns.json"
    assert load_banned_anti_patterns(cfg) == set()

    # Add first token
    added = add_banned_anti_pattern("sec_10k_p3_cash_flows", config_path=cfg)
    assert added is True
    assert "sec_10k_p3_cash_flows" in load_banned_anti_patterns(cfg)

    # Adding duplicate returns False
    added_dup = add_banned_anti_pattern("sec_10k_p3_cash_flows", config_path=cfg)
    assert added_dup is False

    # Add second token
    add_banned_anti_pattern("Consolidated Statement of Cash Flows", config_path=cfg)
    assert len(load_banned_anti_patterns(cfg)) == 2


def test_audit_against_benchmark_cheats_with_banned_fixture(tmp_path: Path) -> None:
    from minuscorrect.anti_cheat import add_banned_anti_pattern, audit_against_benchmark_cheats

    minus_dir = tmp_path / ".minus"
    minus_dir.mkdir(parents=True)
    cfg = minus_dir / "anti_patterns.json"
    add_banned_anti_pattern("sec_10k_p3_cash_flows", config_path=cfg)

    src_dir = tmp_path / "src"
    src_dir.mkdir()
    (src_dir / "parser.py").write_text(
        'TABLE_KEY = "sec_10k_p3_cash_flows"\n',
        encoding="utf-8",
    )

    test_dir = tmp_path / "tests"
    test_dir.mkdir()
    (test_dir / "test_parser.py").write_text(
        'def test_ok(): assert 1 == 1\n',
        encoding="utf-8",
    )

    # Custom anti-pattern path monkeypatched or passed via cwd
    import os
    orig_cwd = os.getcwd()
    try:
        os.chdir(str(tmp_path))
        report = audit_against_benchmark_cheats(src_dir, test_dir)
        assert not report.passed
        assert any(v.violation_type == "BANNED_BENCHMARK_FIXTURE_LEAK" for v in report.violations)
    finally:
        os.chdir(orig_cwd)



