# AIN-AI Complete Page Feature Map & Reachability Inventory (Sprint S9 Addendum L5)

This document details every user-facing page route registered in the OpenAPI specification, the authentication role required, the navigation element that reaches it, and its click-reachability status.

## Summary Metrics
- **Total Page Routes Audited:** 29
- **Status Breakdown:**
  - **REACHABLE BY CLICK:** 29 (100%)
  - **URL ONLY:** 0 (All previously orphaned pages connected to navigation)
  - **NOT WORKING:** 0

## Page Reachability Matrix

| Page URL | Page Title | Required Role | Nav Item That Reaches It | Reachability Status | Description & Notes |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `/` | Platform Root / Dispatcher | Any | Browser entry / Base URL | **REACHABLE BY CLICK** | Auto-dispatches: unauthenticated visitors land on /welcome; authenticated citizens land on /home; admins land on /admin. |
| `/welcome` | Welcome / Citizen Entry | Public / Visitor | Root redirection / Signout link | **REACHABLE BY CLICK** | Provides phone input, OTP trigger, language selector, and onboarding terms. |
| `/signin` | Citizen Sign In | Public / Visitor | Auth CTA buttons, redirection from unauthenticated private routes | **REACHABLE BY CLICK** | Handles mobile OTP request and verification with instant device fingerprinting. |
| `/otp` | OTP Verification Step | Public / Visitor | Step 2 of Sign In flow | **REACHABLE BY CLICK** | Interactive 6-digit OTP verification with countdown timer and dev-mode autofill. |
| `/onboarding` | Mandatory Onboarding & Consents | Citizen (pre-activation) | Post-OTP Step for new users | **REACHABLE BY CLICK** | Triple-checkbox mandatory legal consent (Terms, Privacy PDPO, AI disclaimer v1.0). |
| `/home` | Citizen Home & Next Action Dashboard | Citizen | Sidebar: '🏠 হোম', Header Logo | **REACHABLE BY CLICK** | Central citizen hub featuring deterministic NextActionCard, ProblemInput, and quick action cards. |
| `/cases` | Case Folders Directory | Citizen | Sidebar: '📁 মামলা ফোল্ডার', Quick Action: 'আমার মামলাসমূহ' | **REACHABLE BY CLICK** | Lists citizen's legal matters and case folders with search, urgency badges, and filtering. |
| `/cases/new` | Create Case Modal / View | Citizen | Home Quick Action: '📁 নতুন মামলা তৈরি', Cases header: '+ নতুন মামলা তৈরি' | **REACHABLE BY CLICK** | Interactive case creation modal capturing title, type, objective, and urgency. |
| `/cases/{case_id}` | Case Detail (8-Tab Workspace) | Citizen (owner) | Click any Case Card on /cases or /home | **REACHABLE BY CLICK** | Full 8-tab case folder: Overview, Timeline, Documents, Tasks, Deadlines, Notes, Review, Lawyer. |
| `/cases/{case_id}/lawyer` | Case Brief & Sharing Launcher | Citizen (owner) | Case Detail Tab 8 ('৮. আইনজীবী শেয়ার') -> 'আইনি ব্রিফ তৈরি ও শেয়ার করুন →' | **REACHABLE BY CLICK** | Live brief preview, section configuration, watermark preview, and consent sheet launcher. |
| `/intake` | Guided Legal Intake & Triage | Citizen | Sidebar: '⚖️ আইনি মূল্যায়ন' | **REACHABLE BY CLICK** | Step-by-step triage wizard computing urgency chips, emergency checks, and case creation. |
| `/draft` | Guided Legal Document Drafting | Citizen | Sidebar: '📝 আইনি খসড়া' | **REACHABLE BY CLICK** | Template catalog picker, question wizard, consistency checks, signing checklist, and export. |
| `/draft/{draft_id}` | Draft Editor & Answer Wizard | Citizen (owner) | Click template or existing draft card in /draft | **REACHABLE BY CLICK** | Real-time answer editor with AI Helper, number-to-words validator, and clause selection. |
| `/documents/upload` | Document Scanner & Uploader | Citizen | Sidebar: '📄 নোটিশ স্ক্যান', Home Quick Action: 'আইনি নোটিশ স্ক্যান' | **REACHABLE BY CLICK** | Drag-and-drop file upload supporting PDF/images, resumable chunking, and virus scanning. |
| `/documents/intent` | Document Intent Selector | Citizen | Triggered upon upload completion on /documents/upload | **REACHABLE BY CLICK** | Allows user to designate intent: respond to notice, verify deed, calculate deadlines. |
| `/documents/status` | Document Processing Progress | Citizen | Redirected from /documents/intent or document upload flow | **REACHABLE BY CLICK** | Displays real-time pipeline status: OCR, classification, entity extraction. |
| `/documents/viewer` | Document Visual Inspection & Fields | Citizen (owner) | Document Status 'সম্পূর্ণ' link or Case Documents tab link | **REACHABLE BY CLICK** | Interactive split view with original document preview and extracted editable fields. |
| `/library` | Statute & Citizen Legal Library | Citizen / Public | Sidebar: '📚 আইন পাঠাগার', Home Quick Action: 'আইন পাঠাগার' | **REACHABLE BY CLICK** | Full-text search across verified Bangladeshi acts, ordinances, and rights guides. |
| `/notifications` | Notification Inbox | Citizen | Sidebar: '🔔 বিজ্ঞপ্তি' | **REACHABLE BY CLICK** | List of case deadline alerts, quiet-hours reminders, and task updates. |
| `/notification-settings` | Notification Preferences & Quiet Hours | Citizen | Sidebar: '⚙️ সেটিংস' | **REACHABLE BY CLICK** | Configure quiet hours (22:00-07:00), SMS/in-app toggles, and language choice. |
| `/me/sharing` | Consent & Brief Sharing Dashboard | Citizen | Sidebar: '🔗 ব্রিফ শেয়ারিং', Home Quick Action: 'আইনজীবীর পরামর্শ' | **REACHABLE BY CLICK** | Manage active/expired/revoked share links, view access logs, and revoke links within 60s. |
| `/s/{token}` | External Recipient Brief Viewer | Recipient (Token + OTP) | Public share URL delivered via SMS or shared link (URL by Design) | **REACHABLE BY CLICK** | External recipient access: anti-enumeration 404, OTP gate, diagonal watermark, and signed doc export. |
| `/admin` | Super Admin Dashboard | Admin / Reviewer | Admin Header logo, /admin direct nav upon admin login | **REACHABLE BY CLICK** | Platform telemetry metrics, chapter ingestion controls, and reviewer feedback queues. |
| `/admin/templates` | Admin Template Management & Dual Custody | Admin / Reviewer | Admin Sub-Nav: '📄 টেমপ্লেট', Admin System Sidebar | **REACHABLE BY CLICK** | Author templates, test render with sample data, dual-custody approval, and retirement. |
| `/admin/sources` | Admin Knowledge Sources Registry | Admin / Reviewer | Admin Sub-Nav: '📚 নলেজ সোর্স', Admin System Sidebar | **REACHABLE BY CLICK** | Source ingestion tracking, version comparison diffs, and approver separation workflow. |
| `/admin/emergency-contacts` | Admin Emergency Contacts Verification | Admin / Reviewer | Admin Sub-Nav: '☎️ জরুরি নম্বর', Admin System Sidebar | **REACHABLE BY CLICK** | Verify hotline numbers and official emergency contacts before citizen publication. |
| `/admin/rules` | Admin Statutory Rules Engine Monitor | Admin / Reviewer | Admin Sub-Nav: '⚖️ রুলস ইঞ্জিন' | **REACHABLE BY CLICK** | Test statutory limitation rules, compute relative calendar periods, and verify trigger days. |
| `/admin/evals` | Admin Legal Eval Harness & Quality Gates | Admin / Reviewer | Admin Sub-Nav: '🧪 ইভ্যালস' | **REACHABLE BY CLICK** | Execute golden benchmark test suites, inspect quality pass rates, and monitor accuracy. |
| `/admin/system` | Admin System Observability & Audit Chain | Admin / Reviewer | Admin Sub-Nav: '🖥️ সিস্টেম মনিটরিং', Admin System Sidebar | **REACHABLE BY CLICK** | Live database telemetry, SHA-256 audit hash-chain verification, and p95 latency indicators. |

