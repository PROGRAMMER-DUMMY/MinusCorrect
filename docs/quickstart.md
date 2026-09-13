# Quickstart & Workflow Guide

This guide covers setup, routine developer workflows, and agent dispatch instructions for **MinusCorrect**.

---

## 1. Installation & Repository Setup

### Option A: Direct Repository Integration (Built-in)
If you have cloned or initialized MinusCorrect in your repository:

1. Install the Git pre-commit hook:
   ```bash
   cp scripts/verify_integrity.py .git/hooks/pre-commit # or invoke via shell script wrapper
   ```
2. Run an initial integrity audit:
   ```bash
   python scripts/verify_integrity.py --fix
   ```

### Option B: Integration via Pre-Commit Package (Any Repository)
To add MinusCorrect to any external repository in 60 seconds, add this entry to your root `.pre-commit-config.yaml`:

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
python scripts/verify_integrity.py
```

### Auto-Remediation (`--fix`)
If temporary debug logs or `[DEBUG]` traces were injected during debugging sessions, do not waste time manually editing files. Run:
```bash
python scripts/verify_integrity.py --fix
```
The script will automatically strip all `[DEBUG]` statements from staged files, re-stage the clean versions, and report the actions taken.

---

## 3. Dispatching Autonomous Coding Agents

When assigning a bug fix, refactor, or feature implementation to an autonomous agent (Claude Code, Google Antigravity, OpenAI Codex, Cursor), follow this standardized prompt pattern:

### Standard Agent Prompt Template
```text
Task: Fix the defect identified in tests/golden/test_cache_lru.py.

Constraints & Operating Rules:
1. Boundary Invariant: The acceptance specification in 'tests/golden/test_cache_lru.py' is STRICTLY READ-ONLY. Do NOT loosen assertions, remove tests, or alter contract values.
2. Actuator Isolation: Confine all code edits strictly to 'src/cache.py'. Do not modify sibling modules.
3. No Shortcuts: Do not catch exceptions with blanket 'try/except: pass', do not insert arbitrary 'time.sleep()' delays, and do not add synthetic fallback defaults.
4. Loop Ceiling: You have a maximum of 4 test execution iterations. If you fail twice consecutively with the same error signature, inject temporary '[DEBUG]' logging statements into 'src/cache.py' to observe runtime variable values.
5. Cleanup: Before completing the task, run 'python scripts/verify_integrity.py --fix' to ensure all temporary debug traces are purged.
6. Adhere strictly to AGENTS.md.
```

---

## 4. Supervised Execution Mode

For fully automated agent workflows, execute test cycles under the out-of-process supervisor:

```bash
python scripts/supervisor.py check --target src/cache.py --test-cmd "pytest tests/golden/test_cache_lru.py" --iteration 1
```

If the agent reaches iteration 4 without passing:
- The supervisor triggers an **atomic rollback**, restoring `src/cache.py` to its initial clean state.
- It writes `DIAGNOSTIC-REPORT.md` summarizing the failure signature, observed error logs, and escalation path.
- The human maintainer spends 2 minutes reviewing the report instead of debugging broken repository state.
