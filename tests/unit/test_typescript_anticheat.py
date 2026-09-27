"""
Unit tests for TypeScriptDriver and TypeScript AST Anti-Cheat S-Expression Engine.
# verifies: tests/unit/test_typescript_anticheat.py
"""

from __future__ import annotations

import sys
from typing import Set
from unittest import mock

import pytest

import minuscorrect.drivers as drivers
from minuscorrect.drivers.base import (
    AstDriver,
    get_driver_for_file,
    get_registered_drivers,
    register_driver,
)
from minuscorrect.drivers.treesitter_driver import PolyglotDependencyMissing
from minuscorrect.drivers.typescript_driver import (
    TypeScriptDriver,
    detect_assert_free_tests,
    detect_banned_benchmark_fixtures,
    detect_tautological_assertions,
    detect_test_exception_swallowing,
)


def test_drivers_package_exports_typescript() -> None:
    """
    Test that TypeScriptDriver is exported in minuscorrect.drivers.
    # verifies: tests/unit/test_typescript_anticheat.py
    """
    assert hasattr(drivers, "TypeScriptDriver")
    assert "TypeScriptDriver" in drivers.__all__

    driver = drivers.TypeScriptDriver()
    assert isinstance(driver, AstDriver)
    assert driver.name == "typescript"
    assert driver.language_name == "typescript"
    assert driver.supported_extensions == {".ts", ".tsx", ".js", ".jsx"}


def test_get_driver_for_file_typescript() -> None:
    """
    Test get_driver_for_file resolves TypeScriptDriver for .ts, .tsx, .js, and .jsx when registered.
    # verifies: tests/unit/test_typescript_anticheat.py
    """
    driver = TypeScriptDriver()
    import minuscorrect.drivers.base as base_mod
    orig_drivers = dict(base_mod._DRIVERS)
    try:
        base_mod._DRIVERS.clear()
        register_driver(driver)
        for filename in ("handler.ts", "component.tsx", "script.js", "widget.jsx"):
            found = get_driver_for_file(filename)
            assert found is not None
            assert isinstance(found, TypeScriptDriver)
            assert found.name == "typescript"
    finally:
        base_mod._DRIVERS.clear()
        base_mod._DRIVERS.update(orig_drivers)


def test_tautological_assertions() -> None:
    """
    Test detect_tautological_assertions flags expect(res).toBe(res) and passes expect(res).toBe(10).
    # verifies: tests/unit/test_typescript_anticheat.py
    """
    driver = TypeScriptDriver()

    # Tautological case
    bad_code = """
    describe("calc", () => {
        it("computes result", () => {
            const res = calculate(5);
            expect(res).toBe(res);
        });
    });
    """
    violations = driver.detect_tautological_assertions(bad_code, test_path="test_calc.ts")
    assert len(violations) == 1
    assert violations[0].violation_type == "TAUTOLOGICAL_ASSERTION"
    assert violations[0].file_path == "test_calc.ts"
    assert "expect(res).toBe(res)" in violations[0].snippet
    assert violations[0].severity == "Blocks launch"

    # Valid case
    good_code = """
    describe("calc", () => {
        it("computes result", () => {
            const res = calculate(5);
            expect(res).toBe(10);
        });
    });
    """
    clean_violations = driver.detect_tautological_assertions(good_code, test_path="test_calc.ts")
    assert clean_violations == []


def test_tautological_assertions_varieties() -> None:
    """
    Test tautological assertions flags expect(x).toEqual(x), expect(true).toBe(true),
    assert.equal(x, x), assert.strictEqual(x, x), and assert(true).
    # verifies: tests/unit/test_typescript_anticheat.py
    """
    driver = TypeScriptDriver()
    test_code = """
    expect(x).toEqual(x);
    expect(true).toBe(true);
    assert.equal(x, x);
    assert.strictEqual(x, x);
    assert(true);
    assert.ok(true);
    """
    violations = driver.detect_tautological_assertions(test_code, test_path="sample.test.ts")
    assert len(violations) >= 5
    assert all(v.violation_type == "TAUTOLOGICAL_ASSERTION" for v in violations)


