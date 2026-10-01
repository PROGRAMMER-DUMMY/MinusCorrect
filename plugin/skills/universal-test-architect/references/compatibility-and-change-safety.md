# Compatibility and Change Safety

Contents: why this dimension exists, API and contract compatibility, schema and event evolution, database migrations and rollback, deployment verification, feature flags and dead code, rollout and config changes, dependency changes, post-mortem patterns, example invariants.

## Why this dimension exists

Many major outages come from change rather than from ordinary logic: a deployment that reached only some servers and revived old code through a reused flag; a single rule pushed globally without staged rollout that exhausted CPU fleet-wide; a capacity addition that crossed an OS limit. Unit tests of business logic do not see these, so test the change process and the coexistence of versions.

## API and contract compatibility

- **Consumer-driven contract tests:** the consumer records the interactions it really depends on; the provider replays them against its real implementation (routing, deserialization, validation, serialization; stub only downstream boundaries, never above request validation, or invalid payloads can pass). A compatibility gate (for example can-i-deploy) answers whether these versions are safe together.
- Breaking changes from the consumer's view: removing or renaming a route or field, changing a type (number to string), rejecting a header or query form the consumer sends, changing a status code the client branches on, changing pagination or ordering semantics, tightening validation.
- Use type matchers, not exact values, to avoid brittle contracts; publish contracts with immutable version identity (commit SHA and branch).
- Contract tests are not a substitute for a few end-to-end tests of critical journeys, and they do not cover performance or authorization.

## Schema and event evolution

- Compatibility modes: **backward** (new readers read old data), **forward** (old readers read new data), **full** (both). Pick per producer-consumer deployment relationship and enforce in CI with a schema registry.
- Safest change: add an optional field with a default. Usually breaking: add a required field, remove a field, change a type, reuse a field number or name for a different meaning, narrow a range, change enum meaning.
- Enums: does an old consumer handle an unknown new value (default branch) rather than crash?
- **Events are replayable:** a consumer can replay old data, and a new consumer can appear months later; test current code against historical payloads.
- **Semantic drift** (same shape, different meaning: units, timezone, status codes) does not crash anything, so add range and distribution checks that would notice.
- Unknown-field handling: ignore vs reject, consistently; null vs omitted vs empty collection.

## Database migrations and rollback

- **Expand, migrate, contract:** every breaking change becomes two non-breaking ones. Expand (additive change old code tolerates, no immediate NOT NULL unless every old writer satisfies it), deploy code that works with both shapes, backfill, switch reads, and only then contract (remove old).
- The testable question: can every application version that may run during the rollout read and write every database state it may encounter? Test the matrix (old code x new schema, new code x old schema, mixed fleet).
- Rollback: rolling back the binary is easy, rolling back data is not; test that the old version still works after new-version writes; define forward-fix vs rollback per migration.
- Dual writes create consistency risks: add reconciliation checks and a test that diverging copies are detected.
- Online safety: lock duration, long transactions, replication lag, batch size, resumability after interruption; run against production-sized data.
- Backfills: idempotent, resumable, throttled, verified by row counts and checksums.

## Deployment verification

- Post-deploy check that **every node runs the intended version** (version endpoint, build hash) and that no node runs stale code; deployment is atomic or verified, and a partial deploy halts automatically.
- Smoke tests and synthetic transactions immediately after deploy; automatic rollback on failing health signals.
- Kill switches and automated loss or exposure limits that do not depend on the health of the component they guard.

## Feature flags and dead code

- Retire flags; delete dead code. Anything that can be activated in production is production code.
- Never repurpose an old flag for a new meaning while old code paths still respond to it.
- Test both flag states and the transitions (on to off mid-request, per-user consistency, default when the flag service is down).
- Flag defaults are safe; flags evaluated consistently across services for one request.

## Rollout and configuration changes

- Staged rollout (canary, small percentage, region by region) for every change class, including "non-emergency" rule, config and WAF/feature data pushes; the blast radius of a global push is the whole fleet.
- Config validation in CI and at load time; invalid config is rejected with the old value kept; config changes are versioned and revertible.
- Protective limits (CPU time, memory, timeouts) are covered by a test so that a refactor cannot silently remove them.
- Emergency paths exist and are exercised (a documented fast rollback that has been tried).

## Dependency and platform changes

Library and runtime upgrades, TLS and certificate rotation, time zone database updates, OS or kernel limits, cloud provider API changes, deprecations. Tests: run the suite against the upgraded dependency in CI, contract tests for third-party APIs you call (record and replay plus periodic live checks), certificate expiry alarms tested with a short-lived cert.

## Post-mortem patterns to mine for test ideas

| Incident pattern | Test idea |
|---|---|
| Deploy reached some nodes only; old code reactivated by reused flag | Version-consistency check after deploy; flag-retirement audit; partial-deploy abort test |
| Global rule push caused fleet-wide CPU exhaustion via regex backtracking | Staged-rollout test; regex complexity tests on worst-case inputs; CPU-budget guard test |
| Refactor removed a protection silently | Test that asserts the protection (limit, timeout) exists and triggers |
| Small capacity add tripped an OS-level limit across the fleet | Scale-past-planned-maximum test; per-process resource alarms |
| Loss had no automatic limit and ran for tens of minutes | Kill-switch and automatic exposure-limit tests independent of the component |

## Example invariants to adapt

- I: Any version of the client released in the last N months works against the current server.
- I: At every point of a rolling deploy and rollback, every running version can read all stored data.
- I: A schema change that would break a registered consumer fails CI.
- I: After a deploy completes, all nodes report the same build identifier, or the deploy is rolled back automatically.
