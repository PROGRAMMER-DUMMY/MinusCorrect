"""Tamper-Evident Merkle Audit Chain Ledger for Secure Transaction Auditing.

# verifies: tests/unit/test_audit_chain.py
# Rationale: Implements cryptographic Merkle tree and hash-chain ledger for immutable transaction records.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

GENESIS_PREV_HASH = "0" * 64


def sha256_hex(data: Union[str, bytes]) -> str:
    """Computes SHA-256 hexadecimal digest of input text or bytes.
    # verifies: tests/unit/test_audit_chain.py
    """
    if isinstance(data, str):
        data = data.encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def canonical_json_hash(payload: Any) -> str:
    """Computes SHA-256 digest of deterministic, sorted JSON representation.
    # verifies: tests/unit/test_audit_chain.py
    """
    if isinstance(payload, bytes):
        return sha256_hex(payload)
    if isinstance(payload, str):
        try:
            parsed = json.loads(payload)
            serialized = json.dumps(parsed, sort_keys=True, separators=(",", ":"))
        except (ValueError, TypeError):
            serialized = payload
    else:
        serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return sha256_hex(serialized)


@dataclass(frozen=True)
class AuditEntry:
    """Immutable audit entry in the Merkle chain.
    # verifies: tests/unit/test_audit_chain.py
    """

    index: int
    entry_id: str
    timestamp: str
    event_type: str
    payload_hash: str
    prev_hash: str
    entry_hash: str

    def to_dict(self) -> Dict[str, Any]:
        """Converts audit entry to a JSON-serializable dictionary."""
        return asdict(self)


class MerkleAuditLedger:
    """Tamper-evident append-only ledger backed by cryptographic hash chains and Merkle trees.

    # verifies: tests/unit/test_audit_chain.py
    # Rationale: Guarantees transaction history non-repudiation and detects data tampering.
    """

    def __init__(self, ledger_file: Optional[Union[str, Path]] = None) -> None:
        self.entries: List[AuditEntry] = []
        self._entry_id_map: Dict[str, AuditEntry] = {}
        self.ledger_file: Optional[Path] = Path(ledger_file) if ledger_file else None
        if self.ledger_file and self.ledger_file.exists():
            self._load_from_disk()

    def _compute_entry_hash(
        self, index: int, entry_id: str, timestamp: str, event_type: str, payload_hash: str, prev_hash: str
    ) -> str:
        content = f"{index}:{entry_id}:{timestamp}:{event_type}:{payload_hash}:{prev_hash}"
        return sha256_hex(content)

    def record_transaction(
        self,
        entry_id: str,
        event_type: str,
        payload: Any,
        timestamp: Optional[str] = None,
    ) -> AuditEntry:
        """Records a new transaction into the cryptographic hash chain.
        # verifies: tests/unit/test_audit_chain.py
        """
        if entry_id in self._entry_id_map:
            raise ValueError(f"Duplicate entry_id '{entry_id}' rejected by audit ledger.")

        index = len(self.entries)
        prev_hash = self.entries[-1].entry_hash if self.entries else GENESIS_PREV_HASH
        ts = timestamp or datetime.now(timezone.utc).isoformat()
        p_hash = canonical_json_hash(payload)
        e_hash = self._compute_entry_hash(index, entry_id, ts, event_type, p_hash, prev_hash)

        entry = AuditEntry(
            index=index,
            entry_id=entry_id,
            timestamp=ts,
            event_type=event_type,
            payload_hash=p_hash,
            prev_hash=prev_hash,
            entry_hash=e_hash,
        )

        self.entries.append(entry)
        self._entry_id_map[entry_id] = entry

        if self.ledger_file:
            self._append_to_disk(entry)

        return entry

    def get_entry(self, entry_id: str) -> Optional[AuditEntry]:
        """Retrieves an audit entry by its unique identifier."""
        return self._entry_id_map.get(entry_id)

    def get_entry_by_index(self, index: int) -> Optional[AuditEntry]:
        """Retrieves an audit entry by sequence index."""
        if 0 <= index < len(self.entries):
            return self.entries[index]
        return None

    def get_entries(self) -> List[AuditEntry]:
        """Returns all entries in the audit ledger."""
        return list(self.entries)

    def get_latest_entry(self) -> Optional[AuditEntry]:
        """Returns the most recent entry in the ledger, or None if empty."""
        return self.entries[-1] if self.entries else None

    def compute_merkle_root(self) -> str:
        """Computes the root SHA-256 hash of the Merkle tree over all entries.
        # verifies: tests/unit/test_audit_chain.py
        """
        if not self.entries:
            return GENESIS_PREV_HASH

        current_level = [e.entry_hash for e in self.entries]

        while len(current_level) > 1:
            next_level: List[str] = []
            for i in range(0, len(current_level), 2):
                left = current_level[i]
                right = current_level[i + 1] if i + 1 < len(current_level) else left
                combined = sha256_hex(left + right)
                next_level.append(combined)
            current_level = next_level

        return current_level[0]

    def generate_merkle_proof(self, target: Union[int, str]) -> Tuple[str, List[Tuple[str, str]]]:
        """Generates a Merkle audit proof path for an entry specified by index or ID.
        Returns (leaf_hash, proof_path) where proof_path is a list of (direction, sibling_hash).
        # verifies: tests/unit/test_audit_chain.py
        """
        if isinstance(target, str):
            entry = self._entry_id_map.get(target)
            if not entry:
                raise ValueError(f"Entry ID '{target}' not found in ledger.")
            target_idx = entry.index
        else:
            target_idx = target
            if not (0 <= target_idx < len(self.entries)):
                raise IndexError(f"Index {target_idx} out of range (0-{len(self.entries) - 1}).")

        leaf_hash = self.entries[target_idx].entry_hash
        proof: List[Tuple[str, str]] = []
        current_level = [e.entry_hash for e in self.entries]
        idx = target_idx

        while len(current_level) > 1:
            next_level: List[str] = []
            is_odd_length = len(current_level) % 2 != 0

            for i in range(0, len(current_level), 2):
                left = current_level[i]
                right = current_level[i + 1] if i + 1 < len(current_level) else left
                next_level.append(sha256_hex(left + right))

            if idx % 2 == 0:
                # Target is left child, sibling is right
                sibling = current_level[idx + 1] if idx + 1 < len(current_level) else current_level[idx]
                proof.append(("right", sibling))
            else:
                # Target is right child, sibling is left
                sibling = current_level[idx - 1]
                proof.append(("left", sibling))

            idx = idx // 2
            current_level = next_level

        return leaf_hash, proof

    @staticmethod
    def verify_merkle_proof(leaf_hash: str, proof: List[Tuple[str, str]], expected_root: str) -> bool:
        """Verifies a Merkle proof against a known expected root.
        # verifies: tests/unit/test_audit_chain.py
        """
        current = leaf_hash
        for direction, sibling in proof:
            if direction == "right":
                current = sha256_hex(current + sibling)
            elif direction == "left":
                current = sha256_hex(sibling + current)
            else:
                return False
        return current == expected_root

    def verify_chain_integrity(self) -> Tuple[bool, Optional[str]]:
        """Validates the entire ledger for cryptographic integrity and detects any tampering.
        # verifies: tests/unit/test_audit_chain.py
        """
        for i, entry in enumerate(self.entries):
            if entry.index != i:
                return False, f"Sequence error: entry index {entry.index} does not match expected {i}."

            expected_prev = GENESIS_PREV_HASH if i == 0 else self.entries[i - 1].entry_hash
            if entry.prev_hash != expected_prev:
                return False, f"Broken link at index {i}: prev_hash does not match preceding entry_hash."

            recomputed_hash = self._compute_entry_hash(
                entry.index,
                entry.entry_id,
                entry.timestamp,
                entry.event_type,
                entry.payload_hash,
                entry.prev_hash,
            )
            if entry.entry_hash != recomputed_hash:
                return False, f"Tamper detected at index {i}: recorded hash does not match computed digest."

        return True, None

    def export_ledger(self, file_path: Union[str, Path]) -> None:
        """Exports the full ledger to a JSONL file."""
        target = Path(file_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        with open(target, "w", encoding="utf-8") as f:
            for entry in self.entries:
                f.write(json.dumps(entry.to_dict()) + "\n")

    def _append_to_disk(self, entry: AuditEntry) -> None:
        if not self.ledger_file:
            return
        self.ledger_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.ledger_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry.to_dict()) + "\n")

    def _load_from_disk(self) -> None:
        if not self.ledger_file or not self.ledger_file.exists():
            return
        with open(self.ledger_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                data = json.loads(line)
                entry = AuditEntry(**data)
                self.entries.append(entry)
                self._entry_id_map[entry.entry_id] = entry
