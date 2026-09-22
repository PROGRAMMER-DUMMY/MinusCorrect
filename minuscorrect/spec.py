"""
MinusCorrect Full-Stack Specification & Design Scaffold Engine.
Generates comprehensive PRD, TRD, Refero-style DESIGN.md (Tailwind v4 @theme,
CSS variables, motion tokens), APPFLOW.md, SCHEMA.sql (PostgreSQL/Supabase with RLS),
and Ask-Matt execution plans.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional


def generate_prd(project_name: str = "Enterprise SaaS Application", description: str = "") -> str:
    """
    Generate a complete Product Requirements Document (PRD).
    # verifies: tests/unit/test_spec.py
    """
    desc = description or "High-velocity, multi-tenant enterprise application with self-serve billing and strict tenant isolation."
    return f"""# Product Requirements Document (PRD)
# Project: {project_name}

## 1. Executive Summary & Problem Statement
- **Vision**: {desc}
- **Core Value Proposition**: Deliver enterprise-grade reliability, instant collaborative workflows, and zero-compromise security posture out of the box.
- **Primary Success Metrics**:
  - P95 latency < 350ms across all core workflows.
  - Zero client-side credential exposures or RLS tenant leaks.
  - 100% idempotency across billing and financial mutations.

## 2. User Personas & Permissions Matrix
| Persona | Access Level | Primary Objectives | Security Constraints |
| :--- | :--- | :--- | :--- |
| **Anonymous Visitor** | Public | Product discovery, documentation, marketing | Zero access to tenant data; strict rate limiting on auth endpoints. |
| **Workspace Member** | Authenticated | Read/write collaborative resources within assigned tenant | Tenant boundary strictly enforced (`tenant_id = auth.uid()`). |
| **Workspace Admin** | Authenticated | Billing management, team invites, API key provisioning | Step-up authentication for billing; SAQ A payment iframe isolation. |
| **System Operator** | Internal | Telemetry monitoring, incident triage, disaster drills | No raw PII in logs; operational access via short-lived credentials. |

## 3. Core Functional User Journeys
1. **Onboarding & Authentication**:
   - Frictionless signup via Magic Link / Social OAuth.
   - Bot protection (Turnstile / CAPTCHA) and per-IP velocity throttling to eliminate SMS toll fraud.
2. **Resource Management**:
   - Create, read, update, and soft-delete workspace assets.
   - Soft-deleted entities immediately excluded from collection and search endpoints.
3. **Billing & Subscriptions**:
   - Self-serve upgrade to Pro/Enterprise via Stripe Elements (SAQ A).
   - Asynchronous webhook queue with raw-body cryptographic signature verification.
4. **Data Privacy & Permanent Deletion**:
   - Self-serve GDPR/CCPA data export and permanent erasure across all downstream stores.

## 4. Non-Functional Requirements & SLAs
- **Availability**: 99.9% uptime SLA.
- **Recovery Time Objective (RTO)**: < 30 minutes with verified disaster recovery drill.
- **Recovery Point Objective (RPO)**: < 5 minutes via continuous WAL archiving.
"""


def generate_trd(project_name: str = "Enterprise SaaS Application", description: str = "") -> str:
    """
    Generate a comprehensive Technical Requirements Document (TRD).
    # verifies: tests/unit/test_spec.py
    """
    return f"""# Technical Requirements Document (TRD)
# Project: {project_name}

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
"""


def generate_refero_design(project_name: str = "Enterprise SaaS Application", theme_style: str = "obsidian") -> str:
    """
    Generate a Refero-style DESIGN.md specification with Tailwind CSS v4 (@theme) tokens,
    CSS variables, component variants, and curated design system references.
    # verifies: tests/unit/test_spec.py
    """
    return f"""# Refero-Grade Design System Specification
# Project: {project_name} | Style: {theme_style.title()}

Extracted and extended from **Refero Styles (`styles.refero.design`)** and world-class product benchmarks (Mobbin, Saaspo, PageFlows, Godly, Land-book, Dribbble, Behance, UI Sources, Lapa Ninja).

---

## 1. Tailwind CSS v4 Native Theme Configuration

