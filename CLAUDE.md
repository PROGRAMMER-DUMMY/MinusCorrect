# Claude Code Repository Configuration

## Systemic Integrity & Verification Rules
Adhere strictly to `.agent-rules/systemic-integrity.md` for all tasks, bug fixes, and code generation.

### Key Operational Invariants
- **Evidence Over Labels**: Docstrings and comments are unverified claims, not ground truth. Never accept docstrings as fact without verifying against AST structures, types, and passing tests.
- **Docstring Standards**:
  - Operational claims (`O(1)`, `thread-safe`, `idempotent`) require explicit test links (`# verifies: tests/...`).
  - Contextual comments must use structured prefixes: `# Rationale:`, `# Workaround: [issue]`, or `# Assumption:`.
  - Purge unverified marketing superlatives (`universal`, `bulletproof`, `zero-dependency`).
- **Golden Test Protection**: Files in `tests/golden/` represent the specification and are strictly immutable during implementation tasks.
- **Bounded Actuators**: Inspect types and schemas widely, but isolate code mutations strictly to targeted modules.
- **Iteration Ceiling**: Maximum 4 test-fix iterations. If an identical error occurs twice, inject temporary `[DEBUG]` traces, observe runtime state, and clean them up before finalizing.
