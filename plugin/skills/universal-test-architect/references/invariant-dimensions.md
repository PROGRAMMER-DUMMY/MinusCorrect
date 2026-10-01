# The Eight Dimensions

Use as a sweep after drafting invariants. For each applicable dimension ask the prompts, then draft cases. Skip a dimension only if you can say why it does not apply.

## 1. Contract and behavior
What must be true on the normal path, including shape, types, status, units, rounding, ordering, pagination and latency within the stated SLA.
- What does each input produce, exactly, per the spec? What is the documented error for each invalid input?
- Are response fields, defaults, units and time zones unambiguous? Are nulls distinguishable from missing?
- Keep happy-path cases few and sharp; one per distinct behavior.

## 2. Boundary, degenerate and interacting inputs
Where single values and small combinations break things.
- Limits (min, max, limit plus or minus one), empty, single element, duplicates, very large, deeply nested.
- Wrong type, wrong encoding, Unicode and normalization, locale, negative zero, NaN, time edges.
- Interactions: flags x roles x regions x currencies x plan tiers (pairwise or 3-way).
- Data: see `boundary-datasets.md`.

## 3. State, ordering and concurrency
What changes over time or across actors.
- Every state transition, every illegal (state, event) pair, repeated and out-of-order events.
- Concurrent writers on one entity (lost update, double spend, write skew, check-then-act races, deadlock).
- Duplicate delivery, replay, reordering, resumed-after-crash, partial completion.
- Idempotency: same request N times gives one effect; same key with different payload is rejected.

## 4. Fault tolerance and overload
What happens when the world misbehaves.
- Each dependency: timeout, slow, error 5xx, 429, malformed response, connection reset, partial response, DNS failure.
- The three failure phases of a call: lost before execution, crashed mid-execution, succeeded but response lost.
- Retry amplification, thundering herd, queue backlog, poison messages, circuit breaker or retry-budget behavior, graceful degradation and recovery.
- Disk full, memory pressure, clock skew, process kill, restart during operation.

## 5. Security, authorization and adversarial input
What a hostile or careless actor can do.
- Object-level and function-level authorization: swap IDs across users and tenants; use indirect paths (search, export, batch, webhooks, cached responses).
- Authentication edge cases, token expiry, replay, privilege change mid-session.
- Injection (SQL, command, template, header, path traversal, SSRF), oversized or deeply nested payloads, decompression bombs, regex complexity, rate and resource abuse.
- LLM-specific: direct and indirect prompt injection, data exfiltration through tools, excessive agency (see `domain-llm-agents.md`).
- Secrets and PII in logs, errors and telemetry.

## 6. Compatibility and change safety
What breaks when things change or coexist.
- Old client with new server, new client with old server, old and new code during rolling deploy and rollback.
- Schema and API evolution: optional vs required fields, enum additions, type changes, renamed routes, event replay of old data.
- Migrations: expand, migrate, contract; dual-write consistency; rollback after data changed.
- Deploy verification (did every node get the new version?), dead code and reused feature flags, staged rollout, config changes, dependency upgrades.
- See `compatibility-and-change-safety.md`.

## 7. Capacity and resource limits
What happens at scale, over time, and at limits.
- Saturation point and the first resource to run out (CPU, memory, threads, file descriptors, connections, ports, disk, rate limits).
- Resource use that scales with cluster size or peer count (per-peer threads, per-connection buffers).
- Soak: memory and latency trend over hours; leak detection. Spike and stress behavior, recovery after load drops.
- Algorithmic complexity on hostile input (regex backtracking, quadratic loops, unbounded recursion).
- Cost: unbounded consumption of tokens, queries, storage, egress.

## 8. Observability and operability
Whether a human can tell what broke and recover.
- Every failure path emits a structured log with a correlation ID and the violated invariant, increments an error metric, and does not leak secrets.
- Alerts fire for silent failures (data freshness, row-count anomalies, quality-score drops) and stay quiet for benign ones.
- Health checks tell the truth (not always green); synthetic end-to-end probes exist for critical flows.
- Runbooks and rollback actually work: test the rollback, the kill switch and the dead-letter reprocess.
