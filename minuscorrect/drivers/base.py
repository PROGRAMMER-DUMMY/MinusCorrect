"""
MinusCorrect AstDriver Protocol and Driver Registry.
Provides the pluggable AstDriver interface and language driver registry.
# verifies: tests/unit/test_anti_cheat.py
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Protocol, Set, Union, runtime_checkable


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


@runtime_checkable
class AstDriver(Protocol):
    """
    Protocol defining the interface for language-specific AST inspection drivers.
    # verifies: tests/unit/test_anti_cheat.py
    """
    name: str
    supported_extensions: Set[str]

    def inspect(
        self,
        source_code: str,
        file_path: str,
        is_test: bool = False,
        banned_literals: Optional[Set[str]] = None,
    ) -> List[CheatViolation]:
        """
        Inspect source code or test code for anti-patterns and benchmark cheating.
        """
        ...


_DRIVERS: Dict[str, AstDriver] = {}


def register_driver(driver: AstDriver) -> None:
    """
    Register an AST inspection driver by its name.
    # verifies: tests/unit/test_anti_cheat.py
    """
    _DRIVERS[driver.name] = driver


def get_driver_for_file(path: Union[str, Path]) -> Optional[AstDriver]:
    """
    Retrieve the registered AST driver capable of inspecting the given file based on extension.
    # verifies: tests/unit/test_anti_cheat.py
    """
    p = Path(path)
    suffix = p.suffix.lower()
    if not suffix and p.name.startswith("."):
        suffix = p.name.lower()

    for driver in reversed(list(_DRIVERS.values())):
        if (
            suffix in driver.supported_extensions
            or suffix.lstrip(".") in driver.supported_extensions
            or p.name.lower() in driver.supported_extensions
            or f".{p.name.lower()}" in driver.supported_extensions
        ):
            return driver
    return None


def get_registered_drivers() -> Dict[str, AstDriver]:
    """
    Return a dictionary mapping registered driver names to AstDriver instances.
    # verifies: tests/unit/test_anti_cheat.py
    """
    return dict(_DRIVERS)
