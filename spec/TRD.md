# Technical Requirements Document (TRD)
# Project: Enterprise Application

## 1. Architectural Topology
- **Frontend Layer**: Next.js 15+ (App Router, Server Components, Server Actions).
- **Styling & Design System**: Tailwind CSS v4 (`@theme`), CSS custom properties, Refero Obsidian design tokens.
- **Data Persistence**: PostgreSQL 16 / Supabase (PgBouncer connection pooling, Row Level Security).
- **Payment Gateway**: Stripe Billing API (asynchronous webhook queue, distributed idempotency keys).
- **Observability**: Sentry for error tracking (with PII scrubbing), Datadog/PostHog for analytics, synthetic health checks.
- **Supervised Containment**: MinusCorrect Runtime Supervisor (worktree isolation, 4-loop ceiling, AST verifiers).

## 2. System Invariants & Non-Negotiables
1. **Tenant Boundary Invariant**:
   - Every database table MUST enable Row Level Security (`ALTER TABLE ... ENABLE ROW LEVEL SECURITY`).
   - Every read/write query MUST filter by `tenant_id` linked to `auth.uid()`.
2. **Client-Side Secret Invariant**:
   - Zero administrative keys (e.g. `service_role`, `sk_live_`) prefixed with `NEXT_PUBLIC_` or bundled in client JS.
3. **Cryptographic Webhook Verification**:
   - Webhook handlers MUST verify raw binary request bodies against provider secrets before parsing JSON.
4. **Mutation Idempotency**:
   - All state-mutating HTTP POST/PATCH endpoints MUST enforce unique `Idempotency-Key` headers.
5. **Foreign Key Indexing**:
   - Every column with a `REFERENCES` constraint MUST possess a dedicated B-tree index to eliminate sequential scans.

## 3. Next.js Server Action Security Protocol
- Server Actions (`'use server'`) compile into public HTTP endpoints.
- Layout-level redirects do NOT protect Server Actions.
- Every Server Action MUST explicitly execute:
  ```typescript
  const session = await getSession();
  if (!session?.user?.id) throw new UnauthorizedError();
  await assertTenantAccess(session.user.id, targetTenantId);
  ```

## 4. Operational Fallbacks & Circuit Breakers
- External API integrations (Stripe, Resend, Twilio) MUST be wrapped in 3.0s timeout bounds.
- When an external provider is unreachable, return graceful fallback responses (HTTP 200 with degraded state) instead of unhandled 500 errors.
