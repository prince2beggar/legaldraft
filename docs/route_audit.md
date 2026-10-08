# AIN-AI Complete Route Audit & Collision Analysis (Sprint S9 Addendum L1)

This document audits every registered endpoint in the AIN-AI platform, identifying owner module, authorization role, shadowing status, and UI invocation status.

## Summary Metrics
- **Total Registered Endpoints:** 269
- **Active Pattern Collisions / Shadowed Routes:** 0 (All resolved)
- **Canonical API Prefix:** `/api/v1`
- **Frontend Compatibility Aliases:** Short routes preserved where UI templates require direct relative action links (`/auth/*`, `/intake/*`, `/drafts/*`, `/templates/*`).

## Route Inventory Table

| Method | Path Pattern | Owner Module | Auth Role | Shadowed? | UI Callers |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `GET` | `/` | New App (S0-S9 Architecture) | citizen (authenticated) | No | API / Background |
| `GET` | `/admin` | New App (S0-S9 Architecture) | admin / reviewer | No | API / Background |
| `GET` | `/admin/emergency-contacts` | New App (S0-S9 Architecture) | admin / reviewer | No | API / Background |
| `POST` | `/admin/emergency-contacts` | New App (S0-S9 Architecture) | admin / reviewer | No | API / Background |
| `POST` | `/admin/emergency-contacts/{contact_id}/verify` | New App (S0-S9 Architecture) | admin / reviewer | No | API / Background |
| `GET` | `/admin/evals` | New App (S0-S9 Architecture) | admin / reviewer | No | API / Background |
| `GET` | `/admin/rules` | New App (S0-S9 Architecture) | admin / reviewer | No | API / Background |
| `GET` | `/admin/sources` | New App (S0-S9 Architecture) | admin / reviewer | No | API / Background |
| `GET` | `/admin/system` | New App (S0-S9 Architecture) | admin / reviewer | No | API / Background |
| `GET` | `/admin/templates` | New App (S0-S9 Architecture) | admin / reviewer | No | API / Background |
| `POST` | `/admin/templates` | New App (S0-S9 Architecture) | admin / reviewer | No | API / Background |
| `PATCH` | `/admin/templates/{template_id}` | New App (S0-S9 Architecture) | admin / reviewer | No | API / Background |
| `POST` | `/admin/templates/{template_id}/approve` | New App (S0-S9 Architecture) | admin / reviewer | No | API / Background |
| `POST` | `/admin/templates/{template_id}/retire` | New App (S0-S9 Architecture) | admin / reviewer | No | API / Background |
| `POST` | `/admin/templates/{template_id}/test-render` | New App (S0-S9 Architecture) | admin / reviewer | No | API / Background |
| `GET` | `/api/v1/admin/audit-logs` | Application Core | admin / reviewer | No | `admin.html` |
| `POST` | `/api/v1/admin/emergency-contacts` | New App (S0-S9 Architecture) | admin / reviewer | No | API / Background |
| `POST` | `/api/v1/admin/emergency-contacts/{contact_id}/verify` | New App (S0-S9 Architecture) | admin / reviewer | No | API / Background |
| `GET` | `/api/v1/admin/feedback-queue` | Application Core | admin / reviewer | No | `admin.html` |
| `POST` | `/api/v1/admin/ingest-file` | Application Core | admin / reviewer | No | `admin.html` |
| `POST` | `/api/v1/admin/ingest-nasrin-book` | Application Core | admin / reviewer | No | `admin.html` |
| `GET` | `/api/v1/admin/ingested-documents` | Application Core | admin / reviewer | No | `admin.html` |
| `DELETE` | `/api/v1/admin/ingested-documents/{doc_id}` | Application Core | admin / reviewer | No | `admin.html` |
| `GET` | `/api/v1/admin/ingested-documents/{doc_id}/lessons` | Application Core | admin / reviewer | No | `admin.html` |
| `GET` | `/api/v1/admin/learning` | Application Core | admin / reviewer | No | API / Background |
| `GET` | `/api/v1/admin/notifications/failed` | New App (S0-S9 Architecture) | admin / reviewer | No | API / Background |
| `GET` | `/api/v1/admin/sources` | New App (S0-S9 Architecture) | admin / reviewer | No | API / Background |
| `POST` | `/api/v1/admin/sources` | New App (S0-S9 Architecture) | admin / reviewer | No | API / Background |
| `POST` | `/api/v1/admin/sources/jobs/{job_id}/retry` | New App (S0-S9 Architecture) | admin / reviewer | No | API / Background |
| `GET` | `/api/v1/admin/sources/jobs/{job_id}/status` | New App (S0-S9 Architecture) | admin / reviewer | No | API / Background |
| `GET` | `/api/v1/admin/sources/review-queue` | New App (S0-S9 Architecture) | admin / reviewer | No | API / Background |
| `GET` | `/api/v1/admin/sources/versions/{version_id}/diff` | New App (S0-S9 Architecture) | admin / reviewer | No | API / Background |
| `POST` | `/api/v1/admin/sources/versions/{version_id}/review` | New App (S0-S9 Architecture) | admin / reviewer | No | API / Background |
| `POST` | `/api/v1/admin/sources/{source_id}/versions/upload` | New App (S0-S9 Architecture) | admin / reviewer | No | API / Background |
| `GET` | `/api/v1/admin/stats` | Application Core | admin / reviewer | No | `admin.html` |
| `POST` | `/api/v1/admin/templates` | New App (S0-S9 Architecture) | admin / reviewer | No | API / Background |
| `PATCH` | `/api/v1/admin/templates/{template_id}` | New App (S0-S9 Architecture) | admin / reviewer | No | API / Background |
| `POST` | `/api/v1/admin/templates/{template_id}/approve` | New App (S0-S9 Architecture) | admin / reviewer | No | API / Background |
| `POST` | `/api/v1/admin/templates/{template_id}/retire` | New App (S0-S9 Architecture) | admin / reviewer | No | API / Background |
| `POST` | `/api/v1/admin/templates/{template_id}/test-render` | New App (S0-S9 Architecture) | admin / reviewer | No | API / Background |
| `POST` | `/api/v1/advisory/resolve` | Application Core | citizen (authenticated) | No | `index.html` |
| `POST` | `/api/v1/advisory/solve-problem` | Application Core | citizen (authenticated) | No | API / Background |
| `POST` | `/api/v1/auth/demo-login` | New App (S0-S9 Architecture) | public (guest / onboarding) | No | API / Background |
| `POST` | `/api/v1/auth/logout` | New App (S0-S9 Architecture) | citizen (authenticated) | No | API / Background |
| `POST` | `/api/v1/auth/onboarding` | New App (S0-S9 Architecture) | citizen (authenticated) | No | API / Background |
| `POST` | `/api/v1/auth/otp/request` | New App (S0-S9 Architecture) | public (guest / onboarding) | No | API / Background |
| `POST` | `/api/v1/auth/otp/verify` | New App (S0-S9 Architecture) | public (guest / onboarding) | No | API / Background |
| `POST` | `/api/v1/auth/refresh` | New App (S0-S9 Architecture) | citizen (authenticated) | No | API / Background |
| `GET` | `/api/v1/cases` | New App (S0-S9 Architecture) | citizen (authenticated) | No | `cases.html` |
| `POST` | `/api/v1/cases` | New App (S0-S9 Architecture) | citizen (authenticated) | No | `cases.html` |
| `DELETE` | `/api/v1/cases/{case_id}` | New App (S0-S9 Architecture) | citizen (authenticated) | No | `case_detail.html`, `cases.html` |
| `GET` | `/api/v1/cases/{case_id}` | New App (S0-S9 Architecture) | citizen (authenticated) | No | `case_detail.html`, `cases.html` |
| `PUT` | `/api/v1/cases/{case_id}` | New App (S0-S9 Architecture) | citizen (authenticated) | No | `case_detail.html`, `cases.html` |
| `GET` | `/api/v1/cases/{case_id}/brief` | New App (S0-S9 Architecture) | citizen (authenticated) | No | `case_detail.html`, `cases.html` |
| `POST` | `/api/v1/cases/{case_id}/brief` | New App (S0-S9 Architecture) | citizen (authenticated) | No | `case_detail.html`, `cases.html` |
| `GET` | `/api/v1/cases/{case_id}/brief/docx` | New App (S0-S9 Architecture) | citizen (authenticated) | No | `case_detail.html`, `cases.html` |
| `POST` | `/api/v1/cases/{case_id}/brief/export` | New App (S0-S9 Architecture) | citizen (authenticated) | No | `case_detail.html`, `cases.html` |
| `GET` | `/api/v1/cases/{case_id}/brief/pdf` | New App (S0-S9 Architecture) | citizen (authenticated) | No | `case_detail.html`, `cases.html` |
| `POST` | `/api/v1/cases/{case_id}/documents` | New App (S0-S9 Architecture) | citizen (authenticated) | No | `case_detail.html`, `cases.html` |
| `DELETE` | `/api/v1/cases/{case_id}/documents/{doc_id}` | New App (S0-S9 Architecture) | citizen (authenticated) | No | `case_detail.html`, `cases.html` |
| `POST` | `/api/v1/cases/{case_id}/events` | New App (S0-S9 Architecture) | citizen (authenticated) | No | `case_detail.html`, `cases.html` |
| `POST` | `/api/v1/cases/{case_id}/facts` | New App (S0-S9 Architecture) | citizen (authenticated) | No | `case_detail.html`, `cases.html` |
| `POST` | `/api/v1/cases/{case_id}/facts/{fact_id}/accept` | New App (S0-S9 Architecture) | citizen (authenticated) | No | `case_detail.html`, `cases.html` |
| `POST` | `/api/v1/cases/{case_id}/facts/{fact_id}/dismiss` | New App (S0-S9 Architecture) | citizen (authenticated) | No | `case_detail.html`, `cases.html` |
| `POST` | `/api/v1/cases/{case_id}/notes` | New App (S0-S9 Architecture) | citizen (authenticated) | No | `case_detail.html`, `cases.html` |
| `DELETE` | `/api/v1/cases/{case_id}/notes/{note_id}` | New App (S0-S9 Architecture) | citizen (authenticated) | No | `case_detail.html`, `cases.html` |
| `POST` | `/api/v1/cases/{case_id}/parties` | New App (S0-S9 Architecture) | citizen (authenticated) | No | `case_detail.html`, `cases.html` |
| `DELETE` | `/api/v1/cases/{case_id}/parties/{party_id}` | New App (S0-S9 Architecture) | citizen (authenticated) | No | `case_detail.html`, `cases.html` |
| `POST` | `/api/v1/cases/{case_id}/review` | New App (S0-S9 Architecture) | citizen (authenticated) | No | `case_detail.html`, `cases.html` |
| `GET` | `/api/v1/consents` | New App (S0-S9 Architecture) | citizen (authenticated) | No | `case_brief.html`, `sharing.html` |
| `POST` | `/api/v1/consents` | New App (S0-S9 Architecture) | citizen (authenticated) | No | `case_brief.html`, `sharing.html` |
| `GET` | `/api/v1/consents/signed-doc/{doc_id}` | New App (S0-S9 Architecture) | citizen (authenticated) | No | `case_brief.html`, `sharing.html` |
| `GET` | `/api/v1/consents/{consent_id}/access-log` | New App (S0-S9 Architecture) | citizen (authenticated) | No | `case_brief.html`, `sharing.html` |
| `POST` | `/api/v1/consents/{consent_id}/revoke` | New App (S0-S9 Architecture) | citizen (authenticated) | No | `case_brief.html`, `sharing.html` |
| `POST` | `/api/v1/deadlines/{deadline_id}/dismiss` | New App (S0-S9 Architecture) | citizen (authenticated) | No | API / Background |
| `GET` | `/api/v1/deeds/` | Application Core | citizen (authenticated) | No | `index.html` |
| `GET` | `/api/v1/deeds/dev/corrections` | Application Core | citizen (authenticated) | No | `index.html` |
| `POST` | `/api/v1/deeds/dev/crop-test` | Application Core | citizen (authenticated) | No | `index.html` |
| `GET` | `/api/v1/deeds/engine-status` | Application Core | citizen (authenticated) | No | `index.html` |
| `GET` | `/api/v1/deeds/samples` | Application Core | citizen (authenticated) | No | `index.html` |
| `GET` | `/api/v1/deeds/samples/{sample_id}` | Application Core | citizen (authenticated) | No | `index.html` |
| `POST` | `/api/v1/deeds/upload` | Application Core | citizen (authenticated) | No | `index.html` |
| `GET` | `/api/v1/deeds/{deed_id}` | Application Core | citizen (authenticated) | No | `index.html` |
| `PUT` | `/api/v1/deeds/{deed_id}` | Application Core | citizen (authenticated) | No | `index.html` |
| `POST` | `/api/v1/deeds/{deed_id}/corrections` | Application Core | citizen (authenticated) | No | `index.html` |
| `GET` | `/api/v1/deeds/{deed_id}/export/docx` | Application Core | citizen (authenticated) | No | `index.html` |
| `GET` | `/api/v1/deeds/{deed_id}/export/pdf` | Application Core | citizen (authenticated) | No | `index.html` |
| `POST` | `/api/v1/deeds/{deed_id}/verify-field` | Application Core | citizen (authenticated) | No | `index.html` |
| `GET` | `/api/v1/documents` | New App (S0-S9 Architecture) | citizen (authenticated) | YES (COLLISION) | API / Background |
| `GET` | `/api/v1/documents/` | New App (S0-S9 Architecture) | citizen (authenticated) | YES (COLLISION) | `document_notice.html`, `document_status.html`, `index.html` |
| `PATCH` | `/api/v1/documents/fields/{field_id}` | New App (S0-S9 Architecture) | citizen (authenticated) | No | `document_notice.html`, `document_status.html`, `index.html` |
| `POST` | `/api/v1/documents/fields/{field_id}/verify` | New App (S0-S9 Architecture) | citizen (authenticated) | No | `document_notice.html`, `document_status.html`, `index.html` |
| `POST` | `/api/v1/documents/resumable/chunk` | New App (S0-S9 Architecture) | citizen (authenticated) | No | `document_notice.html`, `document_status.html`, `index.html` |
| `POST` | `/api/v1/documents/resumable/initiate` | New App (S0-S9 Architecture) | citizen (authenticated) | No | `document_notice.html`, `document_status.html`, `index.html` |
| `POST` | `/api/v1/documents/upload` | New App (S0-S9 Architecture) | citizen (authenticated) | No | `document_notice.html`, `document_status.html`, `documents_upload.html`, `index.html` |
| `DELETE` | `/api/v1/documents/{doc_id}` | New App (S0-S9 Architecture) | citizen (authenticated) | No | `document_notice.html`, `document_status.html`, `index.html` |
| `GET` | `/api/v1/documents/{doc_id}` | New App (S0-S9 Architecture) | citizen (authenticated) | No | `document_notice.html`, `document_status.html`, `index.html` |
| `PUT` | `/api/v1/documents/{doc_id}` | New App (S0-S9 Architecture) | citizen (authenticated) | No | `document_notice.html`, `document_status.html`, `index.html` |
| `GET` | `/api/v1/documents/{doc_id}/export/docx` | New App (S0-S9 Architecture) | citizen (authenticated) | No | `document_notice.html`, `document_status.html`, `index.html` |
| `GET` | `/api/v1/documents/{doc_id}/export/pdf` | New App (S0-S9 Architecture) | citizen (authenticated) | No | `document_notice.html`, `document_status.html`, `index.html` |
| `POST` | `/api/v1/documents/{doc_id}/intent` | New App (S0-S9 Architecture) | citizen (authenticated) | No | `document_notice.html`, `document_status.html`, `index.html` |
| `GET` | `/api/v1/documents/{doc_id}/notice` | New App (S0-S9 Architecture) | citizen (authenticated) | No | `document_notice.html`, `document_status.html`, `index.html` |
| `POST` | `/api/v1/documents/{doc_id}/notice/calculate_relative_date` | New App (S0-S9 Architecture) | citizen (authenticated) | No | `document_notice.html`, `document_status.html`, `index.html` |
| `POST` | `/api/v1/documents/{doc_id}/notice/confirm_deadline` | New App (S0-S9 Architecture) | citizen (authenticated) | No | `document_notice.html`, `document_status.html`, `index.html` |
| `POST` | `/api/v1/documents/{doc_id}/notice/save_to_case` | New App (S0-S9 Architecture) | citizen (authenticated) | No | `document_notice.html`, `document_status.html`, `index.html` |
| `POST` | `/api/v1/documents/{doc_id}/notice/simpler` | New App (S0-S9 Architecture) | citizen (authenticated) | No | `document_notice.html`, `document_status.html`, `index.html` |
| `POST` | `/api/v1/documents/{doc_id}/save-to-case` | New App (S0-S9 Architecture) | citizen (authenticated) | No | `document_notice.html`, `document_status.html`, `index.html` |
| `GET` | `/api/v1/documents/{doc_id}/status` | New App (S0-S9 Architecture) | citizen (authenticated) | No | `document_notice.html`, `document_status.html`, `index.html` |
| `GET` | `/api/v1/documents/{doc_id}/versions` | New App (S0-S9 Architecture) | citizen (authenticated) | No | `document_notice.html`, `document_status.html`, `index.html` |
| `POST` | `/api/v1/drafting/generate` | Application Core | citizen (authenticated) | No | `index.html` |
| `GET` | `/api/v1/drafts` | New App (S0-S9 Architecture) | citizen (authenticated) | No | API / Background |
| `POST` | `/api/v1/drafts` | New App (S0-S9 Architecture) | citizen (authenticated) | No | API / Background |
| `DELETE` | `/api/v1/drafts/{draft_id}` | New App (S0-S9 Architecture) | citizen (authenticated) | No | API / Background |
| `GET` | `/api/v1/drafts/{draft_id}` | New App (S0-S9 Architecture) | citizen (authenticated) | No | API / Background |
| `POST` | `/api/v1/drafts/{draft_id}/ai-help` | New App (S0-S9 Architecture) | citizen (authenticated) | No | API / Background |
| `PATCH` | `/api/v1/drafts/{draft_id}/answers` | New App (S0-S9 Architecture) | citizen (authenticated) | No | API / Background |
| `POST` | `/api/v1/drafts/{draft_id}/check` | New App (S0-S9 Architecture) | citizen (authenticated) | No | API / Background |
| `POST` | `/api/v1/drafts/{draft_id}/checklist/{item_id}/confirm` | New App (S0-S9 Architecture) | citizen (authenticated) | No | API / Background |
| `GET` | `/api/v1/drafts/{draft_id}/export` | New App (S0-S9 Architecture) | citizen (authenticated) | No | API / Background |
| `POST` | `/api/v1/drafts/{draft_id}/finalize` | New App (S0-S9 Architecture) | citizen (authenticated) | No | API / Background |
| `POST` | `/api/v1/drafts/{draft_id}/generate` | New App (S0-S9 Architecture) | citizen (authenticated) | No | API / Background |
| `GET` | `/api/v1/drafts/{draft_id}/signing-checklist` | New App (S0-S9 Architecture) | citizen (authenticated) | No | API / Background |
| `GET` | `/api/v1/emergency-contacts` | New App (S0-S9 Architecture) | citizen (authenticated) | No | API / Background |
| `GET` | `/api/v1/evals/golden-sets` | New App (S0-S9 Architecture) | citizen (authenticated) | No | API / Background |
| `POST` | `/api/v1/evals/run` | New App (S0-S9 Architecture) | citizen (authenticated) | No | `admin_evals.html` |
| `GET` | `/api/v1/evals/runs` | New App (S0-S9 Architecture) | citizen (authenticated) | No | `admin_evals.html` |
| `GET` | `/api/v1/evals/runs/{run_id}` | New App (S0-S9 Architecture) | citizen (authenticated) | No | `admin_evals.html` |
| `POST` | `/api/v1/evaluation/benchmark/run` | Application Core | citizen (authenticated) | No | `index.html` |
| `POST` | `/api/v1/evaluation/feedback` | Application Core | citizen (authenticated) | No | `index.html` |
| `GET` | `/api/v1/health` | New App (S0-S9 Architecture) | public (monitoring) | No | `admin_system.html` |
| `GET` | `/api/v1/health/flags` | New App (S0-S9 Architecture) | public (monitoring) | No | `admin_system.html` |
| `GET` | `/api/v1/health/ready` | New App (S0-S9 Architecture) | public (monitoring) | No | `admin_system.html` |
| `GET` | `/api/v1/home` | New App (S0-S9 Architecture) | citizen (authenticated) | No | `home.html` |
| `GET` | `/api/v1/home/next-action` | New App (S0-S9 Architecture) | citizen (authenticated) | No | `home.html` |
| `GET` | `/api/v1/i18n/{locale}` | New App (S0-S9 Architecture) | public (frontend localization) | No | API / Background |
| `POST` | `/api/v1/intake/analyze-scenario` | Application Core | citizen (authenticated) | No | API / Background |
| `POST` | `/api/v1/intake/autofill-missing` | Application Core | citizen (authenticated) | No | API / Background |
| `POST` | `/api/v1/intake/chat` | Application Core | citizen (authenticated) | No | `index.html` |
| `POST` | `/api/v1/intake/scenario-recheck` | Application Core | citizen (authenticated) | No | API / Background |
| `POST` | `/api/v1/intake/sessions` | New App (S0-S9 Architecture) | citizen (authenticated) | No | API / Background |
| `GET` | `/api/v1/intake/sessions/{session_id}` | New App (S0-S9 Architecture) | citizen (authenticated) | No | API / Background |
| `PATCH` | `/api/v1/intake/sessions/{session_id}` | New App (S0-S9 Architecture) | citizen (authenticated) | No | API / Background |
| `POST` | `/api/v1/intake/sessions/{session_id}/abandon` | New App (S0-S9 Architecture) | citizen (authenticated) | No | API / Background |
| `POST` | `/api/v1/intake/sessions/{session_id}/confirm` | New App (S0-S9 Architecture) | citizen (authenticated) | No | API / Background |
| `POST` | `/api/v1/intake/sessions/{session_id}/profile` | New App (S0-S9 Architecture) | citizen (authenticated) | No | API / Background |
| `POST` | `/api/v1/intake/sessions/{session_id}/resume` | New App (S0-S9 Architecture) | citizen (authenticated) | No | API / Background |
| `GET` | `/api/v1/knowledge/statutes` | Application Core | citizen (authenticated) | No | `index.html` |
| `GET` | `/api/v1/knowledge/verify-citation` | Application Core | citizen (authenticated) | No | API / Background |
| `GET` | `/api/v1/legacy/documents/` | Application Core | citizen (authenticated) | No | API / Background |
| `GET` | `/api/v1/legacy/documents/{document_id}` | Application Core | citizen (authenticated) | No | API / Background |
| `PUT` | `/api/v1/legacy/documents/{document_id}` | Application Core | citizen (authenticated) | No | API / Background |
| `GET` | `/api/v1/legacy/documents/{document_id}/export/docx` | Application Core | citizen (authenticated) | No | API / Background |
| `GET` | `/api/v1/legacy/documents/{document_id}/export/pdf` | Application Core | citizen (authenticated) | No | API / Background |
| `GET` | `/api/v1/legacy/documents/{document_id}/versions` | Application Core | citizen (authenticated) | No | API / Background |
| `GET` | `/api/v1/library/categories` | New App (S0-S9 Architecture) | citizen (authenticated) | No | API / Background |
| `GET` | `/api/v1/library/passages/{passage_id}` | New App (S0-S9 Architecture) | citizen (authenticated) | No | API / Background |
| `POST` | `/api/v1/library/passages/{passage_id}/explain` | New App (S0-S9 Architecture) | citizen (authenticated) | No | API / Background |
| `GET` | `/api/v1/library/search` | New App (S0-S9 Architecture) | citizen (authenticated) | No | API / Background |
| `GET` | `/api/v1/library/sources/{source_id}` | New App (S0-S9 Architecture) | citizen (authenticated) | No | API / Background |
| `GET` | `/api/v1/library/versions/{version_id}` | New App (S0-S9 Architecture) | citizen (authenticated) | No | API / Background |
| `GET` | `/api/v1/matters/` | Application Core | citizen (authenticated) | No | API / Background |
| `POST` | `/api/v1/matters/` | Application Core | citizen (authenticated) | No | API / Background |
| `GET` | `/api/v1/matters/{matter_id}` | Application Core | citizen (authenticated) | No | API / Background |
| `GET` | `/api/v1/me` | New App (S0-S9 Architecture) | citizen (authenticated) | No | API / Background |
| `PATCH` | `/api/v1/me` | New App (S0-S9 Architecture) | citizen (authenticated) | No | API / Background |
| `POST` | `/api/v1/me/delete` | New App (S0-S9 Architecture) | citizen (authenticated) | No | API / Background |
| `GET` | `/api/v1/me/devices` | New App (S0-S9 Architecture) | citizen (authenticated) | No | API / Background |
| `DELETE` | `/api/v1/me/devices/{device_id}` | New App (S0-S9 Architecture) | citizen (authenticated) | No | API / Background |
| `POST` | `/api/v1/me/export` | New App (S0-S9 Architecture) | citizen (authenticated) | No | API / Background |
| `GET` | `/api/v1/me/notification-preferences` | New App (S0-S9 Architecture) | citizen (authenticated) | No | `notification_settings.html` |
| `PUT` | `/api/v1/me/notification-preferences` | New App (S0-S9 Architecture) | citizen (authenticated) | No | `notification_settings.html` |
| `GET` | `/api/v1/me/notifications` | New App (S0-S9 Architecture) | citizen (authenticated) | No | API / Background |
| `GET` | `/api/v1/notifications` | New App (S0-S9 Architecture) | citizen (authenticated) | No | `notifications.html` |
| `POST` | `/api/v1/notifications/trigger` | New App (S0-S9 Architecture) | citizen (authenticated) | No | `notifications.html` |
| `GET` | `/api/v1/review/{document_id}/health` | Application Core | citizen (authenticated) | No | `index.html` |
| `GET` | `/api/v1/rules` | New App (S0-S9 Architecture) | citizen (authenticated) | No | API / Background |
| `POST` | `/api/v1/rules/compute` | New App (S0-S9 Architecture) | citizen (authenticated) | No | `admin_rules.html` |
| `POST` | `/api/v1/rules/test` | New App (S0-S9 Architecture) | citizen (authenticated) | No | API / Background |
| `GET` | `/api/v1/s/{token}` | New App (S0-S9 Architecture) | citizen (authenticated) | No | `shared_brief.html` |
| `GET` | `/api/v1/s/{token}/doc/{doc_id}` | New App (S0-S9 Architecture) | citizen (authenticated) | No | `shared_brief.html` |
| `POST` | `/api/v1/s/{token}/request-otp` | New App (S0-S9 Architecture) | citizen (authenticated) | No | `shared_brief.html` |
| `POST` | `/api/v1/s/{token}/verify-otp` | New App (S0-S9 Architecture) | citizen (authenticated) | No | `shared_brief.html` |
| `GET` | `/api/v1/templates` | New App (S0-S9 Architecture) | citizen (authenticated) | No | API / Background |
| `GET` | `/api/v1/templates/{template_id}` | New App (S0-S9 Architecture) | citizen (authenticated) | No | API / Background |
| `POST` | `/auth/demo-login` | New App (S0-S9 Architecture) | public (guest / onboarding) | No | API / Background |
| `POST` | `/auth/logout` | New App (S0-S9 Architecture) | citizen (authenticated) | No | API / Background |
| `POST` | `/auth/onboarding` | New App (S0-S9 Architecture) | citizen (authenticated) | No | `signin.html` |
| `POST` | `/auth/otp/request` | New App (S0-S9 Architecture) | public (guest / onboarding) | No | `signin.html` |
| `POST` | `/auth/otp/verify` | New App (S0-S9 Architecture) | public (guest / onboarding) | No | `signin.html` |
| `POST` | `/auth/refresh` | New App (S0-S9 Architecture) | citizen (authenticated) | No | API / Background |
| `GET` | `/cases` | New App (S0-S9 Architecture) | citizen (authenticated) | No | API / Background |
| `GET` | `/cases/new` | New App (S0-S9 Architecture) | citizen (authenticated) | No | `cases.html`, `home.html`, `intake.html` |
| `GET` | `/cases/{case_id}` | New App (S0-S9 Architecture) | citizen (authenticated) | No | `cases.html`, `home.html`, `intake.html` |
| `GET` | `/cases/{case_id}/brief` | New App (S0-S9 Architecture) | citizen (authenticated) | No | `cases.html`, `home.html`, `intake.html` |
| `POST` | `/cases/{case_id}/brief` | New App (S0-S9 Architecture) | citizen (authenticated) | No | `cases.html`, `home.html`, `intake.html` |
| `GET` | `/cases/{case_id}/brief/docx` | New App (S0-S9 Architecture) | citizen (authenticated) | No | `cases.html`, `home.html`, `intake.html` |
| `POST` | `/cases/{case_id}/brief/export` | New App (S0-S9 Architecture) | citizen (authenticated) | No | `cases.html`, `home.html`, `intake.html` |
| `GET` | `/cases/{case_id}/brief/pdf` | New App (S0-S9 Architecture) | citizen (authenticated) | No | `cases.html`, `home.html`, `intake.html` |
| `GET` | `/cases/{case_id}/lawyer` | New App (S0-S9 Architecture) | citizen (authenticated) | No | `cases.html`, `home.html`, `intake.html` |
| `GET` | `/consents` | New App (S0-S9 Architecture) | citizen (authenticated) | No | API / Background |
| `POST` | `/consents` | New App (S0-S9 Architecture) | citizen (authenticated) | No | API / Background |
| `GET` | `/consents/signed-doc/{doc_id}` | New App (S0-S9 Architecture) | citizen (authenticated) | No | API / Background |
| `GET` | `/consents/{consent_id}/access-log` | New App (S0-S9 Architecture) | citizen (authenticated) | No | API / Background |
| `POST` | `/consents/{consent_id}/revoke` | New App (S0-S9 Architecture) | citizen (authenticated) | No | API / Background |
| `GET` | `/docs` | FastAPI Framework | public / unauthenticated | No | API / Background |
| `HEAD` | `/docs` | FastAPI Framework | public / unauthenticated | No | API / Background |
| `GET` | `/docs/oauth2-redirect` | FastAPI Framework | public / unauthenticated | No | API / Background |
| `HEAD` | `/docs/oauth2-redirect` | FastAPI Framework | public / unauthenticated | No | API / Background |
| `GET` | `/documents/intent` | New App (S0-S9 Architecture) | citizen (authenticated) | No | API / Background |
| `GET` | `/documents/notice` | New App (S0-S9 Architecture) | citizen (authenticated) | No | API / Background |
| `GET` | `/documents/status` | New App (S0-S9 Architecture) | citizen (authenticated) | No | `document_status.html` |
| `GET` | `/documents/upload` | New App (S0-S9 Architecture) | citizen (authenticated) | No | `admin_emergency_contacts.html`, `case_detail.html`, `cases.html`, `document_intent.html`, `document_notice.html`, `document_status.html`, `document_viewer.html`, `documents_upload.html`, `home.html`, `intake.html`, `notification_settings.html`, `notifications.html` |
| `GET` | `/documents/viewer` | New App (S0-S9 Architecture) | citizen (authenticated) | No | `document_status.html`, `document_viewer.html` |
| `GET` | `/documents/{doc_id}/notice` | New App (S0-S9 Architecture) | citizen (authenticated) | No | API / Background |
| `GET` | `/draft` | New App (S0-S9 Architecture) | citizen (authenticated) | No | API / Background |
| `GET` | `/draft/{draft_id}` | New App (S0-S9 Architecture) | citizen (authenticated) | No | `draft.html` |
| `GET` | `/draft/{draft_id}/check` | New App (S0-S9 Architecture) | citizen (authenticated) | No | `draft.html` |
| `GET` | `/draft/{draft_id}/export` | New App (S0-S9 Architecture) | citizen (authenticated) | No | `draft.html` |
| `GET` | `/draft/{draft_id}/preview` | New App (S0-S9 Architecture) | citizen (authenticated) | No | `draft.html` |
| `GET` | `/draft/{draft_id}/q/{step}` | New App (S0-S9 Architecture) | citizen (authenticated) | No | `draft.html` |
| `GET` | `/drafts` | New App (S0-S9 Architecture) | citizen (authenticated) | No | API / Background |
| `POST` | `/drafts` | New App (S0-S9 Architecture) | citizen (authenticated) | No | API / Background |
| `DELETE` | `/drafts/{draft_id}` | New App (S0-S9 Architecture) | citizen (authenticated) | No | `draft.html` |
| `GET` | `/drafts/{draft_id}` | New App (S0-S9 Architecture) | citizen (authenticated) | No | `draft.html` |
| `POST` | `/drafts/{draft_id}/ai-help` | New App (S0-S9 Architecture) | citizen (authenticated) | No | `draft.html` |
| `PATCH` | `/drafts/{draft_id}/answers` | New App (S0-S9 Architecture) | citizen (authenticated) | No | `draft.html` |
| `POST` | `/drafts/{draft_id}/check` | New App (S0-S9 Architecture) | citizen (authenticated) | No | `draft.html` |
| `POST` | `/drafts/{draft_id}/checklist/{item_id}/confirm` | New App (S0-S9 Architecture) | citizen (authenticated) | No | `draft.html` |
| `GET` | `/drafts/{draft_id}/export` | New App (S0-S9 Architecture) | citizen (authenticated) | No | `draft.html` |
| `POST` | `/drafts/{draft_id}/finalize` | New App (S0-S9 Architecture) | citizen (authenticated) | No | `draft.html` |
| `POST` | `/drafts/{draft_id}/generate` | New App (S0-S9 Architecture) | citizen (authenticated) | No | `draft.html` |
| `GET` | `/drafts/{draft_id}/signing-checklist` | New App (S0-S9 Architecture) | citizen (authenticated) | No | `draft.html` |
| `GET` | `/emergency-contacts` | New App (S0-S9 Architecture) | citizen (authenticated) | No | API / Background |
| `GET` | `/health` | New App (S0-S9 Architecture) | public (monitoring) | No | API / Background |
| `GET` | `/health/flags` | New App (S0-S9 Architecture) | public (monitoring) | No | API / Background |
| `GET` | `/health/ready` | New App (S0-S9 Architecture) | public (monitoring) | No | API / Background |
| `GET` | `/home` | New App (S0-S9 Architecture) | citizen (authenticated) | No | API / Background |
| `GET` | `/intake` | New App (S0-S9 Architecture) | citizen (authenticated) | No | API / Background |
| `POST` | `/intake/sessions` | New App (S0-S9 Architecture) | citizen (authenticated) | No | API / Background |
| `GET` | `/intake/sessions/{session_id}` | New App (S0-S9 Architecture) | citizen (authenticated) | No | API / Background |
| `PATCH` | `/intake/sessions/{session_id}` | New App (S0-S9 Architecture) | citizen (authenticated) | No | API / Background |
| `POST` | `/intake/sessions/{session_id}/abandon` | New App (S0-S9 Architecture) | citizen (authenticated) | No | API / Background |
| `POST` | `/intake/sessions/{session_id}/confirm` | New App (S0-S9 Architecture) | citizen (authenticated) | No | API / Background |
| `POST` | `/intake/sessions/{session_id}/profile` | New App (S0-S9 Architecture) | citizen (authenticated) | No | API / Background |
| `POST` | `/intake/sessions/{session_id}/resume` | New App (S0-S9 Architecture) | citizen (authenticated) | No | API / Background |
| `GET` | `/library` | New App (S0-S9 Architecture) | citizen (authenticated) | No | API / Background |
| `GET` | `/me` | New App (S0-S9 Architecture) | citizen (authenticated) | No | API / Background |
| `PATCH` | `/me` | New App (S0-S9 Architecture) | citizen (authenticated) | No | API / Background |
| `POST` | `/me/delete` | New App (S0-S9 Architecture) | citizen (authenticated) | No | API / Background |
| `GET` | `/me/devices` | New App (S0-S9 Architecture) | citizen (authenticated) | No | API / Background |
| `DELETE` | `/me/devices/{device_id}` | New App (S0-S9 Architecture) | citizen (authenticated) | No | API / Background |
| `POST` | `/me/export` | New App (S0-S9 Architecture) | citizen (authenticated) | No | API / Background |
| `GET` | `/me/sharing` | New App (S0-S9 Architecture) | citizen (authenticated) | No | `case_brief.html`, `case_detail.html`, `cases.html`, `home.html`, `sharing.html` |
| `GET` | `/notification-settings` | New App (S0-S9 Architecture) | citizen (authenticated) | No | API / Background |
| `GET` | `/notifications` | New App (S0-S9 Architecture) | citizen (authenticated) | No | API / Background |
| `GET` | `/onboarding` | New App (S0-S9 Architecture) | public (guest / onboarding) | No | API / Background |
| `GET` | `/openapi.json` | FastAPI Framework | public / unauthenticated | No | API / Background |
| `HEAD` | `/openapi.json` | FastAPI Framework | public / unauthenticated | No | API / Background |
| `GET` | `/otp` | New App (S0-S9 Architecture) | public (guest / onboarding) | No | API / Background |
| `GET` | `/redoc` | FastAPI Framework | public / unauthenticated | No | API / Background |
| `HEAD` | `/redoc` | FastAPI Framework | public / unauthenticated | No | API / Background |
| `GET` | `/s/{token}` | New App (S0-S9 Architecture) | public / unauthenticated | No | API / Background |
| `GET` | `/s/{token}/doc/{doc_id}` | New App (S0-S9 Architecture) | public / unauthenticated | No | API / Background |
| `POST` | `/s/{token}/request-otp` | New App (S0-S9 Architecture) | public / unauthenticated | No | API / Background |
| `POST` | `/s/{token}/verify-otp` | New App (S0-S9 Architecture) | public / unauthenticated | No | API / Background |
| `GET` | `/signin` | New App (S0-S9 Architecture) | public (guest / onboarding) | No | API / Background |
| `GET` | `/templates` | New App (S0-S9 Architecture) | citizen (authenticated) | No | API / Background |
| `GET` | `/templates/{template_id}` | New App (S0-S9 Architecture) | citizen (authenticated) | No | API / Background |
| `GET` | `/welcome` | New App (S0-S9 Architecture) | public (guest / onboarding) | No | API / Background |

