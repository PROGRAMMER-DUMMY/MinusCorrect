---
id: RULE-002
title: "Mutating Request Idempotency"
scope: distributed
enforcement: strict
created_at: "2026-09-24T05:45:07.913188+00:00"
---

# RULE-002: Mutating Request Idempotency

- **Scope**: `distributed`
- **Enforcement**: `strict`

## Invariant Instruction for Autonomous Agents
All state-mutating handlers and external webhook consumers must enforce unique Idempotency-Key validation to prevent duplicate processing.

## Prohibited Patterns & Anti-Patterns
- `Idempotency-Key`
- `idempotency_key`