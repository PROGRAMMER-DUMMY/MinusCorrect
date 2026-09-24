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

7. [Smart Intent Router](quickstart.md#4-smart-intent-router-minuscorrect-route)
   - Natural language classification into deterministic operational pipelines
   - Autonomous routing to Council, Ask-Matt, Incident, Spec, or Audit

8. [Second-Brain Store & Task Lifecycles (`.minus/`)](quickstart.md#5-second-brain-ticket-lifecycle-store--minus)
   - Persistent task management: `tickets/open/` -> `tickets/completed/`
   - Cryptographic machine receipts with commit SHAs and exit codes
   - Incident telemetry and post-mortem indexing

9. [10-Domain Pre-Launch Operational & Security Audit](quickstart.md#7-10-domain-pre-launch-security--operational-audit-minuscorrect-audit---pre-launch)
   - Automated detection of NEXT_PUBLIC_ leaks, missing RLS, and BOLA/IDOR
   - Webhook HMAC verification, unindexed foreign keys, and PII log scrubbing

10. [Anti-Benchmark-Maxxing & Anti-Cheating Guardian](quickstart.md#8-anti-benchmark-maxxing--anti-cheating-guardian-minuscorrect-anti-cheat)
    - AST detection of hardcoded test fixture branch bypasses
    - Tautological assertion detection and exception swallowing audits

11. [Git-Pointer Time Machine & Unified Diff Snapshots](quickstart.md#14-git-pointer-time-machine--unified-diff-snapshots-minuscorrect-diff)
    - Automated patch capture in `.minus/diffs/<ticket_id>.patch`
    - Native git reference registration under `refs/minus/tickets/<ticket_id>`
    - Audit logs with base/head commit SHAs, file lists, and diff stats

12. [Atomic Rollback Engine & Verification Gate](quickstart.md#15-atomic-rollback-engine-with-verification-gate-minuscorrect-rollback)
    - Deterministic `git revert` of ticket head commits
    - Safe pre-flight working tree checks excluding `.minus/` metadata
    - Post-rollback test verification gate with automatic reset on failure
    - State transition to `.minus/tickets/rolled_back/` (or `--reopen` to `open/`)

13. [Cognitive Intent Ingestion & Rule Registration](quickstart.md#16-cognitive-intent-ingestion--rule-registration-minuscorrect-intake)
    - Natural language prompt intake without manual ticket creation
    - Persistent rule registration in `.minus/rules/`
    - MinusCouncil deliberation and Ask-Matt ticket decomposition

14. [Deep Web Research Swarm & Knowledge Ontology](quickstart.md#17-deep-web-research-swarm--knowledge-ontology-minuscorrect-research)
    - 3-wave parallel subagent exploration across technical domains
    - Dynamic query evolution based on entity discovery
    - Contradiction detection and persistent ontology storage in `.minus/research/`
