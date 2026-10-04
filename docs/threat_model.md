# AIN-AI — Security Threat Model

**Standard:** STRIDE Methodology  
**Target:** Phase 1 MVP Scope  

---

## 1. System Assets & Trust Boundaries
- **User Case Data & Vault:** Confidential documents, identity tokens, family/property details.
- **Trust Kernel:** Approved legal source passages, rules engine definitions, citation verification indices.
- **AI Gateway:** Redacted prompt payloads, LLM provider communication channels.
- **Audit Ledger:** Append-only hash chain verifying data provenance and access logs.

---

## 2. Threat Analysis & Mitigations

| Threat Category | Specific Attack Vector | Mitigation in AIN-AI Architecture |
| :--- | :--- | :--- |
| **Spoofing** | Unauthorized user masquerading via stolen session token or brute-forcing OTP | Short-lived JWTs (15 min), rotating refresh tokens (30 days), max 5 OTP attempts with 15-min lockout, rate limiting by phone and IP. |
| **Tampering** | Modifying legal rules, altering document field states, or editing audit records | Immutable audit log with SHA-256 hash chaining (`prev_hash`), distinct reviewer authorization role for rule modifications. |
| **Repudiation** | Denying having accessed or shared a legal matter with another user | Every document view, consent grant, and status modification writes an unalterable audit log entry with actor ID and timestamp. |
| **Information Disclosure** | Document leakage via shared links, public S3 buckets, or logs | Short-lived signed URLs (≤5 min expiry), per-object encryption at rest, PII redaction filter on all log outputs, zero public S3 buckets. |
| **Denial of Service** | Resource exhaustion via massive PDF uploads or infinite OCR jobs | Upload file size limit (20 MB), page cap (30 pages in P1), Celery background queues with worker concurrency limits. |
| **Elevation of Privilege** | Citizen attempting to invoke admin endpoints or accessing unconsented cases | Strict `PolicyConsent.can()` authorization checks on 100% of API endpoints, automated route authorization regression tests in CI. |
| **Prompt Injection** | Adversarial user embedding hidden instructions inside scanned legal notices | Document text treated strictly as raw data; prompt isolation with system delimiters; schema-constrained JSON outputs. |
