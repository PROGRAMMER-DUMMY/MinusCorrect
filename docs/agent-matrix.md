# Multi-Agent Integration Matrix

MinusCorrect eliminates fragmented, proprietary configuration files (`CLAUDE.md`, `AGY.md`) in favor of the emerging open standard: **`AGENTS.md`**.

---

## 1. Supported Agent Runtimes

MinusCorrect provides universal interoperability across all leading agentic frameworks:

| Agent Framework | Primary Interface | Native Integration Stub | Canonical Reference |
| :--- | :--- | :--- | :--- |
| **Claude Code** | Terminal CLI (`claude`) | Root `AGENTS.md` | `AGENTS.md` |
| **Google Antigravity (AGY)** | Agent CLI / IDE | Root `AGENTS.md` | `AGENTS.md` |
| **OpenAI Codex** | Cloud / Local Runner | `.codex/instructions.md` | Pointer to `AGENTS.md` |
| **Cursor IDE** | Editor Agent / Composer | `.cursorrules` | Pointer to `AGENTS.md` |
| **Aider & OpenHands** | Terminal CLI | Root `AGENTS.md` | `AGENTS.md` |

---

## 2. The Universal Configuration Pattern

To prevent context drift when multiple agents work on the same repository, all tool-specific configuration stubs contain a clean, one-line reference:

### `.cursorrules`
```text
# MinusCorrect Universal Protocol
Adhere strictly to AGENTS.md and .agent-rules/systemic-integrity.md.
```

### `.codex/instructions.md`
```text
# MinusCorrect Universal Protocol
Read and adhere to the canonical rules in AGENTS.md and .agent-rules/systemic-integrity.md.
```

---

## 3. Cross-Agent Handoff Guarantees

When one agent (e.g. Claude Code) starts a refactoring task and another agent (e.g. Cursor) continues the work:
1. **Unified Invariants:** Both agents operate under the exact same non-negotiable rules defined in `AGENTS.md`.
2. **Zero Scaffolding Contamination:** `scripts/verify_integrity.py --fix` ensures that no temporary debug logs or custom comments from one agent bleed into subsequent agent sessions.
3. **Immutable Regression Safety:** Even if an agent has different internal prompt priors, it is physically constrained from loosening acceptance assertions in `tests/golden/`.
