# Golden Contracts & Test Stratification

Test stratification is the core physical boundary in MinusCorrect. It prevents autonomous agents from gaming evaluation harnesses by separating immutable system contracts from mutable developer tests.

---

## 1. The Stratification Model

In standard software projects, agents often alter test assertion values when implementation becomes challenging (e.g., changing `assert result == 5` to `assert result is not None`). MinusCorrect eliminates this by dividing the test directory into two distinct permission zones:

| Directory | Mutability | Ownership | Purpose |
| :--- | :--- | :--- | :--- |
| **`tests/golden/`** | **Immutable** | Human Maintainers (`.github/CODEOWNERS`) | System contracts, acceptance criteria, bug reproduction suites. Strictly read-only to agents during implementation. |
| **`tests/unit/`** | **Mutable** | Autonomous Agents & Developers | Component-level tests, internal helper mocks, and rapid TDD exploration. Agents have full read/write access. |

---

## 2. The Contract Authoring Lifecycle

Every bug fix or feature addition proceeds through a two-phase lifecycle:

### Phase 1: Spec & Test Authoring
1. Before touching production code in `src/`, author a reproduction test in `tests/golden/` (e.g., `tests/golden/test_issue_402.py`).
2. Include boundary cases: empty payloads, maximum bounds, malformed unicode, concurrent access.
3. Run the test harness to confirm that the test fails for the expected root cause.
4. Commit the new contract:
   ```bash
   git add tests/golden/test_issue_402.py
   git commit -m "spec: add golden acceptance contract for issue #402"
   ```
5. Once committed, `tests/golden/` is frozen.

### Phase 2: Bounded Implementation Solver
1. The agent is dispatched with `tests/golden/` provided as **read-only context**.
2. The agent is bounded to mutate only the designated implementation file (e.g., `src/parser.py`).
3. The local pre-commit hook (`scripts/verify_integrity.py`) blocks any commit that modifies `tests/golden/`.

---

## 3. The Break-Glass Override (`ALLOW_GOLDEN_EDIT=1`)

Software specifications legitimately evolve over time. When an API signature is intentionally changed or a feature is deprecated, human maintainers can bypass the local golden lock using the explicit environment override:

```bash
ALLOW_GOLDEN_EDIT=1 git commit -m "refactor(contracts): update payment API contract for v2"
```

### Git Host Enforcement
Even if an autonomous agent with local shell access discovers and invokes `ALLOW_GOLDEN_EDIT=1`, it cannot merge the changes into protected branches without human review:
- **`.github/CODEOWNERS`** requires mandatory approval from designated repository maintainers for any pull request modifying files in `/tests/golden/`.
- GitHub branch protection rules prevent merging unapproved pull requests.
