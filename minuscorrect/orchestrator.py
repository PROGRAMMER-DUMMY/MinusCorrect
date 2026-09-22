"""
MinusCorrect Multi-Perspective Council and Ask-Matt Orchestrator Engine.
Provides programmatic generators and CLI handlers for LLM Council deliberation,
Ask-Matt Spec-to-Tickets DAG planning, and Antigravity plugin lifecycle.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional


COUNCIL_LENSES: List[Dict[str, str]] = [
    {
        "name": "The Contrarian",
        "role": "Adversarial Invariant & Blast-Radius Auditor",
        "description": "Actively looks for what will break, regressions, AST blast-radius hazards, and unintended side-effects.",
        "prompt": "Assume this proposal has a fatal flaw. What is it, and why will it fail in production?",
    },
    {
        "name": "The First Principles Thinker",
        "role": "Foundational Invariants & Problem Reducer",
        "description": "Strips away surface symptoms; asks what core invariant is being violated. Rebuilds from fundamentals.",
        "prompt": "What fundamental problem are we actually trying to solve? Ignore the proposed tooling and assumptions.",
    },
    {
        "name": "The Expansionist",
        "role": "Systemic Leverage & Architectural Scalability",
        "description": "Identifies systemic leverage, adjacent architectural value, and long-term durability.",
        "prompt": "If this works 10x better than expected, what bigger capability or systemic durability does it unlock?",
    },
    {
        "name": "The Outsider",
        "role": "Zero-Context Ergonomics & Simplicity Auditor",
        "description": "Zero-context sanity check; catches over-engineering, buzzword compliance, and ergonomics traps.",
        "prompt": "Explain this to an engineer with no background in this codebase. Does this solve a real problem simply?",
    },
    {
        "name": "The Executor",
        "role": "Minimal Surgical Implementation Lead",
        "description": "Scope cutter; formulates the minimal, surgical Monday-morning tracer-bullet patch plan.",
        "prompt": "What is the absolute simplest tracer-bullet implementation that can be verified and shipped immediately?",
    },
]


def generate_council_protocol(query: Optional[str] = None, as_json: bool = False) -> str:
    """
    Generate structured prompt scaffolding for the 5-advisor LLM Council.
    """
    subject = query or "Architectural decision / High-risk bug triage"
    data = {
        "query": subject,
        "advisors": COUNCIL_LENSES,
        "deliberation_flow": [
            "1. Dispatch independent queries to 5 advisor subagents with diverse thinking lenses.",
            "2. Collect and anonymize advisor responses (Advisor A through E).",
            "3. Conduct blind peer reviews across advisor outputs.",
            "4. Chairman synthesizes consensus, clashes, and definitive verdict.",
            "5. Automatically translate verdict into an Ask-Matt execution plan (/ask-matt).",
        ],
    }

    if as_json:
        return json.dumps(data, indent=2)

    lines = [
        "=" * 80,
        "MINUSCORRECT LLM COUNCIL PROTOCOL",
        "=" * 80,
        f"Subject: {subject}",
        "",
        "ADVISOR THINKING LENSES (5 Independent Angles):",
        "-" * 80,
    ]

    for i, lens in enumerate(COUNCIL_LENSES, start=1):
        lines.append(f"{i}. {lens['name']} ({lens['role']}):")
        lines.append(f"   Angle: {lens['description']}")
        lines.append(f"   Directive: \"{lens['prompt']}\"")
        lines.append("")

    lines.extend([
        "-" * 80,
        "DELIBERATION & SYNTHESIS FLOW:",
        "1. Dispatch queries to the 5 advisors in parallel.",
        "2. Peer-review advisor outputs anonymously.",
        "3. Synthesize consensus & trade-offs into a definitive verdict.",
        "4. Pipe verdict into an actionable Ask-Matt DAG: minuscorrect ask-matt \"<verdict>\"",
        "=" * 80,
    ])

    return "\n".join(lines)


def evaluate_council_consensus(
    proposals: List[Dict[str, str]],
    engine: Optional[Any] = None,
) -> Dict[str, Any]:
    """
    Evaluate LLM Council Stage-2 consensus using the Middle-Ring DecisionEngine.
    # verifies: tests/unit/test_orchestrator.py
    """
    if engine is None:
        from minuscorrect.decision import get_decision_engine
        engine = get_decision_engine("auto")

    state_lines = ["COUNCIL ADVISOR PROPOSALS:"]
    for p in proposals:
        adv = p.get("advisor", "Unknown")
        stance = p.get("stance", p.get("content", ""))
        state_lines.append(f"[{adv}]: {stance}")
    state = "\n".join(state_lines)

    from minuscorrect.types.decision import Choice, DecisionBatch, Noul, Score

    batch = DecisionBatch(
        state=state,
        questions={
            "consensus_score": Score(
                instructions="Score overall council consensus and alignment on non-negotiable invariants",
                min_val=0.0,
                max_val=10.0,
            ),
            "fatal_flaw_detected": Noul(
                instructions="A fatal unmitigated flaw or fatal regression was identified that requires aborting",
                threshold=0.6,
            ),
            "actionable_now": Noul(
                instructions="The proposals formulate a concrete, viable implementation plan ready for execution",
                threshold=0.5,
            ),
            "recommended_action": Choice(
                instructions="Recommend next pipeline phase based on council consensus",
                criteria={
                    "proceed_to_spec": "Solid consensus; proceed to Ask-Matt architectural spec",
                    "revise_proposal": "Substantive clash requiring another round of advisor deliberation",
                    "hard_abort": "Fatal flaw discovered; abandon proposal",
                },
            ),
        },
    )

    response = engine.evaluate(batch)
    return {
        "consensus_score": getattr(response.answers.get("consensus_score"), "score", 5.0),
        "fatal_flaw_detected": getattr(response.answers.get("fatal_flaw_detected"), "passed", False),
        "actionable_now": getattr(response.answers.get("actionable_now"), "passed", True),
        "recommended_action": getattr(response.answers.get("recommended_action"), "choice", "proceed_to_spec"),
        "latency_ms": response.latency_ms,
        "provider": response.provider,
        "raw_answers": {k: v.to_dict() for k, v in response.answers.items()},
    }


def generate_ask_matt_plan(
    idea: Optional[str] = None,
    as_json: bool = False,
    save_to_store: bool = False,
    store_root: Optional[Path] = None,
) -> str:
    """
    Generate an Ask-Matt Spec-to-Tickets DAG implementation plan.
    Attaches domain specialist system prompts and optionally ingests tickets into .minus/ store.
    # verifies: tests/unit/test_orchestrator.py
    """
    from minuscorrect.specialists import build_specialist_prompt

    subject = idea or "Defect repair / Feature implementation"
    raw_tickets = [
        {
            "id": "TICKET-01",
            "title": "Contract Definition & Test Staging",
            "role": "Distributed Systems Engineer",
            "objective": "Define interface contracts and create staged acceptance tests.",
            "target_files": ["tests/staging/test_contract.py"],
            "protected_boundaries": ["tests/golden/*"],
            "blocked_by": [],
            "blocks": ["TICKET-02"],
            "verification": "minuscorrect run --worktree -- pytest tests/staging/",
        },
        {
            "id": "TICKET-02",
            "title": "Surgical Implementation & Sandboxed Verification",
            "role": "Process Isolation SRE",
            "objective": "Implement minimal solution within single target file blast radius.",
            "target_files": ["src/implementation.py"],
            "protected_boundaries": ["tests/golden/*", "pyproject.toml"],
            "blocked_by": ["TICKET-01"],
            "blocks": ["TICKET-03"],
            "verification": "minuscorrect run --worktree --isolate-env -- pytest tests/staging/",
        },
        {
            "id": "TICKET-03",
            "title": "Pre-Commit Integrity Audit & Clean-up",
            "role": "TDD & Verification Lead",
            "objective": "Run pre-commit systemic verifier, strip debug scaffolding, and export PR proposal.",
            "target_files": ["src/implementation.py", "tests/staging/test_contract.py"],
            "protected_boundaries": ["tests/golden/*"],
            "blocked_by": ["TICKET-02"],
            "blocks": [],
            "verification": "minuscorrect verify --fix --strict && minuscorrect pr",
        },
    ]

    for t in raw_tickets:
        t["specialist_prompt"] = build_specialist_prompt(
            ticket_id=t["id"],
            title=t["title"],
            role=t["role"],
            objective=t["objective"],
            target_files=t.get("target_files"),
            protected_boundaries=t.get("protected_boundaries"),
            verification=t["verification"],
        )

    if save_to_store:
        from minuscorrect.store import MinusStore
        store = MinusStore(root_dir=store_root)
        for t in raw_tickets:
            store.create_ticket(
                ticket_id=t["id"],
                title=t["title"],
                role=t["role"],
                objective=t["objective"],
                target_files=t.get("target_files"),
                protected_boundaries=t.get("protected_boundaries"),
                blocked_by=t["blocked_by"],
                blocks=t["blocks"],
                verification=t["verification"],
            )

    data = {
        "target": subject,
        "spec": {
            "core_invariant": "System state remains consistent; golden contracts are immutable.",
            "data_contracts": "Explicit schemas and input/output contracts.",
            "protected_boundaries": [
                "tests/golden/* (Acceptance contracts strictly read-only)",
                "Production modules outside targeted blast radius",
            ],
        },
        "tracer_bullet_tickets": raw_tickets,
    }

    if as_json:
        return json.dumps(data, indent=2)

    lines = [
        "=" * 80,
        "MINUSCORRECT ASK-MATT EXECUTION PLAN (Spec to Tickets DAG)",
        "=" * 80,
        f"Target: {subject}",
        "",
        "PHASE 1: ARCHITECTURAL SPECIFICATION (/to-spec):",
        "  - Core Invariant: System state remains consistent; golden contracts are immutable.",
        "  - Protected Boundaries:",
        "      * tests/golden/* (strictly read-only)",
        "      * Production modules outside targeted blast radius",
        "",
        "PHASE 2: TRACER-BULLET TICKETS DAG (/to-tickets):",
    ]

    for ticket in data["tracer_bullet_tickets"]:
        blocked_by = ", ".join(ticket["blocked_by"]) if ticket["blocked_by"] else "None"
        blocks = ", ".join(ticket["blocks"]) if ticket["blocks"] else "None"
        lines.extend([
            f"  [{ticket['id']}] {ticket['title']}",
            f"    Role: {ticket['role']}",
            f"    Objective: {ticket['objective']}",
            f"    Dependencies: Blocked By: [{blocked_by}] | Blocks: [{blocks}]",
            f"    Verification: {ticket['verification']}",
            "",
        ])

    lines.extend([
        "PHASE 3: SUPERVISED EXECUTION:",
        "  - Execute tickets under 4-iteration ceiling with ephemeral worktree isolation:",
        "    minuscorrect run --worktree --isolate-env -- pytest <test_path>",
        "  - Run final integrity audit:",
        "    minuscorrect verify --fix --strict",
        "=" * 80,
    ])

    return "\n".join(lines)


def get_plugin_source_dir() -> Path:
    """Locate the plugin directory within the MinusCorrect repository."""
    # Check relative to this source file
    candidates = [
        Path(__file__).resolve().parent.parent / "plugin",
        Path.cwd() / "plugin",
    ]
    for candidate in candidates:
        if candidate.is_dir() and (candidate / "plugin.json").is_file():
            return candidate
    return Path(__file__).resolve().parent.parent / "plugin"


def inspect_plugin_status() -> Dict[str, Any]:
    """Inspect the registration status of the MinusCorrect plugin and skills."""
    user_home = Path.home()
    global_plugin_dir = user_home / ".gemini" / "config" / "plugins" / "minuscorrect"
    global_skills_dir = user_home / ".gemini" / "config" / "skills"

    skills_present = {
        "minuscorrect": (global_skills_dir / "minuscorrect" / "SKILL.md").is_file(),
        "minuscorrect-council": (global_skills_dir / "minuscorrect-council" / "SKILL.md").is_file(),
        "ask-matt": (global_skills_dir / "ask-matt" / "SKILL.md").is_file(),
        "minuscorrect-security": (global_skills_dir / "minuscorrect-security" / "SKILL.md").is_file(),
    }

    # Check agy plugins list
    agy_imported = False
    try:
        res = subprocess.run(["agy", "plugins", "list"], capture_output=True, text=True, check=False)
        if res.returncode == 0 and "minuscorrect" in res.stdout:
            agy_imported = True
    except (FileNotFoundError, OSError):
        pass

    return {
        "plugin_installed": global_plugin_dir.is_dir() and (global_plugin_dir / "plugin.json").is_file(),
        "plugin_directory": str(global_plugin_dir),
        "agy_imported": agy_imported,
        "skills_registered": skills_present,
    }


def install_plugin() -> tuple[bool, str]:
    """Install and register the MinusCorrect plugin into Antigravity."""
    source_dir = get_plugin_source_dir()
    if not source_dir.is_dir() or not (source_dir / "plugin.json").is_file():
        return False, f"Plugin source directory not found at {source_dir}"

    try:
        res = subprocess.run(["agy", "plugin", "install", str(source_dir)], capture_output=True, text=True, check=False)
        if res.returncode == 0:
            return True, f"Successfully installed MinusCorrect plugin into Antigravity CLI:\n{res.stdout.strip()}"
        return False, f"Failed to install plugin via agy: {res.stderr.strip()}"
    except (FileNotFoundError, OSError) as exc:
        # Fallback to direct directory copy if agy executable is not in PATH
        dest_dir = Path.home() / ".gemini" / "config" / "plugins" / "minuscorrect"
        try:
            if dest_dir.exists():
                shutil.rmtree(dest_dir)
            shutil.copytree(source_dir, dest_dir)
            return True, f"Copied MinusCorrect plugin directly to {dest_dir} (agy command not found in PATH)."
        except Exception as copy_exc:
            return False, f"Failed to copy plugin: {copy_exc}"
