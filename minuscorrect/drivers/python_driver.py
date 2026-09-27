"""
MinusCorrect Native Python AST Driver.
Inspects Python source code and test files using the standard library ast module.
# verifies: tests/unit/test_anti_cheat.py
"""

from __future__ import annotations

import ast
from typing import List, Optional, Set

from minuscorrect.drivers.base import AstDriver, CheatViolation


class NativePythonDriver(AstDriver):
    """
    Python AST driver inspecting Python source code and test suites using the standard library ast module.
    # verifies: tests/unit/test_anti_cheat.py
    """
    name: str = "python"
    supported_extensions: Set[str] = {".py"}

    def inspect(
        self,
        source_code: str,
        file_path: str,
        is_test: bool = False,
        banned_literals: Optional[Set[str]] = None,
    ) -> List[CheatViolation]:
        """
        Inspect Python code for anti-patterns and benchmark cheating.
        # verifies: tests/unit/test_anti_cheat.py
        """
        violations: List[CheatViolation] = []
        if is_test:
            violations.extend(self.detect_tautological_assertions(source_code, test_path=file_path))
            violations.extend(self.detect_assert_free_tests(source_code, test_path=file_path))
            violations.extend(self.detect_test_exception_swallowing(source_code, test_path=file_path))
            violations.extend(self.detect_vacuous_assertions(source_code, test_path=file_path))
        else:
            if banned_literals:
                violations.extend(
                    self.detect_banned_benchmark_fixtures(source_code, banned_literals, source_path=file_path)
                )
        return violations

    def detect_tautological_assertions(
        self,
        test_code: str,
        test_path: str = "test.py",
    ) -> List[CheatViolation]:
        """
        Detects tautological assertions in test suites (e.g. assert True, assert x == x).
        # verifies: tests/unit/test_anti_cheat.py
        """
        violations: List[CheatViolation] = []
        try:
            tree = ast.parse(test_code)
        except SyntaxError:
            return violations

        for node in ast.walk(tree):
            if isinstance(node, ast.Assert):
                # Case 1: assert True / assert 1
                if isinstance(node.test, ast.Constant) and bool(node.test.value) is True:
                    violations.append(CheatViolation(
                        violation_type="TAUTOLOGICAL_ASSERTION",
                        file_path=test_path,
                        line_number=node.lineno,
                        severity="Blocks launch",
                        description="Tautological assertion 'assert True' detected; does not verify program behavior.",
                        snippet="assert True",
                    ))
                # Case 2: assert x == x
                elif isinstance(node.test, ast.Compare):
                    left_src = ast.unparse(node.test.left) if hasattr(ast, "unparse") else ""
                    for op, right in zip(node.test.ops, node.test.comparators):
                        if isinstance(op, ast.Eq):
                            right_src = ast.unparse(right) if hasattr(ast, "unparse") else ""
                            if left_src and left_src == right_src:
                                violations.append(CheatViolation(
                                    violation_type="TAUTOLOGICAL_ASSERTION",
                                    file_path=test_path,
                                    line_number=node.lineno,
                                    severity="Blocks launch",
                                    description=f"Self-comparison assertion detected: 'assert {left_src} == {right_src}'.",
                                    snippet=f"assert {left_src} == {right_src}",
                                ))
        return violations

    def detect_assert_free_tests(
        self,
        test_code: str,
        test_path: str = "test.py",
    ) -> List[CheatViolation]:
        """
        Detects test functions that contain zero assertions or pytest checks.
        # verifies: tests/unit/test_anti_cheat.py
        """
        violations: List[CheatViolation] = []
        try:
            tree = ast.parse(test_code)
        except SyntaxError:
            return violations

        for func in ast.walk(tree):
            if isinstance(func, (ast.FunctionDef, ast.AsyncFunctionDef)) and func.name.startswith("test_"):
                has_assert = False
                for node in ast.walk(func):
                    if isinstance(node, ast.Assert):
                        has_assert = True
                        break
                    elif isinstance(node, ast.Call):
                        call_name = ""
                        if isinstance(node.func, ast.Name):
                            call_name = node.func.id
                        elif isinstance(node.func, ast.Attribute):
                            call_name = node.func.attr
                        if any(kw in call_name.lower() for kw in ("raises", "assert", "fail", "warns", "deprecated")):
                            has_assert = True
                            break
                if not has_assert:
                    violations.append(CheatViolation(
                        violation_type="ASSERT_FREE_TEST",
                        file_path=test_path,
                        line_number=func.lineno,
                        severity="Blocks launch",
                        description=f"Test function '{func.name}' contains zero assert or verification statements; does not verify behavior.",
                        snippet=f"def {func.name}(...):",
                    ))
        return violations

    def detect_test_exception_swallowing(
        self,
        test_code: str,
        test_path: str = "test.py",
    ) -> List[CheatViolation]:
        """
        Detects test functions that catch exceptions and silently pass or return.
        # verifies: tests/unit/test_anti_cheat.py
        """
        violations: List[CheatViolation] = []
        try:
            tree = ast.parse(test_code)
        except SyntaxError:
            return violations

        for func in ast.walk(tree):
            if isinstance(func, (ast.FunctionDef, ast.AsyncFunctionDef)) and func.name.startswith("test_"):
                for node in ast.walk(func):
                    if isinstance(node, ast.Try):
                        for handler in node.handlers:
                            is_swallowed = False
                            for stmt in handler.body:
                                if isinstance(stmt, ast.Pass):
                                    is_swallowed = True
                                elif isinstance(stmt, ast.Return) and stmt.value is None:
                                    is_swallowed = True
                                elif isinstance(stmt, ast.Raise):
                                    is_swallowed = False
                                    break
                            if is_swallowed:
                                violations.append(CheatViolation(
                                    violation_type="TEST_EXCEPTION_SWALLOWING",
                                    file_path=test_path,
                                    line_number=handler.lineno,
                                    severity="Blocks launch",
                                    description=f"Test function '{func.name}' swallows exception with pass/return in except block, masking potential test failure.",
                                    snippet=ast.unparse(handler) if hasattr(ast, "unparse") else "except: pass",
                                ))
        return violations

    def detect_vacuous_assertions(
        self,
        test_code: str,
        test_path: str = "test.py",
    ) -> List[CheatViolation]:
        """
        Detects vacuous, mathematically unfalsifiable assertions (e.g. assert len(...) >= 0).
        # verifies: tests/unit/test_anti_cheat.py
        """
        violations: List[CheatViolation] = []
        try:
            tree = ast.parse(test_code)
        except SyntaxError:
            return violations

        for node in ast.walk(tree):
            if isinstance(node, ast.Assert):
                if isinstance(node.test, ast.Compare):
                    left = node.test.left
                    if isinstance(left, ast.Call) and isinstance(left.func, ast.Name) and left.func.id == "len":
                        for op, comp in zip(node.test.ops, node.test.comparators):
                            if isinstance(op, ast.GtE) and isinstance(comp, ast.Constant) and comp.value == 0:
                                violations.append(CheatViolation(
                                    violation_type="VACUOUS_ASSERTION",
                                    file_path=test_path,
                                    line_number=node.lineno,
                                    severity="Blocks launch",
                                    description="Vacuous assertion 'assert len(...) >= 0' detected; mathematically always true in Python.",
                                    snippet=ast.unparse(node) if hasattr(ast, "unparse") else "assert len(...) >= 0",
                                ))
                elif isinstance(node.test, ast.Call) and isinstance(node.test.func, ast.Name) and node.test.func.id == "isinstance":
                    if len(node.test.args) >= 2 and isinstance(node.test.args[1], ast.Name) and node.test.args[1].id == "object":
                        violations.append(CheatViolation(
                            violation_type="VACUOUS_ASSERTION",
                            file_path=test_path,
                            line_number=node.lineno,
                            severity="Blocks launch",
                            description="Vacuous assertion 'assert isinstance(..., object)' detected; all types inherit from object.",
                            snippet=ast.unparse(node) if hasattr(ast, "unparse") else "assert isinstance(..., object)",
                        ))
        return violations

    def detect_banned_benchmark_fixtures(
        self,
        source_code: str,
        banned_literals: Set[str],
        source_path: str = "source.py",
    ) -> List[CheatViolation]:
        """
        Detects when executable source code embeds banned benchmark fixture keys or
        hardcoded table lookups designed to pass benchmarks without general extraction logic.
        # verifies: tests/unit/test_anti_cheat.py
        """
        violations: List[CheatViolation] = []
        if not banned_literals:
            return violations

        try:
            tree = ast.parse(source_code)
        except SyntaxError:
            return violations

        # Identify and exclude docstring constants
        docstring_nodes = set()
        for parent in ast.walk(tree):
            if isinstance(parent, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                if parent.body and isinstance(parent.body[0], ast.Expr):
                    val = parent.body[0].value
                    if isinstance(val, ast.Constant) and isinstance(val.value, str):
                        docstring_nodes.add(val)

        for node in ast.walk(tree):
            if node in docstring_nodes:
                continue
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                for banned in banned_literals:
                    if banned.lower() in node.value.lower():
                        violations.append(CheatViolation(
                            violation_type="BANNED_BENCHMARK_FIXTURE_LEAK",
                            file_path=source_path,
                            line_number=node.lineno,
                            severity="Blocks launch",
                            description=(
                                f"Source code contains banned benchmark fixture key '{banned}'. "
                                f"Embedding hardcoded benchmark answer tables or test tokens is prohibited."
                            ),
                            snippet=ast.unparse(node) if hasattr(ast, "unparse") else node.value,
                        ))
                        break
        return violations


_DEFAULT_PYTHON_DRIVER = NativePythonDriver()


def detect_tautological_assertions(test_code: str, test_path: str = "test.py") -> List[CheatViolation]:
    """
    Detects tautological assertions in test suites (e.g. assert True, assert x == x).
    # verifies: tests/unit/test_anti_cheat.py
    """
    return _DEFAULT_PYTHON_DRIVER.detect_tautological_assertions(test_code, test_path=test_path)


def detect_assert_free_tests(test_code: str, test_path: str = "test.py") -> List[CheatViolation]:
    """
    Detects test functions that contain zero assertions or pytest checks.
    # verifies: tests/unit/test_anti_cheat.py
    """
    return _DEFAULT_PYTHON_DRIVER.detect_assert_free_tests(test_code, test_path=test_path)


def detect_test_exception_swallowing(test_code: str, test_path: str = "test.py") -> List[CheatViolation]:
    """
    Detects test functions that catch exceptions and silently pass or return.
    # verifies: tests/unit/test_anti_cheat.py
    """
    return _DEFAULT_PYTHON_DRIVER.detect_test_exception_swallowing(test_code, test_path=test_path)


def detect_vacuous_assertions(test_code: str, test_path: str = "test.py") -> List[CheatViolation]:
    """
    Detects vacuous, mathematically unfalsifiable assertions (e.g. assert len(...) >= 0).
    # verifies: tests/unit/test_anti_cheat.py
    """
    return _DEFAULT_PYTHON_DRIVER.detect_vacuous_assertions(test_code, test_path=test_path)


def detect_banned_benchmark_fixtures(
    source_code: str,
    banned_literals: Set[str],
    source_path: str = "source.py",
) -> List[CheatViolation]:
    """
    Detects when executable source code embeds banned benchmark fixture keys or
    hardcoded table lookups designed to pass benchmarks without general extraction logic.
    # verifies: tests/unit/test_anti_cheat.py
    """
    return _DEFAULT_PYTHON_DRIVER.detect_banned_benchmark_fixtures(
        source_code, banned_literals=banned_literals, source_path=source_path
    )
