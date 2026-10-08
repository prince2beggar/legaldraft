# Legacy Routes & Historical Endpoints Inventory (Directive M8)

This document provides a comprehensive audit of all legacy pages and API routes created in earlier development iterations (S0–S5), documenting their status, disposition policy, role requirement, and isolation from the modern navigation system.

## Policy & Security Guardrails
1. **Zero Legacy Links in New Navigation:** None of the legacy pages, routes, or endpoints are referenced, linked, or reachable from the modern citizen navigation bar (desktop sidebar or mobile bottom nav).
2. **Fail-Closed in Production (`DEV_MODE=false`):** Internal developer routes (`*/dev/*`) and unverified batch ingest endpoints return HTTP 404 Not Found when `DEV_MODE=false`.
3. **No Code Deletion:** Per strict repository directives, legacy code files and legacy routers are preserved intact without file deletion.

---

## Detailed Legacy Routes Inventory

| Method | Route / Path | Origin / Component | Intended Disposition | Protected Role | Reachable from New Nav? | Notes & Modern Replacement |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `GET` | `/static/index.html` | Legacy Advocate Web UI | **Keep (DEV_MODE-only)** | Advocate / Citizen | **No** | Legacy single-page advocate dashboard. Replaced by modern citizen `/home` and `/cases`. |
| `GET` | `/api/v1/matters/` | Legacy Matter Service | **Keep (DEV_MODE-only)** | Citizen / Advocate | **No** | Replaced by `/api/v1/cases`. |
| `POST` | `/api/v1/matters/` | Legacy Matter Service | **Keep (DEV_MODE-only)** | Citizen / Advocate | **No** | Replaced by `/api/v1/cases`. |
| `GET` | `/api/v1/matters/{matter_id}` | Legacy Matter Service | **Keep (DEV_MODE-only)** | Citizen / Advocate | **No** | Replaced by `/api/v1/cases/{case_id}`. |
| `POST` | `/api/v1/intake/chat` | Legacy Freeform Intake | **Keep (DEV_MODE-only)** | Citizen | **No** | Replaced by guided deterministic triage `/api/v1/intake/sessions`. |
| `POST` | `/api/v1/intake/analyze-scenario` | Legacy Scenario Engine | **Keep (DEV_MODE-only)** | Citizen | **No** | Replaced by `/api/v1/intake/sessions/{id}/profile`. |
| `POST` | `/api/v1/intake/autofill-missing` | Legacy Scenario Engine | **Keep (DEV_MODE-only)** | Citizen | **No** | Replaced by `/api/v1/intake/sessions/{id}` PATCH. |
| `POST` | `/api/v1/intake/scenario-recheck` | Legacy Scenario Engine | **Keep (DEV_MODE-only)** | Citizen | **No** | Replaced by `/api/v1/intake/sessions/{id}/confirm`. |
| `POST` | `/api/v1/drafting/generate` | Legacy Jinja2 Generator | **Keep (DEV_MODE-only)** | Citizen | **No** | Replaced by `/api/v1/drafts/{id}/generate` with Trust Kernel template engine. |
| `GET` | `/api/v1/deeds/dev/corrections` | Legacy Deed OCR Tool | **DEV_MODE-only (404 in Prod)** | Internal Dev | **No** | Returns HTTP 404 when `DEV_MODE=false`. Tested in `test_l2`. |
| `POST` | `/api/v1/deeds/dev/crop-test` | Legacy Deed OCR Tool | **DEV_MODE-only (404 in Prod)** | Internal Dev | **No** | Returns HTTP 404 when `DEV_MODE=false`. Tested in `test_l2`. |
| `GET` | `/api/v1/admin/learning` | Legacy Ingest Harness | **DEV_MODE-only (404 in Prod)** | Admin / Dev | **No** | Returns HTTP 404 when `DEV_MODE=false`. |
| `POST` | `/api/v1/admin/ingest-nasrin-book` | Legacy Book Ingest | **DEV_MODE-only (404 in Prod)** | Admin / Dev | **No** | Returns HTTP 404 when `DEV_MODE=false`. |
| `POST` | `/api/v1/admin/ingest-file` | Legacy File Ingest | **DEV_MODE-only (404 in Prod)** | Admin / Dev | **No** | Returns HTTP 404 when `DEV_MODE=false`. |
| `GET` | `/api/v1/admin/ingested-documents` | Legacy Document Index | **DEV_MODE-only (404 in Prod)** | Admin / Dev | **No** | Returns HTTP 404 when `DEV_MODE=false`. |
| `GET` | `/api/v1/admin/ingested-documents/{doc_id}/lessons` | Legacy Document Lessons | **DEV_MODE-only (404 in Prod)** | Admin / Dev | **No** | Returns HTTP 404 when `DEV_MODE=false`. |
| `DELETE` | `/api/v1/admin/ingested-documents/{doc_id}` | Legacy Document Purge | **DEV_MODE-only (404 in Prod)** | Admin / Dev | **No** | Returns HTTP 404 when `DEV_MODE=false`. |
| `GET` | `/api/v1/legacy/documents/` | Legacy Document Store | **Keep (DEV_MODE-only)** | Citizen | **No** | Remounted under `/api/v1/legacy/documents` to avoid collision with modern `/documents`. |
| `GET` | `/api/v1/legacy/documents/{id}` | Legacy Document Store | **Keep (DEV_MODE-only)** | Citizen | **No** | Remounted under `/api/v1/legacy/documents`. |
| `PUT` | `/api/v1/legacy/documents/{id}` | Legacy Document Store | **Keep (DEV_MODE-only)** | Citizen | **No** | Remounted under `/api/v1/legacy/documents`. |
| `GET` | `/api/v1/legacy/documents/{id}/export/docx` | Legacy Document Export | **Keep (DEV_MODE-only)** | Citizen | **No** | Remounted under `/api/v1/legacy/documents`. |
| `GET` | `/api/v1/legacy/documents/{id}/export/pdf` | Legacy Document Export | **Keep (DEV_MODE-only)** | Citizen | **No** | Remounted under `/api/v1/legacy/documents`. |
| `GET` | `/api/v1/legacy/documents/{id}/versions` | Legacy Document History | **Keep (DEV_MODE-only)** | Citizen | **No** | Remounted under `/api/v1/legacy/documents`. |
| `POST` | `/api/v1/evaluation/benchmark/run` | Legacy Benchmark Tool | **Keep (DEV_MODE-only)** | Citizen / Dev | **No** | Modern replacement: `/api/v1/evals/run`. |
| `POST` | `/api/v1/evaluation/feedback` | Legacy Feedback Loop | **Keep (DEV_MODE-only)** | Citizen / Dev | **No** | Modern replacement: `/admin/evals`. |
| `GET` | `/api/v1/review/{document_id}/health` | Legacy Health Review | **Keep (DEV_MODE-only)** | Citizen | **No** | Remounted and protected. |
| `GET` | `/api/v1/knowledge/statutes` | Legacy Statute Index | **Keep (DEV_MODE-only)** | Citizen / Public | **No** | Replaced by `/api/v1/library/search`. |
| `GET` | `/api/v1/knowledge/verify-citation` | Legacy Citation Verifier | **Keep (DEV_MODE-only)** | Citizen | **No** | Replaced by `/api/v1/library/passages/{id}`. |

---

## Verification & Isolation Proof
- **No Inbound Links:** Verified via crawler reachability (`python scripts/crawler_reachability.py` and BFS test suite). No link or button in the citizen or admin interface points to any `/api/v1/legacy/*`, `/api/v1/matters*`, or `/deeds/dev/*`.
- **404 When DEV_MODE=false:** Automated test `test_l2_legacy_dev_and_ingest_routes_return_404_when_dev_mode_false` in `tests/s9/test_s9_hardening.py` confirms that every dev and ingest endpoint returns HTTP 404 when `DEV_MODE=false`.
- **Preservation:** All source files under `backend/app/api/v1/` are preserved intact with zero deletions.
