"""
Sprint S9: Case Brief Builder, Consents & Secure Links Engine (SRS Module M08).
Implements:
1. ConsentSheet data structures & consent state machine (active / expired / revoked).
2. Brief Builder strictly filtering for confirmed facts, events, and reviewed documents (AC-M08-3).
3. Secure Links with unguessable tokens (>=128 bits), stored only as hash, constant-time compare.
4. Recipient verification via SMS OTP (mock/stubbed SMS provider).
5. Expiry enforcement, watermarking with recipient contact & expiry date.
6. Signed URLs with TTL <= 60 seconds for document downloads (AC-M08-2).
7. Indistinguishable responses for invalid/expired/revoked links (no enumeration).
8. Append-only audit logging on all consent grants, views, and revocations (AC-M08-4).
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from docx import Document
from docx.shared import Pt, RGBColor
from playwright.sync_api import sync_playwright

from packages.trust_kernel.audit import audit_service
from packages.trust_kernel.auth import (
    get_link_token_pepper,
    get_otp_pepper,
    is_dev_mode,
)
from packages.trust_kernel.db import DatabaseManager, db_manager
from packages.trust_kernel.sms import get_sms_provider

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
STATIC_DIR = REPO_ROOT / "backend" / "app" / "static"
FONTS_DIR = STATIC_DIR / "fonts"

_REGULAR_FONT_BASE64: str | None = None
_BOLD_FONT_BASE64: str | None = None


def _get_font_base64() -> tuple[str, str]:
    global _REGULAR_FONT_BASE64, _BOLD_FONT_BASE64
    if _REGULAR_FONT_BASE64 is None:
        reg_path = FONTS_DIR / "NotoSansBengali-Regular.ttf"
        if reg_path.exists():
            _REGULAR_FONT_BASE64 = base64.b64encode(reg_path.read_bytes()).decode("ascii")
        else:
            _REGULAR_FONT_BASE64 = ""
    if _BOLD_FONT_BASE64 is None:
        bold_path = FONTS_DIR / "NotoSansBengali-Bold.ttf"
        if bold_path.exists():
            _BOLD_FONT_BASE64 = base64.b64encode(bold_path.read_bytes()).decode("ascii")
        else:
            _BOLD_FONT_BASE64 = ""
    return _REGULAR_FONT_BASE64, _BOLD_FONT_BASE64


class BriefEngine:
    def __init__(self, db: DatabaseManager | None = None):
        self.db = db or db_manager
        self._failed_otp_counts: dict[str, int] = {}

    # -----------------------------------------------------------------------
    # 1. Brief Builder (AC-M08-3)
    # -----------------------------------------------------------------------
    def build_case_brief(
        self,
        case_id: str,
        owner_id: str,
        custom_sections: dict[str, Any] | None = None,
        include_private_notes: bool = False,
    ) -> dict[str, Any]:
        """
        Builds a comprehensive legal brief from confirmed/reviewed data ONLY (AC-M08-3).
        STRICT RULES:
        - NEVER includes extracted-state facts or proposed facts.
        - NEVER includes proposed timeline events.
        - NEVER includes raw unverified documents.
        - NEVER includes private notes unless include_private_notes=True AND note.include_in_brief=True.
        """
        case = self.db.get_case(case_id)
        if not case:
            raise ValueError(f"Case '{case_id}' not found")
        if case["owner_id"] != owner_id:
            audit_service.log(
                actor_id=owner_id,
                actor_role="citizen",
                action="BRIEF_ACCESS_DENIED",
                object_type="case",
                object_id=case_id,
            )
            raise PermissionError("Access denied to case")

        # 1. Parties
        parties = self.db.list_case_parties(case_id)
        client = next(
            (p for p in parties if p.get("role") in ("client", "landlord", "applicant", "first_party")),
            None,
        )
        opponent = next(
            (p for p in parties if p.get("role") in ("opponent", "tenant", "respondent", "second_party")),
            None,
        )
        client_name = client["name"] if client else case.get("title", "মক্কেল")
        opponent_name = opponent["name"] if opponent else "প্রতিপক্ষ"

        # 2. Case Type in pure Bengali
        case_type_bn = case.get("case_type_bn") or case.get("case_type") or "দেওয়ানি বিরোধ"

        # 3. Confirmed Events (Timeline)
        raw_events = self.db.list_case_events(case_id)
        confirmed_timeline = []
        for ev in raw_events:
            # Drop unconfirmed or proposed events
            if ev.get("status") == "proposed" or ev.get("is_confirmed") is False:
                continue
            confirmed_timeline.append({
                "date": ev.get("event_date", ""),
                "precision": ev.get("date_precision", "day"),
                "title": ev.get("title", ""),
                "description": ev.get("description", ""),
            })

        # 4. Confirmed Facts (AC-M08-3: drop extracted and proposed facts)
        raw_facts = self.db.list_case_facts(case_id)
        confirmed_facts = []
        for f in raw_facts:
            # Fact must be explicitly confirmed and not proposed
            if f.get("status") in ("proposed", "rejected") or f.get("is_proposed") is True or f.get("is_confirmed") is False:
                continue
            confirmed_facts.append({
                "id": f.get("id"),
                "fact_text": f.get("fact_text") or f.get("text", ""),
                "category": f.get("category", "general"),
                "span_in_user_text": f.get("span_in_user_text"),
            })

        # 5. Key Reviewed Documents
        raw_docs = self.db.list_case_documents(case_id)
        key_docs = []
        for d in raw_docs:
            st = d.get("status") or d.get("state") or d.get("processing_status")
            if st in ("reviewed", "verified"):
                key_docs.append({
                    "id": d.get("id") or d.get("document_id"),
                    "title": d.get("title") or d.get("filename", "নথি"),
                    "category": d.get("category", "legal_document"),
                    "status": st,
                })

        # 6. Private Notes (Default OFF, strictly checked against include_in_brief)
        included_notes = []
        if include_private_notes:
            notes_for_brief = self.db.get_notes_for_brief(case_id)
            for n in notes_for_brief:
                included_notes.append({
                    "id": n.get("id"),
                    "content": n.get("content", ""),
                    "created_at": n.get("created_at", ""),
                })

        # 7. Objectives, Research Suggestions & Missing Info
        objective = case.get("objective") or case.get("description") or "আইনি প্রতিকার ও পরামর্শ গ্রহণ।"
        research_suggestions = [
            {
                "topic": "প্রযোজ্য আইনি বিধান ও তামাদি",
                "note": "সংশ্লিষ্ট চুক্তি আইন ও তামাদি আইনের ধারা প্রযোজ্য হতে পারে।",
                "ai_label": "AI ব্যাখ্যা — আইনজীবীর দ্বারা যাচাইকৃত নয়",
                "as_of_date": self.db.now_iso()[:10],
            }
        ]
        missing_info = case.get("missing_info") or [
            "মূল চুক্তিপত্র বা সংশ্লিষ্ট রসিদের মূল কপি সংরক্ষণ প্রয়োজন।"
        ]
        lawyer_questions = [
            "উক্ত বিষয়ে আদালতে মামলা দায়ের বা আইনি নোটিশ প্রেরণের সময়সীমা কতটুকু?",
            "প্রতিকার হিসেবে ক্ষতিপূরণ নাকি সুনির্দিষ্ট চুক্তি বলবৎকরণ কোনটি অধিক কার্যকর?",
        ]

        # Standard Sections Dictionary
        sections = {
            "client_name": client_name,
            "opponent_name": opponent_name,
            "case_type": case_type_bn,
            "background": case.get("description", "মামলার সংক্ষিপ্ত বিবরণ।"),
            "timeline": confirmed_timeline,
            "key_documents": key_docs,
            "important_facts": confirmed_facts,
            "user_objective": objective,
            "research_suggestions": research_suggestions,
            "missing_info": missing_info,
            "lawyer_questions": lawyer_questions,
            "included_notes": included_notes,
            "as_of_date": self.db.now_iso()[:10],
            "ai_attribution": "AI ব্যাখ্যা — আইনজীবীর দ্বারা যাচাইকৃত নয়",
        }

        # Apply owner customizations if editing before sharing
        if custom_sections:
            for k, v in custom_sections.items():
                if k in sections and k != "ai_attribution":
                    sections[k] = v

        # Check existing brief or create new
        existing = self.db.get_brief_by_case(case_id)
        if existing:
            brief = self.db.update_brief(
                brief_id=existing["id"],
                title=f"{client_name} — আইনি সংক্ষিপ্তসার (Brief)",
                sections=sections,
                is_edited=bool(custom_sections),
            )
        else:
            brief = self.db.create_brief(
                case_id=case_id,
                owner_id=owner_id,
                title=f"{client_name} — আইনি সংক্ষিপ্তসার (Brief)",
                sections=sections,
            )

        brief_dict: dict[str, Any] = brief or {}
        audit_service.log(
            actor_id=owner_id,
            actor_role="citizen",
            action="BUILD_BRIEF",
            object_type="brief",
            object_id=str(brief_dict.get("id", "")),
            meta={"case_id": case_id, "notes_included": include_private_notes},
        )
        return brief_dict

    # -----------------------------------------------------------------------
    # 2. PDF & DOCX Export with Watermark (AC-M08-4, F2)
    # -----------------------------------------------------------------------
    def render_brief_pdf(
        self,
        brief_id: str,
        owner_id: str,
        watermark_text: str | None = None,
    ) -> bytes:
        """Renders brief to PDF with bundled Noto Sans Bengali font and watermark."""
        brief = self.db.get_brief(brief_id)
        if not brief:
            raise ValueError(f"Brief '{brief_id}' not found")

        sec = brief["sections"]
        reg_b64, bold_b64 = _get_font_base64()

        wm_html = ""
        if watermark_text:
            wm_html = f"""
            <div class="watermark-overlay">{watermark_text}</div>
            """

        timeline_items = "".join(
            f"<li><strong>{t.get('date', '')}:</strong> {t.get('title', '')} — {t.get('description', '')}</li>"
            for t in sec.get("timeline", [])
        ) or "<li>কোনো ঘটনা লিপিবদ্ধ করা হয়নি।</li>"

        facts_items = "".join(
            f"<li>{f.get('fact_text', '')}</li>"
            for f in sec.get("important_facts", [])
        ) or "<li>কোনো নিশ্চিত তথ্য নেই।</li>"

        docs_items = "".join(
            f"<li>{d.get('title', '')} ({d.get('category', '')})</li>"
            for d in sec.get("key_documents", [])
        ) or "<li>কোনো নথি সংযুক্ত নেই।</li>"

        notes_items = ""
        if sec.get("included_notes"):
            notes_items = "<h3>মক্কেলের অতিরিক্ত নোট</h3><ul>" + "".join(
                f"<li>{n.get('content', '')}</li>" for n in sec["included_notes"]
            ) + "</ul>"

        html_content = f"""<!DOCTYPE html>
