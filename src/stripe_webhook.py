"""Stripe Webhook Listener with Zero PII Logging and Idempotency Guard.

# verifies: tests/staging/test_stripe_webhook.py
# Rationale: Implements secure Stripe webhook processing with idempotency and zero PII logging.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import re
import time
from typing import Any, Dict, Optional, Set, Tuple


# Regex for card numbers (13-19 digits, with optional dashes or spaces)
CARD_PATTERN = re.compile(r"\b(?:\d[ -]*?){13,19}\b")
SECRET_KEY_PATTERN = re.compile(r"(sk_live_[0-9a-zA-Z]{24,}|whsec_[0-9a-zA-Z]{24,}|Bearer\s+[A-Za-z0-9\-_\.]+)")


def sanitize_payment_data(data: Any) -> Any:
    """Recursively redacts credit card numbers and secret tokens from payloads.
    # verifies: tests/staging/test_stripe_webhook.py
    """
    if isinstance(data, dict):
        sanitized = {}
        for k, v in data.items():
            lower_k = k.lower()
            if any(sensitive in lower_k for sensitive in ("card", "cvc", "cvv", "secret", "token", "password")):
                sanitized[k] = "[REDACTED]"
            else:
                sanitized[k] = sanitize_payment_data(v)
        return sanitized
    elif isinstance(data, list):
        return [sanitize_payment_data(item) for item in data]
    elif isinstance(data, str):
        masked = CARD_PATTERN.sub("[REDACTED_CARD]", data)
        masked = SECRET_KEY_PATTERN.sub("[REDACTED_SECRET]", masked)
        return masked
    return data


def verify_stripe_signature(
    payload: bytes,
    sig_header: str,
    webhook_secret: str,
    tolerance: int = 300,
    current_time: Optional[int] = None,
) -> bool:
    """Verifies Stripe webhook HMAC-SHA256 signature against replay attacks.
    # verifies: tests/staging/test_stripe_webhook.py
    """
    if not sig_header or not webhook_secret:
        return False

    elements = {}
    for item in sig_header.split(","):
        parts = item.strip().split("=", 1)
        if len(parts) == 2:
            elements[parts[0]] = parts[1]

    timestamp_str = elements.get("t")
    signature = elements.get("v1")
    if not timestamp_str or not signature:
        return False

    try:
        timestamp = int(timestamp_str)
    except ValueError:
        return False

    now = current_time if current_time is not None else int(time.time())
    if abs(now - timestamp) > tolerance:
        return False  # Replay attack protection

    signed_payload = f"{timestamp}.".encode("utf-8") + payload
    expected = hmac.new(
        webhook_secret.encode("utf-8"),
        signed_payload,
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(signature, expected)


class StripeWebhookHandler:
    """Processes Stripe payment webhook events with idempotency, zero-leak logging, and Merkle audit trails.
    # verifies: tests/staging/test_stripe_webhook.py
    """

    def __init__(self, webhook_secret: str, audit_ledger: Optional[Any] = None):
        self.webhook_secret = webhook_secret
        self.processed_event_ids: Set[str] = set()
        self.audit_ledger = audit_ledger

    def process_webhook(
        self,
        payload: bytes,
        sig_header: str,
        current_time: Optional[int] = None,
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """Validates signature, guards against duplicate event IDs, and returns sanitized event.
        # verifies: tests/staging/test_stripe_webhook.py
        """
        valid = verify_stripe_signature(
            payload=payload,
            sig_header=sig_header,
            webhook_secret=self.webhook_secret,
            current_time=current_time,
        )
        if not valid:
            return False, "Invalid signature or expired timestamp", {}

        try:
            raw_event = json.loads(payload.decode("utf-8"))
        except Exception:
            return False, "Invalid JSON payload", {}

        event_id = raw_event.get("id")
        if not event_id:
            return False, "Missing event ID", {}

        # Idempotency check
        if event_id in self.processed_event_ids:
            return True, "Duplicate event ignored (idempotent)", {"event_id": event_id, "duplicate": True}

        self.processed_event_ids.add(event_id)
        sanitized = sanitize_payment_data(raw_event)

        if self.audit_ledger is not None:
            self.audit_ledger.record_transaction(
                entry_id=event_id,
                event_type=raw_event.get("type", "stripe.webhook"),
                payload=sanitized,
            )

        return True, "Event processed successfully", sanitized
