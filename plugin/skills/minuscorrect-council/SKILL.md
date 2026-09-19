---
name: minuscorrect-council
description: Multi-perspective LLM Council and Ask-Matt orchestration protocol for autonomous coding agents. Use for pre-execution architectural decisions, high-risk bug triage, pressure-testing plans through 5 independent thinking styles (Contrarian, First Principles, Expansionist, Outsider, Executor), and translating verdicts into domain-specialist multi-agent DAG tickets for supervised MinusCorrect execution.
---

# MinusCorrect Council & Ask-Matt Orchestrator Skill

A complete end-to-end autonomous engineering protocol combining **Andrej Karpathy's multi-perspective deliberation** with **Matt Pocock's Ask-Matt execution flow** (`/ask-matt`: Idea -> Spec -> Tracer-Bullet Tickets -> Domain Specialists -> Supervised TDD Implementation -> Review).

When facing architectural decisions, production crash triage, or complex refactors, this skill prevents cognitive tunnel-vision and orchestrates multi-agent implementation under MinusCorrect's supervised runtime containment.

---

## When to Activate

- Triage of high-severity production incidents (`INCIDENT-RCA`)
- Architectural decisions where being wrong breaks system invariants
- Complex refactors with unknown blast radius
- Pre-execution plan pressure-testing before touching production code
- Coordinating multi-agent swarms with domain-specialist roles

---

## Phase 1: The Five Council Thinking Lenses

1. **The Contrarian**: Actively looks for what will break, regressions, AST blast-radius hazards, and unintended side-effects.
2. **The First Principles Thinker**: Strips away surface symptoms; asks what core invariant is being violated.
3. **The Expansionist**: Identifies systemic leverage and long-term architectural durability.
4. **The Outsider**: Provides zero-context sanity checks; catches over-engineering, buzzwords, and developer ergonomics traps.
5. **The Executor**: Cuts scope; formulates the minimal, surgical Monday-morning patch plan.

---

## Phase 2: Deliberation & Peer-Review Workflow

```
[Agent Query / Incident Triage]
              |
              v
+-------------------------------------------------------+
| Step 1: Convene 5 Parallel Advisors                   |
| (Contrarian, First Principles, Expansionist, Outsider, |
|  Executor - each producing independent 150-300 words) |
+---------------------------+---------------------------+
                            |
                            v
+-------------------------------------------------------+
| Step 2: Anonymized Peer Review                        |
| (Evaluate Responses A-E: Strongest, Blind Spot, Missed)|
+---------------------------+---------------------------+
                            |
                            v
+-------------------------------------------------------+
| Step 3: Chairman Synthesis                            |
| (Agreements, Clashes, Caught Blind Spots, Verdict,     |
|  The One Thing to Do First)                           |
+---------------------------+---------------------------+
                            |
                            v
+-------------------------------------------------------+
| Step 4: Ask-Matt Execution Plan (Spec to Tickets DAG) |
+-------------------------------------------------------+
```

---

## Phase 3: Ask-Matt Execution Plan (`/ask-matt`)

When the decision requires building, refactoring, or remediation, the Chairman synthesis automatically generates an actionable Ask-Matt Execution Plan:

1. **Architectural Specification (`/to-spec`)**:
   - Core domain invariants, data contracts, and non-negotiables.
   - Declares explicit **Protected Boundaries** (files that MUST NOT be touched or deleted, such as `tests/golden/`, past council transcripts, and working modules).
2. **Tracer-Bullet Tickets (`/to-tickets`)**:
   - A dependency DAG of self-contained tickets with declared blocking edges (prerequisites).
   - Every ticket declares its `Target Files (In-Scope)` and `Protected Boundaries (Out-of-Scope)`.
3. **Domain Specialist Multi-Agent Mapping**:
   - For each ticket, assigns an explicit domain expert persona (e.g., *Distributed Systems Engineer*, *Security & Policy Auditor*, *Process Isolation SRE*, *TDD & Verification Lead*).
   - Enforces domain-specific invariants rather than generic prompts.
4. **TDD Verification Criteria (`/tdd`)**:
   - Concrete test commands or boundary assertions to verify before committing.

---

## Phase 4: Supervised MinusCorrect Execution

Each unblocked domain-specialist ticket is executed under the **MinusCorrect Supervisor**:

```bash
# Supervised execution of the specialist's test repair inside an ephemeral worktree
minuscorrect run --worktree --isolate-env --timeout 180.0 -- pytest tests/staging/
```

**What MinusCorrect Enforces During Execution:**
- **4-Iteration Ceiling:** Prevents runaway agent loops.
- **Volatile Error Hashing:** Deterministic error signature tracking.
- **Ephemeral Git Worktree:** Isolates test execution from the main working tree.
- **Credential Sandboxing (`--isolate-env`):** Strips ambient secrets (`AWS_*`, `GITHUB_TOKEN`).
- **Atomic Rollback:** Discards bad agent diffs on failure without touching developer configuration files.
- **Systemic Integrity Gate:** Pre-commit verifier (`minuscorrect verify --fix --strict`) checks contracts before completion.
