---
name: ask-matt
description: "Matt Pocock's Ask-Matt execution flow: decomposes any feature request, refactor, or bug fix into an Architectural Spec, a DAG of Tracer-Bullet Tickets with explicit protected boundaries, domain specialist agent assignments, and TDD verification criteria for supervised MinusCorrect execution. Triggers: '/ask-matt', 'ask-matt', 'spec to tickets', 'tracer bullets', 'create implementation plan'."
---

# Ask-Matt Execution Protocol

Adapted from **Matt Pocock's Spec-to-Tickets methodology**, this skill transforms high-level ideas, bug reports, or LLM Council verdicts into an executable, dependency-ordered DAG of tracer-bullet tickets executed under MinusCorrect supervision.

```
Idea / Bug / Verdict
         │
         ▼
┌───────────────────┐
│ 1. /to-spec       │  Architectural Spec (Invariants, Data Contracts, Protected Boundaries)
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│ 2. /to-tickets    │  Tracer-Bullet Tickets (Vertical slices, Dependencies, Blast Radius)
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│ 3. Dispatch Agents│  Domain Specialists (Systems, Security, Isolation, Verification Lead)
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│ 4. MinusCorrect   │  Supervised Execution (Ephemeral Worktree, Isolate-Env, 4-Loop Ceiling)
└───────────────────┘
```

---

## The 4 Core Phases

### Phase 1: Architectural Specification (`/to-spec`)
Before creating tickets or writing code, specify:
1. **Core Invariant**: The fundamental behavior or contract that must hold true.
2. **Data Contracts**: Input/output schemas, API boundaries, and serialization formats.
3. **Protected Boundaries (Out-of-Scope)**:
   - Files and directories that MUST NOT be touched (e.g., `tests/golden/`, legacy contracts, unrelated modules).
4. **Failure Modes**: How the system fails gracefully (timeouts, circuit breakers, fallbacks).

### Phase 2: Tracer-Bullet Tickets (`/to-tickets`)
Decompose the spec into minimal, vertical slices ("tracer bullets") that touch every layer from test to implementation:

Each ticket MUST follow this exact schema:

```markdown
### TICKET-<ID>: <Title>
- **Role**: <Domain Specialist Persona>
- **Objective**: <Single, crisp behavioral outcome>
- **Target Files (In-Scope)**:
  - `<file_path_1>`
  - `<file_path_2>`
- **Protected Boundaries (Out-of-Scope)**:
  - `tests/golden/*` (Immutable)
  - `<unrelated_files>`
- **Dependencies**: `Blocked By: [TICKET-XX] | Blocks: [TICKET-YY]`
- **TDD Contract**:
  - Command: `minuscorrect run --worktree --isolate-env -- pytest <test_path>`
  - Pass Condition: All assertions green, zero residual `[DEBUG]` scaffolding.
```

### Phase 3: Domain Specialist Agent Mapping
Assign each ticket to a specialized agent role rather than a generic coder:
- **Process Isolation SRE**: For sandboxing, worktrees, signal handlers, subprocessing.
- **Security & Policy Auditor**: For credential scrubbers, payload defangers, injection gates.
- **Distributed Systems Engineer**: For concurrency, circuit breakers, backoff, webhooks.
- **TDD & Verification Lead**: For golden contracts, doctests, integrity verifiers.

### Phase 4: Supervised MinusCorrect Execution
Execute unblocked tickets with the MinusCorrect CLI supervisor:

```bash
# Execute within ephemeral worktree with credential isolation and 4-iteration ceiling
minuscorrect run --worktree --isolate-env --target <target_file> -- pytest <test_file>
```

After all tickets pass:
```bash
# Verify systemic integrity and auto-clean scaffolding
minuscorrect verify --fix --strict
```