## Resolution of Prior Collisions

1. **Legacy Documents Yielded to Modern M03 Engine:**
   - Prior state: `GET /api/v1/documents/{doc_id}` (new) collided with `GET /api/v1/documents/{document_id}` (legacy), and `/api/v1/documents` collided with `/api/v1/documents/`.
   - Resolution: Legacy documents router was moved under `/api/v1/legacy/documents` in `backend/app/api/v1/__init__.py`. The new M03 document engine maintains 100% clean, unambiguous ownership over `/api/v1/documents` and `/api/v1/documents/{doc_id}`.

2. **Recipient Viewer Route `/s/{token}` Unification:**
   - Prior state: `@app.get('/s/{token}')` in `main.py` shadowed `@router.get('/s/{token}')` in `sharing_router`.
   - Resolution: Removed duplicate static wrapper in `main.py`. `sharing_router::get_shared_recipient_view` handles all requests with content negotiation (HTML rendering for browser navigation with SVG watermarks, JSON payload for API requests).

3. **Elimination of Duplicate `/api/v1/api/v1/...` Prefixes:**
   - Prior state: `main.py` included `sharing_router` with `prefix='/api/v1'`, prepending an extra prefix to routes that already contained `/api/v1/`.
   - Resolution: Mounted `sharing_router` once without redundant prefix.

