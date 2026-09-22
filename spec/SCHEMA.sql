-- spec/SCHEMA.sql: Production PostgreSQL / Supabase Schema
-- Project: Enterprise Application
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
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
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
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
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
