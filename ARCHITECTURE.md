# MinusCorrect: System Architecture

This document specifies the technical architecture, verification topologies, state transition models, AST claim auditing mechanics, and gatekeeping pipelines of **MinusCorrect**.

---

## 1. High-Level System Architecture

MinusCorrect functions as an automated systemic integrity and anti-shortcut verification protocol. It establishes rigid boundaries around autonomous coding agents (Claude Code, Google Antigravity, OpenAI Codex, Cursor) to prevent common agent failure modes: specification gaming, downstream symptom masking, unverified docstring claims, and infinite context exhaustion loops.

### Visual Architecture Topology

```
+-------------------------------------------------------------------------------+
|                           AUTONOMOUS CODING AGENTS                            |
|             (Claude Code / Google Antigravity / OpenAI Codex / Cursor)         |
+---------------------------------------+---------------------------------------+
                                        | Reads instructions
                                        v
+-------------------------------------------------------------------------------+
|                         LAYER 1: SPECIFICATION INGRESS                        |
|                                                                               |
|   +--------------------------+             +------------------------------+   |
|   |        AGENTS.md         |             |    Native Tool Bootstraps    |   |
|   | (Universal Root Contract)|             |  .cursorrules | instructions |   |
|   +------------+-------------+             +--------------+---------------+   |
|                |                                          |                   |
|                +--------------------+---------------------+                   |
|                                     v                                         |
|                     .agent-rules/systemic-integrity.md                        |
|                   (Intent Reconstruction & Core Invariants)                   |
+-------------------------------------+-----------------------------------------+
                                      | Constrains
                                      v
+-------------------------------------------------------------------------------+
|                       LAYER 2: VERIFICATION BOUNDARIES                        |
|                                                                               |
|   +--------------------------+             +------------------------------+   |
|   |       tests/golden/      |             |         tests/unit/          |   |
|   |   (Acceptance Contracts) |             |   (Developer Working Suite)  |   |
|   |   STATUS: READ-ONLY      |             |   STATUS: READ / WRITE       |   |
|   +--------------------------+             +------------------------------+   |
|                                                                               |
|                           [ BLAST RADIUS TARGET ]                             |
|                           src/<target_module>.py                              |
|                           (Single File Mutation)                              |
+-------------------------------------+-----------------------------------------+
                                      | Iterates under test feedback
                                      v
+-------------------------------------------------------------------------------+
|                    LAYER 3: CLOSED-LOOP SOLVER & CIRCUIT BREAKER              |
|                                                                               |
|   Iter 1-2: Algorithmic Patch  --> Iter 3: [DEBUG] Traces --> Iter 4: ABORT   |
+-------------------------------------+-----------------------------------------+
                                      | Staged code changes
                                      v
+-------------------------------------------------------------------------------+
|                       LAYER 4: DETERMINISTIC GATEKEEPING                      |
|                                                                               |
|   [ LOCAL PRE-COMMIT GATE ]                [ REMOTE OUT-OF-BAND CI GATE ]     |
|   .git/hooks/pre-commit                    .github/workflows/integrity.yml    |
|   scripts/verify_integrity.py              GitHub Actions Virtual Runner      |
|     * tests/golden/ unchanged?               * Verifier script rerun          |
|     * Zero [DEBUG] tags in source?           * Semgrep superlative scan       |
|     * Claims have test receipts?             * Golden branch protection       |
+-------------------------------------------------------------------------------+
```

---

## 2. Verification Boundaries & Actuator Containment

To prevent autonomous agents from compromising test harnesses or scattering changes across unrelated modules, MinusCorrect partitions the repository into three distinct mutability zones.

### Visual Boundary Model

```
                          TASK EXECUTION SCOPE
 
            PERMITTED MUTATIONS (Agent Read / Write)
            +-------------------------------------------------------+
            | tests/unit/                                           |
            | - Developer test helpers, unit tests, and mocks       |
            | - Mutable during implementation                       |
            | - Used for TDD scratchpad exploration                 |
            +-------------------------------------------------------+
            | src/<target_module>.py (Bounded Actuator)             |
            | - Implementation file targeted for bugfix or feature  |
            | - Blast radius strictly confined to this file         |
            +-------------------------------------------------------+
 
                                    ||
                 VERIFIED BY HARNESS || (Execution Feedback)
                                    \/
 
            FORBIDDEN MUTATIONS (Agent Strictly Read-Only)
            +-------------------------------------------------------+
            | tests/golden/ (Immutable Acceptance Contracts)        |
            | - Bug regression reproducers                          |
            | - Core protocol & API specifications                  |
            | - NEVER modified or loosened to make a run pass       |
            +-------------------------------------------------------+
```

