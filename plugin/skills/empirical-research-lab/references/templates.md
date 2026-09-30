# Templates

Contents:
1. Pre-registration (write before running)
2. Decision log
3. Results table convention
4. Research memo skeleton
5. "Please run this" handoff (when you cannot execute)
6. Reviewing user-pasted results

All bracketed fields are placeholders to be filled from real information. Leave a field as `TBD` rather than guessing.

## 1. Pre-registration (write before running)

Keep it to one page. Save it next to the code and reference its path in the receipt.

```markdown
# Experiment plan: [experiment_id]
Date: [YYYY-MM-DD]   Author: [name]   Code commit: [hash or TBD]

## Question
[One sentence.]

## Hypothesis and falsification
H1: [specific, directional if possible]
Falsified if: [concrete observation, with threshold]
H0 / alternative explanations to rule out: [list]

## Design
- Method(s) under test: [...]
- Baselines: [trivial], [strong/standard]  (tuning budget: [...])
- Data: [source, version/hash], split: [train/val/test rule], test set touched: once, at [stage]
- Primary metric: [name, definition]   Secondary: [...]
- Success threshold: [smallest effect that matters]
- Runs: [n seeds / n examples]  -  rationale: [power or practical reason]
- Controls/sanity checks: [shuffled labels, planted signal, known answer]

## Analysis plan
[How the primary comparison will be computed, incl. interval method and any multiplicity correction.]

## Stopping/abandon rule
[When to stop or pivot.]

## Exploratory items (declared up front)
[Anything you expect to look at without a prior hypothesis.]
```

## 2. Decision log

Append an entry whenever the plan changes or a judgment call is made. This is what lets a reader distinguish planned from post-hoc.

```markdown
## [YYYY-MM-DD HH:MM] [short title]
- Trigger: [what was observed or what blocked progress; receipt path]
- Decision: [what changed]
- Alternatives considered: [...]
- Effect on claims: [confirmatory -> exploratory? new baseline? dropped config?]
```

Log at least: dropped or added configs, changed metrics or thresholds, excluded data or runs (with reason), reruns of failed jobs (with reason and both receipts), and any peek at test data.

## 3. Results table convention

Every row is a run set with a receipt. Include `n` and spread. Unrun cells stay `PENDING_RUN`. Use consistent units.

```markdown
| Config | Metric | n (runs/examples) | Mean ± SD | 95% CI | Receipt | Status |
|---|---|---|---|---|---|---|
| [baseline A] | [metric] | [n] | [..] | [..] | receipts/[file].json | MEASURED |
| [method B] | [metric] | [n] | PENDING_RUN | PENDING_RUN | - | PENDING_RUN |
| [config C] | [metric] | [n] | - | - | receipts/[file].json | FAILED: [reason] |
```

Failed and negative rows stay in the table.

## 4. Research memo skeleton

```markdown
# [Title]
Status: [DRAFT / results pending / complete]   Date: [..]

## 1. Summary
[2-4 sentences: question, what was measured, main result with interval, main caveat.]

## 2. Setup (as run)
[Config, data version, commit, environment, seeds. Point to the receipts. Note deviations from the plan and link to the decision log.]

## 3. Findings (measured)
[Results table(s) with n and spread. Each claim labeled by provenance. Includes negative results and failed runs.]

## 4. Sanity checks and controls
[Smoke test, known-answer test, shuffled-label control, leakage checks: what was done and what they showed.]

## 5. Limitations and threats to validity
[What this evidence does not show: dataset scope, contamination risk, number of configs tried, single hardware type, etc.]

## 6. Hypotheses and next experiments (not yet tested)
[Goals, projections, and ideas, all labeled HYPOTHESIS, each with the experiment that would test it.]

## 7. Sources
[Cited works with confirmation of what was used from each.]
```

Keep sections 3 and 6 separate; targets and estimates never appear in the findings table.

## 5. "Please run this" handoff (when you cannot execute)

Use when the target environment (GPU, cluster, instrument) is not available to you.

```markdown
I can't run this here, so nothing below is measured yet. To get real results:

1. Run: `[exact command]`
2. Expected runtime/resources: [estimate, labeled as estimate]
3. It will write: `[receipt path]` (create it with `scripts/make_receipt.py create ...`)
4. Please paste back: the receipt JSON, and the last ~50 lines of stdout (or attach the files).

What I'll do with it: compute intervals over the runs, compare with the baseline, check for leakage/too-good-to-be-true signs, and fill in the PENDING_RUN cells. If the run fails (OOM, divergence, crash), paste the error; that is useful data.
```

## 6. Reviewing user-pasted results

When the user provides numbers or a receipt:

1. Label them `USER-REPORTED` (or `MEASURED` only if you parsed the actual artifact).
2. Check internal consistency: counts vs rates (17/20 is 0.85, not 0.9), sums, units, per-run values vs their reported mean, timestamps, sample sizes vs the stated dataset size.
3. Check what's missing: `n`, seeds, spread, baseline, data/config hash, decoding/eval settings.
4. Apply the too-good-to-be-true and leakage checks before interpreting.
5. Report what the data supports and what it doesn't; ask for the specific missing artifact rather than assuming.
6. If `scripts/make_receipt.py verify` is available and a receipt is attached, run it to check the self-hash and input hashes.
