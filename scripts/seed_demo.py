"""
Seed Demo Database (Sprint S9-I Addendum Directive M7 / K8)

Builds a strictly SEPARATE demo.db with clearly labelled FAKE data:
- Demo citizen user (phone: 01711223344) and demo admin (phone: 01700000001)
- 2 demo cases:
    * Case 1: unconfirmed deadline in 2 days (urgent)
    * Case 2: overdue deadline (action required / overdue)
- Processed synthetic legal notice attached to Case 1
- Proposed facts and timeline events
- Notifications
- Draft in progress with approved template
- Active shared consent / lawyer brief link

RULE: NEVER TOUCH legal_saas.db OR the real ain_ai.db.
"""

import hashlib
import hmac
import json
import os
import sqlite3
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEMO_DB_PATH = REPO_ROOT / "demo.db"
AIN_AI_DB_PATH = REPO_ROOT / "ain_ai.db"


def build_and_seed_demo_db(db_path=None):
    target_db = Path(db_path) if db_path else DEMO_DB_PATH
    print(f"Building demo database at {target_db}...")
    if target_db.exists():
        try:
            target_db.unlink()
        except Exception:
            pass

    # 1. Recreate table structure from schema
    if AIN_AI_DB_PATH.exists():
        src_conn = sqlite3.connect(str(AIN_AI_DB_PATH))
        src_cursor = src_conn.cursor()
        src_cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND sql IS NOT NULL;")
        ddl_statements = [r[0] for r in src_cursor.fetchall()]
        src_conn.close()

        dest_conn = sqlite3.connect(str(target_db))
        dest_cursor = dest_conn.cursor()
        for ddl in ddl_statements:
            try:
                dest_cursor.execute(ddl)
            except Exception:
                pass
        dest_conn.commit()
    else:
        dest_conn = sqlite3.connect(str(target_db))
        dest_cursor = dest_conn.cursor()

    now = datetime.now(timezone.utc)
    now_iso = now.isoformat()
    two_days_later = (now + timedelta(days=2)).strftime("%Y-%m-%d")
    three_days_ago = (now - timedelta(days=3)).strftime("%Y-%m-%d")

    citizen_id = "user-demo-citizen"
    admin_id = "user-demo-admin"

    # 2. Insert Users into both users and trust_users
    dest_cursor.execute(
        """
        INSERT OR REPLACE INTO users (id, phone, name, preferred_lang, numeral_style, status, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """,
        (
            citizen_id,
            "01711223344",
            "ডেমো নাগরিক (নমুনা ডেটা)",
            "bn",
            "bn",
            "active",
            now_iso,
            now_iso,
        ),
    )

    dest_cursor.execute(
        """
        INSERT OR REPLACE INTO users (id, phone, name, preferred_lang, numeral_style, status, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """,
        (
            admin_id,
            "01700000001",
            "ডেমো অ্যাডমিন (নমুনা ডেটা)",
            "bn",
            "bn",
            "active",
            now_iso,
            now_iso,
        ),
    )

    dest_cursor.execute(
        """
        INSERT OR REPLACE INTO users (id, phone, name, preferred_lang, numeral_style, status, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """,
        (
            "user-empty-citizen",
            "01722334455",
            "খালি ফোল্ডার নাগরিক (নমুনা ডেটা)",
            "bn",
            "bn",
            "active",
            now_iso,
            now_iso,
        ),
    )

    # user_roles
    dest_cursor.execute(
        """
        INSERT OR REPLACE INTO user_roles (id, user_id, role, verified, created_at)
        VALUES (?, ?, ?, ?, ?)
    """,
        (str(uuid.uuid4()), citizen_id, "citizen", 1, now_iso),
    )
    dest_cursor.execute(
        """
        INSERT OR REPLACE INTO user_roles (id, user_id, role, verified, created_at)
        VALUES (?, ?, ?, ?, ?)
    """,
        (str(uuid.uuid4()), "user-empty-citizen", "citizen", 1, now_iso),
    )
    dest_cursor.execute(
        """
        INSERT OR REPLACE INTO user_roles (id, user_id, role, verified, created_at)
        VALUES (?, ?, ?, ?, ?)
    """,
        (str(uuid.uuid4()), admin_id, "admin", 1, now_iso),
    )

    # trust_users
    dest_cursor.execute(
        """
        INSERT OR REPLACE INTO trust_users (id, phone, name, role, roles_json, preferred_lang, numeral_style, status, is_onboarded, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,
        (
            citizen_id,
            "01711223344",
            "ডেমো নাগরিক (নমুনা ডেটা)",
            "citizen",
            '["citizen"]',
            "bn",
            "bn",
            "active",
            1,
            now_iso,
        ),
    )

    dest_cursor.execute(
        """
        INSERT OR REPLACE INTO trust_users (id, phone, name, role, roles_json, preferred_lang, numeral_style, status, is_onboarded, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,
        (
            "user-empty-citizen",
            "01722334455",
            "খালি ফোল্ডার নাগরিক (নমুনা ডেটা)",
            "citizen",
            '["citizen"]',
            "bn",
            "bn",
            "active",
            1,
            now_iso,
        ),
    )

    dest_cursor.execute(
        """
        INSERT OR REPLACE INTO trust_users (id, phone, name, role, roles_json, preferred_lang, numeral_style, status, is_onboarded, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,
        (
            admin_id,
            "01700000001",
            "ডেমো অ্যাডমিন (নমুনা ডেটা)",
            "admin",
            '["admin"]',
            "bn",
            "bn",
            "active",
            1,
            now_iso,
        ),
    )

    # 3. Insert 2 Demo Cases
    case_1_id = "case-demo-01"
    case_2_id = "case-demo-02"

    dest_cursor.execute(
        """
        INSERT OR REPLACE INTO cases (id, owner_id, title, case_type, description, objective, urgency, status, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,
        (
            case_1_id,
            citizen_id,
            "নমুনা মামলা: চেক ডিজঅনার নোটিশ",
            "legal_notice",
            "চেক ডিজঅনার নোটিশের জবাব দাখিল সংক্রান্ত কাল্পনিক নমুনা নথি (১০ দিন)।",
            "নোটিশের জবাব দাখিল ও আইনি সুরক্ষা গ্রহণ",
            "urgent",
            "action_required",
            now_iso,
            now_iso,
        ),
    )

    dest_cursor.execute(
        """
        INSERT OR REPLACE INTO cases (id, owner_id, title, case_type, description, objective, urgency, status, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,
        (
            case_2_id,
            citizen_id,
            "নমুনা মামলা ২: মিরপুর জমি চুক্তিপত্র ও দখল বিরোধ",
            "land_dispute",
            "বায়না চুক্তিপত্র লঙ্ঘন এবং জমি দখল সংক্রান্ত আইনি বিরোধ।",
            "জমির দখল সুরক্ষা ও চুক্তি কার্যকর",
            "critical",
            "action_required",
            now_iso,
            now_iso,
        ),
    )

    # 4. Insert Deadlines covering all 3 provenance types (V5 requirement)
    dl_1_id = "dl-demo-01"
    dest_cursor.execute(
        """
        INSERT OR REPLACE INTO deadlines (id, case_id, user_id, title, due_date, status, confirmed_by_user, is_user_set, rule_key, calculation_basis, source_ref, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,
        (
            dl_1_id,
            case_1_id,
            citizen_id,
            "নোটিশের লিখিত জবাব দাখিল",
            two_days_later,
            "pending",
            0,
            0,
            "demo_sample_period",
            "rule_based",
            "রুলস ইঞ্জিন: নমুনা সময়সীমা (১০ দিন)",
            now_iso,
        ),
    )

    dl_2_id = "dl-demo-02"
    dest_cursor.execute(
        """
        INSERT OR REPLACE INTO deadlines (id, case_id, user_id, title, due_date, status, confirmed_by_user, is_user_set, rule_key, calculation_basis, source_ref, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,
        (
            dl_2_id,
            case_2_id,
            citizen_id,
            "থানা সাধারণ ডায়েরি (জিডি) কপি দাখিল",
            three_days_ago,
            "overdue",
            1,
            1,
            None,
            "user_entered",
            "ব্যবহারকারীর নির্ধারিত তারিখ",
            now_iso,
        ),
    )

    dl_3_id = "dl-demo-03"
    seven_days_later = (now + timedelta(days=7)).strftime("%Y-%m-%d")
    dest_cursor.execute(
        """
        INSERT OR REPLACE INTO deadlines (id, case_id, user_id, title, due_date, status, confirmed_by_user, is_user_set, rule_key, calculation_basis, source_ref, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,
        (
            dl_3_id,
            case_1_id,
            citizen_id,
            "নোটিশে উল্লেখিত চূড়ান্ত জবাবের তারিখ",
            seven_days_later,
            "upcoming",
            1,
            0,
            None,
            "stated_date",
            "নোটিশে উল্লেখিত তারিখ",
            now_iso,
        ),
    )

    # 5. Insert Processed Synthetic Notice Document
    doc_1_id = "doc-demo-notice-01"
    dest_cursor.execute(
        """
        INSERT OR REPLACE INTO documents (id, owner_id, case_id, title, status, filename, intent, processing_status, created_at, uploaded_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,
        (
            doc_1_id,
            citizen_id,
            case_1_id,
            "আইনি নোটিশ (এনআই অ্যাক্ট ১৩৮)",
            "reviewed",
            "synthetic_notice_ni_act_138.pdf",
            "respond_notice",
            "completed",
            now_iso,
            now_iso,
        ),
    )

    # 6. Insert Proposed Facts & Events
    dest_cursor.execute(
        """
        INSERT OR REPLACE INTO case_facts (id, case_id, text, fact_text, status, is_proposed, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """,
        (
            "fact-demo-01",
            case_1_id,
            "২০২৬ সালের ৫ সেপ্টেম্বর ৫০,০০০ টাকার চেক ডিজঅনার হয়েছিল।",
            "২০২৬ সালের ৫ সেপ্টেম্বর ৫০,০০০ টাকার চেক ডিজঅনার হয়েছিল।",
            "confirmed",
            0,
            now_iso,
        ),
    )
    dest_cursor.execute(
        """
        INSERT OR REPLACE INTO case_facts (id, case_id, text, fact_text, status, is_proposed, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """,
        (
            "fact-demo-02",
            case_1_id,
            "নোটিশ গ্রহীতার ঠিকানায় ১৫ দিনের সময় প্রদান করা হয়েছে।",
            "নোটিশ গ্রহীতার ঠিকানায় ১৫ দিনের সময় প্রদান করা হয়েছে।",
            "proposed",
            1,
            now_iso,
        ),
    )

    dest_cursor.execute(
        """
        INSERT OR REPLACE INTO case_events (id, case_id, title, event_date, event_type, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """,
        (
            "event-demo-01",
            case_1_id,
            "আইনি নোটিশ জারি ও গ্রহণ",
            now.strftime("%Y-%m-%d"),
            "notice_served",
            now_iso,
        ),
    )

    # 7. Insert Notifications
    dest_cursor.execute(
        """
        INSERT OR REPLACE INTO notifications (id, user_id, kind, title_key, body_key, title, message, status, is_read, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,
        (
            "notif-demo-01",
            citizen_id,
            "deadline",
            "notif.deadline.urgent",
            "notif.deadline.urgent.body",
            "জরুরি সময়সীমা সতর্কবার্তা",
            "আপনার চেক ডিজঅনার নোটিশের জবাব দাখিলের আর মাত্র ২ দিন বাকি।",
            "unread",
            0,
            now_iso,
        ),
    )
    dest_cursor.execute(
        """
        INSERT OR REPLACE INTO notifications (id, user_id, kind, title_key, body_key, title, message, status, is_read, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,
        (
            "notif-demo-02",
            citizen_id,
            "deadline",
            "notif.deadline.overdue",
            "notif.deadline.overdue.body",
            "সময়সীমা অতিক্রান্ত",
            "থানা জিডি কপি দাখিলের নির্ধারিত সময়সীমা অতিবাহিত হয়েছে।",
            "read",
            1,
            now_iso,
        ),
    )

    # 8. Insert Approved Template & Draft
    dest_cursor.execute(
        """
        INSERT OR REPLACE INTO templates (id, doc_type, code, name, name_bn, category, status, approval_status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,
        (
            "tmpl-demo-01",
            "contract",
            "BD_COMMERCIAL_LEASE",
            "Commercial Lease Agreement",
            "বাণিজ্যিক দোকান/স্পেস চুক্তিপত্র",
            "contract",
            "active",
            "approved",
            now_iso,
        ),
    )

    dest_cursor.execute(
        """
        INSERT OR REPLACE INTO drafts (id, owner_id, case_id, template_id, template_version, title, status, answers_json, is_finalized, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,
        (
            "draft-demo-01",
            citizen_id,
            case_1_id,
            "BD_COMMERCIAL_LEASE",
            1,
            "বাণিজ্যিক দোকান চুক্তিপত্র ড্রাফট (নমুনা)",
            "in_progress",
            json.dumps(
                {"lessor_name": "মোঃ করিম", "lessee_name": "ডেমো নাগরিক", "monthly_rent": "30000"}
            ),
            0,
            now_iso,
            now_iso,
        ),
    )

    # 9. Insert Active Consent
    dest_cursor.execute(
        """
        INSERT OR REPLACE INTO consents (id, grantor_id, grantee_id, scope_type, scope_id, permissions, starts_at, expires_at, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,
        (
            "consent-demo-01",
            citizen_id,
            "lawyer-demo-advocate",
            "case",
            case_1_id,
            json.dumps(["read_case", "read_brief"]),
            now_iso,
            (now + timedelta(days=7)).isoformat(),
            now_iso,
        ),
    )

    # 10. Insert trust_consents, briefs, and brief_links for Recipient Viewer (Valid, Expired, Revoked)
    dest_cursor.execute("""
        CREATE TABLE IF NOT EXISTS trust_consents (
            id VARCHAR(64) PRIMARY KEY,
            grantor_id VARCHAR(64) NOT NULL,
            grantee_id VARCHAR(64) NOT NULL,
            scope VARCHAR(64) NOT NULL,
            permissions_json TEXT NOT NULL,
            starts_at VARCHAR(64) NOT NULL,
            expires_at VARCHAR(64) NOT NULL,
            revoked_at VARCHAR(64),
            created_at VARCHAR(64) NOT NULL
        );
    """)
    dest_cursor.execute("""
        CREATE TABLE IF NOT EXISTS briefs (
            id VARCHAR(64) PRIMARY KEY,
            case_id VARCHAR(64) NOT NULL,
            owner_id VARCHAR(64) NOT NULL,
            title VARCHAR(255) NOT NULL,
            sections_json TEXT NOT NULL,
            is_edited BOOLEAN NOT NULL DEFAULT 0,
            created_at VARCHAR(64) NOT NULL,
            updated_at VARCHAR(64) NOT NULL
        );
    """)
    dest_cursor.execute("""
        CREATE TABLE IF NOT EXISTS brief_links (
            id VARCHAR(64) PRIMARY KEY,
            consent_id VARCHAR(64) NOT NULL,
            case_id VARCHAR(64) NOT NULL,
            token_hash VARCHAR(64) NOT NULL UNIQUE,
            recipient_contact VARCHAR(128) NOT NULL,
            otp_hash VARCHAR(64),
            otp_expires_at VARCHAR(64),
            otp_attempts INTEGER NOT NULL DEFAULT 0,
            otp_locked_until VARCHAR(64),
            otp_verified_at VARCHAR(64),
            view_count INTEGER NOT NULL DEFAULT 0,
            last_viewed_at VARCHAR(64),
            expires_at VARCHAR(64) NOT NULL,
            revoked_at VARCHAR(64),
            created_at VARCHAR(64) NOT NULL
        );
    """)

    dest_cursor.execute(
        """
        INSERT OR REPLACE INTO trust_consents (id, grantor_id, grantee_id, scope, permissions_json, starts_at, expires_at, revoked_at, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,
        (
            "consent-demo-01",
            citizen_id,
            "01811223344",
            "case",
            json.dumps({"download": True, "comment": False, "scopes": ["brief", "documents"]}),
            now_iso,
            (now + timedelta(days=7)).isoformat(),
            None,
            now_iso,
        ),
    )

    dest_cursor.execute(
        """
        INSERT OR REPLACE INTO briefs (id, case_id, owner_id, title, sections_json, is_edited, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """,
        (
            "brief-demo-01",
            case_1_id,
            citizen_id,
            "নমুনা মামলা: চেক ডিজঅনার নোটিশ",
            json.dumps({
                "case_title": "নমুনা মামলা: চেক ডিজঅনার নোটিশ",
                "case_type_bn": "চেক ডিজঅনার নোটিশ",
                "client_name": "ডেমো নাগরিক",
                "as_of_date": now_iso,
                "background": "চেক ডিজঅনারের বিপরীতে লিগ্যাল নোটিশের জবাব দাখিল ও প্রস্তুতি।",
                "user_objective": "আইনি অধিকার সংরক্ষণ ও যথাসময়ে জবাব নিশ্চিত করা।",
                "timeline": [{"event_date": "২০২৬-১০-০১", "description": "নোটিশ প্রাপ্তি"}],
                "important_facts": [{"text": "চেক প্রত্যাখ্যাত হয়েছে ও ১০ দিনের নমুনা সময়সীমা চলমান।"}],
                "key_documents": [],
                "possible_legal_issues": ["১০ দিনের মধ্যে জবাব দাখিল"],
                "missing_information": [],
                "questions_for_lawyer": ["পরবর্তী পদক্ষেপ কী?"]
            }),
            0,
            now_iso,
            now_iso,
        ),
    )

    pepper = os.environ.get("LINK_TOKEN_PEPPER", "crawler-link-pepper-12345678901234567890123456789012")

    def _hash_link_tok(tok: str) -> str:
        return hmac.new(pepper.encode("utf-8"), tok.encode("utf-8"), hashlib.sha256).hexdigest()

    # Valid link (pre-verified OTP)
    dest_cursor.execute(
        """
        INSERT OR REPLACE INTO brief_links (id, consent_id, case_id, token_hash, recipient_contact, otp_attempts, otp_verified_at, view_count, expires_at, revoked_at, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,
        (
            "link-demo-valid",
            "consent-demo-01",
            case_1_id,
            _hash_link_tok("share-valid-token"),
            "01811223344",
            0,
            now_iso,
            1,
            (now + timedelta(days=7)).isoformat(),
            None,
            now_iso,
        ),
    )

    # Expired link
    dest_cursor.execute(
        """
        INSERT OR REPLACE INTO brief_links (id, consent_id, case_id, token_hash, recipient_contact, otp_attempts, otp_verified_at, view_count, expires_at, revoked_at, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,
        (
            "link-demo-expired",
            "consent-demo-01",
            case_1_id,
            _hash_link_tok("share-expired-token"),
            "01811223344",
            0,
            now_iso,
            0,
            (now - timedelta(days=2)).isoformat(),
            None,
            (now - timedelta(days=5)).isoformat(),
        ),
    )

    # Revoked link
    dest_cursor.execute(
        """
        INSERT OR REPLACE INTO brief_links (id, consent_id, case_id, token_hash, recipient_contact, otp_attempts, otp_verified_at, view_count, expires_at, revoked_at, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,
        (
            "link-demo-revoked",
            "consent-demo-01",
            case_1_id,
            _hash_link_tok("share-revoked-token"),
            "01811223344",
            0,
            now_iso,
            0,
            (now + timedelta(days=7)).isoformat(),
            (now - timedelta(hours=1)).isoformat(),
            now_iso,
        ),
    )

    dest_conn.commit()
    dest_conn.close()

    print(f"Successfully generated and seeded {target_db} with labelled fake demo entities.")
    return True


if __name__ == "__main__":
    build_and_seed_demo_db()
