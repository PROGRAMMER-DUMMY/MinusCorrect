"""
Unit tests for MinusCorrect AstDriver protocol and language drivers.
# verifies: tests/unit/test_anti_cheat.py
"""

from pathlib import Path
from typing import List, Optional, Set

from minuscorrect.drivers import (
    AstDriver,
    CheatViolation,
    NativePythonDriver,
    get_driver_for_file,
    get_registered_drivers,
    register_driver,
)


def test_ast_driver_protocol_compliance() -> None:
    driver = NativePythonDriver()
    assert isinstance(driver, AstDriver)
    assert driver.name == "python"
    assert ".py" in driver.supported_extensions


def test_driver_registry_lookup() -> None:
    # NativePythonDriver should be registered by default
    drivers = get_registered_drivers()
    assert "python" in drivers

    # Look up by str path and Path object
    driver_str = get_driver_for_file("app/main.py")
    assert driver_str is not None
    assert driver_str.name == "python"

    driver_path = get_driver_for_file(Path("tests/test_something.py"))
    assert driver_path is not None
    assert driver_path.name == "python"

    # Non-existent extension returns None
    assert get_driver_for_file("app/index.unknown") is None


def test_custom_driver_registration() -> None:
    class DummyJsDriver(AstDriver):
        name: str = "javascript"
        supported_extensions: Set[str] = {".js", ".jsx"}

        def inspect(
            self,
            source_code: str,
            file_path: str,
            is_test: bool = False,
            banned_literals: Optional[Set[str]] = None,
        ) -> List[CheatViolation]:
            if "CHEAT_PAYLOAD" in source_code:
                return [
                    CheatViolation(
                        violation_type="JS_CHEAT",
                        file_path=file_path,
                        line_number=1,
                        severity="Blocks launch",
                        description="Detected JS cheat payload.",
                        snippet="CHEAT_PAYLOAD",
                    )
                ]
            return []

    js_driver = DummyJsDriver()
    import minuscorrect.drivers.base as base_mod
    orig_drivers = dict(base_mod._DRIVERS)
    try:
        register_driver(js_driver)

        registered = get_registered_drivers()
        assert "javascript" in registered

        found = get_driver_for_file("frontend/src/index.jsx")
        assert found is not None
        assert found.name == "javascript"

        violations = found.inspect("const x = CHEAT_PAYLOAD;", "index.jsx")
        assert len(violations) == 1
        assert violations[0].violation_type == "JS_CHEAT"
    finally:
        base_mod._DRIVERS.clear()
        base_mod._DRIVERS.update(orig_drivers)


def test_native_python_driver_inspect_test_suite() -> None:
    driver = NativePythonDriver()
    test_code = """
def test_tautology():
    assert True

def test_empty():
    x = 1 + 1

def test_swallow():
    try:
        do_work()
    except Exception:
        pass

def test_vacuous():
    items = []
    assert len(items) >= 0
"""
    violations = driver.inspect(test_code, file_path="test_mock.py", is_test=True)
    violation_types = {v.violation_type for v in violations}
    assert "TAUTOLOGICAL_ASSERTION" in violation_types
    assert "ASSERT_FREE_TEST" in violation_types
    assert "TEST_EXCEPTION_SWALLOWING" in violation_types
    assert "VACUOUS_ASSERTION" in violation_types


def test_native_python_driver_inspect_source_banned_fixture() -> None:
    driver = NativePythonDriver()
    source_code = """
def process():
    token = "forbidden_fixture_key_123"
    return token
"""
    banned = {"forbidden_fixture_key_123"}
    violations = driver.inspect(
        source_code,
        file_path="service.py",
        is_test=False,
        banned_literals=banned,
    )
    assert len(violations) == 1
    assert violations[0].violation_type == "BANNED_BENCHMARK_FIXTURE_LEAK"
    assert "forbidden_fixture_key_123" in violations[0].description