```css
/* app/globals.css - Tailwind CSS v4 Native @theme Directive */
@import "tailwindcss";

@theme {{
  /* Primary Brand & Accent Colors */
  --color-brand-primary: var(--brand-primary);
  --color-brand-primary-hover: var(--brand-primary-hover);
  --color-brand-accent: var(--brand-accent);
  --color-brand-accent-subtle: var(--brand-accent-subtle);

  /* Surface Hierarchies */
  --color-surface-base: var(--surface-base);
  --color-surface-subtle: var(--surface-subtle);
  --color-surface-elevated: var(--surface-elevated);
  --color-surface-border: var(--surface-border);
  --color-surface-border-strong: var(--surface-border-strong);

  /* Semantic Typography Colors */
  --color-text-primary: var(--text-primary);
  --color-text-secondary: var(--text-secondary);
  --color-text-muted: var(--text-muted);

  /* Typography Scales */
  --font-display: "Geist", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  --font-mono: "Geist Mono", monospace;

  /* Elevation Shadows */
  --shadow-subtle: 0 1px 2px 0 rgb(0 0 0 / 0.05);
  --shadow-card: 0 4px 6px -1px rgb(0 0 0 / 0.08), 0 2px 4px -2px rgb(0 0 0 / 0.06);
  --shadow-elevated: 0 20px 25px -5px rgb(0 0 0 / 0.12), 0 8px 10px -6px rgb(0 0 0 / 0.08);

  /* Fluid Motion & Animation */
  --ease-spring: cubic-bezier(0.16, 1, 0.3, 1);
  --ease-out-smooth: cubic-bezier(0.22, 1, 0.36, 1);
  --duration-instant: 100ms;
  --duration-fast: 150ms;
  --duration-normal: 250ms;
}}

/* CSS Custom Properties / Design Tokens */
:root {{
  --brand-primary: #18181b;
  --brand-primary-hover: #27272a;
  --brand-accent: #6366f1;
  --brand-accent-subtle: #e0e7ff;

  --surface-base: #ffffff;
  --surface-subtle: #f8fafc;
  --surface-elevated: #ffffff;
  --surface-border: #e2e8f0;
  --surface-border-strong: #cbd5e1;

  --text-primary: #0f172a;
  --text-secondary: #475569;
  --text-muted: #94a3b8;
}}

[data-theme="dark"] {{
  --brand-primary: #f8fafc;
  --brand-primary-hover: #e2e8f0;
  --brand-accent: #818cf8;
  --brand-accent-subtle: #312e81;

  --surface-base: #09090b;
  --surface-subtle: #18181b;
  --surface-elevated: #1e1e24;
  --surface-border: #27272a;
  --surface-border-strong: #3f3f46;

  --text-primary: #f8fafc;
  --text-secondary: #94a3b8;
  --text-muted: #64748b;
}}
```

---

## 2. Core Component Variants & Micro-Interactions

### Button System (with Double-Submit Concurrency Guard)
- **Primary Action**:
  `bg-brand-primary text-surface-base hover:bg-brand-primary-hover active:scale-[0.98] transition-all duration-fast ease-spring rounded-lg px-4 py-2.5 font-medium shadow-subtle disabled:opacity-50 disabled:pointer-events-none`
- **Secondary Subtle**:
  `bg-surface-subtle border border-surface-border text-text-primary hover:bg-surface-border/50 active:scale-[0.98] transition-all duration-fast ease-spring rounded-lg px-4 py-2.5 font-medium`
- **Destructive**:
  `bg-red-600 text-white hover:bg-red-700 active:scale-[0.98] transition-all duration-fast rounded-lg px-4 py-2.5 font-medium`
- **Execution Guard**: All mutation buttons MUST bind `disabled={{isPending || isSubmitting}}` and display a spinner while promises remain unsettled.

### Cards & Elevation
- **Interactive Container**:
  `bg-surface-elevated border border-surface-border hover:border-surface-border-strong transition-colors duration-normal rounded-xl p-6 shadow-card`

### Modal & Dialog System (WCAG 2.1 AA Compliant)
- Mandatory focus traps (`aria-modal="true"`).
- Smooth backdrop blur (`backdrop-blur-sm bg-black/40`).
- Keyboard dismissal via `Escape` key restoring focus to triggering element.

---

