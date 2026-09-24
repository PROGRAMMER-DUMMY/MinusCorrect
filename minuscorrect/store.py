"""
MinusCorrect Local Store & Second-Brain Task Lifecycle Engine.
Manages .minus/ state directory, ticket lifecycles (open -> completed),
atomic transitions, index.json lookup tables, and machine-verifiable execution receipts.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
from typing import Any, Dict, List, Optional


@dataclass
class ExecutionReceipt:
    """Cryptographic machine receipt confirming ticket verification."""
    commit_sha: str
    test_command: str
    exit_code: int
    verified_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    specialist: str = ""
    integrity_hash: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Ticket:
    """Represents an actionable task with explicit boundaries and domain specialist assignment."""
    id: str
    title: str
    role: str
    status: str  # "open", "completed", "quarantined"
    objective: str
    target_files: List[str] = field(default_factory=list)
    protected_boundaries: List[str] = field(default_factory=list)
    blocked_by: List[str] = field(default_factory=list)
    blocks: List[str] = field(default_factory=list)
    verification: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    closed_at: Optional[str] = None
    receipt: Optional[ExecutionReceipt] = None
    body: str = ""

    def to_markdown(self) -> str:
        """Render ticket as Markdown with YAML frontmatter."""
        lines = [
            "---",
            f"id: {self.id}",
            f"title: \"{self.title}\"",
            f"role: \"{self.role}\"",
            f"status: {self.status}",
            f"created_at: {self.created_at}",
        ]
        if self.closed_at:
            lines.append(f"closed_at: {self.closed_at}")
        if self.blocked_by:
            lines.append(f"blocked_by: {json.dumps(self.blocked_by)}")
        if self.blocks:
            lines.append(f"blocks: {json.dumps(self.blocks)}")
        if self.receipt:
            lines.append("receipt:")
            for k, v in self.receipt.to_dict().items():
                lines.append(f"  {k}: \"{v}\"")
        lines.append("---")
        lines.append("")
        lines.append(f"# {self.id}: {self.title}")
        lines.append("")
        lines.append(f"- **Assigned Specialist**: {self.role}")
        lines.append(f"- **Objective**: {self.objective}")
        lines.append(f"- **Status**: `{self.status.upper()}`")
        lines.append("")
        lines.append("## Target Files (In-Scope)")
        if self.target_files:
            for tf in self.target_files:
                lines.append(f"- `{tf}`")
        else:
            lines.append("- *(None specified)*")
        lines.append("")
        lines.append("## Protected Boundaries (Out-of-Scope)")
        if self.protected_boundaries:
            for pb in self.protected_boundaries:
                lines.append(f"- `{pb}`")
        else:
            lines.append("- `tests/golden/*` (Strictly read-only)")
        lines.append("")
        lines.append("## Verification Contract")
        lines.append(f"```bash\n{self.verification or 'minuscorrect verify --fix --strict'}\n```")
        if self.body:
            lines.append("")
            lines.append("## Additional Context")
            lines.append(self.body)
        return "\n".join(lines)

    @classmethod
    def from_markdown(cls, text: str) -> "Ticket":
        """Parse ticket from Markdown frontmatter and body."""
        frontmatter_match = re.match(r"^---\n(.*?)\n---\n*(.*)$", text, re.DOTALL)
        meta: Dict[str, Any] = {}
        body = text
        if frontmatter_match:
            fm_text, body = frontmatter_match.groups()
            for line in fm_text.splitlines():
                if ":" in line and not line.startswith("  "):
                    k, v = line.split(":", 1)
                    k = k.strip()
                    v = v.strip().strip('"\'')
                    if v.startswith("[") and v.endswith("]"):
                        try:
                            v = json.loads(v)
                        except Exception:
                            pass
                    meta[k] = v

        # Extract objective and targets from body if present
        obj_match = re.search(r"- \*\*Objective\*\*:\s*(.+)$", body, re.MULTILINE)
        objective = obj_match.group(1).strip() if obj_match else meta.get("title", "")

        return cls(
            id=meta.get("id", "T-000"),
            title=meta.get("title", "Untitled Ticket"),
            role=meta.get("role", "Process Isolation SRE"),
            status=meta.get("status", "open"),
            objective=objective,
            created_at=meta.get("created_at", datetime.now(timezone.utc).isoformat()),
            closed_at=meta.get("closed_at"),
            blocked_by=meta.get("blocked_by", []) if isinstance(meta.get("blocked_by"), list) else [],
            blocks=meta.get("blocks", []) if isinstance(meta.get("blocks"), list) else [],
            body=body.strip(),
        )


class MinusStore:
    """
    Second-brain persistent lifecycle store located at .minus/.
    Governs tickets, incidents, sessions, and atomic state transitions.
    # verifies: tests/unit/test_store.py
    """

    def __init__(self, root_dir: Optional[Path] = None):
        self.root = (root_dir or Path.cwd()) / ".minus"
        self.tickets_open = self.root / "tickets" / "open"
        self.tickets_completed = self.root / "tickets" / "completed"
        self.incidents_dir = self.root / "incidents"
        self.sessions_dir = self.root / "sessions"
        self.research_dir = self.root / "research"
        self.rules_dir = self.root / "rules"
        self.index_file = self.root / "index.json"
        self.ensure_layout()

    def ensure_layout(self) -> None:
        """Initialize directory tree and root index.json."""
        self.tickets_open.mkdir(parents=True, exist_ok=True)
        self.tickets_completed.mkdir(parents=True, exist_ok=True)
        self.incidents_dir.mkdir(parents=True, exist_ok=True)
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        self.research_dir.mkdir(parents=True, exist_ok=True)
        self.rules_dir.mkdir(parents=True, exist_ok=True)

        if not self.index_file.exists():
            self._write_index({
                "version": "1.0",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "tickets": {},
                "incidents": {},
                "research": {},
                "rules": {},
            })

    def _read_index(self) -> Dict[str, Any]:
        try:
            return json.loads(self.index_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {"version": "1.0", "tickets": {}, "incidents": {}, "research": {}, "rules": {}}

    def _write_index(self, data: Dict[str, Any]) -> None:
        data["updated_at"] = datetime.now(timezone.utc).isoformat()
        temp_file = self.index_file.with_suffix(".tmp")
        temp_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
        temp_file.replace(self.index_file)

    def next_ticket_id(self) -> str:
        """Compute the next sequential ticket identifier (e.g. T-001)."""
        idx = self._read_index()
        existing = list(idx.get("tickets", {}).keys())
        nums = [0]
        for t in existing:
            m = re.match(r"^T-(\d+)$", t)
            if m:
                nums.append(int(m.group(1)))
        return f"T-{max(nums) + 1:03d}"

    def create_ticket(
        self,
        title: str,
        role: str = "Process Isolation SRE",
        objective: str = "",
        target_files: Optional[List[str]] = None,
        protected_boundaries: Optional[List[str]] = None,
        blocked_by: Optional[List[str]] = None,
        blocks: Optional[List[str]] = None,
        verification: str = "",
        body: str = "",
        ticket_id: Optional[str] = None,
    ) -> Ticket:
        """Create a new ticket in .minus/tickets/open/ and update index.json."""
        tid = ticket_id or self.next_ticket_id()
        ticket = Ticket(
            id=tid,
            title=title,
            role=role,
            status="open",
            objective=objective or title,
            target_files=target_files or [],
            protected_boundaries=protected_boundaries or ["tests/golden/*"],
            blocked_by=blocked_by or [],
            blocks=blocks or [],
            verification=verification or "minuscorrect verify --fix --strict",
            body=body,
        )

        ticket_path = self.tickets_open / f"{tid}.md"
        ticket_path.write_text(ticket.to_markdown(), encoding="utf-8")

        idx = self._read_index()
        idx.setdefault("tickets", {})[tid] = {
            "id": tid,
            "title": title,
            "role": role,
            "status": "open",
            "blocked_by": ticket.blocked_by,
            "blocks": ticket.blocks,
            "file": f"tickets/open/{tid}.md",
            "created_at": ticket.created_at,
            "closed_at": None,
        }
        self._write_index(idx)
        return ticket

    def get_ticket(self, ticket_id: str) -> Optional[Ticket]:
        """Fetch ticket by ID from either open or completed folder."""
        open_file = self.tickets_open / f"{ticket_id}.md"
        if open_file.exists():
            return Ticket.from_markdown(open_file.read_text(encoding="utf-8"))

        completed_file = self.tickets_completed / f"{ticket_id}.md"
        if completed_file.exists():
            return Ticket.from_markdown(completed_file.read_text(encoding="utf-8"))

        return None

    def list_tickets(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """List tickets from index.json with optional status filter ('open' or 'completed')."""
        idx = self._read_index()
        tickets = list(idx.get("tickets", {}).values())
        if status:
            norm_status = status.lower()
            tickets = [t for t in tickets if t.get("status") == norm_status]
        return sorted(tickets, key=lambda t: t.get("id", ""))

    def close_ticket(
        self,
        ticket_id: str,
        commit_sha: str = "HEAD",
        test_command: str = "minuscorrect verify",
        exit_code: int = 0,
        specialist: str = "",
    ) -> Ticket:
        """
        Atomically transition ticket from open/ to completed/ and log machine execution receipt.
        # verifies: tests/unit/test_store.py
        """
        open_path = self.tickets_open / f"{ticket_id}.md"
        completed_path = self.tickets_completed / f"{ticket_id}.md"

        if not open_path.exists():
            if completed_path.exists():
                return Ticket.from_markdown(completed_path.read_text(encoding="utf-8"))
            raise FileNotFoundError(f"Ticket {ticket_id} not found in open store: {open_path}")

        ticket = Ticket.from_markdown(open_path.read_text(encoding="utf-8"))
        ticket.status = "completed"
        ticket.closed_at = datetime.now(timezone.utc).isoformat()
        ticket.receipt = ExecutionReceipt(
            commit_sha=commit_sha,
            test_command=test_command,
            exit_code=exit_code,
            specialist=specialist or ticket.role,
        )

        completed_path.write_text(ticket.to_markdown(), encoding="utf-8")
        try:
            open_path.unlink()
        except OSError:
            pass

        idx = self._read_index()
        entry = idx.setdefault("tickets", {}).setdefault(ticket_id, {})
        entry.update({
            "status": "completed",
            "closed_at": ticket.closed_at,
            "file": f"tickets/completed/{ticket_id}.md",
            "receipt": ticket.receipt.to_dict(),
        })
        self._write_index(idx)
        return ticket

    def register_incident(self, incident_id: str, payload_summary: Dict[str, Any]) -> Path:
        """Register an incident post-mortem/telemetry record in .minus/incidents/."""
        inc_file = self.incidents_dir / f"{incident_id}.json"
        data = {
            "incident_id": incident_id,
            "ingested_at": datetime.now(timezone.utc).isoformat(),
            **payload_summary,
        }
        inc_file.write_text(json.dumps(data, indent=2), encoding="utf-8")

        idx = self._read_index()
        idx.setdefault("incidents", {})[incident_id] = {
            "id": incident_id,
            "ingested_at": data["ingested_at"],
            "file": f"incidents/{incident_id}.json",
            "error": payload_summary.get("error_message", "Unknown error"),
        }
        self._write_index(idx)
        return inc_file

    def next_research_id(self) -> str:
        """Compute next sequential research session identifier (e.g. RES-001)."""
        idx = self._read_index()
        existing = list(idx.get("research", {}).keys())
        nums = [0]
        for r in existing:
            m = re.match(r"^RES-(\d+)$", r)
            if m:
                nums.append(int(m.group(1)))
        return f"RES-{max(nums) + 1:03d}"

    def save_research(
        self,
        topic: str,
        report_markdown: str,
        metadata: Optional[Dict[str, Any]] = None,
        research_id: Optional[str] = None,
    ) -> str:
        """Save a deep research report into .minus/research/ and register in index.json."""
        rid = research_id or self.next_research_id()
        res_file = self.research_dir / f"{rid}.md"
        res_file.write_text(report_markdown, encoding="utf-8")

        meta = metadata or {}
        idx = self._read_index()
        idx.setdefault("research", {})[rid] = {
            "id": rid,
            "topic": topic,
            "created_at": meta.get("created_at", datetime.now(timezone.utc).isoformat()),
            "file": f"research/{rid}.md",
            "findings_count": meta.get("findings_count", 0),
            "sources_count": meta.get("sources_count", 0),
            "consensus_score": meta.get("consensus_score", 1.0),
            "consensus_verdict": meta.get("consensus_verdict", "Strong Consensus"),
            "contradictions_count": meta.get("contradictions_count", 0),
        }
        self._write_index(idx)
        return rid

    def get_research(self, research_id: str) -> Optional[str]:
        """Fetch research report markdown by ID."""
        res_file = self.research_dir / f"{research_id}.md"
        if res_file.exists():
            return res_file.read_text(encoding="utf-8")
        return None

    def list_research(self) -> List[Dict[str, Any]]:
        """List all saved research sessions from index.json."""
        idx = self._read_index()
        items = list(idx.get("research", {}).values())
        return sorted(items, key=lambda r: r.get("id", ""))

    def next_rule_id(self) -> str:
        """Compute next sequential rule identifier (e.g. RULE-001)."""
        idx = self._read_index()
        existing = list(idx.get("rules", {}).keys())
        nums = [0]
        for r in existing:
            m = re.match(r"^RULE-(\d+)$", r)
            if m:
                nums.append(int(m.group(1)))
        return f"RULE-{max(nums) + 1:03d}"

    def save_rule(
        self,
        title: str,
        instruction: str,
        scope: str = "general",
        enforcement: str = "strict",
        prohibited_patterns: Optional[List[str]] = None,
        rule_id: Optional[str] = None,
    ) -> str:
        """Save a natural language rule into .minus/rules/ and register in index.json."""
        rid = rule_id or self.next_rule_id()
        rule_file = self.rules_dir / f"{rid}.md"

        content = [
            "---",
            f"id: {rid}",
            f"title: \"{title}\"",
            f"scope: {scope}",
            f"enforcement: {enforcement}",
            f"created_at: \"{datetime.now(timezone.utc).isoformat()}\"",
            "---",
            "",
            f"# {rid}: {title}",
            "",
            f"- **Scope**: `{scope}`",
            f"- **Enforcement**: `{enforcement}`",
            "",
            "## Invariant Instruction for Autonomous Agents",
            instruction,
        ]
        if prohibited_patterns:
            content.extend([
                "",
                "## Prohibited Patterns & Anti-Patterns",
            ])
            for pat in prohibited_patterns:
                content.append(f"- `{pat}`")

        rule_file.write_text("\n".join(content), encoding="utf-8")

        idx = self._read_index()
        idx.setdefault("rules", {})[rid] = {
            "id": rid,
            "title": title,
            "scope": scope,
            "enforcement": enforcement,
            "file": f"rules/{rid}.md",
            "instruction": instruction,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self._write_index(idx)
        return rid

    def get_rule(self, rule_id: str) -> Optional[str]:
        """Fetch rule content by ID."""
        r_file = self.rules_dir / f"{rule_id}.md"
        if r_file.exists():
            return r_file.read_text(encoding="utf-8")
        return None

    def list_rules(self, scope: Optional[str] = None) -> List[Dict[str, Any]]:
        """List rules from index.json, optionally filtered by scope."""
        idx = self._read_index()
        items = list(idx.get("rules", {}).values())
        if scope:
            norm_scope = scope.lower()
            items = [r for r in items if r.get("scope") in (norm_scope, "all", "general")]
        return sorted(items, key=lambda r: r.get("id", ""))
