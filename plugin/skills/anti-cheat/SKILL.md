---
name: anti-cheat
description: >-
  AST-level anti-cheating guardian and benchmark overfitting prevention for Python and TypeScript.
---
# MinusCorrect AST Anti-Cheating Guardian & Benchmark Integrity Skill

MinusCorrect Gate 2 provides AST-level static verification to prevent autonomous coding agents from cheating on evaluation benchmarks, writing vacuous tests, or swallowing exceptions.

## When to Activate

- Auditing production and test code for benchmark overfitting or hardcoded shortcuts
- Banning specific benchmark fixture keys or table identifiers (e.g. `sec_10k_p3_cash_flows`)
- Automatically harvesting test fixtures and ground-truth tokens from benchmark corpus files (`sec100p_corpus.py`, `benchmarks/`)
- Catching assert-free tests, `try/except: pass` exception swallowing, and tautological assertions (`assert True`, `assert x == x`, `assert len(items) >= 0`)
- Authoring drop-in custom AST checkers in `.minus/checkers/*.py`

---

## Core Commands & Workflows

### 1. Run Complete Anti-Cheat Audit
```bash
minuscorrect anti-cheat
```
Or for machine-readable JSON:
```bash
minuscorrect anti-cheat --json
```

### 2. Ban a Benchmark Fixture or Anti-Pattern Literal
Register a prohibited benchmark identifier into `.minus/anti_patterns.json`:
```bash
minuscorrect anti-cheat --ban "sec_10k_p3_cash_flows"
minuscorrect anti-cheat --ban "Consolidated Statement of Cash Flows"
```

List all currently banned tokens:
```bash
minuscorrect anti-cheat --list-banned
```

### 3. Automated Corpus Harvesting
Automatically extract fixture keys, document identifiers, and table headers from a benchmark corpus file or folder:
```bash
minuscorrect anti-cheat --harvest minusbrain/benchmark/sec100p_corpus.py
```
MinusCorrect parses the corpus AST, filters out generic keywords, and automatically registers all dataset identifiers into `.minus/anti_patterns.json`.

### 4. Drop-in Custom Checkers (`.minus/checkers/`)
Drop any Python checker into `.minus/checkers/`. MinusCorrect automatically discovers and executes all functions accepting `(content, path)`:
```python
# .minus/checkers/check_benchmark_tables.py
from minuscorrect.anti_cheat import CheatViolation

def check_hardcoded_benchmark_matrices(content: str, path: str):
    # Scan AST for oversized static float tuples
    ...
```

### 5. Polyglot AST Anti-Cheat (TypeScript, TSX, JavaScript)
MinusCorrect includes pluggable Tree-sitter drivers for inspecting polyglot and mixed repositories (`.py`, `.ts`, `.tsx`, `.js`, `.jsx`):
- **Tautological Assertions**: Flags `expect(x).toBe(x)`, `expect(x).toEqual(x)`, `expect(true).toBe(true)`, `assert.equal(x, x)`, `assert.strictEqual(x, x)`.
- **Empty Catches**: Flags `catch (e) {}` blocks that swallow runtime exceptions without handling.
- **Assert-Free Tests**: Flags `it('...', ...)` or `test('...', ...)` with zero assertions or expect calls.
- **Fixture Leaks**: Scans TSX/JSX literals and string templates for banned benchmark answer tokens.

To install polyglot dependencies:
```bash
pip install minuscorrect[polyglot]
```

### 6. Pre-Commit Integration
Anti-cheat checks run automatically under strict verification:
```bash
minuscorrect verify --strict
```
Fails the build if any `Blocks launch` anti-cheat violations are found.

