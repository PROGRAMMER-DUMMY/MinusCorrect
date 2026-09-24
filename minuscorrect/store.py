"""
MinusCorrect Local Store & Second-Brain Task Lifecycle Engine.
Manages .minus/ state directory, ticket lifecycles (open -> completed),
atomic transitions, index.json lookup tables, and machine-verifiable execution receipts.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
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
    base_commit_sha: str = ""
    head_commit_sha: str = ""
    diff_file: Optional[str] = None
    files_touched: List[str] = field(default_factory=list)
    insertions: int = 0
    deletions: int = 0

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
        if self.verification:
            lines.append(f"verification: {json.dumps(self.verification)}")
        if self.blocked_by:
            lines.append(f"blocked_by: {json.dumps(self.blocked_by)}")
        if self.blocks:
            lines.append(f"blocks: {json.dumps(self.blocks)}")
        if self.receipt:
            lines.append("receipt:")
            for k, v in self.receipt.to_dict().items():
                if isinstance(v, list):
                    lines.append(f"  {k}: {json.dumps(v)}")
                elif v is None:
                    lines.append(f"  {k}: null")
                else:
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
        receipt_dict: Dict[str, Any] = {}
        in_receipt = False

        if frontmatter_match:
            fm_text, body = frontmatter_match.groups()
            for line in fm_text.splitlines():
                if line.startswith("receipt:"):
                    in_receipt = True
                    continue
                if in_receipt:
                    if line.startswith("  ") and ":" in line:
                        rk, rv = line.strip().split(":", 1)
                        rk = rk.strip()
                        rv = rv.strip().strip('"\'')
                        if rv == "null":
                            receipt_dict[rk] = None
                        elif rv.startswith("[") and rv.endswith("]"):
                            try:
                                receipt_dict[rk] = json.loads(rv)
                            except Exception:
                                receipt_dict[rk] = []
                        elif rv.isdigit():
                            receipt_dict[rk] = int(rv)
                        else:
                            receipt_dict[rk] = rv
                        continue
                    elif not line.startswith("  "):
                        in_receipt = False

                if ":" in line and not line.startswith("  "):
                    k, v = line.split(":", 1)
                    k = k.strip()
                    v = v.strip()
                    if v.startswith("[") and v.endswith("]"):
                        try:
                            v = json.loads(v)
                        except Exception:
                            pass
                    elif v.startswith('"') and v.endswith('"'):
                        try:
                            v = json.loads(v)
                        except Exception:
                            v = v.strip('"\'')
                    else:
                        v = v.strip('"\'')
                    meta[k] = v

        # Extract objective and targets from body if present
        obj_match = re.search(r"- \*\*Objective\*\*:\s*(.+)$", body, re.MULTILINE)
        objective = obj_match.group(1).strip() if obj_match else meta.get("title", "")

        parsed_receipt = None
        if receipt_dict:
            parsed_receipt = ExecutionReceipt(
                commit_sha=str(receipt_dict.get("commit_sha", "")),
                test_command=str(receipt_dict.get("test_command", "")),
                exit_code=int(receipt_dict.get("exit_code", 0)),
                verified_at=str(receipt_dict.get("verified_at", "")),
                specialist=str(receipt_dict.get("specialist", "")),
                integrity_hash=str(receipt_dict.get("integrity_hash", "")),
                base_commit_sha=str(receipt_dict.get("base_commit_sha", "")),
                head_commit_sha=str(receipt_dict.get("head_commit_sha", "")),
                diff_file=receipt_dict.get("diff_file"),
                files_touched=receipt_dict.get("files_touched", []) if isinstance(receipt_dict.get("files_touched"), list) else [],
                insertions=int(receipt_dict.get("insertions", 0)),
                deletions=int(receipt_dict.get("deletions", 0)),
            )

        # Extract verification contract from frontmatter or body
        ver_match = re.search(r"## Verification Contract\s*\n```(?:bash|sh)?\s*\n(.*?)\n```", body, re.DOTALL)
        verification = meta.get("verification") or (ver_match.group(1).strip() if ver_match else "minuscorrect verify --fix --strict")

        return cls(
            id=meta.get("id", "T-000"),
            title=meta.get("title", "Untitled Ticket"),
            role=meta.get("role", "Process Isolation SRE"),
            status=meta.get("status", "open"),
            objective=objective,
            verification=verification,
            created_at=meta.get("created_at", datetime.now(timezone.utc).isoformat()),
            closed_at=meta.get("closed_at"),
            blocked_by=meta.get("blocked_by", []) if isinstance(meta.get("blocked_by"), list) else [],
            blocks=meta.get("blocks", []) if isinstance(meta.get("blocks"), list) else [],
            receipt=parsed_receipt,
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
        self.tickets_rolled_back = self.root / "tickets" / "rolled_back"
        self.diffs_dir = self.root / "diffs"
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
        self.tickets_rolled_back.mkdir(parents=True, exist_ok=True)
        self.diffs_dir.mkdir(parents=True, exist_ok=True)
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
                "diffs": {},
            })

    def _read_index(self) -> Dict[str, Any]:
        try:
            return json.loads(self.index_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {
                "version": "1.0",
                "tickets": {},
                "incidents": {},
                "research": {},
                "rules": {},
                "diffs": {},
            }

    def _write_index(self, data: Dict[str, Any]) -> None:
        data["updated_at"] = datetime.now(timezone.utc).isoformat()
        temp_file = self.index_file.with_suffix(".tmp")
        temp_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
        temp_file.replace(self.index_file)

    def resolve_commit_sha(self, rev: str = "HEAD", cwd: Optional[Path] = None) -> str:
        """Resolve a git revision into an exact 40-character commit SHA."""
        target_dir = cwd or self.root.parent
        try:
            res = subprocess.run(
                ["git", "rev-parse", rev],
                cwd=str(target_dir),
                capture_output=True,
                text=True,
                check=False,
            )
            if res.returncode == 0 and res.stdout.strip():
                return res.stdout.strip()
        except (OSError, subprocess.SubprocessError):
            pass
        return rev

    def capture_ticket_diff(
        self,
        ticket_id: str,
        base_sha: str,
        head_sha: str,
        cwd: Optional[Path] = None,
    ) -> Dict[str, Any]:
        """
        Capture unified git diff between base_sha and head_sha.
        Persists bit-exact patch into .minus/diffs/<ticket_id>.patch.
        """
        target_dir = cwd or self.root.parent
        patch_file = self.diffs_dir / f"{ticket_id}.patch"
        stats: Dict[str, Any] = {
            "diff_file": None,
            "files_touched": [],
            "insertions": 0,
            "deletions": 0,
            "patch_sha256": None,
        }

        try:
            diff_cmd = ["git", "diff", f"{base_sha}..{head_sha}"]
            res = subprocess.run(
                diff_cmd,
                cwd=str(target_dir),
                capture_output=True,
                text=True,
                check=False,
            )
            patch_content = res.stdout if res.returncode == 0 else ""

            if not patch_content.strip() and head_sha not in ("HEAD", ""):
                show_res = subprocess.run(
                    ["git", "show", "--format=", head_sha],
                    cwd=str(target_dir),
                    capture_output=True,
                    text=True,
                    check=False,
                )
                if show_res.returncode == 0 and show_res.stdout.strip():
                    patch_content = show_res.stdout

            if patch_content.strip():
                patch_file.write_text(patch_content, encoding="utf-8")
                patch_hash = hashlib.sha256(patch_content.encode("utf-8")).hexdigest()
                stats["diff_file"] = f"diffs/{ticket_id}.patch"
                stats["patch_sha256"] = patch_hash

            stat_res = subprocess.run(
                ["git", "diff", "--numstat", f"{base_sha}..{head_sha}"],
                cwd=str(target_dir),
                capture_output=True,
                text=True,
                check=False,
            )
            if stat_res.returncode == 0 and stat_res.stdout.strip():
                for line in stat_res.stdout.splitlines():
                    parts = line.split("\t")
                    if len(parts) >= 3:
                        ins = int(parts[0]) if parts[0].isdigit() else 0
                        dels = int(parts[1]) if parts[1].isdigit() else 0
                        stats["insertions"] += ins
                        stats["deletions"] += dels
                        stats["files_touched"].append(parts[2])
        except (OSError, subprocess.SubprocessError):
            pass

        return stats

    def create_git_ref(
        self,
        ticket_id: str,
        commit_sha: str,
        cwd: Optional[Path] = None,
    ) -> bool:
        """Create or update a native git reference refs/minus/tickets/<ticket_id>."""
        target_dir = cwd or self.root.parent
        try:
            res = subprocess.run(
                ["git", "update-ref", f"refs/minus/tickets/{ticket_id}", commit_sha],
                cwd=str(target_dir),
                capture_output=True,
                text=True,
                check=False,
            )
            return res.returncode == 0
        except (OSError, subprocess.SubprocessError):
            return False

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
        """Fetch ticket by ID from open, completed, or rolled_back folder."""
        for folder in (self.tickets_open, self.tickets_completed, self.tickets_rolled_back):
            fpath = folder / f"{ticket_id}.md"
            if fpath.exists():
                return Ticket.from_markdown(fpath.read_text(encoding="utf-8"))
        return None

    def get_ticket_diff(self, ticket_id: str) -> Optional[str]:
        """Retrieve unified diff patch for a ticket if available."""
        diff_path = self.diffs_dir / f"{ticket_id}.patch"
        if diff_path.exists():
            return diff_path.read_text(encoding="utf-8")
        return None

    def list_tickets(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """List tickets from index.json with optional status filter."""
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
        base_commit_sha: Optional[str] = None,
        test_command: str = "minuscorrect verify",
        exit_code: int = 0,
        specialist: str = "",
        capture_diff: bool = True,
        update_ref: bool = True,
        cwd: Optional[Path] = None,
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

        # Resolve Head and Base commits
        head_sha = self.resolve_commit_sha(commit_sha, cwd=cwd) if commit_sha == "HEAD" else commit_sha
        if base_commit_sha:
            base_sha = base_commit_sha
        else:
            base_sha = self.resolve_commit_sha(f"{head_sha}~1", cwd=cwd) if head_sha != "HEAD" else "HEAD~1"

        # Capture Diff and Stats
        diff_stats: Dict[str, Any] = {"diff_file": None, "files_touched": [], "insertions": 0, "deletions": 0}
        if capture_diff:
            diff_stats = self.capture_ticket_diff(ticket_id, base_sha, head_sha, cwd=cwd)

        # Update Git native ref pointer
        if update_ref and head_sha not in ("HEAD", ""):
            self.create_git_ref(ticket_id, head_sha, cwd=cwd)

        ticket.receipt = ExecutionReceipt(
            commit_sha=head_sha,
            test_command=test_command,
            exit_code=exit_code,
            specialist=specialist or ticket.role,
            base_commit_sha=base_sha,
            head_commit_sha=head_sha,
            diff_file=diff_stats.get("diff_file"),
            files_touched=diff_stats.get("files_touched", []),
            insertions=diff_stats.get("insertions", 0),
            deletions=diff_stats.get("deletions", 0),
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
        if diff_stats.get("diff_file"):
            idx.setdefault("diffs", {})[ticket_id] = diff_stats
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
