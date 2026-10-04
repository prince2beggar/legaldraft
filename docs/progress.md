# AIN-AI — Sprint Progress & Status Tracker

**Current Phase:** Phase 1 (MVP: Understand and Prepare)  
**Current Sprint:** Sprint S6 — Case Folder (M06), Home / Next Action (M02), Notifications & In-Process Reminders (M07) (Completed, Verified)  
**Last Updated:** 4 October 2026  
**Status:** Sprint S6 Completed (All S0-S6 tests passing; CI green)  

---

## 1. Sprint Roadmap & Status

| Sprint | Name | Goal | Status | Acceptance Criteria Covered |
| :--- | :--- | :--- | :--- | :--- |
| **S0** | **Scaffold** | Monorepo layout, Docker Compose, CI, migrations baseline, i18n (`bn` default), UI kit & tokens, PWA shell, health endpoints, feature flags, structured logging, docs | 🟢 Closed | AC-S0-1..AC-S0-5, DoD reversible migrations (SQLite), landmark a11y, port 8088 |
| **S1** | **Auth, Audit, Policy** | Phone OTP (mock + adapter slot), tokens, devices, onboarding with versioned consents, `/me`, append-only hash-chained audit log, `PolicyConsent.can`, rate limits, export/delete skeleton, X-001 sweep | 🟢 Closed | AC-M01-1..5, X-001 sweep, audit tamper test, legacy routes secured, 7 S1 fixes |
| **S2** | **Source Registry & Retrieval** | Ingestion pipeline, review/approve (approver != uploader), version supersede + overlap block + diff, hybrid retrieval (as-of date filter), rights badges, Citizen Library, Admin Knowledge Center, Responsive by Default | 🟢 Closed | AC-M09-1..4, AC-M10-1..3, AC-M10-6, Viewport Tests, 12 Screenshots, Legacy Data Migrated |
| **S3** | **Rules Engine, Citation Verifier, AI Gateway, Eval Harness** | Deterministic rules engine (relative period, trigger day, HR-D6 provenance), citation verifier (exact/normalized/temporal), redaction gateway (PII roundtrip, model router, schema validation, cost guard), eval harness (golden sets, zero-critical gate, DB persistence), responsive admin | 🟢 Closed | Relative period engine, HR-D6 deadline provenance, citation verifier, PII roundtrip, model fallback, schema guard, eval harness, /admin/rules, /admin/evals |
| **S4** | **Documents (M03)** | Upload, safety scan, PDF split, image enhance, OCR (ben+eng), classification, field extract, snippet crop, field state machine (extracted->reviewed->verified), intent, status/retry UI, dedupe, purge audit | 🟢 Completed (115/115 Tests Green) | AC-M03-1..6, Viewport Tests, 12 Screenshots, ADR-022, ADR-023, Migration 004 |
| **S5** | **Notice Interpreter (M04)** | Notice extraction, 8 core sections, DeadlineCard, relative period flow, Save to case | 🟡 Built, Not Validated | AC-M04-1..6, Viewport Tests, 15 Screenshots, ADR-024, Migration 005. Needs Owner Inputs: Q2 LLM Vendor, Tesseract on Staging, 100 Lawyer Notices, 50 Reviews |
| **S6** | **Case Folder, Home / Next Action & Notifications (M06, M02, M07)** | Case folder with 8 tabs, timeline date precision, note privacy flag (AC-M06-5), case review (case.review.v1), deterministic 10-priority Next Action algorithm with reason_refs, in-process notification scheduler with injectable clock, generic SMS, quiet hours deferral | 🟢 Completed | AC-M02-1..4, AC-M06-1..5, AC-M07-1..4, Viewport Tests, 21 Screenshots, ADR-026, Migration 006 |
| **S7** | Intake & Triage (M11) | Triage chips, UrgentBanner, emergency contacts, structured Case Profile | ⚪ Planned | AC-M11-1..5 |
| **S8** | Drafting (M05) | Template engine, question flow, prefill from reviewed fields, PDF/DOCX export | ⚪ Planned | AC-M05-1..6 |
| **S9** | Sharing, Brief & Hardening | Scoped consent, 60s revocation, lawyer brief, penetration test fixes, load test | ⚪ Planned | AC-M08-1..5, X-001..X-008 |
| **S10**| Pilot & Gate G1 Review | Pilot with 30–50 users, lawyer review of 200 outputs, G1 gate review | ⚪ Planned | Gate G1 sign-off |

---

## 2. Open Items & Verification Status (Carried Forward)
The following open items and environment constraints remain recorded:
1. **(a) Audit Chain Multi-Worker DB Locking (Before Staging):**
   - Current design keeps the latest hash in process memory with write-through to DB.
   - **Requirement before Staging:** In multi-worker container deployments, append must happen inside a database transaction that acquires a row-level lock on the latest audit entry (`SELECT ... FOR UPDATE` in PostgreSQL) to prevent workers from concurrently forking the cryptographic hash chain. Add concurrency test once PostgreSQL 16 is running in CI/Docker.
