---
name: rollback
description: >-
  Atomic Rollback Engine: safely revert an agent ticket commit with automated post-revert verification gates.
---
# MinusCorrect Second-Brain Store & Rollback Engine Skill

MinusCorrect embeds a file-system backed Second Brain (`.minus/`) directly into the repository to manage ticket lifecycles, project rules, execution receipts, and atomic rollbacks.

## When to Activate

- Managing task lifecycles across `open/`, `completed/`, and `rolled_back/`
- Registering and inspecting repository-wide natural language project rules in `.minus/rules/`
- Reviewing unified diff snapshots of code changes produced by autonomous agents
- Reverting a failed or problematic ticket commit with automated verification gates

---

## Core Commands & Workflows

### 1. Ticket Lifecycle Management
```bash
# List all tickets or filter by status
minuscorrect ticket list
minuscorrect ticket list --status open

# Create a new ticket
minuscorrect ticket create -t "Implement Redis Cache" --role "Distributed Systems Engineer" --target "src/cache.py"

# Inspect ticket details
minuscorrect ticket view T-001

# Close ticket and record execution receipt
minuscorrect ticket close T-001 --commit HEAD --test-cmd "pytest tests/unit/" --exit-code 0
```
Transitions ticket from `.minus/tickets/open/` to `.minus/tickets/completed/`, records verification receipts, and snapshots git diff patches into `.minus/diffs/`.

### 2. Project Rule Management
```bash
# List all project rules
minuscorrect rule list

# Register a new project rule
minuscorrect rule add "Enforce UTC Timestamps" \
  --instruction "All database models and API payloads must use UTC ISO-8601 timestamps with timezone offsets." \
  --scope code \
  --enforcement strict

# View a specific rule
minuscorrect rule view RULE-001
```

### 3. Unified Diff Inspection
Inspect the exact patch associated with an agent's ticket:
```bash
minuscorrect diff T-001
```

### 4. Atomic Rollback Engine
Safely revert an agent ticket's commit while running verification gates:
```bash
# Revert commit and verify tests pass post-revert
minuscorrect rollback T-001

# Move ticket back to open/ for repair instead of rolled_back/
minuscorrect rollback T-001 --reopen
```
Ensures:
- Pre-flight working tree is clean.
- `git revert` is applied cleanly.
- Test suite verifies the revert left the codebase in a healthy state. If tests fail post-revert, the revert is automatically rolled back.
