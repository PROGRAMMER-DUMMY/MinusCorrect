---
name: council
description: >-
  Convene the 5-advisor LLM Council protocol (Contrarian, First Principles, Expansionist, Outsider, Executor) to analyze architecture decisions, refactors, or bugs with mandatory parallel subagent deliberation and anonymous peer-review.
---
# MinusCorrect LLM Council Protocol

An enterprise-grade autonomous engineering deliberation protocol combining **Andrej Karpathy's multi-perspective council** with **MinusCorrect's supervised execution runtime**.

You ask one AI a question, you get one answer. That answer might be great or it might be flawed. The council runs your question through 5 independent advisors, each thinking from a fundamentally different angle. Then they review each other's work anonymously. Then a chairman synthesizes everything into a final recommendation that tells you where the advisors agree, where they clash, and what you should actually do.

When the decision calls for building, refactoring, or remediation, the Chairman synthesis automatically generates an actionable **Ask-Minus Execution Plan**: an architectural spec and a dependency DAG of tracer-bullet tickets executed under MinusCorrect supervision.

---

## When to Run the Council

The council is for questions where being wrong is expensive:
- Triage of high-severity production incidents (`INCIDENT-RCA`)
- Architectural decisions where being wrong breaks system invariants
- Complex refactors with unknown blast radius
- Pre-execution plan pressure-testing before touching production code
- Coordinating multi-agent swarms with domain-specialist roles

Do NOT council trivial questions (simple yes/no questions, factual lookups, syntax queries). The council is for genuine uncertainty where multiple perspectives add value.

---

## The Five Advisors

Each advisor thinks from a different angle. They are thinking styles that naturally create tension with each other:

1. **The Contrarian**:
   Actively looks for what is wrong, what is missing, and what will fail. Assumes the proposal has fatal flaws and exposes them. Catches blast-radius hazards, edge cases, and regressions.

2. **The First Principles Thinker**:
   Ignores surface-level symptoms and asks: "What are we actually trying to solve here?" Strips away assumptions. Rebuilds the problem from foundational invariants.

3. **The Expansionist**:
   Looks for 10x upside everyone else is missing. Identifies adjacent opportunities, long-term leverage, and architectural durability.

4. **The Outsider**:
   Zero-context common-sense sanity check. Catches developer ergonomics traps, complexity bloat, and the curse of knowledge. Sees what fresh eyes see.

5. **The Executor**:
   Only cares about what can actually be built, tested, and shipped on Monday morning. Cuts scope; demands a concrete, surgical implementation plan.

---

## The 5-Step Execution State Machine (MANDATORY SUBAGENT PROTOCOL)

### Non-Negotiable Operational Invariants
1. **STRICTLY PROHIBITED TO SIMULATE ADVISORS INLINE**: You must NOT write out the 5 advisor responses in your own response text.
2. **Mandatory Parallel Subagent Execution**: You must call `invoke_subagent` with `TypeName='self'` to spawn 5 concurrent background subagents.
3. **Anonymized Peer Review**: The second round must anonymize the 5 responses (Response A through E) to eliminate positional and identity bias.
4. **Non-Destructive Boundary**: Past council transcripts, rules in `.minus/rules/`, and immutable golden tests in `tests/golden/` are strictly read-only.

---

### Step 1: Frame the Question
Before dispatching, reframe the inquiry into a clear, neutral prompt for all advisors:
1. Core question or architectural decision.
2. Concrete constraints, performance requirements, and error states.
3. What is at stake (why this decision matters).

---

### Step 2: Convene the Council (5 Subagents in Parallel)

Call `invoke_subagent` with 5 parallel entries:

