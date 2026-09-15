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

---

## 5. Defensive Production Incident Pipeline & RCA

Ingest live production crashes (from Sentry, Datadog, or tracebacks) without risking credential leaks or prompt injection attacks:

```bash
# Ingest crash JSON or log, defang PII & injections, and create staged test
minuscorrect incident crash_payload.json --id INC-1042

# Or pipe directly via stdin
cat crash.json | python scripts/incident_to_golden.py --id INC-1042
```

### What Happens Automatically:
1. **PII & Credential Redaction:** Bearer tokens, JWTs, API keys, passwords, emails, IPs, and UUIDs are defanged.
2. **Prompt Injection Neutralization:** Hostile LLM hijack tokens (`<system>`, `[SYSTEM INSTRUCTION]`, `IGNORE PREVIOUS INSTRUCTIONS`, `eval(`, `os.system`) are defanged before reaching test files or agent context.
3. **Staged Reproduction Contract:** Generated in `tests/staging/test_incident_inc_1042.py`.
4. **Automated Root Cause Analysis:** Generated in `INCIDENT-RCA-inc_1042.md`.
5. **Controlled Contract Promotion:**
   ```bash
   ALLOW_GOLDEN_EDIT=1 git mv tests/staging/test_incident_inc_1042.py tests/golden/
   ```

---

## 6. Cloudflare Security Audit Bridge (`minuscorrect audit`)

Ingest adversarially confirmed vulnerabilities from `cloudflare/security-audit-skill`:

```bash
# Parse findings.json, quarantine unvalidated findings, and scaffold confirmed exploits
minuscorrect audit findings.json --output-dir tests/staging
```

- Confirmed exploits generate reproduction contracts in `tests/staging/test_sec_<id>.py`.
- Generates `SECURITY-AUDIT-SUMMARY.md` tracking confirmed vs rejected candidates.
- Unvalidated or rejected findings are quarantined to prevent test suite poisoning.

---

## 7. Blast-Radius Patch Validator (`minuscorrect patch`)

Validate agent-proposed unified diffs against zero-trust write boundaries:

```bash
# Validate and apply patch with blast radius restrictions
minuscorrect patch fix.diff --allowed-target src/parser.py

# Perform dry-run blast radius verification without modifying disk
minuscorrect patch fix.diff --check-only --allowed-target src/parser.py
```

- Strictly blocks path traversal (`..`).
- Blocks import-time execution hazards: modifications to `conftest.py`, `.github/`, `setup.py`, and `pyproject.toml`.
- Blocks modifications to `tests/golden/` without `ALLOW_GOLDEN_EDIT=1`.