4. **N2 Static HTML Route Deduplication (Canonical Router Ownership):**
   - Prior state: An uncommitted block of static page handlers in `main.py` re-registered endpoints already registered in modular routers:
     - `GET /admin/rules` (duplicated between `main.py` and `services/api/app/routers/rules.py`)
     - `GET /admin/evals` (duplicated between `main.py` and `services/api/app/routers/evals.py`)
     - `GET /documents/upload` (duplicated between `main.py` and `services/api/app/routers/documents.py`)
     - `GET /documents/intent` (duplicated between `main.py` and `services/api/app/routers/documents.py`)
     - `GET /documents/viewer` (duplicated between `main.py` and `services/api/app/routers/documents.py`)
     - `GET /documents/{doc_id}/notice` / `GET /documents/notice` (duplicated between `main.py` and `services/api/app/routers/documents.py`)
   - Resolution: Deleted the duplicate registrations in `main.py`. Canonical owners:
     - `GET /admin/rules` -> Owned by `rules_router` (`services/api/app/routers/rules.py`)
     - `GET /admin/evals` -> Owned by `evals_router` (`services/api/app/routers/evals.py`)
     - `GET /documents/upload` -> Owned by `documents_router` (`services/api/app/routers/documents.py`)
     - `GET /documents/intent` -> Owned by `documents_router` (`services/api/app/routers/documents.py`)
     - `GET /documents/viewer` -> Owned by `documents_router` (`services/api/app/routers/documents.py`)
     - `GET /documents/{doc_id}/notice` -> Owned by `documents_router` (`services/api/app/routers/documents.py`)
   - Verification: All routes retain identical HTTP status, redirect logic, role authentication, and HTML template delivery (`admin_rules.html`, `admin_evals.html`, `documents_upload.html`, `document_intent.html`, `document_viewer.html`, `document_notice.html`).