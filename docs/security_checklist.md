# Security Checklist & Controls Audit (Sprint S9 Hardening)

This document tracks platform security controls, cross-cutting requirements (X-001 through X-008), and verification status as of Sprint S9.

## 1. Security Controls Verification Matrix

| Control ID | Control Name | Implementation Details | Status | Verified By / Evidence |
|---|---|---|---|---|
| **SEC-01** | **Fail-Closed Secrets in Production** | `get_jwt_secret()`, `get_otp_pepper()`, `get_link_token_pepper()`, `_get_draft_storage_key()` strictly raise `RuntimeError` if unset or using known dev defaults when `DEV_MODE=false`. Mock SMS provider is strictly refused. | **TESTED** | `tests/s9/test_s9_hardening.py::test_c0_fail_closed_secrets_in_production`, `test_g9_otp_leakage_and_mock_refusal_when_dev_mode_false` |
| **SEC-02** | **HTTP Security Headers** | Middleware enforces CSP (`default-src 'self'`, no external hosts, no `unsafe-eval`, `frame-ancestors 'none'`), `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: strict-origin-when-cross-origin`. | **TESTED** | `tests/s9/test_s9_hardening.py::test_g4_security_headers_and_cache_control_enforcement` |
| **SEC-03** | **No-Store Cache Control on Shared Data** | All `/s/*`, `/api/v1/s/*`, and `/consents` endpoints set `Cache-Control: no-store, no-cache, must-revalidate, max-age=0` and `Pragma: no-cache`. | **TESTED** | `tests/s9/test_s9_hardening.py::test_g4_security_headers_and_cache_control_enforcement`, `test_ac_m08_2_revocation_blocks_access_within_60s_cached_pages_signed_urls` |
| **SEC-04** | **Link Token Entropy & Storage (HMAC-SHA256)** | Tokens generated with `secrets.token_urlsafe(32)` (256 bits entropy). Stored exclusively as **HMAC-SHA256 with LINK_TOKEN_PEPPER**; raw tokens never stored or logged. Evaluated via constant-time `hmac.compare_digest`. | **TESTED** | `tests/s9/test_ac_m08_sharing.py::test_sharing_token_entropy_and_hash_only_storage` |
| **SEC-05** | **Anti-Enumeration 404 Responses** | Invalid, expired, and revoked share links return an identical HTTP 404 response to eliminate oracle/enumeration attacks (ADR-030). | **TESTED** | `tests/s9/test_ac_m08_sharing.py::test_anti_enumeration_indistinguishable_404_responses`, `test_ac_m08_1_recipient_link_without_active_consent_returns_anti_enumeration_404_and_audited` |
| **SEC-06** | **Encrypted Draft Storage at Rest** | Draft payloads and files encrypted using AES-256-GCM (12-byte random IV/nonce) with 256-bit key derived via SHA-256. In production (`DEV_MODE=false`), a minimum key length of 32 bytes (256 bits) is strictly enforced (fails closed if shorter or default). | **TESTED** | `tests/s8/test_drafts.py`, `tests/s9/test_s9_hardening.py::test_h2_sec06_draft_storage_key_minimum_32_bytes_in_prod` |
| **SEC-07** | **Signed Document URLs with TTL <= 60s** | HMAC-SHA256 signed URLs for document downloads from shared briefs; immediate invalidation if consent is revoked. Expired/invalid signatures rejected. | **TESTED** | `tests/s9/test_ac_m08_sharing.py::test_ac_m08_2_revocation_blocks_access_within_60s_cached_pages_signed_urls` |
| **SEC-08** | **Tenant Data Isolation Matrix** | Strict user ownership isolation verified across Cases, Documents, Intake, Drafts, Notes, Notifications, Consents, Briefs, sub-resources, and ungranted recipient links (403/404). | **TESTED** | `tests/s9/test_s9_hardening.py::test_tenant_isolation_matrix_all_user_resources` |
| **SEC-09** | **Tamper-Evident Audit Logging** | Append-only SHA-256 hash chain covering all authentication, intake, review, draft, consent, access, and revocation events (X-002). | **TESTED** | `tests/s9/test_s9_hardening.py::test_x002_audit_completeness_state_changing_routes`, `test_backup_and_restore_rehearsal_with_audit_chain` |
| **SEC-10** | **Rate Limiting (OTP, Uploads, AI calls)** | 5-attempt lock on link OTP; 15-minute lockout on 6th failed auth OTP; 50 uploads/user/day limit; token cost guard quotas (X-006). | **TESTED** | `tests/s9/test_s9_hardening.py::test_x006_rate_limiting_enforcement`, `tests/s9/test_ac_m08_sharing.py::test_otp_rate_limiting_locks_after_5_attempts` |
| **SEC-11** | **Automated Accessibility (WCAG 2.2 AA)** | Evaluated with locally vendored `axe-core` v4.14.0 across 8 core screens at 360 and 1280 viewports. 0 critical, 0 serious violations. | **TESTED** | `scripts/run_axe_audit.py`, `tests/s9/test_s9_hardening.py::test_x008_accessibility_axe_audit` |
| **SEC-12** | **CORS Configuration & Origin Restrictions** | Configured with explicit allowed origins (`ALLOWED_ORIGINS`, defaulting to `http://localhost:8000,http://127.0.0.1:8000,http://localhost:3000`). Untrusted/foreign origins receive no CORS allowance headers. | **TESTED** | `services/api/app/main.py`, `tests/s9/test_s9_hardening.py::test_h2_cors_enforcement_rejects_foreign_origin` |
| **SEC-13** | **CSRF Immunity via Bearer Token Model** | Authentication strictly requires `Authorization: Bearer <jwt>` HTTP header. No session cookies are used for API state mutations. Requests providing only cookies without the Bearer header are rejected with 401 Unauthorized, rendering CSRF impossible. | **TESTED** | `tests/s9/test_s9_hardening.py::test_h2_csrf_auth_model_rejects_cookie_only_auth` |
| **SEC-14** | **Upload Validation & Magic Bytes Scanning** | File extension allowlist, magic-bytes scanner (`BasicMagicBytesScanner`), 20MB file size limit, and ClamAV adapter slot for virus inspection. | **TESTED** | `packages/trust_kernel/document_engine.py`, `tests/s4/test_documents.py` |
| **SEC-15** | **SSRF Elimination** | Zero API endpoints accept user-supplied destination URLs for outbound HTTP fetching. All external communications (e.g. real SMS gateway) use fixed, server-side environment-configured hostnames. Verified via programmatic AST/signature route audit. | **TESTED** | `tests/s9/test_s9_hardening.py::test_h2_sec13_no_ssrf_endpoints_fetch_user_supplied_urls` |
| **SEC-16** | **SQL & Command Injection Prevention** | All database interactions parametrized through SQLAlchemy ORM; zero raw string concatenation in SQL queries; subprocess arguments passed as arrays. | **TESTED** | `packages/trust_kernel/db.py`, `tests/` |
| **SEC-17** | **Dependency Vulnerability Audit (pip-audit)** | Audited locally using `pip-audit 2.10.1`. 19 known CVEs found across 4 packages (`multidict 6.7.1`, `pip 24.0`, `pypdf 6.18.1`, `urllib3 2.7.0`). | **TESTED** *(Vulnerabilities identified; pinned upgrade list prepared)* | `python -m pip_audit` |
| **SEC-18** | **External Penetration Test** | Formal third-party application and network penetration testing by an independent cybersecurity firm. | **NOT VERIFIED** | *Owner Action Required Prior to Public Launch* |

