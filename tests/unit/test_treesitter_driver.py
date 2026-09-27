"""
Unit tests for TreeSitterDriver base class and PolyglotDependencyMissing exception.
# verifies: tests/unit/test_treesitter_driver.py
"""

from __future__ import annotations

import sys
from typing import Set
from unittest import mock

import pytest

from minuscorrect.drivers.base import AstDriver
from minuscorrect.drivers.treesitter_driver import (
    PolyglotDependencyMissing,
    TreeSitterDriver,
)


def test_drivers_package_exports() -> None:
    """
    Test that PolyglotDependencyMissing and TreeSitterDriver are exported in minuscorrect.drivers.
    # verifies: tests/unit/test_treesitter_driver.py
    """
    import minuscorrect.drivers as drivers

    assert hasattr(drivers, "PolyglotDependencyMissing")
    assert hasattr(drivers, "TreeSitterDriver")
    assert "PolyglotDependencyMissing" in drivers.__all__
    assert "TreeSitterDriver" in drivers.__all__


def test_polyglot_dependency_missing_formatting_default() -> None:
    """
    Test PolyglotDependencyMissing formatting with default extra_pkg.
    # verifies: tests/unit/test_treesitter_driver.py
    """
    exc = PolyglotDependencyMissing("typescript")
    assert isinstance(exc, ImportError)
    assert exc.language == "typescript"
    assert exc.extra_pkg == "minuscorrect[polyglot]"
    error_msg = str(exc)
    assert "typescript" in error_msg
    assert "minuscorrect[polyglot]" in error_msg
    assert "pip install minuscorrect[polyglot]" in error_msg


def test_polyglot_dependency_missing_formatting_custom_package() -> None:
    """
    Test PolyglotDependencyMissing formatting with custom extra_pkg.
    # verifies: tests/unit/test_treesitter_driver.py
    """
    exc = PolyglotDependencyMissing("rust", extra_pkg="minuscorrect[rust]")
    assert exc.language == "rust"
    assert exc.extra_pkg == "minuscorrect[rust]"
    error_msg = str(exc)
    assert "rust" in error_msg
    assert "minuscorrect[rust]" in error_msg


def test_treesitter_driver_instantiation_defaults() -> None:
    """
    Test default TreeSitterDriver instantiation and AstDriver protocol compliance.
    # verifies: tests/unit/test_treesitter_driver.py
    """
    driver = TreeSitterDriver()
    assert driver.name == "treesitter-base"
    assert driver.language_name == "base"
    assert driver.supported_extensions == set()
    assert isinstance(driver, AstDriver)


def test_treesitter_driver_instantiation_custom_attributes() -> None:
    """
    Test TreeSitterDriver instantiation with customized parameters.
    # verifies: tests/unit/test_treesitter_driver.py
    """
    extensions: Set[str] = {".ts", ".tsx"}
    driver = TreeSitterDriver(
        name="custom-ts",
        language_name="typescript",
        supported_extensions=extensions,
    )
    assert driver.name == "custom-ts"
    assert driver.language_name == "typescript"
    assert driver.supported_extensions == {".ts", ".tsx"}
    assert isinstance(driver, AstDriver)


def test_treesitter_driver_subclass_protocol_compliance() -> None:
    """
    Test that subclasses of TreeSitterDriver conform to AstDriver protocol.
    # verifies: tests/unit/test_treesitter_driver.py
    """
    class SampleDriver(TreeSitterDriver):
        name: str = "sample"
        language_name: str = "sample"
        supported_extensions: Set[str] = {".smp"}

    sample = SampleDriver()
    assert sample.name == "sample"
    assert sample.language_name == "sample"
    assert sample.supported_extensions == {".smp"}
    assert isinstance(sample, AstDriver)


def test_is_available_returns_false_when_uninstalled() -> None:
    """
    Test is_available returns False when grammar is not installed.
    # verifies: tests/unit/test_treesitter_driver.py
    """
    driver = TreeSitterDriver(language_name="nonexistent_lang_12345")
    assert driver.is_available() is False


def test_is_available_returns_false_for_base_driver() -> None:
    """
    Test base TreeSitterDriver has is_available False since base has no concrete grammar.
    # verifies: tests/unit/test_treesitter_driver.py
    """
    driver = TreeSitterDriver()
    assert driver.is_available() is False


def test_is_available_returns_false_when_treesitter_core_mocked_away() -> None:
    """
    Test is_available returns False when tree_sitter core module is missing.
    # verifies: tests/unit/test_treesitter_driver.py
    """
    with mock.patch.dict(sys.modules, {"tree_sitter": None}):
        driver = TreeSitterDriver(language_name="typescript")
        assert driver.is_available() is False


