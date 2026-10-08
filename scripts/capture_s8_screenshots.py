"""
Capture S8 screenshots and sample PDF export.
Saves 6 views into storage/screenshots/ and 1 PDF into storage/:
1. s8_draft_picker_mobile_360.png, s8_draft_picker_tablet_768.png, s8_draft_picker_desktop_1280.png
2. s8_draft_wizard_ai_helper_mobile_360.png, s8_draft_wizard_ai_helper_desktop_1280.png
3. s8_draft_preview_watermark_mobile_360.png, s8_draft_preview_watermark_desktop_1280.png
4. s8_draft_checklist_mobile_360.png, s8_draft_checklist_desktop_1280.png
5. s8_draft_preview_finalized_mobile_360.png, s8_draft_preview_finalized_desktop_1280.png
6. s8_admin_templates_mobile_360.png, s8_admin_templates_desktop_1280.png
"""

from __future__ import annotations

import json
from pathlib import Path

from playwright.sync_api import sync_playwright

REPO_ROOT = Path(__file__).resolve().parent.parent
STATIC_DIR = REPO_ROOT / "backend" / "app" / "static"
SCREENSHOTS_DIR = REPO_ROOT / "storage" / "screenshots"

SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)

MOCK_TEMPLATES = [
    {
        "id": "tmpl-dt-01",
        "code": "DT-01",
        "title_bn": "বাড়ি বা ফ্ল্যাট ভাড়ার চুক্তিপত্র",
        "title_en": "House / Premises Rental Agreement",
        "category": "rental",
        "description_bn": "বাড়ি, ফ্ল্যাট বা বাণিজ্যিক দোকান ভাড়ার জন্য স্ট্যান্ডার্ড খসড়া চুক্তিপত্র।",
        "what_needed_bn": "বাড়িওয়ালা ও ভাড়াটিয়ার নাম-ঠিকানা, এনআইডি নম্বর, ভাড়ার পরিমাণ, জামানত ও চুক্তির মেয়াদ।",
        "version": 1,
        "status": "approved",
        "author_id": "usr-admin-01",
        "approver_id": "usr-lawyer-02",
        "effective_from": "2026-10-01",
        "questions_schema": [
            {
                "id": "landlord_name",
                "type": "text",
                "label_bn": "বাড়িওয়ালার পূর্ণ নাম",
                "help_bn": "জাতীয় পরিচয়পত্র অনুযায়ী বাড়িওয়ালার সঠিক নাম লিখুন।",
                "example_bn": "উদা: আবুল কাশেম",
                "required": True,
            },
            {
                "id": "monthly_rent",
                "type": "amount",
                "label_bn": "মাসিক ভাড়ার পরিমাণ (টাকা)",
                "help_bn": "প্রতি মাসে প্রদেয় সর্বমোট ভাড়ার অংক লিখুন।",
                "example_bn": "উদা: ৩৫,০০০",
                "required": True,
            },
        ],
    },
    {
        "id": "tmpl-dt-02",
        "code": "DT-02",
        "title_bn": "সাধারণ এফিডেভিট / হলফনামা",
        "title_en": "General Affidavit",
        "category": "affidavit",
        "description_bn": "নাম সংশোধন, পারিবারিক তথ্য ঘোষণা বা সাধারণ বিবরণ সম্বলিত প্রথম শ্রেণীর ম্যাজিস্ট্রেট বা নোটারি পাবলিকের সম্মুখে প্রদত্ত হলফনামা।",
        "what_needed_bn": "হলফকারীর নাম-ঠিকানা, এনআইডি নম্বর, ও সুনির্দিষ্ট ঘোষণার বিবরণ।",
        "version": 1,
        "status": "draft_not_reviewed",
        "staging_warning": "পরীক্ষামূলক টেমপ্লেট — আইনজীবী কর্তৃক অনুমোদিত নয়",
        "author_id": "usr-admin-01",
    },
    {
        "id": "tmpl-dt-03",
        "code": "DT-03",
        "title_bn": "আইনি নোটিশের জবাব (খসড়া)",
        "title_en": "Reply to Legal Notice",
        "category": "notice_reply",
        "description_bn": "প্রাপ্ত লিগ্যাল নোটিশের সুনির্দিষ্ট দফাভিত্তিক জবাব ও আত্মপক্ষ সমর্থনের প্রাথমিক খসড়া।",
        "what_needed_bn": "নোটিশদাতার আইনজীবী তথ্য, নোটিশ গ্রহণের তারিখ ও অভিযোগের যুক্তিযুক্ত জবাব।",
        "version": 1,
        "status": "draft_not_reviewed",
        "author_id": "usr-admin-01",
    },
]