---

## 2. Dependency Vulnerability Audit (`pip-audit`) Findings

Executed via `python -m pip_audit`:

| Package Name | Installed Version | Vulnerability ID | Severity / Risk | Required Fix Version | Impact on Platform |
|---|---|---|---|---|---|
| `multidict` | 6.7.1 | CVE-2026-104874 | Moderate | 6.9.1 | Used by aiohttp dependency tree |
| `pip` | 24.0 | PYSEC-2026-1795, PYSEC-2026-1796, PYSEC-2026-2875, PYSEC-2026-2876, PYSEC-2026-196, PYSEC-2026-3721 | Moderate | 26.2.0 | Host CLI package manager; not exposed over HTTP |
| `pypdf` | 6.18.1 | PYSEC-2026-4160, PYSEC-2026-4159, PYSEC-2026-4157 | High / Moderate | 6.19.0 | Used during PDF extraction and shaping tests |
| `urllib3` | 2.7.0 | PYSEC-2026-4177, PYSEC-2026-4176, PYSEC-2026-4175 | Moderate | 2.8.0 | Used by requests library |

> [!NOTE]
> Per Standing Rule and Directive H2, **pinned packages were NOT upgraded without owner authorization**, preventing unexpected breaking changes across dependencies. Packages are flagged for scheduled bump.

---

## 3. Owner Actions & Open Items

> [!WARNING]
> **Owner Action Required Prior to Public Release**:
> 1. **SEC-18 (External Penetration Testing)**: Automated tests confirm strict cryptographic correctness, tenant isolation, fail-closed secrets, anti-enumeration behavior, and security headers. However, **no external third-party penetration test has been performed** on live staging or production network infrastructure. This remains **NOT VERIFIED** and requires owner execution.
> 2. **Dependency Upgrade Review**: Review and authorize upgrade of `pypdf` to `>= 6.19.0` and `urllib3` to `>= 2.8.0`.
