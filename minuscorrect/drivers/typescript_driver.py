"""
MinusCorrect TypeScript / JavaScript AST Inspection Driver.
Provides Tree-sitter powered anti-cheat analysis for TypeScript and TSX files.
# verifies: tests/unit/test_typescript_anticheat.py
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Generator, List, Optional, Set

from minuscorrect.drivers.base import AstDriver, CheatViolation
from minuscorrect.drivers.treesitter_driver import (
    PolyglotDependencyMissing,
    TreeSitterDriver,
)


class TypeScriptDriver(TreeSitterDriver):
    """
    TypeScript and JavaScript AST driver using Tree-sitter.
    Inspects source code and test suites across .ts, .tsx, .js, and .jsx files.
    # verifies: tests/unit/test_typescript_anticheat.py
    """

    name: str = "typescript"
    language_name: str = "typescript"
    supported_extensions: Set[str] = {".ts", ".tsx", ".js", ".jsx"}

    def __init__(
        self,
        language_name: Optional[str] = "typescript",
        supported_extensions: Optional[Set[str]] = None,
        name: Optional[str] = "typescript",
        parser: Optional[Any] = None,
        language: Optional[Any] = None,
    ) -> None:
        if supported_extensions is None:
            supported_extensions = {".ts", ".tsx", ".js", ".jsx"}
        super().__init__(
            language_name=language_name,
            supported_extensions=supported_extensions,
            name=name,
            parser=parser,
            language=language,
        )
        self._parsers: Dict[str, Any] = {}

    def is_available(self) -> bool:
        """
        Check if Tree-sitter core library and tree_sitter_typescript grammar are available.
        # verifies: tests/unit/test_typescript_anticheat.py
        """
        if self._parser is not None:
            return True

        try:
            import tree_sitter
            if tree_sitter is None or not hasattr(tree_sitter, "Parser"):
                return False
        except (ImportError, ModuleNotFoundError, Exception):
            # Workaround: Tree-sitter core library is unavailable in this environment
            return False

        try:
            import tree_sitter_typescript
            if tree_sitter_typescript is None or not hasattr(tree_sitter_typescript, "language_typescript"):
                return False
        except (ImportError, ModuleNotFoundError, Exception):
            # Workaround: tree_sitter_typescript grammar package is not installed
            return False

        return True

    def get_language(self, is_tsx: bool = False) -> Any:
        """
        Safely resolve and return the Tree-sitter Language instance for TS or TSX.
        Raises PolyglotDependencyMissing if dependencies or grammar are missing.
        # verifies: tests/unit/test_typescript_anticheat.py
        """
        if self._language is not None and not is_tsx:
            return self._language

        try:
            import tree_sitter
            if tree_sitter is None:
                raise PolyglotDependencyMissing(self.language_name)
        except (ImportError, ModuleNotFoundError) as exc:
            # Rationale: Translate missing tree_sitter import to PolyglotDependencyMissing
            raise PolyglotDependencyMissing(self.language_name) from exc

        try:
            import tree_sitter_typescript
            if tree_sitter_typescript is None:
                raise PolyglotDependencyMissing(self.language_name)
        except (ImportError, ModuleNotFoundError) as exc:
            # Rationale: Translate missing tree_sitter_typescript import to PolyglotDependencyMissing
            raise PolyglotDependencyMissing(self.language_name) from exc

        fn = tree_sitter_typescript.language_tsx if is_tsx else tree_sitter_typescript.language_typescript
        if fn is None or not callable(fn):
            raise PolyglotDependencyMissing(self.language_name)

        try:
            raw_lang = fn()
            lang_cls = getattr(tree_sitter, "Language", None)
            if isinstance(lang_cls, type) and isinstance(raw_lang, lang_cls):
                return raw_lang
            elif callable(lang_cls):
                return lang_cls(raw_lang)
            return raw_lang
        except Exception as exc:
            # Rationale: Propagate polyglot failure if language object construction fails
            raise PolyglotDependencyMissing(self.language_name) from exc

    def get_parser(self, file_path: Optional[str] = None) -> Any:
        """
        Safely returns an initialized Tree-sitter Parser for TypeScript or TSX.
        Raises PolyglotDependencyMissing if Tree-sitter or grammar is unavailable.
        # verifies: tests/unit/test_typescript_anticheat.py
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
            # Rationale: Translate missing tree_sitter to PolyglotDependencyMissing
            raise PolyglotDependencyMissing(self.language_name) from exc

        is_tsx = bool(file_path and Path(file_path).suffix.lower() in {".tsx", ".jsx"})
        cache_key = "tsx" if is_tsx else "typescript"
        if cache_key in self._parsers:
            return self._parsers[cache_key]

        lang = self.get_language(is_tsx=is_tsx)
        try:
            try:
                parser = parser_cls(lang)
            except (TypeError, Exception):
                # Workaround: Handle bindings where Parser requires language assignment after instantiation
                parser = parser_cls()
                parser.language = lang
            self._parsers[cache_key] = parser
            return parser
        except PolyglotDependencyMissing:
            raise
        except Exception as exc:
            # Rationale: Re-raise parser errors as PolyglotDependencyMissing
            raise PolyglotDependencyMissing(self.language_name) from exc

    def _parse_tree(self, source_code: str, file_path: str = "source.ts") -> Any:
        """
        Parses source code string into a Tree-sitter Tree.
        # verifies: tests/unit/test_typescript_anticheat.py
        """
        if not self.is_available():
            raise PolyglotDependencyMissing(self.language_name)
        parser = self.get_parser(file_path=file_path)
        code_bytes = source_code.encode("utf-8") if isinstance(source_code, str) else source_code
        return parser.parse(code_bytes)

    @staticmethod
    def _walk_tree(node: Any) -> Generator[Any, None, None]:
        """
        Traverses all AST nodes in depth-first order.
        # verifies: tests/unit/test_typescript_anticheat.py
        """
        stack = [node]
        while stack:
            curr = stack.pop()
            yield curr
            stack.extend(reversed(curr.children))

    def detect_tautological_assertions(
        self,
        source_code: str,
        test_path: str = "test.ts",
    ) -> List[CheatViolation]:
        """
        Detects tautological assertions in TypeScript/JavaScript test suites.
        Flags: expect(x).toBe(x), expect(x).toEqual(x), expect(true).toBe(true),
        assert.equal(x, x), assert.strictEqual(x, x).
        # verifies: tests/unit/test_typescript_anticheat.py
        """
        violations: List[CheatViolation] = []
        try:
            tree = self._parse_tree(source_code, file_path=test_path)
        except PolyglotDependencyMissing:
            raise
        except Exception:
            # Rationale: Return empty violations on malformed source code
            return violations

        for node in self._walk_tree(tree.root_node):
            if node.type != "call_expression":
                continue

            fn = node.child_by_field_name("function")
            args = node.child_by_field_name("arguments")
            if not fn or not args:
                continue

            # Case 1: expect(x).toBe(x), expect(x).toEqual(x), expect(true).toBe(true)
            if fn.type == "member_expression":
                obj = fn.child_by_field_name("object")
                prop = fn.child_by_field_name("property")
                prop_name = prop.text.decode("utf-8", errors="replace") if prop else ""

                if obj and obj.type == "call_expression" and prop_name in (
                    "toBe", "toEqual", "toStrictEqual", "toBeStrictEqual", "toDeepEqual"
                ):
                    inner_fn = obj.child_by_field_name("function")
                    inner_args = obj.child_by_field_name("arguments")
                    if inner_fn and inner_fn.text == b"expect" and inner_args:
                        if len(inner_args.named_children) >= 1 and len(args.named_children) >= 1:
                            inner_arg = inner_args.named_children[0]
                            outer_arg = args.named_children[0]
                            if inner_arg.text.strip() == outer_arg.text.strip():
                                snippet = node.text.decode("utf-8", errors="replace")
                                violations.append(CheatViolation(
                                    violation_type="TAUTOLOGICAL_ASSERTION",
                                    file_path=test_path,
                                    line_number=node.start_point[0] + 1,
                                    severity="Blocks launch",
                                    description=f"Tautological assertion '{snippet}' detected; self-comparison does not verify behavior.",
                                    snippet=snippet,
                                ))
                                continue

                # expect(true).toBeTruthy() or expect(true).toBeTrue()
                if obj and obj.type == "call_expression" and prop_name in ("toBeTruthy", "toBeTrue"):
                    inner_fn = obj.child_by_field_name("function")
                    inner_args = obj.child_by_field_name("arguments")
                    if inner_fn and inner_fn.text == b"expect" and inner_args:
                        if len(inner_args.named_children) >= 1:
                            inner_arg = inner_args.named_children[0]
                            if inner_arg.type == "true" or inner_arg.text.strip() == b"true":
                                snippet = node.text.decode("utf-8", errors="replace")
                                violations.append(CheatViolation(
                                    violation_type="TAUTOLOGICAL_ASSERTION",
                                    file_path=test_path,
                                    line_number=node.start_point[0] + 1,
                                    severity="Blocks launch",
                                    description=f"Tautological assertion '{snippet}' detected; constant true does not verify behavior.",
                                    snippet=snippet,
                                ))
                                continue

                # Case 2: assert.equal(x, x), assert.strictEqual(x, x)
                obj_name = obj.text.decode("utf-8", errors="replace") if obj else ""
                if obj_name == "assert" and prop_name in (
                    "equal", "strictEqual", "deepEqual", "deepStrictEqual", "strict"
                ):
                    if len(args.named_children) >= 2:
                        arg0 = args.named_children[0]
                        arg1 = args.named_children[1]
                        if arg0.text.strip() == arg1.text.strip():
                            snippet = node.text.decode("utf-8", errors="replace")
                            violations.append(CheatViolation(
                                violation_type="TAUTOLOGICAL_ASSERTION",
                                file_path=test_path,
                                line_number=node.start_point[0] + 1,
                                severity="Blocks launch",
                                description=f"Self-comparison assertion detected: '{snippet}'.",
                                snippet=snippet,
                            ))
                            continue

            # Case 3: assert(true) or assert.ok(true) or assert(x === x)
            fn_text = fn.text.decode("utf-8", errors="replace")
            if fn_text in ("assert", "assert.ok"):
                if len(args.named_children) >= 1:
                    arg0 = args.named_children[0]
                    if arg0.type == "true" or arg0.text.strip() == b"true":
                        snippet = node.text.decode("utf-8", errors="replace")
                        violations.append(CheatViolation(
                            violation_type="TAUTOLOGICAL_ASSERTION",
                            file_path=test_path,
                            line_number=node.start_point[0] + 1,
                            severity="Blocks launch",
                            description=f"Tautological assertion '{snippet}' detected; does not verify program behavior.",
                            snippet=snippet,
                        ))
                    elif arg0.type == "binary_expression":
                        left = arg0.child_by_field_name("left")
                        op = arg0.child_by_field_name("operator")
                        right = arg0.child_by_field_name("right")
                        if op and op.text in (b"==", b"===", b"!=") and left and right:
                            if left.text.strip() == right.text.strip():
                                snippet = node.text.decode("utf-8", errors="replace")
                                violations.append(CheatViolation(
                                    violation_type="TAUTOLOGICAL_ASSERTION",
                                    file_path=test_path,
                                    line_number=node.start_point[0] + 1,
                                    severity="Blocks launch",
                                    description=f"Self-comparison assertion detected: '{snippet}'.",
                                    snippet=snippet,
                                ))

        return violations

    def detect_test_exception_swallowing(
        self,
        source_code: str,
        test_path: str = "test.ts",
    ) -> List[CheatViolation]:
        """
        Detects catch clauses whose body block contains no named statements/children (empty catch).
        # verifies: tests/unit/test_typescript_anticheat.py
        """
        violations: List[CheatViolation] = []
        try:
            tree = self._parse_tree(source_code, file_path=test_path)
        except PolyglotDependencyMissing:
            raise
        except Exception:
            # Rationale: Return empty violations on malformed source code
            return violations

        for node in self._walk_tree(tree.root_node):
            if node.type == "catch_clause":
                body = node.child_by_field_name("body")
                if not body:
                    for child in node.named_children:
                        if child.type == "statement_block":
                            body = child
                            break
                if body:
                    statements = [
                        c for c in body.named_children
                        if c.type not in ("comment", "empty_statement")
                    ]
                    if len(statements) == 0:
                        snippet = node.text.decode("utf-8", errors="replace")
                        violations.append(CheatViolation(
                            violation_type="TEST_EXCEPTION_SWALLOWING",
                            file_path=test_path,
                            line_number=node.start_point[0] + 1,
                            severity="Blocks launch",
                            description="Test catch block swallows exception with empty body, masking potential test failure.",
                            snippet=snippet,
                        ))

        return violations

    def detect_assert_free_tests(
        self,
        source_code: str,
        test_path: str = "test.ts",
    ) -> List[CheatViolation]:
        """
        Detects it(...) or test(...) call expressions whose callback body contains zero assertion calls (expect, assert, verify).
        # verifies: tests/unit/test_typescript_anticheat.py
        """
        violations: List[CheatViolation] = []
        try:
            tree = self._parse_tree(source_code, file_path=test_path)
        except PolyglotDependencyMissing:
            raise
        except Exception:
            # Rationale: Return empty violations on malformed source code
            return violations

        for node in self._walk_tree(tree.root_node):
            if node.type != "call_expression":
                continue

            fn = node.child_by_field_name("function")
            args = node.child_by_field_name("arguments")
            if not fn or not args:
                continue

            fn_text = fn.text.decode("utf-8", errors="replace")
            is_test_call = False
            if fn.type == "identifier" and fn_text in ("it", "test"):
                is_test_call = True
            elif fn.type == "member_expression":
                obj = fn.child_by_field_name("object")
                prop = fn.child_by_field_name("property")
                obj_text = obj.text.decode("utf-8", errors="replace") if obj else ""
                prop_text = prop.text.decode("utf-8", errors="replace") if prop else ""
                if obj_text in ("it", "test") and prop_text in (
                    "only", "skip", "todo", "concurrent", "failing"
                ):
                    is_test_call = True
            elif fn.type == "call_expression":
                inner_callee = fn.child_by_field_name("function")
                if inner_callee and inner_callee.type == "member_expression":
                    inner_obj = inner_callee.child_by_field_name("object")
                    inner_prop = inner_callee.child_by_field_name("property")
                    inner_obj_text = inner_obj.text.decode("utf-8", errors="replace") if inner_obj else ""
                    inner_prop_text = inner_prop.text.decode("utf-8", errors="replace") if inner_prop else ""
                    if inner_obj_text in ("it", "test") and inner_prop_text == "each":
                        is_test_call = True

            if not is_test_call:
                continue

            callback = None
            for arg in args.named_children:
                if arg.type in ("arrow_function", "function_expression", "function"):
                    callback = arg
                    break

            if callback is None:
                continue

            has_assertion = False
            for sub in self._walk_tree(callback):
                if sub.type == "call_expression":
                    sub_fn = sub.child_by_field_name("function")
                    if sub_fn:
                        for token in self._walk_tree(sub_fn):
                            if token.type in ("identifier", "property_identifier"):
                                token_name = token.text.decode("utf-8", errors="replace").lower()
                                if any(kw in token_name for kw in ("expect", "assert", "verify")):
                                    has_assertion = True
                                    break
                    if has_assertion:
                        break

            if not has_assertion:
                title = "unnamed test"
                if len(args.named_children) >= 1 and args.named_children[0].type in (
                    "string", "template_string"
                ):
                    title = args.named_children[0].text.decode("utf-8", errors="replace").strip("\"'`")

                snippet = node.text.decode("utf-8", errors="replace")
                first_line = snippet.splitlines()[0] if snippet else f"it('{title}', ...)"
                violations.append(CheatViolation(
                    violation_type="ASSERT_FREE_TEST",
                    file_path=test_path,
                    line_number=node.start_point[0] + 1,
                    severity="Blocks launch",
                    description=f"Test '{title}' contains zero assertion calls (expect, assert, verify); does not verify behavior.",
                    snippet=first_line,
                ))

        return violations

    def detect_banned_benchmark_fixtures(
        self,
        source_code: str,
        banned_literals: Set[str],
        source_path: str = "source.ts",
    ) -> List[CheatViolation]:
        """
        Detects string literals matching banned benchmark tokens (excluding comments).
        # verifies: tests/unit/test_typescript_anticheat.py
        """
        violations: List[CheatViolation] = []
        if not banned_literals:
            return violations

        try:
            tree = self._parse_tree(source_code, file_path=source_path)
        except PolyglotDependencyMissing:
            raise
        except Exception:
            # Rationale: Return empty violations on malformed source code
            return violations

        for node in self._walk_tree(tree.root_node):
            raw_text = None
            if node.type in ("string", "jsx_text"):
                raw_text = node.text.decode("utf-8", errors="replace")
            elif node.type == "template_string":
                for child in node.children:
                    if child.type == "string_fragment":
                        frag = child.text.decode("utf-8", errors="replace")
                        for banned in banned_literals:
                            if banned.lower() in frag.lower():
                                raw_text = node.text.decode("utf-8", errors="replace")
                                break
                        if raw_text is not None:
                            break

            if raw_text is not None:
                for banned in banned_literals:
                    if banned.lower() in raw_text.lower():
                        violations.append(CheatViolation(
                            violation_type="BANNED_BENCHMARK_FIXTURE_LEAK",
                            file_path=source_path,
                            line_number=node.start_point[0] + 1,
                            severity="Blocks launch",
                            description=(
                                f"Source code contains banned benchmark fixture key '{banned}'. "
                                f"Embedding hardcoded benchmark answer tables or test tokens is prohibited."
                            ),
                            snippet=raw_text.strip(),
                        ))
                        break

        return violations

    def inspect(
        self,
        source_code: str,
        file_path: str,
        is_test: bool = False,
        banned_literals: Optional[Set[str]] = None,
    ) -> List[CheatViolation]:
        """
        Inspect TypeScript/JavaScript source code or test files for anti-patterns and benchmark cheating.
        Verifies is_available() first (raises PolyglotDependencyMissing if unavailable).
        # verifies: tests/unit/test_typescript_anticheat.py
        """
        if not self.is_available():
            raise PolyglotDependencyMissing(self.language_name)

        violations: List[CheatViolation] = []
        if is_test:
            violations.extend(self.detect_tautological_assertions(source_code, test_path=file_path))
            violations.extend(self.detect_assert_free_tests(source_code, test_path=file_path))
            violations.extend(self.detect_test_exception_swallowing(source_code, test_path=file_path))
        else:
            if banned_literals:
                violations.extend(
                    self.detect_banned_benchmark_fixtures(source_code, banned_literals, source_path=file_path)
                )
        return violations


