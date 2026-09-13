# MinusCorrect: Architectural Specification & System Mechanics

A formal, code-first architectural specification of the control loops, verification boundaries, and deterministic gatekeepers governing autonomous coding agents.

---

## 1. Architectural Thesis: Code Over Diagrams

Conventional architecture documentation relies on static boxes-and-arrows diagrams that decay immediately upon implementation. In autonomous agent engineering, diagrammatic abstractions are fundamentally insufficient because:
1. Autonomous agents (Claude Code, Antigravity, OpenAI Codex, Cursor) cannot compile or execute visual geometry.
2. Abstract arrows fail to define invariant boundaries, type signatures, and state transition error conditions.
3. Systemic guarantees (immutability, blast-radius containment, claim verification) require deterministic algorithmic definitions.

MinusCorrect formalizes its architecture directly as typed data contracts, interface abstractions, finite state machines, and executable verification pipelines.

---

## 2. Core Domain Contracts & Type System

The architecture is founded on a formal type system modeling agent actions, verification boundaries, and documentation claims.

```python
from __future__ import annotations

import ast
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import List, Optional, Protocol, Sequence, Set


class BoundaryMutability(Enum):
    """Defines agent write permissions across repository subtrees."""
    IMMUTABLE_CONTRACT = auto()  # e.g., tests/golden/ (Read-only during implementation)
    MUTABLE_WORKING = auto()     # e.g., tests/unit/ (Read-write for iterative testing)
    TARGET_ACTUATOR = auto()     # e.g., src/ (Target implementation file under edit)


class ClaimCategory(Enum):
    """Categorization of comments and docstring assertions."""
    OPERATIONAL_GUARANTEE = "Category_1_Operational"  # Complexity, concurrency, purity
    CONTEXTUAL_RATIONALE = "Category_2_Rationale"     # Trade-offs, hardware quirks, workarounds


class LoopStatus(Enum):
    """Termination state for the agent actuator circuit breaker."""
    ACTIVE = "ACTIVE"
    CONVERGED = "CONVERGED"
    SCAFFOLDING_REQUIRED = "SCAFFOLDING_REQUIRED"
    HARD_ABORT = "HARD_ABORT"


@dataclass(frozen=True)
class OperationalClaim:
    """Represents an extracted code docstring claim requiring verification."""
    symbol_name: str
    file_path: Path
    line_number: int
    category: ClaimCategory
    declared_attribute: str   # e.g., "O(1)", "thread-safe", "idempotent"
    receipt_target: Optional[Path] = None
    is_verified: bool = False


@dataclass
class CircuitBreakerState:
    """Tracks closed-loop iteration history and error signatures."""
    current_iteration: int = 0
    max_iterations: int = 4
    error_hash_history: List[str] = field(default_factory=list)
    scaffolding_injected: bool = False
    status: LoopStatus = LoopStatus.ACTIVE

    def register_run(self, error_hash: Optional[str]) -> LoopStatus:
        self.current_iteration += 1

        if error_hash is None:
            self.status = LoopStatus.CONVERGED
            return self.status

        self.error_hash_history.append(error_hash)

        if self.current_iteration >= self.max_iterations:
            self.status = LoopStatus.HARD_ABORT
            return self.status

        # If consecutive runs produce identical error hashes, mandate epistemic debug traces
        if len(self.error_hash_history) >= 2 and self.error_hash_history[-1] == self.error_hash_history[-2]:
            self.status = LoopStatus.SCAFFOLDING_REQUIRED
        else:
            self.status = LoopStatus.ACTIVE

        return self.status
```

---

## 3. The Cybernetic Closed-Loop Controller

The agent actuator does not operate in an unconstrained conversation loop. It is governed by a cybernetic state machine that coordinates prompt synthesis, test harness execution, error hashing, and emergency circuit breaking.

