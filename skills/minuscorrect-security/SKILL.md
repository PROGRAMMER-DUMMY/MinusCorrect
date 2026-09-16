---
name: minuscorrect-security
description: Fused security review and adversarial vulnerability verification skill. Combines cognitive dataflow analysis across 10 security domains (secrets, input validation, SQLi, XSS, CSRF, auth/RLS, sensitive logging, crypto, dependencies) with executable proof-of-concept test generation for MinusCorrect closed-loop remediation.
---

# MinusCorrect Security Review & Exploit Contract Skill

This skill fuses upstream cognitive vulnerability analysis (tracing data flows from untrusted inputs to dangerous sinks) with downstream adversarial verification (generating reproducible acceptance contracts in `tests/staging/test_sec_<id>.py` for MinusCorrect supervision).

## When to Activate

- Adding authentication, authorization, or Row-Level Security (RLS)
- Handling untrusted user inputs, query parameters, or file uploads
- Creating new API endpoints or webhook handlers
- Managing secrets, credentials, or environment variables
- Auditing dependencies or investigating potential CVEs
- Reviewing code for injection flaws, XSS, SSRF, or IDOR vulnerabilities

## The 10-Domain Security Checklist

### 1. Secrets Management
- **Rule:** Never hardcode secrets, tokens, or private keys.
- **Verification:** Ensure all credentials reside in environment variables. Verify that `.env*` files are excluded in `.gitignore` and `.dockerignore`.

### 2. Input Validation
- **Rule:** Validate and constrain all untrusted inputs at the boundary using strict schemas (e.g. Zod in TypeScript, Pydantic in Python).
- **Verification:** Enforce whitelist validation, strict length bounds, and file upload restrictions (size, MIME type, extension).

### 3. Injection Prevention (SQLi, Command Injection, Template Injection)
- **Rule:** Never concatenate or interpolate user input into database queries or shell execution strings.
- **Verification:** Use parameterized queries, ORM boundary models, and `subprocess.run(args_list)` without `shell=True`.

### 4. Authentication & Access Control
- **Rule:** Enforce principle of least privilege. Store tokens in `httpOnly`, `Secure`, `SameSite=Strict` cookies (never `localStorage`).
- **Verification:** Verify authorization checks before performing state mutations. Ensure Row Level Security (RLS) policies are active.

### 5. Cross-Site Scripting (XSS) & Content Security Policy
- **Rule:** Sanitize all rendered HTML using established libraries (e.g. DOMPurify). Configure robust CSP headers.
- **Verification:** Ensure no unescaped user-controlled input reaches template rendering or `dangerouslySetInnerHTML`.

### 6. Cross-Site Request Forgery (CSRF)
- **Rule:** Protect all state-changing endpoints with CSRF validation or strict SameSite cookie enforcement.

### 7. Rate Limiting & Resource Throttling
- **Rule:** Apply window-based rate limiting on all public API endpoints and aggressive limits on expensive operations (search, auth, AI prompts).

### 8. Sensitive Data & Log Exposure
- **Rule:** Redact PII, auth headers, and credit card numbers from application logs and APM telemetry.
- **Verification:** Return generic error messages to users; never leak internal tracebacks or database schemas.

### 9. Cryptography & Randomness
- **Rule:** Use modern cryptographic primitives (Argon2id, bcrypt, AES-GCM). Never use MD5, SHA1, or predictable PRNGs (`random.random()`) for security tokens.

### 10. Dependency Hygiene & Lockfiles
- **Rule:** Always commit lockfiles (`package-lock.json`, `poetry.lock`). Pin exact major/minor dependencies and run vulnerability audits (`npm audit`, `pip-audit`).

---

## Adversarial PoC Contract Generation

When a potential vulnerability is identified, do not merely report text. Synthesize an executable acceptance contract proving the flaw:

1. **Author Staged Contract:** Create `tests/staging/test_sec_<id>.py`:
   ```python
   def test_unauthenticated_access_blocked():
       response = client.get("/api/v1/user/sensitive-data")
       assert response.status_code == 401
   ```
2. **Execute Under MinusCorrect Supervision:**
   ```bash
   minuscorrect run --session-id sec-fix-<id> -- pytest tests/staging/test_sec_<id>.py
   ```
3. **Verify Blast-Radius:**
   Validate that the patch only touches implementation code, avoids `conftest.py` tampering, and generates a clean Draft PR:
   ```bash
   minuscorrect pr --session-id sec-fix-<id>
   ```