## 3. Curated Design Inspiration Benchmarks
- **Refero Styles** (`https://styles.refero.design`): Extracted real-world design systems and tokens.
- **Mobbin** (`https://mobbin.com`): Real-world mobile and web user flows.
- **Saaspo** (`https://saaspo.com`): High-converting SaaS landing pages and component patterns.
- **PageFlows** (`https://pageflows.com`): User journey screen recordings and UX states.
- **Godly** (`https://godly.website`): Creative direction and micro-interaction benchmarks.
- **Land-book** (`https://land-book.com`): Editorial typography and product layouts.
"""


def generate_appflow(project_name: str = "Enterprise SaaS Application") -> str:
    """
    Generate an Appflow state machine specification in Mermaid format.
    # verifies: tests/unit/test_spec.py
    """
    return f"""# Application Flow & State Machine Specification
# Project: {project_name}

## 1. High-Level User Journey Diagram

```mermaid
stateDiagram-v2
    [*] --> Unauthenticated

    state Unauthenticated {{
        [*] --> Landing
        Landing --> AuthModal : Click Get Started
        AuthModal --> CaptchaCheck : Submit Credentials
        CaptchaCheck --> RateLimited : Exceeded Velocity (HTTP 429)
        CaptchaCheck --> OTPPending : Bot Challenge Passed
        OTPPending --> AuthenticatedSession : Verified Token
    }}

    state AuthenticatedSession {{
        [*] --> WorkspaceDashboard
        WorkspaceDashboard --> MutationWorkflow : Trigger Resource Action
        MutationWorkflow --> ConcurrencyLock : Button Pressed
        ConcurrencyLock --> BackendProcessing : Generate Idempotency Key
        BackendProcessing --> WorkspaceDashboard : Mutation Confirmed
        BackendProcessing --> DegradedState : External Timeout / Error

        WorkspaceDashboard --> BillingFlow : Upgrade Plan
        BillingFlow --> StripeIframe : Load Elements (SAQ A)
        StripeIframe --> WebhookQueue : Payment Authorization
        WebhookQueue --> WorkspaceDashboard : Entitlement Active
    }}

    AuthenticatedSession --> Unauthenticated : Server-Side Revocation
```

## 2. Route & State Transitions Matrix
| Source Route | Trigger Event | Guard / Verification | Destination Route |
| :--- | :--- | :--- | :--- |
| `/` (Landing) | Click "Login" | None | `/login` |
| `/login` | Submit Email | Velocity cap + Turnstile token check | `/auth/verify` (HTTP 200) or HTTP 429 |
| `/auth/verify` | Submit OTP | Match OTP; set httpOnly secure cookie | `/dashboard` |
| `/dashboard` | Submit Resource Mutation | Tenant verification + Idempotency check | `/dashboard` (Cache revalidated) |
| `/billing` | Click "Checkout" | CSRF token + Valid active session | Stripe Checkout Hosted Iframe |
| `/api/webhooks/stripe` | Inbound Event | Raw body cryptographic HMAC signature | HTTP 200 + Enqueue background job |
"""


def generate_schema(project_name: str = "Enterprise SaaS Application") -> str:
    """
    Generate a production-ready PostgreSQL / Supabase schema with mandatory RLS,
    foreign-key indexing, and audit logging.
    # verifies: tests/unit/test_spec.py
    """
    return f"""-- spec/SCHEMA.sql: Production PostgreSQL / Supabase Schema
-- Project: {project_name}
-- Mandatory Invariant: RLS ENABLED ON ALL TABLES. Zero unrestricted public access.

-- Extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- 1. Tenants Table
CREATE TABLE public.tenants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    plan TEXT NOT NULL DEFAULT 'free' CHECK (plan IN ('free', 'pro', 'enterprise')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
ALTER TABLE public.tenants ENABLE ROW LEVEL SECURITY;

-- 2. Tenant Members Table
CREATE TABLE public.tenant_members (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES public.tenants(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    role TEXT NOT NULL DEFAULT 'member' CHECK (role IN ('owner', 'admin', 'member')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, user_id)
);
ALTER TABLE public.tenant_members ENABLE ROW LEVEL SECURITY;

-- Foreign Key Indexes (Eliminates sequential scans at production scale)
CREATE INDEX idx_tenant_members_tenant_id ON public.tenant_members(tenant_id);
CREATE INDEX idx_tenant_members_user_id ON public.tenant_members(user_id);

-- RLS Policy: Users view only memberships for their user_id
CREATE POLICY "Users view their own memberships"
ON public.tenant_members FOR SELECT
USING (user_id = auth.uid());

-- 3. Core Resource Table (Projects)
CREATE TABLE public.projects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES public.tenants(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    description TEXT DEFAULT '',
    metadata JSONB NOT NULL DEFAULT '{{}}'::jsonb,
    deleted_at TIMESTAMPTZ, -- Soft delete support
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
ALTER TABLE public.projects ENABLE ROW LEVEL SECURITY;

-- Indexes on Foreign Key & Soft-Delete Filter
CREATE INDEX idx_projects_tenant_id ON public.projects(tenant_id);
CREATE INDEX idx_projects_active ON public.projects(tenant_id) WHERE deleted_at IS NULL;

-- RLS Policies: Multi-Tenant Isolation
CREATE POLICY "Tenant members can view active projects"
ON public.projects FOR SELECT
USING (
    tenant_id IN (
        SELECT tm.tenant_id FROM public.tenant_members tm
        WHERE tm.user_id = auth.uid()
    )
    AND deleted_at IS NULL
);

CREATE POLICY "Tenant admins can mutate projects"
ON public.projects FOR ALL
USING (
    tenant_id IN (
        SELECT tm.tenant_id FROM public.tenant_members tm
        WHERE tm.user_id = auth.uid() AND tm.role IN ('owner', 'admin')
    )
);

-- 4. Processed Webhook Events (Idempotency Ledger)
CREATE TABLE public.processed_webhooks (
    idempotency_key TEXT PRIMARY KEY,
    provider TEXT NOT NULL,
    event_type TEXT NOT NULL,
    processed_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
ALTER TABLE public.processed_webhooks ENABLE ROW LEVEL SECURITY;
-- Deliberately empty RLS policy: Accessible exclusively via backend service_role / RPC functions

-- 5. Audit Log Ledger
CREATE TABLE public.audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES public.tenants(id) ON DELETE CASCADE,
    actor_id UUID REFERENCES auth.users(id),
    action TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    payload JSONB NOT NULL DEFAULT '{{}}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
ALTER TABLE public.audit_logs ENABLE ROW LEVEL SECURITY;

CREATE INDEX idx_audit_logs_tenant_id ON public.audit_logs(tenant_id);
CREATE INDEX idx_audit_logs_actor_id ON public.audit_logs(actor_id);
CREATE INDEX idx_audit_logs_created_at ON public.audit_logs(created_at DESC);

CREATE POLICY "Tenant owners and admins view audit logs"
ON public.audit_logs FOR SELECT
USING (
    tenant_id IN (
        SELECT tm.tenant_id FROM public.tenant_members tm
        WHERE tm.user_id = auth.uid() AND tm.role IN ('owner', 'admin')
    )
);
"""


def generate_plan(project_name: str = "Enterprise SaaS Application", description: str = "") -> str:
    """
    Generate an Ask-Matt tracer-bullet implementation plan.
    # verifies: tests/unit/test_spec.py
    """
    from minuscorrect.orchestrator import generate_ask_matt_plan
    return generate_ask_matt_plan(idea=f"{project_name}: {description}" if description else project_name)


def scaffold_spec_suite(
    output_dir: Path,
    project_name: str = "Enterprise Application",
    description: str = "",
) -> Dict[str, Path]:
    """
    Scaffolds the canonical full-stack spec suite (PRD, TRD, DESIGN, APPFLOW, SCHEMA, PLAN).
    # verifies: tests/unit/test_spec.py
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    files = {
        "PRD.md": generate_prd(project_name, description),
        "TRD.md": generate_trd(project_name, description),
        "DESIGN.md": generate_refero_design(project_name),
        "APPFLOW.md": generate_appflow(project_name),
        "SCHEMA.sql": generate_schema(project_name),
        "PLAN.md": generate_plan(project_name, description),
    }

    written: Dict[str, Path] = {}
    for filename, content in files.items():
        target = output_dir / filename
        target.write_text(content, encoding="utf-8")
        written[filename] = target

    return written
