"""
Unit tests for MinusCorrect Domain Specialists Engine (minuscorrect/specialists.py).
"""

from minuscorrect.specialists import (
    SPECIALISTS,
    build_specialist_prompt,
    get_specialist,
    list_specialists,
)


def test_specialists_catalog_complete() -> None:
    expected_roles = {
        "Process Isolation SRE",
        "Security & Policy Auditor",
        "Distributed Systems Engineer",
        "Storage & Database Specialist",
        "Frontend & UI/UX Specialist",
        "TDD & Verification Lead",
    }
    assert set(SPECIALISTS.keys()) == expected_roles


def test_get_specialist_lookup_and_fallback() -> None:
    spec = get_specialist("Security & Policy Auditor")
    assert spec.role == "Security & Policy Auditor"
    assert len(spec.domain_invariants) >= 3

    fallback = get_specialist("NonExistentSpecialist")
    assert fallback.role == "Process Isolation SRE"


def test_list_specialists() -> None:
    specs = list_specialists()
    assert len(specs) == 6
    for s in specs:
        assert "role" in s
        assert "title" in s
        assert "focus" in s


def test_render_system_prompt() -> None:
    spec = get_specialist("Distributed Systems Engineer")
    prompt = spec.render_system_prompt()
    assert "Distributed Systems & Concurrency Engineer" in prompt
    assert "Non-Negotiable Domain Invariants" in prompt
    assert "Idempotency-Key" in prompt
    assert "Prohibited Actions" in prompt


def test_build_specialist_prompt() -> None:
    prompt = build_specialist_prompt(
        ticket_id="TICKET-42",
        title="Implement Circuit Breaker",
        role="Distributed Systems Engineer",
        objective="Wrap external API calls in 3.0s timeout",
        target_files=["src/api.py"],
        protected_boundaries=["tests/golden/*"],
        verification="pytest tests/unit/",
    )

    assert "TICKET-42" in prompt
    assert "Implement Circuit Breaker" in prompt
    assert "Distributed Systems & Concurrency Engineer" in prompt
    assert "src/api.py" in prompt
    assert "tests/golden/*" in prompt
    assert "pytest tests/unit/" in prompt
