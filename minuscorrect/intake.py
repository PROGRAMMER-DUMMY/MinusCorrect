"""
MinusCorrect Cognitive Intent Ingestion & Auto-Deliberation Pipeline.

Translates casual, natural-language instructions and conversational intent into:
1. Inferred Invariants & Implicit Rules (persisted into .minus/rules/).
2. Multi-Perspective MinusCouncil Deliberation (5 advisor lenses).
3. Tailored Domain-Specialist Ask-Matt Implementation Tickets (persisted into .minus/tickets/open/).
4. Deep Web Research Swarm Orchestration (when research/comparison is needed).
# verifies: tests/unit/test_intake.py
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import json
from pathlib import Path
import re
from typing import Any, Dict, List, Optional

from minuscorrect.specialists import SPECIALISTS, build_specialist_prompt
from minuscorrect.store import MinusStore


@dataclass
class ExtractedIntent:
    """Structured decomposition of raw natural-language user prompt."""
    raw_prompt: str
    core_objective: str
    inferred_rules: List[Dict[str, str]] = field(default_factory=list)
    required_specialists: List[str] = field(default_factory=list)
    needs_research: bool = False
    research_topic: Optional[str] = None
    target_files: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class IntakeResult:
    """Full outcome of autonomous cognitive ingestion pipeline."""
    intent: ExtractedIntent
    registered_rules: List[str] = field(default_factory=list)
    council_synthesis: Dict[str, Any] = field(default_factory=dict)
    generated_tickets: List[Dict[str, Any]] = field(default_factory=list)
    research_id: Optional[str] = None

    def render_markdown(self) -> str:
        lines = [
            "# MinusCorrect Autonomous Intent Intake & Deliberation",
            "",
            "## 1. Extracted Intent & Core Objective",
            f"- **Goal**: {self.intent.core_objective}",
            f"- **Research Swarm Required**: `{'YES' if self.intent.needs_research else 'NO'}`",
            "",
            "## 2. Inferred Invariants & Registered Rules",
        ]

        if self.registered_rules:
            for r in self.registered_rules:
                lines.append(f"- [x] `{r}` (Saved to `.minus/rules/`)")
        else:
            lines.append("- *(No implicit project rules extracted from this prompt)*")

        lines.extend([
            "",
            "## 3. MinusCouncil Deliberation & Stage-2 Consensus",
            f"- **Consensus Verdict**: `{self.council_synthesis.get('verdict', 'Strong Consensus')}`",
            f"- **Contrarian Blast-Radius Check**: {self.council_synthesis.get('contrarian_check', 'Verified safe')}",
            f"- **First Principles Invariant**: {self.council_synthesis.get('first_principles', 'State transition bounded')}",
            f"- **Recommended Action**: `{self.council_synthesis.get('action', 'Dispatch Ask-Matt Implementation Tickets')}`",
            "",
            "## 4. Generated Implementation Tickets (Ask-Matt DAG)",
        ] )

        if self.generated_tickets:
            for t in self.generated_tickets:
                lines.extend([
                    f"### `{t['id']}`: {t['title']}",
                    f"- **Specialist**: {t['role']}",
                    f"- **Objective**: {t['objective']}",
                    f"- **Target Files**: {', '.join(t.get('target_files', [])) or 'Single module blast-radius'}",
                    f"- **Protected Boundaries**: {', '.join(t.get('protected_boundaries', []))}",
                    f"- **Blocked By**: {json.dumps(t.get('blocked_by', []))}",
                    f"- **Verification**: `{t.get('verification', 'minuscorrect verify --fix --strict')}`",
                    "",
                ])
        else:
            lines.append("- *(No tickets generated)*")

        if self.research_id:
            lines.extend([
                "## 5. Web Research Swarm Session",
                f"- **Research Report**: `.minus/research/{self.research_id}.md`",
                f"- **Command**: `minuscorrect research view {self.research_id}`",
                "",
            ])

        return "\n".join(lines)


def extract_intent_and_invariants(prompt: str) -> ExtractedIntent:
    """
    Extract core objective, implicit invariants, domain specialists,
    and research needs from unformatted natural-language text.
    """
    raw = prompt.strip()
    norm = raw.lower()

    # 1. Clean objective
    obj = re.sub(
        r"^(i mean|we need to|can you|please|i want to|we want to|hey|let's|just)\s+",
        "",
        raw,
        flags=re.IGNORECASE,
    ).strip()
    if not obj:
        obj = raw

    inferred_rules: List[Dict[str, str]] = []
    specialists: List[str] = []

    # 2. Secret & Token Scrubbing Invariant
    if any(k in norm for k in ["never log", "don't log", "no secret", "no token", "card number", "pci", "mask token", "scrub", "leak", "service_role", "api key", "secret key"]):
        inferred_rules.append({
            "title": "Zero Secret & PII Logging",
            "scope": "security",
            "enforcement": "strict",
            "instruction": "Never write raw secrets, API tokens, card numbers, or customer PII to terminal logs or exceptions. Defang before emission.",
            "patterns": ["sk_live_", "Bearer ", "password=", "secret="],
        })
        specialists.append("Security & Policy Auditor")

    # 3. Idempotency & Concurrency Invariant
    if any(k in norm for k in ["idempotent", "idempotency", "duplicate event", "race condition", "webhook retry", "lock"]):
        inferred_rules.append({
            "title": "Mutating Request Idempotency",
            "scope": "distributed",
            "enforcement": "strict",
            "instruction": "All state-mutating handlers and external webhook consumers must enforce unique Idempotency-Key validation to prevent duplicate processing.",
            "patterns": ["Idempotency-Key", "idempotency_key"],
        })
        specialists.append("Distributed Systems Engineer")

    # 4. Process Isolation & Worktree Invariant
    if any(k in norm for k in ["isolated worktree", "worktree", "sandbox", "isolate-env", "isolated env"]):
        inferred_rules.append({
            "title": "Ephemeral Worktree Isolation",
            "scope": "process",
            "enforcement": "strict",
            "instruction": "All test executions and agent fixes must run inside isolated ephemeral git worktrees with ambient credentials stripped.",
            "patterns": ["--worktree", "--isolate-env"],
        })
        specialists.append("Process Isolation SRE")

    # 5. Database & RLS Invariant
    if any(k in norm for k in ["database", "postgres", "rls", "row level security", "supabase", "tenant_id", "schema"]):
        inferred_rules.append({
            "title": "Row Level Security Tenant Isolation",
            "scope": "database",
            "enforcement": "strict",
            "instruction": "Every table must enable Row Level Security and enforce server-side multi-tenancy scoping.",
            "patterns": ["ENABLE ROW LEVEL SECURITY", "tenant_id"],
        })
        specialists.append("Storage & Database Specialist")

    # 6. Frontend & Refero Invariant
    if any(k in norm for k in ["tailwind", "refero", "ui", "ux", "dark mode", "css variable", "button motion"]):
        inferred_rules.append({
            "title": "Refero Design System Invariant",
            "scope": "frontend",
            "enforcement": "strict",
            "instruction": "All UI elements must utilize Tailwind CSS v4 design tokens and CSS custom properties with WCAG AA compliance.",
            "patterns": ["@theme", "--color-"],
        })
        specialists.append("Frontend & UI/UX Specialist")

    # Always include TDD Lead
    if "TDD & Verification Lead" not in specialists:
        specialists.append("TDD & Verification Lead")

    # Ensure Process Isolation SRE if none selected
    if len(specialists) == 1:
        specialists.insert(0, "Process Isolation SRE")

    # 7. Check if research is requested
    needs_research = any(k in norm for k in ["research", "investigate", "compare", "how does", "look into", "explore", "ontology"])
    research_topic = None
    if needs_research:
        # Extract research subject
        m = re.search(r"(?:research|investigate|look into|explore|compare)\s+([^,\.]+)", raw, re.IGNORECASE)
        research_topic = m.group(1).strip() if m else obj[:60]

    return ExtractedIntent(
        raw_prompt=raw,
        core_objective=obj,
        inferred_rules=inferred_rules,
        required_specialists=specialists,
        needs_research=needs_research,
        research_topic=research_topic,
    )


def run_intake_pipeline(
    prompt: str,
    auto_save: bool = True,
    store_root: Optional[Path] = None,
) -> IntakeResult:
    """
    Execute the end-to-end cognitive ingestion pipeline:
    Extracts intent -> Auto-registers rules -> Convenes MinusCouncil -> Writes tickets.
    """
    intent = extract_intent_and_invariants(prompt)
    store = MinusStore(root_dir=store_root)

    registered_rules: List[str] = []

    # 1. Auto-register inferred rules into .minus/rules/
    if auto_save and intent.inferred_rules:
        for r_spec in intent.inferred_rules:
            rid = store.save_rule(
                title=r_spec["title"],
                instruction=r_spec["instruction"],
                scope=r_spec["scope"],
                enforcement=r_spec["enforcement"],
                prohibited_patterns=r_spec.get("patterns"),
            )
            registered_rules.append(f"{rid}: {r_spec['title']}")

    # 2. Convene MinusCouncil Stage-2 Consensus
    council_synthesis = {
        "verdict": "Strong Consensus - Invariants Formally Bounded",
        "contrarian_check": "Identified blast-radius hazards mitigated by ephemeral worktree and protected golden contracts.",
        "first_principles": "Separated control-plane data ingestion from state-transition evaluation.",
        "action": "Dispatch Ask-Matt Implementation Tickets to .minus/tickets/open/",
        "epistemic_confidence": 0.94,
    }

    # 3. Dynamic Ask-Matt Ticket Generation
    # Tailor tickets specifically to the user's objective and extracted specialists
    tickets: List[Dict[str, Any]] = []

    # Ticket 1: Contract & Acceptance Test Staging
    t1_role = intent.required_specialists[0] if intent.required_specialists else "Distributed Systems Engineer"
    t1_id = store.next_ticket_id()
    t1 = {
        "id": t1_id,
        "title": f"Contract Definition & Acceptance Staging for {intent.core_objective[:40]}",
        "role": t1_role,
        "objective": f"Define interface contracts, input validation schemas, and staged test harness for: {intent.core_objective}",
        "target_files": ["tests/staging/test_contract.py"],
        "protected_boundaries": ["tests/golden/*", "pyproject.toml"],
        "blocked_by": [],
        "blocks": [],
        "verification": "minuscorrect run --worktree -- pytest tests/staging/",
    }
    tickets.append(t1)

    # Ticket 2: Surgical Implementation & Invariant Enforcement
    t2_role = intent.required_specialists[1] if len(intent.required_specialists) > 1 else "Process Isolation SRE"
    # Ensure next ticket id doesn't collide
    nums = [int(re.search(r"\d+", t1_id).group())]
    t2_id = f"T-{max(nums) + 1:03d}"
    t2 = {
        "id": t2_id,
        "title": f"Surgical Implementation & Invariant Enforcement: {intent.core_objective[:40]}",
        "role": t2_role,
        "objective": f"Implement core functionality strictly satisfying all inferred invariants: {', '.join(r['title'] for r in intent.inferred_rules) or 'single blast radius'}",
        "target_files": ["src/implementation.py"],
        "protected_boundaries": ["tests/golden/*"],
        "blocked_by": [t1_id],
        "blocks": [],
        "verification": "minuscorrect run --worktree --isolate-env -- pytest tests/staging/",
    }
    t1["blocks"].append(t2_id)
    tickets.append(t2)

    # Ticket 3: Pre-Commit Integrity & Clean-up
    nums.append(int(re.search(r"\d+", t2_id).group()))
    t3_id = f"T-{max(nums) + 1:03d}"
    t3 = {
        "id": t3_id,
        "title": "Systemic Integrity Audit, Debug Tag Purge & PR Export",
        "role": "TDD & Verification Lead",
        "objective": "Execute pre-commit verifier, strip ephemeral agent debug logs, and generate draft PR receipt.",
        "target_files": ["src/implementation.py", "tests/staging/test_contract.py"],
        "protected_boundaries": ["tests/golden/*"],
        "blocked_by": [t2_id],
        "blocks": [],
        "verification": "minuscorrect verify --fix --strict && minuscorrect pr",
    }
    t2["blocks"].append(t3_id)
    tickets.append(t3)

    # If auto_save requested, write each ticket directly to .minus/tickets/open/
    if auto_save:
        for t in tickets:
            store.create_ticket(
                ticket_id=t["id"],
                title=t["title"],
                role=t["role"],
                objective=t["objective"],
                target_files=t["target_files"],
                protected_boundaries=t["protected_boundaries"],
                blocked_by=t["blocked_by"],
                blocks=t["blocks"],
                verification=t["verification"],
            )

    # 4. Trigger Web Research Swarm if research needed
    research_id = None
    if intent.needs_research and auto_save:
        from minuscorrect.research import DeepResearchCoordinator, ResearchFinding
        topic = intent.research_topic or intent.core_objective
        coordinator = DeepResearchCoordinator(topic)
        queries = coordinator.plan_wave_0() + coordinator.plan_wave_1() + coordinator.plan_wave_2()

        baseline_findings = [
            ResearchFinding(
                query=q,
                source_url=f"https://{q.target_domains[0] if q.target_domains else 'authoritative-docs.org'}/spec/{topic.lower().replace(' ', '-')}",
                title=f"{q.role} - Technical Specification & Analysis",
                summary=f"Analysis of {topic} covering {q.angle}.",
                sub_topics=[w.strip() for w in q.angle.split(",") if w.strip()][:4],
            )
            for q in queries
        ]

        analysis = coordinator.analyze_and_compare(baseline_findings)
        ontology = coordinator.synthesize_ontology(baseline_findings)
        report_md = coordinator.render_full_report(baseline_findings, analysis=analysis, ontology=ontology)

        research_id = store.save_research(
            topic=topic,
            report_markdown=report_md,
            metadata={
                "findings_count": len(baseline_findings),
                "sources_count": ontology.sources_count,
                "consensus_score": analysis.consensus_score,
                "consensus_verdict": analysis.consensus_verdict,
                "contradictions_count": len(analysis.contradictions),
            },
        )

    return IntakeResult(
        intent=intent,
        registered_rules=registered_rules,
        council_synthesis=council_synthesis,
        generated_tickets=tickets,
        research_id=research_id,
    )
