"""
MinusCorrect Operational Notification Egress
Dispatches structured operational failure and success alerts to external webhooks
(Slack, PagerDuty, Datadog) when supervisor events occur.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.request
import urllib.error
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional


@dataclass
class NotificationEvent:
    event_type: str  # RUN_SUCCESS, CIRCUIT_BREAKER_ABORT, TIMEOUT_ABORT, TAMPERING_DETECTED
    session_id: str
    summary: str
    details: Dict[str, Any]
    timestamp: str = ""
    report_path: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()


def format_slack_payload(event: NotificationEvent) -> Dict[str, Any]:
    """
    Formats a NotificationEvent into a rich Slack Incoming Webhook blocks payload.
    """
    status_emoji = ":white_check_mark:" if event.event_type == "RUN_SUCCESS" else ":rotating_light:"
    header_text = f"{status_emoji} MinusCorrect: {event.event_type}"

    fields = [
        {"type": "mrkdwn", "text": f"*Session:*\n`{event.session_id}`"},
        {"type": "mrkdwn", "text": f"*Time:*\n{event.timestamp}"},
    ]

    if "iteration" in event.details:
        fields.append({"type": "mrkdwn", "text": f"*Iteration:*\n{event.details['iteration']}"})
    if "error_hash" in event.details and event.details["error_hash"]:
        fields.append({"type": "mrkdwn", "text": f"*Error Hash:*\n`{event.details['error_hash'][:12]}`"})

    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": header_text[:150], "emoji": True},
        },
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*{event.summary}*"},
        },
        {
            "type": "section",
            "fields": fields,
        },
    ]

    if event.report_path:
        blocks.append(
            {
                "type": "context",
                "elements": [
                    {"type": "mrkdwn", "text": f"Artifact: `{event.report_path}`"}
                ],
            }
        )

    return {
        "text": f"MinusCorrect Alert: {event.event_type} - {event.summary}",
        "blocks": blocks,
    }


def dispatch_notification(
    event: NotificationEvent,
    webhook_url: Optional[str] = None,
    timeout: float = 5.0,
) -> bool:
    """
    Dispatches a notification event to a webhook endpoint.
    Returns True if successfully dispatched (HTTP 2xx), False otherwise.
    # Rationale: Network failures must never crash the core supervisor loop.
    """
    target_url = webhook_url or os.environ.get("MINUSCORRECT_WEBHOOK_URL")
    if not target_url:
        return False

    is_slack = "hooks.slack.com" in target_url or "slack.com/services" in target_url
    if is_slack:
        payload_data = format_slack_payload(event)
    else:
        payload_data = {
            "source": "minuscorrect",
            "event_type": event.event_type,
            "session_id": event.session_id,
            "summary": event.summary,
            "timestamp": event.timestamp,
            "report_path": event.report_path,
            "details": event.details,
        }

    raw_body = json.dumps(payload_data).encode("utf-8")
    req = urllib.request.Request(
        target_url,
        data=raw_body,
        headers={"Content-Type": "application/json", "User-Agent": "MinusCorrect-Supervisor/1.0"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            status_code = response.getcode()
            return 200 <= status_code < 300
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError) as err:
        # Rationale: Gracefully capture network or timeout failures without interrupting core supervision
        sys.stderr.write(f"[WARN] Failed to dispatch MinusCorrect webhook to {target_url}: {err}\n")
        return False
