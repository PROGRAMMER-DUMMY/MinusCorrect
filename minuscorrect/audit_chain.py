"""Tamper-evident Merkle audit chain ledger re-export.

# verifies: tests/unit/test_audit_chain.py
# Rationale: Re-exports MerkleAuditLedger and AuditEntry for the minuscorrect package.
"""

from src.audit_chain import (
    GENESIS_PREV_HASH,
    AuditEntry,
    MerkleAuditLedger,
    canonical_json_hash,
    sha256_hex,
)

__all__ = [
    "AuditEntry",
    "MerkleAuditLedger",
    "GENESIS_PREV_HASH",
    "canonical_json_hash",
    "sha256_hex",
]
