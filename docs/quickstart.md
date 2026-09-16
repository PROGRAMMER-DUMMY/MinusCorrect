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

---

## 8. Operational Webhook Egress (`--webhook-url`)

Stream real-time operational notifications to Slack, PagerDuty, or Datadog upon supervisor events:

```bash
# Pass webhook URL via flag
minuscorrect run --webhook-url "https://hooks.slack.com/services/..." -- pytest tests/staging/test_incident_1042.py

# Or export via environment variable
export MINUSCORRECT_WEBHOOK_URL="https://alerts.internal.net/events"
minuscorrect run -- pytest tests/staging/test_incident_1042.py
```

Dispatched events include:
- `RUN_SUCCESS`: Test harness passed; patch verified.
- `CIRCUIT_BREAKER_ABORT`: 4-iteration ceiling reached; atomic rollback executed and diagnostic report written.
- `TIMEOUT_ABORT`: Execution exceeded timeout threshold.
- `TAMPERING_DETECTED`: Attempted unauthorized modification of `tests/golden/`.

---

## 9. Ephemeral Git Worktree Isolation (`--worktree`)

Prevent `.git/index.lock` collisions and workspace contamination during parallel agent runs or CI executions:

```bash
# Execute supervised test run inside an isolated, disposable git worktree
minuscorrect run --worktree --session-id parallel-worker-1 -- pytest tests/staging/
```

- Spawns an isolated `git worktree` checkout under `.minuscorrect/worktrees/`.
- Executes all tests and supervisor steps inside the temporary worktree.
- Automatically cleans up the worktree and disposable branch upon completion.

---

## 10. Autonomous PR Decoupling (`minuscorrect pr`)

Enforce the core invariant that autonomous agents must never commit directly to production default branches:

```bash
# Generate a structured Draft Pull Request proposal
minuscorrect pr --session-id cache-lru --summary "Fix LRU cache eviction key boundary"

# Optionally create an isolated branch and commit verified files
minuscorrect pr --session-id cache-lru --commit-and-branch
```

- Generates `DRAFT-PR-<session_id>.md` containing:
  - Verified test receipts and execution iteration counts.
  - Blast-radius summary and diff statistics.
  - Human review checklist and local reproduction instructions.

---

## 11. Hardened Container Execution (Docker)

Deploy MinusCorrect inside a secure, unprivileged container sandbox for CI/CD runners or staging environments:

```bash
# Build the hardened container image
docker build -t minuscorrect:latest .

# Run supervisor inside container mounting the target workspace
docker run --rm -v $(pwd):/workspace minuscorrect:latest run -- pytest tests/golden/
```

---

## 12. Model Context Protocol (MCP) Server

Expose MinusCorrect's execution containment and verification tools natively to any MCP-compatible coding agent (Claude Code, Cursor, Google Antigravity, Cline, Windsurf) over standard JSON-RPC:

```bash
# Launch MCP server over stdio
minuscorrect mcp

# Or via dedicated binary
mc-mcp
```

### Supported MCP Tools:
- `minuscorrect_run`: Execute tests under the 4-iteration circuit breaker with rollback.
- `minuscorrect_verify`: Verify golden test protection, anti-swallowing AST rules, and debug tag cleanup.
- `minuscorrect_validate_patch`: Validate a unified diff against write blast-radius rules (blocks `conftest.py`, `pyproject.toml`, path traversal).
- `minuscorrect_ingest_incident`: Redact secrets/PII, defang injections, and synthesize staged reproduction contracts from crash JSON.
- `minuscorrect_create_draft_pr`: Generate a decoupled Draft PR proposal (`DRAFT-PR-<id>.md`).
- `minuscorrect_status`: Inspect session history and iteration count.

### Client Configuration (`claude_desktop_config.json` or `.gemini/settings.json`):
```json
{
  "mcpServers": {
    "minuscorrect": {
      "command": "minuscorrect",
      "args": ["mcp"]
    }
  }
}
```

---

## 13. Agent Skills Library (`skills/`)

MinusCorrect bundles standalone, declarative skill specifications for agent pre-execution reasoning:

- **`skills/minuscorrect-council/SKILL.md`**: Multi-perspective deliberation protocol (Contrarian, First Principles, Expansionist, Outsider, Executor) to stress-test high-risk bug fixes and architectural decisions before burning iteration budgets.
- **`skills/minuscorrect-security/SKILL.md`**: Fused 10-domain security checklist (secrets, input validation, SQLi, XSS, CSRF, auth/RLS, sensitive logging, crypto, dependencies) with adversarial PoC contract synthesis for closed-loop remediation.