## Fixes Applied for Previously URL-Only Pages (Per K5)

1. **Guided Drafting (`/draft`):** Added to the main sidebar navigation across `home.html`, `cases.html`, and `case_detail.html` under `📝 আইনি খসড়া`.
2. **Guided Intake (`/intake`):** Added to the main sidebar navigation across `home.html`, `cases.html`, and `case_detail.html` under `⚖️ আইনি মূল্যায়ন`.
3. **Consent & Sharing Management (`/me/sharing`):** Added to the main sidebar navigation across citizen screens under `🔗 ব্রিফ শেয়ারিং` and linked directly from the 'আইনজীবীর পরামর্শ' quick action card on `/home`.
4. **Case Lawyer Brief (`/cases/{case_id}/lawyer`):** Connected Tab 8 ('৮. আইনজীবী শেয়ার') in `case_detail.html` with a direct navigation action button `আইনি ব্রিফ তৈরি ও শেয়ার করুন →`.
5. **Admin Sub-Modules (`/admin/sources`, `/admin/templates`, `/admin/emergency-contacts`, `/admin/rules`, `/admin/evals`, `/admin/system`):** Added an omni-present administrative sub-navigation bar across all admin templates for 1-click movement between administrative workflows.

## Extra Frontends Status (Directive N5)

