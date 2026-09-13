# Systemic Integrity & Anti-Shortcut Engineering Specification

**Target Audience:** Autonomous Coding Agents (Claude Code, Antigravity/Agy, OpenAI Codex, Cursor) and Human Engineers.

---

## 0. Intent Reconstruction: Evidence Over Labels

Before proposing or modifying any code:
* **Code is physics; documentation is claims.** Comments and docstrings cost nothing to write and are ignored by runtimes and compilers. They can be wrong by accident (stale, aspirational) or wrong by design (marketing superlatives, LLM hallucinations).
* **Treat self-reported text as hypotheses to verify, never ground truth.** Downstream agents must not accept docstrings as fact without behavioral verification.
* **Derive real intent from behavioral evidence:** how functions are called across the codebase, what contracts sibling components enforce, and the actual shape of production inputs.
* **Verify behaviorally:** Construct at least one adversarial input or trace through unexercised code paths to verify whether the implementation matches its documented contract.

---

## 1. Core Invariants

1. **Resolve at Source, Never Mask at Consumer:**
   * Trace invalid states, missing keys, or malformed data back to the component producing them.
   * *Strictly Prohibited:* Swallowing exceptions (`except Exception: pass`, empty `catch {}`), optional chaining fallbacks with synthetic dummy defaults, or silent `None`/`null` bypasses.

2. **Test Immutability During Implementation:**
   * Acceptance tests in `tests/golden/` represent the specification and are **strictly read-only**.
   * *Strictly Prohibited:* Modifying, commenting out, or loosening assertions in `tests/golden/` to make a run pass. Production code adapts to the specification, never the reverse.

3. **No Synthetic Invariants (Magic Constants):**
   * Never insert arbitrary constants (e.g., fixed `sleep()` delays to bypass race conditions, hardcoded batch sizes, artificial confidence clamps like `clamp(val, 0, 1)`).
   * Synchronization must derive from real system primitives (locks, events, promises, queues) or mathematical invariants.

4. **Held-Out Stress Verification:**
   * Never validate solely against the failing test or example payload that prompted the fix.
   * Verify proposed logic against at least one unobserved condition: empty inputs, extreme boundary sizes, concurrent execution, or malformed external inputs.

5. **Bounded Actuator, Wide Observer:**
   * Read widely across imported types, contracts, and sibling implementations to understand cross-module context.
   * Restrict write mutations strictly to the targeted implementation file. Do not perform uncoordinated multi-file edits without explicit architectural scope.

6. **No False Generality or Superlatives:**
   * Prohibit unverified marketing superlatives in docstrings ("universal", "domain-agnostic", "zero-dependency", "bulletproof", "blazing fast").
   * If true generality is out of scope, explicitly document the bounded operating scope instead of claiming unbounded behavior.

---

## 2. Docstring & Comment Auditing (The Two-Category Standard)

Comments and docstrings must strictly adhere to the separation between **Operational Guarantees** and **Contextual Rationale**:

### Category 1: Operational Guarantees ("The What")
Claims regarding algorithmic complexity, concurrency guarantees, purity, or behavioral scope.
* **Requirements:**
  1. **Receipts Required:** Any claim of `thread-safe`, `O(1)`, `idempotent`, or `zero-dependency` MUST link directly to an automated verification test or benchmark (e.g., `# verifies: tests/golden/test_concurrency.py`).
  2. **Executable Examples:** All code examples in docstrings must be executable and pass via doctests (`pytest --doctest-modules`).
  3. **Purge Unverified Claims:** If a claim cannot be verified by an automated test or type checker, strip the claim immediately.

### Category 2: Contextual Rationale ("The Why")
Explanations of business trade-offs, historical context, hardware quirks, or external bug workarounds that cannot be captured by automated tests alone.
* **Requirements:**
  1. Must be explicitly tagged with context prefixes:
     * `# Rationale: <business reason or architectural trade-off>`
     * `# Workaround: <vendor/browser quirk, issue link or ticket ID>`
     * `# Assumption: <external system boundary or invariant>`
  2. Never use rationale comments to justify silent error swallowing or masked failures.

---

## 3. Closed-Loop Execution Protocol

When executing bug fixes or feature additions, adhere to this 2-phase loop:

### Phase 1: Spec & Test Authoring (Separation of Powers)
* When given a requirement or bug report, first author a reproducing test in `tests/golden/` (or `tests/unit/` for local unit tests).
* Include happy path, edge cases, and invalid inputs.
* Do not write production code until the test accurately captures the expected failure or specification.

### Phase 2: Bounded Implementation Solver
* Supply the test file as **read-only context**.
* Mutate only the target implementation file.
* Execute the test command (`pytest`, `npm test`, etc.) and feed stderr/stdout back into the prompt.
* **Max 4 Iterations:**
  * **Iteration 1–2:** Apply algorithmic fixes based on compiler/test output.
  * **Iteration 3 (Identical Error Hash):** Inject temporary `[DEBUG]` logs to observe runtime state. Re-run test.
  * **Iteration 4:** If still failing, **hard abort**. Do not burn tokens. Report:
    1. The specific invariant failing.
    2. Observed runtime values from `[DEBUG]` logs.
    3. The architectural blocker requiring human clarification.
* **Scaffolding Cleanup:** All temporary `[DEBUG]` statements must be removed before reporting task completion.

---

## 4. Delivery & Review Structure

For routine bug fixes and code generation:
1. **Root Cause:** 1–2 sentences explaining why the invariant failed at the source.
2. **General Mechanism:** How the fix addresses the problem class rather than just the isolated test case.
3. **Verification Evidence:** Confirmation that tests in `tests/golden/` pass, unobserved boundary cases were evaluated, and any docstring claims have verified receipts.
4. **Declared Boundaries:** Explicit disclosure of any known limitations, trade-offs, or tagged `# Rationale:` items.