```python
import hashlib
import subprocess
from typing import Dict, Any


class ClosedLoopActuator:
    """
    Coordinates agent code mutations within bounded test-iteration cycles.
    Derived from micro-agent closed-loop feedback architecture.
    """

    def __init__(self, target_file: Path, golden_suite: Path, test_cmd: List[str]):
        self.target_file = target_file
        self.golden_suite = golden_suite
        self.test_cmd = test_cmd
        self.state = CircuitBreakerState()

    def compute_error_hash(self, stderr: str, stdout: str) -> str:
        """Derives a normalized SHA-256 signature from test failure output."""
        normalized = f"{stderr.strip()}\n{stdout.strip()}"
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]

    def run_cycle(self, agent_runtime: Any) -> Dict[str, Any]:
        """
        Executes bounded solver loop with a hard 4-iteration ceiling.
        """
        while self.state.status in (LoopStatus.ACTIVE, LoopStatus.SCAFFOLDING_REQUIRED):
            # Phase 1: Synthesize patch bounded strictly to target file
            patch = agent_runtime.synthesize_patch(
                target_file=self.target_file,
                golden_suite=self.golden_suite,
                iteration=self.state.current_iteration,
                mode="DEBUG" if self.state.status == LoopStatus.SCAFFOLDING_REQUIRED else "NORMAL"
            )
            self.apply_patch(patch)

            # Phase 2: Execute immutable test harness
            result = subprocess.run(self.test_cmd, capture_output=True, text=True)

            if result.returncode == 0:
                # Tests passed: Verify no debug scaffolding was left behind
                if self.detect_leftover_scaffolding():
                    self.strip_scaffolding()
                self.state.status = LoopStatus.CONVERGED
                return {"status": "SUCCESS", "iterations": self.state.current_iteration}

            # Phase 3: Hash error and transition state machine
            error_sig = self.compute_error_hash(result.stderr, result.stdout)
            next_status = self.state.register_run(error_sig)

            if next_status == LoopStatus.HARD_ABORT:
                # Trip breaker: prevent infinite token burn and force escalation
                return {
                    "status": "HARD_ABORT",
                    "iterations": self.state.current_iteration,
                    "last_error_hash": error_sig,
                    "stderr": result.stderr,
                    "stdout": result.stdout,
                    "reason": "Exceeded 4 iterations on immutable acceptance contracts."
                }

        return {"status": self.state.status.value}

    def detect_leftover_scaffolding(self) -> bool:
        content = self.target_file.read_text(encoding="utf-8")
        return "[DEBUG]" in content

    def strip_scaffolding(self) -> None:
        lines = self.target_file.read_text(encoding="utf-8").splitlines()
        cleaned = [line for line in lines if "[DEBUG]" not in line]
        self.target_file.write_text("\n".join(cleaned) + "\n", encoding="utf-8")

    def apply_patch(self, patch_content: str) -> None:
        self.target_file.write_text(patch_content, encoding="utf-8")
```

---

## 4. AST Docstring & Claim Verification Engine

Rather than relying on fragile regex heuristics, MinusCorrect parses code into an Abstract Syntax Tree (`ast`) to statically inspect function and class docstrings for unsubstantiated claims.

```python
class SystemicIntegrityAuditor(ast.NodeVisitor):
    """
    AST Visitor auditing Category 1 Operational Guarantees and Category 2 Rationale tags.
    """

    FORBIDDEN_SUPERLATIVES = {
        "universal", "bulletproof", "blazing fast", "domain-agnostic", "infinitely scalable"
    }

    OPERATIONAL_TAGS = {
        "o(1)": "Complexity",
        "thread-safe": "Concurrency",
        "lock-free": "Concurrency",
        "idempotent": "Purity",
        "zero-dependency": "Dependency"
    }

    def __init__(self, file_path: Path):
        self.file_path = file_path
        self.violations: List[str] = []
        self.extracted_claims: List[OperationalClaim] = []

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._audit_docstring(node.name, node.lineno, ast.get_docstring(node))
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._audit_docstring(node.name, node.lineno, ast.get_docstring(node))
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self._audit_docstring(node.name, node.lineno, ast.get_docstring(node))
        self.generic_visit(node)

    def _audit_docstring(self, symbol_name: str, lineno: int, docstring: Optional[str]) -> None:
        if not docstring:
            return

        doc_lower = docstring.lower()

        # Check 1: Superlative Ban
        for superlative in self.FORBIDDEN_SUPERLATIVES:
            if superlative in doc_lower:
                self.violations.append(
                    f"{self.file_path}:{lineno} Symbol '{symbol_name}' contains "
                    f"prohibited marketing superlative: '{superlative}'"
                )

        # Check 2: Operational Guarantee Verification Receipt
        for tag, attr_type in self.OPERATIONAL_TAGS.items():
            if tag in doc_lower:
                # Operational claim found: Must have explicit test receipt
                receipt_prefix = "# verifies:"
                if receipt_prefix not in docstring:
                    self.violations.append(
                        f"{self.file_path}:{lineno} Symbol '{symbol_name}' claims {attr_type} "
                        f"guarantee '{tag}' but lacks mandatory test receipt ('# verifies: tests/...')"
                    )
                else:
                    self.extracted_claims.append(
                        OperationalClaim(
                            symbol_name=symbol_name,
                            file_path=self.file_path,
                            line_number=lineno,
                            category=ClaimCategory.OPERATIONAL_GUARANTEE,
                            declared_attribute=tag,
                            is_verified=True
                        )
                    )
```

---

## 5. Deterministic Gatekeeper Pipeline

Enforcement does not rely on voluntary agent compliance. The gatekeeper executes as a composable pipeline where each gate validates a specific systemic invariant.

