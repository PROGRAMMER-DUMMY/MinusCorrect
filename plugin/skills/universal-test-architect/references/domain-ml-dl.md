# Machine Learning and Deep Learning Systems

Contents: failure topology, test groups, data tests, model behavior tests, training-code tests, serving and skew, monitoring and drift, pitfalls, example invariants.

## Failure topology

ML systems fail without errors: accuracy decays, subgroups are harmed, training and serving compute features differently, labels or future information leak into features. Behavior depends on data and cannot be fully specified in advance, so tests combine exact checks (code, data contracts) with statistical and relational checks (model behavior).

Organize tests in four groups (from Google's ML Test Score rubric): **data**, **model**, **infrastructure**, **monitoring**.

## Data tests

- Schema, ranges, null rates and category sets checked on every training and serving batch.
- **Leakage:** no feature is computed from information available only after the prediction time (target, post-outcome fields, future timestamps, aggregates over the whole dataset including test rows); split by time or entity where the real world does; duplicates do not span train and test.
- **Label quality:** label noise bounds, delayed or biased labeling, label definition changes.
- Class imbalance and rare classes present in evaluation; slices with enough samples.
- Feature pipeline unit tests: each transformation on hand-built rows including nulls, extremes and unseen categories.

## Model behavior tests (no ground truth needed)

Use the three CheckList test types:
- **Minimum functionality tests:** small hand-written cases for a capability (negation, numbers, rare entities) expecting specific outputs; they catch shortcut learning.
- **Invariance tests:** label-preserving perturbations (typos, irrelevant name or location swaps, unit changes, reordering independent fields) must not change the prediction beyond tolerance.
- **Directional expectation tests:** a change with a known effect must move the output that way (raise income: approval not lower; add a negative phrase: sentiment not more positive; larger area: price not lower).
Also: slice and subgroup performance gaps with confidence intervals; calibration (predicted probabilities match frequencies); abstention or fallback on out-of-distribution input; robustness to missing features; monotonic constraints if the business requires them; fairness metrics against documented thresholds where regulation applies.

**Differential testing:** compare against a simple baseline and against the previous model; a new model must not regress on protected slices or critical cases even if the aggregate improves. Keep a **golden set** of must-not-regress cases.

## Training and deep-learning code tests

- Shape contracts at each stage (batch, sequence, channel order, embedding width, mask broadcast); explicit assertions localize faults.
- Numerical stability: softmax with large logits (subtract max), log of zero or negative, division by zero, empty reductions, overflow and underflow, half-precision ranges; loss on perfect, uniform, confidently wrong, empty-batch and imbalanced inputs.
- Gradient flow: loss decreases on a tiny dataset; the model can overfit a single small batch; gradients are finite and not all zero; frozen parameters stay frozen.
- Determinism: seeds respected across Python, NumPy, framework and accelerator; same seed gives same result within a stated tolerance; data-loader shuffling and augmentation reproducible.
- Checkpoint save and load round-trip; resume training gives equivalent state; optimizer state included.
- Data-augmentation and preprocessing identical between train and eval except where intended.
- Do not use **neuron coverage** as a quality target: studies find that increasing it can reduce defects found and naturalness of inputs. Prefer behavior, slice and differential tests.

## Serving, skew and infrastructure

- **Training-serving skew:** score the same examples through the offline and the online feature pipelines; results must match within numeric tolerance. A mismatch is an engineering bug fixed in code, not by retraining.
- Batch-of-one vs batch-of-N consistency; ordering within a batch; padding does not change outputs.
- Input validation and schema enforcement at the endpoint; behavior on missing, extra, out-of-range, NaN and adversarial features.
- Latency and throughput at p50, p95, p99 under open-model load; cold start; memory per replica; saturation point and autoscaling margin.
- Model versioning, canary and rollback; old and new models serving side by side; feature store point-in-time correctness.
- Fallback path when the model or feature store is down.

## Monitoring and drift tests

- Distribution monitors per feature: PSI, KS test, Wasserstein distance, chi-squared for categoricals. The common PSI thresholds 0.1 (moderate) and 0.25 (major) came from credit scoring: treat them as starting points and calibrate per domain.
- With many features, correct for multiple testing; with large samples pair significance with effect size, or trivial shifts will alert constantly.
- Concept drift: track quality metrics when delayed labels arrive; use proxies (confidence, prediction distribution) meanwhile.
- Alerts fire on injected synthetic drift in a test; dashboards show slices.

## Pitfalls for a test generator

- Do not assert exact floats or exact generated text; use tolerances, statistics and properties.
- Do not evaluate on data the model or pipeline has seen; do not tune thresholds on the test set.
- Do not treat aggregate accuracy as sufficient; always include slices and worst-case examples.

## Example invariants to adapt

- I: No feature at training time uses information unavailable at serving time.
- I: Offline and online feature values for the same entity and timestamp agree within tolerance.
- I: Raising a monotonic feature never lowers the score (within numerical tolerance).
- I: Model performance on each protected or critical slice stays above its floor.
- I: A new model version does not regress on the golden set.
