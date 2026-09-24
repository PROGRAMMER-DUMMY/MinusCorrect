"""
Unit tests for MinusCorrect Cognitive Intent Ingestion & Auto-Deliberation Pipeline.

# verifies: tests/unit/test_intake.py
# Rationale: Verifies intent extraction, inferred invariant registration, MinusCouncil deliberation, and Ask-Matt ticket generation.
"""

from pathlib import Path
import pytest

from minuscorrect.intake import extract_intent_and_invariants, run_intake_pipeline
from minuscorrect.router import route_intent, RouteType
from minuscorrect.store import MinusStore


def test_extract_intent_and_invariants():
    """Verify that natural language prompts without explicit rule syntax have invariants extracted."""
    prompt = (
        "i mean we need to build a webhook listener for Stripe payments, "
        "make sure we never log card numbers or secret tokens, "
        "handle duplicate events with idempotency keys, and test it in an isolated worktree"
    )

    intent = extract_intent_and_invariants(prompt)
    assert "build a webhook listener" in intent.core_objective
    assert len(intent.inferred_rules) >= 3

    rule_titles = [r["title"] for r in intent.inferred_rules]
    assert "Zero Secret & PII Logging" in rule_titles
    assert "Mutating Request Idempotency" in rule_titles
    assert "Ephemeral Worktree Isolation" in rule_titles

    assert "Security & Policy Auditor" in intent.required_specialists
    assert "Distributed Systems Engineer" in intent.required_specialists
    assert "TDD & Verification Lead" in intent.required_specialists


def test_run_intake_pipeline_end_to_end(tmp_path: Path):
    """Verify end-to-end cognitive intake pipeline saving rules and tickets into .minus/."""
    store = MinusStore(root_dir=tmp_path)
    prompt = (
        "we need to create a user profile database table in Postgres Supabase, "
        "ensure row level security is enabled, and never leak service_role keys"
    )

    result = run_intake_pipeline(prompt, auto_save=True, store_root=tmp_path)

    # 1. Inferred rules registered
    assert len(result.registered_rules) >= 2
    rules = store.list_rules()
    assert len(rules) >= 2

    # 2. Council synthesis present
    assert "Strong Consensus" in result.council_synthesis["verdict"]

    # 3. Dynamic tickets created and saved to open store
    assert len(result.generated_tickets) == 3
    open_tickets = store.list_tickets(status="open")
    assert len(open_tickets) == 3

    # Check specialist roles assigned
    roles = [t.get("role") for t in open_tickets]
    assert "Security & Policy Auditor" in roles or "Storage & Database Specialist" in roles
    assert "TDD & Verification Lead" in roles

    # 4. Markdown output renders correctly
    md = result.render_markdown()
    assert "# MinusCorrect Autonomous Intent Intake & Deliberation" in md
    assert "Extracted Intent & Core Objective" in md
    assert "Inferred Invariants & Registered Rules" in md
    assert "MinusCouncil Deliberation" in md


def test_router_detects_intake_route():
    """Verify router automatically classifies conversational feature prompts as INTAKE."""
    query = (
        "i mean i dont need to like mention it rule sometimes it should "
        "understnad the intent and add those things and write teh timckets of implemnetationa and otehr thigns via minuscouncil and all"
    )
    decision = route_intent(query)
    assert decision.route == RouteType.INTAKE
    assert decision.confidence >= 0.95
    assert "minuscorrect intake" in decision.recommended_command
