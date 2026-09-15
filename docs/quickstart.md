# Quickstart & Workflow Guide

This guide covers setup, routine developer workflows, and agent dispatch instructions for **MinusCorrect**.

---

## 1. Installation & Repository Setup

### Option A: Python Package Installation (Recommended)
Install MinusCorrect directly into your development environment or agent sandbox:

```bash
# From PyPI or internal registry
pip install minuscorrect

# Or in editable mode from source
git clone https://github.com/PROGRAMMER-DUMMY/MinusCorrect.git
cd MinusCorrect
pip install -e .
```

### Option B: Pre-Commit Hook Integration (Any Repository)
To add MinusCorrect systemic integrity verification to any external repository in 60 seconds, add this block to your root `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/PROGRAMMER-DUMMY/MinusCorrect
    rev: main
    hooks:
      - id: verify-integrity
```

Then install the hook:
```bash
pre-commit install
```

---

## 2. Daily Developer & Maintainer Workflow

MinusCorrect is optimized to minimize human developer overhead:

### Running Verification Locally
Before committing code, verify repository compliance:
```bash
minuscorrect verify
```
Or use the direct script wrapper:
```bash
python scripts/verify_integrity.py
```

### Auto-Remediation (`--fix`)
If temporary debug logs or `[DEBUG]` traces were injected during debugging sessions, do not waste time manually editing files. Run:
```bash
minuscorrect verify --fix
```
The command automatically strips all `[DEBUG]` statements from staged files, re-stages the clean versions, and reports the actions taken.

---

## 3. Supervised Agent Execution Mode

For fully automated agent workflows, execute test cycles under the out-of-process supervisor:

```bash
# Run supervised cycle on a specific golden test
minuscorrect run --session-id cache-lru -- pytest tests/golden/test_cache_lru.py

# Inspect active supervisor session history and error signatures
minuscorrect status --session-id cache-lru

# Reset session after completing task
minuscorrect reset --session-id cache-lru
```

If the agent reaches iteration 4 without passing:
- The supervisor triggers an **atomic git-tree rollback**, restoring the entire repository to its initial clean state.
- It writes `DIAGNOSTIC-REPORT.md` summarizing the failure signature, observed error logs, and escalation path.
- The human maintainer spends 2 minutes reviewing the report instead of debugging broken repository state.

---

## 4. Dispatching Autonomous Coding Agents

When assigning a bug fix, refactor, or feature implementation to an autonomous agent (Claude Code, Google Antigravity, OpenAI Codex, Cursor), follow this standardized prompt pattern:

### Standard Agent Prompt Template
```text
Task: Fix the defect identified in tests/golden/test_cache_lru.py.

Constraints & Operating Rules:
1. Boundary Invariant: The acceptance specification in 'tests/golden/test_cache_lru.py' is STRICTLY READ-ONLY. Do NOT loosen assertions, remove tests, or alter contract values.
2. Actuator Isolation: Confine all code edits strictly to 'src/cache.py'. Do not modify sibling modules.
3. No Shortcuts: Do not catch exceptions with blanket 'try/except: pass', do not insert arbitrary 'time.sleep()' delays, and do not add synthetic fallback defaults.
4. Loop Ceiling: You have a maximum of 4 test execution iterations. If you fail twice consecutively with the same error signature, inject temporary '[DEBUG]' logging statements into 'src/cache.py' to observe runtime variable values.
5. Verification & Cleanup: Run test iterations using 'minuscorrect run -- pytest tests/golden/test_cache_lru.py'. Before completing the task, run 'minuscorrect verify --fix' to ensure all temporary debug traces are purged.
6. Adhere strictly to AGENTS.md.
```
