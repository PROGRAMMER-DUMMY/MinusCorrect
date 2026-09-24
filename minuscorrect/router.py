"""
MinusCorrect Smart Intent Router.
Classifies incoming user requests, error telemetry, and architectural queries
into precise operational execution routes without manual command micromanagement.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import json
from pathlib import Path
import re
from typing import Any, Dict, List, Optional


class RouteType:
    INTAKE = "INTAKE"
    RULE = "RULE"
    COUNCIL = "COUNCIL"
    SPEC_GENERATE = "SPEC_GENERATE"
    ASK_MATT = "ASK_MATT"
    INCIDENT = "INCIDENT"
    PRE_LAUNCH_AUDIT = "PRE_LAUNCH_AUDIT"
    SUPERVISED_RUN = "SUPERVISED_RUN"
    TICKET = "TICKET"
    ANTI_CHEAT = "ANTI_CHEAT"
    DEEP_RESEARCH = "DEEP_RESEARCH"


@dataclass
class RoutingDecision:
    """The outcome of the smart router's intent classification."""
    route: str
    confidence: float
    recommended_command: str
    rationale: str
    extracted_entities: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)

    def format_text(self) -> str:
        lines = [
            "=" * 72,
            "               MinusCorrect Smart Intent Router",
            "=" * 72,
            f"Detected Route:       [{self.route}] (Confidence: {self.confidence:.0%})",
            f"Recommended Command:  {self.recommended_command}",
            f"Rationale:            {self.rationale}",
        ]
        if self.extracted_entities:
            lines.append("Extracted Entities:")
            for k, v in self.extracted_entities.items():
                lines.append(f"  - {k}: {v}")
        lines.append("=" * 72)
        return "\n".join(lines)


