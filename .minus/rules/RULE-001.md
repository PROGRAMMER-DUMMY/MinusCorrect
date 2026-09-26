---
id: RULE-001
title: "Zero Secret & PII Logging"
scope: security
enforcement: strict
created_at: "2026-09-24T05:45:07.896303+00:00"
---

# RULE-001: Zero Secret & PII Logging

- **Scope**: `security`
- **Enforcement**: `strict`

## Invariant Instruction for Autonomous Agents
Never write raw secrets, API tokens, card numbers, or customer PII to terminal logs or exceptions. Defang before emission.

## Prohibited Patterns & Anti-Patterns
- `sk_live_`
- `Bearer `
- `password=`
- `secret=`