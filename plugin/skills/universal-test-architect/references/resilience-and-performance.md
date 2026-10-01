# Resilience, Fault Tolerance and Performance

Contents: 1 Timeouts and retries, 2 Overload and degradation, 3 Fault-injection approaches, 4 Chaos experiments, 5 Load and performance testing, 6 Resource limits, 7 Observability checks, 8 Example invariants.

## 1. Timeouts and retries

Why: a slow call holds memory, threads, connections and ports, so clients need timeouts. Retries help with transient and partial failures but add load to a system that is already struggling, so they need budgets.

Tests to generate:
- Every outbound call has a connection timeout and a request timeout; a hung dependency does not hang the caller beyond the deadline.
- **Deadline propagation:** per-attempt timers are derived from one absolute overall deadline; attempts plus backoff never exceed it.
- **Retry budget:** when every request fails at once, total dependency traffic stays within the budget (a per-call limit of two retries still triples traffic if unbounded across callers). Prefer a token-bucket style limit over unbounded per-call retries.
- **Retry placement:** in a multi-layer stack, retries at each layer multiply (three retries across five layers can amplify load by two orders of magnitude); assert retry happens at one layer.
- **Backoff with jitter:** simultaneous failures produce spread-out retries, not synchronized waves; apply jitter to other periodic work too (cron, polling, cache expiry).
- **What to retry:** transient and server errors (5xx, 429 honoring `Retry-After`, timeouts), not client errors (4xx other than 429); retry only idempotent operations or those protected by idempotency keys.
- False-timeout rate: a timeout set near the median triggers retry storms; choose from a high latency percentile of the dependency.

## 2. Overload and degradation

- Load shedding and admission control: beyond capacity, the service fails fast with a clear error and keeps serving priority traffic, rather than collapsing.
- Queue backlog behavior: bounded queues, priority, draining after recovery without a second spike.
- Circuit breakers are stateful and hard to test; if present, test open, half-open and closed transitions with a fake clock, and that they do not stay open forever.
- Graceful degradation: stale cache, reduced features, read-only mode; the degraded mode is visible to users and monitored.
- **Metastable failure check:** after a trigger is removed (traffic spike, slow dependency), does the system recover on its own, or does retry and queue load keep it down until manual intervention?
- Bulkheads: one noisy tenant or dependency cannot exhaust shared pools.

## 3. Fault-injection approaches

- **Jepsen-style black-box testing:** generate concurrent client operations, inject faults (partitions, process kills, clock shifts, disk stalls), record the operation history, then check it against the claimed guarantee (linearizability, serializability, causal consistency). Separate **availability failures** (timeouts, errors) from **safety failures** (an "ok" that returned wrong data or lost an acknowledged write). Report minimal failing histories.
- **Deterministic simulation:** run production code in a single-process harness where time, network, disk and scheduling are seeded and mocked; every failure replays from one seed; run thousands of seeds and keep assertions on. Needs the code designed with injectable clock, network and storage.
- **Targeted fault injection at seams:** fake a dependency that times out, returns 500, returns malformed data, drops the connection after sending half a response, or responds successfully but too late.
- **Crash-recovery tests:** kill the process at each step of a multi-step operation and restart.

## 4. Chaos experiments

Template: Given steady state (business-level metric, threshold, window), when a realistic fault is introduced at a limited scope, then steady state holds or degrades within bounds and recovers in a stated time. Start in a safe environment with a small blast radius, abort conditions and a kill switch; widen only after repeated passes; automate the experiments that pass. Steady state should be a measurable output (throughput, error rate, latency percentile, orders per minute), not an internal attribute.

Example faults: instance loss, zone loss, dependency latency, 429 or 503 from a dependency, packet loss, disk full, certificate expiry, clock skew, DNS failure, config push with a bad value.

## 5. Load and performance testing

Test types and questions: load (meets the SLO at expected peak?), stress (where and how does it break?), soak (does memory or latency drift over hours?), spike (survives a sudden surge and recovers?), breakpoint or capacity (what throughput per replica?), scalability (does adding nodes add capacity?).

Design rules:
- **Use an open model** (arrival-rate driven) for public APIs. A closed model lets a slow server slow the load generator, which hides the worst latencies (coordinated omission). One study example showed a 1.4-second stall producing a corrected p99 about 200 times larger than the uncorrected one.
- **Measure response time, not just service time**, and report percentiles (p50, p95, p99, p99.9, max), never just averages.
- **Do not average percentiles** across load generators: merge the latency distributions, or take the worst per-generator value as a bound.
- Find the **saturation point** with a staged ramp (rise, hold, rise); run replicas with margin below it (for example 10 to 20 percent) so autoscaling has time to react.
- Workload realism: endpoint mix, payload size distribution, think time, cache warm and cold, data volume that matches production indexes.
- Warm-up before measuring; run long enough to include compaction, GC cycles and cache effects.
- Verify the load generator is not the bottleneck (CPU, network, file descriptors) and that the target rate was actually held.
- Collect server-side metrics in the same window: CPU, memory trend, connection-pool saturation, queue depth, GC pauses, downstream latency. The first resource to saturate is the finding.
- Report: latency percentiles at target load, throughput ceiling where SLO still holds, the breaking point and how it fails (errors, timeouts, latency cliff), and the saturated resource. For soak, report the memory and latency trend.
- In CI, compare to a stored baseline and fail on regressions beyond an allowed delta; performance tests in shared CI are noisy, so use relative thresholds and repeat runs.

## 6. Resource limits

Ask what scales with cluster size, connection count or peer count (threads per peer, buffers per connection, file descriptors, ephemeral ports, memory per stream). A small capacity addition can push per-node resource use over an operating-system limit and cause a fleet-wide failure. Tests: scale the cluster or fan-out past the planned maximum in a safe environment and watch per-process threads, descriptors and memory; add alarms before limits; test that hitting a limit degrades, not crashes.

Hostile-input complexity: regular expressions with nested quantifiers on long inputs (catastrophic backtracking can exhaust CPU on every core of a fleet), quadratic algorithms, unbounded recursion, decompression bombs, huge JSON depth. Use linear-time regex engines where input is untrusted and time limits elsewhere.

## 7. Observability checks

Failure paths emit structured logs with correlation IDs and the failing invariant; error and saturation metrics exist and alert; synthetic end-to-end probes for critical flows fire within minutes of a bad change; alerts do not flap on benign events; dashboards show golden signals (latency, traffic, errors, saturation); log volume under failure does not itself cause an outage.

## 8. Example invariants to adapt

- I: Under a full dependency outage, added retry traffic stays below X times baseline.
- I: After a dependency recovers, the system returns to steady state within T without manual action.
- I: No acknowledged write is lost under any single-node crash or network partition.
- I: At target load, p99 latency stays under the SLO; at 1.5x load, errors rise gracefully, not catastrophically.
- I: Per-process thread and descriptor counts stay under 70 percent of OS limits at the maximum supported cluster size.
