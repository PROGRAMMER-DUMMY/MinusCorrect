---
id: RULE-003
title: "Ephemeral Worktree Isolation"
scope: process
enforcement: strict
created_at: "2026-09-24T05:45:07.925705+00:00"
---

# RULE-003: Ephemeral Worktree Isolation

- **Scope**: `process`
- **Enforcement**: `strict`

## Invariant Instruction for Autonomous Agents
All test executions and agent fixes must run inside isolated ephemeral git worktrees with ambient credentials stripped.

## Prohibited Patterns & Anti-Patterns
- `--worktree`
- `--isolate-env`