def test_empty_catch_swallowing() -> None:
    """
    Test detect_test_exception_swallowing flags try { run(); } catch (err) {}
    and passes catch (err) { throw err; }.
    # verifies: tests/unit/test_typescript_anticheat.py
    """
    driver = TypeScriptDriver()

    # Empty catch swallowing
    swallowed_code = """
    try {
        run();
    } catch (err) {}
    """
    violations = driver.detect_test_exception_swallowing(swallowed_code, test_path="run.test.ts")
    assert len(violations) == 1
    assert violations[0].violation_type == "TEST_EXCEPTION_SWALLOWING"
    assert "catch (err) {}" in violations[0].snippet
    assert violations[0].severity == "Blocks launch"

    # Non-swallowing catch with re-throw
    clean_code = """
    try {
        run();
    } catch (err) {
        throw err;
    }
    """
    clean_violations = driver.detect_test_exception_swallowing(clean_code, test_path="run.test.ts")
    assert clean_violations == []

    # Optional catch binding syntax try { run(); } catch {}
    opt_catch_code = """
    try {
        run();
    } catch {
        /* empty block */
    }
    """
    opt_violations = driver.detect_test_exception_swallowing(opt_catch_code, test_path="run.test.ts")
    assert len(opt_violations) == 1
    assert opt_violations[0].violation_type == "TEST_EXCEPTION_SWALLOWING"


def test_assert_free_tests() -> None:
    """
    Test detect_assert_free_tests flags it('should work', () => { const x = 1; })
    and passes it('valid', () => { expect(x).toBe(1); }).
    # verifies: tests/unit/test_typescript_anticheat.py
    """
    driver = TypeScriptDriver()

    # Assert-free test block
    bad_test = """
    it('should work', () => {
        const x = 1;
    });
    """
    violations = driver.detect_assert_free_tests(bad_test, test_path="app.spec.ts")
    assert len(violations) == 1
    assert violations[0].violation_type == "ASSERT_FREE_TEST"
    assert violations[0].file_path == "app.spec.ts"
    assert violations[0].severity == "Blocks launch"
    assert "should work" in violations[0].description

    # Test with valid expect assertion
    valid_test = """
    it('valid', () => {
        const x = 1;
        expect(x).toBe(1);
    });
    """
    clean_violations = driver.detect_assert_free_tests(valid_test, test_path="app.spec.ts")
    assert clean_violations == []

    # Test with assert or verify calls
    valid_assert_test = """
    test('valid assert', () => {
        assert.strictEqual(1, 1);
    });
    it('valid verify', () => {
        verify(mockService).execute();
    });
    """
    assert driver.detect_assert_free_tests(valid_assert_test, test_path="app.spec.ts") == []


def test_banned_fixtures() -> None:
    """
    Test detect_banned_benchmark_fixtures flags banned token leak in TS source file.
    # verifies: tests/unit/test_typescript_anticheat.py
    """
    driver = TypeScriptDriver()
    banned_tokens: Set[str] = {"sec_10k_p3_cash_flows", "BENCHMARK_ANSWER_TOKEN"}

    # Source code embedding banned token
    source_code = """
    export function extractFinancials(docType: string): any {
        if (docType === "sec_10k_p3_cash_flows") {
            return { revenue: 100000 };
        }
        return null;
    }
    """
    violations = driver.detect_banned_benchmark_fixtures(
        source_code, banned_tokens, source_path="extractor.ts"
    )
    assert len(violations) == 1
    assert violations[0].violation_type == "BANNED_BENCHMARK_FIXTURE_LEAK"
    assert violations[0].file_path == "extractor.ts"
    assert "sec_10k_p3_cash_flows" in violations[0].description
    assert violations[0].severity == "Blocks launch"

    # Source code with clean string literals
    clean_source = """
    export function extractFinancials(docType: string): any {
        return parseDocument(docType);
    }
    """
    assert driver.detect_banned_benchmark_fixtures(clean_source, banned_tokens, "extractor.ts") == []


