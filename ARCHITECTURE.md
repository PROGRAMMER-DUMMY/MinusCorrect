# MinusCorrect: System Architecture

This document specifies the technical architecture, execution topology, state transition models, AST verification engines, gatekeeping pipelines, and data schemas of **MinusCorrect**.

---

## 1. High-Level System Architecture

MinusCorrect serves as the deterministic systemic integrity and anti-shortcut verification engine for autonomous coding agents operating across modern repositories.

### Visual Architecture Topology

```
+-------------------------------------------------------------------------------------------------------+
|                                      AUTONOMOUS AGENT RUNTIMES                                        |
|                                                                                                       |
|  +--------------------+   +--------------------+   +--------------------+   +----------------------+  |
|  |     Claude Code    |   | Google Antigravity |   |    OpenAI Codex    |   |      Cursor IDE      |  |
|  |    (CLI Agent)     |   |   (Engine Agent)   |   |   (Codex Engine)   |   |     (Editor Agent)   |  |
|  +---------+----------+   +---------+----------+   +---------+----------+   +----------+-----------+  |
|            |                        |                        |                         |              |
+------------|------------------------|------------------------|-------------------------|--------------+
             |                        |                        |                         |
             | [Task Dispatch / Tool] | [Session Prompt]       | [Patch Proposal]        | [File Edit]
             v                        v                        v                         v
+-------------------------------------------------------------------------------------------------------+
|                                     MINUSCORRECT INGRESS BOUNDARY                                     |
|                                                                                                       |
|       +-----------------------------------+             +-------------------------------------+       |
|       |             AGENTS.md             |             |        Native Tool Bootstraps       |       |
|       |    (Universal Root Standard)      |             |   .cursorrules | .codex/instructions|       |
|       +-----------------+-----------------+             +------------------+------------------+       |
|                         |                                                  |                          |
|                         +------------------------+-------------------------+                          |
|                                                  |                                                    |
+--------------------------------------------------|----------------------------------------------------+
                                                   v
+-------------------------------------------------------------------------------------------------------+
|                                      ACTUATOR & REASONING CONTROL                                     |
|                                                                                                       |
|  +------------------------+      +--------------------------+      +-------------------------------+  |
|  |   Target Actuator File | ---> |  Immutable Golden Suite  | ---> |   Ephemeral Scaffolding       |  |
|  |   (Single File Mutate) |      |  (tests/golden/ Spec)    |      |   (Iteration 3 [DEBUG] Traces)|  |
|  +------------------------+      +--------------------------+      +---------------+---------------+  |
|                                                                                    |                  |
+------------------------------------------------------------------------------------|------------------+
                                                                                     v
+-------------------------------------------------------------------------------------------------------+
|                                      VERIFICATION & GATEKEEPING                                       |
|                                                                                                       |
|  +------------------------------------+             +-----------------------------------------+       |
|  |    Pre-Commit Verifier Hook        |             |       Out-of-Band CI Pipeline           |       |
|  |    scripts/verify_integrity.py     |             |       .github/workflows/integrity.yml   |       |
|  +-----------------+------------------+             +--------------------+--------------------+       |
|                    |                                                     |                            |
|                    v                                                     v                            |
|  +------------------------------------+             +-----------------------------------------+       |
|  |   Golden Contract Mutation Gate    |             |      Static AST & Semgrep Claim Audit   |       |
|  |   (ALLOW_GOLDEN_EDIT=1 Override)   |             |      (.semgrep/unverified-claims.yml)   |       |
|  +------------------------------------+             +-----------------------------------------+       |
+-------------------------------------------------------------------------------------------------------+
```

---

## 2. Solver Lifecycle & State Transitions

Tasks progress through a deterministic finite-state machine governed by the 4-iteration circuit breaker. Silent drops, unhandled states, and concealed policy rejections are disallowed by design.

### Visual State Transition Flowchart

```
                 [ TASK_INITIATED ]
                        |
                        v
               [ PHASE 1: SPEC FREEZE ]
                        |
            (Reproduction Test Written)
                        |
                        v
               [ GOLDEN CONTRACT FROZEN ]
                        |
                        v
            +--> [ PATCH_SYNTHESIS ] (Bounded Actuator: 1 file)
            |           |
            |           v
            |    [ TEST EXECUTION ] (pytest / npm test)
            |           |
            |     +-----+-----+
            |     |           |
            |  (Failed)    (Passed)
            |     |           |
            |     v           v
            |  [ HASH ERROR ] [ SCAFFOLDING CHECK ]
            |     |           |
            |     +----+------+-----+
            |          |            |
            |    (Iter < 3)    (Leftover [DEBUG])
            |          |            |
            |     +----+            v
            |     |           [ STRIP DEBUG ]
            |     |                 |
            |     |                 v
            |     |           [ PRE-COMMIT GATE ]
            |     |                 |
            |  (Iter == 3)    +-----+-----+
            |     |           |           |
            |     v       (Passed)    (Rejected)
            |  [ INJECT ]     |           |
            |  [ [DEBUG]]     v           v
            |     |       [ COMMITTED ] [ ABORT_COMMIT ]
            |     |
            |  (Iter == 4: Identical Failure)
            |     |
            |     v
            +-- [ HARD_ABORT & ESCALATE ]
```

