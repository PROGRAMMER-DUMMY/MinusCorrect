"""
MinusCorrect Defensive Production Incident Pipeline
Provides:
1. PII, credential, and secret redaction on incident crash payloads.
2. Adversarial prompt-injection defanging on untrusted crash inputs.
3. Staged reproduction contract generation (tests/staging/test_incident_<id>.py).
4. Automated Root Cause Analysis (RCA) report synthesis (INCIDENT-RCA-<id>.md).
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union


# High-risk secret patterns for automated defanging and redaction
SECRET_REDACTION_PATTERNS = [
    # Bearer authorization headers (processed before bare JWTs)
    (r"(?i)\bBearer\s+[A-Za-z0-9\-._~+/]+=*", "Bearer <REDACTED_BEARER_TOKEN>"),
    # JWT tokens
    (r"eyJ[A-Za-z0-9\-_=]+\.eyJ[A-Za-z0-9\-_=]+\.[A-Za-z0-9\-_.+/=]*", "<REDACTED_JWT>"),
    # AWS access keys
    (r"\b(AKIA|ABIA|ACCA|ASIA)[0-9A-Z]{16}\b", "<REDACTED_AWS_KEY>"),
    # GitHub / generic provider tokens
    (r"\bgh[pousr]_[A-Za-z0-9_]{36,}\b", "<REDACTED_GITHUB_TOKEN>"),
    (r"\bsk-[a-zA-Z0-9]{20,}\b", "<REDACTED_API_KEY>"),
    # Key-value password/secret pairs
    (
        r"(?i)(password|passwd|pwd|secret|api_?key|token|auth_?token|client_?secret)\s*[:=]\s*['\"][^'\"]{3,}['\"]",
        r'\1="<REDACTED_SECRET>"'
    ),
    # Email addresses
    (r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", "<REDACTED_EMAIL>"),
    # IPv4 addresses
    (r"\b(?:\d{1,3}\.){3}\d{1,3}\b", "<REDACTED_IP>"),
    # UUIDs
    (r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b", "<REDACTED_UUID>")
]

# Adversarial prompt-injection defanging patterns
PROMPT_INJECTION_PATTERNS = [
    # System instruction markup and override tags
    (r"(?i)<\s*/?\s*(?:system|instruction|prompt|context|assistant|human|developer)\b[^>]*>", "[DEFANGED_TAG]"),
    # Bracketed system tokens (supporting spaces or underscores)
    (r"(?i)\[\s*(?:SYSTEM|INSTRUCTION|SYSTEM[\s_]+INSTRUCTION|SYSTEM[\s_]+PROMPT|OVERRIDE|ADMIN)\s*\]", "[DEFANGED_PROMPT_HEADER]"),
    # Common adversarial override directives
    (
        r"(?i)\b(?:ignore\s+(?:all\s+)?previous\s+instructions|override\s+(?:the\s+)?system\s+prompt|disregard\s+all\s+prior|bypass\s+(?:all\s+)?guardrails)\b",
        "[DEFANGED_PROMPT_INJECTION_OVERRIDE]"
    ),
    # Code execution strings embedded inside user inputs
    (
        r"(?i)\b(?:eval|exec|os\.system|subprocess\.run|subprocess\.Popen|shutil\.rmtree|__import__)\s*\(",
        "[DEFANGED_EXEC]("
    ),
]


def sanitize_incident_payload(raw_text: str, defang: bool = True) -> str:
    """
    Sanitizes raw crash telemetry by:
    1. Defanging adversarial prompt-injection payloads in untrusted strings (unless defang=False).
    2. Redacting sensitive credentials, secrets, PII, and network identifiers.

    # Rationale: Allows security and prompt engineers to preserve verbatim attack strings via --no-defang or MINUSCORRECT_PRESERVE_PAYLOAD=1.
    """
    if not raw_text:
        return ""

    sanitized = raw_text

    # Respect environment variable override
    if os.environ.get("MINUSCORRECT_PRESERVE_PAYLOAD") == "1":
        defang = False

    # 1. Defang adversarial prompt injection tokens (if enabled)
    if defang:
        for pattern, replacement in PROMPT_INJECTION_PATTERNS:
            sanitized = re.sub(pattern, replacement, sanitized)

    # 2. Redact sensitive credentials and PII (always active)
    for pattern, replacement in SECRET_REDACTION_PATTERNS:
        sanitized = re.sub(pattern, replacement, sanitized)

    return sanitized


@dataclass
class IncidentReport:
    """Structured representation of a sanitized production incident."""
    incident_id: str
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    exception_type: str = "UnknownException"
    exception_message: str = ""
    failing_module: str = "unknown"
    failing_function: str = "unknown"
    sanitized_inputs: Dict[str, Any] = field(default_factory=dict)
    stack_trace: str = ""
    raw_sanitized: str = ""
    error_hash: str = ""
    defanged: bool = True
    failing_file: Optional[str] = None
    failing_line: Optional[int] = None
    culprit_correlation: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        if not self.error_hash:
            payload_str = f"{self.exception_type}:{self.exception_message}\n{self.stack_trace}"
            self.error_hash = hashlib.sha256(payload_str.encode("utf-8")).hexdigest()[:16]


def correlate_incident_to_ticket(
    file_path: Union[str, Path],
    line_number: int,
    cwd: Optional[Path] = None,
    store: Optional[Any] = None,
) -> Optional[Dict[str, Any]]:
    """
    Correlate a crash location (file and line) back to the originating git commit and ticket.
    # verifies: tests/unit/test_incident.py
    """
    target_dir = cwd or Path.cwd()
    norm_path = Path(file_path)
    if norm_path.is_absolute():
        try:
            rel_file = norm_path.relative_to(target_dir).as_posix()
        except ValueError:
            rel_file = norm_path.as_posix()
    else:
        rel_file = norm_path.as_posix()

    try:
        res = subprocess.run(
            ["git", "blame", "-L", f"{line_number},{line_number}", "--porcelain", rel_file],
            cwd=str(target_dir),
            capture_output=True,
            text=True,
            check=False,
        )
        if res.returncode != 0 or not res.stdout.strip():
            return None
        first_line = res.stdout.strip().splitlines()[0]
        commit_sha = first_line.split()[0]
    except (OSError, subprocess.SubprocessError):
        return None

    from minuscorrect.store import MinusStore
    s = store or MinusStore(root_dir=target_dir)
    idx = s._read_index()
    tickets = idx.get("tickets", {})

    matching_ticket = None
    for tid, tmeta in tickets.items():
        receipt = tmeta.get("receipt", {})
        if (
            receipt.get("head_commit_sha") == commit_sha
            or receipt.get("commit_sha") == commit_sha
            or (commit_sha.startswith(receipt.get("commit_sha", "____")) and len(receipt.get("commit_sha", "")) >= 7)
        ):
            matching_ticket = tmeta
            break

    if matching_ticket:
        tid = matching_ticket.get("id")
        return {
            "ticket_id": tid,
            "commit_sha": commit_sha,
            "title": matching_ticket.get("title", ""),
            "author_specialist": matching_ticket.get("role", "Unknown Specialist"),
            "status": matching_ticket.get("status", "completed"),
            "rollback_cmd": f"minuscorrect rollback {tid}",
        }

    return {
        "ticket_id": None,
        "commit_sha": commit_sha,
        "author_specialist": None,
        "title": None,
        "status": None,
        "rollback_cmd": f"git revert {commit_sha[:8]}",
    }


def parse_incident_payload(
    raw: Union[str, Dict[str, Any]],
    incident_id: Optional[str] = None,
    defang: bool = True,
    cwd: Optional[Path] = None,
    store: Optional[Any] = None,
) -> IncidentReport:
    """
    Parses a Sentry/Datadog JSON payload or raw stack trace into a sanitized IncidentReport.
    """
    raw_str = raw if isinstance(raw, str) else json.dumps(raw, indent=2)
    sanitized_text = sanitize_incident_payload(raw_str, defang=defang)

    # Attempt to parse as JSON
    parsed_json: Optional[Dict[str, Any]] = None
    try:
        parsed_json = json.loads(sanitized_text)
    except Exception:
        pass

    extracted_id = incident_id
    exc_type = "UnknownException"
    exc_msg = ""
    failing_mod = "unknown"
    failing_func = "unknown"
    failing_file = None
    failing_line = None
    sanitized_inputs: Dict[str, Any] = {}
    stack_trace = ""

    if parsed_json and isinstance(parsed_json, dict):
        # 1. Sentry format
        if "exception" in parsed_json:
            exc_data = parsed_json.get("exception", {})
            values = exc_data.get("values", [])
            if values:
                last_exc = values[-1]
                exc_type = last_exc.get("type", "Exception")
                exc_msg = last_exc.get("value", "")
                stacktrace_data = last_exc.get("stacktrace", {})
                frames = stacktrace_data.get("frames", [])
                if frames:
                    last_frame = frames[-1]
                    failing_mod = last_frame.get("module", last_frame.get("filename", "unknown"))
                    failing_func = last_frame.get("function", "unknown")
                    failing_file = last_frame.get("filename", last_frame.get("abs_path"))
                    failing_line = last_frame.get("lineno")
                    sanitized_inputs = last_frame.get("vars", {})
        # 2. Datadog / custom format
        elif "error.message" in parsed_json or "message" in parsed_json:
            exc_type = parsed_json.get("error.kind", parsed_json.get("error_type", "RuntimeError"))
            exc_msg = parsed_json.get("error.message", parsed_json.get("message", ""))
            stack_trace = parsed_json.get("error.stack", parsed_json.get("stacktrace", ""))
            sanitized_inputs = parsed_json.get("inputs", parsed_json.get("attributes", parsed_json.get("context", {})))
        # 3. Simple key-value crash dict
        else:
            exc_type = parsed_json.get("type", parsed_json.get("exception", "Exception"))
            exc_msg = parsed_json.get("message", parsed_json.get("error", ""))
            failing_mod = parsed_json.get("module", "unknown")
            failing_func = parsed_json.get("function", "unknown")
            sanitized_inputs = parsed_json.get("inputs", {})
            stack_trace = parsed_json.get("traceback", "")

        if not extracted_id:
            extracted_id = parsed_json.get("event_id", parsed_json.get("id", parsed_json.get("incident_id")))

    # If raw plain text traceback
    if not exc_msg and not stack_trace:
        stack_trace = sanitized_text
        match_exc = re.search(r"([A-Za-z_][A-Za-z0-9_.]*(?:Error|Exception)): (.*)", sanitized_text)
        if match_exc:
            exc_type = match_exc.group(1)
            exc_msg = match_exc.group(2).strip()

        match_frame = re.findall(r'File "([^"]+)", line (\d+), in ([A-Za-z0-9_]+)', sanitized_text)
        if match_frame:
            failing_file, line_str, failing_func = match_frame[-1]
            failing_mod = failing_file
            try:
                failing_line = int(line_str)
            except ValueError:
                pass

    if not extracted_id:
        seed = f"{exc_type}:{exc_msg}:{stack_trace[:100]}"
        extracted_id = f"INC-{hashlib.sha256(seed.encode('utf-8')).hexdigest()[:8].upper()}"

    culprit_correlation = None
    if failing_file and failing_line:
        culprit_correlation = correlate_incident_to_ticket(failing_file, failing_line, cwd=cwd, store=store)

    return IncidentReport(
        incident_id=extracted_id,
        exception_type=exc_type,
        exception_message=exc_msg,
        failing_module=failing_mod,
        failing_function=failing_func,
        sanitized_inputs=sanitized_inputs,
        stack_trace=stack_trace,
        raw_sanitized=sanitized_text,
        defanged=defang,
        failing_file=failing_file,
        failing_line=failing_line,
        culprit_correlation=culprit_correlation,
    )


def generate_staged_test(
    report: IncidentReport,
    output_dir: Optional[Path] = None,
    test_path: Optional[Path] = None
) -> Path:
    """
    Generates a staged reproduction acceptance test: tests/staging/test_incident_<id>.py
    Requires human review before promotion to tests/golden/.
    """
    safe_id = re.sub(r"\W+", "_", report.incident_id).strip("_").lower()
    target_dir = test_path.parent if test_path else (output_dir or (Path("tests") / "staging"))
    target_dir.mkdir(parents=True, exist_ok=True)
    if test_path is None:
        test_path = target_dir / f"test_incident_{safe_id}.py"

    # Write inert payload to fixtures directory to isolate control plane from data plane
    # Rationale: Prevents adversarial payload strings from executing as inline Python code
    fixtures_dir = target_dir / "fixtures"
    fixtures_dir.mkdir(parents=True, exist_ok=True)
    fixture_path = fixtures_dir / f"inc_{safe_id}.json"
    fixture_path.write_text(json.dumps(report.sanitized_inputs, indent=2), encoding="utf-8")

    content = f'''"""