def test_banned_fixtures_in_comments_ignored() -> None:
    """
    Test detect_banned_benchmark_fixtures ignores banned tokens inside comments.
    # verifies: tests/unit/test_typescript_anticheat.py
    """
    driver = TypeScriptDriver()
    banned_tokens = {"banned_fixture_123"}
    code_with_comment = """
    // Reference: banned_fixture_123 benchmark case
    /*
     * Note: banned_fixture_123 should be processed generically.
     */
    export const DEFAULT_TIMEOUT = 5000;
    """
    violations = driver.detect_banned_benchmark_fixtures(code_with_comment, banned_tokens, "util.ts")
    assert violations == []


def test_tsx_grammar_support() -> None:
    """
    Test TSX grammar parses JSX syntax without errors and detects violations.
    # verifies: tests/unit/test_typescript_anticheat.py
    """
    driver = TypeScriptDriver()
    banned_tokens = {"banned_secret_header"}

    tsx_code = """
    import React from "react";

    export const HeaderComponent: React.FC = () => {
        return (
            <header className="banned_secret_header">
                <h1>Report</h1>
            </header>
        );
    };
    """
    violations = driver.detect_banned_benchmark_fixtures(tsx_code, banned_tokens, "Header.tsx")
    assert len(violations) == 1
    assert violations[0].violation_type == "BANNED_BENCHMARK_FIXTURE_LEAK"
    assert violations[0].file_path == "Header.tsx"


def test_inspect_method_routing() -> None:
    """
    Test inspect method routes to test detectors when is_test=True and banned fixtures when is_test=False.
    # verifies: tests/unit/test_typescript_anticheat.py
    """
    driver = TypeScriptDriver()

    test_source = """
    it("empty test", () => {});
    """
    violations = driver.inspect(test_source, file_path="test.ts", is_test=True)
    assert len(violations) >= 1
    assert any(v.violation_type == "ASSERT_FREE_TEST" for v in violations)

    prod_source = """
    export const TOKEN = "banned_key";
    """
    banned_violations = driver.inspect(
        prod_source, file_path="app.ts", is_test=False, banned_literals={"banned_key"}
    )
    assert len(banned_violations) == 1
    assert banned_violations[0].violation_type == "BANNED_BENCHMARK_FIXTURE_LEAK"


def test_polyglot_missing_fallback() -> None:
    """
    Test clean PolyglotDependencyMissing error when grammar or tree-sitter is mocked missing.
    # verifies: tests/unit/test_typescript_anticheat.py
    """
    # 1. When tree-sitter core module is mocked away
    with mock.patch.dict(sys.modules, {"tree_sitter": None}):
        driver = TypeScriptDriver()
        assert driver.is_available() is False
        with pytest.raises(PolyglotDependencyMissing) as exc_info:
            driver.inspect("const x = 1;", "app.ts", is_test=False)
        assert exc_info.value.language == "typescript"
        assert "minuscorrect[polyglot]" in str(exc_info.value)

        with pytest.raises(PolyglotDependencyMissing):
            driver.get_parser()

    # 2. When tree_sitter_typescript grammar module is mocked away
    with mock.patch.dict(sys.modules, {"tree_sitter_typescript": None}):
        driver_no_grammar = TypeScriptDriver()
        assert driver_no_grammar.is_available() is False
        with pytest.raises(PolyglotDependencyMissing) as exc_info:
            driver_no_grammar.inspect("const x = 1;", "app.ts", is_test=False)
        assert exc_info.value.language == "typescript"

        with pytest.raises(PolyglotDependencyMissing):
            driver_no_grammar.get_parser()
