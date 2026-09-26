"""
Custom Anti-Cheat Checker: Benchmark Table Overfitting & Hardcoded Matrices.
Scans source files for embedded numeric matrices, hardcoded financial cash flow tuples,
or static lookup tables designed to pass benchmarks without general document extraction.
"""

from __future__ import annotations

import ast
from typing import List
from minuscorrect.anti_cheat import CheatViolation


def check_hardcoded_benchmark_matrices(content: str, path: str) -> List[CheatViolation]:
    """Flag source files embedding literal tables with multiple financial float tuples."""
    violations: List[CheatViolation] = []
    try:
        tree = ast.parse(content)
    except SyntaxError:
        return violations

    for node in ast.walk(tree):
        # Detect lists/tuples containing >= 4 nested tuples/lists with float literals
        if isinstance(node, (ast.List, ast.Tuple)):
            nested_numeric_tuples = 0
            for elt in node.elts:
                if isinstance(elt, (ast.Tuple, ast.List)):
                    if any(
                        isinstance(val, ast.Constant) and isinstance(val.value, (float, int))
                        for val in elt.elts
                    ):
                        nested_numeric_tuples += 1

            if nested_numeric_tuples >= 4:
                violations.append(
                    CheatViolation(
                        violation_type="HARDCODED_BENCHMARK_MATRIX",
                        file_path=path,
                        line_number=node.lineno,
                        severity="Blocks launch",
                        description=(
                            f"Detected hardcoded tabular data matrix ({nested_numeric_tuples} numeric row tuples). "
                            "Embedding static financial or benchmark answer tables in source code is prohibited; "
                            "use dynamic extraction algorithms."
                        ),
                        snippet="[ (label, num1, num2, ...), ... ]",
                    )
                )
    return violations