def route_intent(query: str, cwd: Optional[Path] = None) -> RoutingDecision:
    """
    Classifies a natural-language request or telemetry dump into a deterministic MinusCorrect route.
    # verifies: tests/unit/test_router.py
    """
    text = query.strip()

    # 0. Check for Cognitive Intake Intent (Conversational multi-intent, implicit rules, auto-deliberation)
    intake_patterns = [
        r"i mean",
        r"understand the intent",
        r"without.*mentioning.*rule",
        r"write the tickets of implementation",
        r"add those things",
        r"and make sure we",
    ]
    if any(re.search(pat, text, re.IGNORECASE) for pat in intake_patterns):
        return RoutingDecision(
            route=RouteType.INTAKE,
            confidence=0.97,
            recommended_command=f"minuscorrect intake \"{text[:60]}\"",
            rationale="Query contains conversational feature request with implicit invariants, requiring autonomous cognitive intake, rule extraction, and MinusCouncil ticket generation.",
            extracted_entities={"prompt": text[:60]},
        )

    # Check for Rule Management Intent
    rule_keywords = ["rule add", "rule list", "project rules", ".minus/rules", "manage rules"]
    if any(kw in text.lower() for kw in rule_keywords):
        return RoutingDecision(
            route=RouteType.RULE,
            confidence=0.95,
            recommended_command="minuscorrect rule list",
            rationale="Detected project rule management or inspection intent.",
            extracted_entities={"scope": "rule_store"},
        )

    # 1. Check for Crash Telemetry / Tracebacks (INCIDENT)
    if any(sig in text for sig in ("Traceback (most recent call last):", "Error: ", "FATAL:", "Exception in thread", "HTTP 500")):
        return RoutingDecision(
            route=RouteType.INCIDENT,
            confidence=0.98,
            recommended_command="minuscorrect incident -",
            rationale="Detected stack trace or unhandled exception telemetry in input.",
            extracted_entities={"type": "crash_payload"},
        )

    # 2. Check for Pre-Launch / Security Audit Intent
    audit_keywords = ["pre-launch", "audit", "security check", "owasp", "secret leak", "rls check", "launch readiness", "vulnerability"]
    if any(kw in text.lower() for kw in audit_keywords):
        return RoutingDecision(
            route=RouteType.PRE_LAUNCH_AUDIT,
            confidence=0.92,
            recommended_command="minuscorrect audit --pre-launch",
            rationale="Query seeks operational or security audit across the 10 production domains.",
            extracted_entities={"scope": "10-domain-pre-launch"},
        )

    # 3. Check for Anti-Cheat / Overfitting / Benchmark Maxxing Intent
    cheat_keywords = ["overfit", "overfitting", "benchmark", "cheating", "hardcoded", "tautology", "cheat", "metric maxxing"]
    if any(kw in text.lower() for kw in cheat_keywords):
        return RoutingDecision(
            route=RouteType.ANTI_CHEAT,
            confidence=0.94,
            recommended_command="minuscorrect anti-cheat",
            rationale="Query relates to detecting benchmark overfitting, hardcoded test logic, or tautological assertions.",
            extracted_entities={"scope": "anti-cheating-guardian"},
        )

    # 4. Check for Ticket Management Intent
    ticket_keywords = ["ticket create", "ticket list", "close ticket", "open tickets", "my tickets", ".minus/tickets"]
    if any(kw in text.lower() for kw in ticket_keywords):
        return RoutingDecision(
            route=RouteType.TICKET,
            confidence=0.95,
            recommended_command="minuscorrect ticket list",
            rationale="Detected second-brain ticket lifecycle operation.",
            extracted_entities={"scope": "ticket_store"},
        )

    # 5. Check for Deep Web Research Intent
    research_keywords = ["deep research", "web research", "research swarm", "research ontology", "research on", "investigate topic", "multi-agent research"]
    if any(kw in text.lower() for kw in research_keywords):
        return RoutingDecision(
            route=RouteType.DEEP_RESEARCH,
            confidence=0.96,
            recommended_command=f"minuscorrect research \"{text[:60]}\"",
            rationale="Query requests multi-agent 3-wave deep research and ontology synthesis.",
            extracted_entities={"topic": text[:60]},
        )

    # 5. Check for Council Intent (Debate, trade-offs, architecture dilemma)
    council_keywords = ["should i", "which option", "tradeoff", "trade-off", "council", "debate", "pros and cons", "pressure test", "dilemma"]
    if any(kw in text.lower() for kw in council_keywords):
        return RoutingDecision(
            route=RouteType.COUNCIL,
            confidence=0.91,
            recommended_command=f"minuscorrect council \"{text[:60]}\"",
            rationale="Detected architectural decision dilemma requiring multi-perspective advisor deliberation.",
            extracted_entities={"topic": text[:60]},
        )

    # 6. Check for Greenfield Specification Scaffolding Intent
    spec_keywords = ["scaffold spec", "prd", "trd", "refero design", "design system", "generate schema", "new project spec", "appflow"]
    if any(kw in text.lower() for kw in spec_keywords):
        return RoutingDecision(
            route=RouteType.SPEC_GENERATE,
            confidence=0.93,
            recommended_command="minuscorrect spec init --dir spec",
            rationale="Query requests full-stack specification suite (PRD, TRD, Refero DESIGN, APPFLOW, SCHEMA).",
            extracted_entities={"target_dir": "spec"},
        )

    # 7. Check for Ask-Matt Implementation Plan Intent
    plan_keywords = ["implement", "tickets", "tracer bullet", "spec to tickets", "decompose", "break down into tickets", "plan"]
    if any(kw in text.lower() for kw in plan_keywords):
        return RoutingDecision(
            route=RouteType.ASK_MATT,
            confidence=0.90,
            recommended_command=f"minuscorrect ask-matt \"{text[:60]}\"",
            rationale="Query requests decomposition into a dependency DAG of domain-specialist tracer-bullet tickets.",
            extracted_entities={"idea": text[:60]},
        )

    # 8. Default to Supervised Execution
    return RoutingDecision(
        route=RouteType.SUPERVISED_RUN,
        confidence=0.75,
        recommended_command="minuscorrect run --worktree --isolate-env -- pytest",
        rationale="Standard test-driven bug repair or code modification under supervised 4-loop ceiling.",
        extracted_entities={"strategy": "supervised_execution"},
    )