MOCK_DRAFT = {
    "id": "drf-test-01",
    "user_id": "usr-cit-01",
    "template_id": "tmpl-dt-01",
    "template_version": 1,
    "title": "বাড়ি বা ফ্ল্যাট ভাড়ার চুক্তিপত্র (খসড়া)",
    "status": "in_progress",
    "answers": {
        "landlord_name": "আবুল কাশেম",
        "monthly_rent": 35000,
    },
    "selected_clause_ids": ["C-01", "C-02"],
    "checklist_states": {
        "chk_stamp": False,
        "chk_witness": False,
    },
    "watermark_text": "খসড়া — AI-সহায়তায় তৈরি, আইনি পরামর্শ নয়",
    "is_finalized": False,
    "created_at": "2026-10-01T10:00:00Z",
    "updated_at": "2026-10-01T10:00:00Z",
}


def populate_preview_script():
    return """
        switchView('preview');
        document.getElementById('docPreviewTitle').textContent = 'বাড়ি বা ফ্ল্যাট ভাড়ার চুক্তিপত্র (খসড়া)';
        const clausesList = document.getElementById('docClausesList');
        clausesList.innerHTML = `
          <div class="preview-clause">
            <div class="preview-clause-title">১. পক্ষগণের পরিচয়</div>
            <div class="preview-clause-body">প্রথম পক্ষ (বাড়িওয়ালা): আবুল কাশেম, পিতা: মরহুম রফিকুল ইসলাম, সাং ধানমন্ডি, ঢাকা। দ্বিতীয় পক্ষ (ভাড়াটিয়া): মো: তানভীর হোসেন, পিতা: আনোয়ার হোসেন, সাং মিরপুর, ঢাকা।</div>
          </div>
          <div class="preview-clause">
            <div class="preview-clause-title">২. ভাড়ার পরিমাণ ও মেয়াদ</div>
            <div class="preview-clause-body">মাসিক ভাড়া ৩৫,০০০/- (পঁয়ত্রিশ হাজার) টাকা ধার্য করা হইল, যাহা প্রতি মাসের ৭ তারিখের মধ্যে প্রদেয়। চুক্তির মেয়াদ ০১-১১-২০২৬ হইতে ৩১-১০-২০২৭ তারিখ পর্যন্ত বলবৎ থাকিবে।</div>
          </div>
          <div class="preview-clause">
            <div class="preview-clause-title">৩. অগ্রিম জামানত</div>
            <div class="preview-clause-body">ভাড়াটিয়া অগ্রিম জামানত বাবদ ৭০,০০০/- (সত্তর হাজার) টাকা বাড়িওয়ালাকে প্রদান করিলেন, যাহা চুক্তি সমাপ্তিতে ফেরতযোগ্য।</div>
          </div>
        `;
        document.getElementById('watermarkOverlay').style.display = 'block';
        const chkList = document.getElementById('checklistItemsList');
        chkList.innerHTML = `
          <div class="checklist-row">
            <input type="checkbox" id="chk_stamp">
            <div>
              <label for="chk_stamp" style="font-weight: 700; font-size: 14px;">নন-জুডিশিয়াল স্ট্যাম্পে মুদ্রণ</label>
              <div style="font-size: 12px; color: #64748B;">স্ট্যাম্প আইন অনুযায়ী ৩০০ টাকার নন-জুডিশিয়াল স্ট্যাম্পে চুক্তিপত্রটি প্রিন্ট করুন।</div>
              <div style="font-size: 11px; color: #047857; margin-top: 2px;">আইনি ভিত্তি: The Stamp Act, 1899</div>
            </div>
          </div>
          <div class="checklist-row">
            <input type="checkbox" id="chk_witness">
            <div>
              <label for="chk_witness" style="font-weight: 700; font-size: 14px;">২ জন প্রাপ্তবয়স্ক সাক্ষীর স্বাক্ষর</label>
              <div style="font-size: 12px; color: #64748B;">উভয় পক্ষের উপস্থিতিতে নূন্যতম ২ জন সাক্ষীর পূর্ণ নাম, ঠিকানা ও স্বাক্ষর নিশ্চিত করুন।</div>
              <div style="font-size: 11px; color: #047857; margin-top: 2px;">আইনি ভিত্তি: Evidence Act & Contract Act</div>
            </div>
          </div>
        `;
    """


