"""
Unit tests for MinusCorrect Operational Notification Egress
"""

import os
from unittest.mock import MagicMock, patch
import urllib.error
import pytest

from minuscorrect.notify import NotificationEvent, dispatch_notification, format_slack_payload
from minuscorrect.supervisor import AgentSupervisor


def test_notification_event_defaults():
    event = NotificationEvent(
        event_type="CIRCUIT_BREAKER_ABORT",
        session_id="session-123",
        summary="Test summary",
        details={"iteration": 4, "error_hash": "abc1234"},
        report_path="DIAGNOSTIC-REPORT.md",
    )
    assert event.event_type == "CIRCUIT_BREAKER_ABORT"
    assert event.session_id == "session-123"
    assert event.summary == "Test summary"
    assert event.details["iteration"] == 4
    assert event.timestamp != ""
    assert event.report_path == "DIAGNOSTIC-REPORT.md"


def test_format_slack_payload():
    event = NotificationEvent(
        event_type="RUN_SUCCESS",
        session_id="session-success",
        summary="Test passed successfully",
        details={"iteration": 2, "exit_code": 0},
    )
    payload = format_slack_payload(event)
    assert "blocks" in payload
    assert "MinusCorrect" in payload["text"]
    assert any("session-success" in str(block) for block in payload["blocks"])


def test_dispatch_notification_no_url():
    event = NotificationEvent(
        event_type="RUN_SUCCESS",
        session_id="session-none",
        summary="No URL test",
        details={},
    )
    with patch.dict(os.environ, {}, clear=True):
        assert not dispatch_notification(event, webhook_url=None)


def test_dispatch_notification_generic_webhook_success():
    event = NotificationEvent(
        event_type="CIRCUIT_BREAKER_ABORT",
        session_id="session-fail",
        summary="Aborted test",
        details={"iteration": 4},
    )
    mock_response = MagicMock()
    mock_response.getcode.return_value = 200
    mock_response.__enter__.return_value = mock_response

    with patch("urllib.request.urlopen", return_value=mock_response) as mock_urlopen:
        success = dispatch_notification(event, webhook_url="https://alerts.example.com/webhook")
        assert success
        assert mock_urlopen.called
        req = mock_urlopen.call_args[0][0]
        assert req.full_url == "https://alerts.example.com/webhook"
        assert req.method == "POST"


def test_dispatch_notification_slack_webhook():
    event = NotificationEvent(
        event_type="RUN_SUCCESS",
        session_id="session-slack",
        summary="Passed test",
        details={},
    )
    mock_response = MagicMock()
    mock_response.getcode.return_value = 200
    mock_response.__enter__.return_value = mock_response

    with patch("urllib.request.urlopen", return_value=mock_response) as mock_urlopen:
        success = dispatch_notification(event, webhook_url="https://hooks.slack.com/services/T00/B00/X00")
        assert success
        assert mock_urlopen.called


def test_dispatch_notification_network_error_graceful_failure():
    event = NotificationEvent(
        event_type="TIMEOUT_ABORT",
        session_id="session-err",
        summary="Timed out",
        details={},
    )
    with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("Connection refused")):
        # Must return False and not crash
        assert not dispatch_notification(event, webhook_url="https://broken.endpoint.local")


def test_supervisor_dispatches_notification_on_success(tmp_path):
    mock_response = MagicMock()
    mock_response.getcode.return_value = 200
    mock_response.__enter__.return_value = mock_response

    supervisor = AgentSupervisor(
        session_id="test_notify_success",
        webhook_url="https://notify.example.com/mc",
        cwd=tmp_path
    )

    with patch("urllib.request.urlopen", return_value=mock_response) as mock_urlopen, \
         patch("minuscorrect.verifier.check_golden_tests", return_value=(True, "OK")), \
         patch("minuscorrect.verifier.check_debug_tags", return_value=(True, [])):

        result = supervisor.run_step(test_cmd=["python", "-c", "import sys; sys.exit(0)"])
        assert result["status"] == "SUCCESS"
        assert mock_urlopen.called
        event_payload = mock_urlopen.call_args[0][0].data.decode("utf-8")
        assert "RUN_SUCCESS" in event_payload
