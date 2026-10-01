# Backend Services, APIs, Queues, Payments

Contents: failure topology, idempotency, concurrency, webhooks and queues, authorization, caching, data layer, API details, example invariants.

## Failure topology

Silent, high-severity failures dominate: duplicate side effects, lost updates, cross-tenant reads, stale or partially applied state, and cascading timeouts. Design tests around these, then around contract correctness.

## Idempotency (payments, orders, webhooks, any retried write)

A client cannot tell which phase a timed-out call failed in: before execution, mid-execution, or after success with the response lost. So retries must be safe.

Test cases to generate:
- Same request with the same idempotency key N times concurrently and sequentially: exactly one side effect, identical response each time.
- Same key with a different payload: rejected with a conflict, not silently accepted and not executed.
- Key scoped to caller and endpoint: two callers using the same key value must not see each other's responses.
- Failed or timed-out first attempt: the stored result must not be a cached 5xx that poisons every later retry.
- Key expiry window: behavior exactly at, just before and just after expiry.
- Crash after side effect but before storing the key or response: recovery yields one effect (transactional write or outbox).
- Client retry with a fresh key per attempt (a client bug) versus per logical operation (correct); assert the server defends where it can, for example via a natural business key.
- Non-idempotent endpoints are never retried by middleware.

## Concurrency and state

- Two withdrawals racing on one balance: balance never negative, total conserved.
- Read-modify-write without a lock or version: lost update; test with optimistic version conflict and retry.
- Check-then-act (inventory reserve, seat booking, unique username): uniqueness enforced by the database, not by a prior query.
- Distributed lock expiry mid-operation; fencing tokens; clock skew effects on leases.
- State machine: every transition legal and illegal, repeated events, out-of-order events, cancellation racing completion.
- Transactions: partial failure rolls back all effects, including external calls (saga compensation tested both ways).
- Pagination under concurrent inserts and deletes: no duplicates or gaps with cursor pagination; define behavior for offset pagination.

## Webhooks, events and queues (at-least-once is the normal case)

- Duplicate delivery, out-of-order delivery, delayed delivery hours later, replay of an old event after newer state.
- Signature verification: missing, wrong, expired timestamp, replayed signature, body modified after signing (raw-body handling).
- Poison message: bounded retries then dead-letter; reprocessing from the dead-letter queue is idempotent.
- Consumer crash after processing before ack, and after ack before side effect is committed.
- Backlog drain: consumer catches up without overwhelming downstream; ordering keys respected.
- Schema evolution of events: old events replayed into a new consumer (see `compatibility-and-change-safety.md`).

## Authorization and tenancy (run for every object-ID endpoint)

Build a matrix: actor (anonymous, user A, user B of the same tenant, user C of another tenant, admin, service account) x object (own, other's, nonexistent, soft-deleted) x action (read, create, update, delete, list, export) x path (direct, search, batch, webhook, cached).
- Swap the object ID for another user's: denied with the same response shape as nonexistent (no existence leak).
- Function-level: a low-privilege user calls an admin route or uses a different HTTP method on the same path.
- Property-level: mass assignment (client sets `role`, `owner_id`, `price`), excessive data exposure in responses.
- Privilege change mid-session and token revocation take effect within the stated window.

## Caching and derived data

- Stampede on expiry, stale reads after write (read-your-writes), invalidation on every write path, negative caching of errors, cache key omitting tenant or locale.

## Data layer

- Constraints exist in the database, not only in code: unique, not-null, foreign key, check.
- Migrations safe under load (locks, long transactions), reversible or forward-fixable (see compatibility file).
- Time: store UTC, test DST transitions, leap day, month ends, and clock changes.
- Precision: money as integer minor units or decimal, never binary float; rounding mode specified and tested.

## API details

- Status codes and error bodies for each invalid input class; consistent error schema; no stack traces.
- Unknown fields, missing fields, null vs absent, wrong content type, huge body, slow body, many headers.
- Rate limiting: exactly at the limit, burst, per-key vs per-IP, reset behavior, `Retry-After` honored.
- Timeouts on every outbound call; per-try timeouts derived from one overall deadline.
- Versioning: old clients keep working (see compatibility file).

## Example invariants to adapt

- I: For any idempotency key, at most one charge exists, regardless of retries or concurrency.
- I: Sum of ledger entries per transaction is zero; no account balance drops below its floor.
- I: A user can read or modify only objects their tenant owns, on every path.
- I: Every accepted message is processed at least once and its effects applied at most once.
- I: After recovery from any single-node crash, no acknowledged write is lost.
