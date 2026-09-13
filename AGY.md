# Antigravity (AGY) Repository Configuration

## Systemic Integrity & Verification Rules
Adhere strictly to `.agent-rules/systemic-integrity.md` for all tasks, bug fixes, and code generation.

### Operational Directives
- **Evidence Over Labels**: Treat comments and docstrings as unauthenticated hypotheses; reconstruct actual intent from call sites and behavioral contracts.
- **Docstring Standards**:
  - Operational claims (`O(1)`, `thread-safe`, `idempotent`) require explicit test links (`# verifies: tests/...`).
  - Contextual comments must use structured prefixes: `# Rationale:`, `# Workaround: [issue]`, or `# Assumption:`.
  - Purge unverified marketing superlatives (`universal`, `bulletproof`, `zero-dependency`).
- **Golden Test Protection**: Treat files in `tests/golden/` as read-only specification contracts.
- **Root-Cause Resolution**: Fix issues at the producer source; never swallow exceptions or insert synthetic defaults downstream.
- **Bounded Iteration**: Limit iterative test-repair loops to 4 runs. Escalate with runtime diagnostics if stuck.
