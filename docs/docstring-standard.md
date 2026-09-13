# Two-Category Docstring & Claim Auditing Standard

Autonomous coding agents generate authoritative, persuasive docstrings that often describe aspirational behavior rather than actual code reality. MinusCorrect audits all documentation through the **Two-Category Docstring Standard**.

---

## 1. Category 1: Operational Guarantees ("The What")

Operational Guarantees make measurable assertions regarding algorithmic complexity, concurrency safety, or architectural purity.

### High-Risk Assertions Requiring Verification
- **Complexity:** `O(1)`, `O(log n)`, `O(n)`
- **Concurrency:** `thread-safe`, `lock-free`, `reentrant`
- **Purity:** `idempotent`, `pure function`, `side-effect-free`
- **Footprint:** `zero-dependency`, `zero-allocation`

### The Rule: Automated Test Receipts
Any Category 1 claim **must include a verified test receipt** linking directly to an automated verification test in `tests/golden/` or `tests/unit/`:

```python
def get(self, key: str) -> Optional[Value]:
    """
    Retrieves item from in-memory cache in O(1) time.
    
    # verifies: tests/golden/test_cache_lru.py
    """
    ...
```

### Prohibited Marketing Superlatives
The following superlatives are banned outright across all code docstrings:
- `universal`
- `bulletproof`
- `blazing fast`
- `domain-agnostic`
- `infinitely scalable`

If true generality is out of scope, explicitly document the bounded operating scope instead of claiming unbounded behavior.

---

## 2. Category 2: Contextual Rationale ("The Why")

Contextual Rationale captures business trade-offs, historical quirks, hardware limitations, or vendor bugs that cannot be proven by automated tests alone.

### Structured Prefix Tags
All Category 2 comments must use explicit, searchable tags:

```python
# Rationale: Using 64-bit integer timestamps to avoid 2038 epoch rollover.
timestamp = int(time.time())

# Workaround: Chrome headless v122 drops WebSocket frames on rapid disconnects (Chromium issue #99482).
socket.flush_sync()

# Assumption: Ingress payloads have already undergone UTF-8 normalization at gateway.
payload_str = raw_bytes.decode("utf-8")
```

---

## 3. Zero-Friction Linter Calibration

To ensure that human developers are not burdened by administrative overhead:
1. **Calibrated Warning Default:** In local development, unverified claims emit clean `[WARNING]` notices so routine human edits are not blocked.
2. **Strict CI Enforcement:** When `STRICT_DOCSTRINGS=1` is set (or during automated pull request validation in CI), unverified claims fail the build, preventing agents from introducing unsubstantiated guarantees into production.
3. **Static Semgrep Integration:** `.semgrep/unverified-claims.yml` scans code changes for marketing superlatives and missing receipt links.