### State Definitions:
- `PHASE 1: SPEC FREEZE`: Acceptance criteria and reproduction tests are authored in `tests/golden/`. Once validated, this suite is declared strictly read-only.
- `PATCH_SYNTHESIS`: The agent mutates only the targeted source implementation file. Mutating other files or test specs is rejected.
- `TEST_EXECUTION`: The local test harness executes against the immutable golden contract.
- `HASH_ERROR`: Normalizes `stderr` and `stdout` into a SHA-256 fingerprint to detect repeating failure cycles.
- `INJECT [DEBUG]`: On iteration 3, if consecutive error hashes match, the agent is forced to inject runtime variable inspection scaffolding (`[DEBUG]`).
- `HARD_ABORT`: On iteration 4, if tests still fail, the circuit breaker trips. The agent must abort, report the failing invariant, and dump observed variable states.
- `SCAFFOLDING_CHECK`: Verifies that zero temporary `[DEBUG]` traces remain in staged diffs.
- `PRE-COMMIT GATE`: Deterministic verification script inspecting path boundaries, docstring claim receipts, and test immutability.
- `COMMITTED`: Clean, verified code changes permitted into source tree.

---

## 3. Epistemic Debugging & Circuit Breaker Trace Board

MinusCorrect halts context window exhaustion and hallucination loops using a deterministic 4-iteration trace board. Below is the step-by-step progression of an agent resolving a defect under systemic integrity constraints.

### Visual Trace Board

```
Iteration 0: Problem Formulation & Spec Freeze
---------------------------------------------------------------------------------------------
Human/Agent  -> Authors reproduction test in tests/golden/test_cache_lru.py
Harness Exec -> Fails with AssertionError: Key 'session_99' not evicted under load
MinusCorrect -> Freezes tests/golden/ (Marked IMMUTABLE_CONTRACT)
Agent Scope  -> Bounded to src/cache.py (TARGET_ACTUATOR)


Iteration 1: Algorithmic Patch Attempt
---------------------------------------------------------------------------------------------
Agent Patch  -> Updates eviction pointer logic in src/cache.py
Harness Exec -> Fails with DeadlockTimeout: Lock acquisition exceeded 5.0s
Error Hash   -> SHA256("DeadlockTimeout: Lock acquisition...") = e4a19b22
State Action -> LoopStatus.ACTIVE (Iteration 1/4 recorded)


Iteration 2: Secondary Algorithmic Patch
---------------------------------------------------------------------------------------------
Agent Patch  -> Refactors lock acquisition order
Harness Exec -> Fails with DeadlockTimeout: Lock acquisition exceeded 5.0s
Error Hash   -> SHA256("DeadlockTimeout: Lock acquisition...") = e4a19b22
State Action -> Detected identical consecutive error hash: e4a19b22 == e4a19b22
State Action -> Transition to LoopStatus.SCAFFOLDING_REQUIRED (Prepare Iteration 3)


Iteration 3: Epistemic Scaffolding Injection
---------------------------------------------------------------------------------------------
Agent Patch  -> Injects temporary runtime traces:
                print(f"[DEBUG] Acquired mutex A in thread {tid}")
                print(f"[DEBUG] Waiting for mutex B in thread {tid}")
Harness Exec -> Fails with DeadlockTimeout: Lock acquisition exceeded 5.0s
Runtime Log  -> [DEBUG] Thread 1 holds Mutex A, waiting on Mutex B
                [DEBUG] Thread 2 holds Mutex B, waiting on Mutex A (Circular Deadlock Identified)
Agent Action -> Identifies inverted lock hierarchy between EvictionList and KeyStore
Agent Patch  -> Replaces dual locks with unified reentrant ReadWriteLock. Strips all [DEBUG] lines.


Iteration 4: Verification & Convergence
---------------------------------------------------------------------------------------------
Harness Exec -> All 42 tests in tests/golden/ pass in 0.08s
MinusCorrect -> Checks for residual [DEBUG] tags: 0 found
MinusCorrect -> Checks docstrings: Found "O(1) thread-safe cache"
                Audits receipt: "# verifies: tests/golden/test_cache_lru.py" verified!
State Action -> Transition to LoopStatus.CONVERGED (Clean exit approved)
```

---

## 4. Contract Data Structures & Schema Layout

MinusCorrect models its governance rules through four formal relational and AST data schemas:

### Visual Schema Layout

