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
