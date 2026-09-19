---
name: minuscorrect
description: Autonomous corrective runtime, process isolation supervisor, and blast-radius gate for coding agents. Use when fixing bugs, applying agent diffs, investigating production crashes, or verifying repository integrity.
---

# MinusCorrect Agent Skill

MinusCorrect provides autonomous execution containment, circuit breaking, token sandboxing, and write blast-radius validation for autonomous coding agents (Claude Code, Antigravity CLI/IDE, Cursor, Aider, OpenHands).

## When to Activate

- Running test-driven bug repairs with a hard 4-iteration loop ceiling
- Modifying code where errors must not corrupt the git index or main branch
- Defensively ingesting Sentry/Datadog crash dumps into reproduction tests
- Validating agent diff patches against path traversal and build/container file tampering
- Running pre-flight environment checks before long-running autonomous runs

---

## Core Agent Workflows

### 1. Pre-Flight Diagnostic Check
Before executing complex multi-file refactors or autonomous repair cycles, run the environment doctor:

```bash
minuscorrect doctor
```
Or for machine-readable JSON:
```bash
minuscorrect doctor --json
```

### 2. Supervised Repair Cycle (Circuit Breaker & Rollback)
Instead of invoking `pytest` directly in an unconstrained loop, wrap execution in the supervisor:

```bash
minuscorrect run --worktree --isolate-env --timeout 180.0 -- pytest tests/staging/
```

**What the Supervisor Guarantees:**
- **4-Loop Hard Ceiling:** Aborts automatically if an identical error hash repeats or on iteration 4.
- **Atomic Rollback:** If aborted, reverts tracked modifications and purges untracked scratch files while preserving `.env` and configuration files.
- **Execution Sandboxing (`--isolate-env`):** Strips ambient secrets (`AWS_*`, `GITHUB_TOKEN`, `*_SECRET`) from the subprocess test environment.
- **Git Worktree Isolation (`--worktree`):** Executes all tests inside an isolated ephemeral worktree, keeping the working directory clean.

### 3. Write Blast-Radius Patch Validation
Before applying an agent's proposed unified diff:

```bash
# Dry-run check
minuscorrect patch --check-only patch.diff

# Apply atomically only if clean
minuscorrect patch --allowed-target minuscorrect/supervisor.py patch.diff
```

Blocks modifications to:
- `tests/golden/` (unless `ALLOW_GOLDEN_EDIT=1`)
- `pyproject.toml`, `setup.py`, `conftest.py`
- `Makefile`, `tox.ini`, `noxfile.py`
- `Dockerfile`, `Containerfile`, `docker-compose*.yml`
- `.gitlab-ci.yml`, `.circleci/`
- Any file outside `--allowed-target`

### 4. Crash Telemetry Ingestion (`minuscorrect incident`)
When given a crash report or Sentry traceback:

```bash
minuscorrect incident crash_payload.json --id INC-1042
```
Outputs:
- Sanitized reproduction test in `tests/staging/test_inc_1042.py`
- Markdown Root Cause Analysis in `INCIDENT-RCA-1042.md`

### 5. Pre-Commit Systemic Integrity Verification
Before committing or completing a task:

```bash
minuscorrect verify --fix --strict
```
Auto-strips leftover `[DEBUG]` scaffolding and validates docstring contract receipts.
