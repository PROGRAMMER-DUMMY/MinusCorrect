# LLM Applications, RAG and Agents

Contents: failure topology, eval design, scoring methods, judge biases, RAG, structured output, agents and tools, security, cost and operations, example invariants.

## Failure topology

The model still answers, the answers look plausible, latency and token use are normal, and quality has quietly regressed or an attacker has steered behavior. Output is non-deterministic, so tests assert *properties and rates*, not exact strings. Treat evals as unit tests for non-deterministic output, plus security tests for an input channel that mixes instructions with data.

## Eval design

- **Golden set:** curated (input, expected behavior) pairs from real usage, including hard and previously failed cases, not only cases that already work. Start with 50 to 100 cases for core behaviors and grow from production failures.
- **Three case types:** golden regression cases, edge and adversarial cases, and a holdout never used for prompt tuning.
- **Run multiple times** per case (for example 3 to 5) to measure variance; report pass *rates* with confidence intervals and compare to the last known-good baseline before blocking or shipping a change.
- **Regression gate in CI:** any change to prompt, model, retrieval settings or tools reruns the suite; per-metric thresholds; block on regression. Include cost and latency as metrics so a fix does not quietly double spend.
- **Online checks:** sample live traffic for scoring and human review; turn failures into new eval cases.

## Scoring methods (use the cheapest that is valid)

1. **Deterministic assertions:** JSON parses and matches schema, required fields present, forbidden strings absent, tool called with valid arguments, citations resolve, length and format limits.
2. **Heuristic and reference checks:** exact match or normalized match when one answer is right; contains-key-facts; numeric tolerance.
3. **LLM-as-judge:** for open-ended quality (helpfulness, faithfulness, tone). Use a structured rubric, reasoning before score, and **reference-guided grading** when a reference answer exists.
4. **Human review:** to build and calibrate the golden set and to spot-check the judge.

**Known judge biases:** position bias (favors an answer because of where it appears), verbosity bias (favors longer answers), self-enhancement bias (favors its own family's outputs), and limited reasoning on hard math or code. Mitigate by swapping answer order and requiring agreement across both orders, length-controlled rubrics, a judge from a different model family than the system under test, and periodic human agreement checks. Strong judges can agree with humans on the order of 80% or more on general chat quality, but validate on your domain.

## RAG (test retrieval and generation separately)

- **Retrieval:** recall@k, precision@k, MRR, nDCG on labeled queries; queries with no relevant document (must abstain); near-duplicate and outdated documents; access control respected at retrieval (a user must never retrieve documents they cannot read); chunk-boundary cases where the answer spans two chunks.
- **Generation given context:** faithfulness (claims supported by retrieved text), answer relevance, handling of contradictory sources, refusal when context is insufficient, citation correctness.
- **Index lifecycle:** reindex or document update changes answers as expected; deleted documents stop appearing; embedding model upgrade does not silently change neighbors.

## Structured output and tools

- Malformed JSON, extra or missing fields, wrong types, enum violations, truncated output at the token limit; retry or repair policy bounded and tested.
- Tool calls: invalid arguments, missing permissions, tool error or timeout, tool returning huge or malicious content; idempotency of tools with side effects; limits on tool-call count and recursion depth.
- Agents: goal drift over long runs, loops, repeated failing calls, partial completion and resume, state persistence between steps, human-approval gates actually block, and the final answer reflects real tool results (no fabricated success).

## Security (OWASP LLM Top 10 mindset)

- **Prompt injection, direct and indirect:** run every injection technique against *every input boundary*: chat input, uploaded files, retrieved documents, web pages, tool outputs, emails. Indirect injection through retrieved or tool content is the hard case and has led to zero-click data exfiltration in real products.
- Sensitive-information disclosure, system-prompt leakage, cross-user memory or context leakage, improper output handling (model output rendered as HTML, executed as code or SQL, or passed to a shell without sanitization).
- **Excessive agency:** the model can only call tools and scopes it needs; destructive actions need confirmation; least-privilege credentials; test that an injected instruction cannot trigger a privileged action.
- Data and model poisoning via training or retrieval corpora; supply-chain checks on models, plugins and MCP servers.
- Unbounded consumption: max tokens, max tool calls, rate limits, cost caps, adversarial prompts that maximize tokens or loops.
- Tenancy: vector store and cache keys include tenant; BOLA-style tests on any ID the model can be induced to request.

## Safety and quality behaviors

Refusal correctness (should refuse, should not over-refuse), harmful-content policy cases, bias and fairness probes with paired inputs differing only in a protected attribute, multilingual and code-switching inputs, very long inputs near the context limit, empty and adversarial whitespace, and instruction conflicts between system and user messages.

## Operations

Prompt and model versions pinned and logged per request; rollback path; provider outage and rate-limit fallback; latency percentiles including time to first token; drift monitoring on input topics and output quality; PII redaction in logs and traces.

## Example invariants to adapt

- I: Every factual claim in an answer is supported by a retrieved document the user is authorized to read (faithfulness above threshold).
- I: Output always parses against the declared schema, or the system returns a defined error after at most N repairs.
- I: No instruction found in retrieved or tool content can cause a tool call outside the user's granted scope.
- I: Quality metrics on the golden set stay within tolerance of the baseline after any prompt, model or retrieval change.
