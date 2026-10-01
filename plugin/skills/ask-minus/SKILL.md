---
name: ask-minus
description: >-
  Autonomous meta-orchestrator and cognitive intake brain for MinusCorrect. Knows all 16 repository skills, decodes colloquial or frustrated user requests, diagnoses root causes, builds tracer-bullet ticket DAGs in .minus/tickets/, and dispatches domain specialist subagents under supervised worktree containment. Triggers: '/ask-minus', 'ask-minus', 'minus check', 'what should we do', 'plan and execute', 'fix this'.
---
# MinusCorrect Ask-Minus Autonomous Orchestrator

The central intake brain and autonomous dispatch controller for MinusCorrect.

Instead of requiring developers to manually memorize 16 different CLI subcommands or slash commands, `ask-minus` ingests natural, unformatted, or frustrated developer requests, determines the root objective, routes to the appropriate MinusCorrect skills in optimal dependency order, registers tracer-bullet tickets in `.minus/tickets/open/`, and dispatches specialized subagents via `invoke_subagent`.

---

## Skill Capability Registry

`ask-minus` maintains full operational awareness of every MinusCorrect subsystem:

| Skill / Subsystem | Primary Capability | When `ask-minus` Activates It |
|---|---|---|
| **anti-cheat** | AST tautology detection, empty catch inspection, fixture leaks | "tests passing suspiciously", "are agents cheating", "vacuous assertions" |
| **doctor** | Diagnostic health check, polyglot driver availability, tool readiness | "subagents not launching", "environment broken", "missing dependencies" |
| **council** | 5-advisor deliberation (Contrarian, First Principles, Expansionist, Outsider, Executor) | High-stakes architectural decisions, "should I do X or Y", conflicting trade-offs |
| **research** | 3-wave multi-agent deep web research swarm (1 -> 3 -> 8) | "compare libraries deeply", "investigate RFC/spec", "find failure modes" |
| **audit** | 10-domain pre-launch security and operational audit | "pre-launch check", "is this production ready", "audit RLS and secrets" |
| **security** | Adversarial vulnerability scanning, PoC reproduction contracts | "check injection vectors", "audit auth boundaries", "verify CVE" |
| **spec** | Enterprise specification suite (PRD, TRD, Refero DESIGN, SCHEMA, APPFLOW) | "spec this feature", "design UI tokens", "scaffold new system" |
| **ticket** | Second-brain ticket lifecycle management in `.minus/tickets/` | Managing tasks, tracking open issues, closing tickets with receipts |
| **verify** | Golden test contract protection, anti-swallowing gate, clean diffs | Pre-commit sanity, "verify everything", "clean up debug logs" |
| **rollback** | Atomic revert of agent commits with post-revert verification | "undo bad agent change", "rollback ticket commit" |
| **empirical-research-lab** | Tamper-evident experiment receipts (`make_receipt.py`), statistical rigor | "benchmark performance", "evaluate model run", "verify test claims" |
| **supervisor** | Ephemeral git worktree isolation, 4-loop ceiling, isolate-env | Executing any code mutation safely without breaking main |

---

## Cognitive Intent Decoding

When a user presents a natural language request, `ask-minus` decodes the underlying operational intent:

### Intent 1: "The agents are cheating / tests pass too easily"
- **User Prompt Examples**:
  - *"minus check i think the agents are cheating here see where are they and fix these things first"*
  - *"tests pass but the bug is still there"*
- **Ask-Minus Execution Route**:
  1. Immediately execute `minuscorrect anti-cheat` across `tests/` and source directories (`.py`, `.ts`, `.tsx`, `.js`).
  2. Inspect for:
     - Tautological assertions (`assert x == x`, `expect(x).toBe(x)`)
     - Swallowed exceptions (`try/except: pass`, empty `catch` blocks)
     - Assert-free tests (`it('should work', () => {})` with no assertions)
  3. Create fix tickets in `.minus/tickets/open/` targeting each flagged file.
  4. Dispatch the `TDD & Verification Lead` subagent to replace fake assertions with real invariant contracts.

### Intent 2: "Subagents are not firing / why are they idle"
- **User Prompt Examples**:
  - *"in antigravity none is launching the subagents it requires i dont see the subagents why"*
  - *"why is council not spawning subagents"*
- **Ask-Minus Execution Route**:
  1. Inspect command definitions in `plugin/commands/*.toml` to verify presence of `invoke_subagent` directives.
  2. Run `minuscorrect doctor` to check polyglot AST drivers and environment dependencies.
  3. Check active subagent state via `manage_subagents(Action='list')`.
  4. Report diagnostic status and re-dispatch pending tasks using explicit `invoke_subagent` calls.

### Intent 3: "Architectural dilemma / trade-off debate"
- **User Prompt Examples**:
  - *"should we use Redis distributed locks or PostgreSQL advisory locks for our jobs"*
  - *"i am torn between approach A and approach B"*
- **Ask-Minus Execution Route**:
  1. Frame the neutral question.
  2. Convene the 5-advisor `council` by calling `invoke_subagent` for all 5 advisors concurrently.
  3. Run anonymized peer-review round.
  4. Synthesize Chairman Verdict and build the Ask-Minus ticket DAG.

### Intent 4: "Feature implementation / bug fix"
- **User Prompt Examples**:
  - *"add webhooks with HMAC verification and idempotency keys"*
  - *"fix memory leak in worktree cleanup"*
- **Ask-Minus Execution Route**:
  1. Phase 1: Architectural Spec (`/to-spec`) defining Core Invariant and Protected Boundaries (`tests/golden/*`).
  2. Phase 2: Tracer-Bullet Tickets DAG (`/to-tickets`) in `.minus/tickets/open/`.
  3. Phase 3: Assign Domain Specialist Personas.
  4. Phase 4: Dispatch unblocked tickets via `invoke_subagent` under supervised worktree containment.

---

## Ticket DAG & Dispatch Lifecycle

Every action planned by `ask-minus` produces structured tickets:

```markdown
### T-00X: [Title]
- **Role**: [Domain Specialist Persona]
- **Objective**: [Crisp behavioral outcome]
- **Target Files (In-Scope)**:
  - `path/to/target.py`
- **Protected Boundaries (Out-of-Scope - READ-ONLY)**:
  - `tests/golden/*`
- **Dependencies**: Blocked By: [] | Blocks: [T-00Y]
- **TDD Contract**:
  - Command: `minuscorrect run --worktree --isolate-env -- pytest <test_path>`
  - Pass Condition: Green assertions, zero debug tags.
```

### Autonomous Subagent Dispatch Protocol
When tickets are ready to execute:
1. Identify all unblocked root tickets (tickets with no unfinished dependencies).
2. For each unblocked ticket, call `invoke_subagent` with `TypeName='self'`.
3. Provide the full specialist persona system prompt from `minuscorrect/specialists.py`.
4. As each subagent completes, mark the ticket complete in `.minus/tickets/completed/`, update `.minus/index.json`, and dispatch newly unblocked downstream tickets.
5. Once all tickets pass, run `python scripts/verify_integrity.py --fix --strict` and present the final commit receipt.
