# Golden Tests (Immutable Acceptance Specifications)

Files in this directory define the **non-negotiable system contracts, acceptance tests, and regression reproduction suites**.

## Rules for Autonomous Agents
1. **Strictly Read-Only During Implementation**: Autonomous agents are forbidden from modifying or loosening assertions in this directory when fixing bugs or implementing features.
2. **Authoring Phase Only**: Agents may add new test files here only during Phase 1 (Spec & Test Authoring), before implementation code is written.
3. **CI Gate**: CI pipelines enforce that PRs touching `tests/golden/` require explicit human review flags.
