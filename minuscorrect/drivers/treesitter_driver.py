"""
MinusCorrect Tree-sitter Base AST Driver and Lazy Dependency Guard.
Provides PolyglotDependencyMissing exception and TreeSitterDriver base class.
# verifies: tests/unit/test_treesitter_driver.py
"""

from __future__ import annotations

import importlib
from typing import Any, List, Optional, Set

from minuscorrect.drivers.base import AstDriver, CheatViolation


class PolyglotDependencyMissing(ImportError):
    """
    Exception raised when Tree-sitter or language grammar dependencies are missing.
    # verifies: tests/unit/test_treesitter_driver.py
    """

    def __init__(self, language: str, extra_pkg: str = "minuscorrect[polyglot]"):
        self.language = language
        self.extra_pkg = extra_pkg
        self.message = (
            f"Polyglot AST parsing for '{language}' requires optional dependencies. "
            f"Install with: pip install {extra_pkg}"
        )
        self.msg = self.message
        super().__init__(self.message)


class TreeSitterDriver(AstDriver):
    """
    Base Tree-sitter AST driver with lazy dependency guard.
    # verifies: tests/unit/test_treesitter_driver.py
    """

    name: str = "treesitter-base"
    language_name: str = "base"
    supported_extensions: Set[str] = set()

    def __init__(
        self,
        language_name: Optional[str] = None,
        supported_extensions: Optional[Set[str]] = None,
        name: Optional[str] = None,
        parser: Optional[Any] = None,
        language: Optional[Any] = None,
    ) -> None:
        if name is not None:
            self.name = name
        if language_name is not None:
            self.language_name = language_name
        if supported_extensions is not None:
            self.supported_extensions = set(supported_extensions)
        elif not hasattr(self, "supported_extensions") or self.supported_extensions is None:
            self.supported_extensions = set()

        self._parser: Optional[Any] = parser
        self._language: Optional[Any] = language

    def is_available(self) -> bool:
        """
        Check if Tree-sitter core library and language grammar are available.
        # verifies: tests/unit/test_treesitter_driver.py
        """
        if self._parser is not None:
            return True

        try:
            import tree_sitter
            if tree_sitter is None or not hasattr(tree_sitter, "Parser"):
                return False
        except (ImportError, ModuleNotFoundError):
            return False

        try:
            lang = self.get_language()
            return lang is not None
        except PolyglotDependencyMissing:
            return False
        except Exception:
            return False

    def get_language(self) -> Any:
        """
        Safely resolve and return the Tree-sitter Language instance.
        Raises PolyglotDependencyMissing if dependencies or grammar are missing.
        # verifies: tests/unit/test_treesitter_driver.py
        """
        if self._language is not None:
            return self._language

        if not self.language_name or self.language_name == "base":
            raise PolyglotDependencyMissing(self.language_name or "base")

        try:
            import tree_sitter
            if tree_sitter is None:
                raise PolyglotDependencyMissing(self.language_name)
        except (ImportError, ModuleNotFoundError) as exc:
            raise PolyglotDependencyMissing(self.language_name) from exc

        clean_name = self.language_name.lower().replace("-", "_")
        alias_map = {"ts": "typescript", "js": "javascript", "py": "python"}
        clean_name = alias_map.get(clean_name, clean_name)
        mod_name = f"tree_sitter_{clean_name}"

        try:
            mod = importlib.import_module(mod_name)
            if mod is None:
                raise PolyglotDependencyMissing(self.language_name)
        except (ImportError, ModuleNotFoundError) as exc:
            raise PolyglotDependencyMissing(self.language_name) from exc

        fn = (
            getattr(mod, f"language_{clean_name}", None)
            or getattr(mod, "language", None)
            or getattr(mod, clean_name, None)
            or getattr(mod, "get_language", None)
        )
        if fn is None:
            raise PolyglotDependencyMissing(self.language_name)

        try:
            raw_lang = fn() if callable(fn) else fn
            language_cls = getattr(tree_sitter, "Language", None)
            if isinstance(language_cls, type) and isinstance(raw_lang, language_cls):
                return raw_lang
            elif callable(language_cls):
                return language_cls(raw_lang)
            return raw_lang
        except Exception as exc:
            raise PolyglotDependencyMissing(self.language_name) from exc

    def get_parser(self) -> Any:
        """
        Safely imports tree_sitter.Parser and Language, returning an initialized Parser.
        If Tree-sitter or the language grammar is missing, raises PolyglotDependencyMissing.
        # verifies: tests/unit/test_treesitter_driver.py
        """
        if self._parser is not None:
            return self._parser

        try:
            import tree_sitter
            if tree_sitter is None:
                raise PolyglotDependencyMissing(self.language_name)
            parser_cls = getattr(tree_sitter, "Parser", None)
            if parser_cls is None:
                raise PolyglotDependencyMissing(self.language_name)
        except (ImportError, ModuleNotFoundError) as exc:
            raise PolyglotDependencyMissing(self.language_name) from exc

        lang = self.get_language()

        try:
            try:
                parser = parser_cls(lang)
            except (TypeError, Exception):
                # Workaround: Handle bindings where Parser requires language assignment after instantiation
                parser = parser_cls()
                parser.language = lang
            return parser
        except PolyglotDependencyMissing:
            raise
        except Exception as exc:
            raise PolyglotDependencyMissing(self.language_name) from exc

    def inspect(
        self,
        source_code: str,
        file_path: str,
        is_test: bool = False,
        banned_literals: Optional[Set[str]] = None,
    ) -> List[CheatViolation]:
        """
        Inspect source code or test code using Tree-sitter AST.
        Raises PolyglotDependencyMissing if dependencies are not available.
        # verifies: tests/unit/test_treesitter_driver.py
        """
        if not self.is_available():
            raise PolyglotDependencyMissing(self.language_name)

        parser = self.get_parser()
        if hasattr(parser, "parse"):
            code_bytes = source_code.encode("utf-8") if isinstance(source_code, str) else source_code
            _tree = parser.parse(code_bytes)

        return []