### Boundary Definitions:
- **`tests/golden/` (Immutable Acceptance Contracts):** Represents the non-negotiable specification. When an agent is dispatched to fix a bug or implement a feature, files in this directory are frozen. Any modification aborts the pre-commit hook unless explicitly authorized by a human using `ALLOW_GOLDEN_EDIT=1`.
- **`tests/unit/` (Mutable Working Suite):** Open sandbox where agents may add, modify, or refactor unit tests, component tests, and test helpers to support their implementation workflow.
- **Target Actuator (`src/`):** The single file or tightly bounded component undergoing mutation. Agents are instructed to read widely across the project to understand context, but write strictly to the target file.

---

## 3. Closed-Loop Solver & Circuit Breaker State Machine

Agents operate within a cybernetic control loop modeled after deterministic state machines. Retries are capped at 4 iterations to prevent token burn and hallucination loops.

### Visual State Transition Flowchart

```
                      [ USER TASK / ISSUE REPORT ]
                                   |
                                   v
                      [ PHASE 1: SPEC AUTHORING ]
                 Agent authors test in tests/golden/
                                   |
                                   v
                     [ FREEZE ACCEPTANCE CONTRACT ]
                     tests/golden/ locked READ-ONLY
                                   |
                                   v
                      [ PHASE 2: SOLVER CYCLE ]
                                   |
                   +--------------->+
                   |                |
                   |                v
                   |    [ AGENT GENERATES PATCH ]
                   |    (Mutates target file only)
                   |                |
                   |                v
                   |       [ RUN TEST HARNESS ]
                   |       (pytest / test runner)
                   |                |
                   |        +-------+-------+
                   |        |               |
                   |     (Pass)          (Fail)
                   |        |               |
                   |        v               v
                   |  [ CLEANUP ]     [ HASH ERROR OUTPUT ]
                   |  Remove debug    Normalize stderr/stdout
                   |        |               |
                   |        v         +-----+-----+-----+
                   |  [ PRE-COMMIT ]  |           |     |
                   |  Gate passes?    |           |     |
                   |    +---+---+  (Iter 1-2) (Iter 3) (Iter 4)
                   |    |       |     |           |     |
                   |  (Yes)   (No)    |     [Identical] |
                   |    |       |     |     Error Hash? |
                   |    v       v     |       +---+     |
                   | [COMMIT] [ABORT] |       |   |     |
                   |                  |     (Yes) |     |
                   |                  |       |   |     |
                   |                  |       v   v     |
                   |                  |   [ INJECT ]    |
                   |                  |   [ [DEBUG] ]   |
                   |                  |   [ TRACES ]    |
                   |                  |       |         |
                   |                  +-------+         v
                   |                              [ HARD ABORT ]
                   |                           Halt token burn;
                   |                           Report invariant
                   |                           failure to human
                   +------------------------------------+
```

### State Progression Details:
1. **Phase 1: Spec Authoring:** Before writing production code, a reproduction or acceptance test is authored in `tests/golden/`.
2. **Phase 2: Solver Iteration 1–2:** The agent receives test output and attempts algorithmic fixes.
3. **Phase 2: Solver Iteration 3 (Observability Injection):** If consecutive runs produce identical error hashes, the agent must inject temporary `[DEBUG]` traces to inspect variable state at runtime.
4. **Phase 2: Solver Iteration 4 (Circuit Breaker Hard Abort):** If tests continue failing, the agent immediately stops. It must report:
   - The specific failing invariant.
   - Observed runtime values from `[DEBUG]` logs.
   - The architectural ambiguity requiring human clarification.
5. **Scaffolding Cleanup:** Prior to committing, all `[DEBUG]` traces must be cleanly removed.

---

## 4. The Two-Category Docstring & Claim Verification Engine

Docstrings and comments cost nothing to generate, leading agents to author authoritative-sounding but completely fabricated claims. MinusCorrect divides all code documentation into two strictly audited categories.

### Visual Claim Taxonomy

```
                        SOURCE CODE DOCSTRINGS & COMMENTS
                                        |
                 +----------------------+----------------------+
                 |                                             |
                 v                                             v
     CATEGORY 1: OPERATIONAL GUARANTEES            CATEGORY 2: CONTEXTUAL RATIONALE
     ("The What: Complexity, Concurrency")         ("The Why: Trade-offs, Quirks")
                 |                                             |
     Examples:                                     Examples:
     * "O(1) lookup complexity"                    * "# Rationale: Trade memory for speed"
     * "Thread-safe concurrent cache"              * "# Workaround: WebKit bug #10842"
     * "Idempotent event dispatcher"               * "# Assumption: Payload is UTF-8"
                 |                                             |
                 v                                             v
     +---------------------------+                 +---------------------------+
     |   REQUIREMENT: RECEIPT    |                 |   REQUIREMENT: TAGGING    |
     | Must include verification |                 | Must use structured tag:  |
     | receipt linking to test:  |                 | # Rationale:              |
     | # verifies: tests/golden/ |                 | # Workaround:             |
     |                           |                 | # Assumption:             |
     +-------------+-------------+                 +-------------+-------------+
                   |                                             |
                   v                                             v
     [ AST / SEMGREP STATIC AUDIT ]                [ CODE CONTEXT PRESERVATION ]
     - Banned superlatives stripped                - Explainable teleology
     - Unverified claims rejected                  - Human audit trail
```

