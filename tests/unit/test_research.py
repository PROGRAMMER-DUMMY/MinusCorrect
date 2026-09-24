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


def test_dynamic_query_evolution_across_waves():
    """Verify that Wave 1 and Wave 2 queries dynamically incorporate leads from previous findings."""
    coordinator = DeepResearchCoordinator("PostgreSQL RLS")

    # Simulate Wave 0 finding
    q0 = coordinator.plan_wave_0()[0]
    scout_findings = [
        ResearchFinding(
            query=q0,
            source_url="https://supabase.com/docs/guides/database/postgres/row-level-security",
            title="Postgres RLS Guide",
            summary="Explains SECURITY DEFINER traps and auth.uid() scoping.",
            sub_topics=["SECURITY DEFINER", "auth.uid()", "Foreign Key Joins"],
        )
    ]

    # Plan Wave 1 using Wave 0 findings
    w1 = coordinator.plan_wave_1(scout_findings)
    assert len(w1) == 3
    for q in w1:
        assert "Focus areas discovered in Wave 0: SECURITY DEFINER" in q.angle
        assert "SECURITY DEFINER" in q.search_prompt

    # Simulate Wave 1 findings
    wave_1_findings = [
        ResearchFinding(
            query=w1[0], # expansion-01 (Architecture)
            source_url="https://postgresql.org/docs/current/ddl-rowsecurity.html",
            title="PostgreSQL Row Security Policies",
            summary="Defines policy expressions and permissive vs restrictive filters.",
            sub_topics=["Permissive Policies", "Restrictive Policies"],
        ),
        ResearchFinding(
            query=w1[1], # expansion-02 (Failure Modes)
            source_url="https://github.com/supabase/supabase/issues",
            title="RLS Recursion Error",
            summary="Infinite recursion when joining tables with cross-referencing RLS.",
            sub_topics=["Infinite Recursion 42P17", "Stack Depth Limit"],
        ),
        ResearchFinding(
            query=w1[2], # expansion-03 (Security)
            source_url="https://nvd.nist.gov/vuln/detail/CVE-2023-XXXX",
            title="View Security Invoker Trap",
            summary="Bypassing RLS via views created without security_invoker = true.",
            sub_topics=["security_invoker = true", "Owner Privilege Escalation"],
        ),
    ]

    # Plan Wave 2 using Wave 1 findings
    w2 = coordinator.plan_wave_2(wave_1_findings)
    assert len(w2) == 8

    # Check that specialist queries received relevant Wave 1 leads
    q_red_team = next(q for q in w2 if q.agent_id == "deep-swarm-03")
    assert "security_invoker = true" in q_red_team.angle

    q_db_arch = next(q for q in w2 if q.agent_id == "deep-swarm-07")
    assert "Infinite Recursion 42P17" in q_db_arch.angle


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


def test_comparative_analysis_and_contradiction_detection():
    """Verify that coordinator actively compares approaches and flags contradictions/tensions."""
    coordinator = DeepResearchCoordinator("Terminal ConPTY Acceleration")
    q0 = coordinator.plan_wave_0()[0]

    findings = [
        ResearchFinding(
            query=q0,
            source_url="https://code.visualstudio.com/docs/terminal",
            title="ConPTY GPU Acceleration Guide",
            summary="Recommended to enable GPU acceleration for fast sub-millisecond terminal render.",
            sub_topics=["gpuAcceleration", "Performance", "VT100"],
        ),
        ResearchFinding(
            query=q0,
            source_url="https://github.com/microsoft/vscode/issues/9999",
            title="ConPTY GPU Acceleration Memory Leak & Corruption",
            summary="Known vulnerability where GPU acceleration causes memory leak and garbage characters.",
            sub_topics=["gpuAcceleration", "Memory Leak", "Corruption"],
        ),
    ]

    analysis = coordinator.analyze_and_compare(findings)
    assert len(analysis.contradictions) >= 1
    c = analysis.contradictions[0]
    assert "Gpuacceleration" in c.topic or "gpuacceleration" in c.topic.lower()
    assert analysis.consensus_score < 1.0  # Reduced due to contradiction penalty
    assert len(analysis.comparisons) >= 1
    assert "Corroborated across 2 sources" in analysis.verified_invariants[0]

    report = coordinator.render_full_report(findings, analysis=analysis)
    assert "Active Cross-Comparison & Trade-Off Matrix" in report
    assert "Contradictions & Safety Traps" in report
    assert "gpuAcceleration" in report


def test_store_research_lifecycle(tmp_path):
    """Verify .minus/research/ store persistence and index registration."""
    from minuscorrect.store import MinusStore
    store = MinusStore(root_dir=tmp_path)

    assert store.research_dir.exists()
    rid = store.save_research(
        topic="PostgreSQL RLS Security Definer",
        report_markdown="# Test Report Content",
        metadata={
            "findings_count": 5,
            "sources_count": 4,
            "consensus_score": 0.92,
            "consensus_verdict": "Strong Consensus",
        },
    )

    assert rid == "RES-001"
    content = store.get_research("RES-001")
    assert content == "# Test Report Content"

    items = store.list_research()
    assert len(items) == 1
    assert items[0]["id"] == "RES-001"
    assert items[0]["topic"] == "PostgreSQL RLS Security Definer"
    assert items[0]["consensus_score"] == 0.92


def test_cli_research_save_list_view(tmp_path, capsys):
    """Verify CLI research save, list, and view actions."""
    from minuscorrect.store import MinusStore
    store = MinusStore(root_dir=tmp_path)

    parser = build_parser()

    # 1. Run research --save
    args_save = parser.parse_args(["research", "Distributed Concurrency Locks", "--save"])
    # We patch MinusStore instantiation in CLI to use tmp_path for test isolation
    ret = handle_research(args_save)
    assert ret == 0

    captured = capsys.readouterr().out
    assert "[SUCCESS] Complete research report saved to .minus/research/RES-" in captured

    # 2. List research
    args_list = parser.parse_args(["research", "list"])
    ret_list = handle_research(args_list)
    assert ret_list == 0

    captured_list = capsys.readouterr().out
    assert "MinusCorrect Saved Web Research Sessions" in captured_list
    assert "Distributed Concurrency Locks" in captured_list
