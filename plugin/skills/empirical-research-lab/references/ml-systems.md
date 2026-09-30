# ML systems reference (training, inference, GPU benchmarking)

Contents:
1. Verify against real configs
2. Memory envelope (formulas are lower bounds)
3. Parallelism and topology
4. Telemetry capture
5. Silent defaults that corrupt benchmarks
6. LLM and model-quality evaluation
7. Hybrid / multi-engine architectures
8. Hermetic smoke test for ML

Every formula below produces a `DERIVED` estimate. Validate it against a measured run (`MEASURED`) before relying on it. If you cannot run, present the estimate with its assumptions and mark measured cells `PENDING_RUN`.

## 1. Verify against real configs

Before a run, read the actual artifacts rather than relying on memory or a model card's marketing summary:

- `config.json` (or equivalent): layer count, hidden size, attention heads, KV heads, head dimension, vocab size, tied embeddings, max sequence length, dtype.
- Layer types, if the architecture is hybrid: which layers are full attention, which are linear/recurrent/state-space/MoE. Only some layers may carry a KV cache.
- Checkpoint: file sizes, shard list, dtype/quantization actually stored, parameter count computed from the loaded state dict (not from the model's name; "27B" is a label).
- Tokenizer and chat template version, since these change results.

Record the config's hash in the receipt.

## 2. Memory envelope

Treat all of these as **lower bounds** for planning; measure the real peak.

**Weights.**
```
weight_bytes ≈ n_params × bytes_per_element
```
bf16/fp16 = 2 bytes, fp32 = 4, int8 = 1, 4-bit ≈ 0.5 plus overhead. This is not exact: quantization scales/zero-points, tied vs untied embeddings, layers kept in higher precision, and framework/CUDA context (often several hundred MB per device) all shift the total.

**KV cache (per token, attention layers only).**
```
kv_bytes_per_token = 2 × n_attn_layers × n_kv_heads × head_dim × bytes_per_element
kv_total_bytes     = kv_bytes_per_token × seq_len × batch_size
```
The leading 2 is for keys and values. Use the number of layers that actually keep a KV cache (`n_attn_layers`), not total layers, in hybrid models. With grouped-query attention `n_kv_heads` is smaller than the number of query heads. Sliding-window layers cap the cache at the window length.

**Inference total** ≈ weights + KV cache + activations/workspace + framework overhead + fragmentation headroom. For long sequences or large batches the KV cache can dominate.

**Training total** is much larger than weights alone. A common mixed-precision Adam rule of thumb is about 16 bytes per parameter for weights, gradients, fp32 master weights, and two optimizer moments (roughly 2 + 2 + 4 + 4 + 4), before activations. Activation memory depends on batch size, sequence length, and checkpointing/recomputation, and is usually best measured. Sharded optimizers (ZeRO/FSDP) divide the model-state portion across devices but not activations.

## 3. Parallelism and topology

- Ask how devices are connected before choosing a strategy. Without a fast interconnect (NVLink/NVSwitch), for example on many cloud notebook or PCIe-only nodes, tensor parallelism with per-layer all-reduces can be bandwidth-bound and slow; pipeline parallelism or simple layer-wise device placement usually communicates less.
- Layer-wise "balanced sharding" (naive device_map) makes only one device busy at a time; it fits a model in memory but doesn't speed it up. Say which you are doing.
- Report the actual topology (`nvidia-smi topo -m`) in the receipt when it affects the result.
- Don't claim a speedup from parallelism without a single-device (or smaller-scale) baseline measured under the same conditions.

## 4. Telemetry capture

Capture automatically and store in the receipt:

- Device names, counts, total memory, driver and CUDA versions, framework versions.
- **Peak memory:** call `torch.cuda.reset_peak_memory_stats()` before the measured region, then read `torch.cuda.max_memory_allocated()` (tensors) and `torch.cuda.max_memory_reserved()` (allocator pool). They differ; say which you report. `nvidia-smi` shows a larger figure that includes the CUDA context.
- **Timing:** GPU work is asynchronous. Call `torch.cuda.synchronize()` before starting and stopping the timer (or use CUDA events), use `time.perf_counter()`, run **warmup** iterations that are discarded, then run enough timed iterations to report median, p95/p99, and count.
- State exactly what was timed: batch size, input/output lengths, whether it includes tokenization, data loading, host-device transfer, and first-token vs steady-state.
- Throughput: define the unit (tokens/s of prefill vs decode vs both) and whether padding tokens are counted.
- Host RAM, disk read speed, and data-loader throughput when they could be the bottleneck.

## 5. Silent defaults that corrupt benchmarks

Check each explicitly and record the setting used:

- **KV cache:** for a non-autoregressive pass (classification/encoding/scoring with a causal backbone), confirm `use_cache=False` (or the framework equivalent) so cache structures aren't allocated. To back a "zero cache" claim, measure memory with and without it.
- **Train vs eval mode:** `model.eval()` and `torch.no_grad()`/`inference_mode()` for evaluation. Dropout or batch-norm in train mode silently changes outputs.
- **Reasoning/"thinking" modes:** some models default to emitting chain-of-thought tokens or use a chat template that toggles them (e.g., an `enable_thinking` flag). This changes latency, token counts, and accuracy. Set it deliberately and record it.
- **Precision and kernels:** dtype, attention implementation (eager/SDPA/flash), quantization method, and `torch.backends` flags (TF32, deterministic mode).
- **Decoding parameters:** temperature, top-p/top-k, max new tokens, stop sequences, number of samples, seed. Greedy vs sampled results are different claims.
- **Batching and padding side**, and whether the same prompt template is used for all methods compared.
- **Compilation/first-run effects:** `torch.compile`, cuDNN autotune, and lazy CUDA init inflate the first iterations; exclude them via warmup.
- **Caching layers you didn't intend:** prompt caches, dataset caches, or a memoized function returning stale results.

## 6. LLM and model-quality evaluation

- Report `n` (number of problems), samples per problem, and interval (Wilson for proportions; see `statistics.md`). Pass@1 = 1.0 on 20 problems is "no failures in 20", not a perfect system.
- Use a fixed, versioned evaluation harness and prompt template; compare methods under identical prompts and decoding settings.
- Check contamination (`statistics.md` §5). Prefer held-out or freshly constructed items for headline claims.
- Grade with a metric you have validated: spot-check a sample of "correct" and "incorrect" verdicts by hand, since parsers and regex graders fail silently.
- Structural validity checks (for generated code or structured output: parses with an AST/JSON parser, brackets balanced, schema valid) are cheap and independent of model scale. Report validity **before and after** any repair/healing step separately; a repair pass that fixes syntax should not be credited to the model.
- Semantic correctness (tests pass, answer matches) is a separate metric from structural validity.
- Compare against a baseline model of similar size and a trivial or non-ML baseline where one exists.

## 7. Hybrid / multi-engine architectures

For systems with multiple components (e.g., a fast triage/classification path plus a slower generative path):

- Evaluate each path on its own metric, and the combined system end to end, including the cost of routing errors.
- Measure memory and latency per path; don't assume the fast path's cost from the slow path's numbers.
- Keep component-level claims (e.g., cache-free triage) separate from system-level claims (overall accuracy/latency).
- State the architectural contract explicitly: which layers/heads are shared, where interfaces (grafts, adapters, projections) sit, and their tensor shapes; validate shapes at each interface in the smoke test.

## 8. Hermetic smoke test for ML

Before dispatching to a large run:

- Instantiate a tiny version (for example 2 layers, small hidden size, short sequence) and run forward, backward, one optimizer step, save/load, and the eval metric code end to end on CPU or a single small GPU.
- Assert shape transitions across layers and at every graft/interface.
- Overfit a single small batch: loss should fall close to zero. If it doesn't, something is broken.
- Sanity-check metric code with known inputs (perfect predictions give the maximum score, random predictions give chance).
- Run a shuffled-label control: performance should collapse to chance.
- Confirm the receipt writer works and produces a valid receipt with a `smoke_test` note, and never let a smoke-test receipt be mistaken for a full-scale result.
