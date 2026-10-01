# Evidence Ledger

What the skill's rules rest on, and how much to trust each item. Quote numbers only from this file or from the user's own data. Research was done by web search in October 2026; items marked "background" come from well-known literature and general engineering practice and were not re-verified in that session.

Contents: authority levels, ledger by topic, claims to treat with caution, known gaps.

## Authority levels

- **A**: peer-reviewed paper, standard, or official engineering write-up by the system's owner.
- **B**: reputable practitioner documentation or vendor engineering blog.
- **C**: secondary summary, newsletter, or skill-registry or blog post; use as a heuristic and verify.

## Ledger

| Topic | Finding used by the skill | Source | Level |
|---|---|---|---|
| Coverage vs effectiveness | About 31,000 generated suites across five systems (up to about 724K lines): low-to-moderate correlation between coverage and effectiveness once suite size is controlled; stronger coverage types add nothing; coverage is useful to find under-tested code, not as a target | Inozemtseva and Holmes, ICSE 2014 | A |
| Mutants vs real faults | 357 real faults in five programs: detecting mutants correlates with detecting real faults independent of coverage; about 73 percent of real faults coupled to mutants, about 27 percent not | Just et al., FSE 2014 | A |
| Mutation at scale | Surviving mutants used as concrete test goals; mutants coupled to real faults | Google mutation-testing papers (Petrovic et al.) | A |
| LLM test oracles | LLM-generated tests tend to capture actual rather than expected behavior; buggy code can mislead the model into asserting faulty behavior; requirement-derived oracles align better with intended behavior | 2025-2026 empirical studies on LLM unit-test generation | A/B |
| LLM test filtering | At Meta, TestGen-LLM: about 75 percent of generated test classes built, 57 percent passed reliably, 25 percent increased coverage; filters on build, repeated passes and coverage gain | Meta, "Assured LLM-Based Software Engineering" / TestGen-LLM | A |
| Flakiness | About 1.5 percent of test runs flaky at Google; almost 16 percent of tests show some flakiness; emulator and WebDriver tests flakier than small tests; flakiness compounds across large suites | Google Testing Blog and related publications | A |
| Test design at Google | Prefer testing through public APIs and behavior; brittle tests fail on unrelated changes; roughly 80/15/5 unit/integration/end-to-end guideline | Software Engineering at Google | A/B |
| Distributed system testing | Jepsen black-box method: concurrent ops plus faults plus history checker; separates safety from availability failures | jepsen.io analyses | A/B |
| Deterministic simulation | Seeded single-thread simulation of time, network and disk reproduces failures from a seed; used by FoundationDB and TigerBeetle | Project documentation and talks | B |
| Formal methods | TLA+ used on 10 large systems at AWS found subtle bugs missed by other methods; one data-loss bug had a 35-step shortest trace | Newcombe et al., CACM 2015 | A |
| Combinatorial testing | Pairwise detects roughly 50 to 97 percent of faults in studies; 67 to 98 percent of failures involve 1 to 3 parameters; failures needing more than 6 are rare; constraints matter | NIST (Kuhn et al.) | A |
| Retries and timeouts | Slow calls hold resources; retries add load to failing systems; per-attempt timers from one deadline; token-bucket retry limits; retry at one layer; amplification across layers | AWS Builders' Library | A |
| Chaos engineering | Steady-state hypothesis; vary real-world events; minimize blast radius; start small | Principles of Chaos Engineering | A |
| Idempotency | Three failure phases; key reuse with different parameters rejected; pitfalls: key scope, caching failures | Stripe API documentation; library docs | B |
| Contract testing | Consumer-driven contracts, provider verification, deployment gate; do not stub above request validation; exact matchers are brittle | Pact documentation | B |
| Schema and DB evolution | Backward/forward/full compatibility; expand-migrate-contract; rollout must work for all running versions | Schema registry docs; practitioner references | B/C |
| Load testing | Open vs closed model; coordinated omission; do not average percentiles; saturation via staged ramp | HdrHistogram/wrk2 literature; load-testing docs | B |
| Fuzzing | OSS-Fuzz: over 1,000 bugs in about five months (264 potential security vulnerabilities); also logic bugs; timeouts and out-of-memory findings are flaky; later study of 23,907 bugs in 316 projects | Google OSS-Fuzz papers and blog | A |
| Neuron coverage | Higher neuron coverage can reduce defects detected and input naturalness; one random input can achieve 100 percent code coverage with under 10 percent neuron coverage | Harel-Canada et al., FSE 2020; DeepXplore | A |
| ML test rubric | 28 tests in four groups: data, model, infrastructure, monitoring | Breck et al., "The ML Test Score" | A |
| Behavioral NLP testing | Minimum functionality, invariance, directional expectation tests; invariance and directional work without labels | Ribeiro et al., ACL 2020 (CheckList) | A |
| Training-serving skew and PSI | Skew is an engineering bug; PSI cutoffs 0.1 and 0.25 conventional from credit scoring, need calibration; correct for multiple testing | ML-ops practitioner docs | B/C |
| LLM-as-judge | Position, verbosity and self-enhancement biases; strong judges above 80 percent agreement with humans on general chat; reference-guided grading helps | Zheng et al., NeurIPS 2023 (MT-Bench) | A |
| LLM security | Prompt injection is the top-listed risk; indirect injection via retrieved or tool content; excessive agency; unbounded consumption | OWASP Top 10 for LLM Applications (2025) | A |
| API security | Broken object-level authorization ranks first; top three are authorization problems | OWASP API Security Top 10 (2023) | A |
| Risk prioritization | Risk Priority Number replaced by Action Priority in the 2019 AIAG-VDA FMEA handbook; equal RPNs can hide very different risk profiles | AIAG-VDA FMEA Handbook | A/B |
| Test documentation | Test case fields: identifier, objective, priority, traceability, preconditions, inputs, expected results | ISO/IEC/IEEE 29119-3 | A |
| WCAG 2.2 | Nine new success criteria, 4.1.1 removed; AA: 2.4.11, 2.5.7, 2.5.8, 3.3.8; A: 3.2.6, 3.3.7 | W3C WCAG 2.2 | A |
| Streaming | Some sinks at-least-once so writes must be idempotent; watermark must cover tolerated lateness | Spark/Flink documentation | A/B |
| Post-mortems | Knight Capital 2012: partial deploy plus reused flag, about 440 million dollars in about 45 minutes, no kill switch. Cloudflare 2019: single rule with regex backtracking exhausted CPU globally. AWS Kinesis 2020: capacity addition tripped OS thread limit | SEC order and commentary; Cloudflare and AWS post-event summaries | A |
| Mobile offline | Queue persistence, ordering, conflict resolution, silent data loss as primary failure | Vendor and practitioner blogs | C |
| Boundary datasets | Big List of Naughty Strings; falsehoods-programmers-believe lists | Public repositories and essays | B/C |
| DL unit-test patterns | Shape, numeric stability, overfit-one-batch, seed tests | Practitioner posts and general practice | C (background) |

## Claims to treat with caution

- Percentages like "70 percent of effort on boundaries" circulate informally; no supporting source was found, so the skill states the qualitative principle only.
- The amplification figure for layered retries (for example 243x for three retries across five layers) is simple arithmetic from a secondary summary; the principle is solid, the number is illustrative.
- Mobile, LLM-eval operational numbers (for example "start with 50 to 100 golden cases", "3 to 5 runs") are community practice, not research findings.
- Priority lookup in Step 3 of the skill is a heuristic modeled on action-priority tables, not an industry standard.
- Many vendor pages are marketing; prefer primary sources when citing outside this skill.

## Known gaps

Not researched in depth: hardware and embedded systems, game testing, real-time and safety-critical certification (DO-178C, ISO 26262), accessibility automation limits in detail, test-data management and synthetic data generation, long-term industrial adoption of formal verification beyond AWS, and domain regulations (HIPAA, PCI DSS, GDPR) as test sources. Extend `references/` with a new `domain-*.md` file when needed and add a routing row in `SKILL.md`.