```json
{
  "Subagents": [
    {
      "TypeName": "self",
      "Role": "The Contrarian",
      "Prompt": "You are The Contrarian on an LLM Council.\n\nYour thinking style: Actively looks for what will fail, what is missing, regressions, and hidden blast-radius traps.\n\nQuestion:\n[Framed Question]\n\nRespond from your perspective. Be direct and specific. Don't hedge. Keep response between 200-350 words. No preamble."
    },
    {
      "TypeName": "self",
      "Role": "The First Principles Thinker",
      "Prompt": "You are The First Principles Thinker on an LLM Council.\n\nYour thinking style: Strips away buzzwords and surface symptoms. Asks what fundamental invariant is being solved.\n\nQuestion:\n[Framed Question]\n\nRespond from your perspective. Be direct and specific. Don't hedge. Keep response between 200-350 words. No preamble."
    },
    {
      "TypeName": "self",
      "Role": "The Expansionist",
      "Prompt": "You are The Expansionist on an LLM Council.\n\nYour thinking style: Looks for 10x upside, systemic leverage, and architectural durability.\n\nQuestion:\n[Framed Question]\n\nRespond from your perspective. Be direct and specific. Don't hedge. Keep response between 200-350 words. No preamble."
    },
    {
      "TypeName": "self",
      "Role": "The Outsider",
      "Prompt": "You are The Outsider on an LLM Council.\n\nYour thinking style: Zero context, common-sense reality check. Catches developer ergonomics traps, complexity bloat, and unnecessary cognitive load.\n\nQuestion:\n[Framed Question]\n\nRespond from your perspective. Be direct and specific. Don't hedge. Keep response between 200-350 words. No preamble."
    },
    {
      "TypeName": "self",
      "Role": "The Executor",
      "Prompt": "You are The Executor on an LLM Council.\n\nYour thinking style: Only cares about what can actually be built, tested, and shipped on Monday morning. Demands a concrete, surgical tracer-bullet plan.\n\nQuestion:\n[Framed Question]\n\nRespond from your perspective. Be direct and specific. Don't hedge. Keep response between 200-350 words. No preamble."
    }
  ]
}
```

Stop tool calling and await subagent completion messages.

---

### Step 3: Anonymized Peer Review (5 Reviewer Subagents)

Once all 5 advisor responses are received:
1. Label them randomly as `Response A`, `Response B`, `Response C`, `Response D`, and `Response E`.
2. Call `invoke_subagent` to have each advisor peer-review all 5 anonymized responses:

```
Review Questions:
1. Which response is the strongest and why?
2. Which response has the biggest blind spot and what is it?
3. What did ALL responses miss that the council should consider?
```

---

### Step 4: Chairman Synthesis & Ask-Minus Plan

Synthesize the 5 perspectives and 5 peer reviews into a final structured verdict:

```markdown
## Council Verdict: [Topic]

### Where the Council Agrees
[High-confidence signals where multiple advisors converged independently.]

### Where the Council Clashes
[Genuine trade-offs and disagreements. Present both sides clearly.]

### Blind Spots the Council Caught
[Critical issues that only emerged through peer review.]

### The Recommendation
[A direct, unambiguous decision with clear technical rationale.]

### The One Thing to Do First
[A single concrete next action. Not a list.]

### Ask-Minus Execution Plan: Tracer-Bullet Tickets DAG
[When code changes are needed:
 1. Architectural Spec: Invariants and protected boundaries.
 2. Tracer-Bullet Tickets: Minimal vertical slices with dependencies.
 3. Domain Specialist Mapping: Assigned specialist persona.
 4. TDD Verification: Specific pytest command and verification criteria.]
```

---

### Step 5: Supervised Execution

When the user triggers execution ("proceed", "implement", "execute"):
1. Ingest tickets into `.minus/tickets/open/`.
2. Dispatch unblocked tickets to domain specialists via `invoke_subagent`.
3. Enforce the MinusCorrect Supervisor safeguards:
   - 4-Iteration Ceiling
   - Ephemeral Git Worktree isolation
   - Credential sandboxing (`--isolate-env`)
   - Pre-commit verifier (`minuscorrect verify --fix --strict`)
