================================================================================
MINUSCORRECT ASK-MATT EXECUTION PLAN (Spec to Tickets DAG)
================================================================================
Target: Enterprise Application: High-velocity enterprise application

PHASE 1: ARCHITECTURAL SPECIFICATION (/to-spec):
  - Core Invariant: System state remains consistent; golden contracts are immutable.
  - Protected Boundaries:
      * tests/golden/* (strictly read-only)
      * Production modules outside targeted blast radius

PHASE 2: TRACER-BULLET TICKETS DAG (/to-tickets):
  [TICKET-01] Contract Definition & Test Staging
    Role: Distributed Systems Engineer
    Objective: Define interface contracts and create staged acceptance tests.
    Dependencies: Blocked By: [None] | Blocks: [TICKET-02]
    Verification: minuscorrect run --worktree -- pytest tests/staging/

  [TICKET-02] Surgical Implementation & Sandboxed Verification
    Role: Process Isolation SRE
    Objective: Implement minimal solution within single target file blast radius.
    Dependencies: Blocked By: [TICKET-01] | Blocks: [TICKET-03]
    Verification: minuscorrect run --worktree --isolate-env -- pytest tests/staging/

  [TICKET-03] Pre-Commit Integrity Audit & Clean-up
    Role: TDD & Verification Lead
    Objective: Run pre-commit systemic verifier, strip debug scaffolding, and export PR proposal.
    Dependencies: Blocked By: [TICKET-02] | Blocks: [None]
    Verification: minuscorrect verify --fix --strict && minuscorrect pr

PHASE 3: SUPERVISED EXECUTION:
  - Execute tickets under 4-iteration ceiling with ephemeral worktree isolation:
    minuscorrect run --worktree --isolate-env -- pytest <test_path>
  - Run final integrity audit:
    minuscorrect verify --fix --strict
================================================================================