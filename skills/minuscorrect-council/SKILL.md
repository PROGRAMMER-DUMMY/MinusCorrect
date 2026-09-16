---
name: minuscorrect-council
description: Multi-perspective LLM Council protocol for autonomous coding agents. Use for pre-execution architectural decisions, high-risk bug triage, and pressure-testing plans through 5 independent thinking styles (Contrarian, First Principles, Expansionist, Outsider, Executor) before touching production code.
---

# MinusCorrect Council Skill

A structured pre-execution deliberation protocol for autonomous coding agents. When facing architectural trade-offs, complex bug fixes, or high-risk refactors, running a council deliberation prevents the single-model cognitive tunnel-vision that leads to burned iteration budgets.

## When to Activate

- Triage of high-severity production incidents (`INCIDENT-RCA`)
- Architectural decisions where being wrong breaks system invariants
- Complex refactors with unknown blast radius
- Pre-execution review of patches before committing to the 4-iteration supervisor loop

## The Five Thinking Lenses

1. **The Contrarian**: Actively looks for what will break, regressions, AST blast-radius hazards, and unintended side-effects.
2. **The First Principles Thinker**: Strips away surface symptoms; asks what core invariant is being violated.
3. **The Expansionist**: Identifies systemic leverage and long-term architectural durability.
4. **The Outsider**: Provides zero-context sanity checks; catches over-engineering, buzzwords, and developer ergonomics traps.
5. **The Executor**: Cuts scope; formulates the minimal, surgical Monday-morning patch plan.

## The Deliberation Workflow

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
+-------------------------------------------------------+
```

## Integrating with MinusCorrect Supervisor

Once the Council yields **The One Thing to Do First**, the agent executes the minimal patch under MinusCorrect's 4-iteration supervisor:

```bash
# Supervised execution of the council's minimal test fix
minuscorrect run --session-id council-triage -- pytest tests/staging/
```
