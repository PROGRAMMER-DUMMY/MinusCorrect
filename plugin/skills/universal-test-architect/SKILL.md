---
name: universal-test-architect
description: >-
  Generates risk-ranked, high-signal test cases, test plans, QA strategies and test-suite reviews for ANY technical system: backend APIs and microservices, data pipelines and ETL, ML/DL models, LLM apps and agents, web and mobile front ends, infrastructure and deployments. Use this skill whenever the user asks for test cases, edge cases, a test plan, QA strategy, what to test, failure modes, invariants, property-based tests, chaos or load test design, contract tests, data-quality checks, model or LLM evals, or wants an existing test suite reviewed or strengthened.
---

# Universal Test Architect

Turn a system description, code, schema, design doc or requirement into a small set of test cases that would actually catch the bugs that hurt. The goal is bug-catching power per test, not volume and not coverage percentage.

## Why this skill works the way it does

Five findings shape every step below (evidence and sources are in `references/evidence.md`):

1. **Expected results must not come from the code under test.** LLM-written tests tend to assert what the code does rather than what it should do, and will happily encode a bug as "correct". So every test names the source of its oracle (Step 0).
2. **Coverage is not the target.** Research on large codebases finds only a weak-to-moderate link between coverage and fault detection once suite size is controlled. Ask instead: what real bug would this test catch, and would it fail if that bug existed?
3. **Bugs cluster at boundaries and interactions.** Most failures involve one to three parameters, so boundary values first, pairwise for interactions, deeper only where severity justifies it.
4. **Outages come from change, scale and failure handling as much as from logic.** Real post-mortems (deploy mismatches, unbounded regex cost, thread limits, retry storms) are mostly invisible to happy-path unit tests, so the skill treats compatibility, deployment, overload and resource limits as first-class dimensions.
5. **Flaky tests destroy trust.** A few percent of flaky results makes large suites unreadable, so every test must control time, randomness, network and ordering.

## Workflow

Work through these steps in order. Keep visible output proportional to the request (see "Sizing").

### Step 0 - Establish intent and the oracle

Before generating anything, identify where "correct" is defined. Acceptable oracle sources, in order of preference:

- **Spec**: requirement, acceptance criteria, API schema, contract, SLA, regulation, documented behavior.
- **Invariant or property**: a rule that must always hold (balance never negative, output sorted, retry produces one side effect, more credit score never lowers approval).
- **Reference or differential**: previous version, second implementation, or trusted model. Label these regression or differential oracles.
- **User-confirmed decision**: ask, or state the assumption explicitly.

If the only source is the code itself, label the test **characterization** and say it pins current behavior without proving correctness. If the code contradicts its own names, docs or comments, report a *suspected defect* and do not encode the behavior as expected.

Ask at most two or three sharp questions, and only when the answer would change a P0 test. Otherwise proceed and list your assumptions at the top of the output.

### Step 1 - Classify the system and load references

Identify every archetype that applies (most real systems are several) and read the matching file(s):

| System looks like | Read |
|---|---|
| HTTP/gRPC API, microservice, queue consumer, webhook, payments, auth, DB-backed service | `references/domain-backend-services.md` |
| ETL/ELT, warehouse, streaming job, dbt/Spark/Flink/Airflow, data contract | `references/domain-data-engineering.md` |
| Trained model, feature pipeline, recommender, classifier, deep learning code | `references/domain-ml-dl.md` |
| LLM feature, RAG, agent, prompt, tool use | `references/domain-llm-agents.md` |
| Web UI, SPA, mobile app, design system, accessibility | `references/domain-frontend-mobile.md` |
| Anything distributed, latency-sensitive, or with retries and dependencies | `references/resilience-and-performance.md` |
| Anything that ships, migrates, versions, or has consumers you do not control | `references/compatibility-and-change-safety.md` |

Always consult `references/invariant-dimensions.md` (the eight dimensions) and `references/technique-selection.md` (which technique fits which failure type). Use `references/boundary-datasets.md` when you need concrete hostile values.

### Step 2 - Model the system, then write invariants first

In a few lines, list: actors, entities and their states, inputs and their domains, external dependencies, and trust boundaries. Then write 5 to 15 numbered invariants (I1, I2, ...) in three groups:

- **Safety**: something bad never happens (no double charge, no cross-tenant read, no data loss, no NaN in output).
- **Liveness**: something good eventually happens (every accepted job completes or lands in a dead-letter queue; system recovers after partition heals).
- **Quality of service**: latency, freshness, accuracy or cost stays within stated bounds.

Test cases are then built to *attack* these invariants. A test that cannot be tied to an invariant or a named failure mode is probably filler.

### Step 3 - Risk-rank failure modes

For each plausible failure mode assign:

- **Severity**: 4 catastrophic (money, data loss or corruption, security breach, safety, legal), 3 major (core flow down or visibly wrong), 2 moderate (degraded, workaround exists), 1 minor.
- **Likelihood**: 3 likely (common path, known to happen at scale), 2 plausible, 1 rare.
- **Silent?** Yes if nothing would alert anyone (wrong numbers, stale data, quiet data loss).

Priority rule (a severity-gated lookup; never multiply the ratings together, because identical products hide very different risks):