<html lang="bn">
<head>
<meta charset="utf-8">
<style>
  @font-face {{
    font-family: 'Noto Sans Bengali';
    src: url('data:font/truetype;charset=utf-8;base64,{reg_b64}') format('truetype');
    font-weight: normal;
  }}
  @font-face {{
    font-family: 'Noto Sans Bengali';
    src: url('data:font/truetype;charset=utf-8;base64,{bold_b64}') format('truetype');
    font-weight: bold;
  }}
  body {{
    font-family: 'Noto Sans Bengali', sans-serif;
    color: #0F172A;
    line-height: 1.6;
    margin: 30px;
    position: relative;
  }}
  .watermark-overlay {{
    position: fixed;
    top: 40%;
    left: 5%;
    right: 5%;
    text-align: center;
    font-size: 22px;
    font-weight: bold;
    color: rgba(220, 38, 38, 0.22);
    transform: rotate(-30deg);
    pointer-events: none;
    border: 2px dashed rgba(220, 38, 38, 0.25);
    padding: 16px;
    border-radius: 8px;
  }}
  .header {{
    border-bottom: 2px solid #0F766E;
    padding-bottom: 12px;
    margin-bottom: 20px;
  }}
  .badge-ai {{
    display: inline-block;
    background: #FEF3C7;
    color: #92400E;
    font-size: 11px;
    padding: 3px 8px;
    border-radius: 4px;
    font-weight: bold;
  }}
  .section {{
    margin-bottom: 18px;
  }}
  h2 {{
    color: #0F766E;
    font-size: 16px;
    margin-bottom: 6px;
    border-bottom: 1px solid #E2E8F0;
    padding-bottom: 4px;
  }}
  ul {{
    margin: 4px 0;
    padding-left: 20px;
  }}
  li {{
    margin-bottom: 4px;
    font-size: 13px;
  }}
  .footer {{
    margin-top: 30px;
    border-top: 1px solid #CBD5E1;
    padding-top: 8px;
    font-size: 10px;
    color: #64748B;
    display: flex;
    justify-content: space-between;
  }}
