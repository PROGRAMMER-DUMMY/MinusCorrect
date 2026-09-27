---
name: minuscorrect-intake
description: Cognitive intent ingestion and automated task orchestration. Translates raw user instructions, feature ideas, and architectural questions into formal invariants, auto-registered project rules in .minus/rules/, 5-advisor LLM Council syntheses, and executable Ask-Matt tracer-bullet tickets. Triggers: '/intake', '/plan', 'intake', 'cognitive intake', 'ingest intent'.
---

# MinusCorrect Cognitive Intent Ingestion Skill

MinusCorrect provides cognitive intent ingestion to transform unstructured, natural language user prompts into formal invariants, persistent project rules, architectural trade-off evaluations, and decomposed tracer-bullet tickets.

## When to Activate

- Turning a high-level feature idea or refactor request into concrete specifications and tickets
- Auto-extracting behavioral invariants and constraints from user prompts
- Automatically convening the 5-advisor LLM Council before starting implementation
- Generating Matt Pocock Spec-to-Tickets DAGs and persisting them into `.minus/tickets/open/`

---

## Core Commands & Workflows

### 1. Ingest Natural Language Request
```bash
minuscorrect intake "Add Redis rate limiting to our auth endpoints with a 4-iteration ceiling and zero credential leakage"
```
Or use the alias:
```bash
minuscorrect plan "Refactor payment webhook handling to be strictly idempotent"
```

### 2. Output Format Options
```bash
# Markdown plan (default)
minuscorrect intake "Implement background task runner"

# Machine-readable JSON
minuscorrect intake "Implement background task runner" --json

# Dry-run without writing to .minus/
minuscorrect intake "Implement background task runner" --no-save
```

### 3. What the Intake Pipeline Generates
1. **Extracted Invariants**: Discovers security, data integrity, and blast-radius rules from the prompt text.
2. **Auto-Registered Rules**: Writes new project rules to `.minus/rules/RULE-xxx.md`.
3. **Council Stage-1 Synthesis**: Generates 5 distinct lenses (Contrarian, First Principles, Expansionist, Outsider, Executor).
4. **Tracer-Bullet Tickets**: Generates DAG tickets and saves them into `.minus/tickets/open/` with assigned domain specialist personas.
