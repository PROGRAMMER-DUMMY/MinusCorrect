"""
Unit Tests for MinusCorrect Decision Engine and Typed Primitives.
Verifies Choice, Score, Noul schemas, LocalRuleEngine deterministic resolution,
and JevProvider network fallback behavior.
"""

from unittest.mock import MagicMock, patch
import urllib.error
import pytest

from minuscorrect.types.decision import (
    Choice,
    Score,
    Noul,
    DecisionBatch,
    DecisionResponse,
)
from minuscorrect.decision import (
    LocalRuleEngine,
    JevProvider,
    MockDecisionEngine,
    get_decision_engine,
)


def test_decision_primitives_serialization():
    choice = Choice(
        instructions="Select target file",
        criteria={"src/auth.py": "Authentication logic", "src/db.py": "Database operations"}
    )
    score = Score(
        instructions="Rate patch safety",
        min_val=0.0,
        max_val=10.0
    )
    noul = Noul(
        instructions="Does the patch breach the golden test boundary?",
        threshold=0.8
    )

    batch = DecisionBatch(
        state="Modifying src/auth.py to fix token refresh bug. All golden tests clean.",
        questions={
            "target": choice,
            "safety": score,
            "breach": noul,
        }
    )

    data = batch.to_dict()
    assert data["state"].startswith("Modifying src/auth.py")
    assert "target" in data["questions"]
    assert data["questions"]["target"]["type"] == "choice"
    assert data["questions"]["safety"]["type"] == "score"
    assert data["questions"]["breach"]["type"] == "noul"


def test_local_rule_engine_deterministic_resolution():
    engine = LocalRuleEngine()

    batch = DecisionBatch(
        state="AST analysis confirms only src/auth.py is modified. Tests pass safely with zero regressions.",
        questions={
            "target": Choice(
                instructions="Which file was modified?",
                criteria={"auth": "src/auth.py", "database": "src/db.py"}
            ),
            "safety": Score(
                instructions="Safety score",
                min_val=1.0,
                max_val=5.0
            ),
            "passes_audit": Noul(
                instructions="Tests pass safely",
                threshold=0.5
            ),
        }
    )

    resp = engine.evaluate(batch)
    assert resp.provider == "local-rules"
    assert "target" in resp.answers
    assert resp.answers["target"].choice == "auth"
    assert resp.answers["safety"].score >= 1.0
    assert resp.answers["passes_audit"].passed is True
    assert 0.0 <= resp.answers["passes_audit"].probability <= 1.0


def test_jev_provider_fallback_when_no_api_key(monkeypatch):
    monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)
    jev = JevProvider(api_key=None)

    batch = DecisionBatch(
        state="Offline test state",
        questions={"check": Noul(instructions="Is system intact?", threshold=0.5)}
    )

    # Should fall back cleanly without raising
    resp = jev.evaluate(batch)
    assert resp.provider == "local-rules"
    assert "check" in resp.answers


def test_jev_provider_fallback_on_network_timeout(monkeypatch):
    monkeypatch.setenv("TYPESAFE_API_KEY", "test-key-12345")
    jev = JevProvider(api_key="test-key-12345", timeout=0.5)

    batch = DecisionBatch(
        state="Test network drop",
        questions={"check": Noul(instructions="Test check", threshold=0.5)}
    )

    with patch("urllib.request.urlopen", side_effect=TimeoutError("Network timed out")):
        resp = jev.evaluate(batch)
        # Verify graceful fallback to local rule engine
        assert resp.provider == "local-rules"
        assert "check" in resp.answers


def test_jev_provider_successful_mocked_response(monkeypatch):
    monkeypatch.setenv("TYPESAFE_API_KEY", "test-key-12345")
    jev = JevProvider(api_key="test-key-12345")

    batch = DecisionBatch(
        state="Execution trace verified",
        questions={
            "tool": Choice(instructions="Next tool", criteria={"pytest": "run tests", "git": "commit"}),
            "confidence": Noul(instructions="Execution is sound", threshold=0.7),
        }
    )

    mock_json = {
        "answers": {
            "tool": {"choice": "pytest", "distribution": {"pytest": 0.95, "git": 0.05}, "confidence": 0.95},
            "confidence": {"noul": 0.92, "confidence": 0.92},
        }
    }

    mock_resp = MagicMock()
    mock_resp.read.return_value = json_bytes(mock_json)
    mock_resp.__enter__.return_value = mock_resp

    with patch("urllib.request.urlopen", return_value=mock_resp):
        resp = jev.evaluate(batch)
        assert resp.provider == "jev-systemone"
        assert resp.answers["tool"].choice == "pytest"
        assert resp.answers["confidence"].passed is True
        assert resp.answers["confidence"].probability == 0.92


def test_get_decision_engine_factory(monkeypatch):
    # Forced local
    eng_local = get_decision_engine("local")
    assert isinstance(eng_local, LocalRuleEngine)

    # Forced mock
    eng_mock = get_decision_engine("mock")
    assert isinstance(eng_mock, MockDecisionEngine)

    # Auto without key -> LocalRuleEngine
    monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)
    eng_auto_local = get_decision_engine("auto")
    assert isinstance(eng_auto_local, LocalRuleEngine)

    # Auto with key -> JevProvider
    monkeypatch.setenv("TYPESAFE_API_KEY", "test-key")
    eng_auto_jev = get_decision_engine("auto")
    assert isinstance(eng_auto_jev, JevProvider)


def json_bytes(data: dict) -> bytes:
    import json
    return json.dumps(data).encode("utf-8")