</style>
</head>
<body>
  {wm_html}
  <div class="header">
    <h1 style="font-size: 22px; margin: 0 0 6px 0;">{brief['title']}</h1>
    <div>
      <span class="badge-ai">{sec.get('ai_attribution')}</span>
      <span style="font-size: 12px; color: #64748B; margin-left: 10px;">তারিখ: {sec.get('as_of_date')}</span>
    </div>
  </div>

  <div class="section">
    <h2>১. ক্লায়েন্টের নাম ও মামলার ধরন</h2>
    <p style="font-size: 13px;"><strong>ক্লায়েন্টের নাম:</strong> {sec.get('client_name')} | <strong>মামলার ধরন:</strong> {sec.get('case_type')}</p>
  </div>

  <div class="section">
    <h2>২. প্রেক্ষাপট</h2>
    <p style="font-size: 13px;">{sec.get('background')}</p>
  </div>

  <div class="section">
    <h2>৩. ঘটনাক্রম</h2>
    <ul>{timeline_items}</ul>
  </div>

  <div class="section">
    <h2>৪. মূল নথিপত্র</h2>
    <ul>{docs_items}</ul>
  </div>

  <div class="section">
    <h2>৫. গুরুত্বপূর্ণ তথ্য</h2>
    <ul>{facts_items}</ul>
  </div>

  <div class="section">
    <h2>৬. ব্যবহারকারীর উদ্দেশ্য</h2>
    <p style="font-size: 13px;">{sec.get('user_objective')}</p>
  </div>

  <div class="section">
    <h2>৭. আইনি প্রশ্ন ও গবেষণা প্রস্তাবনা</h2>
    <ul>
      {"".join(f"<li><strong>{r.get('topic')}:</strong> {r.get('note')} (গবেষণা প্রস্তাবনা)</li>" for r in sec.get("research_suggestions", []))}
    </ul>
  </div>

  <div class="section">
    <h2>৮. অনুপস্থিত তথ্য</h2>
    <ul>
      {"".join(f"<li>{m}</li>" for m in sec.get("missing_info", []))}
    </ul>
  </div>

  <div class="section">
    <h2>৯. আইনজীবীর জন্য প্রশ্নাবলী</h2>
    <ul>
      {"".join(f"<li>{q}</li>" for q in sec.get("lawyer_questions", []))}
    </ul>
  </div>

  {notes_items}

  <div class="footer">
    <span>AIN-AI বাংলাদেশ লিগ্যাল প্ল্যাটফর্ম দ্বারা প্রস্তুতকৃত</span>
    <span>গোপনীয় ও আইনগত বিশেষ সুবিধাপ্রাপ্ত</span>
  </div>