- Severity 4 is **P0** regardless of likelihood (drop to P1 only if effectively impossible).
- Severity 3 with likelihood 2 or 3 is **P0**; severity 3 with likelihood 1 is **P1**.
- Severity 2 with likelihood 3 is **P1**; other severity 2 is **P2**. Severity 1 is **P2**.
- If the failure is **silent**, raise the priority one level (P2 to P1, P1 to P0).

This rule is a practical heuristic modeled on action-priority tables; say so if asked, and let the user override severities from their own business context.

### Step 4 - Generate candidates, choosing technique by failure type

For each P0 and P1 failure mode, pick the technique that fits (table in `references/technique-selection.md`), then sweep the eight dimensions for gaps:

1. Contract and behavior
2. Boundary, degenerate and interacting inputs
3. State, ordering and concurrency
4. Fault tolerance and overload
5. Security, authorization and adversarial input
6. Compatibility and change safety
7. Capacity and resource limits
8. Observability and operability

Spend effort where bugs hide: boundaries, negative space (invalid, missing, duplicated, reordered, stale, oversized), state transitions, and failure handling. One or two happy-path cases per feature are enough.

### Step 5 - Quality gates (self-critique before showing anything)

Run each candidate through `references/quality-rubric.md`. In short, drop or repair a test if any hard gate fails:

- No named oracle source, or the oracle is just the current code output.
- Cannot say what realistic bug it would catch, or it would still pass if that bug were injected (name the mutation it kills: flipped boundary, negated condition, deleted call, removed retry or auth check, swapped order).
- Non-deterministic (uncontrolled clock, random, network, ordering, shared state).
- Asserts implementation details (private calls, exact log text, call counts) rather than observable behavior.
- Failure message would not tell an on-call engineer which invariant broke.
- Redundant with another test (same invariant, same equivalence class, same mutation).

Then check the **set**: does it cover every dimension that applies, use more than one technique, and put its weight on P0 risks? Do not use coverage percentage as a quality target.

### Step 6 - Output

Use this structure (adapt depth to the request):

1. **Assumptions and oracle sources** (short).
2. **System model and invariants** (I1..In).
3. **Risk map**: top failure modes with severity, likelihood, silent flag, priority.
4. **Test cases** grouped by dimension. P0 cases get the full spec from `references/test-case-schema.md`; P1 and P2 use the compact one-line form.
5. **Not covered and residual risk**: what you deliberately left out and why, plus any spec gaps or suspected defects found.
6. **Automation notes**: suggested layer (unit, component, contract, integration, end to end, chaos, load), determinism controls needed (fake clock, seeded random, stubbed network, isolated data), and tools fitting the user's stack.
7. **Self-check**: one or two lines reporting which gates were applied and what was dropped.

If the user wants executable tests, write them in their framework and language, keep one behavior per test, name tests as statements of behavior, put the violated invariant in the assertion message, prefer real dependencies or fakes over mocks where feasible, and use property-based tools (Hypothesis, fast-check, jqwik, proptest) for properties.

## Sizing

- **Quick** ("give me some edge cases for X"): 8 to 12 cases, mostly P0 and P1, compact form, brief assumptions.
- **Standard** (a feature, service or pipeline): 20 to 40 cases across dimensions, P0 fully specified.
- **Deep** (whole system or release gate): work module by module, produce the risk map first, then cases per module; offer to continue rather than emitting hundreds of cases at once.

Never pad to reach a number. A short list that attacks the real risks beats a long list of near-duplicates.

## Review mode (user supplies existing tests)

When asked to review, audit or strengthen an existing suite:

1. Classify each test: behavior test, **change-detector** (breaks on harmless refactors), **characterization** (pins current output), weak assertion (executes code but asserts little), flaky-prone (time, random, network, order, shared state).
2. Mentally inject mutants into the code under test (flip a boundary, negate a condition, delete a statement, return a constant, skip auth or retry) and list which ones no current test would catch. These are the highest-value gaps.
3. Compare against the invariants and dimensions to find missing areas.
4. Output a prioritized list: fix, delete, add. Offer to write the additions.

## Calibration rules

- Do not invent statistics. Quote numbers only from `references/evidence.md` or from the user's own data, and label conventional thresholds (for example PSI 0.1 and 0.25) as starting points to calibrate.
- Distinguish facts about the system from assumptions. Say when a behavior depends on the specific engine, version or vendor and should be verified there.
- Point out spec ambiguity instead of guessing silently. Ambiguities are often the best bugs.
- Keep tone practical. Explain *why* a test matters in one sentence of business or engineering impact, not with alarmist language.

## Anti-patterns to avoid

- Happy-path-only suites; "tests" that assert a mock was called.
- Copying the implementation's logic into the assertion (circular test).
- Exact-match assertions on LLM or model output where a property, tolerance or metamorphic relation is the right check.
- Sleeps and real clocks for timing; shared mutable fixtures; order-dependent tests.
- Treating 100% coverage, neuron coverage or test count as success.
- RPN-style multiplication of severity, occurrence and detection for prioritization.
- Retrying a failing test until it passes instead of fixing the nondeterminism.