def test_is_available_returns_false_when_grammar_mocked_away() -> None:
    """
    Test is_available returns False when language grammar is missing.
    # verifies: tests/unit/test_treesitter_driver.py
    """
    with mock.patch.dict(sys.modules, {"tree_sitter_typescript": None}):
        driver = TreeSitterDriver(language_name="typescript")
        assert driver.is_available() is False


def test_calling_get_parser_raises_when_unavailable() -> None:
    """
    Test get_parser raises PolyglotDependencyMissing when grammar is uninstalled.
    # verifies: tests/unit/test_treesitter_driver.py
    """
    driver = TreeSitterDriver(language_name="uninstalled_grammar_xyz")
    with pytest.raises(PolyglotDependencyMissing) as exc_info:
        driver.get_parser()
    assert exc_info.value.language == "uninstalled_grammar_xyz"
    assert "uninstalled_grammar_xyz" in str(exc_info.value)
    assert "minuscorrect[polyglot]" in str(exc_info.value)


def test_calling_inspect_raises_when_unavailable() -> None:
    """
    Test inspect raises PolyglotDependencyMissing when driver is unavailable.
    # verifies: tests/unit/test_treesitter_driver.py
    """
    driver = TreeSitterDriver(language_name="uninstalled_grammar_xyz")
    with pytest.raises(PolyglotDependencyMissing) as exc_info:
        driver.inspect(source_code="fn main() {}", file_path="main.xyz")
    assert exc_info.value.language == "uninstalled_grammar_xyz"


def test_calling_get_parser_and_inspect_raises_when_tree_sitter_mocked_away() -> None:
    """
    Test get_parser and inspect raise when tree_sitter core is missing.
    # verifies: tests/unit/test_treesitter_driver.py
    """
    with mock.patch.dict(sys.modules, {"tree_sitter": None}):
        driver = TreeSitterDriver(language_name="python")
        with pytest.raises(PolyglotDependencyMissing):
            driver.get_parser()
        with pytest.raises(PolyglotDependencyMissing):
            driver.inspect(source_code="x = 1", file_path="x.py")


def test_mock_parser_execution_via_injected_parser() -> None:
    """
    Test execution when mock parser is provided directly.
    # verifies: tests/unit/test_treesitter_driver.py
    """
    mock_parser = mock.MagicMock()
    mock_tree = mock.MagicMock()
    mock_parser.parse.return_value = mock_tree

    driver = TreeSitterDriver(
        name="mock-driver",
        language_name="mock_lang",
        supported_extensions={".mock"},
        parser=mock_parser,
    )
    assert driver.is_available() is True
    assert driver.get_parser() is mock_parser

    violations = driver.inspect(source_code="test code content", file_path="sample.mock")
    assert violations == []
    mock_parser.parse.assert_called_once_with(b"test code content")


def test_mock_parser_execution_via_sys_modules() -> None:
    """
    Test execution when tree_sitter and language modules are mocked in sys.modules.
    # verifies: tests/unit/test_treesitter_driver.py
    """
    mock_ts = mock.MagicMock()
    mock_parser_instance = mock.MagicMock()
    mock_ts.Parser.return_value = mock_parser_instance

    mock_grammar = mock.MagicMock()
    mock_lang_capsule = mock.MagicMock()
    mock_grammar.language.return_value = mock_lang_capsule

    with mock.patch.dict(
        sys.modules,
        {
            "tree_sitter": mock_ts,
            "tree_sitter_mocklang": mock_grammar,
        },
    ):
        driver = TreeSitterDriver(language_name="mocklang", supported_extensions={".ml"})
        assert driver.is_available() is True
        parser = driver.get_parser()
        assert parser is mock_parser_instance

        violations = driver.inspect(source_code="let a = 10;", file_path="test.ml")
        assert violations == []
        mock_parser_instance.parse.assert_called_once_with(b"let a = 10;")


def test_real_treesitter_driver_if_available() -> None:
    """
    Test execution with real tree-sitter language if installed in environment.
    # verifies: tests/unit/test_treesitter_driver.py
    """
    driver = TreeSitterDriver(language_name="python", supported_extensions={".py"})
    if driver.is_available():
        parser = driver.get_parser()
        assert parser is not None
        violations = driver.inspect(source_code="a = 1 + 2", file_path="foo.py")
        assert violations == []