```python
class VerificationGate(Protocol):
    def evaluate(self, staged_files: Sequence[Path], env: Dict[str, str]) -> GateResult:
        """Evaluates invariant against staged changeset. Returns non-zero on failure."""
        ...


@dataclass
class GateResult:
    passed: bool
    gate_name: str
    message: str
    errors: List[str] = field(default_factory=list)


class GoldenBoundaryGate:
    """
    Prevents autonomous agents from loosening or modifying acceptance specs in tests/golden/.
    Allows human override only when ALLOW_GOLDEN_EDIT=1 is explicitly supplied.
    """

    def evaluate(self, staged_files: Sequence[Path], env: Dict[str, str]) -> GateResult:
        golden_mods = [f for f in staged_files if "tests/golden" in f.as_posix()]

        if not golden_mods:
            return GateResult(True, "GoldenBoundaryGate", "No golden contracts modified.")

        if env.get("ALLOW_GOLDEN_EDIT") == "1":
            return GateResult(True, "GoldenBoundaryGate", "Golden edit permitted via explicit override flag.")

        return GateResult(
            passed=False,
            gate_name="GoldenBoundaryGate",
            message="Modification to immutable golden contracts detected.",
            errors=[f"Unauthorized edit: {f}" for f in golden_mods]
        )


class ScaffoldingSanitizationGate:
    """
    Ensures temporary epistemic traces ([DEBUG]) injected during iteration 3 are purged.
    """

    def evaluate(self, staged_files: Sequence[Path], env: Dict[str, str]) -> GateResult:
        residual_tags = []
        source_extensions = {".py", ".ts", ".js", ".go", ".rs", ".java"}

        for file_path in staged_files:
            if file_path.suffix not in source_extensions:
                continue
            if not file_path.exists():
                continue

            content = file_path.read_text(encoding="utf-8", errors="ignore")
            if "[DEBUG]" in content or '__DEBUG__' in content:
                residual_tags.append(str(file_path))

        if residual_tags:
            return GateResult(
                passed=False,
                gate_name="ScaffoldingSanitizationGate",
                message="Committed files contain residual debug scaffolding.",
                errors=[f"Leftover [DEBUG] tag in: {f}" for f in residual_tags]
            )

        return GateResult(True, "ScaffoldingSanitizationGate", "Source tree free of debug scaffolding.")


class IntegrityPipeline:
    """Executes verification gates in linear sequence."""

    def __init__(self, gates: Sequence[VerificationGate]):
        self.gates = gates

    def run(self, staged_files: Sequence[Path], env: Dict[str, str]) -> bool:
        for gate in self.gates:
            result = gate.evaluate(staged_files, env)
            if not result.passed:
                print(f"[REJECTED] {result.gate_name}: {result.message}")
                for err in result.errors:
                    print(f"  - {err}")
                return False
            print(f"[PASSED] {result.gate_name}")
        return True
```

---

## 6. Threat Modeling & Isolation Architecture

Executing autonomous agents with local shell access introduces distinct operational attack surfaces:

| Threat Vector | Mechanism | Systemic Mitigation |
| :--- | :--- | :--- |
| **Specification Gaming** | Agent alters test assertion values (e.g. `assert res == 5` to `assert res is not None`) to achieve an artificial green exit code. | `GoldenBoundaryGate` blocks all commits altering `tests/golden/` unless signed by human override `ALLOW_GOLDEN_EDIT=1`. |
| **Synthetic Delay Injection** | Agent bypasses concurrency race conditions by injecting hardcoded `time.sleep(0.5)` calls. | Invariant 3 explicitly bans magic constants. Pre-commit AST analysis detects artificial delays in non-IO code. |
| **Downstream Symptom Masking** | Agent wraps failing core routines in blanket `try/except: pass` blocks and returns blank mock dictionaries. | Invariant 1 mandates root-cause resolution. Unit suites require strict held-out boundary testing against empty and adversarial inputs. |
| **Watcher Paradox (In-Band Tampering)** | Agent with write access modifies `scripts/verify_integrity.py` to disable verification gates. | Bifurcated execution: Local checks provide fast feedback, while **out-of-band GitHub Actions CI** runs on isolated, immutable runner images. |
| **Infinite Context Exhaustion** | Agent spins across 20+ iterations repeatedly analyzing identical test failure traces. | `CircuitBreakerState` hashes error signatures and forces a hard abort at iteration 4 with runtime state dump. |

---

## 7. Multi-Agent Interoperability Architecture

MinusCorrect unifies heterogeneous agent tooling under the open **`AGENTS.md`** standard:

```
[Agent System Initialization]
          │
          ├─► Claude Code ──────────┐
          ├─► Google Antigravity ───┼─► Reads root AGENTS.md
          ├─► OpenAI Codex ─────────┤   (Canonical instruction set)
          └─► Cursor IDE ───────────┘
                                      │
                                      ▼
                      Reads .agent-rules/systemic-integrity.md
                                      │
                                      ▼
                      Bounded Actuator Loop (Phase 1 -> Phase 2)
                                      │
                                      ▼
                      Local Pre-Commit Hook (scripts/verify_integrity.py)
                                      │
                                      ▼
                      Remote CI Pipeline (.github/workflows/integrity.yml)
```

By decoupling operational rules from proprietary prompt formats and compiling them into deterministic code contracts, MinusCorrect ensures consistent, disciplined engineering execution across all agent runtimes.
