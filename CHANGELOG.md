# Changelog

All notable changes to **MinusCorrect** will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.1.0] - 2026-09-14

### Initial Release: Systemic Integrity & Closed-Loop Verification Protocol

#### Added
- **Canonical Core Specification (`.agent-rules/systemic-integrity.md`)**:
  - Intent Reconstruction & Evidence Over Labels philosophy.
  - Non-negotiable engineering invariants: Root-cause resolution, no synthetic magic constants, bounded actuators, held-out stress verification.
  - The Two-Category Docstring & Comment Auditing Standard (Operational Claims requiring test receipts vs. Tagged Contextual Rationale).
  - 4-Iteration failure ceiling with automated diagnostic escalation.
  - Scaffolding debug trace injection (`[DEBUG]`) and mandatory cleanup.
- **Multi-Agent Native Bootstraps**:
  - `CLAUDE.md`: Universal directives and docstring rules for Claude Code.
  - `AGY.md`: Native operational directives for Google Antigravity (AGY).
  - `.codex/instructions.md`: Rules and constraints for OpenAI Codex.
  - `.cursorrules`: Rules and constraints for Cursor IDE.
- **Test Stratification Architecture**:
  - `tests/golden/`: Immutable acceptance and contract regression test boundary.
  - `tests/unit/`: Mutable developer unit test suite for local feature development.
- **Deterministic Enforcement**:
  - `scripts/verify_integrity.py`: Cross-platform pre-commit verifier blocking unauthorized edits to golden tests, stripping leftover debug tags, and flagging unverified docstring claims.
  - `.git/hooks/pre-commit`: Active physical hook wired directly to git commit lifecycle.
  - `.semgrep/unverified-claims.yml`: Static analysis rule flagging unverified docstring superlatives.
  - `.github/workflows/integrity.yml`: Out-of-band GitHub Actions CI verification pipeline.
- **Documentation & Open Source Foundations**:
  - Comprehensive root `README.md` with system architecture diagrams and quickstart guides.
  - `LICENSE`: MIT License.
  - `CONTRIBUTING.md`: Guidelines for proposing changes and authoring contract tests.