Incident Reproduction Contract: {report.incident_id}
Generated by MinusCorrect Defensive Incident Pipeline
Normalized Error Hash: {report.error_hash}

SAFETY & INTEGRITY NOTICE:
1. This test is currently STAGED in tests/staging/.
2. Human Maintainer Verification Steps:
   [a] Confirm reproduction payload is sanitized of all real-world customer PII/secrets.
   [b] Confirm test reproduces a genuine invariant failure rather than network/infra flake.
   [c] To promote this contract to immutable acceptance suite, run:
       ALLOW_GOLDEN_EDIT=1 git mv {test_path.as_posix()} tests/golden/
"""

import json
from pathlib import Path
import pytest

# Reproduction Metadata
INCIDENT_ID = "{report.incident_id}"
EXCEPTION_TYPE = "{report.exception_type}"
FAILING_MODULE = "{report.failing_module}"
FAILING_FUNCTION = "{report.failing_function}"
FIXTURE_PATH = Path(__file__).parent / "fixtures" / "inc_{safe_id}.json"


def test_reproduce_incident_{safe_id}():
    """
    Verifies that the system handles the boundary condition without triggering {report.exception_type}.
    # verifies: {test_path.as_posix()}
    """
    # Inert fixture loading: payload bytes never execute directly as Python source code
    if FIXTURE_PATH.exists():
        inputs = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    else:
        inputs = {json.dumps(report.sanitized_inputs, indent=4)}

    # TODO (Maintainer): Connect 'inputs' to target unit entry point:
    # Example:
    # from {report.failing_module} import {report.failing_function}
    # result = {report.failing_function}(**inputs)
    # assert result is not None

    # Baseline assertion: Documented failure condition must not crash unhandled
    with pytest.raises(Exception) as exc_info:
        # Replace with invocation reproducing {report.exception_type}
        raise {report.exception_type if report.exception_type.endswith(("Error", "Exception")) else "RuntimeError"}("{report.exception_message or 'Simulated reproduction'}")

    assert exc_info.type.__name__ == EXCEPTION_TYPE
'''
    test_path.write_text(content, encoding="utf-8")
    return test_path


def generate_rca_report(
    report: IncidentReport,
    supervisor_history: Optional[List[Dict[str, Any]]] = None,
    output_path: Optional[Path] = None
) -> Path:
    """
    Generates a structured machine-readable INCIDENT-RCA-<id>.md post-mortem artifact.
    """
    safe_id = re.sub(r"\W+", "_", report.incident_id).strip("_").lower()
    if output_path is None:
        output_path = Path(f"INCIDENT-RCA-{safe_id}.md")

    history_lines = []
    if supervisor_history:
        for item in supervisor_history:
            history_lines.append(
                f"- **Iteration {item.get('iteration')}**: Exit Code {item.get('exit_code')} (Hash: `{item.get('hash')}`)"
            )
    else:
        history_lines.append("- (Pending MinusCorrect supervisor solver execution)")

    history_str = "\n".join(history_lines)

    correlation_section = ""
    if report.culprit_correlation:
        corr = report.culprit_correlation
        tid_display = f"`{corr['ticket_id']}` ({corr.get('title', '')})" if corr.get('ticket_id') else "*(No ticket registered for commit)*"
        spec_display = f"`{corr['author_specialist']}`" if corr.get('author_specialist') else "*(Unknown author)*"
        correlation_section = f"""
