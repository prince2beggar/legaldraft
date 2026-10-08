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

import json
import sqlite3
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEMO_DB_PATH = REPO_ROOT / "demo.db"
AIN_AI_DB_PATH = REPO_ROOT / "ain_ai.db"


def build_and_seed_demo_db():
    print(f"Building demo database at {DEMO_DB_PATH}...")
    if DEMO_DB_PATH.exists():
        try:
            DEMO_DB_PATH.unlink()
        except Exception:
            pass

    # 1. Recreate table structure from schema
    if AIN_AI_DB_PATH.exists():
        src_conn = sqlite3.connect(str(AIN_AI_DB_PATH))
        src_cursor = src_conn.cursor()
        src_cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND sql IS NOT NULL;")
        ddl_statements = [r[0] for r in src_cursor.fetchall()]
        src_conn.close()

        dest_conn = sqlite3.connect(str(DEMO_DB_PATH))
        dest_cursor = dest_conn.cursor()
        for ddl in ddl_statements:
            try:
                dest_cursor.execute(ddl)
            except Exception:
                pass
        dest_conn.commit()
    else:
        dest_conn = sqlite3.connect(str(DEMO_DB_PATH))
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
            "নমুনা মামলা ১: এনআই অ্যাক্ট ১৩৮ চেক ডিজঅনার নোটিশ",
            "legal_notice",
            "৫০,০০০ টাকার চেক ডিজঅনার নোটিশের ১৫ দিনের জবাব দাখিল সংক্রান্ত নমুনা নথি।",
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

    # 4. Insert Deadlines
    dl_1_id = "dl-demo-01"
    dest_cursor.execute(
        """
        INSERT OR REPLACE INTO deadlines (id, case_id, user_id, title, due_date, status, confirmed_by_user, is_user_set, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            now_iso,
        ),
    )

    dl_2_id = "dl-demo-02"
    dest_cursor.execute(
        """
        INSERT OR REPLACE INTO deadlines (id, case_id, user_id, title, due_date, status, confirmed_by_user, is_user_set, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            json.dumps({"lessor_name": "মোঃ করিম", "lessee_name": "ডেমো নাগরিক", "monthly_rent": "30000"}),
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

    dest_conn.commit()
    dest_conn.close()

    print(f"Successfully generated and seeded {DEMO_DB_PATH} with labelled fake demo entities.")
    return True


if __name__ == "__main__":
    build_and_seed_demo_db()
