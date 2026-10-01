# Technique Selection

Pick the technique from the failure type, not from habit. Contents: 1 Decision table, 2 Procedures, 3 Property and metamorphic catalogs, 4 Mutation-kill analysis, 5 Formal models, 6 Experiment templates.

## 1. Decision table

| Failure type | First-choice technique | Add when severity is high | Do not use when |
|---|---|---|---|
| Single-value faults (off-by-one, limits, empty, null) | Equivalence partitioning + boundary value analysis | Property-based tests over the same domain | - |
| Two- or three-parameter interaction faults (config combos, flags, locale x currency x role) | Pairwise covering array | 3-way for safety or money flows; always add parameter constraints | Parameters are not independent and constraints are unknown |
| Encode/decode, parse/format, normalize, serialize | Property-based: round-trip, idempotence | Fuzzing with a corpus and sanitizers | Oracle is as complex as the implementation |
| Stateful objects, workflows, APIs with ordering | State-transition tests + stateful property tests (random operation sequences against a simple model) | Model checking (see section 5) | State space is trivial |
| No ground truth (ML, search, ranking, simulations) | Metamorphic relations, invariance and directional tests, differential testing | Slice and subgroup checks | A cheap exact oracle exists |
| Concurrency, replication, consensus, distributed transactions | Deterministic simulation or controlled schedules; Jepsen-style fault injection with a history checker | Formal model of the design | Pure single-threaded code |
| Retry, timeout, overload, dependency failure | Fault injection at dependency boundaries; chaos experiment with steady-state hypothesis | Load plus fault combined | No external dependencies |
| Integration drift between independently deployed services | Consumer-driven contract tests + compatibility checks | Schema registry compatibility gates | One team deploys both sides atomically |
| Parsers, deserializers, regex, file and protocol handlers | Fuzzing and property tests; complexity (ReDoS) checks | Resource limits on input size and time | - |
| Capacity, latency SLOs, leaks | Open-model load, stress, soak, spike | Saturation and knee analysis | - |
| Authorization and tenancy | Object-level and function-level access matrix (user x role x object x action) | Indirect paths (search, export, batch, webhooks) | - |
| Data correctness over time | Invariant queries, reconciliation, re-run/backfill idempotency, late-data cases | Contracts with compatibility modes | - |

## 2. Procedures

**Equivalence partitioning + boundary value analysis.** For each input: list valid classes, invalid classes (wrong type, missing, null, empty, oversized, malformed, wrong encoding), then test the boundary value, one step inside and one step outside of every limit (on/in/out). Include the implicit boundaries: zero, negative, maximum representable, length limits, precision limits, time-window edges, and page-size edges. Most failures are triggered by a single value, so this is the highest-yield step.

**Pairwise and t-way.** Model parameters and values (using equivalence classes, not raw values), declare constraints (invalid combinations), generate a 2-way array for general coverage and 3-way for P0 flows. Real faults are mostly 1- to 3-way, so going beyond 4-way is rarely worth it, but a few known dangerous combinations should be added by hand. Report which parameters and constraints you assumed.

**State-transition tests.** Draw states and events; cover every transition, every illegal (state, event) pair, repeated events, and out-of-order events. Add timeout and crash events at each state. Assert the invariant after every step, not only at the end.

**Differential and cross-referencing oracles.** When two implementations or models should agree (old vs new, fast vs reference, model A vs model B), generate inputs and investigate disagreements. Disagreement does not say which side is wrong, so triage.

## 3. Catalogs

**Property strength (weak to strong):** no exception, type preserved, invariant holds, idempotence, round-trip. Prefer the strongest property that is cheap to state.

| Property | Form | Typical targets |
|---|---|---|
| Round-trip | decode(encode(x)) == x | serializers, codecs, migrations |
| Idempotence | f(f(x)) == f(x) | normalization, deduplication, upserts, retries, backfills |
| Invariant | property holds before and after | sort, filter, ledger operations |
| Commutativity / associativity | order or grouping does not matter | merge, aggregate, CRDTs, streaming windows |
| Oracle | optimized(x) == reference(x) | refactors, caches, rewrites |
| Conservation | totals preserved | money transfers, row counts across joins, token counts |
| Monotonicity | more of X never gives less of Y | scores, limits, prices, pagination offsets |

**Metamorphic relations for models:** invariance (label-preserving perturbations: typos, synonyms, irrelevant name swaps, unit changes, reordering of independent rows), directional (a change must move output a known way: raising credit score must not lower approval probability), scaling and symmetry (rotating an image by the training-augmentation range should not flip class), additivity and consistency across batch sizes (same example scored alone vs in a batch must match within tolerance).

## 4. Mutation-kill analysis (use on every P0 test)

Seed a mental mutant into the code or design and ask whether the test fails. Standard mutants: flip `<` to `<=`; negate a condition; swap `and`/`or`; delete a statement or call (the retry, the auth check, the dedup, the rollback); return a constant or empty; change the order of two operations; change a default; drop an `await`; widen or narrow a type; remove a timeout. If none fail the test, rewrite the assertion to observe the effect, not merely to run the line.

Mutants are a good, not perfect, proxy: studies find most real faults are coupled to simple mutants but a meaningful minority (about a quarter) are not, so also reason from the failure-mode list, especially for missing-code and design-level faults.

## 5. When to propose a formal model

Propose a TLA+ or similar model (and list its invariants and the interleavings to explore) when the design has replication, leader election, distributed transactions, cache invalidation, workflows with compensation, or lock-free structures. Tests on code cannot reach the astronomically large state space of such designs; model checking of the design can find bugs whose shortest failing trace is dozens of steps. Output the state variables, actions, safety invariants and liveness properties, then the test cases that mirror counterexample traces.

## 6. Experiment templates

**Chaos experiment (hypothesis form):**
Given steady state `<metric, threshold, window>`;
When `<real-world fault, scope, duration>`;
Then steady state holds, or degrades to `<bounded acceptable level>` and recovers within `<time>`;
Guardrails: blast radius, abort condition, kill switch, rollback.
Start small, widen only after repeated passes. Prefer faults that really occur (instance loss, latency, partition, dependency 429/503, disk full, clock skew).

**Load test design:** see `resilience-and-performance.md` (open model, percentiles, saturation, soak, spike).

**Fuzz target checklist:** entry point that accepts bytes or structured input, seed corpus from real samples, sanitizers on, time and memory limits, crash-minimization, regression corpus committed. Expect timeouts and out-of-memory findings to be flaky; set deterministic limits.
