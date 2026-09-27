"""
MinusCorrect Language AST Drivers package.
Provides modular AST drivers for inspecting source code and test suites across languages.
# verifies: tests/unit/test_anti_cheat.py
"""

from minuscorrect.drivers.base import (
    AstDriver,
    CheatViolation,
    get_driver_for_file,
    get_registered_drivers,
    register_driver,
)
from minuscorrect.drivers.python_driver import (
    NativePythonDriver,
    detect_assert_free_tests,
    detect_banned_benchmark_fixtures,
    detect_tautological_assertions,
    detect_test_exception_swallowing,
    detect_vacuous_assertions,
)
from minuscorrect.drivers.treesitter_driver import (
    PolyglotDependencyMissing,
    TreeSitterDriver,
)

# Register default Python driver
register_driver(NativePythonDriver())

__all__ = [
    "AstDriver",
    "CheatViolation",
    "NativePythonDriver",
    "PolyglotDependencyMissing",
    "TreeSitterDriver",
    "detect_assert_free_tests",
    "detect_banned_benchmark_fixtures",
    "detect_tautological_assertions",
    "detect_test_exception_swallowing",
    "detect_vacuous_assertions",
    "get_driver_for_file",
    "get_registered_drivers",
    "register_driver",
]
