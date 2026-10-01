# Test Quality Rubric (self-critique before output)

Contents: 1 Hard gates, 2 Scored criteria, 3 Verdict rules, 4 Set-level checks, 5 Worked examples, 6 Fast checklist.

Apply to every P0 and P1 candidate. The point is to catch low-value filler and circular tests before the user sees them. Hard gates are pass/fail; do not average them away with high scores elsewhere.

## 1. Hard gates (any failure means REVISE or DROP)

| Gate | Question | Typical failure |
|---|---|---|
| G1 Oracle | Is the expected result sourced from a spec, invariant, reference, or confirmed decision, and is the source named? | Expected value copied from what the code returns |
| G2 Bug-catching | Can you name the realistic bug or mutation this test kills, and would the test actually fail if it were injected? | Test executes a line but asserts nothing about its effect |
| G3 Determinism | Are clock, randomness, network, ordering, shared data and environment controlled? | Sleeps, real time, shared fixtures, order dependence |
| G4 Behavior focus | Does it assert observable behavior or a contract rather than private structure? | Asserts that a mock was called N times, exact log text, internal method names |
| G5 Diagnosability | Would the failure message say which invariant broke and give a lead to the cause? | `expected true, got false` |
| G6 Non-redundancy | Does it differ from other tests in invariant, equivalence class or mutation? | Five tests of the same boundary class |

## 2. Scored criteria (1 to 5, for tests that pass the gates)

| Criterion | 1 | 3 | 5 |
|---|---|---|---|
| Invariant strength | Checks it runs without error | Checks one output field | States a business or safety invariant that must hold under stress |
| Specificity and executability | Vague ("works correctly") | Steps clear, data partly implied | Exact preconditions, inputs and assertions; an engineer or harness can run it unambiguously |
| Negative-space value | Happy path | Single invalid input | Targets boundary, ordering, duplication, partial failure, or hostile input with a rationale |
| Blast-radius clarity | No impact stated | Generic impact | Names the failure mode and the business or engineering consequence concretely |
| Maintainability | Breaks on harmless refactors | Some coupling to internals | Survives refactors; one behavior per test; clear name |

## 3. Verdict rules

- Any hard gate fails: **REVISE** (state what to fix); if it cannot be fixed (no oracle exists, bug is imaginary), **DROP**.
- All gates pass and any score is 1 or 2: **REVISE**.
- All gates pass and every score is 3 or more: **KEEP**. Prefer to ship tests with mostly 4s and 5s for P0.
- Never present a test labeled P0 that you have not run through G1 and G2.

## 4. Set-level checks

1. **Risk alignment:** every P0 failure mode in the risk map has at least one test; the number of tests per area follows risk, not file size.
2. **Dimension coverage:** each applicable dimension of the eight has coverage, or an explicit reason it is out of scope.
3. **Technique diversity:** more than boundary tests alone; properties, state, fault injection, contracts or metamorphic relations used where the failure type calls for them.
4. **Negative-space weight:** most tests target boundaries, invalid input, failure and concurrency; happy path is a minority.
5. **Oracle mix is honest:** characterization tests are labeled; suspected defects are reported separately.
6. **Determinism plan:** the output lists the controls needed (fake clock, seeded random, isolated data, stubbed network).
7. **Size sanity:** no padding; duplicates merged; tests ordered by priority.
8. **Do not optimize for coverage percentage or test count.** Use coverage only to find untested areas, never as a goal.

## 5. Worked examples

**Low value (fails G1, G2, G4):**
"Test that `process_payment()` returns success for a valid card. Assert `mock_gateway.charge` was called once."
Why it fails: the expected result is whatever the code does; a mock-call assertion couples to implementation; many bugs (double charge on retry, wrong amount, lost update) would still pass.

**High value (KEEP):**
`TC-PAY-007 Duplicate webhook is idempotent` - Oracle: payments contract, section on idempotency. Pre: order O-1 pending, empty ledger. Action: deliver webhook `payment.succeeded` for O-1 five times, three concurrently. Expect: exactly one ledger entry of the order amount; order state `paid`; all deliveries get 2xx; metric `webhook_duplicate` increments four times. Failure message: "I1 violated: more than one ledger entry for payment P-9 (found 2)". Kills: removed dedup check, dedup keyed on delivery ID instead of event ID, non-atomic check-then-insert. Blast radius: customers double charged or double credited; reconciliation breaks.

**Repair example:** "Search returns relevant results" becomes a metamorphic test: for a query q and its same-meaning rewrite q2 (reordered words), the top-5 result sets overlap at least 80 percent (oracle: product requirement on query-order invariance; kills: tokenizer treats word order as meaningful; determinism: fixed index snapshot).

## 6. Fast checklist before sending

- Every test: oracle named? bug named? mutation would fail it? deterministic? message diagnostic? unique?
- Every set: P0 coverage, dimensions, mixed techniques, honest labels, assumptions listed, residual risk listed.
