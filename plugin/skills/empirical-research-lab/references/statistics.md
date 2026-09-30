# Statistical rigor reference

Contents:
1. Uncertainty on a single result
2. Comparing methods
3. Baselines and ablations
4. Multiple comparisons and researcher degrees of freedom
5. Leakage and contamination checklist
6. Nondeterminism
7. Exploratory vs confirmatory
8. Stopping rules
9. Snippets

These are working rules of thumb, not a substitute for a statistician when stakes are high. When the design is unusual (clustered data, time series, heavy tails), say so and choose methods that respect that structure.

## 1. Uncertainty on a single result

**Proportions (accuracy, pass@1, success rate).** Report the count, not just the rate: "17/20", not "0.85". Use a Wilson score interval; the naive normal interval fails near 0 and 1 and at small n.

- Zero failures in n trials is not "0% failure". The **rule of three**: the 95% upper bound on the failure rate is about 3/n. With n = 20, you can only say the failure rate is plausibly under ~15%.
- Wilson 95% lower bound for a perfect score is roughly n / (n + 3.84). For n = 20 that is about 0.84; for n = 100 about 0.96.
- pass@k with n samples per problem and c correct: use the unbiased estimator `1 - C(n-c, k) / C(n, k)` averaged over problems, not "did any of my k tries pass" computed from exactly k samples. Report n, k, temperature, and sampling settings.

**Continuous metrics (latency, loss, error).**
- Repeat over independent runs (different seeds, fresh processes). Report mean and standard deviation, plus a confidence interval (t-interval for small n if roughly symmetric; bootstrap otherwise).
- With fewer than 3 runs you cannot estimate spread at all; say "single run, spread unknown". Five or more is a sensible default for anything you plan to compare.
- For latency/throughput, means hide tail behavior. Report median and p95/p99 plus the number of iterations, after warmup.

**Two sources of variance.** Variation across seeds (training/initialization/sampling) and variation across test examples (finite test set). Seed variance says how stable the method is; example variance says how much the number would move on a different sample from the same distribution. Report the one relevant to the claim, and be explicit which.

## 2. Comparing methods

- Use the **same** data splits, budget, and (where meaningful) seeds for every method, and compare **paired** per-example or per-seed differences. Pairing removes much of the noise.
- Report the **difference with its interval**, not two separate intervals eyeballed for overlap. "A - B = +1.2 [0.3, 2.1]" is the claim. If the interval includes zero or a negligible effect, the honest conclusion is "no reliable difference detected", not "A is slightly better".
- Report effect size in meaningful units (points of accuracy, milliseconds, percent), alongside any p-value. A tiny p-value on a trivial effect isn't a result; a large effect with wide interval is a lead, not a conclusion.
- Decide before running what difference would matter practically (the smallest effect of interest). It determines how many runs you need.

**Rough sample sizing.** To detect a difference `d` between two paired methods when per-run standard deviation of the difference is `s`, you need on the order of `n ≈ 8 (s/d)^2` runs for ~80% power at 5% two-sided significance. If `s ≈ d`, that is about 8 runs; if `s` is twice `d`, about 32. Use a proper power calculation for anything important.

## 3. Baselines and ablations

- **Trivial baselines** show the floor: random/chance, majority class, previous value, linear model, simple heuristic, an untrained/randomly initialized model. If the new method barely beats these, the metric or task may be broken.
- **Strong baselines** show whether the idea adds anything over what already exists. Give them equal tuning effort and equal compute; report the budgets. A well-tuned simple baseline often erases claimed gains.
- **Ablations** remove or replace one component at a time to show which part causes the gain. Change one thing per ablation. Report all of them, including the ones where nothing changed.
- **Controls:** shuffled labels (should give chance), random-feature or noise input, and a known-answer/planted-signal test. These catch pipeline bugs that no amount of statistics will.

## 4. Multiple comparisons and researcher degrees of freedom

Every config, metric, subset, seed, or prompt variant you try is another lottery ticket. Best-of-many overstates real performance.

