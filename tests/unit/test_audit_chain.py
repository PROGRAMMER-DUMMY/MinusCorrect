"""Unit tests for the tamper-evident Merkle Audit Chain ledger.

# verifies: src/audit_chain.py
# Rationale: Tests cryptographic Merkle tree and hash-chain ledger for immutable transaction records.
"""

import json
from pathlib import Path
import sys
import pytest

root_dir = str(Path(__file__).resolve().parents[2])
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from src.audit_chain import AuditEntry, MerkleAuditLedger, GENESIS_PREV_HASH, sha256_hex


def test_genesis_and_single_entry():
    ledger = MerkleAuditLedger()
    assert ledger.get_latest_entry() is None
    assert ledger.compute_merkle_root() == GENESIS_PREV_HASH

    entry = ledger.record_transaction(
        entry_id="tx_001",
        event_type="payment.created",
        payload={"amount": 5000, "currency": "usd"},
        timestamp="2026-09-29T11:00:00Z",
    )

    assert entry.index == 0
    assert entry.entry_id == "tx_001"
    assert entry.prev_hash == GENESIS_PREV_HASH
    assert entry.event_type == "payment.created"
    assert len(entry.entry_hash) == 64
    assert ledger.get_latest_entry() == entry
    assert ledger.compute_merkle_root() == entry.entry_hash


def test_sequential_hash_chain():
    ledger = MerkleAuditLedger()
    e0 = ledger.record_transaction("tx_001", "payment.created", {"amount": 100})
    e1 = ledger.record_transaction("tx_002", "payment.captured", {"amount": 100})
    e2 = ledger.record_transaction("tx_003", "payment.refunded", {"amount": 20})

    assert e1.prev_hash == e0.entry_hash
    assert e2.prev_hash == e1.entry_hash
    assert len(ledger.get_entries()) == 3

    ok, err = ledger.verify_chain_integrity()
    assert ok is True
    assert err is None


def test_duplicate_entry_id_rejected():
    ledger = MerkleAuditLedger()
    ledger.record_transaction("tx_duplicate", "charge.succeeded", {"val": 1})
    with pytest.raises(ValueError, match="Duplicate entry_id 'tx_duplicate'"):
        ledger.record_transaction("tx_duplicate", "charge.succeeded", {"val": 2})


def test_merkle_proof_generation_and_verification():
    ledger = MerkleAuditLedger()
    entry_ids = [f"tx_{i:03d}" for i in range(7)]
    for eid in entry_ids:
        ledger.record_transaction(eid, "event", {"id": eid})

    root = ledger.compute_merkle_root()
    assert len(root) == 64

    for idx, eid in enumerate(entry_ids):
        leaf_hash, proof = ledger.generate_merkle_proof(eid)
        assert leaf_hash == ledger.get_entry(eid).entry_hash
        assert MerkleAuditLedger.verify_merkle_proof(leaf_hash, proof, root) is True

        # Tampered leaf hash must fail verification
        tampered_hash = sha256_hex("fraudulent_leaf_data")
        assert MerkleAuditLedger.verify_merkle_proof(tampered_hash, proof, root) is False


def test_tamper_detection_chain_integrity():
    ledger = MerkleAuditLedger()
    ledger.record_transaction("tx_1", "ev", {"val": 1})
    ledger.record_transaction("tx_2", "ev", {"val": 2})
    ledger.record_transaction("tx_3", "ev", {"val": 3})

    ok, err = ledger.verify_chain_integrity()
    assert ok is True

    # Tamper with entry in memory
    tampered_entry = AuditEntry(
        index=1,
        entry_id="tx_2",
        timestamp="2026-09-29T00:00:00Z",
        event_type="ev",
        payload_hash=sha256_hex("modified_payload"),
        prev_hash=ledger.entries[0].entry_hash,
        entry_hash=ledger.entries[1].entry_hash,  # mismatched hash
    )
    ledger.entries[1] = tampered_entry

    ok, err = ledger.verify_chain_integrity()
    assert ok is False
    assert "Tamper detected at index 1" in err


def test_disk_persistence_and_reload(tmp_path: Path):
    ledger_file = tmp_path / "audit_chain.jsonl"
    ledger1 = MerkleAuditLedger(ledger_file=ledger_file)
    ledger1.record_transaction("tx_disk_1", "order.placed", {"items": 3})
    ledger1.record_transaction("tx_disk_2", "order.shipped", {"carrier": "FedEx"})

    root1 = ledger1.compute_merkle_root()

    # Reload into new instance
    ledger2 = MerkleAuditLedger(ledger_file=ledger_file)
    assert len(ledger2.get_entries()) == 2
    assert ledger2.compute_merkle_root() == root1
    ok, err = ledger2.verify_chain_integrity()
    assert ok is True


def test_stripe_webhook_audit_ledger_integration():
    import hmac
    import hashlib
    import time
    from src.stripe_webhook import StripeWebhookHandler

    secret = "whsec_test_secret_key_12345"
    ledger = MerkleAuditLedger()
    handler = StripeWebhookHandler(webhook_secret=secret, audit_ledger=ledger)

    payload_dict = {
        "id": "evt_test_001",
        "type": "payment_intent.succeeded",
        "data": {
            "object": {
                "id": "pi_123",
                "amount": 2000,
                "currency": "usd",
                "card_number": "4242 4242 4242 4242",
            }
        },
    }
    payload_bytes = json.dumps(payload_dict).encode("utf-8")
    now = int(time.time())
    sig = hmac.new(secret.encode("utf-8"), f"{now}.".encode("utf-8") + payload_bytes, hashlib.sha256).hexdigest()
    sig_header = f"t={now},v1={sig}"

    ok, msg, sanitized = handler.process_webhook(payload_bytes, sig_header, current_time=now)
    assert ok is True
    assert msg == "Event processed successfully"

    # Verify ledger recorded transaction
    assert len(ledger.get_entries()) == 1
    entry = ledger.get_entry("evt_test_001")
    assert entry is not None
    assert entry.event_type == "payment_intent.succeeded"
    assert entry.index == 0

    # Ensure PII was redacted before hashing into Merkle ledger
    assert sanitized["data"]["object"]["card_number"] == "[REDACTED]"
    ledger_ok, _ = ledger.verify_chain_integrity()
    assert ledger_ok is True

