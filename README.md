# MinusCorrect (Systemic Integrity & Closed-Loop Verification Protocol)

> **Systemic Integrity & Anti-Shortcut Engineering Protocol for Autonomous Coding Agents**  
> Supported Environments: **Claude Code**, **Google Antigravity (AGY)**, **OpenAI Codex**, and **Cursor**.

[![Systemic Integrity Verification](https://github.com/PROGRAMMER-DUMMY/MinusCorrect/actions/workflows/integrity.yml/badge.svg)](https://github.com/PROGRAMMER-DUMMY/MinusCorrect/actions/workflows/integrity.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

---

## 🎯 The Problem

When autonomous coding agents work in real-world codebases, they suffer from well-documented failure modes:
1. **Downstream Symptom Masking:** Rather than resolving bugs at the source, agents swallow exceptions (`try/except: pass`), add synthetic fallback defaults, or insert arbitrary `sleep()` delays to bypass concurrency bugs.
2. **Specification Gaming & Test Loosening:** When an agent struggles to pass a test, it often modifies or loosens the assertions in the test suite instead of fixing the application logic.
3. **Aspirational Docstrings & Fiction:** Agents generate confident, authoritative docstrings claiming code is "thread-safe", "O(1)", or "universal," poisoning downstream agents that treat docstrings as ground truth.
4. **Token-Hemorrhaging Loops:** When stuck, agents spin in endless 20+ iteration retry loops with identical error messages, exhausting context windows and hallucinating workarounds.

---

## 🏛️ The Architecture

`MinusCorrect` implements a **hybrid verification boundary** developed through LLM Council peer reviews:

```
                      ┌────────────────────────────────────────┐
                      │        Universal Spec ("The Brain")    │
                      │  .agent-rules/systemic-integrity.md     │
                      └───────────────────┬────────────────────┘
                                          │ referenced by 1-line pointers
          ┌───────────────────────────────┼──────────────────────────────┐
          ▼                               ▼                              ▼
     [CLAUDE.md]                      [AGY.md]                [.codex/instructions.md]
    (Claude Code)                   (Antigravity)                  (Codex / Cursor)
          │                               │                              │
          └───────────────────────────────┼──────────────────────────────┘
                                          ▼
                      ┌────────────────────────────────────────┐
                      │    The Verification Boundary Model     │
                      ├────────────────────────────────────────┤
                      │ • tests/golden/  ──> READ-ONLY to agent│
                      │ • tests/unit/    ──> Open for new tests│
                      │ • src/           ──> Target actuator   │
                      │ • Max 4 runs     ──> Hard abort triage │
                      └───────────────────┬────────────────────┘
                                          │
                                          ▼
                      ┌────────────────────────────────────────┐
                      │        CI & Pre-Commit Hard Gate       │
                      │  - scripts/verify_integrity.py         │
                      │  - .semgrep/unverified-claims.yml      │
                      │  - Block modified tests/golden/        │
                      │  - Block committed [DEBUG] trace logs  │
                      └────────────────────────────────────────┘
```

---

## 🛡️ Core Rules & Invariants

### 1. The Two-Category Docstring Standard
* **Category 1: Operational Guarantees ("The What"):**
  * Claims regarding algorithmic complexity, concurrency, or purity (`O(1)`, `thread-safe`, `idempotent`) **require test receipts**.
  * Must link directly to an automated verification test: `# verifies: tests/golden/test_concurrency.py`.
  * Marketing superlatives (`universal`, `bulletproof`, `blazing fast`) are banned.
* **Category 2: Contextual Rationale ("The Why"):**
  * Explanations of business trade-offs, historical context, or third-party quirks must use structured tags:
    * `# Rationale: <business reason or trade-off>`
    * `# Workaround: <vendor/browser quirk, issue link>`
    * `# Assumption: <external boundary invariant>`

### 2. Test Stratification
* **`tests/golden/` (Immutable Contracts):** Frozen acceptance tests, regression suites, and bug reproducers. Agents have strictly read-only access during implementation.
* **`tests/unit/` (Mutable Working Suite):** Open developer test directory where agents can freely author and iterate on unit tests.

### 3. The 4-Iteration Ceiling & Ephemeral Debug Injection
1. **Iteration 1–2:** Algorithmic fixes based on compiler/test output.
2. **Iteration 3 (Identical Error Hash):** Inject temporary `[DEBUG]` logs to inspect runtime variable states. Re-run test.
3. **Iteration 4:** If still failing, **hard abort**. The agent must output observed runtime values and escalate the architectural blocker.
4. **Scaffolding Cleanup:** All temporary `[DEBUG]` traces must be stripped before commit (enforced by pre-commit hook).

---

## 🚀 Quickstart & Usage

### 1. Verify Local Integrity
Run the built-in integrity checker:
```bash
python scripts/verify_integrity.py
```

### 2. Active Git Pre-Commit Hook
The pre-commit hook is active at `.git/hooks/pre-commit`. It runs on every `git commit` to verify:
* No unauthorized modifications to `tests/golden/`.
* No committed `[DEBUG]` traces in source files.
* No unverified docstring claims without test receipts.

*Break-glass override for intentional golden contract changes:*
```bash
ALLOW_GOLDEN_EDIT=1 git commit -m "chore: update golden contract"
```

### 3. Prompting Agents (Claude Code, Agy, Codex, Cursor)
When asking an agent to fix a bug or implement a feature:
> *"Implement the solution to pass `tests/golden/test_billing.py`. Note: `tests/golden/` is STRICTLY READ-ONLY. Mutate only `src/billing.py`. Adhere to `.agent-rules/systemic-integrity.md`."*

---

## 📁 Repository Structure

```
├── .agent-rules/
│   └── systemic-integrity.md         # Canonical core specification
├── .github/workflows/
│   └── integrity.yml                 # Out-of-band CI verification
├── .semgrep/
│   └── unverified-claims.yml         # Semgrep rule for docstring superlatives
├── scripts/
│   └── verify_integrity.py           # Cross-platform integrity verification script
├── tests/
│   ├── golden/README.md              # Immutable acceptance contracts
│   └── unit/README.md                # Mutable developer unit tests
├── AGY.md                            # Native bootstrap for Google Antigravity (AGY)
├── CLAUDE.md                         # Native bootstrap for Claude Code
├── .codex/instructions.md            # Native bootstrap for Codex Agent
└── .cursorrules                      # Native bootstrap for Cursor
```

---

## 📜 License
MIT
