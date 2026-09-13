# Enterprise CI & Git Host Governance

This document outlines the security model, host-level protections, and continuous integration pipeline governing **MinusCorrect**.

---

## 1. The Watcher Paradox & In-Band Vulnerabilities

An autonomous agent with local shell execution operates with full user privileges. In a pure client-side setup, a runaway agent can:
1. Run `git commit --no-verify` to bypass local pre-commit hooks.
2. Export `ALLOW_GOLDEN_EDIT=1` to modify frozen test specifications.
3. Edit `scripts/verify_integrity.py` to disable verification checks.

MinusCorrect resolves this "Watcher Paradox" by implementing **bifurcated enforcement**:
- **Local Pre-Commit Hook:** Provides fast, zero-latency feedback to well-behaved agents and human developers.
- **Remote Out-of-Band CI:** Executes on clean, isolated GitHub Actions virtual machines where agent shell commands have zero reach.

---

## 2. Host-Level Protection via `.github/CODEOWNERS`

To ensure that golden contracts cannot be modified through automated pull requests without human review:

```
# .github/CODEOWNERS
/tests/golden/ @PROGRAMMER-DUMMY
```

### Pull Request Governance
1. Any pull request touching a file in `/tests/golden/` automatically requests review from designated human maintainers.
2. Repository branch protection rules enforce that PRs cannot merge into `main` without maintainer sign-off.
3. Even if an agent generates a pull request modifying golden assertions, the Git host blocks the merge.

---

## 3. GitHub Actions Verification Workflow

The CI workflow ([`.github/workflows/integrity.yml`](../.github/workflows/integrity.yml)) runs on every push and pull request:

```yaml
name: Systemic Integrity Verification

on:
  push:
    branches: [ main, master ]
  pull_request:
    branches: [ main, master ]

jobs:
  verify:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Run Systemic Integrity Verification
        run: |
          python scripts/verify_integrity.py

      - name: Run Semgrep Claim Audits
        uses: returntocorp/semgrep-action@v1
        with:
          config: .semgrep/unverified-claims.yml
        continue-on-error: true
```

This guarantees that every commit merging into production is verified independently of client-side repository state.
