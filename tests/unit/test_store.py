"""
Unit tests for MinusCorrect Second-Brain Store (minuscorrect/store.py).
"""

from pathlib import Path
import pytest
from minuscorrect.store import ExecutionReceipt, MinusStore, Ticket


def test_minus_store_initialization(tmp_path: Path) -> None:
    store = MinusStore(root_dir=tmp_path)
    assert store.root.exists()
    assert store.tickets_open.exists()
    assert store.tickets_completed.exists()
    assert store.incidents_dir.exists()
    assert store.sessions_dir.exists()
    assert store.index_file.exists()

    idx = store._read_index()
    assert idx.get("version") == "1.0"
    assert "tickets" in idx


def test_create_and_get_ticket(tmp_path: Path) -> None:
    store = MinusStore(root_dir=tmp_path)
    ticket = store.create_ticket(
        title="Enforce RLS tenant policies",
        role="Security & Policy Auditor",
        objective="Ensure all queries join tenant_id",
        target_files=["schema.sql"],
        protected_boundaries=["tests/golden/*"],
        verification="pytest tests/unit/",
    )

    assert ticket.id == "T-001"
    assert ticket.status == "open"
    assert (store.tickets_open / "T-001.md").exists()

    fetched = store.get_ticket("T-001")
    assert fetched is not None
    assert fetched.title == "Enforce RLS tenant policies"
    assert fetched.role == "Security & Policy Auditor"


def test_list_tickets_with_filter(tmp_path: Path) -> None:
    store = MinusStore(root_dir=tmp_path)
    store.create_ticket("Ticket One", role="Process Isolation SRE")
    store.create_ticket("Ticket Two", role="Distributed Systems Engineer")

    all_tickets = store.list_tickets()
    assert len(all_tickets) == 2

    open_tickets = store.list_tickets(status="open")
    assert len(open_tickets) == 2

    completed_tickets = store.list_tickets(status="completed")
    assert len(completed_tickets) == 0


def test_close_ticket_and_receipt(tmp_path: Path) -> None:
    store = MinusStore(root_dir=tmp_path)
    t = store.create_ticket("Ticket to close", role="TDD & Verification Lead")

    closed = store.close_ticket(
        ticket_id=t.id,
        commit_sha="a1b2c3d4",
        test_command="pytest",
        exit_code=0,
        specialist="TDD Lead",
    )

    assert closed.status == "completed"
    assert closed.closed_at is not None
    assert closed.receipt is not None
    assert closed.receipt.commit_sha == "a1b2c3d4"

    # Verify atomic file move
    assert not (store.tickets_open / f"{t.id}.md").exists()
    assert (store.tickets_completed / f"{t.id}.md").exists()

    # Verify index updated
    idx = store._read_index()
    entry = idx["tickets"][t.id]
    assert entry["status"] == "completed"
    assert entry["receipt"]["commit_sha"] == "a1b2c3d4"


def test_register_incident(tmp_path: Path) -> None:
    store = MinusStore(root_dir=tmp_path)
    inc_file = store.register_incident("INC-101", {
        "error_message": "Connection pool exhausted",
        "service": "database",
    })

    assert inc_file.exists()
    idx = store._read_index()
    assert "INC-101" in idx["incidents"]
    assert idx["incidents"]["INC-101"]["error"] == "Connection pool exhausted"