_DEFAULT_TYPESCRIPT_DRIVER = TypeScriptDriver()


def detect_tautological_assertions(
    source_code: str,
    test_path: str = "test.ts",
) -> List[CheatViolation]:
    """
    Detects tautological assertions in TypeScript / JavaScript test suites.
    # verifies: tests/unit/test_typescript_anticheat.py
    """
    return _DEFAULT_TYPESCRIPT_DRIVER.detect_tautological_assertions(source_code, test_path=test_path)


def detect_test_exception_swallowing(
    source_code: str,
    test_path: str = "test.ts",
) -> List[CheatViolation]:
    """
    Detects empty catch clauses in TypeScript / JavaScript test suites.
    # verifies: tests/unit/test_typescript_anticheat.py
    """
    return _DEFAULT_TYPESCRIPT_DRIVER.detect_test_exception_swallowing(source_code, test_path=test_path)


def detect_assert_free_tests(
    source_code: str,
    test_path: str = "test.ts",
) -> List[CheatViolation]:
    """
    Detects assert-free it(...) or test(...) blocks in TypeScript / JavaScript test suites.
    # verifies: tests/unit/test_typescript_anticheat.py
    """
    return _DEFAULT_TYPESCRIPT_DRIVER.detect_assert_free_tests(source_code, test_path=test_path)


def detect_banned_benchmark_fixtures(
    source_code: str,
    banned_literals: Set[str],
    source_path: str = "source.ts",
) -> List[CheatViolation]:
    """
    Detects banned benchmark fixtures embedded in TypeScript / JavaScript source files.
    # verifies: tests/unit/test_typescript_anticheat.py
    """
    return _DEFAULT_TYPESCRIPT_DRIVER.detect_banned_benchmark_fixtures(
        source_code, banned_literals, source_path=source_path
    )
