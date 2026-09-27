"""Acceptance contract tests for Stripe webhook listener.

# verifies: tests/staging/test_stripe_webhook.py
# Rationale: Verifies signature authentication, idempotency deduplication, and zero PII logging.
"""

import hashlib
import hmac
import json
from pathlib import Path
import sys
import time

# Ensure root workspace is on sys.path
root_dir = str(Path(__file__).resolve().parents[2])
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from src.stripe_webhook import (
    StripeWebhookHandler,
    sanitize_payment_data,
    verify_stripe_signature,
)


def make_signature_header(payload: bytes, secret: str, timestamp: int) -> str:
    """Helper to generate valid Stripe-Signature header."""
    signed_payload = f"{timestamp}.".encode("utf-8") + payload
    sig = hmac.new(secret.encode("utf-8"), signed_payload, hashlib.sha256).hexdigest()
    return f"t={timestamp},v1={sig}"


def test_signature_verification_success() -> None:
    secret = "whsec_test_secret_12345678901234567890"
    payload = json.dumps({"id": "evt_001", "type": "payment_intent.succeeded"}).encode("utf-8")
    now = int(time.time())
    sig_header = make_signature_header(payload, secret, now)

    assert verify_stripe_signature(payload, sig_header, secret, current_time=now) is True


def test_signature_verification_invalid_signature() -> None:
    secret = "whsec_test_secret_12345678901234567890"
    payload = json.dumps({"id": "evt_001"}).encode("utf-8")
    now = int(time.time())
    bad_header = f"t={now},v1=bad_signature_hash"

    assert verify_stripe_signature(payload, bad_header, secret, current_time=now) is False


def test_signature_verification_replay_attack_tolerance() -> None:
    secret = "whsec_test_secret_12345678901234567890"
    payload = json.dumps({"id": "evt_001"}).encode("utf-8")
    old_time = 100000
    now = 101000  # 1000 seconds later, exceeds tolerance of 300
    sig_header = make_signature_header(payload, secret, old_time)

    assert verify_stripe_signature(payload, sig_header, secret, tolerance=300, current_time=now) is False


def test_webhook_idempotency_duplicate_events() -> None:
    secret = "whsec_test_secret_12345678901234567890"
    handler = StripeWebhookHandler(webhook_secret=secret)

    now = int(time.time())
    event_data = {"id": "evt_unique_123", "type": "charge.captured", "amount": 5000}
    payload = json.dumps(event_data).encode("utf-8")
    sig_header = make_signature_header(payload, secret, now)

    # First attempt: processed successfully
    ok1, msg1, data1 = handler.process_webhook(payload, sig_header, current_time=now)
    assert ok1 is True
    assert "successfully" in msg1
    assert data1.get("duplicate") is not True

    # Second attempt with identical event ID: idempotently ignored
    ok2, msg2, data2 = handler.process_webhook(payload, sig_header, current_time=now)
    assert ok2 is True
    assert "Duplicate" in msg2
    assert data2.get("duplicate") is True


def test_zero_pii_and_card_redaction() -> None:
    sensitive_payload = {
        "id": "evt_card_test",
        "customer": "cus_123",
        "card_number": "4242 4242 4242 4242",
        "cvc": "123",
        "secret_token": "token_dummy_secret_value_12345",
        "metadata": {
            "notes": "Payment using card 5555-5555-5555-5555 and token Bearer abc.def.ghi",
        },
    }

    sanitized = sanitize_payment_data(sensitive_payload)

    assert sanitized["card_number"] == "[REDACTED]"
    assert sanitized["cvc"] == "[REDACTED]"
    assert sanitized["secret_token"] == "[REDACTED]"
    assert "4242" not in str(sanitized)
    assert "5555" not in str(sanitized)
    assert "[REDACTED_CARD]" in sanitized["metadata"]["notes"]
    assert "[REDACTED_SECRET]" in sanitized["metadata"]["notes"]
