# Data Engineering and Analytics Pipelines

Contents: failure topology, quality dimensions, pipeline-level tests, streaming, schema and contracts, transformations, serving, example invariants.

## Failure topology

The worst failures are silent: the job succeeds and the numbers are wrong (null propagation, duplicate rows after a join, dropped late data, timezone shifts, precision loss, stale partitions). Crashes are the easy case. Prioritize tests that detect wrong-but-successful runs.

## Quality dimensions (check each; turn into assertions)

Completeness (non-null where required, expected row counts), uniqueness (primary keys and natural keys), validity (formats, ranges, enums), consistency (across tables and systems, referential integrity), timeliness (freshness versus SLA), accuracy (reconciliation against the source system or an independent calculation). Validate at boundaries: at ingestion before data enters the warehouse, and at serving before consumers read it. Treat data contracts like versioned APIs.

## Pipeline-level tests

- **Re-run idempotency:** run the job twice on the same input and compare final state: identical, no duplicate rows.
- **Backfill equivalence:** a backfill over a date range produces the same result as the daily runs for that range.
- **Restart and partial failure:** kill the job mid-write and mid-checkpoint; the next run converges without duplicates or gaps; a partially written partition is never visible to readers (atomic publish).
- **Empty and tiny inputs:** zero rows, one row, all-null column, a single partition; job succeeds and downstream behaves.
- **Volumetric anomalies:** row count or sum deviates beyond a tolerance from recent history triggers an alert or fails the run, with thresholds set from the series, not a constant.
- **Dependency ordering:** upstream late or missing; downstream must not silently publish stale data as fresh.
- **Determinism:** fixed seeds for sampling, stable tie-breaking in ranking and deduplication (non-deterministic ORDER BY ties produce different results each run).

## Streaming and event-time

- Out-of-order and late events: inside the watermark (included), after the watermark (defined handling: drop, side-output, or reprocess), and very late (replay path).
- Watermark long enough for the lateness you must not drop; idle-source behavior so watermarks keep advancing.
- Window boundaries: events exactly at the window edge; session gaps; daylight-saving shifts for wall-clock windows.
- Sink semantics: some sinks give at-least-once only, so writes must be idempotent (upsert by key or transactional commit). Test a forced replay and a restart from checkpoint.
- Exactly-once claims: verify end to end with fault injection, not only per component.
- Consumer lag, backpressure and checkpoint-failure behavior under load.

## Schema drift and contracts

- Added column, dropped column, renamed column, type widened or narrowed, nullable changed, enum value added, nested field added.
- Contract compatibility mode (backward, forward, full) enforced in CI; breaking changes fail the build, not the dashboard.
- Semantic drift without schema change (units changed, status codes redefined, timezone of a timestamp changed): add distribution and range checks that would notice.
- Replay of historical data through the current code (events are replayable for years).

## Transformations and joins

- Join fan-out: many-to-many join duplicates rows; assert row counts and sum conservation before and after.
- Null semantics: NULL in comparisons, joins, aggregations, `NOT IN`, and `COUNT(col)` vs `COUNT(*)`.
- Deduplication: which record wins on ties (latest by which timestamp), late-arriving updates, tombstones and deletes.
- Slowly changing dimensions: overlap and gap in validity ranges; as-of joins.
- Floating-point aggregation order and precision; decimals for money; rounding mode.
- Time: timezone conversion, DST, event time vs processing time, date truncation at boundaries, leap day.
- Partition skew: one hot key; empty partitions; very small files.

## Serving and governance

- Late or incomplete data is marked, not shown as final. Consumers see consistent snapshots across related tables.
- PII: masking and deletion requests propagate to derived tables, caches and backups within policy.
- Access: row- and column-level security tested for each role.
- Cost guards: runaway query or scan limits.

## Example invariants to adapt

- I: Primary key is unique in every published table after every run.
- I: Re-running any job for any date yields byte-identical results (or a documented tolerance).
- I: Total revenue in the mart equals total in the source ledger within a stated tolerance, per day.
- I: No record dropped silently: rows in = rows out + rows in the rejects table.
- I: Published data is never older than the freshness SLA without an alert.

## Tools to suggest by stack

dbt tests and unit tests, Great Expectations or Soda checks, schema registry with compatibility modes, Spark or Flink test harnesses with in-memory sources, data diff tools for backfill equivalence.