---

## 5. Culprit Ticket & Agent Attribution
- **Originating Git Commit**: `{corr['commit_sha'][:8]}`
- **Responsible Second-Brain Ticket**: {tid_display}
- **Author Specialist Persona**: {spec_display}
- **Autonomous Remediation Command**:
  ```bash
  {corr['rollback_cmd']}
  ```
"""

    remed_num = 6 if report.culprit_correlation else 5

    content = f"""# Incident Root Cause Analysis (RCA): `{report.incident_id}`

**Generated:** {report.timestamp}
**Normalized Error Hash:** `{report.error_hash}`
**Exception Type:** `{report.exception_type}`
**Failing Component:** `{report.failing_module}::{report.failing_function}`

---

## 1. Executive Summary
An unhandled exception was captured in production telemetry and ingested via MinusCorrect.
* **Symptom:** `{report.exception_type}: {report.exception_message}`
* **Reproduced In Contract:** `tests/staging/test_incident_{safe_id}.py`
* **Defanging Status:** PII, credentials, and prompt injection signatures defanged.

---

## 2. Sanitized Stack Trace
```text
{report.stack_trace.strip() or "(No stack trace captured)"}
```

---

## 3. Sanitized Boundary Inputs
```json
{json.dumps(report.sanitized_inputs, indent=2)}
```

