"""Unit tests for MinusCorrect Deep Web Research Swarm & Ontology Protocol.

# verifies: tests/unit/test_research.py
# Rationale: Verifies deterministic multi-agent 3-wave research orchestration and ontology synthesis.
"""

import json
from pathlib import Path
import pytest

from minuscorrect.research import (
    ResearchWave,
    ResearchQuery,
    ResearchFinding,
    ResearchOntology,
    DeepResearchCoordinator,
)
from minuscorrect.cli import build_parser, handle_research
from minuscorrect.router import route_intent, RouteType


def test_research_wave_enumeration():
    """Verify research wave constants."""
    assert ResearchWave.SCOUT.value == "wave_0_scout"
    assert ResearchWave.EXPANSION.value == "wave_1_expansion"
    assert ResearchWave.DEEP_SWARM.value == "wave_2_deep_swarm"


def test_research_query_defaults():
    """Verify search prompt and system prompt defaults."""
    q = ResearchQuery(
        wave=ResearchWave.SCOUT,
        agent_id="scout-01",
        role="Scout",
        topic="PostgreSQL RLS",
        angle="policies and bypasses",
        target_domains=["postgresql.org"],
    )
    assert q.search_prompt == "PostgreSQL RLS - focus on policies and bypasses"
    assert "You are a specialized Web Research Agent focusing on: Scout." in q.system_prompt
    d = q.to_dict()
    assert d["agent_id"] == "scout-01"
    assert d["wave"] == "wave_0_scout"


def test_deep_research_coordinator_wave_progression():
    """Verify 1 -> 3 -> 8 agent swarm planning."""
    coordinator = DeepResearchCoordinator("AI Coding Agent Sandboxes")

    # Wave 0: 1 agent
    w0 = coordinator.plan_wave_0()
    assert len(w0) == 1
    assert w0[0].agent_id == "scout-01"
    assert w0[0].wave == ResearchWave.SCOUT

    # Wave 1: 3 agents
    w1 = coordinator.plan_wave_1()
    assert len(w1) == 3
    assert all(q.wave == ResearchWave.EXPANSION for q in w1)
    agent_ids_w1 = {q.agent_id for q in w1}
    assert agent_ids_w1 == {"expansion-01", "expansion-02", "expansion-03"}

    # Wave 2: 8 agents
    w2 = coordinator.plan_wave_2()
    assert len(w2) == 8
    assert all(q.wave == ResearchWave.DEEP_SWARM for q in w2)
    assert len({q.agent_id for q in w2}) == 8


def test_subagent_specs_generation():
    """Verify Antigravity invoke_subagent specifications format."""
    coordinator = DeepResearchCoordinator("Next.js Server Actions")
    queries = coordinator.plan_wave_1()
    specs = coordinator.generate_subagent_specs(queries)

    assert len(specs) == 3
    for s in specs:
        assert s["TypeName"] == "research"
        assert "Role" in s
        assert "Prompt" in s
        assert "Next.js Server Actions" in s["Prompt"]


def test_ontology_synthesis_and_markdown():
    """Verify ontology knowledge graph synthesis and mermaid rendering."""
    coordinator = DeepResearchCoordinator("Distributed Lock Contention")
    q1 = ResearchQuery(wave=ResearchWave.DEEP_SWARM, agent_id="a1", role="Role1", topic="Topic", angle="Angle1")
    q2 = ResearchQuery(wave=ResearchWave.DEEP_SWARM, agent_id="a2", role="Role2", topic="Topic", angle="Angle2")

    findings = [
        ResearchFinding(
            query=q1,
            source_url="https://redis.io/docs/manual/patterns/distributed-locks/",
            title="Redlock Algorithm",
            summary="Redlock uses multiple master instances with clock drift consideration.",
            sub_topics=["Redlock", "Clock Drift", "Quorum"],
        ),
        ResearchFinding(
            query=q2,
            source_url="https://martin.kleppmann.com/2016/02/08/how-to-do-distributed-locking.html",
            title="Kleppmann Analysis",
            summary="Martin Kleppmann argues Redlock is not safe for correctness without fencing tokens.",
            sub_topics=["Fencing Tokens", "Clock Drift", "GC Pauses"],
        ),
    ]

    ontology = coordinator.synthesize_ontology(findings)
    assert ontology.seed_topic == "Distributed Lock Contention"
    assert ontology.sources_count == 2
    assert ontology.findings_count == 2
    assert "redlock" in ontology.concepts
    assert "fencing tokens" in ontology.concepts
    assert len(ontology.relationships) >= 2
    assert len(ontology.citations) == 2

    md = ontology.render_markdown()
    assert "# Deep Research Ontology: Distributed Lock Contention" in md
    assert "```mermaid" in md
    assert "flowchart TD" in md
    assert "Redlock Algorithm" in md


def test_cli_research_command_stdout(capsys):
    """Verify CLI research command execution in text mode."""
    parser = build_parser()
    args = parser.parse_args(["research", "Token Bucket Rate Limiting", "--waves", "3"])
    ret = handle_research(args)
    assert ret == 0

    captured = capsys.readouterr().out
    assert "MinusCorrect Deep Research Swarm: 'Token Bucket Rate Limiting'" in captured
    assert "Wave 0 (Scout):       1 Agent" in captured
    assert "Wave 1 (Expansion):   3 Agents" in captured
    assert "Wave 2 (Deep Swarm):  8 Agents" in captured
    assert "Total Research Nodes: 12 Dispatched Subagents" in captured


def test_cli_research_command_json(capsys):
    """Verify CLI research command with --json output."""
    parser = build_parser()
    args = parser.parse_args(["research", "PostgreSQL Connection Pooling", "--json"])
    ret = handle_research(args)
    assert ret == 0

    captured = capsys.readouterr().out
    data = json.loads(captured)
    assert data["topic"] == "PostgreSQL Connection Pooling"
    assert len(data["waves"]["wave_0_scout"]) == 1
    assert len(data["waves"]["wave_1_expansion"]) == 3
    assert len(data["waves"]["wave_2_deep_swarm"]) == 8
    assert len(data["subagent_specs"]) == 12


def test_cli_research_command_export(tmp_path):
    """Verify CLI research command exporting to file with --out."""
    out_file = tmp_path / "plan.md"
    parser = build_parser()
    args = parser.parse_args(["research", "Zero-Knowledge Rollups", "--out", str(out_file)])
    ret = handle_research(args)
    assert ret == 0

    assert out_file.exists()
    content = out_file.read_text(encoding="utf-8")
    assert "# Deep Research Swarm Plan: Zero-Knowledge Rollups" in content
    assert "Wave 0: Foundational Scout" in content
    assert "Wave 1: Orthogonal Expansion" in content
    assert "Wave 2: Specialized Deep Swarm" in content


def test_router_detects_deep_research():
    """Verify Smart Intent Router routes deep research requests to DEEP_RESEARCH."""
    decision = route_intent("Please do deep research on agent execution sandboxes")
    assert decision.route == RouteType.DEEP_RESEARCH
    assert decision.confidence >= 0.90
    assert "minuscorrect research" in decision.recommended_command
