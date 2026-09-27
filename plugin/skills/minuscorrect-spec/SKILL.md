---
name: minuscorrect-spec
description: Enterprise specification suite scaffolding and management. Automatically generates PRD, TRD, Refero-grade DESIGN.md (Tailwind CSS v4 @theme, design tokens, CSS variables), APPFLOW.md state transitions, PostgreSQL/Supabase SCHEMA.sql with Row-Level Security (RLS) enabled by default, and Ask-Matt PLAN.md. Triggers: '/spec', 'scaffold spec', 'generate prd', 'generate schema', 'refero design'.
---

# MinusCorrect Specification Suite Skill

MinusCorrect provides automated scaffolding of enterprise-grade specifications that bridge product intent, technical invariants, Refero-grade UI design tokens, database schemas with strict security, and executable agent execution plans.

## When to Activate

- Scaffolding a new project or major feature from ground up
- Generating a Product Requirements Document (PRD) or Technical Requirements Document (TRD)
- Creating a Refero-style UI/UX design system with Tailwind CSS v4 `@theme` tokens and CSS variables
- Designing PostgreSQL / Supabase database schemas with Row-Level Security (RLS) policies by default
- Building an executable Ask-Matt implementation plan (`PLAN.md`)

---

## Core Commands & Workflows

### 1. Scaffold Full Specification Suite
Generate all 6 specification documents in one command:
```bash
minuscorrect spec init --dir spec --name "My Enterprise Project" --desc "AI-powered real-time platform"
```

Generates:
- `spec/PRD.md`: Problem statement, target personas, functional requirements, and non-goals.
- `spec/TRD.md`: Architectural topology, API contracts, latency/throughput SLAs, and invariant gates.
- `spec/DESIGN.md`: Refero-grade UI tokens, Tailwind CSS v4 `@theme` configuration, accessible contrast pairs, component motion tokens.
- `spec/APPFLOW.md`: User journeys, state transition machines, and navigation graphs.
- `spec/SCHEMA.sql`: PostgreSQL/Supabase relational schema with `ENABLE ROW LEVEL SECURITY` on every table and tenant isolation policies.
- `spec/PLAN.md`: Ask-Matt Spec-to-Tickets DAG with tracer bullets, protected boundaries, and specialist assignments.

### 2. Generate Individual Artifacts
```bash
minuscorrect spec generate prd --name "Payment Service"
minuscorrect spec generate design --name "Analytics Dashboard"
minuscorrect spec generate schema --name "Multi-Tenant CRM"
```

### 3. Overwrite Safety
Existing spec files are protected by default. To overwrite:
```bash
minuscorrect spec generate schema --force
```