- Keep a **count of everything tried** and report it. "Best of 40 configs" is a different claim from "the one config we planned".
- Tune on validation data only; touch the test set once, for the final chosen configuration. If you peek and change something, the test set is now validation data; say so and, if possible, get a fresh one.
- When testing many hypotheses/metrics, adjust: Holm-Bonferroni (simple, valid), or Benjamini-Hochberg if controlling false discovery rate among many exploratory tests is appropriate.
- Don't slice the data after the fact until a subgroup shows the effect. Subgroup analyses found post hoc are exploratory hypotheses.

## 5. Leakage and contamination checklist

Run this before trusting any good result.

- Train/val/test split done **before** preprocessing, feature selection, normalization statistics, deduplication, or augmentation? Anything fit on all data leaks.
- Near-duplicates across splits (same document, same user, same patient, same problem in different wording)? Split by group/entity, not by row, when rows are correlated.
- Time series: only past information used to predict the future; splits respect time order.
- Target leakage: any feature that encodes the label or is only known after the outcome.
- Hyperparameters, prompts, or thresholds chosen while looking at test results.
- **Benchmark contamination** (LLMs and pretrained models): could benchmark items or their solutions be in pretraining/fine-tuning data? Look for verbatim overlap (n-gram search), check whether the model reproduces the benchmark's exact formatting or canary strings, and test on freshly written or post-cutoff items. Contamination can't be ruled out for public benchmarks; state that.
- Evaluation harness shortcuts: same prompt templates in few-shot examples and test items, answer-position or length biases, metrics that can be gamed by trivial outputs.

## 6. Nondeterminism

Fixing a seed does not always give bitwise-identical results (non-deterministic GPU kernels, parallel reductions, data loader ordering, library versions). So:

- Set and record seeds for every RNG in play (Python, NumPy, framework, data loader workers), and note which deterministic-mode flags you enabled.
- Even with all of that, treat run-to-run variation as real and measure it with repeats. Don't rely on a single "reproduced" run to claim determinism.
- Record library versions, hardware, and driver versions; results can shift across them.

## 7. Exploratory vs confirmatory

| | Exploratory | Confirmatory |
|---|---|---|
| Hypothesis | Formed while looking at data | Stated before running |
| Purpose | Generate ideas | Test a specific claim |
| Statistics | Descriptive; p-values not meaningful | Intervals/tests valid as planned |
| Reporting | "We observed X; this suggests..." | "We predicted X; result was Y" |

Both are legitimate. Mixing them up is the problem. Anything that surprised you and got investigated afterwards is exploratory, and needs a confirmatory follow-up on new data before it is called established.

## 8. Stopping rules

- Fix the number of runs/samples in advance. Running until the result "becomes significant" (optional stopping) inflates false positives.
- If you plan sequential looks, use a method designed for it and say so.
- Decide in advance when to abandon a direction (e.g., "if after 3 seeds the effect is below X, stop"), and record the trigger in the decision log.

## 9. Snippets

Wilson interval (proportion):

```python
from math import sqrt

def wilson(k, n, z=1.96):
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    denom = 1 + z**2 / n
    centre = (p + z**2 / (2 * n)) / denom
    half = z * sqrt(p * (1 - p) / n + z**2 / (4 * n**2)) / denom
    return (centre - half, centre + half)
```

Bootstrap confidence interval for a mean (or any statistic):

```python
import numpy as np

def bootstrap_ci(x, stat=np.mean, n_boot=10_000, alpha=0.05, seed=0):
    rng = np.random.default_rng(seed)
    x = np.asarray(x)
    boots = np.array([stat(rng.choice(x, size=len(x), replace=True))
                      for _ in range(n_boot)])
    return np.quantile(boots, [alpha / 2, 1 - alpha / 2])
```

Paired difference interval (per-example or per-seed scores `a` and `b` aligned by index):

```python
diff = np.asarray(a) - np.asarray(b)
lo, hi = bootstrap_ci(diff)
print(f"mean diff = {diff.mean():.4f}, 95% CI [{lo:.4f}, {hi:.4f}], n = {len(diff)}")
```

Unbiased pass@k for one problem (n samples, c correct):

```python
from math import comb

def pass_at_k(n, c, k):
    if n - c < k:
        return 1.0
    return 1.0 - comb(n - c, k) / comb(n, k)
```
