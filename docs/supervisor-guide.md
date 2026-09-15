# Autonomous Supervisor & Circuit Breaker Guide

This document details the mechanics, state transitions, and operational guarantees of the **MinusCorrect Autonomous Supervisor** (`minuscorrect.supervisor` / `minuscorrect run`).

---

## 1. Why External Process Supervision is Required

Prompt-based constraints ("stop after 4 retries") fail in production because:
1. Large Language Models do not reliably maintain iteration counters under long context degradation.
2. Under token pressure, agents panic and attempt ungrounded brute-force modifications.
3. When an in-band agent aborts, it leaves the local working tree corrupted with broken syntax, dirty diffs, and leftover debug print statements.

MinusCorrect moves circuit breaking **out-of-process** into `minuscorrect.supervisor` (accessible via `minuscorrect run` and `mc-supervisor`). The supervisor executes external test commands, normalizes failure streams, computes deterministic error hashes, persists execution state to disk, and enforces strict process termination.

---

## 2. Supervisor Architecture & Cycle Progression

```
[Agent Initiates Solver Cycle]
               |
               v
   Capture Git Tree State Snapshot
               |
               v
       Execute Test Harness (e.g. pytest tests/golden/)
               |
       +-------+-------+
       |               |
    (Pass)          (Fail)
       |               |
       v               v
Auto-Clean Debug   Sanitize Trace & Compute SHA-256 Hash
(verify_integrity)     |
       |         +-----+-----+-----+
       v         |           |     |
     COMMIT   (Iter 1-2)  (Iter 3) (Iter 4)
                 |           |     |
              Repeat?     Repeat?  |
                 |        [DEBUG]  v
                 v        Inject  [ HARD ABORT ]
              Continue       |    1. Git-Tree Atomic Rollback
                 |           v    2. Generate DIAGNOSTIC-REPORT.md
                 +-------> Retest 3. Alert Human Maintainer
```

---

## 3. Persistent Multi-Session State

To maintain loop counters across independent CLI calls, the supervisor serializes session history to `.minuscorrect/sessions/<session_id>.json`:

```json
{
  "session_id": "default",
  "created_at": "2026-09-14T19:11:37.464271+00:00",
  "updated_at": "2026-09-14T19:11:39.123456+00:00",
  "status": "ACTIVE",
  "current_iteration": 2,
  "max_iterations": 4,
  "history": [
    {
      "iteration": 1,
      "exit_code": 1,
      "hash": "a31e555fb0de1000",
      "command": ["pytest", "tests/golden/test_issue.py"]
    }
  ]
}
```

### Session Lifecycle States
- **`ACTIVE`**: The agent is within the 1-4 iteration budget and actively attempting algorithmic solutions.
- **`SCAFFOLDING_REQUIRED`**: Repeated identical error signatures detected at iteration 3. The supervisor prompts for `[DEBUG]` logging injection.
- **`HARD_ABORT`**: The agent reached the 4-iteration ceiling without passing. The supervisor executes an atomic rollback and halts execution.
- **`CONVERGED`**: Test harness passed with exit code 0. Residual debug logs are automatically sanitized.

---

## 4. Volatile-Token Sanitization & Deterministic Error Hashing

Raw stderr and stdout frequently contain timing jitter, memory addresses, and process IDs. If hashed directly, every run produces a different hash, blinding loop detection.

The supervisor's `sanitize_trace()` function removes non-deterministic tokens before hashing:

```python
def sanitize_trace(raw_trace: str) -> str:
    cleaned = raw_trace
    # Strip memory pointers: 0x7fff5fbff8b0 -> 0xADDR
    cleaned = re.sub(r"0x[0-9a-fA-F]+", "0xADDR", cleaned)
    # Strip test execution durations: 0.04s, 12ms -> <DURATION>
    cleaned = re.sub(r"\b\d+(\.\d+)?(s|ms)\b", "<DURATION>", cleaned)
    # Strip ISO timestamps: 2026-09-14T18:00:00Z -> <TIMESTAMP>
    cleaned = re.sub(r"\d{4}-\d{2}-\d{2}[T\s]\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:?\d{2})?", "<TIMESTAMP>", cleaned)
    # Strip PID markers
    cleaned = re.sub(r"\bpid\s*=\s*\d+\b", "pid=<PID>", cleaned, flags=re.IGNORECASE)
    return cleaned
```