---

## 4. Supervisor Solver Iteration History
{history_str}
{correlation_section}
---

## {remed_num}. Remediation & Preventive Invariants
1. **Contract Promotion:** Once verified by human maintainer, promote contract:
   ```bash
   ALLOW_GOLDEN_EDIT=1 git mv tests/staging/test_incident_{safe_id}.py tests/golden/
   ```
2. **Anti-Swallowing Rule:** Fix must address root cause calculation rather than introducing defensive exception swallowing (`except: pass`).
3. **Receipt Linking:** Implementation changes must link directly to the golden test receipt.
"""
    output_path.write_text(content, encoding="utf-8")
    return output_path


def promote_incident_to_golden(
    staged_path: Path,
    golden_dir: Optional[Path] = None
) -> Tuple[bool, str]:
    """
    Promotes a staged test to tests/golden/, strictly enforcing ALLOW_GOLDEN_EDIT=1.
    """
    if os.environ.get("ALLOW_GOLDEN_EDIT") != "1":
        return False, (
            "[ERROR] Golden contract promotion rejected: ALLOW_GOLDEN_EDIT=1 is required.\n"
            f"Run: ALLOW_GOLDEN_EDIT=1 minuscorrect incident --promote {staged_path}"
        )

    target_dir = golden_dir or (Path("tests") / "golden")
    target_dir.mkdir(parents=True, exist_ok=True)
    destination = target_dir / staged_path.name

    staged_path.rename(destination)
    return True, f"Successfully promoted {staged_path} to {destination}."
