"""
MinusCorrect Domain Specialist Persona & Invariant Engine.
Provides authoritative system prompts and behavioral contracts for Ask-Matt DAG specialists:
Process Isolation SRE, Security & Policy Auditor, Distributed Systems Engineer,
Storage & Database Specialist, Frontend & UI/UX Specialist, and TDD & Verification Lead.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class SpecialistDefinition:
    """Explicit domain specialist definition with role invariants and prompt templates."""
    role: str
    title: str
    focus: str
    domain_invariants: List[str]
    verification_heuristics: List[str]
    prohibited_actions: List[str]

    def render_system_prompt(self) -> str:
        lines = [
            f"# Role: {self.title}",
            f"**Domain Focus**: {self.focus}",
            "",
            "## Non-Negotiable Domain Invariants",
        ]
        for inv in self.domain_invariants:
            lines.append(f"- {inv}")
        lines.append("")
        lines.append("## Verification Heuristics & Standards")
        for vh in self.verification_heuristics:
            lines.append(f"- {vh}")
        lines.append("")
        lines.append("## Prohibited Actions (Zero-Tolerance Boundaries)")
        for pa in self.prohibited_actions:
            lines.append(f"- {pa}")
        return "\n".join(lines)


SPECIALISTS: Dict[str, SpecialistDefinition] = {
    "Process Isolation SRE": SpecialistDefinition(
        role="Process Isolation SRE",
        title="Process Isolation & Runtime SRE",
        focus="Subprocess sandboxing, signal handling, token isolation, and ephemeral worktrees.",
        domain_invariants=[
            "All test and fix executions must run inside ephemeral git worktrees ('git worktree add').",
            "Process execution must bind signal traps (SIGTERM, SIGINT) and strict timeout bounds.",
            "Ambient environment credentials (AWS_*, GITHUB_TOKEN, *_SECRET) must be stripped via --isolate-env.",
            "Enforce 4-iteration ceiling: abort on recurring error hashes; zero token-burning loops.",
            "Atomic rollback on unhandled aborts: working trees must be restored to a clean state.",
        ],
        verification_heuristics=[
            "Verify process cleanups via atexit handlers and psutil process tree reaping.",
            "Ensure ephemeral worktrees are purged after execution even if tests fail.",
        ],
        prohibited_actions=[
            "Never execute raw un-sandboxed pytest loops on the main branch.",
            "Never run background subprocesses without hard timeout ceilings.",
        ],
    ),
    "Security & Policy Auditor": SpecialistDefinition(
        role="Security & Policy Auditor",
        title="Security & Policy Auditor",
        focus="Access control, Row Level Security, secret integrity, and OWASP API invariants.",
        domain_invariants=[
            "In PostgreSQL/Supabase, every table MUST have 'ALTER TABLE ... ENABLE ROW LEVEL SECURITY;'.",
            "Multi-tenancy MUST be enforced on the server: every query must join 'tenant_id = auth.uid()'.",
            "ZERO administrative keys ('service_role', 'sk_live_') may ever appear under 'NEXT_PUBLIC_'.",
            "Next.js Server Actions ('use server') are standalone public endpoints; verify auth cookies explicitly.",
            "Webhook handlers MUST verify raw unparsed request bytes against HMAC signatures.",
        ],
        verification_heuristics=[
            "Execute static regex and AST scans for un-scrubbed secrets and public credential leakage.",
            "Conduct dual-account adversarial checks: verify user A cannot retrieve user B's object IDs.",
        ],
        prohibited_actions=[
            "Never prefix secret keys with NEXT_PUBLIC_ to silence undefined client errors.",
            "Never declare database views without 'WITH (security_invoker = true)'.",
        ],
    ),
    "Distributed Systems Engineer": SpecialistDefinition(
        role="Distributed Systems Engineer",
        title="Distributed Systems & Concurrency Engineer",
        focus="Idempotency, distributed locking, circuit breakers, and fault-tolerant network retries.",
        domain_invariants=[
            "All state-mutating requests (POST, PATCH, DELETE) MUST enforce unique Idempotency-Key headers.",
            "Every third-party network call (Stripe, Twilio, OpenAI) MUST be bounded by a 3.0s timeout.",
            "Wrap external APIs in circuit breakers with exponential backoff, jitter, and degraded fallbacks.",
            "Financial transactions and quota increments must be atomic (SELECT FOR UPDATE or distributed lock).",
            "Acknowledge external webhook queues with HTTP 200 within 10 seconds before dispatching async tasks.",
        ],
        verification_heuristics=[
            "Verify duplicate webhook delivery produces zero duplicate ledger entries.",
            "Simulate downstream network timeouts and confirm graceful HTTP 200 degraded responses.",
        ],
        prohibited_actions=[
            "Never perform unbounded HTTP requests without connect and read timeout arguments.",
            "Never catch exceptions and silently swallow them without structured # Rationale: tags.",
        ],
    ),
    "Storage & Database Specialist": SpecialistDefinition(
        role="Storage & Database Specialist",
        title="Storage & Relational Database Specialist",
        focus="Relational schemas, foreign key indexing, soft-delete filtering, and zero-downtime migrations.",
        domain_invariants=[
            "Every column with a 'REFERENCES' constraint MUST possess a dedicated B-tree index.",
            "Tables with soft deletes ('deleted_at') must have partial composite indexes ('WHERE deleted_at IS NULL').",
            "Zero table locks on migrations: use 'ADD COLUMN IF NOT EXISTS' with sensible defaults.",
            "Foreign key deletes must specify explicit cascades or restrictions ('ON DELETE CASCADE' / 'RESTRICT').",
        ],
        verification_heuristics=[
            "Inspect EXPLAIN ANALYZE query plans to ensure zero sequential scans on tenant-filtered queries.",
            "Verify all foreign keys are indexed via automated AST schema audits.",
        ],
        prohibited_actions=[
            "Never create unindexed foreign key reference columns.",
            "Never drop columns in a single migration without an expand-and-contract transition phase.",
        ],
    ),
    "Frontend & UI/UX Specialist": SpecialistDefinition(
        role="Frontend & UI/UX Specialist",
        title="Frontend & Refero Design Specialist",
        focus="Design tokens, Tailwind CSS v4, component concurrency locks, and accessible micro-interactions.",
        domain_invariants=[
            "Use Tailwind CSS v4 '@theme' and CSS custom properties; no arbitrary magic numbers.",
            "All mutation buttons MUST bind double-submit guards ('disabled={isPending || isSubmitting}').",
            "Modals and dialogs MUST implement WCAG AA focus traps and Escape key dismissal.",
            "Micro-interactions must utilize spring curves ('cubic-bezier(0.16, 1, 0.3, 1)') under 150ms.",
        ],
        verification_heuristics=[
            "Verify double-clicking a submit button triggers exactly one network invocation.",
            "Verify keyboard navigation cycles focus entirely within open dialog containers.",
        ],
        prohibited_actions=[
            "Never leave mutation buttons unlocked while promises are unsettled.",
            "Never place raw inline hex colors in component files when theme variables exist.",
        ],
    ),
    "TDD & Verification Lead": SpecialistDefinition(
        role="TDD & Verification Lead",
        title="TDD & Systemic Integrity Verification Lead",
        focus="Immutable golden acceptance contracts, anti-cheating assertion integrity, and clean diffs.",
        domain_invariants=[
            "Production code adapts to the test specification, never the reverse.",
            "'tests/golden/' acceptance contracts are strictly read-only.",
            "All docstring operational claims must link directly to executable test receipts.",
            "Zero unverified marketing superlatives ('universal', 'bulletproof', 'blazing fast') allowed.",
            "All temporary '[DEBUG]' and console logging traces must be stripped before commit.",
        ],
        verification_heuristics=[
            "Execute 'python scripts/verify_integrity.py --fix --strict' before every commit.",
            "Verify doctests run cleanly via 'pytest --doctest-modules'.",
        ],
        prohibited_actions=[
            "Never modify or loosen assertions in tests/golden/ to achieve a passing test run.",
            "Never bypass pre-commit verifier hooks.",
        ],
    ),
}


def get_specialist(role: str) -> SpecialistDefinition:
    """Retrieve specialist definition by role name with fallback to SRE."""
    for name, spec in SPECIALISTS.items():
        if role.lower() in name.lower() or name.lower() in role.lower():
            return spec
    return SPECIALISTS["Process Isolation SRE"]


def list_specialists() -> List[Dict[str, str]]:
    """List available domain specialist roles and their focus."""
    return [
        {"role": s.role, "title": s.title, "focus": s.focus}
        for s in SPECIALISTS.values()
    ]


def build_specialist_prompt(
    ticket_id: str,
    title: str,
    role: str,
    objective: str,
    target_files: Optional[List[str]] = None,
    protected_boundaries: Optional[List[str]] = None,
    verification: str = "",
) -> str:
    """
    Constructs a complete, domain-hardened prompt for subagent execution of an Ask-Matt ticket.
    # verifies: tests/unit/test_specialists.py
    """
    spec = get_specialist(role)
    tf_list = "\n".join(f"- `{f}`" for f in (target_files or [])) or "- *(Infer from ticket objective)*"
    pb_list = "\n".join(f"- `{f}`" for f in (protected_boundaries or ["tests/golden/*"]))

    return f"""{spec.render_system_prompt()}

---

# TICKET ASSIGNMENT: {ticket_id} - {title}

You have been dispatched to execute this specific ticket under the MinusCorrect supervised runtime.

## Assigned Objective
{objective}

## Target Files (In-Scope - You may ONLY edit these)
{tf_list}

## Protected Boundaries (Out-of-Scope - STRICTLY READ-ONLY)
{pb_list}

## Verification Criteria
Execute this command to verify completion before reporting back:
```bash
{verification or 'minuscorrect verify --fix --strict'}
```

Report your diff and test receipt upon passing. Do NOT touch files outside your in-scope target files.
"""