The normalized trace is hashed with SHA-256 (truncated to 16 hex characters):
- If consecutive iterations yield the **identical error hash**, the supervisor recognizes that the agent's mental model is flawed.
- On iteration 3, the supervisor mandates **epistemic debug injection** (`[DEBUG]` print statements) so the agent observes runtime values rather than guessing.

---

## 5. Safe Git-Tree Atomic Rollback & Execution Timeouts

### Execution Timeout Protection
To prevent test deadlocks, infinite loops, or hanging network requests from freezing the supervisor, test commands are executed with an enforced wall-clock timeout (default: 120 seconds, configurable via `--timeout`):

- If a test exceeds the timeout threshold, the supervisor raises `subprocess.TimeoutExpired`, records exit code `124`, notes the timeout in `stderr`, and advances the loop counter.
- This guarantees that process deadlocks trigger the circuit breaker rather than hanging indefinitely.

### Safe Rollback with Secret & Configuration Preservation
When iteration 4 fails, the circuit breaker trips. Rather than executing a destructive wipe of untracked developer files, the supervisor executes a **safe atomic rollback**:

```bash
git checkout -- .
git clean -fd -e ".env*" -e ".venv*" -e "venv*" -e "*.local" -e ".minuscorrect*"
```

1. Reverts all modified tracked files across the repository to the pre-session state.
2. Deletes untracked agent scratch files and temporary build artifacts.
3. **Preserves developer secrets and configurations:** Untracked `.env`, `.env.local`, virtual environments (`.venv/`), and `.minuscorrect` state files are strictly preserved.
4. Automatically writes `DIAGNOSTIC-REPORT.md` to the workspace root.

### Structure of `DIAGNOSTIC-REPORT.md`
The generated report contains:
- **Failure Signature:** Normalized SHA-256 error hash and iteration count.
- **Last Stderr & Stdout:** The exact compiler or test runner failure trace.
- **Reproduction Command:** The exact test command executed.
- **Escalation Guidance:** The specific invariant that failed and options for human intervention.

This reduces human intervention from 30–60 minutes of tedious git archaeology to **2 minutes of targeted root-cause review**.

---

## 6. CLI Command Reference

MinusCorrect provides a unified CLI for supervisor operations:

```bash
# Run a test under supervisor control with timeout (default: 120s)
minuscorrect run --session-id issue-402 --timeout 60 -- pytest tests/golden/test_issue_402.py

# Inspect active supervisor session status
minuscorrect status --session-id issue-402

# Reset an existing session
minuscorrect reset --session-id issue-402

# Direct runner entry point
mc-supervisor --session-id issue-402 --timeout 60 -- pytest tests/golden/test_issue_402.py
```

---

## 7. Local Golden Immutability & Anti-Swallowing Gates

MinusCorrect enforces systemic integrity before code ever reaches remote GitHub PR checks:

### Local Golden Immutability Guard
Before executing any test step, `minuscorrect run` inspects `git status --porcelain`. If any file in `tests/golden/` has been modified, added, or deleted without the explicit break-glass token `ALLOW_GOLDEN_EDIT=1`, the supervisor immediately halts execution with status `TAMPERING_DETECTED` (exit code 3). This prevents local agents from modifying acceptance criteria during iterative solver runs.

### Anti-Swallowing Semantic Check
In `minuscorrect verify`, staged source code changes are analyzed to detect the "fix-by-swallowing" anti-pattern:
- Blanket `except: pass` or `except Exception: return None` blocks are rejected unless explicitly documented with a business rationale tag (`# Rationale: <reason>`).
- Forces agents to solve underlying boundary logic rather than masking symptoms behind silent exception suppression.

