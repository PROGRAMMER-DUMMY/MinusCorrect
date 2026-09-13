# Universal Agent Instructions (AGENTS.md)

> This repository adheres to **Systemic Integrity & Closed-Loop Verification**. All autonomous coding agents (Claude Code, Google Antigravity/Agy, OpenAI Codex, Cursor, Aider, OpenHands) operating in this repository must strictly follow this specification.

---

## Core Reference
Read and adhere to the canonical rules in [`.agent-rules/systemic-integrity.md`](.agent-rules/systemic-integrity.md).

---

## Non-Negotiable Operational Invariants

### 1. Evidence Over Labels
* **Docstrings and comments are claims, not evidence.** Never accept self-reported text as ground truth.
* Derive actual intent from AST structures, type signatures, sibling contracts, and passing test assertions.
* Reconstruct behavioral reality before proposing code changes.

### 2. Test Stratification (The "No Cheating" Boundary)
* **`tests/golden/` (Immutable Acceptance Contracts):**
  * When fixing bugs or implementing features, files in `tests/golden/` are **strictly read-only**.
  * **Strictly Prohibited:** Modifying, commenting out, or loosening assertions in `tests/golden/` to make a run pass.
  * Production code adapts to the specification, never the reverse.
  * *Break-glass override for intentional contract changes:* `ALLOW_GOLDEN_EDIT=1 git commit`.
* **`tests/unit/` (Mutable Developer Tests):**
  * Agents have full read/write access to author and update unit tests, component tests, and test helpers.

### 3. The Two-Category Docstring Standard
* **Category 1: Operational Guarantees ("The What"):**
  * Any claim of algorithmic complexity, concurrency, or purity (`O(1)`, `thread-safe`, `idempotent`, `zero-dependency`) **must have receipts** linking directly to a test: `# verifies: tests/golden/test_concurrency.py`.
  * All usage examples in docstrings must be executable via doctests (`pytest --doctest-modules`).
  * Marketing superlatives (`universal`, `bulletproof`, `blazing fast`) are prohibited.
* **Category 2: Contextual Rationale ("The Why"):**
  * Explanations of business trade-offs, legacy quirks, or third-party workarounds must use structured tags:
    * `# Rationale: <business reason or trade-off>`
    * `# Workaround: <vendor/browser quirk or issue link>`
    * `# Assumption: <external boundary invariant>`

### 4. Bounded Actuator & 4-Iteration Ceiling
* **Blast Radius:** Read widely across imported types, contracts, and schemas, but isolate code mutations strictly to the targeted implementation file.
* **Max 4 Iterations:**
  1. **Iteration 1–2:** Algorithmic fixes based on compiler/test error output.
  2. **Iteration 3 (Identical Error Hash):** Inject temporary `[DEBUG]` logs to observe runtime state. Re-run test.
  3. **Iteration 4:** If still failing, **hard abort**. Do not burn tokens. Report the failing invariant and observed runtime values.
* **Scaffolding Cleanup:** All temporary `[DEBUG]` traces must be stripped before completing the task. The pre-commit hook will reject commits containing leftover debug tags.

---

## Pre-Commit Verification
Before declaring any task complete or making a commit, run the local integrity verifier:
```bash
python scripts/verify_integrity.py
```
Ensure that:
1. Golden tests in `tests/golden/` are untouched.
2. No `[DEBUG]` logs or `console.log("__DEBUG__")` traces exist in source code.
3. No unverified docstring superlatives were added without test receipts.