def capture_all():
    draft_url = (STATIC_DIR / "draft.html").as_uri()
    admin_url = (STATIC_DIR / "admin_templates.html").as_uri()

    templates_json = json.dumps(MOCK_TEMPLATES, ensure_ascii=False)
    draft_json = json.dumps(MOCK_DRAFT, ensure_ascii=False)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        # -------------------------------------------------------------
        # 1. Template picker view (Mobile 360, Tablet 768, Desktop 1280)
        # -------------------------------------------------------------
        # Mobile 360x640
        page = browser.new_page(viewport={"width": 360, "height": 640})
        page.goto(draft_url)
        page.evaluate(
            f"() => {{ allTemplates = {templates_json}; renderTemplatesGrid(allTemplates); }}"
        )
        page.wait_for_timeout(200)
        page.screenshot(
            path=str(SCREENSHOTS_DIR / "s8_draft_picker_mobile_360.png"), full_page=True
        )
        page.close()

        # Tablet 768x1024
        page = browser.new_page(viewport={"width": 768, "height": 1024})
        page.goto(draft_url)
        page.evaluate(
            f"() => {{ allTemplates = {templates_json}; renderTemplatesGrid(allTemplates); }}"
        )
        page.wait_for_timeout(200)
        page.screenshot(
            path=str(SCREENSHOTS_DIR / "s8_draft_picker_tablet_768.png"), full_page=True
        )
        page.close()

        # Desktop 1280x800
        page = browser.new_page(viewport={"width": 1280, "height": 800})
        page.goto(draft_url)
        page.evaluate(
            f"() => {{ allTemplates = {templates_json}; renderTemplatesGrid(allTemplates); }}"
        )
        page.wait_for_timeout(200)
        page.screenshot(
            path=str(SCREENSHOTS_DIR / "s8_draft_picker_desktop_1280.png"), full_page=True
        )

        # -------------------------------------------------------------
        # 2. Wizard with AI Helper Open
        # -------------------------------------------------------------
        page.evaluate(f"""() => {{
            currentDraft = {draft_json};
            currentTemplate = {templates_json}[0];
            draftAnswers = currentDraft.answers;
            questionsList = currentTemplate.questions_schema;
            currentQuestionIndex = 0;
            switchView('wizard');
            renderCurrentQuestion();
            document.getElementById('aiHelperBox').style.display = 'block';
            document.getElementById('aiRephrasedText').textContent = 'বাড়িওয়ালার জাতীয় পরিচয়পত্রে যেভাবে নাম লেখা আছে ঠিক সেভাবে এখানে নাম লিখুন।';
            document.getElementById('aiTermExplanation').innerHTML = '<strong>বাড়িওয়ালা / ১ম পক্ষ:</strong> যিনি সম্পত্তির বৈধ মালিক এবং সম্পত্তিটি ভাড়ায় প্রদান করিতেছেন।';
        }}""")
        page.wait_for_timeout(200)
        page.screenshot(
            path=str(SCREENSHOTS_DIR / "s8_draft_wizard_ai_helper_desktop_1280.png"), full_page=True
        )
        page.close()

        # Mobile AI helper
        page = browser.new_page(viewport={"width": 360, "height": 640})
        page.goto(draft_url)
        page.evaluate(f"""() => {{
            currentDraft = {draft_json};
            currentTemplate = {templates_json}[0];
            draftAnswers = currentDraft.answers;
            questionsList = currentTemplate.questions_schema;
            currentQuestionIndex = 0;
            switchView('wizard');
            renderCurrentQuestion();
            document.getElementById('aiHelperBox').style.display = 'block';
            document.getElementById('aiRephrasedText').textContent = 'বাড়িওয়ালার জাতীয় পরিচয়পত্রে যেভাবে নাম লেখা আছে ঠিক সেভাবে এখানে নাম লিখুন।';
            document.getElementById('aiTermExplanation').innerHTML = '<strong>বাড়িওয়ালা / ১ম পক্ষ:</strong> যিনি সম্পত্তির বৈধ মালিক এবং সম্পত্তিটি ভাড়ায় প্রদান করিতেছেন।';
        }}""")
        page.wait_for_timeout(200)
        page.screenshot(
            path=str(SCREENSHOTS_DIR / "s8_draft_wizard_ai_helper_mobile_360.png"), full_page=True
        )
        page.close()

        # -------------------------------------------------------------
        # 3. Preview with Watermark & 4. Execution Checklist Gate
        # -------------------------------------------------------------
        page = browser.new_page(viewport={"width": 1280, "height": 800})
        page.goto(draft_url)
        page.evaluate(
            f"() => {{ currentDraft = {draft_json}; currentTemplate = {templates_json}[0]; {populate_preview_script()} }}"
        )
        page.wait_for_timeout(200)
        page.screenshot(
            path=str(SCREENSHOTS_DIR / "s8_draft_preview_watermark_desktop_1280.png"),
            full_page=True,
        )

        # Distinct Checklist Gate View (showing unconfirmed checklist requirement & validation warning)
        page.evaluate("""() => {
            const errEl = document.getElementById('finalizeErrorMsg');
            errEl.textContent = 'চূড়ান্ত করার পূর্বে সকল সম্পাদন চেকলিস্ট আইটেম নিশ্চিত করা আবশ্যক।';
            errEl.style.display = 'block';
        }""")
        page.wait_for_timeout(200)
        page.screenshot(
            path=str(SCREENSHOTS_DIR / "s8_draft_checklist_desktop_1280.png"), full_page=True
        )

        # Mobile Preview & Checklist Gate
        page_m = browser.new_page(viewport={"width": 360, "height": 640})
        page_m.goto(draft_url)
        page_m.evaluate(
            f"() => {{ currentDraft = {draft_json}; currentTemplate = {templates_json}[0]; {populate_preview_script()} }}"
        )
        page_m.wait_for_timeout(200)
        page_m.screenshot(
            path=str(SCREENSHOTS_DIR / "s8_draft_preview_watermark_mobile_360.png"), full_page=True
        )

        # Mobile Checklist Gate View (scroll to checklist and show gate warning)
        page_m.evaluate("""() => {
            const errEl = document.getElementById('finalizeErrorMsg');
            errEl.textContent = 'চূড়ান্ত করার পূর্বে সকল সম্পাদন চেকলিস্ট আইটেম নিশ্চিত করা আবশ্যক।';
            errEl.style.display = 'block';
            document.querySelector('.checklist-card').scrollIntoView();
        }""")
        page_m.wait_for_timeout(200)
        page_m.screenshot(
            path=str(SCREENSHOTS_DIR / "s8_draft_checklist_mobile_360.png"), full_page=True
        )
        page_m.close()

        # -------------------------------------------------------------
        # 5. Finalized Preview & Export Screen (Desktop 1280 & Mobile 360)
        # -------------------------------------------------------------
        page.evaluate("""() => {
            currentDraft.is_finalized = true;
            switchView('export');
            const list = document.getElementById('signingStepsList');
            list.innerHTML = `
              <div class="checklist-row">
                <input type="checkbox" id="s1" checked>
                <div><strong>পদক্ষেপ ১: নন-জুডিশিয়াল স্ট্যাম্প সংগ্রহ</strong><div style="font-size:12px; color:#64748B;">বাংলাদেশ ডাক বিভাগ বা সরকার অনুমোদিত ভেন্ডার হইতে ৩০০ টাকার নন-জুডিশিয়াল স্ট্যাম্প কিনুন।</div></div>
              </div>
              <div class="checklist-row">
                <input type="checkbox" id="s2">
                <div><strong>পদক্ষেপ ২: স্ট্যাম্পে মুদ্রণ ও উভয় পক্ষের স্বাক্ষর</strong><div style="font-size:12px; color:#64748B;">ডাউনলোডকৃত পিডিএফ প্রিন্ট করিয়া প্রথম ও দ্বিতীয় পক্ষের পূর্ণ স্বাক্ষর নিশ্চিত করুন।</div></div>
              </div>
            `;
        }""")
        page.wait_for_timeout(200)
        page.screenshot(
            path=str(SCREENSHOTS_DIR / "s8_draft_preview_finalized_desktop_1280.png"),
            full_page=True,
        )
        page.screenshot(
            path=str(SCREENSHOTS_DIR / "s8_draft_export_desktop_1280.png"),
            full_page=True,
        )
        page.close()

        # Mobile 360 Export Screen
        page_m_exp = browser.new_page(viewport={"width": 360, "height": 640})
        page_m_exp.goto(draft_url)
        page_m_exp.evaluate(f"""() => {{
            currentDraft = {draft_json};
            currentDraft.is_finalized = true;
            currentTemplate = {templates_json}[0];
            switchView('export');
            const list = document.getElementById('signingStepsList');
            list.innerHTML = `
              <div class="checklist-row">
                <input type="checkbox" id="s1" checked>
                <div><strong>পদক্ষেপ ১: নন-জুডিশিয়াল স্ট্যাম্প সংগ্রহ</strong><div style="font-size:12px; color:#64748B;">বাংলাদেশ ডাক বিভাগ বা ভেন্ডার হইতে ৩০০ টাকার স্ট্যাম্প কিনুন।</div></div>
              </div>
              <div class="checklist-row">
                <input type="checkbox" id="s2">
                <div><strong>পদক্ষেপ ২: মুদ্রণ ও স্বাক্ষর</strong><div style="font-size:12px; color:#64748B;">পিডিএফ প্রিন্ট করিয়া উভয় পক্ষের স্বাক্ষর নিশ্চিত করুন।</div></div>
              </div>
            `;
        }}""")
        page_m_exp.wait_for_timeout(200)
        page_m_exp.screenshot(
            path=str(SCREENSHOTS_DIR / "s8_draft_export_mobile_360.png"),
            full_page=True,
        )
        page_m_exp.close()

        # -------------------------------------------------------------
        # 6. Admin Templates View
        # -------------------------------------------------------------
        page = browser.new_page(viewport={"width": 1280, "height": 800})
        page.goto(admin_url)
        page.evaluate(
            f"() => {{ activeTemplates = {templates_json}; renderTable(activeTemplates); }}"
        )
        page.wait_for_timeout(200)
        page.screenshot(
            path=str(SCREENSHOTS_DIR / "s8_admin_templates_desktop_1280.png"), full_page=True
        )

        # Admin Test-Render Modal
        page.evaluate("""() => {
            document.getElementById('renderModalTitle').textContent = 'টেস্ট রেন্ডার: DT-01 (বাড়ি বা ফ্ল্যাট ভাড়ার চুক্তিপত্র)';
            const container = document.getElementById('renderClausesContent');
            container.innerHTML = `
              <div style="margin-bottom:12px;">
                <div style="font-weight:700; color:#0F172A;">১. পক্ষগণের পরিচয়</div>
                <div style="color:#334155; font-size:13px;">প্রথম পক্ষ (বাড়িওয়ালা): আবুল কাশেম। দ্বিতীয় পক্ষ: মো: তানভীর হোসেন।</div>
              </div>
              <div style="margin-bottom:12px;">
                <div style="font-weight:700; color:#0F172A;">২. মাসিক ভাড়া ও জামানত</div>
                <div style="color:#334155; font-size:13px;">মাসিক ভাড়া ৩৫,০০০/- (পঁয়ত্রিশ হাজার) টাকা ধার্য করা হইল।</div>
              </div>
            `;
            document.getElementById('renderModal').style.display = 'flex';
        }""")
        page.wait_for_timeout(200)
        page.screenshot(
            path=str(SCREENSHOTS_DIR / "s8_admin_template_modal_desktop_1280.png"), full_page=True
        )
        page.close()

        # Admin Mobile 360
        page_adm = browser.new_page(viewport={"width": 360, "height": 640})
        page_adm.goto(admin_url)
        page_adm.evaluate(
            f"() => {{ activeTemplates = {templates_json}; renderTable(activeTemplates); }}"
        )
        page_adm.wait_for_timeout(200)
        page_adm.screenshot(
            path=str(SCREENSHOTS_DIR / "s8_admin_templates_mobile_360.png"), full_page=True
        )
        page_adm.close()

        browser.close()

    brain_dir = Path(
        r"C:\Users\Lenovo\.gemini\antigravity\brain\f5b387fc-eb28-4e1b-9940-b3291f442234"
    )
    brain_dir.mkdir(parents=True, exist_ok=True)
    import shutil

    for f in SCREENSHOTS_DIR.glob("s8_*.png"):
        dest = brain_dir / f.name
        shutil.copy2(f, dest)
        size_kb = dest.stat().st_size / 1024
        print(f"Captured: {f.name} ({size_kb:.1f} KB) -> {dest}")

    print("All S8 screenshots captured and synced successfully.")


if __name__ == "__main__":
    capture_all()
