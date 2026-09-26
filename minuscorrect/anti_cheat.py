"""
MinusCorrect Anti-Benchmark-Maxxing & Anti-Cheating Guardian.
Detects LLM overfitting to test fixtures, hardcoded branch bypasses,
tautological assertions, test tampering, and naked exception swallowing.
"""

from __future__ import annotations

import ast
from dataclasses import asdict, dataclass, field
import json
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Set


@dataclass
class CheatViolation:
    """Represents a detected benchmark cheat, test bypass, or overfitting flaw."""
    violation_type: str  # HARDCODED_TEST_BYPASS, TAUTOLOGICAL_ASSERTION, EXCEPTION_SWALLOWING, TEST_TAMPERING
    file_path: str
    line_number: int
    severity: str  # Blocks launch, Warning
    description: str
    snippet: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class AntiCheatReport:
    """Report summarizing anti-cheating and benchmark robustness inspection."""
    violations: List[CheatViolation] = field(default_factory=list)
    files_inspected: int = 0
    passed: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "passed": self.passed,
            "violations_count": len(self.violations),
            "files_inspected": self.files_inspected,
            "violations": [v.to_dict() for v in self.violations],
        }

    def format_text(self) -> str:
        lines = [
            "=" * 72,
            "     MinusCorrect Anti-Benchmark-Maxxing & Robustness Audit",
            "=" * 72,
            "",
            f"Files Inspected: {self.files_inspected} | Violations Found: {len(self.violations)}",
            f"Overall Status:  {'[PASSED] Code is robust & general' if self.passed else '[FAILED] Cheating / Overfitting Detected'}",
            "",
        ]
        if not self.violations:
            lines.append("No benchmark cheats, hardcoded test branches, or tautologies detected.")
        else:
            lines.append("Detected Violations:")
            for v in self.violations:
                badge = f"[{v.severity.upper()}]"
                lines.append(f"  {badge:<16} {v.violation_type} at {v.file_path}:{v.line_number}")
                lines.append(f"  Details:         {v.description}")
                if v.snippet:
                    lines.append(f"  Snippet:         {v.snippet.strip()}")
                lines.append("")
        lines.append("=" * 72)
        return "\n".join(lines)


def _extract_literals_from_ast(tree: ast.AST) -> Set[Any]:
    """Extract constant values from AST nodes."""
    literals = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant):
            if isinstance(node.value, (str, int, float)) and node.value not in ("", 0, 1, True, False, None):
                literals.add(node.value)
    return literals


def detect_hardcoded_overfitting(
    source_code: str,
    test_code: str,
    source_path: str = "source.py",
) -> List[CheatViolation]:
    """
    Detects when source code implements literal equality checks against test fixtures
    (e.g. if x == 'test_special_token': return 42) rather than general algorithmic logic.
    # verifies: tests/unit/test_anti_cheat.py
    """
    violations: List[CheatViolation] = []
    try:
        source_ast = ast.parse(source_code)
        test_ast = ast.parse(test_code)
    except SyntaxError:
        return violations

    # Extract assertion target constants from test code
    test_constants: Set[Any] = set()
    for node in ast.walk(test_ast):
        if isinstance(node, ast.Assert):
            test_constants.update(_extract_literals_from_ast(node))

    if not test_constants:
        return violations

    # Inspect source code functions for If statements comparing parameter variables directly to test constants
    for func in ast.walk(source_ast):
        if not isinstance(func, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        # Skip CLI dispatch handlers where status-to-exit-code mapping is expected
        if func.name.startswith("handle_") or func.name in ("main", "build_parser", "to_dict"):
            continue
        param_names = {arg.arg for arg in func.args.args}
        for node in ast.walk(func):
            if isinstance(node, ast.If) and isinstance(node.test, ast.Compare):
                left = node.test.left
                is_param_check = isinstance(left, ast.Name) and left.id in param_names
                if is_param_check:
                    for comparator in node.test.comparators:
                        if isinstance(comparator, ast.Constant) and comparator.value in test_constants:
                            if len(node.body) == 1 and isinstance(node.body[0], ast.Return):
                                ret_val = node.body[0].value
                                if isinstance(ret_val, ast.Constant):
                                    violations.append(CheatViolation(
                                        violation_type="HARDCODED_TEST_BYPASS",
                                        file_path=source_path,
                                        line_number=node.lineno,
                                        severity="Blocks launch",
                                        description=(
                                            f"Function '{func.name}' contains hardcoded test bypass: branches on parameter '{left.id}' "
                                            f"matching test fixture constant '{comparator.value}' and returns literal '{ret_val.value}'. "
                                            f"This indicates benchmark overfitting rather than general algorithmic implementation."
                                        ),
                                        snippet=ast.unparse(node) if hasattr(ast, "unparse") else "",
                                    ))
    return violations


def detect_tautological_assertions(test_code: str, test_path: str = "test.py") -> List[CheatViolation]:
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


def detect_assert_free_tests(test_code: str, test_path: str = "test.py") -> List[CheatViolation]:
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


def detect_test_exception_swallowing(test_code: str, test_path: str = "test.py") -> List[CheatViolation]:
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


def detect_vacuous_assertions(test_code: str, test_path: str = "test.py") -> List[CheatViolation]:
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


def audit_against_benchmark_cheats(
    source_dir: Path,
    test_dir: Path,
) -> AntiCheatReport:
    """
    Performs full repository anti-cheating audit across source and test files.
    # verifies: tests/unit/test_anti_cheat.py
    """
    report = AntiCheatReport()
    source_files = list(source_dir.glob("**/*.py")) if source_dir.is_dir() else []
    test_files = list(test_dir.glob("**/*.py")) if test_dir.is_dir() else []

    report.files_inspected = len(source_files) + len(test_files)

    # 1. Tautological assertions, empty tests, exception swallowing, vacuous assertions in test files
    for tf in test_files:
        try:
            content = tf.read_text(encoding="utf-8", errors="ignore")
            report.violations.extend(detect_tautological_assertions(content, test_path=str(tf.name)))
            report.violations.extend(detect_assert_free_tests(content, test_path=str(tf.name)))
            report.violations.extend(detect_test_exception_swallowing(content, test_path=str(tf.name)))
            report.violations.extend(detect_vacuous_assertions(content, test_path=str(tf.name)))
        except OSError:
            pass

    # 2. Hardcoded test constant bypasses in source files
    combined_test_code = ""
    for tf in test_files:
        try:
            combined_test_code += tf.read_text(encoding="utf-8", errors="ignore") + "\n"
        except OSError:
            pass

    for sf in source_files:
        try:
            content = sf.read_text(encoding="utf-8", errors="ignore")
            bypasses = detect_hardcoded_overfitting(content, combined_test_code, source_path=str(sf.name))
            report.violations.extend(bypasses)
        except OSError:
            pass

    report.passed = not any(v.severity == "Blocks launch" for v in report.violations)
    return report