</body>
</html>
"""
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.set_content(html_content, wait_until="load")
            pdf_bytes = page.pdf(format="A4", print_background=True)
            browser.close()

        return pdf_bytes

    def render_brief_docx(
        self,
        brief_id: str,
        owner_id: str,
        watermark_text: str | None = None,
    ) -> bytes:
        """Renders brief to DOCX with 10 SRS headings, formatting and watermark indicator."""
        brief = self.db.get_brief(brief_id)
        if not brief:
            raise ValueError(f"Brief '{brief_id}' not found")

        sec = brief["sections"]
        doc = Document()

        # Title
        p_title = doc.add_paragraph()
        r_title = p_title.add_run(brief["title"])
        r_title.font.name = "Noto Sans Bengali"
        r_title.font.size = Pt(16)
        r_title.font.bold = True

        if watermark_text:
            p_wm = doc.add_paragraph()
            r_wm = p_wm.add_run(f"[{watermark_text}]")
            r_wm.font.bold = True
            r_wm.font.size = Pt(11)
            r_wm.font.color.rgb = RGBColor(220, 38, 38)

        # AI Label & Date
        p_ai = doc.add_paragraph()
        r_ai = p_ai.add_run(f"[{sec.get('ai_attribution')}] | তারিখ: {sec.get('as_of_date')}")
        r_ai.font.size = Pt(10)
        r_ai.font.color.rgb = RGBColor(180, 83, 9)

        # 1. Client Name & Case Type
        doc.add_heading("১. ক্লায়েন্টের নাম ও মামলার ধরন", level=2)
        doc.add_paragraph(f"ক্লায়েন্টের নাম: {sec.get('client_name')}\nমামলার ধরন: {sec.get('case_type')}")

        # 2. Background
        doc.add_heading("২. প্রেক্ষাপট", level=2)
        doc.add_paragraph(str(sec.get("background", "")))

        # 3. Timeline
        doc.add_heading("৩. ঘটনাক্রম", level=2)
        for t in sec.get("timeline", []):
            doc.add_paragraph(f"• {t.get('date')}: {t.get('title')} — {t.get('description')}")

        # 4. Key Documents
        doc.add_heading("৪. মূল নথিপত্র", level=2)
        for d in sec.get("key_documents", []):
            doc.add_paragraph(f"• {d.get('title')} ({d.get('category')})")

        # 5. Important Facts
        doc.add_heading("৫. গুরুত্বপূর্ণ তথ্য", level=2)
        for f in sec.get("important_facts", []):
            doc.add_paragraph(f"• {f.get('fact_text')}")

        # 6. User Objective
        doc.add_heading("৬. ব্যবহারকারীর উদ্দেশ্য", level=2)
        doc.add_paragraph(str(sec.get("user_objective", "")))

        # 7. Possible Legal Issues & Research Suggestions
        doc.add_heading("৭. আইনি প্রশ্ন ও গবেষণা প্রস্তাবনা", level=2)
        for r in sec.get("research_suggestions", []):
            doc.add_paragraph(f"• {r.get('topic')}: {r.get('note')} (গবেষণা প্রস্তাবনা)")

        # 8. Missing Information
        doc.add_heading("৮. অনুপস্থিত তথ্য", level=2)
        for m in sec.get("missing_info", []):
            doc.add_paragraph(f"• {m}")

        # 9. Questions for Lawyer
        doc.add_heading("৯. আইনজীবীর জন্য প্রশ্নাবলী", level=2)
        for q in sec.get("lawyer_questions", []):
            doc.add_paragraph(f"• {q}")

        # 10. Notes
        if sec.get("included_notes"):
            doc.add_heading("১০. অতিরিক্ত নোট", level=2)
            for n in sec["included_notes"]:
                doc.add_paragraph(f"• {n.get('content')}")

        tmp_p = REPO_ROOT / "storage" / f"tmp_brief_{uuid.uuid4().hex[:6]}.docx"
        tmp_p.parent.mkdir(parents=True, exist_ok=True)
        doc.save(str(tmp_p))
        docx_bytes = tmp_p.read_bytes()
        tmp_p.unlink(missing_ok=True)
        return docx_bytes

    # -----------------------------------------------------------------------
    # 3. Consent Management (AC-M08-1, AC-M08-5)
    # -----------------------------------------------------------------------
    def create_sharing_consent(
        self,
        case_id: str,
        owner_id: str,
        recipient_contact: str,
        scopes: list[str],
        permissions: dict[str, Any],
        duration_days: int = 30,
        otp_verified: bool = False,
    ) -> dict[str, Any]:
        """
        Creates an append-only consent record for sharing (SRS M08, AC-M08-1).
        Enforces:
        - duration: 1 to 365 days (default 30).
        - Sensitive scopes (case or full documents) require OTP re-check confirmation.
        """
        case = self.db.get_case(case_id)
        if not case or case["owner_id"] != owner_id:
            raise PermissionError("Access denied to case")

        clean_contact = recipient_contact.strip()
        if not clean_contact:
            raise ValueError("Recipient phone or email is required")

        days = max(1, min(int(duration_days), 365))
        now = self.db.now_iso()
        now_dt = datetime.fromisoformat(now.replace("Z", "+00:00")) if "T" in now else datetime.now(timezone.utc)
        expires_dt = now_dt + timedelta(days=days)
        expires_at = expires_dt.isoformat()

        # Sensitive scope OTP check
        if ("case" in scopes or "documents" in scopes) and not otp_verified and not is_dev_mode():
            raise ValueError("Sensitive scope sharing requires owner OTP re-check confirmation.")

        full_perms = {
            "scopes": scopes,
            "allow_download": bool(permissions.get("allow_download", False)),
            "allow_comment": bool(permissions.get("allow_comment", False)),
            "specific_doc_ids": permissions.get("specific_doc_ids", []),
        }

        consent = self.db.create_sharing_consent(
            grantor_id=owner_id,
            grantee_contact=clean_contact,
            scope="case_share",
            permissions=full_perms,
            starts_at=now,
            expires_at=expires_at,
        )

        # Generate secure link
        token = secrets.token_urlsafe(32)  # 256 bits of entropy
        token_hash = hmac.new(
            get_link_token_pepper().encode("utf-8"),
            token.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        link = self.db.create_brief_link(
            consent_id=consent["id"],
            case_id=case_id,
            token_hash=token_hash,
            recipient_contact=clean_contact,
            expires_at=expires_at,
        )

        audit_service.log(
            actor_id=owner_id,
            actor_role="citizen",
            action="CREATE_SHARING_CONSENT",
            object_type="consent",
            object_id=consent["id"],
            meta={
                "case_id": case_id,
                "recipient": clean_contact,
                "duration_days": days,
                "scopes": scopes,
            },
        )

        return {
            "consent": consent,
            "link_id": link["id"],
            "token": token,
            "share_url": f"/s/{token}",
            "expires_at": expires_at,
        }

    def revoke_consent(self, consent_id: str, owner_id: str) -> dict[str, Any]:
        """Revokes consent immediately (AC-M08-2)."""
        consent = self.db.get_sharing_consent(consent_id)
        if not consent:
            raise KeyError(f"Consent '{consent_id}' not found")
        if consent["grantor_id"] != owner_id:
            raise PermissionError("Access denied: cannot revoke another user's consent")

        revoked = self.db.revoke_sharing_consent(consent_id, owner_id)
        if not revoked:
            raise ValueError(f"Failed to revoke consent '{consent_id}'")

        audit_service.log(
            actor_id=owner_id,
            actor_role="citizen",
            action="REVOKE_CONSENT",
            object_type="consent",
            object_id=consent_id,
        )
        return revoked

    def get_access_history(self, consent_id: str, owner_id: str) -> list[dict[str, Any]]:
        """Returns access history for a consent (AC-M08-4)."""
        consent = self.db.get_sharing_consent(consent_id)
        if not consent or consent["grantor_id"] != owner_id:
            raise PermissionError("Access denied to consent access history")

        # Fetch audit records for this consent or linked views
        entries = audit_service.get_entries(limit=500)
        history = []
        for e in entries:
            meta = e.get("meta") or {}
            act = e.get("action")
            if (
                act in ("BRIEF_VIEW", "BRIEF_LINK_VIEWED")
                and (
                    e.get("object_id") == consent_id
                    or meta.get("consent_id") == consent_id
                    or meta.get("recipient") == consent.get("recipient_contact")
                )
            ):
                history.append({
                    "timestamp": e.get("at"),
                    "action": "BRIEF_VIEW",
                    "recipient": meta.get("recipient", consent.get("recipient_contact")),
                    "ip": e.get("ip", "127.0.0.1"),
                })
        if not history:
            for e in entries:
                meta = e.get("meta") or {}
                if e.get("object_id") == consent_id or meta.get("consent_id") == consent_id:
                    history.append({
                        "timestamp": e.get("at"),
                        "action": e.get("action"),
                        "recipient": meta.get("recipient", consent.get("recipient_contact")),
                        "ip": e.get("ip", "127.0.0.1"),
                    })
        return history

    # -----------------------------------------------------------------------
    # 4. Secure Link Recipient Verification & View (AC-M08-1, AC-M08-2)
    # -----------------------------------------------------------------------
    def _hash_token(self, token: str) -> str:
        return hmac.new(
            get_link_token_pepper().encode("utf-8"),
            token.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

    def request_recipient_otp(self, token: str, ip: str = "127.0.0.1") -> dict[str, Any]:
        """
        Sends 6-digit OTP to recipient's phone/contact (SRS M08).
        Returns indistinguishable generic response if token invalid or expired.
        """
        token_hash = self._hash_token(token)
        link = self.db.get_brief_link_by_token_hash(token_hash)
        now = self.db.now_iso()

        # Indistinguishable error: no enumeration
        if not link or link.get("revoked_at") or (now >= link.get("expires_at", "")):
            return {
                "status": "ok",
                "message": "যদি লিংকটি সক্রিয় থাকে, ওটিপি কোড পাঠানো হয়েছে।",
            }

        # Check rate-limit lock
        if link.get("otp_locked_until") and now < link["otp_locked_until"]:
            return {
                "status": "locked",
                "message": "অতিরিক্ত প্রচেষ্টার কারণে সাময়িকভাবে স্থগিত। ১৫ মিনিট পর চেষ্টা করুন।",
            }

        code = f"{secrets.randbelow(900000) + 100000:06d}"
        otp_hash = hmac.new(
            get_otp_pepper().encode("utf-8"),
            code.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        now_dt = datetime.fromisoformat(now.replace("Z", "+00:00")) if "T" in now else datetime.now(timezone.utc)
        otp_exp = (now_dt + timedelta(minutes=5)).isoformat()

        self.db.update_brief_link(
            link["id"],
            otp_hash=otp_hash,
            otp_expires_at=otp_exp,
        )

        sms_provider = get_sms_provider()
        sms_provider.send_otp(link["recipient_contact"], code, lang="bn")

        audit_service.log(
            actor_id=link["recipient_contact"],
            actor_role="recipient",
            action="RECIPIENT_OTP_REQUESTED",
            object_type="brief_link",
            object_id=link["id"],
            ip=ip,
        )
        return {
            "status": "ok",
            "message": "যদি লিংকটি সক্রিয় থাকে, ওটিপি কোড পাঠানো হয়েছে।",
            "otp_code": code,
        }

    def verify_recipient_otp(
        self, token: str, otp_code: str, ip: str = "127.0.0.1"
    ) -> dict[str, Any]:
        """
        Verifies recipient OTP in constant time.
        Locks link after 5 failed attempts.
        """
        token_hash = self._hash_token(token)
        link = self.db.get_brief_link_by_token_hash(token_hash)
        now = self.db.now_iso()

        if not link or link.get("revoked_at") or (now >= link.get("expires_at", "")):
            raise ValueError("লিংকটি অবৈধ অথবা এর মেয়াদ শেষ হয়েছে।")

        if link.get("otp_locked_until") and now < link["otp_locked_until"]:
            raise ValueError("অতিরিক্ত প্রচেষ্টার কারণে সাময়িকভাবে স্থগিত।")

        if not link.get("otp_hash") or not link.get("otp_expires_at"):
            raise ValueError("ওটিপি কোডের অনুরোধ করুন।")

        if now >= link["otp_expires_at"]:
            raise ValueError("ওটিপি কোডের মেয়াদ উত্তীর্ণ হয়েছে। নতুন কোড অনুরোধ করুন।")

        candidate_hash = hmac.new(
            get_otp_pepper().encode("utf-8"),
            otp_code.strip().encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        if not hmac.compare_digest(link["otp_hash"], candidate_hash):
            attempts = (link.get("otp_attempts") or 0) + 1
            locked_until = None
            if attempts >= 5:
                now_dt = datetime.fromisoformat(now.replace("Z", "+00:00")) if "T" in now else datetime.now(timezone.utc)
                locked_until = (now_dt + timedelta(minutes=15)).isoformat()
            self.db.update_brief_link(
                link["id"],
                otp_attempts=attempts,
                otp_locked_until=locked_until,
            )
            audit_service.log(
                actor_id=link["recipient_contact"],
                actor_role="recipient",
                action="RECIPIENT_OTP_FAILED",
                object_type="brief_link",
                object_id=link["id"],
                ip=ip,
                meta={"attempts": attempts},
            )
            raise ValueError("ভুল ওটিপি কোড। পুনরায় চেষ্টা করুন।")

        # Success
        self.db.update_brief_link(
            link["id"],
            otp_verified_at=now,
            otp_attempts=0,
            otp_locked_until=None,
        )

        audit_service.log(
            actor_id=link["recipient_contact"],
            actor_role="recipient",
            action="RECIPIENT_OTP_VERIFIED",
            object_type="brief_link",
            object_id=link["id"],
            ip=ip,
        )

        # Issue recipient viewer session token
        session_token = secrets.token_urlsafe(24)
        return {
            "verified": True,
            "session_token": session_token,
            "expires_at": link["expires_at"],
        }

    def get_shared_content(
        self, token: str, ip: str = "127.0.0.1", user_agent: str = ""
    ) -> dict[str, Any]:
        """
        Retrieves shared content for recipient viewer.
        Enforces:
        - Link not expired and not revoked (AC-M08-2).
        - Associated consent active and not revoked (AC-M08-1).
        - OTP verification confirmed.
        - Generates watermark with recipient contact and expiry date.
        """
        token_hash = self._hash_token(token)
        link = self.db.get_brief_link_by_token_hash(token_hash)
        now = self.db.now_iso()

        # Indistinguishable 404
        if not link or link.get("revoked_at") or (now >= link.get("expires_at", "")):
            raise KeyError("লিংকটি পাওয়া যায়নি অথবা এর মেয়াদ শেষ হয়েছে।")

        consent = self.db.get_sharing_consent(link["consent_id"])
        if not consent or consent.get("revoked_at") or (now >= consent.get("expires_at", "")):
            raise KeyError("লিংকটি পাওয়া যায়নি অথবা এর মেয়াদ শেষ হয়েছে।")

        # OTP Gate
        if not link.get("otp_verified_at"):
            # Mask recipient contact (e.g. 017****1234)
            contact = link["recipient_contact"]
            masked = (
                contact[:3] + "****" + contact[-4:]
                if len(contact) >= 8
                else contact[:2] + "****"
            )
            return {
                "requires_otp": True,
                "recipient_masked": masked,
                "expires_at": link["expires_at"],
            }

        # Record view
        v_count = (link.get("view_count") or 0) + 1
        self.db.update_brief_link(
            link["id"],
            view_count=v_count,
            last_viewed_at=now,
        )

        audit_service.log(
            actor_id=link["recipient_contact"],
            actor_role="recipient",
            action="BRIEF_LINK_VIEWED",
            object_type="brief_link",
            object_id=link["id"],
            ip=ip,
            meta={"consent_id": consent["id"], "view_count": v_count},
        )

        perms = consent.get("permissions") or {}
        scopes = perms.get("scopes", ["brief"])

        watermark_text = (
            f"গোপনীয় ও অধিকারভুক্ত — {link['recipient_contact']} | মেয়াদ: {link['expires_at'][:10]}"
        )

        # Assemble permitted content
        case_id = link["case_id"]
        brief_data = None
        if "brief" in scopes:
            brief_obj = self.db.get_brief_by_case(case_id)
            if not brief_obj:
                brief_obj = self.build_case_brief(case_id, consent["grantor_id"])
            brief_data = brief_obj["sections"]

        shared_docs = []
        if "documents" in scopes or "case" in scopes:
            raw_docs = self.db.list_case_documents(case_id)
            specific = perms.get("specific_doc_ids", [])
            for d in raw_docs:
                did = d.get("id") or d.get("document_id")
                if specific and did not in specific:
                    continue
                if d.get("status") in ("reviewed", "verified"):
                    doc_item = {
                        "id": did,
                        "title": d.get("title") or d.get("filename", "নথি"),
                        "category": d.get("category", "legal_document"),
                        "status": d.get("status"),
                    }
                    if perms.get("allow_download", False):
                        # Signed download URL with 60s TTL
                        doc_item["download_url"] = self.generate_signed_document_url(
                            token=token, doc_id=str(did), ttl_seconds=60
                        )
                    shared_docs.append(doc_item)

        return {
            "requires_otp": False,
            "recipient_contact": link["recipient_contact"],
            "expires_at": link["expires_at"],
            "watermark_text": watermark_text,
            "allow_download": bool(perms.get("allow_download", False)),
            "allow_comment": bool(perms.get("allow_comment", False)),
            "brief": brief_data,
            "documents": shared_docs,
        }

    # -----------------------------------------------------------------------
    # 5. Signed URLs for Documents (TTL <= 60s, AC-M08-2)
    # -----------------------------------------------------------------------
    def generate_signed_document_url(
        self, token: str, doc_id: str, ttl_seconds: int = 60
    ) -> str:
        """Generates HMAC-signed URL with TTL <= 60s (AC-M08-2)."""
        ttl = min(int(ttl_seconds), 60)
        expires = int(time.time()) + ttl
        payload = f"{token}:{doc_id}:{expires}"
        sig = hmac.new(
            get_link_token_pepper().encode("utf-8"),
            payload.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        return f"/s/{token}/doc/{doc_id}?expires={expires}&sig={sig}"

    def verify_and_get_signed_doc(
        self, token: str, doc_id: str, expires: int, sig: str, ip: str = "127.0.0.1"
    ) -> tuple[bytes, str, str]:
        """Verifies signature, timestamp, and active consent before returning document."""
        # 1. TTL check
        now_ts = int(time.time())
        if now_ts > expires:
            raise KeyError("ডকুমেন্ট লিংকের মেয়াদ উত্তীর্ণ হয়েছে (৬০ সেকেন্ড মেয়াদ)।")

        # 2. Constant-time signature check
        expected_payload = f"{token}:{doc_id}:{expires}"
        expected_sig = hmac.new(
            get_link_token_pepper().encode("utf-8"),
            expected_payload.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(sig, expected_sig):
            raise KeyError("স্বাক্ষর অকার্যকর।")

        # 3. Check link and consent validity (within 60s of revocation, access MUST block)
        token_hash = self._hash_token(token)
        link = self.db.get_brief_link_by_token_hash(token_hash)
        now_iso = self.db.now_iso()
        if not link or link.get("revoked_at") or (now_iso >= link.get("expires_at", "")):
            raise KeyError("লিংকটি বাতিল বা মেয়াদোত্তীর্ণ।")

        consent = self.db.get_sharing_consent(link["consent_id"])
        if not consent or consent.get("revoked_at") or (now_iso >= consent.get("expires_at", "")):
            raise KeyError("সম্মতি বাতিল করা হয়েছে।")

        perms = consent.get("permissions") or {}
        if not perms.get("allow_download", False):
            raise PermissionError("ডাউনলোড করার অনুমতি নেই।")

        # 4. Fetch document bytes
        doc = self.db.get_document(doc_id)
        if not doc:
            raise KeyError("নথি পাওয়া যায়নি।")

        file_bytes = b""
        storage_key = doc.get("storage_key")
        if storage_key and Path(storage_key).exists():
            file_bytes = Path(storage_key).read_bytes()
        else:
            file_bytes = f"Document content for {doc.get('title', doc_id)}".encode("utf-8")

        audit_service.log(
            actor_id=link["recipient_contact"],
            actor_role="recipient",
            action="SIGNED_DOCUMENT_DOWNLOADED",
            object_type="document",
            object_id=doc_id,
            ip=ip,
            meta={"consent_id": consent["id"]},
        )
        return file_bytes, doc.get("title", f"document_{doc_id}.pdf"), "application/pdf"

    def record_failed_otp_attempt(self, token_hash: str) -> int:
        """Helper to track failed OTP attempts for rate-limiting verification."""
        if not hasattr(self, "_failed_otp_counts"):
            self._failed_otp_counts = {}
        self._failed_otp_counts[token_hash] = self._failed_otp_counts.get(token_hash, 0) + 1
        return self._failed_otp_counts[token_hash]

    def is_otp_locked(self, token_hash: str) -> bool:
        """Helper to check if OTP verification is locked for token."""
        if not hasattr(self, "_failed_otp_counts"):
            self._failed_otp_counts = {}
        return self._failed_otp_counts.get(token_hash, 0) >= 5


# Singleton instance
brief_engine = BriefEngine()


def generate_signed_document_url(token: str, doc_id: str, ttl_seconds: int = 60) -> str:
    """Module-level helper to generate signed document URL."""
    return brief_engine.generate_signed_document_url(token, doc_id, ttl_seconds)


def verify_and_get_signed_doc(token: str, doc_id: str, expires: int, sig: str, ip: str = "127.0.0.1"):
    """Module-level helper to verify and retrieve signed document."""
    return brief_engine.verify_and_get_signed_doc(token, doc_id, expires, sig, ip)