```
+---------------------------------------------------------------------------------------------------+
|                                        EXECUTION_CONTEXT                                          |
+--------------------+------------------------------------------------------------------------------+
| session_id (PK)    | string (e.g. "sess_20260914_99a8")                                           |
| target_file        | path ("src/cache.py")                                                        |
| golden_suite       | path ("tests/golden/test_cache_lru.py")                                      |
| max_iterations     | integer (Default: 4)                                                         |
| current_iteration  | integer (0 to 4)                                                             |
| breaker_status     | string ("ACTIVE", "SCAFFOLDING_REQUIRED", "CONVERGED", "HARD_ABORT")         |
| created_at         | ISO 8601 Timestamp                                                           |
+--------------------+------------------------------------------------------------------------------+
         |
         | 1-to-Many
         v
+---------------------------------------------------------------------------------------------------+
|                                         ITERATION_TRACE                                           |
+--------------------+------------------------------------------------------------------------------+
| trace_id (PK)      | string (e.g. "tr_001_iter1")                                                 |
| session_id (FK)    | string -> EXECUTION_CONTEXT(session_id)                                      |
| iteration_number   | integer (1, 2, 3, 4)                                                         |
| patch_diff         | text (Unified git diff applied to target_file)                               |
| exit_code          | integer (0 for pass, non-zero for test failure)                              |
| error_hash         | string (SHA-256 fingerprint of stderr + stdout)                              |
| stdout             | text                                                                         |
| stderr             | text                                                                         |
| scaffolding_active | boolean (True if [DEBUG] traces were injected)                              |
| timestamp          | ISO 8601 Timestamp                                                           |
+--------------------+------------------------------------------------------------------------------+
         |
         | 1-to-Many
         v
+---------------------------------------------------------------------------------------------------+
|                                       OPERATIONAL_CLAIMS                                          |
+--------------------+------------------------------------------------------------------------------+
| claim_id (PK)      | string ("claim_cache_thread_safe")                                           |
| session_id (FK)    | string -> EXECUTION_CONTEXT(session_id)                                      |
| symbol_name        | string ("LRUCache.get")                                                      |
| file_path          | path ("src/cache.py")                                                        |
| line_number        | integer (42)                                                                 |
| claim_category     | string ("OPERATIONAL_GUARANTEE", "CONTEXTUAL_RATIONALE")                     |
| declared_attribute | string ("thread-safe", "O(1)", "idempotent")                                 |
| receipt_target     | path ("tests/golden/test_cache_lru.py")                                      |
| receipt_verified   | boolean (True if verified by test harness)                                   |
+--------------------+------------------------------------------------------------------------------+

+---------------------------------------------------------------------------------------------------+
|                                      GATEKEEPER_AUDIT_LOG                                         |
+--------------------+------------------------------------------------------------------------------+
| id (PK)            | integer (Monotonic autoincrement)                                            |
| timestamp          | ISO 8601 Timestamp                                                           |
| commit_sha         | string ("ac70cb5...")                                                        |
| gate_name          | string ("GoldenBoundaryGate", "ScaffoldingGate", "ClaimReceiptGate")          |
| evaluation_result  | string ("PASSED", "REJECTED")                                                |
| override_flag      | string ("ALLOW_GOLDEN_EDIT=1" or null)                                       |
| violations         | JSON (List of file paths, missing receipts, or detected [DEBUG] tags)       |
+--------------------+------------------------------------------------------------------------------+
```

---

## 5. Defensive Guardrails & Blast Radius Containment

1. **Golden Contract Immutability Boundary:**
   `GoldenBoundaryGate` monitors `git diff --cached` for any modifications to `tests/golden/`. If changes are staged without `ALLOW_GOLDEN_EDIT=1`, the commit is aborted instantly, preventing agents from altering test assertions to manufacture passing runs.
2. **Ephemeral Scaffolding Sanitization:**
   `ScaffoldingSanitizationGate` inspects staged source code files for residual `[DEBUG]` logs or `__DEBUG__` traces. Any attempt to commit diagnostic scaffolding is rejected before touching the commit history.
3. **AST Claim Audit and Superlative Ban:**
   Static inspection via Python's Abstract Syntax Tree (`ast.NodeVisitor`) and Semgrep parses all docstrings in modified modules. Marketing superlatives ("universal", "bulletproof", "blazing fast") are banned, and Category 1 operational guarantees (`O(1)`, `thread-safe`, `idempotent`) must contain explicit `# verifies: <path>` test receipts.
4. **Finite-State Circuit Breaker:**
   `CircuitBreakerState` tracks the error hash history of each test execution cycle. If two consecutive runs produce identical error signatures, the agent is forced into epistemic debug injection. If the test still fails at iteration 4, the loop immediately hard-aborts to prevent token-burning hallucination spirals.
5. **Out-of-Band CI Verification:**
   To solve the Watcher Paradox (where an in-band agent with write access could tamper with local verification scripts), all integrity checks are executed out-of-band in GitHub Actions CI (`.github/workflows/integrity.yml`) on clean, isolated virtual environments before code can merge into protected branches.