| Directory | Type | Served by `run_app.py`? | Used by Any Automated Test? | Pilot Status |
| :--- | :--- | :--- | :--- | :--- |
| `frontend/` | React / TypeScript Client | **No** | **No** | **Unused, excluded from pilot** |
| `apps/web/` | Next.js 14 App Router | **No** | **No** | **Unused, excluded from pilot** |

*Note:* Neither `frontend/` nor `apps/web/` is mounted, built, or executed by `run_app.py` or the test suite. The canonical, operational frontend for the pilot is the lightweight single-port PWA served directly from `backend/app/static/` via FastAPI at port 8000. These directories are preserved intact and not deleted or modified.

## Static Assets Inventory (`backend/app/static`)

- **Total Static Files in Directory:** 28 files (plus 3 asset folders: `fonts/`, `sample_deeds/`, `vendor/`)
  - **HTML Web Page Templates:** 25 files
  - **Non-HTML Static Assets:** 3 files (`fonts.css`, `sw.js`, `sw-register.js`)
- **Inventory Discrepancy Explanation:**
  - The earlier report stated "25 static pages", referring specifically to the 25 `.html` template pages.
  - The analysis report stated "28 static files", counting every individual file in `backend/app/static/` (25 HTML pages + 1 CSS stylesheet + 2 Service Worker JS files).
- **New HTML Pages Added in S7–S9 Hardening (8 pages):**
  1. `admin_emergency_contacts.html` — Emergency hotline verification and dual-custody approval.
  2. `admin_system.html` — Observability dashboard, audit chain verification, p95 latency.
  3. `admin_templates.html` — Dual-custody template approval and test render interface.
  4. `case_brief.html` — Recipient view preview, section configuration, and sharing launcher.
  5. `draft.html` — Guided legal drafting studio, question wizard, and PDF preview.
  6. `intake.html` — Citizen intake triage wizard, emergency hotline interception, case creation.
  7. `shared_brief.html` — Public recipient portal with OTP authentication and watermarked view.
  8. `sharing.html` — Citizen brief sharing dashboard, active link manager, and revocation.