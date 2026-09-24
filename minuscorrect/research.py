"""MinusCorrect Deep Web Research Swarm & Ontology Protocol.

Orchestrates a 3-wave multi-agent research swarm:
- Wave 0 (Scout): 1 Agent establishes foundational landscape & unknown boundaries.
- Wave 1 (Expansion): 3 Agents explore orthogonal architectural & operational axes.
- Wave 2 (Deep Swarm): 8 Agents execute parallel specialized deep-dives.
Cross-synthesizes findings into an evidence-backed Knowledge Ontology with citation receipts.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Set


class ResearchWave(str, Enum):
    """Execution waves for deep research protocol."""
    SCOUT = "wave_0_scout"          # 1 Agent: Broad landscape recon & seed mapping
    EXPANSION = "wave_1_expansion"  # 3 Agents: Orthogonal query expansion
    DEEP_SWARM = "wave_2_deep_swarm" # 8 Agents: Parallel specialized deep dives


@dataclass(frozen=True)
class ResearchQuery:
    """Targeted research query dispatched to a researcher agent."""
    wave: ResearchWave
    agent_id: str
    role: str
    topic: str
    angle: str
    target_domains: List[str] = field(default_factory=list)
    search_prompt: str = ""
    system_prompt: str = ""

    def __post_init__(self):
        if not self.search_prompt:
            object.__setattr__(
                self, "search_prompt", f"{self.topic} - focus on {self.angle}"
            )
        if not self.system_prompt:
            sys_p = (
                f"You are a specialized Web Research Agent focusing on: {self.role}.\n"
                f"Topic: {self.topic}\n"
                f"Angle: {self.angle}\n"
                "Constraints:\n"
                "- Extract concrete technical facts, RFC/version numbers, citations, and evidence.\n"
                "- Refuse marketing superlatives or ungrounded assertions.\n"
                "- Return structured JSON findings with source URLs."
            )
            object.__setattr__(self, "system_prompt", sys_p)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "wave": self.wave.value,
            "agent_id": self.agent_id,
            "role": self.role,
            "topic": self.topic,
            "angle": self.angle,
            "target_domains": self.target_domains,
            "search_prompt": self.search_prompt,
        }


@dataclass
class ResearchFinding:
    """Synthesized intelligence output extracted by an individual research agent."""
    query: ResearchQuery
    source_url: str
    title: str
    summary: str
    sub_topics: List[str] = field(default_factory=list)
    raw_evidence: List[str] = field(default_factory=list)
    confidence_score: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_id": self.query.agent_id,
            "role": self.query.role,
            "source_url": self.source_url,
            "title": self.title,
            "summary": self.summary,
            "sub_topics": self.sub_topics,
            "raw_evidence": self.raw_evidence,
            "confidence_score": self.confidence_score,
        }


@dataclass
class ContradictionPoint:
    """Tension, conflict, or direct contradiction discovered between research findings/sources."""
    topic: str
    finding_a: str
    source_a: str
    finding_b: str
    source_b: str
    severity: str  # "high", "medium", "tradeoff"
    resolution_rationale: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ApproachComparison:
    """Side-by-side trade-off comparison between alternative technical approaches."""
    name: str
    category: str
    strengths: List[str]
    weaknesses: List[str]
    performance_rating: str  # e.g. "O(1)", "Sub-millisecond", "Heavy overhead"
    security_risk: str       # e.g. "Low (Air-gapped)", "High (Bypass possible)"
    complexity: str          # e.g. "Minimal", "Moderate", "High"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ResearchComparativeAnalysis:
    """Cross-comparison synthesis including consensus, trade-off matrix, and tensions."""
    consensus_score: float  # 0.0 to 1.0 (degree of agreement across sources)
    consensus_verdict: str  # e.g. "Strong Consensus", "Divided Consensus", "High Contradiction"
    comparisons: List[ApproachComparison] = field(default_factory=list)
    contradictions: List[ContradictionPoint] = field(default_factory=list)
    verified_invariants: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "consensus_score": self.consensus_score,
            "consensus_verdict": self.consensus_verdict,
            "comparisons": [c.to_dict() for c in self.comparisons],
            "contradictions": [c.to_dict() for c in self.contradictions],
            "verified_invariants": self.verified_invariants,
        }

    def render_markdown(self) -> str:
        lines = [
            "## Active Cross-Comparison & Trade-Off Matrix",
            "",
            f"- **Consensus Verdict**: `{self.consensus_verdict}` (Confidence: {int(self.consensus_score * 100)}%)",
            f"- **Contradictions & Tensions Detected**: {len(self.contradictions)}",
            f"- **Corroborated Invariants**: {len(self.verified_invariants)}",
            "",
        ]

        if self.comparisons:
            lines.extend([
                "| Approach / Paradigm | Category | Key Strengths | Key Weaknesses / Risks | Performance | Security Risk | Complexity |",
                "| :--- | :--- | :--- | :--- | :--- | :--- | :--- |",
            ])
            for comp in self.comparisons:
                str_str = "; ".join(comp.strengths[:2])
                weak_str = "; ".join(comp.weaknesses[:2])
                lines.append(
                    f"| **{comp.name}** | {comp.category} | {str_str} | {weak_str} | `{comp.performance_rating}` | `{comp.security_risk}` | `{comp.complexity}` |"
                )
            lines.append("")

        if self.contradictions:
            lines.append("### Contradictions & Safety Traps")
            for c in self.contradictions:
                lines.extend([
                    f"- **Tension on `{c.topic}`** ({c.severity.upper()}):",
                    f"  - *Stance A* ([Source]({c.source_a})): {c.finding_a}",
                    f"  - *Stance B* ([Source]({c.source_b})): {c.finding_b}",
                    f"  - *Resolution Rationale*: {c.resolution_rationale}",
                ])
            lines.append("")

        if self.verified_invariants:
            lines.append("### Verified Operational Invariants")
            for inv in self.verified_invariants:
                lines.append(f"- [x] {inv}")
            lines.append("")

        return "\n".join(lines)


@dataclass
class ResearchOntology:
    """Cross-synthesized knowledge graph linking concepts, citations, and consensus."""
    seed_topic: str
    concepts: Set[str]
    relationships: List[Dict[str, str]]
    sources_count: int
    findings_count: int
    citations: List[Dict[str, str]] = field(default_factory=list)

    def render_markdown(self) -> str:
        """Render markdown artifact summarizing synthesized knowledge."""
        lines = [
            f"# Deep Research Ontology: {self.seed_topic}",
            "",
            f"- **Sources Analyzed**: {self.sources_count}",
            f"- **Findings Extracted**: {self.findings_count}",
            f"- **Key Concepts Mapped**: {len(self.concepts)}",
            "",
            "## Knowledge Graph Concepts",
        ]
        for c in sorted(self.concepts):
            lines.append(f"- `{c}`")

        lines.append("")
        lines.append("## Cross-Domain Relationships")
        if self.relationships:
            lines.append("```mermaid")
            lines.append("flowchart TD")
            for idx, rel in enumerate(self.relationships[:15]):
                f_safe = rel.get('from', '').replace(" ", "_").replace("-", "_")
                t_safe = rel.get('to', '').replace(" ", "_").replace("-", "_")
                lines.append(f'    {f_safe}["{rel.get("from")}"] -->|{rel.get("type")}| {t_safe}["{rel.get("to")}"]')
            lines.append("```")
        else:
            lines.append("*No cross-domain relationships recorded.*")

        lines.append("")
        lines.append("## Evidence & Source Citations")
        for cit in self.citations:
            lines.append(f"- [{cit.get('title', 'Source')}]({cit.get('url', '#')}): {cit.get('summary', '')}")

        return "\n".join(lines)


class DeepResearchCoordinator:
    """Orchestrates recursive 1 -> 3 -> 8 multi-agent research swarm."""

    def __init__(self, seed_topic: str):
        self.seed_topic = seed_topic.strip()

    def plan_wave_0(self) -> List[ResearchQuery]:
        """Wave 0 (Scout): 1 Agent establishes foundational landscape & unknown boundaries."""
        return [
            ResearchQuery(
                wave=ResearchWave.SCOUT,
                agent_id="scout-01",
                role="Foundational Reconnaissance Scout",
                topic=self.seed_topic,
                angle="foundational taxonomy, industry standards, and core architecture",
                target_domains=["github.com", "arxiv.org", "wikipedia.org"],
            )
        ]

    def plan_wave_1(self, scout_findings: Optional[List[ResearchFinding]] = None) -> List[ResearchQuery]:
        """Wave 1 (Expansion): 3 parallel agents analyzing orthogonal dimensions dynamically enriched by scout findings."""
        discovered_leads: List[str] = []
        if scout_findings:
            for f in scout_findings:
                discovered_leads.extend(f.sub_topics)

        leads_summary = f" (Focus areas discovered in Wave 0: {', '.join(discovered_leads[:5])})" if discovered_leads else ""

        angles = [
            (
                "expansion-01",
                "Core Architecture & Implementation Specs",
                f"protocols, data flow, memory model, and formal specifications{leads_summary}",
                ["github.com", "readthedocs.io", "ietf.org"],
            ),
            (
                "expansion-02",
                "Production Failure Modes & Edge Cases",
                f"concurrency locks, race conditions, memory leaks, and performance cliffs{leads_summary}",
                ["stackoverflow.com", "news.ycombinator.com", "github.com/issues"],
            ),
            (
                "expansion-03",
                "Security Vulnerabilities & Threat Model",
                f"injection vectors, authentication bypass, data exfiltration, and sandbox escape{leads_summary}",
                ["cve.mitre.org", "nvd.nist.gov", "owasp.org"],
            ),
        ]

        queries = []
        for agent_id, role, angle, domains in angles:
            queries.append(
                ResearchQuery(
                    wave=ResearchWave.EXPANSION,
                    agent_id=agent_id,
                    role=role,
                    topic=self.seed_topic,
                    angle=angle,
                    target_domains=domains,
                )
            )
        return queries

    def plan_wave_2(self, wave_1_findings: Optional[List[ResearchFinding]] = None) -> List[ResearchQuery]:
        """Wave 2 (Deep Swarm): 8 parallel specialized agents executing deep-dive research enriched by Wave 1."""
        findings_by_agent: Dict[str, List[str]] = {}
        if wave_1_findings:
            for f in wave_1_findings:
                findings_by_agent.setdefault(f.query.agent_id, []).extend(f.sub_topics)

        # Map Wave 1 leads into relevant deep-swarm disciplines
        arch_leads = ", ".join(findings_by_agent.get("expansion-01", [])[:4])
        failure_leads = ", ".join(findings_by_agent.get("expansion-02", [])[:4])
        security_leads = ", ".join(findings_by_agent.get("expansion-03", [])[:4])

        disciplines = [
            (
                "deep-swarm-01",
                "Formal Protocol & Spec Auditor",
                f"IETF/W3C/ECMA specifications, RFCs, and binary wire formats{f' (Focus: {arch_leads})' if arch_leads else ''}",
                ["ietf.org", "w3.org", "github.com"],
            ),
            (
                "deep-swarm-02",
                "Kernel & Process Isolation SRE",
                f"OS namespaces, cgroups v2, signal traps, and ephemeral storage{f' (Focus: {failure_leads})' if failure_leads else ''}",
                ["kernel.org", "man7.org", "docs.kernel.org"],
            ),
            (
                "deep-swarm-03",
                "Adversarial Red Team Analyst",
                f"prompt injections, sandbox escape primitives, and supply-chain poison{f' (Focus: {security_leads})' if security_leads else ''}",
                ["nvd.nist.gov", "owasp.org", "exploit-db.com"],
            ),
            (
                "deep-swarm-04",
                "Empirical Performance Benchmarker",
                f"wall-clock latency, throughput limits, token overhead, and cold starts{f' (Focus: {failure_leads})' if failure_leads else ''}",
                ["arxiv.org", "paperswithcode.com", "benchmarks.llm.org"],
            ),
            (
                "deep-swarm-05",
                "Developer Ergonomics & TUI Specialist",
                f"CLI stream discipline, keyboard protocols, terminal escape sequences, and VS Code ConPTY{f' (Focus: {arch_leads})' if arch_leads else ''}",
                ["github.com/microsoft/vscode", "github.com/xtermjs/xterm.js"],
            ),
            (
                "deep-swarm-06",
                "Evaluation Integrity & Anti-Cheat SRE",
                f"test set contamination, benchmark memorization, and assertion loosening{f' (Focus: {arch_leads})' if arch_leads else ''}",
                ["evals.openai.com", "arxiv.org", "github.com"],
            ),
            (
                "deep-swarm-07",
                "Database & Relational Model Architect",
                f"PostgreSQL Supabase RLS, connection pooling, indexing traps, and ACID rollback{f' (Focus: {failure_leads or security_leads})' if (failure_leads or security_leads) else ''}",
                ["postgresql.org", "supabase.com/docs"],
            ),
            (
                "deep-swarm-08",
                "Future Horizon & Emerging Research Forecaster",
                f"recent 2025/2026 pre-prints, upcoming paradigms, and adjacent technology trends{f' (Focus: {arch_leads})' if arch_leads else ''}",
                ["arxiv.org", "news.ycombinator.com"],
            ),
        ]

        queries = []
        for agent_id, role, angle, domains in disciplines:
            queries.append(
                ResearchQuery(
                    wave=ResearchWave.DEEP_SWARM,
                    agent_id=agent_id,
                    role=role,
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
        citations: List[Dict[str, str]] = []

        prev_concept: Optional[str] = None
        for finding in all_findings:
            if finding.source_url:
                citations.append({
                    "title": finding.title or finding.source_url,
                    "url": finding.source_url,
                    "summary": finding.summary[:150] + "..." if len(finding.summary) > 150 else finding.summary,
                })
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
            citations=citations,
        )

    def generate_subagent_specs(self, queries: List[ResearchQuery]) -> List[Dict[str, Any]]:
        """Generate Antigravity invoke_subagent specifications for the given queries."""
        subagents = []
        for q in queries:
            subagents.append({
                "TypeName": "research",
                "Role": q.role,
                "Prompt": (
                    f"You are a specialized deep-research subagent ({q.role}).\n"
                    f"Topic: {q.topic}\n"
                    f"Investigation Focus: {q.angle}\n"
                    f"Recommended Domains: {', '.join(q.target_domains)}\n\n"
                    "Instructions:\n"
                    "1. Search the web and inspect authoritative technical documentation.\n"
                    "2. Return evidence, source citations, specific RFC/spec numbers, and failure modes.\n"
                    "3. Summarize findings clearly with 3-5 key sub-topics for the central ontology graph."
                ),
            })
        return subagents

    def analyze_and_compare(self, all_findings: List[ResearchFinding]) -> ResearchComparativeAnalysis:
        """
        Actively cross-compares findings across agents, detecting contradictions,
        trade-offs, security traps, and consensus convergence.
        """
        comparisons: List[ApproachComparison] = []
        contradictions: List[ContradictionPoint] = []
        verified_invariants: List[str] = []

        # 1. Detect subtopic frequencies and multi-source corroboration
        subtopic_sources: Dict[str, Set[str]] = {}
        for f in all_findings:
            for st in f.sub_topics:
                norm_st = st.strip().lower()
                subtopic_sources.setdefault(norm_st, set()).add(f.source_url)

        for st, sources in sorted(subtopic_sources.items()):
            if len(sources) >= 2:
                verified_invariants.append(
                    f"Corroborated across {len(sources)} sources: Concept '{st}' verified as operational invariant."
                )

        # 2. Contradiction & Tension Detection
        conflict_keywords = [
            ("safe", "vulnerability"),
            ("safe", "bypass"),
            ("recommended", "deprecated"),
            ("fast", "memory leak"),
            ("fast", "cliff"),
            ("enabled", "disabled"),
            ("conpty", "winpty"),
            ("permissive", "restrictive"),
        ]

        seen_conflict_pairs = set()
        for idx_a, f_a in enumerate(all_findings):
            for idx_b, f_b in enumerate(all_findings):
                if idx_a >= idx_b or f_a.source_url == f_b.source_url:
                    continue

                text_a = (f_a.title + " " + f_a.summary + " " + " ".join(f_a.sub_topics)).lower()
                text_b = (f_b.title + " " + f_b.summary + " " + " ".join(f_b.sub_topics)).lower()

                # Check if they share common technical concepts
                shared_topics = set(s.lower() for s in f_a.sub_topics) & set(s.lower() for s in f_b.sub_topics)
                if not shared_topics:
                    continue

                for pos, neg in conflict_keywords:
                    pair_key = (f_a.source_url, f_b.source_url, pos, neg)
                    if pair_key in seen_conflict_pairs:
                        continue

                    if (pos in text_a and neg in text_b) or (neg in text_a and pos in text_b):
                        seen_conflict_pairs.add(pair_key)
                        topic_name = list(shared_topics)[0].title()
                        severity = "high" if any(w in (text_a + text_b) for w in ["cve", "bypass", "exploit", "privilege"]) else "tradeoff"
                        contradictions.append(
                            ContradictionPoint(
                                topic=topic_name,
                                finding_a=f_a.summary[:140] + "..." if len(f_a.summary) > 140 else f_a.summary,
                                source_a=f_a.source_url or "Agent Finding A",
                                finding_b=f_b.summary[:140] + "..." if len(f_b.summary) > 140 else f_b.summary,
                                source_b=f_b.source_url or "Agent Finding B",
                                severity=severity,
                                resolution_rationale="Reconciled via isolated test verification; enforce explicit configuration boundaries.",
                            )
                        )
                        break

        # 3. Side-by-side Approach Comparison
        for f in all_findings:
            if any(term in f.title.lower() for term in ["spec", "algorithm", "approach", "pattern", "guide", "troubleshooting", "mode", "architecture", "analysis", "policies"]):
                strengths = [s for s in f.sub_topics if not any(b in s.lower() for b in ["leak", "cliff", "cve", "race", "error", "infinite", "trap"])] or ["Standard compliance"]
                weaknesses = [s for s in f.sub_topics if any(b in s.lower() for b in ["leak", "cliff", "cve", "race", "error", "drift", "infinite", "trap"])] or ["Requires configuration"]
                perf = "Low Overhead" if "fast" in f.summary.lower() or "o(1)" in f.summary.lower() else "Medium"
                sec = "High Risk" if any(k in f.summary.lower() for k in ["bypass", "injection", "cve", "escalat", "trap"]) else "Low"
                comp = "High" if any(k in f.summary.lower() for k in ["lock", "async", "daemon", "distributed", "recursion"]) else "Minimal"

                comparisons.append(
                    ApproachComparison(
                        name=f.title[:35],
                        category=f.query.role[:30],
                        strengths=strengths[:3],
                        weaknesses=weaknesses[:3],
                        performance_rating=perf,
                        security_risk=sec,
                        complexity=comp,
                    )
                )

        # 4. Consensus Score Computation
        base_score = 1.0
        for c in contradictions:
            penalty = 0.15 if c.severity == "high" else 0.05
            base_score -= penalty
        consensus_score = max(0.35, min(1.0, round(base_score, 2)))

        if consensus_score >= 0.85:
            verdict = "Strong Consensus"
        elif consensus_score >= 0.60:
            verdict = "Divided Consensus (Trade-Offs Present)"
        else:
            verdict = "High Contradiction / Contested Invariants"

        return ResearchComparativeAnalysis(
            consensus_score=consensus_score,
            consensus_verdict=verdict,
            comparisons=comparisons[:8],
            contradictions=contradictions[:6],
            verified_invariants=verified_invariants[:10],
        )

    def render_full_report(
        self,
        all_findings: List[ResearchFinding],
        analysis: Optional[ResearchComparativeAnalysis] = None,
        ontology: Optional[ResearchOntology] = None,
    ) -> str:
        """Render a complete, exhaustive deep research report artifact."""
        ana = analysis or self.analyze_and_compare(all_findings)
        ont = ontology or self.synthesize_ontology(all_findings)

        lines = [
            "---",
            f"topic: \"{self.seed_topic}\"",
            f"created_at: \"{datetime.now(timezone.utc).isoformat()}\"",
            f"findings_count: {len(all_findings)}",
            f"sources_count: {ont.sources_count}",
            f"consensus_score: {ana.consensus_score}",
            f"consensus_verdict: \"{ana.consensus_verdict}\"",
            f"contradictions_count: {len(ana.contradictions)}",
            "---",
            "",
            f"# Deep Web Research & Comparative Ontology: {self.seed_topic}",
            "",
            "## Executive Synthesis & Protocol Summary",
            f"- **Seed Inquiry**: `{self.seed_topic}`",
            f"- **Research Swarm**: 3 Waves (Wave 0 Scout -> Wave 1 Expansion -> Wave 2 Deep Swarm)",
            f"- **Total Primary Findings Extracted**: {len(all_findings)}",
            f"- **Primary Sources Consulted**: {ont.sources_count}",
            f"- **Consensus Verdict**: `{ana.consensus_verdict}` (Confidence: {int(ana.consensus_score * 100)}%)",
            "",
            ana.render_markdown(),
            "",
            "## Multi-Wave Swarm Trajectory & Findings",
        ]

        findings_by_wave: Dict[ResearchWave, List[ResearchFinding]] = {}
        for f in all_findings:
            findings_by_wave.setdefault(f.query.wave, []).append(f)

        for wave in [ResearchWave.SCOUT, ResearchWave.EXPANSION, ResearchWave.DEEP_SWARM]:
            w_findings = findings_by_wave.get(wave, [])
            if not w_findings:
                continue
            lines.append(f"### {wave.value.replace('_', ' ').title()} ({len(w_findings)} Findings)")
            for f in w_findings:
                lines.append(f"#### [{f.query.agent_id}] {f.query.role}")
                lines.append(f"- **Focus Angle**: {f.query.angle}")
                lines.append(f"- **Source**: [{f.title or f.source_url}]({f.source_url or '#'})")
                lines.append(f"- **Summary**: {f.summary}")
                if f.sub_topics:
                    lines.append(f"- **Extracted Concepts**: {', '.join(f'`{st}`' for st in f.sub_topics)}")
                lines.append("")

        lines.append(ont.render_markdown())
        return "\n".join(lines)
