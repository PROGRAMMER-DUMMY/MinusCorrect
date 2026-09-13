# Contributing to MinusCorrect

Thank you for contributing to **MinusCorrect**! We welcome improvements to the specification, enforcement tooling, and multi-agent workflows.

---

## 🛠️ Development & Contribution Workflow

MinusCorrect practices what it preaches: all code modifications must pass our own Systemic Integrity verification.

### 1. Test Stratification
* **Golden Tests (`tests/golden/`):**
  * When fixing a bug or adding a core specification requirement, first add a failing test in `tests/golden/`.
  * Golden tests represent non-negotiable contract specifications. Once merged, they are strictly read-only.
  * If a contract change legitimately requires updating an existing golden test, commit with the break-glass override:
    ```bash
    ALLOW_GOLDEN_EDIT=1 git commit -m "refactor(contracts): update contract specification"
    ```
* **Unit Tests (`tests/unit/`):**
  * Feature-level tests and internal helper tests belong in `tests/unit/` and can be freely iterated upon.

### 2. The Two-Category Docstring Standard
* **Category 1: Operational Guarantees ("The What")**:
  * Any claim regarding complexity (`O(1)`), concurrency (`thread-safe`), purity, or zero dependencies MUST be linked to an automated test receipt:
    ```python
    # verifies: tests/golden/test_concurrency.py
    ```
  * Marketing superlatives (`universal`, `bulletproof`, `blazing fast`) are forbidden.
* **Category 2: Contextual Rationale ("The Why")**:
  * Explanations of business trade-offs, legacy quirks, or third-party workarounds must use structured tags:
    * `# Rationale: <business or architectural trade-off>`
    * `# Workaround: <issue ID or browser/vendor quirk>`
    * `# Assumption: <external boundary invariant>`

### 3. Local Verification
Before opening a pull request, run the integrity verifier:
```bash
python scripts/verify_integrity.py
```

Ensure that:
* No temporary agent debug logs (`[DEBUG]`) remain in source files.
* No unauthorized modifications exist in `tests/golden/`.
* No unverified docstring superlatives are introduced.

---

## 📜 Code of Conduct
Please be respectful, constructive, and direct in all discussions and pull requests.
