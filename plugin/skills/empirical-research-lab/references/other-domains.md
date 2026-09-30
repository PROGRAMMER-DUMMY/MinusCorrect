# Other domains reference

Contents:
1. Data analysis
2. Simulation and numerical experiments
3. Theory and derivations with numerical checks
4. Performance benchmarks (non-GPU)
5. Field, lab, and user-collected data

Use alongside `statistics.md`. The principles in `SKILL.md` still apply: provenance labels, pre-stated hypotheses, baselines, variance, receipts.

## 1. Data analysis

- **Fix the analysis plan before looking at outcomes**: primary variables, exclusion rules, transformations, and the model. Post-hoc choices are exploratory.
- **Know the data first.** Record source, collection date, version/hash, row counts before and after each filtering step, and missingness. Report how many rows each exclusion removed and why.
- **Unit of analysis and independence.** Repeated measures per person/site/session are not independent rows. Use grouped splits, clustered or mixed-effects methods, or aggregate to the true unit.
- **Association is not causation.** Say "associated with" unless the design supports causal claims (randomization, or a credible identification strategy with stated assumptions). Name plausible confounders.
- **Check assumptions and outliers** with plots or diagnostics, and report results with and without any outlier removal. Don't drop points without a pre-stated rule.
- **Robustness:** show that the conclusion survives reasonable alternative specifications (different model, different exclusion rule, different metric). If it doesn't, that is the finding.
- **Multiple outcomes/subgroups:** count them and adjust or label as exploratory (`statistics.md` §4).
- Keep the analysis reproducible: a script or notebook that runs from raw data to every reported number, with versions pinned.

## 2. Simulation and numerical experiments

- **Verification vs validation.** Verification asks "does the code solve the equations correctly?" (convergence tests, conservation laws, analytic special cases, method of manufactured solutions). Validation asks "do the equations match reality?" (comparison to measurements). A verified simulation isn't automatically valid; state which you did.
- **Convergence:** vary step size, mesh, tolerance, or particle count, and show the result stabilizes. Report the rate if known.
- **Stochastic simulations:** run multiple independent seeds, discard burn-in with a stated rule, and report Monte Carlo error alongside the estimate. Check for autocorrelation in MCMC/time-series output (effective sample size).
- **Parameter sensitivity:** vary uncertain inputs and report how much conclusions move. Reporting one parameter set as "the answer" hides fragility.
- **Known-answer tests:** run a case with an exact solution, or a limiting regime where the answer is known, before trusting outputs elsewhere.
- **Numerical pitfalls:** floating-point precision, stiff systems, catastrophic cancellation, timestep-dependent instabilities. Check dimensional consistency and units.
- Record RNG seeds, solver settings, tolerances, and software versions in the receipt.

## 3. Theory and derivations with numerical checks

- Mark each statement as **proved** (with the proof shown or cited), **checked numerically** (with the range and count of cases; this is evidence, not proof), or **conjectured**.
- Test conjectures against small cases, edge cases, and counterexample search (random or adversarial) before investing in a proof.
- A numerical check on N cases supports a claim only within the sampled regime. State the domain sampled.
- For claimed bounds or asymptotics, check that the constants and the regime where they apply are stated, and test near the boundary of validity.
- Re-derive key steps independently (or use a symbolic tool) rather than trusting a single derivation, including your own.

## 4. Performance benchmarks (non-GPU)

- **Warmup and steady state:** discard initial iterations (JIT, caches, lazy initialization). Report how many were discarded.
- **Enough repetitions** to report median and tail percentiles, plus spread across separate process launches (not just loops within one process).
- **Control the environment:** pin CPU frequency/governor if possible, isolate cores, avoid noisy neighbors, record machine model, OS, compiler/runtime versions and flags.
- **Prevent dead-code elimination and unrealistic caching:** consume outputs, use realistic and varied inputs, and note cache state (cold vs warm).
- **Measure what users experience:** end to end where that matters, microbenchmarks where isolating a component. Say which.
- Compare against the incumbent implementation on the same machine and inputs; report relative change with an interval.
- Separate throughput from latency, and report the load (concurrency, request rate, input size) under which each was measured.

## 5. Field, lab, and user-collected data

- Record protocol, instrument versions/calibration, operator, environment conditions, and any deviations from protocol.
- Randomize or counterbalance order effects where possible; include controls and blanks.
- Estimate measurement error (repeat measurements) and propagate it to derived quantities.
- Keep raw data unedited and immutable; do cleaning in scripted steps that produce a separate cleaned file and a log of what changed.
- For human-subject or personal data, note consent/ethics and privacy handling; don't include identifiable data in artifacts or receipts.