### Audit Rules:
- **Category 1 (Operational Guarantees):** Any statement claiming algorithmic complexity (`O(1)`), concurrency (`thread-safe`), purity (`idempotent`), or dependency footprint (`zero-dependency`) MUST be accompanied by an executable test receipt (e.g. `# verifies: tests/golden/test_concurrency.py`). Marketing superlatives (`universal`, `bulletproof`, `blazing fast`) are banned outright.
- **Category 2 (Contextual Rationale):** Captures business decisions, vendor quirks, and external constraints. Must use structured tags (`# Rationale:`, `# Workaround:`, `# Assumption:`).

---

## 5. Dual-Gate Gatekeeping Architecture

Enforcement does not rely on voluntary agent compliance. The verification pipeline operates across two decoupled gates: local pre-commit inspection and remote out-of-band CI verification.

### Visual Gatekeeping Pipeline

```
                                 STAGED CODE COMMIT
                                          |
                                          v
+---------------------------------------------------------------------------------------+
| GATE 1: LOCAL PRE-COMMIT VERIFIER (.git/hooks/pre-commit -> scripts/verify_integrity.py)
|
|   Check 1: Golden Test Immutability
|            git diff --cached tests/golden/ == 0?
|            [NO]  --> ALLOW_GOLDEN_EDIT=1 present?
|                      [NO]  --> REJECT COMMIT (Cannot alter golden spec)
|                      [YES] --> PASS (Human intentional override)
|            [YES] --> PASS
|
|   Check 2: Ephemeral Scaffolding Leakage
|            git diff --cached source files contain '[DEBUG]' or '__DEBUG__'?
|            [YES] --> REJECT COMMIT (Must clean temporary debug tags)
|            [NO]  --> PASS
|
|   Check 3: Operational Claim Receipts
|            Docstring claims have matching '# verifies: tests/golden/...'?
|            [NO]  --> WARN / REJECT (Unsubstantiated operational guarantee)
|            [YES] --> PASS
+-------------------------------------------+-------------------------------------------+
                                            | Local commit created
                                            v
                                     [ GIT PUSH ]
                                            |
                                            v
+---------------------------------------------------------------------------------------+
| GATE 2: OUT-OF-BAND CI VERIFICATION (.github/workflows/integrity.yml)
|
|   Environment: Isolated GitHub Actions Runner (Clean virtual machine)
|
|   Step 1: Fresh Checkout of PR / Main Branch
|   Step 2: Python Environment Setup
|   Step 3: Execute scripts/verify_integrity.py
|   Step 4: Execute Semgrep Static Claim Linter (.semgrep/unverified-claims.yml)
|   Step 5: Gated Merge Enforcement (Branch Protection blocks unverified PRs)
+---------------------------------------------------------------------------------------+
                                            |
                                            v
                                  [ PROTECTED MAIN BRANCH ]
```

---

## 6. Defensive Guardrails & Threat Model Matrix

Autonomous agents with local tool execution access introduce unique failure patterns. MinusCorrect mitigates each threat at the architectural level:

| Threat Vector | Attack Mechanism | Systemic Mitigation |
| :--- | :--- | :--- |
| **Specification Gaming** | Agent loosens or removes test assertions (`assert res == 5` $\to$ `assert res is not None`) to manufacture a passing run. | `GoldenBoundaryGate` blocks all commits touching `tests/golden/` unless signed by human override flag `ALLOW_GOLDEN_EDIT=1`. |
| **Downstream Symptom Masking** | Agent wraps failing routines in blanket `try/except: pass` and returns empty mock data. | Invariant 1 (*Resolve at Source*) forbids synthetic fallbacks. Golden tests enforce strict non-empty, valid payloads. |
| **Synthetic Delay Injection** | Agent bypasses race conditions by inserting arbitrary `time.sleep(0.5)` calls. | Invariant 3 (*No Synthetic Constants*) bans artificial delays. Synchronization must derive from mutexes, events, or queues. |
| **Aspirational Docstrings** | Agent authors misleading claims ("thread-safe", "O(1)") without implementing thread safety. | Two-Category Standard and Semgrep audit rule flag claims lacking automated `# verifies:` receipts. |
| **Context Window Exhaustion** | Agent spins across 20+ iterations repeatedly analyzing identical test failure traces. | 4-iteration circuit breaker hashes error output and terminates the loop with diagnostic escalation. |
| **Watcher Paradox (In-Band Tampering)** | Agent with write access edits `scripts/verify_integrity.py` to bypass local pre-commit checks. | Bifurcated gatekeeping: local hooks provide rapid developer feedback, while out-of-band GitHub Actions CI runs in clean, isolated runners before code can merge. |
