"""
Unit Tests for MinusCorrect Orchestrator Engine.
Tests LLM Council prompt scaffolding, Ask-Matt Spec-to-Tickets generation,
and plugin status discovery.
"""

import json
from minuscorrect.orchestrator import (
    generate_council_protocol,
    generate_ask_matt_plan,
    inspect_plugin_status,
    get_plugin_source_dir,
    COUNCIL_LENSES,
)


def test_council_protocol_text_and_json():
    # Text format
    text = generate_council_protocol("Should we migrate to ASGI?")
    assert "Should we migrate to ASGI?" in text
    assert "The Contrarian" in text
    assert "The First Principles Thinker" in text
    assert "The Expansionist" in text
    assert "The Outsider" in text
    assert "The Executor" in text

    # JSON format
    json_str = generate_council_protocol("Should we migrate to ASGI?", as_json=True)
    data = json.loads(json_str)
    assert data["query"] == "Should we migrate to ASGI?"
    assert len(data["advisors"]) == 5
    assert len(data["deliberation_flow"]) == 5


def test_ask_matt_plan_text_and_json():
    # Text format
    text = generate_ask_matt_plan("Refactor database pooling")
    assert "Refactor database pooling" in text
    assert "TICKET-01" in text
    assert "TICKET-02" in text
    assert "TICKET-03" in text
    assert "tests/golden/*" in text

    # JSON format
    json_str = generate_ask_matt_plan("Refactor database pooling", as_json=True)
    data = json.loads(json_str)
    assert data["target"] == "Refactor database pooling"
    assert len(data["tracer_bullet_tickets"]) == 3
    assert data["tracer_bullet_tickets"][0]["id"] == "TICKET-01"


def test_get_plugin_source_dir():
    plugin_dir = get_plugin_source_dir()
    assert plugin_dir.is_dir()
    assert (plugin_dir / "plugin.json").is_file()


def test_inspect_plugin_status():
    status = inspect_plugin_status()
    assert isinstance(status, dict)
    assert "plugin_installed" in status
    assert "plugin_directory" in status
    assert "skills_registered" in status


def test_evaluate_council_consensus_local():
    from minuscorrect.orchestrator import evaluate_council_consensus
    from minuscorrect.decision import LocalRuleEngine

    proposals = [
        {"advisor": "The Contrarian", "stance": "Identified blast-radius hazard in conftest.py"},
        {"advisor": "The First Principles Thinker", "stance": "Heuristics propose; determinism enforces."},
        {"advisor": "The Expansionist", "stance": "High upside in microsecond peer scoring."},
        {"advisor": "The Outsider", "stance": "Zero-dependency local-first execution must be preserved."},
        {"advisor": "The Executor", "stance": "Actionable tracer-bullet implementation plan ready."},
    ]

    result = evaluate_council_consensus(proposals, engine=LocalRuleEngine())
    assert "consensus_score" in result
    assert "recommended_action" in result
    assert result["provider"] == "local-rules"
    assert result["recommended_action"] in {"proceed_to_spec", "revise_proposal", "hard_abort"}


def test_evaluate_council_consensus_mock_jev():
    from pathlib import Path
    from minuscorrect.orchestrator import evaluate_council_consensus
    from minuscorrect.decision import MockDecisionEngine
    from minuscorrect.types.decision import ChoiceResult, DecisionResponse, NoulResult, ScoreResult

    fixture_path = Path(__file__).resolve().parent.parent / "fixtures" / "jev_ballots.json"
    with open(fixture_path, "r", encoding="utf-8") as f:
        fixture_data = json.load(f)

    proposals = fixture_data["mock_ballots"]

    mock_resp = DecisionResponse(
        answers={
            "consensus_score": ScoreResult(score=8.5, confidence=0.9),
            "fatal_flaw_detected": NoulResult(probability=0.1, passed=False, confidence=0.9),
            "actionable_now": NoulResult(probability=0.95, passed=True, confidence=0.95),
            "recommended_action": ChoiceResult(choice="proceed_to_spec", distribution={"proceed_to_spec": 0.95}, confidence=0.95),
        },
        latency_ms=75.0,
        provider="jev-systemone",
    )

    mock_engine = MockDecisionEngine(canned_response=mock_resp)
    result = evaluate_council_consensus(proposals, engine=mock_engine)

    assert result["consensus_score"] == 8.5
    assert result["fatal_flaw_detected"] is False
    assert result["actionable_now"] is True
    assert result["recommended_action"] == "proceed_to_spec"
    assert result["provider"] == "jev-systemone"
    assert len(mock_engine.recorded_batches) == 1

