# Autonomous Supervisor & Circuit Breaker Guide

This document details the mechanics, state transitions, and operational benefits of the **MinusCorrect Autonomous Supervisor** (`scripts/supervisor.py`).

---

## 1. Why External Process Supervision is Required

Prompt-based constraints ("stop after 4 retries") fail in production because:
1. Large Language Models do not reliably maintain iteration counters under long context degradation.
2. Under token pressure, agents panic and attempt ungrounded brute-force modifications.
3. When an in-band agent aborts, it leaves the local working tree corrupted with broken syntax, dirty diffs, and leftover debug print statements.

MinusCorrect moves circuit breaking **out-of-process** into `scripts/supervisor.py`. The supervisor executes external commands, monitors exit codes, computes error hashes, and enforces process termination.

---

## 2. Supervisor Architecture & Cycle Progression

```
[Agent Initiates Solver Cycle]
               │
               ▼
   Take Clean Snapshot of Target
               │
               ▼
       Execute Test Harness
               │
       +-------+-------+
       │               │
    (Pass)          (Fail)
       │               │
       ▼               ▼
Auto-Clean Debug   Compute SHA-256 Error Hash
(verify_integrity)     │
       │         +-----+-----+-----+
       ▼         │           │     │
     COMMIT   (Iter 1-2)  (Iter 3) (Iter 4)
                 │           │     │
              Repeat?     Repeat?  │
                 │        [DEBUG]  ▼
                 ▼        Inject  [ HARD ABORT ]
              Continue       │    1. Atomic Rollback
                 │           ▼    2. Generate DIAGNOSTIC-REPORT.md
                 +-------> Retest 3. Alert Human Maintainer
```

---

## 3. Normalized Error Hashing

To detect whether an agent is making algorithmic progress or spinning on the same root defect, the supervisor captures and normalizes `stderr` and `stdout`:

```python
def compute_error_hash(stderr: str, stdout: str) -> str:
    normalized = f"{stderr.strip()}\n{stdout.strip()}".strip()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]
```

- If two consecutive iterations yield the **identical error hash**, the supervisor recognizes that the agent's mental model is flawed.
- On iteration 3, the supervisor mandates **epistemic debug injection** (`[DEBUG]` print statements) so the agent can observe runtime values rather than guessing.

---

## 4. Transactional Rollback: Zero Cleanup Time for Humans

When iteration 4 fails, the circuit breaker trips. Rather than leaving the human engineer with a broken workspace, the supervisor executes an **atomic rollback**:

1. Restores the target implementation file from the initial pre-session snapshot.
2. Purges any untracked or partially modified files.
3. Automatically writes `DIAGNOSTIC-REPORT.md` to the workspace root.

### Structure of `DIAGNOSTIC-REPORT.md`
The generated report contains:
- **Failure Signature:** Normalized SHA-256 error hash and iteration count.
- **Last Stderr & Stdout:** The exact compiler or test runner failure trace.
- **Escalation Guidance:** The specific invariant that failed and options for human intervention.

This reduces human intervention from 30–60 minutes of tedious git archaeology to **2 minutes of targeted root-cause review**.
