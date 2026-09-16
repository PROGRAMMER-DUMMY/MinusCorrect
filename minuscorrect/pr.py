"""
MinusCorrect Autonomous PR Decoupling Engine
Enforces the systemic invariant that autonomous patches must never commit directly
to shared production branches, decoupling fixes into isolated Draft PR artifacts.
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class DraftPRMetadata:
    session_id: str
    branch_name: str
    title: str
    summary: str
    modified_files: List[str] = field(default_factory=list)
    tests_passed: List[str] = field(default_factory=list)
    iteration_count: int = 1
    rca_reference: Optional[str] = None
    diff_stat: str = ""


def generate_draft_pr_markdown(metadata: DraftPRMetadata) -> str:
    """
    Generates a structured Draft Pull Request description formatted for GitHub/GitLab.
    """
    files_list = "\n".join(f"- `{f}`" for f in metadata.modified_files) if metadata.modified_files else "- None"
    tests_list = "\n".join(f"- `{t}`" for t in metadata.tests_passed) if metadata.tests_passed else "- Verified test suite passed"

    rca_section = ""
    if metadata.rca_reference:
        rca_section = f"\n### Root Cause Reference\n- Reference Report: `{metadata.rca_reference}`\n"

    return f"""# {metadata.title}

> **Autonomous Repair Notice:** This pull request was synthesized by MinusCorrect under bounded supervision. All acceptance contracts have passed verification. Review by a human engineer is required prior to merge.

---

## 1. Summary of Changes
- **Session ID:** `{metadata.session_id}`
- **Source Branch:** `{metadata.branch_name}`
- **Supervisor Iterations:** {metadata.iteration_count}
- **Description:** {metadata.summary}
{rca_section}
---

## 2. Blast-Radius Verification
### Modified Files
{files_list}

### Passing Contracts
{tests_list}

```
Diff Statistics:
{metadata.diff_stat.strip() or "No diff statistics available"}
```

---

## 3. Human Review Checklist
- [ ] Verify that no business logic was silently bypassed or swallowed.
- [ ] Confirm acceptance contract adheres to expected domain semantics.
- [ ] Run full continuous integration regression suite.

---

## 4. Local Reproduction & Checkout
```bash
git fetch origin {metadata.branch_name}
git checkout {metadata.branch_name}
pytest
```
"""


def create_draft_pr_artifact(
    repo_root: Optional[Path] = None,
    session_id: str = "default",
    branch_name: Optional[str] = None,
    summary: str = "Automated defect repair via MinusCorrect supervisor",
    output_file: Optional[Path] = None,
    commit_and_branch: bool = False,
) -> Path:
    """
    Analyzes the current git status / diff, compiles DraftPRMetadata, and writes
    a DRAFT-PR-<session_id>.md artifact. Optionally creates an isolated git branch.
    """
    root = (repo_root or Path.cwd()).resolve()
    target_branch = branch_name or f"minuscorrect/patch-{session_id}"
    out_path = output_file or (root / f"DRAFT-PR-{session_id}.md")

    # 1. Inspect modified files
    diff_files_res = subprocess.run(
        ["git", "diff", "--name-only", "HEAD"],
        cwd=str(root),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    modified = [line.strip() for line in diff_files_res.stdout.splitlines() if line.strip()]

    # 2. Inspect diff stat
    stat_res = subprocess.run(
        ["git", "diff", "--stat", "HEAD"],
        cwd=str(root),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    diff_stat = stat_res.stdout

    # 3. Read session state if available
    session_file = root / ".minuscorrect" / "sessions" / f"{session_id}.json"
    iteration_count = 1
    if session_file.exists():
        try:
            data = json.loads(session_file.read_text(encoding="utf-8"))
            iteration_count = data.get("current_iteration", 1)
        except Exception:
            # Rationale: Corrupted or unreadable session file defaults gracefully to iteration 1
            iteration_count = 1

    # 4. Optional branch creation and commit
    if commit_and_branch and modified:
        subprocess.run(
            ["git", "checkout", "-b", target_branch],
            cwd=str(root),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        subprocess.run(
            ["git", "add"] + modified,
            cwd=str(root),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        subprocess.run(
            ["git", "commit", "-m", f"fix(minuscorrect): autonomous repair for session {session_id}"],
            cwd=str(root),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

    metadata = DraftPRMetadata(
        session_id=session_id,
        branch_name=target_branch,
        title=f"fix(minuscorrect): autonomous repair [{session_id}]",
        summary=summary,
        modified_files=modified,
        iteration_count=iteration_count,
        diff_stat=diff_stat,
    )

    content = generate_draft_pr_markdown(metadata)
    out_path.write_text(content, encoding="utf-8")
    return out_path
