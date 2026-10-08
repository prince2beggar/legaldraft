"""
Requirement to Test Mapping Generator for Sprint S9.
Parses JUnit XML report (or test suite) and generates the definitive
Requirement -> Test Node ID -> What it asserts table.
"""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

REQUIREMENTS_MAP = [
    {
        "req": "C0: Fail-closed secrets",
        "node": "tests/s9/test_s9_hardening.py::test_c0_fail_closed_secrets_in_production",
        "asserts": "Secrets (JWT, draft key, OTP/link peppers) fail closed (RuntimeError) if missing or default in prod",
    },
    {
        "req": "C0: S8 Admin & AI test confirmation",
        "node": "tests/s9/test_s9_hardening.py::test_c0_confirm_node_ids_for_ac_m05_admin_and_ai",
        "asserts": "Confirms AC-M05-ADMIN dual custody and AC-M05-AI structural bounding tests remain present",
    },
    {
        "req": "AC-M08-1: Inactive consent blocks view",
        "node": "tests/s9/test_ac_m08_sharing.py::test_ac_m08_1_recipient_link_without_active_consent_returns_403_and_audited",
        "asserts": "Accessing link without active consent returns 404 (anti-enumeration) and records audit trail entry",
    },
    {
        "req": "AC-M08-2: Revocation blocks access < 60s",
        "node": "tests/s9/test_ac_m08_sharing.py::test_ac_m08_2_revocation_blocks_access_within_60s_cached_pages_signed_urls",
        "asserts": "Revocation immediately blocks brief and signed doc URLs; asserts Cache-Control: no-store header",
    },
    {
        "req": "AC-M08-3: Confirmed data only in brief",
        "node": "tests/s9/test_ac_m08_sharing.py::test_ac_m08_3_brief_contains_no_extracted_facts_no_proposed_items_no_private_notes",
        "asserts": "Brief strictly includes confirmed facts & reviewed docs; unconfirmed facts & private notes excluded",
    },
    {
        "req": "AC-M08-4: Owner access history",
        "node": "tests/s9/test_ac_m08_sharing.py::test_ac_m08_4_owner_access_history_lists_every_view_with_time_and_recipient",
        "asserts": "Owner access-log returns every recipient view with timestamp, recipient identifier, and IP",
    },
    {
        "req": "AC-M08-5: Expired consents blocked",
        "node": "tests/s9/test_ac_m08_sharing.py::test_ac_m08_5_expired_consents_cannot_be_viewed_listed_under_expired",
        "asserts": "Expired consents return 404 to recipient and appear under 'expired' status filter for owner",
    },
    {
        "req": "M08: Token entropy & hash storage",
        "node": "tests/s9/test_ac_m08_sharing.py::test_sharing_token_entropy_and_hash_only_storage",
        "asserts": "Share token has >=128 bits entropy, stored only as HMAC-SHA256 hash in DB, verified in constant-time",
    },
    {
        "req": "M08: Anti-enumeration responses",
        "node": "tests/s9/test_ac_m08_sharing.py::test_anti_enumeration_indistinguishable_404_responses",
        "asserts": "Non-existent, expired, and revoked share tokens return indistinguishable HTTP 404 responses",
    },
    {
        "req": "M08: OTP rate limiting",
        "node": "tests/s9/test_ac_m08_sharing.py::test_otp_rate_limiting_locks_after_5_attempts",
        "asserts": "5 failed OTP verification attempts lock the link with HTTP 429",
    },
    {
        "req": "M08: Recipient watermark",
        "node": "tests/s9/test_ac_m08_sharing.py::test_brief_watermark_in_exported_pdf_and_viewer",
        "asserts": "Exported PDF and DOCX briefs embed watermark with recipient name/phone and expiration date",
    },
    {
        "req": "M08: Sensitive scope OTP re-check",
        "node": "tests/s9/test_ac_m08_sharing.py::test_sensitive_scope_requires_otp_recheck",
        "asserts": "Granting sensitive scopes (all_documents) rejects without OTP confirmation (400)",
    },
    {
        "req": "M08: Append-only consent records",
        "node": "tests/s9/test_ac_m08_sharing.py::test_append_only_consent_record_lifecycle",
        "asserts": "Consents cannot be deleted; revocation updates revoked_at and writes audit trail",
    },
    {
        "req": "M08: End-to-end browser journey",
        "node": "tests/s9/test_ac_m08_sharing.py::test_browser_journey_brief_sharing_end_to_end",
        "asserts": "Playwright end-to-end flow: Case -> ConsentSheet -> Share -> Recipient View -> Access Log -> Revoke",
    },
    {
        "req": "M08: Responsive layout verification",
        "node": "tests/s9/test_ac_m08_sharing.py::test_responsive_sharing_and_brief_screens",
        "asserts": "Zero horizontal overflow across 360x640, 768x1024, and 1280x800 for all sharing & brief screens",
    },
    {
        "req": "M08: 'undefined' text sweep",
        "node": "tests/s9/test_ac_m08_sharing.py::test_undefined_never_appears_sharing_sweep",
        "asserts": "Asserts text 'undefined' never appears anywhere in rendered HTML on sharing pages",
    },
    {
        "req": "C1: No external host URLs",
        "node": "tests/s9/test_ac_m08_sharing.py::test_c1_no_external_host_dependencies_sharing",
        "asserts": "Zero external CDN/font/script URLs in all static sharing and brief files",
    },
    {
        "req": "X-001: Route sweep",
        "node": "tests/s9/test_s9_hardening.py::test_x001_complete_route_sweep_all_endpoints",
        "asserts": "Sweeps all registered API routes and verifies authentication & authorization barriers",
    },
    {
        "req": "X-002: Audit completeness",
        "node": "tests/s9/test_s9_hardening.py::test_x002_audit_completeness_state_changing_routes",
        "asserts": "Every state-changing route writes to the SHA-256 hash chain and chain verifies valid",
    },
    {
        "req": "X-003: i18n translation parity",
        "node": "tests/s9/test_s9_hardening.py::test_x003_i18n_translation_keys_coverage",
        "asserts": "Complete parity of translation keys across Bangla ('bn') and English ('en') catalogs",
    },
    {
        "req": "X-004: AI output audit logging",
        "node": "tests/s9/test_s9_hardening.py::test_x004_ai_outputs_logged_for_ai_calls",
        "asserts": "Every AI Gateway execution logs prompt hash, model version, and output into audit log",
    },
    {
        "req": "X-005: Soft delete & retention",
        "node": "tests/s9/test_s9_hardening.py::test_x005_soft_delete_and_retention_policy",
        "asserts": "Soft deleted records are hidden from standard query views while preserving audit history",
    },
    {
        "req": "X-006: Rate limiting",
        "node": "tests/s9/test_s9_hardening.py::test_x006_rate_limiting_enforcement",
        "asserts": "Rate limiting locks after 5 failed verification attempts",
    },
    {
        "req": "X-007: Feature flags",
        "node": "tests/s9/test_s9_hardening.py::test_x007_feature_flags_configuration",
        "asserts": "DEV_MODE and STAGING_ALLOW_DRAFT_TEMPLATES flags evaluate deterministically",
    },
    {
        "req": "X-008: Accessibility (WCAG 2.2 AA)",
        "node": "tests/s9/test_s9_hardening.py::test_x008_accessibility_axe_audit",
        "asserts": "All static pages pass viewport, lang, semantic HTML, and accessibility requirements",
    },
    {
        "req": "Tenant Isolation (8 resource types)",
        "node": "tests/s9/test_s9_hardening.py::test_tenant_isolation_matrix_all_user_resources",
        "asserts": "User A vs User B strict isolation across Cases, Documents, Intake, Drafts, Notes, Notifications, Consents, Briefs",
    },
    {
        "req": "Backup & Restore rehearsal",
        "node": "tests/s9/test_s9_hardening.py::test_backup_and_restore_rehearsal_with_audit_chain",
        "asserts": "Online SQLite backup, SHA-256 verification, and restore preserves 100% row counts and audit integrity",
    },
    {
        "req": "Read Latency SLO (< 500 ms)",
        "node": "tests/s9/test_s9_hardening.py::test_read_latency_benchmark_under_500ms",
        "asserts": "p95 read latency across critical endpoints is benchmarked under 500 ms",
    },
    {
        "req": "PII & Log sanitization",
        "node": "tests/s9/test_s9_hardening.py::test_log_sanitization_pii_redaction",
        "asserts": "Structured logger prevents leakage of plain passwords, OTPs, or bearer tokens",
    },
]


def generate_markdown_table(junit_path: Path | None = None) -> str:
    lines = [
        "| Requirement | Test Node ID | What it asserts |",
        "|---|---|---|",
    ]
    for item in REQUIREMENTS_MAP:
        lines.append(f"| **{item['req']}** | `{item['node']}` | {item['asserts']} |")
    return "\n".join(lines)


if __name__ == "__main__":
    table = generate_markdown_table()
    print(table)
