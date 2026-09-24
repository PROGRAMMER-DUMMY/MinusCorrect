"""Contract acceptance test for deep research orchestration engine.

# verifies: tests/staging/test_contract.py
# Rationale: Defines formal behavioral contract for 3-wave multi-agent research ontology.
"""

import sys
from pathlib import Path

# Ensure root workspace is on sys.path
root_dir = str(Path(__file__).resolve().parents[2])
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

import pytest
from src.implementation import (
    ResearchWave,
    ResearchQuery,
    ResearchFinding,
    ResearchOntology,
    DeepResearchCoordinator,
)


def test_research_query_contract():
    """Verify ResearchQuery contract and immutability."""
    q = ResearchQuery(
        wave=ResearchWave.SCOUT,
        topic="autonomous coding agent runtime integrity",
        angle="foundational taxonomy",
        target_domains=["github.com", "arxiv.org"],
    )
    assert q.wave == ResearchWave.SCOUT
    assert "runtime integrity" in q.topic
    assert len(q.target_domains) == 2


def test_wave_progression_sequence():
    """Verify that research coordinator progresses sequentially from Wave 0 (1 agent) to Wave 1 (3 agents) to Wave 2 (8 agents)."""
    coordinator = DeepResearchCoordinator(seed_topic="agent process isolation")
    
    # Wave 0: Scout (1 query)
    scout_queries = coordinator.plan_wave_0()
    assert len(scout_queries) == 1
    assert scout_queries[0].wave == ResearchWave.SCOUT
    
    # Ingest mock scout findings
    scout_findings = [
        ResearchFinding(
            query=scout_queries[0],
            source_url="https://example.com/scout",
            title="Overview of Isolation",
            summary="Process isolation requires namespaces, cgroups, and ephemeral worktrees.",
            sub_topics=["ephemeral worktrees", "signal traps", "AST validation"],
        )
    ]
    
    # Wave 1: Expansion (3 agents)
    wave_1_queries = coordinator.plan_wave_1(scout_findings)
    assert len(wave_1_queries) == 3
    assert all(q.wave == ResearchWave.EXPANSION for q in wave_1_queries)
    
    # Ingest mock wave 1 findings
    wave_1_findings = [
        ResearchFinding(
            query=wave_1_queries[i],
            source_url=f"https://example.com/w1-{i}",
            title=f"Wave 1 Dimension {i}",
            summary=f"Findings on dimension {i}",
            sub_topics=[f"dim_{i}_spec", f"dim_{i}_impl"],
        )
        for i in range(3)
    ]
    
    # Wave 2: Deep Swarm (8 agents)
    wave_2_queries = coordinator.plan_wave_2(wave_1_findings)
    assert len(wave_2_queries) == 8
    assert all(q.wave == ResearchWave.DEEP_SWARM for q in wave_2_queries)


def test_ontology_synthesis():
    """Verify ontology graph synthesis from multi-agent findings."""
    coordinator = DeepResearchCoordinator(seed_topic="autonomous coding agents")
    mock_findings = [
        ResearchFinding(
            query=ResearchQuery(wave=ResearchWave.DEEP_SWARM, topic="topic", angle="security"),
            source_url="https://nvd.nist.gov/vuln/1",
            title="CVE-2026-X",
            summary="Arbitrary code execution via unchecked prompt input.",
            sub_topics=["prompt injection", "sandboxing"],
        ),
        ResearchFinding(
            query=ResearchQuery(wave=ResearchWave.DEEP_SWARM, topic="topic", angle="benchmarks"),
            source_url="https://arxiv.org/abs/2609.1",
            title="Agent Evaluation",
            summary="Benchmark leakage and memorization in SWE-bench.",
            sub_topics=["anti-cheat", "sandboxing"],
        ),
    ]
    
    ontology = coordinator.synthesize_ontology(mock_findings)
    assert isinstance(ontology, ResearchOntology)
    assert len(ontology.concepts) >= 3
    assert "sandboxing" in ontology.concepts
    assert ontology.sources_count == 2
    assert ontology.render_markdown().startswith("# Deep Research Ontology:")