2. **(b) Salted Blocklist & Migration Reversibility Verification (Fixed):**
   - `PHONE_BLOCKLIST_SALT` is enforced as an environment-only secret (`os.getenv("PHONE_BLOCKLIST_SALT")`) without code fallbacks.
   - All `trust_*` tables (`trust_users`, `trust_devices`, `trust_consents`, `trust_audit_logs`, `trust_blocked_phone_hashes`) and `ingestion_jobs` are verified in Alembic migration `002_trust_kernel_s2` and covered by `tests/s0/test_reversible_migrations.py`.
3. **(c) Docker & Postgres 16 Verification Deferred (Owner Decision):**
   - **Owner's Explicit Directive:** Docker Desktop is intentionally NOT installed on this local Windows machine at this time.
   - **Verification Requirement:** `docker compose up` and PostgreSQL 16 + pgvector migrations/extensions remain **unverified locally** on this machine. They **must be validated via CI (GitHub Actions)** or on a Docker-equipped server prior to any staging deployment.
4. **(d) Accessibility Check:** The S0 accessibility test performs semantic HTML landmark and form label audits; headless `axe-core` browser integration is scheduled for end-to-end integration phases.
5. **(e) UI Kit TypeScript Types:** `ui_kit` components in `packages/ui_kit` are staged for CI type-check in subsequent frontend bundle integration.
6. **(f) Permanent Project Rule — Responsive by Default (ADR-018 & DoD #11):** Every screen must work fluidly across Mobile (360px), Tablet (768px), and Desktop (1280px). Tested via automated Playwright viewport assertions.
7. **(g) Backend/App Legacy Static Type Coverage (Open Item):** `backend/app` contains legacy prototype services (drafting engine, deed reading, training service) with 54 untyped mypy errors. `packages` and `services` are 100% typed clean; `backend/app` will be progressively typed as modules are refactored into Trust Kernel architecture in S4/S5/S8.

---

---

## 3. Sprint S1 — Deliverables, Security Fixes & Acceptance Criteria

All 7 S1 Acceptance Fixes have been completed and verified:
- [x] **1. PyJWT Integration & Hardened Token Security:**
  - Hand-written JWT replaced with vetted `PyJWT` (v2.15.1).
  - Pinned algorithm strictly to `HS256`.
  - Constant-time signature comparison.
  - Enforced `exp` and `nbf` claim validation.
  - Secret loaded strictly from environment (`JWT_SECRET`); fails securely if missing.
  - Tested against signature tampering, token expiration, and `alg=none` bypass attacks (`tests/s1/test_jwt_security.py`).
- [x] **2. Real Database Persistence for Trust Kernel:**
  - Real database persistence layer implemented in `packages/trust_kernel/db.py` via SQLAlchemy ORM (`trust_users`, `trust_devices`, `trust_consents`, `trust_audit_logs`, `trust_blocked_phone_hashes`).
  - `AuthService`, `PolicyConsentService`, and `InMemoryAuditService` persist state changes immediately and re-hydrate on startup (`load_from_db()`).
  - Tested: User, device, versioned consents, and audit hash chain survive full application restart, and hash chain verifies integrity (`tests/s1/test_persistence_restart.py`).
- [x] **3. Cross-Tenant Data Isolation & PolicyConsent.can Enforcement:**
  - Audited and secured all legacy `/api/v1/*` routes:
    - `/api/v1/matters`: Filtered by ownership for citizens; `GET /{id}` enforces `PolicyConsent.can(actor, "read", obj)`.
    - `/api/v1/documents`: Filtered by matter ownership for citizens; `GET /{id}`, `PUT /{id}`, `GET /{id}/versions`, and export endpoints enforce `PolicyConsent.can`.
    - `/api/v1/intake`: `POST /chat` and `POST /analyze-scenario` verify matter ownership before persisting extracted facts.
    - `/api/v1/drafting`: `POST /generate` verifies matter ownership before attaching drafts.
    - `/api/v1/review`: `GET /{id}/health` enforces document read permissions before performing audits.
    - `/api/v1/admin/*`: Restricted to `role in ("admin", "reviewer")`; citizens receive HTTP 403 Forbidden.
  - Negative sweep tests prove User A cannot read or tamper with User B's data (`tests/s1/test_ownership_isolation.py`).
- [x] **4. Salted Hash Blocklist for Deleted Accounts & Provisional Q8 Status:**
  - Plain phone numbers are never stored in the blocklist; `AuthService` computes salted SHA-256 hash using `PHONE_BLOCKLIST_SALT`.
  - Deletion removes or anonymizes user PII per SRS 8.4 while preserving append-only audit continuity.
  - Permanent blocking marked provisional pending legal counsel decision on Question Q8 (Draft PDPO right-to-be-forgotten vs fraud prevention).
- [x] **5. Neutral SMS Gateway Adapter Slot:**
  - `MockSmsProvider` remains default for local development and CI testing.
  - Real adapter slot named neutrally as `RealSmsAdapterSlot` (`REAL_SMS_ADAPTER_CLASS` / `REAL_SMS_API_KEY`). Question Q3 remains open.
- [x] **6. CI Pipeline Banner:**
  - Fixed banner in `run_ci.py` to reflect Sprint S1 Definition of Done.
- [x] **7. Architecture Decisions & Progress Documentation:**
  - Recorded ADR-012 through ADR-017 and Question Q8 in `docs/decisions.md`.
  - Updated `docs/progress.md` with full sprint status.

---

## 4. Sprint S2 — Deliverables & Acceptance Criteria (Satisfied)

All S2 Acceptance Criteria and deliverables have been implemented and verified:
- [x] **1. Ingestion Pipeline (SRS M10, AC-M10-6):**
  - Asynchronous multi-step pipeline in `packages/trust_kernel/source_registry.py`:
    `uploaded` -> `extracted` -> `cleaned` -> `classified` -> `chunked` -> `indexed` -> `review_pending`.
  - Per-step status tracking in `ingestion_jobs` table (`details_json`, `step`, `status`).
  - Pipeline error handling and retry mechanism (`retry_ingestion_job`) verified by `test_ac_m10_6_ingestion_pipeline_steps_and_retry`.
- [x] **2. Review & Approval Separation (SRS AC-M10-1):**
  - Strict role and identity separation: `approver_id != uploader_id`.
  - Uploader attempting self-approval raises `PermissionError` and returns `HTTP 403 Forbidden` (`test_ac_m10_1_approver_cannot_be_uploader`).
- [x] **3. Version Superseding, Overlap Check & Diff View (SRS AC-M10-2):**
  - Approving version N+1 with `effective_from` sets predecessor version N's `effective_to = (N+1.effective_from - 1 day)`.
  - Date overlap / inverted chronology validation blocks conflicting approvals with `ValueError` / `HTTP 409 Conflict`.
  - Version Diff viewer (`compute_version_diff`) outputs categorized `added`, `removed`, and `modified` passage diffs.
- [x] **4. Closed Corpus Guarantee & Hybrid Retrieval (SRS AC-M09-1, AC-M09-2, AC-M10-3):**
  - `HybridRetriever` combines term frequency / keyword overlap with 128-dim dense vector cosine similarity.
  - Closed corpus filtering: only `status == 'approved'` versions are ever returned; unapproved drafts and rejected items are invisible to citizens.
  - Strict as-of date filtering: `effective_from <= as_of_date <= effective_to`.
- [x] **5. Rights Badges & Unlicensed Restrictions (SRS AC-M09-3):**
  - Displays `official`, `licensed`, `unlicensed`, and `public_domain` badges.
  - For `unlicensed` sources, passage text is omitted/redacted with external link only.
- [x] **6. Plain Explanation with Static Placeholder (No AI before S3):**
  - Per core rules B1-B15 and HR-07, no AI-generated legal explanations are permitted before S3 (AI Gateway & Citation Verifier).
  - `POST /api/v1/library/passages/{id}/explain` outputs structured metadata with `ai_label`: `"STATIC_PLACEHOLDER_NO_AI (AI Gateway & Citation Verifier deferred to S3)"`, `is_ai_generated`: `False`, and clearly labelled static text `[DRAFT_NOT_REVIEWED / STATIC PLACEHOLDER]`. Frontend UI displays static draft badge without AI claims.
- [x] **7. Ingestion Pipeline Implementation Matrix (Real vs Stubbed):**
  - **1. uploaded (REAL):** DB record created, initial state captured in `sources`, `source_versions`, and `ingestion_jobs`.
  - **2. extracted (STUBBED):** UTF-8 plain-text / bytes decode only. Full PDF parsing and OCR via Tesseract (ben+eng) are stubbed because Tesseract is not installed on this Windows host.
  - **3. cleaned (REAL):** Text normalization, line-ending standardization, carriage return stripping.
  - **4. classified (STUBBED):** Rule-based keyword matching heuristic for legal categories (no trained ML classifier).
  - **5. chunked (REAL):** Section and paragraph boundary chunking into passages.
  - **6. indexed (REAL for SQLite):** Pure-Python `DeterministicEmbedder` (128-dim normalized dense vector). PostgreSQL `PgvectorEmbedder` is implemented but marked UNVERIFIED pending Postgres 16.
  - **7. review_pending (REAL):** Version status set to `review_pending` in database, feeding the dual-custody review queue.
  - **Execution Mode (SIMULATED):** In-process asynchronous task runner. Celery/Redis queue is simulated pending Docker environment availability.
- [x] **8. Embedder Architecture & PostgreSQL Status:**
  - `DeterministicEmbedder`: 128-dimensional normalized dense float vector generator for reproducible SQLite test runs.
  - `PgvectorEmbedder`: PostgreSQL pgvector adapter implemented behind `EmbedderInterface`. Explicitly marked: `"UNVERIFIED until run in Postgres (CI or Docker)"`.
- [x] **9. Single-Database Architecture (Eliminating Split-Brain):**
  - Consolidated legacy advocate models and modern Trust Kernel tables into a single SQLite database (`ain_ai.db`) managed by a unified Alembic migration baseline (`002_trust_kernel_and_s2_enhancements.py`), completely eliminating earlier dual-database file split-brain between `legal_saas.db` and `ain_ai.db`.
- [x] **10. Responsive by Default & Screenshots (ADR-018 & DoD #11):**
  - Citizen Library (`/library` / `library.html`) and Admin Knowledge Center (`/admin/sources` / `admin_sources.html`) built mobile-first (360px), tablet (768px), and desktop (1280px).
  - Legacy Advocate dashboard (`/`) and Admin console (`/admin`) headers polished to prevent text overflow on 360px viewports.
  - Automated Playwright viewport tests verified: zero horizontal overflow (`scrollWidth <= clientWidth`), bottom tab navigation on mobile, side rail on tablet, full sidebar on desktop, touch targets >= 44px.
  - 12 real PNG screenshots captured in `storage/screenshots/`:
    * `citizen_library_search_mobile_360.png`, `..._tablet_768.png`, `..._desktop_1280.png`
    * `source_viewer_mobile_360.png`, `..._tablet_768.png`, `..._desktop_1280.png`
    * `admin_knowledge_center_list_mobile_360.png`, `..._tablet_768.png`, `..._desktop_1280.png`
    * `approve_flow_mobile_360.png`, `..._tablet_768.png`, `..._desktop_1280.png`

---

## 5. Sprint S2 Status Breakdown

* **DONE:**
  - SourceRegistry service and DB persistence (`sources`, `source_versions`, `source_passages`, `ingestion_jobs`).
  - Asynchronous 7-step ingestion tracker with retry capability (`test_ac_m10_6`).
  - Strict uploader/approver separation (`approver_id != uploader_id`, `test_ac_m10_1`, `test_3e`).
  - Legal version superseding (`effective_to = predecessor - 1 day`), date overlap rejection (`test_ac_m10_2`, `test_3d`), and passage diff viewer.
  - Closed corpus hybrid retrieval: keyword + 128-dim dense vector (`DeterministicEmbedder`), strictly filtered to `status == 'approved'` (`test_ac_m09_2`, `test_ac_m10_3`, `test_3a`), and as-of date window (`test_ac_m09_1`, `test_3b`, `test_3c`).
  - Rights badges (`official`, `licensed`, `unlicensed`, `public_domain`), with unlicensed passage text withheld (`test_ac_m09_3`).
  - Tamper-evident audit logging for all source state transitions (`test_3f`).
  - Static placeholder for legal explanations prior to S3 (`test_ac_m09_4`).
  - Responsive by Default (ADR-018) across Mobile (360px), Tablet (768px), and Desktop (1280px).
  - Legacy data from `legal_saas.db` safely migrated to `ain_ai.db` and verified across restarts.
* **NOT VERIFIED LOCALLY:**
  - `docker compose up` and container orchestration (host lacks Docker Desktop).
  - PostgreSQL 16 + pgvector adapter (`PgvectorEmbedder` marked UNVERIFIED pending Postgres).
  - Real headless `axe-core` binary audit (HTML5 structural accessibility verified).
* **BLOCKED / PENDING OWNER INPUTS:**
  - **Question Q5 (Closed for S2 with fake test seed):** Real statutory content from legal team needed for production staging.
  - **Question Q2 (Closed for S3 with neutral adapter slot):** Data residency terms pending enterprise LLM contract; `FakeLLMProvider` is default.

---

## 6. Sprint S3 — Deliverables, Safety Gates & Acceptance Criteria (Satisfied)

All Sprint S3 core requirements and safety gates have been implemented and verified:
- [x] **1. Deterministic Rules Engine — Trust Kernel Core (Decision D6 / ADR-004, Rule B6):**
  - Belongs strictly to the **Trust Kernel** (core determinism platform), not M11/Intake.
  - Implemented `relative_period.calendar_days.v1` in `packages/trust_kernel/rules_engine.py`:
    * Trigger day handling: `include_trigger_day=False` (default, standard legal rule: day 1 is following day) and `include_trigger_day=True` (trigger day counted as day 1).
    * Handles positive offsets, negative offsets (e.g. "5 days prior"), and zero offsets.
    * Explicit holiday calendar data model marked with `EMPTY_FAKE_TEST_DATA` comments and label.
    * **Decision D6 Provenance Enforcement:** `validate_deadline_provenance()` rejects any deadline invented by LLMs without Rules Engine provenance or verbatim statutory passage support (`UnverifiedDeadlineError`).
    * `compute()` returns `rule_id`, `rule_version`, and the exact `inputs` used (`start_date`, `days`, `include_trigger_day`, `calendar`) so the UI can clearly display how a date was calculated.
    * Persisted test suite runner (`run_rule_tests()`) against `rule_tests` table.
- [x] **2. Citation Verifier (SRS B3, SRS §2.1):**
  - Implemented `packages/trust_kernel/citation_verifier.py`:
    * Deterministic exact verbatim passage matching (`is_verbatim=True`, `match_score=1.0`).
    * Full legal normalization applied: Unicode NFKC decomposition/composition, whitespace consolidation (`\s+` -> `' '`), punctuation standardization (curly quotes/dashes), and 1:1 digit canonicalization (`০-৯` <-> `0-9`).
    * Strict anti-hallucination boundary: Numbers and dates must match exactly. Changing statutory numbers or quantities (e.g. 60 vs 70 bigha) is strictly rejected as `CONTRADICTED` with 0.0 match score.
    * Rejection of non-existent sources, non-existent versions, and non-existent section passages.
    * Temporal validity checking (`as_of_valid`): validates whether the cited version was active on the target `as_of_date`.
    * Rejects citations referencing draft/unapproved versions or superseded versions outside their validity window.
- [x] **3. Governed AI Gateway (SRS 8.3, B15, ADR-021):**
  - Implemented `packages/trust_kernel/ai_gateway.py`:
    * Versioned prompt registry: prompts are versioned; every `ai_output` records `prompt_id` and `prompt_version`; unregistered prompts are refused with `ValueError`.
    * Prompt injection defense: scans user inputs for injection attempts (`ignore previous instructions`, `output a deadline`, `reveal the system prompt`), safely encapsulates untrusted input, preserves output schema intact, strictly prevents deadline invention, and flags the output (`injection_flagged=True`, `security_flags` persisted in DB).
    * Pre-provider PII redaction and round-trip unredaction (`PIIRedactor`) for Bangladesh phone numbers (`+8801...`), 10/13/17-digit NID numbers, and emails.
    * Model router with automatic fallback (`model_preference="primary"` falls back gracefully).
    * Neutral `RealLlmAdapterSlot` strictly disabled by default (`ENABLE_REAL_LLM=false`); default provider is `FakeLLMProvider`.
    * Strict JSON-schema output validation via `jsonschema`; invalid outputs raise `SchemaValidationError`.
    * Cost guard quota enforcement (`CostLimitExceededError`) tracking cumulative tokens against daily/request ceilings.
    * Claim Links: Every claim in an AI output is stored with its source-passage link in `claim_links`; claims without verified links are flagged and NEVER shown as verified (`is_verified=False`, `is_flagged=True`).
    * Full database persistence in `ai_outputs` and `claim_links`.
- [x] **4. Evaluation Harness & Legal Quality Gates (SRS §8.7, §9.3 S3):**
  - Implemented `packages/trust_kernel/eval_harness.py`:
    * Pre-configured golden test suites labeled `FAKE_TEST_DATA`:
      1. `limitation_deadline_calculation_golden.v1` (Rules Engine)
      2. `citation_exactness_golden.v1` (Citation Verifier)
      3. `gateway_schema_compliance_golden.v1` (AI Gateway)
    * Automated test execution tracking latency, individual pass/fail, and aggregate accuracy score.
    * **Legal Quality Gates:** Replaced flat 80% threshold with legal-grade gate requiring **zero critical errors** (`critical_errors == 0`) and suite-defined minimum score. A run with 95% average score but 1 critical error strictly FAILS the gate.
    * Real DB persistence in `eval_runs` and `eval_results`.
- [x] **5. Database Schema & Reversible Migration 003:**
  - Alembic migration `003_s3_rules_verifier_gateway.py` added tables: `rule_tests`, `prompts`, `ai_outputs`, `claim_links`, `eval_runs`, `eval_results`, plus column alters on `rules`, `rule_versions`, and `ai_outputs`.
  - Migration reversibility (upgrade -> seed -> downgrade -> upgrade) verified 100% in `tests/s0/test_reversible_migrations.py`.
- [x] **6. Responsive Admin Web Screens (ADR-018):**
  - `/admin/rules` (`admin_rules.html`): Interactive Rules Engine registry and calculation sandbox.
  - `/admin/evals` (`admin_evals.html`): Eval Harness dashboard with metric cards, test suite runner, and recent run history.
  - Verified responsive with zero horizontal overflow across Mobile (360x640), Tablet (768x1024), and Desktop (1280x800).
  - 6 new screenshots recorded in `storage/screenshots/`:
    * `admin_rules_mobile_360.png`, `..._tablet_768.png`, `..._desktop_1280.png`
    * `admin_evals_mobile_360.png`, `..._tablet_768.png`, `..._desktop_1280.png`

---

## 7. Sprint S4 — Documents (M03) Deliverables & Acceptance Criteria (Satisfied)

All S4 Acceptance Criteria and deliverables have been implemented and verified:
- [x] **1. Direct & Resumable Upload with Deduplication (AC-M03-1, AC-M03-6, ADR-022):**
  - Chunked resumable upload session (`/api/v1/documents/resumable/initiate`, `/chunk`) with chunk tracking and automated full-file reassembly.
  - Offline queue support with IndexedDB + ServiceWorker fallback event handling in `documents_upload.html`.
  - SHA-256 deduplication: duplicate uploads by the same user return existing document record idempotently (`is_deduplicated=True`) without duplicating storage.
- [x] **2. File Safety Scanning & Adapter Slots (ADR-022, ADR-023):**
  - Magic bytes & extension scanner (`BasicMagicBytesScanner`) rejects PE binaries, ELF executables, shell scripts, and enforces size limit.
  - `ClamAvAdapterSlot` marked UNVERIFIED (falls back safely to `BasicMagicBytesScanner`).
  - `MinioObjectStoreAdapterSlot` marked UNVERIFIED (falls back safely to `LocalFilesystemObjectStore`).
- [x] **3. PDF Page Splitting & Image Enhancement (AC-M03-1, ADR-023):**
  - PDF page splitting via `pypdf`, extracting embedded images per page.
  - Image enhancer (`ImageEnhancer`): 90-degree deskew rotation, grayscale conversion, and 1.4x contrast normalization.
  - Bounding box snippet crop generator (`crop_snippet`) creates verified image snippets for extracted fields.
- [x] **4. OCR Engine & Transparent Host Reporting (ADR-023):**
  - Host CLI inspection: transparently reported that `tesseract` CLI is not installed on host machine.
  - `TesseractOcrAdapter` marked UNVERIFIED without crashing pipeline.
  - `FakeOcrEngine` benchmark runner accurately and deterministically reads synthetic scans (`clean`, `rotated`, `low_contrast`, `blurred`, `noisy`, `ben_eng_mixed`, and 5-page PDF) all stamped `[নমুনা]` / `FAKE_TEST_DATA`.
- [x] **5. Document Classification & Stated-Date Field Extraction (AC-M03-1, AC-M03-4):**
  - Classifies legal documents into: `notice`, `deed`, `court_order`, `petition`, `receipt`, `id_card`, `other`.
  - Stated-dates-only entity extraction (strictly zero invented deadline dates).
  - Screening filter (AC-M03-4): items without bounding box / span_ref NEVER appear in client UI or API response.
- [x] **6. Field State Machine & Snippet Crop Linkage (AC-M03-2):**
  - Every extracted field links to a snippet crop image in object store.
  - Field state machine: `extracted` -> `reviewed` -> `verified`.
  - Editing field value without confirmation fails; editing with `confirm=True` transitions state to `reviewed`. Verification transitions to `verified`.
  - Confidence words: `clear`, `check`, `not sure`. Low confidence is always flagged for human check and never hidden.
- [x] **7. OCR Failure Retry & Zero Data Loss (AC-M03-3):**
  - Auto-retry up to 3 times on OCR failure.
  - After 3rd failure, document state is `failed` with clear Bangla user error message and zero data loss (original scan preserved).
- [x] **8. Ownership Isolation & Immutable Purge (AC-M03-5):**
  - Unauthorised cross-user document requests return 403 Forbidden and log breach events in `trust_audit_logs`.
  - Purge API completely removes document files and database rows, recording an immutable audit entry with document SHA-256 and size (zero sensitive text).
- [x] **9. Responsive Web Screens (ADR-018):**
  - Upload (`documents_upload.html`), Intent (`document_intent.html`), Viewer (`document_viewer.html`), Status/Retry UI (`document_status.html`).
  - Zero horizontal overflow across Mobile (360x640), Tablet (768x1024), Desktop (1280x800).
  - 12 verified screenshots captured in `storage/screenshots/` and documented in `s4_screenshots.md`.

---

## 8. Sprint S5 — Notice Interpreter (M04) Deliverables & Status (Built, Not Validated)

Sprint S5 is **Built, Not Validated**. Complete functionality is built and passes automated pipeline verification, pending the owner requirements:
- **Owner Pre-Conditions to Validate & Close S5:**
  1. **LLM Vendor Decision (Question Q2):** Contract selection with zero-data-retention and data residency terms.
  2. **Tesseract on Staging/Production:** Installation and validation of Tesseract OCR binary on deployment hosts.
  3. **Real Lawyer Golden Set:** At least 100 authentic Bangladeshi legal notices written/curated by practicing advocates.
  4. **Lawyer Output Review:** Independent verification of at least 50 end-to-end model outputs by practicing advocates.

- **Verified Deliverables in Sprint S5:**
  - [x] **1. Notice Interpreter Engine & 8 Structured Sections (M04):**
    - `packages/trust_kernel/notice_engine.py` provides 8 structured sections in fixed order: Label Bar, One-line summary, Details (Sender, Why received, What it says), Actionable Checklist, DeadlineCard, Documents needed, If you ignore it, Questions for lawyer.
  - [x] **2. Grounded "If You Ignore It" Fallback (AC-M04-2):**
    - 100% of displayed claims link to resolvable source passages.
    - If notice does not state a consequence, strictly outputs verified fallback: `"নথিতে এমন কিছু উল্লেখ নেই। একজন আইনজীবীর পরামর্শ নিন।"` (never hallucinated from model knowledge).
  - [x] **3. Deterministic Deadlines & Rules Engine Calculation (AC-M04-3):**
    - Stated dates require explicit user confirmation before saving to database.
    - Relative deadlines (e.g. 15/30 days from receipt) are computed solely via pure-code Rules Engine (`relative_period.calendar_days.v1`) with full visible step breakdown.
  - [x] **4. Mandatory Labels & Script Purity (AC-M04-4):**
    - 100% of results include: AI label (`AI ব্যাখ্যা — আইনজীবীর দ্বারা যাচাইকৃত নয়`), formatted as-of date (`হালনাগাদ: ০৩ অক্টোবর ২০২৬`), and authentic Bengali certainty label (`স্পষ্ট`, `যাচাই করুন`, or `নিশ্চিত নই`). Legacy word `পরিष्कार` and non-Bengali Devanagari characters are strictly forbidden.
  - [x] **5. Synthetic Pipeline Check (AC-M04-1, AC-M04-5):**
    - Golden set evaluation in `tests/s5/test_eval_golden_set_notices.py` accurately labeled as synthetic pipeline check (says nothing about real model quality).
    - Pipeline latency p90 for 3-page notice well within 20s budget.
  - [x] **6. Prompt Injection Defense & Negative Tests (AC-M04-6):**
    - System overrides, prompt extraction attacks, and forced unconfirmed deadlines are neutralized.
  - [x] **7. Injectable Clock & Past Reminder Filtering (ADR-004, M07):**
    - DatabaseManager supports injectable clock (`set_clock()`).
    - Reminders are scheduled at `08:00 Asia/Dhaka` (+06:00). Reminders whose scheduled time is in the past (e.g. T-7 for a deadline 5 days away) are never created.
  - [x] **8. Fake Model Disclosure Banner & Provider Flag:**
    - Non-real LLM responses carry `provider="fake"`.
    - Every notice screen displays prominent warning banner: `"পরীক্ষামূলক মোড: এটি আসল AI বিশ্লেষণ নয়।"`.
  - [x] **9. Cross-Module Integrity & Decision D08:**
    - Lawyer consultation/sharing correctly linked to module **M08** (M09 is Legal Library).
    - Decision D08 records that Cases reversibly wrap/supersede legacy matters (`matters`) without modifying or deleting legacy data.
  - [x] **10. 15 Responsive Viewport Screenshots (ADR-018):**
    - Captured across Mobile (360x640), Tablet (768x1024), Desktop (1280x800):
      * Notice Result: `storage/screenshots/s5_notice_result_mobile_360.png`, `..._tablet_768.png`, `..._desktop_1280.png`
      * DeadlineCard: `storage/screenshots/s5_deadline_card_mobile_360.png`, `..._tablet_768.png`, `..._desktop_1280.png`
      * Relative Flow: `storage/screenshots/s5_relative_flow_mobile_360.png`, `..._tablet_768.png`, `..._desktop_1280.png`
      * Fallback Unreadable: `storage/screenshots/s5_fallback_unreadable_mobile_360.png`, `..._tablet_768.png`, `..._desktop_1280.png`
      * Save to Case: `storage/screenshots/s5_save_to_case_mobile_360.png`, `..._tablet_768.png`, `..._desktop_1280.png`

---

## 9. Sprint S6 — Case Folder, Home / Next Action & Notifications (M06, M02, M07) Deliverables (Satisfied)

All Sprint S6 core requirements, acceptance criteria, and responsive viewport standards have been implemented and verified:
- [x] **1. Case Folder Architecture & Lifecycle (SRS M06, AC-M06-1, AC-M06-2, ADR-026):**
  - Implemented `packages/trust_kernel/case_engine.py` wrapping case creation, updates, and closure.
  - Complete 8-tab case workspace: `Overview`, `Documents`, `Timeline`, `Facts`, `Tasks & Deadlines`, `Notes`, `Review`, and `Lawyer Consultation`.
  - Chronological Timeline supporting four distinct date precisions (`day`, `month`, `year`, `approximate`) with dispute tagging and event provenance links.
  - Case facts state machine (`proposed` -> `accepted` / `dismissed`) with user review confirmation.
- [x] **2. Case Note Privacy Guarantee (AC-M06-5):**
  - Case notes feature an explicit `include_in_analysis` boolean flag (defaults to `False`).
  - Strict privacy boundary: Private notes are strictly excluded from all AI prompt payloads and context assembly.
- [x] **3. Governed AI Case Review Prompt `case.review.v1` (AC-M06-3, AC-M06-4):**
  - Registered versioned prompt `case.review.v1` with JSON-schema output validation.
  - Outputs 6 structured sections: Case Overview, Timeline Gaps, Contradictions, Missing Documents, Legal Risks, and Recommended Actions.
  - Proposed review items start in `proposed` state and are completely ignored by the Next Action engine until user accepts them.
  - Mandatory AI label displayed: `"AI বিশ্লেষণ, আইনি পরামর্শ নয়"` (`ai_disclaimer_bn`).
  - Zero-outcome guarantee: Red-team verified with 32 adversarial prompts; absolutely refuses win/loss probabilities or definitive judicial outcome statements.
- [x] **4. Notice-to-Case Integration (M04 -> M06):**
  - "Save to case" flow seamlessly creates a new case or links an existing one from S5 Notice Interpreter outputs.
  - Updates `document.case_id` and registers notice sender, required actions, and primary deadline card into the case folder automatically.
- [x] **5. Home Screen & Deterministic Next Action Engine (SRS M02, AC-M02-1..4):**
  - Implemented `packages/trust_kernel/home_engine.py`.
  - Time-aware Bengali greeting: `সকাল` (05:00-11:59), `দুপুর` (12:00-14:59), `বিকাল` (15:00-17:59), `সন্ধ্যা` (18:00-19:59), `রাত` (20:00-04:59).
  - ProblemInput field with automatic whitespace trimming, metadata tracking, and voice input trigger (`#btnMic`).
  - **Deterministic Next Action Algorithm (SRS p. 21):** Pure Python code executing a strict 10-priority ranking:
    1. Critical Deadline Today (T=0)
    2. Overdue Deadline (T<0)
    3. Urgent Notice Requiring Action (<=3 days)
    4. Pending Document Review (extracted fields awaiting confirmation)
    5. Upcoming Deadline Soon (<=7 days)
    6. Case Review Issues Requiring Attention (accepted gaps/risks)
    7. Draft In Progress (incomplete legal draft)
    8. Case Missing Primary Documents
    9. Unfiled / Draft Case
    10. All Good / Exploration Default
  - Every recommendation includes deterministic `reason_refs` and clear Bengali explanation modal (`#btnWhyNextAction`).
  - Displays "My Cases" summary and "Upcoming Deadlines" (capped at 5 items).
- [x] **6. Notifications & In-Process Reminders (SRS M07, AC-M07-1..4):**
  - Implemented `packages/trust_kernel/notification_engine.py` with in-process scheduler and injectable clock.
  - Automatic deadline reminder cadence: T-7 days, T-3 days, T-1 day, and Day-of at `08:00 Asia/Dhaka` (+06:00).
  - Past reminder prevention: Reminders whose trigger time has already passed are never scheduled.
  - Daily Digest: 08:00 AM Asia/Dhaka aggregate digest for multiple same-day notifications.
  - Quiet Hours Deferral: Non-critical notifications generated between 22:00 and 07:00 Asia/Dhaka are deferred to 07:00 AM next morning.
  - SMS Escalation Safety: Critical deadlines escalate to SMS using strictly generic text (`"You have a deadline soon. Open AIN-AI."` / `"আপনার একটি আইনি সময়সীমা আসন্ন। আইন-AI অ্যাপটি দেখুন।"`) with zero case title, court name, or PII.
  - Delivery receipts, 3 retries with 5-minute exponential backoff, and administrative failure view.
- [x] **7. Responsive Web Screens (ADR-018):**
  - `/home` (`home.html`), `/cases` (`cases.html`), `/cases/{id}` (`case_detail.html` with 8 tabs), `/notifications` (`notifications.html`), `/notification-settings` (`notification_settings.html`).
  - Tested responsive across Mobile (360x640), Tablet (768x1024), Desktop (1280x800) with zero horizontal overflow (`scrollWidth <= clientWidth`).
  - 21 real PNG screenshots captured in `storage/screenshots/` and copied to artifact directory.
- [x] **8. Comprehensive Test Suite (27 S6 Tests Green):**
  - `tests/s6/test_ac_m02_home.py` (5/5 PASSED)
  - `tests/s6/test_ac_m06_cases.py` (7/7 PASSED)
  - `tests/s6/test_ac_m07_notifications.py` (6/6 PASSED)
  - `tests/s6/test_s6_viewport_responsive.py` (7/7 PASSED)
  - `tests/s6/test_s6_e2e_journey.py` (2/2 PASSED: API + Playwright browser flow)

---

## 10. Test Verification Status
- **Test Suite Command:** `python -m pytest tests -v --tb=short`
- **Total Tests:** 186 passed, 0 failed (100% green across S0, S1, S2, S3, S4, S5, and S6).
- **CI Pipeline:** `python run_ci.py` passes all stages:
  1. Code Linting (Ruff: clean, 0 errors)
  2. Static Type Checking (Mypy: clean on packages and services)
  3. Automated Tests (Pytest: 186/186 tests green)
  4. Raw CI log written to `reports/ci_latest.txt` and JUnit XML written to `reports/junit_latest.xml`.


