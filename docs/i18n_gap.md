# Internationalization (i18n) Gap Analysis & Roadmap (X-003)

> **Sprint S9 Status:** **NOT SATISFIED / GAP DOCUMENTED**
> While backend translation catalog parity (`/content/i18n/bn.json` and `en.json`) is verified across 76 dictionary keys, the frontend static HTML templates currently utilize hardcoded Bengali strings directly in markup. Full dynamic DOM internationalization is **NOT** satisfied.

---

## 1. Inventory Summary

- **Total Static HTML Files Audited:** 25
- **Total User-Facing Strings Analyzed:** 1,236
- **Hard-coded Bengali Strings:** 1,182 (95.6%)
- **Hard-coded English Strings:** 54 (4.4%)
- **Elements with `data-i18n` Translation Keys:** 0 (0.0% coverage)
- **Estimated Keys to Extract:** ~450 to 550 unique semantic translation keys (after deduplicating navigation, button labels, and shared status indicators)

---

## 2. Top Files with Most Hard-Coded Text

The following 5 files contain the largest concentration of hardcoded strings:

| Rank | File Name | Total Strings | Bengali Strings | English Strings | Description / Context |
|---|---|---|---|---|---|
| 1 | `index.html` | 218 | 205 | 13 | Core citizen/admin workflow template |
| 2 | `admin_system.html` | 95 | 81 | 14 | Core citizen/admin workflow template |
| 3 | `document_viewer.html` | 72 | 72 | 0 | Core citizen/admin workflow template |
| 4 | `admin.html` | 69 | 61 | 8 | Core citizen/admin workflow template |
| 5 | `admin_sources.html` | 67 | 63 | 4 | Core citizen/admin workflow template |

---

## 3. Complete File-by-File String Inventory

| File Name | Total Strings | Hard-coded Bengali | Hard-coded English | `data-i18n` Keyed | Coverage % |
|---|---|---|---|---|---|
| `index.html` | 218 | 205 | 13 | 0 | 0.0% |
| `admin_system.html` | 95 | 81 | 14 | 0 | 0.0% |
| `document_viewer.html` | 72 | 72 | 0 | 0 | 0.0% |
| `admin.html` | 69 | 61 | 8 | 0 | 0.0% |
| `admin_sources.html` | 67 | 63 | 4 | 0 | 0.0% |
| `case_brief.html` | 63 | 63 | 0 | 0 | 0.0% |
| `admin_evals.html` | 57 | 49 | 8 | 0 | 0.0% |
| `case_detail.html` | 53 | 53 | 0 | 0 | 0.0% |
| `draft.html` | 48 | 47 | 1 | 0 | 0.0% |
| `document_notice.html` | 47 | 47 | 0 | 0 | 0.0% |
| `signin.html` | 45 | 42 | 3 | 0 | 0.0% |
| `document_status.html` | 40 | 39 | 1 | 0 | 0.0% |
| `home.html` | 40 | 40 | 0 | 0 | 0.0% |
| `admin_rules.html` | 39 | 38 | 1 | 0 | 0.0% |
| `library.html` | 36 | 36 | 0 | 0 | 0.0% |
| `cases.html` | 32 | 32 | 0 | 0 | 0.0% |
| `documents_upload.html` | 30 | 30 | 0 | 0 | 0.0% |
| `shared_brief.html` | 30 | 30 | 0 | 0 | 0.0% |
| `admin_templates.html` | 29 | 29 | 0 | 0 | 0.0% |
| `intake.html` | 26 | 26 | 0 | 0 | 0.0% |
| `notification_settings.html` | 26 | 25 | 1 | 0 | 0.0% |
| `document_intent.html` | 24 | 24 | 0 | 0 | 0.0% |
| `admin_emergency_contacts.html` | 23 | 23 | 0 | 0 | 0.0% |
| `sharing.html` | 14 | 14 | 0 | 0 | 0.0% |
| `notifications.html` | 13 | 13 | 0 | 0 | 0.0% |

---

## 4. Proposed Minimal Client-Side i18n Architecture

To avoid heavy third-party framework overhead, the proposed implementation uses a single lightweight vanilla JavaScript module (`i18n.js`):

### Architecture Specification:
1. **Catalog Delivery:** On page initialization, `i18n.js` detects the user's preferred language (from `localStorage.getItem('lang')` or `navigator.language` or query param `?lang=...`, defaulting to `bn`).
2. **Catalog Fetch & Caching:** Calls `GET /api/v1/i18n/{locale}` once and caches the dictionary in `sessionStorage`.
3. **DOM Attribute Translation:**
   - Elements use `data-i18n="key_name"` for text content.
   - Elements use `data-i18n-placeholder="key_name"` for input placeholders.
   - Elements use `data-i18n-title="key_name"` for tooltips / aria-labels.
4. **Dynamic DOM Sweep:** `i18n.applyTranslations()` queries `document.querySelectorAll('[data-i18n], [data-i18n-placeholder]')` and updates `.innerText` / attributes in a single animation frame batch.
5. **Digit Formatting:** When locale is `bn`, numeric quantities and dates are piped through `toBanglaDigits()` helper.

---

## 5. Phased Implementation Roadmap (Page Priority Order)

Migration is recommended in the following phased order based on user exposure and citizen criticality:

1. **Phase 1: Entry & Authentication (Highest Citizen Exposure)**
   - `signin.html` (Citizen phone OTP login)
   - `home.html` (Citizen dashboard & triage)
   - `intake.html` (Guided 10-step intake wizard)

2. **Phase 2: External Facing & Sharing (Recipient Exposure)**
   - `shared_brief.html` (External recipient viewer, OTP challenge, watermark)
   - `case_brief.html` (Case brief builder & ConsentSheet modal)
   - `sharing.html` (Consent management & access history)

3. **Phase 3: Case Management & Guided Drafting**
   - `cases.html` / `case_detail.html` (Case folders & party lists)
   - `draft.html` (Guided legal drafting & checklist)
   - `notifications.html` / `notification_settings.html`

4. **Phase 4: Admin & Specialized Portals**
   - `admin.html` & `admin_system.html` (System observability)
   - `admin_templates.html` & `admin_emergency_contacts.html`
   - `library.html`, `admin_rules.html`, `admin_evals.html`, `admin_sources.html`

---

> [!IMPORTANT]
> **S9 DOD Compliance Note**: In accordance with Directive H3, this document registers the exact string inventory and implementation blueprint. No hasty client-side refactor was applied in S9 to avoid regressions, and requirement **X-003 is formally documented as an open gap** pending Phase 1 execution.