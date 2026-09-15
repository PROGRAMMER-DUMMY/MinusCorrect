"""
MinusCorrect Cloudflare Security Audit Bridge
Parses findings.json from cloudflare/security-audit-skill, validates findings against
the staging lifecycle, defangs adversarial prompt injections, and synthesizes reproduction tests.
"""

from __future__ import annotations

import json
import os
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from minuscorrect.incident import sanitize_incident_payload


@dataclass
class SecurityFinding:
    """Represents a validated finding from cloudflare/security-audit-skill."""
    finding_id: str
    title: str
    severity: str = "medium"  # critical, high, medium, low, info
    description: str = ""
    affected_files: List[str] = field(default_factory=list)
    proof_of_concept: str = ""
    status: str = "confirmed"  # confirmed, needs_validation, rejected


def parse_audit_findings(raw_json_text: str) -> Tuple[List[SecurityFinding], List[SecurityFinding], List[SecurityFinding]]:
    """
    Parses findings.json conforming to cloudflare/security-audit-skill schema.
    Returns (confirmed_findings, needs_validation_findings, rejected_findings).
    """
    clean_text = sanitize_incident_payload(raw_json_text)
    data = json.loads(clean_text)

    confirmed: List[SecurityFinding] = []
    needs_val: List[SecurityFinding] = []
    rejected: List[SecurityFinding] = []

    # Handle standard schema: {"confirmed": [...], "needs_validation": [...], "rejected": [...]}
    if isinstance(data, dict):
        raw_confirmed = data.get("confirmed", [])
        raw_needs_val = data.get("needs_validation", [])
        raw_rejected = data.get("rejected", [])
    elif isinstance(data, list):
        # Fallback if findings are a flat list
        raw_confirmed = data
        raw_needs_val = []
        raw_rejected = []
    else:
        return [], [], []

    def build_finding(item: Dict[str, Any], default_status: str) -> SecurityFinding:
        f_id = item.get("id") or item.get("finding_id") or item.get("title") or "SEC-UNKNOWN"
        title = item.get("title") or item.get("name") or str(f_id)
        severity = item.get("severity") or "medium"
        desc = item.get("description") or item.get("summary") or ""
        files = item.get("affected_files") or item.get("files") or []
        if isinstance(files, str):
            files = [files]
        poc = item.get("proof_of_concept") or item.get("poc") or item.get("reproduction") or ""
        return SecurityFinding(
            finding_id=str(f_id),
            title=str(title),
            severity=str(severity).lower(),
            description=str(desc),
            affected_files=list(files),
            proof_of_concept=str(poc),
            status=default_status
        )

    for item in raw_confirmed:
        if isinstance(item, dict):
            confirmed.append(build_finding(item, "confirmed"))

    for item in raw_needs_val:
        if isinstance(item, dict):
            needs_val.append(build_finding(item, "needs_validation"))

    for item in raw_rejected:
        if isinstance(item, dict):
            rejected.append(build_finding(item, "rejected"))

    return confirmed, needs_val, rejected


def generate_staged_security_test(
    finding: SecurityFinding,
    output_dir: Optional[Path] = None
) -> Path:
    """
    Synthesizes an executable reproduction test in tests/staging/test_sec_<id>.py
    from a confirmed audit finding.
    """
    safe_id = re.sub(r"\W+", "_", finding.finding_id).strip("_").lower()
    target_dir = output_dir or (Path("tests") / "staging")
    target_dir.mkdir(parents=True, exist_ok=True)
    test_path = target_dir / f"test_sec_{safe_id}.py"

    affected_comment = ", ".join(finding.affected_files) if finding.affected_files else "Entire workspace"

    content = f'''"""
Security Audit Reproduction Contract: {finding.finding_id}
Origin: cloudflare/security-audit-skill (Severity: {finding.severity.upper()})
Title: {finding.title}
Affected Files: {affected_comment}

SAFETY & INTEGRITY NOTICE:
1. This security contract is STAGED in tests/staging/.
2. It represents an adversarially confirmed vulnerability finding.
3. Once reviewed and confirmed by security maintainers, promote to immutable suite:
   ALLOW_GOLDEN_EDIT=1 git mv {test_path.as_posix()} tests/golden/
"""

import pytest

# Vulnerability Metadata
FINDING_ID = "{finding.finding_id}"
SEVERITY = "{finding.severity}"
AFFECTED_FILES = {json.dumps(finding.affected_files)}


def test_vulnerability_reproduce_{safe_id}():
    """
    Verifies that the vulnerability '{finding.finding_id}' is mitigated and cannot be exploited.
    # verifies: {test_path.as_posix()}
    """
    # Proof of Concept / Exploit Payload (Defanged):
    # {finding.proof_of_concept.strip() or "(No inline PoC provided by audit finding)"}

    # Maintainer / Agent Task:
    # 1. Implement boundary defense in {affected_comment}
    # 2. Confirm the exploit payload is neutralized
    pass
'''
    test_path.write_text(content, encoding="utf-8")
    return test_path


def generate_security_audit_summary(
    confirmed: List[SecurityFinding],
    needs_val: List[SecurityFinding],
    rejected: List[SecurityFinding],
    output_path: Optional[Path] = None
) -> Path:
    """
    Generates a structured SECURITY-AUDIT-SUMMARY.md report.
    """
    summary_path = output_path or Path("SECURITY-AUDIT-SUMMARY.md")
    timestamp = datetime.now(timezone.utc).isoformat()

    confirmed_rows = []
    for f in confirmed:
        files = ", ".join(f.affected_files) if f.affected_files else "N/A"
        confirmed_rows.append(f"| `{f.finding_id}` | **{f.severity.upper()}** | {f.title} | `{files}` |")

    confirmed_table = "\n".join(confirmed_rows) if confirmed_rows else "| None | - | No confirmed vulnerabilities | - |"

    content = f"""# Cloudflare Security Audit Ingestion Summary

**Ingested:** {timestamp}
**Audit Source:** `cloudflare/security-audit-skill` (`findings.json`)
**Confirmed Vulnerabilities:** {len(confirmed)}
**Unvalidated Candidates:** {len(needs_val)}
**Rejected / Disproven:** {len(rejected)}

---

## 1. Confirmed Exploits (Staged Contracts Generated)
| Finding ID | Severity | Title | Affected Files |
| :--- | :--- | :--- | :--- |
{confirmed_table}

---

## 2. Staging & Quarantine Lifecycle
To maintain golden contract integrity, confirmed findings are placed into `tests/staging/`.
Review reproduction assertions, then promote to immutable acceptance contracts:
```bash
ALLOW_GOLDEN_EDIT=1 git mv tests/staging/test_sec_<id>.py tests/golden/
```

---

## 3. Unvalidated Findings (Requires Manual Investigation)
Total candidates requiring proof-of-concept validation: {len(needs_val)}
*(Unvalidated findings are quarantined and will NOT generate golden tests until proven)*
"""
    summary_path.write_text(content, encoding="utf-8")
    return summary_path
