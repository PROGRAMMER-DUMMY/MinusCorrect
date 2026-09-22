"""
Unit tests for MinusCorrect Smart Intent Router (minuscorrect/router.py).
"""

from minuscorrect.router import RouteType, route_intent


def test_route_incident() -> None:
    crash = """
    Traceback (most recent call last):
      File "main.py", line 42, in <module>
        raise ValueError("Invalid session")
    """
    decision = route_intent(crash)
    assert decision.route == RouteType.INCIDENT
    assert "incident" in decision.recommended_command
    assert decision.confidence >= 0.9


def test_route_pre_launch_audit() -> None:
    decision = route_intent("Perform a pre-launch security audit checking for RLS and secret leaks")
    assert decision.route == RouteType.PRE_LAUNCH_AUDIT
    assert "audit --pre-launch" in decision.recommended_command


def test_route_anti_cheat() -> None:
    decision = route_intent("Check if the agent is overfitting to benchmark test fixtures or using hardcoded logic")
    assert decision.route == RouteType.ANTI_CHEAT
    assert "anti-cheat" in decision.recommended_command


def test_route_ticket() -> None:
    decision = route_intent("List all open tickets in .minus/tickets")
    assert decision.route == RouteType.TICKET
    assert "ticket list" in decision.recommended_command


def test_route_council() -> None:
    decision = route_intent("Should I use Redis or PostgreSQL for distributed locking? What are the tradeoffs?")
    assert decision.route == RouteType.COUNCIL
    assert "council" in decision.recommended_command


def test_route_spec() -> None:
    decision = route_intent("Scaffold full spec suite with PRD, TRD, and Refero design system for new project")
    assert decision.route == RouteType.SPEC_GENERATE
    assert "spec init" in decision.recommended_command


def test_route_ask_matt() -> None:
    decision = route_intent("Implement a new billing module and break down into tracer bullet tickets")
    assert decision.route == RouteType.ASK_MATT
    assert "ask-matt" in decision.recommended_command


def test_route_default_supervised_run() -> None:
    decision = route_intent("Fix the flaky unit test in test_worker.py")
    assert decision.route == RouteType.SUPERVISED_RUN
    assert "minuscorrect run" in decision.recommended_command
