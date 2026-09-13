# MinusCorrect Documentation Hub

Welcome to the documentation suite for **MinusCorrect**, the systemic integrity and anti-shortcut verification protocol for autonomous coding agents.

---

## Documentation Index

1. [Quickstart & Workflow Guide](quickstart.md)
   - Installing the pre-commit hook in any repository
   - Running the local integrity verifier with auto-remediation (`--fix`)
   - Dispatching agents with bounded actuators

2. [Golden Contracts & Test Stratification](golden-contracts.md)
   - Immutable acceptance contracts (`tests/golden/`)
   - Mutable developer unit suites (`tests/unit/`)
   - The break-glass override protocol (`ALLOW_GOLDEN_EDIT=1`)

3. [Autonomous Supervisor & Circuit Breaker](supervisor-guide.md)
   - Out-of-process process supervisor (`scripts/supervisor.py`)
   - Normalized SHA-256 error hashing
   - Epistemic debug trace injection at iteration 3
   - Transactional isolation and automatic atomic rollback on hard abort
   - Reading and resolving `DIAGNOSTIC-REPORT.md`

4. [Two-Category Docstring & Claim Auditing](docstring-standard.md)
   - Category 1: Operational Guarantees (`O(1)`, `thread-safe`, `idempotent`)
   - Automated `# verifies:` test receipts
   - Banned superlatives (`universal`, `bulletproof`, `blazing fast`)
   - Category 2: Contextual Rationale (`# Rationale:`, `# Workaround:`, `# Assumption:`)
   - Static AST and Semgrep inspection rules

5. [Multi-Agent Integration Matrix](agent-matrix.md)
   - Universal root instruction standard (`AGENTS.md`)
   - Tool bootstraps: Claude Code, Google Antigravity, OpenAI Codex, Cursor
   - Preventing prompt drift and state pollution across toolchains

6. [Enterprise CI & Git Host Governance](ci-governance.md)
   - Host-level protection via `.github/CODEOWNERS`
   - Out-of-band GitHub Actions CI (`.github/workflows/integrity.yml`)
   - Mitigating the Watcher Paradox and shell-level bypasses
