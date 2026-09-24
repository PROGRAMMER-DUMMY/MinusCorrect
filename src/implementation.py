"""Deep Research Swarm Coordinator and Ontology Engine.

# verifies: tests/staging/test_contract.py
# Rationale: Implements recursive 3-wave multi-agent deep research ontology protocol.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Set, Optional


class ResearchWave(str, Enum):
    """Execution waves for deep research protocol."""
    SCOUT = "wave_0_scout"          # 1 Agent: Broad landscape recon & seed mapping
    EXPANSION = "wave_1_expansion"  # 3 Agents: Orthogonal query expansion
    DEEP_SWARM = "wave_2_deep_swarm" # 8 Agents: Parallel specialized deep dives


@dataclass(frozen=True)
class ResearchQuery:
    """Targeted research query dispatched to a researcher agent."""
    wave: ResearchWave
    topic: str
    angle: str
    target_domains: List[str] = field(default_factory=list)
    search_prompt: str = ""

    def __post_init__(self):
        if not self.search_prompt:
            object.__setattr__(
                self, "search_prompt", f"{self.topic} - focus on {self.angle}"
            )


@dataclass
class ResearchFinding:
    """Synthesized intelligence output extracted by an individual research agent."""
    query: ResearchQuery
    source_url: str
    title: str
    summary: str
    sub_topics: List[str] = field(default_factory=list)
    confidence_score: float = 1.0


@dataclass
class ResearchOntology:
    """Cross-synthesized knowledge graph linking concepts, citations, and consensus."""
    seed_topic: str
    concepts: Set[str]
    relationships: List[Dict[str, str]]
    sources_count: int
    findings_count: int

    def render_markdown(self) -> str:
        """Render markdown artifact summarizing synthesized knowledge."""
        lines = [
            f"# Deep Research Ontology: {self.seed_topic}",
            "",
            f"- **Sources Analyzed**: {self.sources_count}",
            f"- **Concepts Mapped**: {len(self.concepts)}",
            "",
            "## Key Concepts",
        ]
        for c in sorted(self.concepts):
            lines.append(f"- `{c}`")
        lines.append("")
        lines.append("## Cross-Domain Relationships")
        for rel in self.relationships:
            lines.append(f"- **{rel.get('from')}** -> *{rel.get('type')}* -> **{rel.get('to')}**")
        return "\n".join(lines)


class DeepResearchCoordinator:
    """Orchestrates recursive 1 -> 3 -> 8 multi-agent research swarm."""

    def __init__(self, seed_topic: str):
        self.seed_topic = seed_topic

    def plan_wave_0(self) -> List[ResearchQuery]:
        """Wave 0 (Scout): Single broad reconnaissance agent establishing foundational taxonomy."""
        return [
            ResearchQuery(
                wave=ResearchWave.SCOUT,
                topic=self.seed_topic,
                angle="foundational taxonomy, industry standards, and core architecture",
                target_domains=["github.com", "arxiv.org", "wikipedia.org"],
            )
        ]

    def plan_wave_1(self, scout_findings: List[ResearchFinding]) -> List[ResearchQuery]:
        """Wave 1 (Expansion): 3 parallel agents analyzing orthogonal dimensions based on scout findings."""
        # Derive key sub-topics surfaced in Wave 0
        discovered_topics = []
        for f in scout_findings:
            discovered_topics.extend(f.sub_topics)

        # 3 Orthogonal angles
        angles = [
            ("Core Architecture & Implementation Specs", ["github.com", "readthedocs.io"]),
            ("Failure Modes, Edge Cases & Performance Bottlenecks", ["stackoverflow.com", "news.ycombinator.com"]),
            ("Ecosystem Standards, Security & Adversarial Vulnerabilities", ["cve.mitre.org", "arxiv.org"]),
        ]

        queries = []
        for angle, domains in angles:
            queries.append(
                ResearchQuery(
                    wave=ResearchWave.EXPANSION,
                    topic=self.seed_topic,
                    angle=angle,
                    target_domains=domains,
                )
            )
        return queries

    def plan_wave_2(self, wave_1_findings: List[ResearchFinding]) -> List[ResearchQuery]:
        """Wave 2 (Deep Swarm): 8 parallel specialized agents executing deep-dive research."""
        # 8 Specialized research disciplines
        disciplines = [
            ("Formal Specifications & Protocol Standards", ["ietf.org", "w3.org", "github.com"]),
            ("Kernel / OS & Process Isolation Hardening", ["kernel.org", "man7.org", "docs.kernel.org"]),
            ("Adversarial Threat Modeling & Exploit Vectors", ["nvd.nist.gov", "owasp.org"]),
            ("Empirical Benchmarks & Comparative Latency", ["arxiv.org", "paperswithcode.com"]),
            ("Developer Ergonomics & Production Pain Points", ["github.com/issues", "reddit.com"]),
            ("Anti-Cheating, Guardrails & Evaluation Integrity", ["evals.openai.com", "arxiv.org"]),
            ("Supply Chain Security & Dependency Blast Radius", ["snyk.io", "deps.dev"]),
            ("Future Horizon, Research Trajectory & Emerging RFCs", ["arxiv.org", "news.ycombinator.com"]),
        ]

        queries = []
        for angle, domains in disciplines:
            queries.append(
                ResearchQuery(
                    wave=ResearchWave.DEEP_SWARM,
                    topic=self.seed_topic,
                    angle=angle,
                    target_domains=domains,
                )
            )
        return queries

    def synthesize_ontology(self, all_findings: List[ResearchFinding]) -> ResearchOntology:
        """Synthesize multi-agent findings into a cohesive knowledge ontology."""
        concepts: Set[str] = set()
        relationships: List[Dict[str, str]] = []

        prev_concept: Optional[str] = None
        for finding in all_findings:
            for sub in finding.sub_topics:
                norm_sub = sub.strip().lower()
                concepts.add(norm_sub)
                if prev_concept and prev_concept != norm_sub:
                    relationships.append({
                        "from": prev_concept,
                        "type": "relates_to",
                        "to": norm_sub
                    })
                prev_concept = norm_sub

        return ResearchOntology(
            seed_topic=self.seed_topic,
            concepts=concepts,
            relationships=relationships,
            sources_count=len({f.source_url for f in all_findings if f.source_url}),
            findings_count=len(all_findings),
        )
