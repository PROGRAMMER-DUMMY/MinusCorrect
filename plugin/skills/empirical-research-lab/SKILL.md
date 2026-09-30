---
name: empirical-research-lab
description: >-
  Rigorous protocol for empirical research in any domain: experimental design, benchmark interpretation, model and algorithm evaluation, data analyses, ablations, and performance measurements. Enforces claim provenance (MEASURED, USER-REPORTED, CITED, DERIVED, HYPOTHESIS), pre-stated hypotheses, baselines, variance, leakage checks, machine-generated tamper-evident run receipts (make_receipt.py), and honest handling of negative results.
---

# Empirical Research Lab

A protocol for making empirical claims that survive scrutiny. It is domain-neutral: it applies to ML experiments, simulations, data analysis, performance benchmarks, and even theory work that leans on numerical checks. Domain-specific material lives in `references/` and is loaded only when relevant.

The underlying goal: a reader should be able to take any number in your output and trace it to where it came from, and should know how much to trust it.

## Core principles

1. **Every claim has provenance.** Each number or factual claim is one of the labels in the table below. If it can't be labeled, it doesn't go in as a finding.
2. **No fabricated numbers.** Never invent, extrapolate, round up, or "typically expect" a metric and present it as a result. Projections are allowed only when labeled `HYPOTHESIS` with the reasoning shown. Plausible-looking made-up numbers are worse than blanks, because they get copied into papers and decisions.
3. **Receipts over recollection.** Metrics come from machine-generated artifacts (logs, receipt files, profiler traces, notebooks' saved outputs), not from memory or from what the code "should" print.
4. **Failure is data.** OOM crashes, divergence, regressions, null results, and surprising baselines are findings. Diagnose root causes; never drop, rerun-until-good, or quietly patch around them.
5. **Ground everything in the real files.** Hyperparameters, dimensions, dataset versions, and checkpoints are read from the actual config/data before a run, not assumed.
6. **Scale claims to the evidence.** A result with no sample size, variance, or baseline is an anecdote. State what was measured, on how much, against what, and what would change the conclusion.

### Provenance labels

| Label | Meaning | Required attachment |
|---|---|---|
| `MEASURED` | Produced by a run in this work | path to receipt/log |
| `USER-REPORTED` | User pasted or stated it; not verified by you | say so; sanity-check consistency |
| `CITED` | From a paper/doc/source | exact source; you confirmed it exists and says this |
| `DERIVED` | Calculated from other labeled values | show the formula and inputs |
| `HYPOTHESIS` | Prediction or estimate, not yet tested | reasoning + how to test |
| `PENDING_RUN` | Slot for a result not yet obtained | the command that will fill it |

## First decision: can you execute anything?

Check what tools you actually have before promising results.

- **You can run code on the target environment:** follow the full workflow below, and generate receipts with `scripts/make_receipt.py`.
- **You cannot run it** (typical in chat, or when the target is the user's GPU/cluster/lab): your job is to make the user's run maximally informative. Deliver (a) the harness or script, (b) the exact command, (c) the pre-run plan from step 1, (d) a results table with every cell `PENDING_RUN`, and (e) a request to paste back the receipt/log. Do not fill the table "for illustration". When results come back, mark them `USER-REPORTED` unless the artifact itself is attached and you parse it.
- **You can run only small things** (CPU, mock data): run the hermetic smoke test (step 3) and report it as exactly that, a smoke test, not as evidence about the real system.

## Workflow

Research is iterative. Loop back freely, but log every deviation from the plan (see `references/templates.md`, decision log) so the final report shows what was planned versus what was done.

### 1. Frame before running

Write down, before seeing results:

- **Question and hypothesis**, plus a **falsification criterion**: what result would make you abandon or revise the hypothesis. Without one, any outcome can be explained after the fact.
- **Primary metric** and success threshold; any secondary metrics named up front.
- **Baselines**: at least one trivial (random, majority class, naive heuristic) and one strong/standard method, given the same tuning effort and compute budget as the new method.
- **Data and splits**: what is train/validation/test, where the test set is touched exactly once.
- **Sample plan**: number of seeds/runs/examples, and why that is enough to detect the effect you care about.
- **Exploratory vs confirmatory**: anything decided after seeing data is exploratory and must be reported as such.

Use the pre-registration template in `references/templates.md`. Short is fine; unwritten is not.

### 2. Design for integrity

Before compute is spent, check:

- Leakage: overlap between train/val/test, preprocessing fit on all data, tuning on test, benchmark contamination in pretraining data. (Checklist: `references/statistics.md`.)
- Comparisons are fair: same data, same budget, same seeds where paired.
- Configs verified against the real files, not remembered.
- Environment pinned (versions, seeds, commit, data hash).
- Measurement is what you think it is: silent defaults (caching, train/eval mode, warmup, async execution, cached results) can invalidate a benchmark. Look for them explicitly.

### 3. Hermetic smoke test

Run the smallest possible version (tiny config, subset of data, few steps) to catch shape errors, crashes, and broken metrics code before a large run. Include a **known-answer test** where the correct result is known in advance (an overfit-one-batch test, a synthetic dataset with planted signal, a shuffled-label control that should give chance performance). A pipeline that can't recover a planted effect can't be trusted to find a real one.

### 4. Feasibility and resource envelope

Estimate cost (memory, time, samples needed) before launching. Label every estimate `DERIVED` or `HYPOTHESIS`, and treat formulas as lower bounds unless you have measured. Domain formulas: `references/ml-systems.md`, `references/other-domains.md`.

### 5. Execute and capture

Log the environment and raw outputs automatically, not by hand. Emit a receipt per run (schema in `references/receipt-schema.json`, generator in `scripts/make_receipt.py`). Record failed and partial runs as receipts too, with the failure reason.

### 6. Audit before reporting

Before any number leaves the lab, run this pass:

- Does each number trace to a receipt? Are `n`, seeds, and spread reported?
- Is there a baseline, and is the comparison paired and fair?
- **Too-good-to-be-true check:** perfect or near-perfect scores, huge gains, or results that beat published numbers call for hunting for leakage, metric bugs, or trivial solutions *first*. A `1.0` on a small test set is at best "no failures observed in n cases" (see the Wilson interval in `references/statistics.md`).
- How many configs, seeds, or variants were tried in total? Are you reporting the best of many? If so, say so and correct for it.
- Are negative and inconclusive results in the same table as the positives?
- Would a skeptical reviewer's first three questions be answered in the write-up?

### 7. Report

Follow the memo skeleton in `references/templates.md`. Non-negotiables:

- **Separate sections** for *Findings (measured)* and *Hypotheses / next experiments*. Targets and goals never share a table with observations.
- Report **mean ± spread over multiple runs** (or an interval), with `n`. Point estimates alone are not enough.
- State **limitations and threats to validity** concretely: what this evidence does not show.
- Prefer plain claims scaled to the evidence ("in 5 seeds on X, A beat B by 1.2 points, 95% CI [0.3, 2.1]") over adjectives ("significantly better").

## Literature and outside claims

- Never invent citations. If you can't verify a paper exists (search or fetch it), say you can't, and don't cite it as fact.
- Check that the source actually supports the specific claim, including its setup (dataset, model size, metric). A number from a different setup is context, not a baseline.
- Distinguish "the paper reports X" (`CITED`) from "X holds" (which you would need to verify or reproduce).

## When the result is negative or unclear

Say so plainly and treat it as progress: state what was ruled out, what remains ambiguous, and the cheapest experiment that would discriminate between explanations. Don't tune the analysis until something crosses a threshold. If a decision to stop or pivot is made, write down the rule that triggered it.

## Reference map

Load only what the task needs.

| File | Read when |
|---|---|
| `references/statistics.md` | Choosing sample sizes, computing intervals, comparing methods, handling multiple comparisons, checking leakage, exploratory vs confirmatory |
| `references/ml-systems.md` | ML training/inference experiments, GPU memory and latency, sharding, KV-cache, LLM benchmarks |
| `references/other-domains.md` | Data analysis, simulation, theory with numerical checks, non-GPU performance benchmarks |
| `references/templates.md` | Writing the pre-registration, decision log, research memo, or the "please run this" handoff |
| `references/receipt-schema.json` | Defining or validating a run receipt |
| `scripts/make_receipt.py` | Creating a tamper-evident receipt (`create`) or checking one (`verify`) |

## Common failure modes to watch for in yourself

- Filling a results table because it "looks incomplete" without data.
- Treating a smoke test or mock run as evidence about the real system.
- Reporting the best seed/config as the result.
- Comparing a carefully tuned new method to an untuned baseline.
- Explaining away a failed falsification criterion after the fact.
- Trusting a user-pasted number more than its provenance allows, or, conversely, ignoring an internal inconsistency in it (sums that don't add up, accuracy that doesn't match the counts).
