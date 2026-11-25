#!/usr/bin/env python3
"""
Generates 10 static HTML mock-ups in docs/ux_mockups/ for Directive U0.3 & U0.4,
renders each at 360px, 768px, and 1280px via Playwright,
saves PNG screenshots to storage/mockup_screenshots/,
and writes reports/mockup_hashes.json.
"""

import hashlib
import json
from pathlib import Path

from playwright.sync_api import sync_playwright

REPO_ROOT = Path(__file__).resolve().parent.parent
MOCKUPS_DIR = REPO_ROOT / "docs" / "ux_mockups"
SCREENSHOTS_DIR = REPO_ROOT / "storage" / "mockup_screenshots"
REPORTS_DIR = REPO_ROOT / "reports"

MOCKUPS_DIR.mkdir(parents=True, exist_ok=True)
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

COMMON_CSS = """
  :root {
    --primary: #047857;
    --primary-light: #ecfdf5;
    --primary-dark: #064e3b;
    --surface: #ffffff;
    --bg: #f8fafc;
    --text: #0f172a;
    --text-muted: #64748b;
    --border: #e2e8f0;
    --amber-bg: #fffbeb;
    --amber-border: #fde68a;
    --amber-text: #92400e;
    --danger: #dc2626;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: 'Noto Sans Bengali', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    background: var(--bg);
    color: var(--text);
    display: flex;
    flex-direction: column;
    min-height: 100vh;
  }
  header {
    background: var(--surface);
    border-bottom: 1px solid var(--border);
    padding: 0.75rem 1rem;
    display: flex;
    align-items: center;
    justify-content: space-between;
  }
  .brand {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-weight: 700;
    color: var(--primary-dark);
    font-size: 1.1rem;
  }
  .disclaimer-banner {
    background: var(--amber-bg);
    border-bottom: 1px solid var(--amber-border);
    color: var(--amber-text);
    padding: 0.5rem 1rem;
    font-size: 0.8rem;
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }
  main {
    flex: 1;
    max-width: 900px;
    width: 100%;
    margin: 0 auto;
    padding: 1rem;
    display: flex;
    flex-direction: column;
    gap: 1rem;
  }
  .chat-bubble {
    padding: 0.85rem 1rem;
    border-radius: 1rem;
    max-width: 85%;
    font-size: 0.95rem;
    line-height: 1.5;
  }
  .chat-ai {
    background: var(--surface);
    border: 1px solid var(--border);
    align-self: flex-start;
    border-bottom-left-radius: 0.25rem;
  }
  .chat-user {
    background: var(--primary);
    color: #ffffff;
    align-self: flex-end;
    border-bottom-right-radius: 0.25rem;
  }
  .ai-badge {
    display: inline-block;
    font-size: 0.75rem;
    font-weight: 700;
    color: var(--primary);
    margin-bottom: 0.35rem;
  }
  .chips-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
    gap: 0.75rem;
    margin-top: 1rem;
  }
  .chip-card {
    background: var(--surface);
    border: 1px solid var(--border);
    padding: 1rem;
    border-radius: 0.75rem;
    text-align: left;
    font-size: 0.9rem;
    font-weight: 600;
    cursor: pointer;
    display: flex;
    flex-direction: column;
    gap: 0.35rem;
    transition: all 0.2s;
  }
  .chip-card:hover {
    border-color: var(--primary);
    background: var(--primary-light);
  }
  .chip-card span.icon { font-size: 1.5rem; }
  .bottom-nav {
    background: var(--surface);
    border-top: 1px solid var(--border);
    display: flex;
    justify-content: space-around;
    padding: 0.5rem 0;
  }
  .nav-item {
    display: flex;
    flex-direction: column;
    align-items: center;
    font-size: 0.75rem;
    color: var(--text-muted);
    text-decoration: none;
    gap: 0.2rem;
  }
  .nav-item.active {
    color: var(--primary);
    font-weight: 700;
  }
  .btn {
    padding: 0.6rem 1rem;
    border-radius: 0.5rem;
    font-weight: 600;
    font-size: 0.9rem;
    cursor: pointer;
    border: 1px solid transparent;
  }
  .btn-primary { background: var(--primary); color: #fff; }
  .btn-outline { border-color: var(--border); background: var(--surface); color: var(--text); }
  .btn-secondary { background: #e2e8f0; color: #0f172a; }
  .action-buttons {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem;
    margin-top: 0.75rem;
  }
  .dual-path {
    display: flex;
    gap: 0.5rem;
    margin-top: 0.5rem;
    font-size: 0.85rem;
  }
"""

MOCKUP_TEMPLATES = {
    # 1. Home / Chat Start
    "01_home_chat_start.html": f"""<!DOCTYPE html>
<html lang="bn">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>আইন-AI সহকারী — শুরু</title>
  <style>{COMMON_CSS}</style>
</head>
<body>
  <header>
    <div class="brand">⚖️ আইন-AI</div>
    <div style="font-size: 0.85rem; color: var(--text-muted);">নাগরিক ডেমো [নমুনা - যাচাই বাকি]</div>
  </header>
  <div class="disclaimer-banner">
    ⚠️ <strong>সতর্কতা:</strong> এটি তথ্য ও পরবর্তী ধাপ সহায়িকা, কোনো আদালতের আইনি সিদ্ধান্ত বা আইনজীবীর বিকল্প নয়।
  </div>
  <main>
    <div class="chat-bubble chat-ai">
      <div class="ai-badge">🤖 আইন-AI সহকারী | আমি আইনজীবী নই</div>
      <p>আসসালামু আলাইকুম। আমি আপনার আইনি ডিজিটাল সহকারী। আপনি যেকোনো আইনি প্রশ্ন লিখতে পারেন বা নিচের বিষয়গুলো থেকে বেছে নিতে পারেন:</p>
      <div class="chips-grid">
        <button class="chip-card">
          <span class="icon">📝</span>
          <span>দলিল লিখুন</span>
          <small style="color: var(--text-muted); font-size: 0.75rem;">ভাড়াচুক্তি, নোটিশ, জিডি</small>
        </button>
        <button class="chip-card">
          <span class="icon">🔍</span>
          <span>নোটিশ বুঝুন</span>
          <small style="color: var(--text-muted); font-size: 0.75rem;">চিঠির ছবি তুলে অর্থ জানুন</small>
        </button>
        <button class="chip-card">
          <span class="icon">🗣️</span>
          <span>সমস্যা বলুন</span>
          <small style="color: var(--text-muted); font-size: 0.75rem;">বিরোধ বা ঘটনা খুলে বলুন</small>
        </button>
        <button class="chip-card">
          <span class="icon">📁</span>
          <span>কাগজ সংরক্ষণ</span>
          <small style="color: var(--text-muted); font-size: 0.75rem;">দলিল বা রসিদ ফোল্ডারে রাখুন</small>
        </button>
      </div>
    </div>
  </main>
  <div style="padding: 0.75rem 1rem; background: var(--surface); border-top: 1px solid var(--border); display: flex; gap: 0.5rem; max-width: 900px; margin: 0 auto; width: 100%;">
    <input type="text" placeholder="কী করতে চান বলুন... (যেমন: ভাড়াচুক্তি করতে চাই)" style="flex: 1; padding: 0.75rem 1rem; border-radius: 0.5rem; border: 1px solid var(--border); font-size: 0.95rem;" />
    <button class="btn btn-primary">পাঠান</button>
  </div>
  <nav class="bottom-nav">
    <a href="#" class="nav-item active"><span>💬</span><span>সহায়িকা</span></a>
    <a href="#" class="nav-item"><span>📁</span><span>ফোল্ডার</span></a>
    <a href="#" class="nav-item"><span>➕</span><span>যোগ</span></a>
    <a href="#" class="nav-item"><span>📖</span><span>সাহায্য</span></a>
    <a href="#" class="nav-item"><span>👤</span><span>আমার</span></a>
  </nav>
</body>
</html>
""",

    # 2. Draft Mode Collecting
    "02_draft_mode_collecting.html": f"""<!DOCTYPE html>
<html lang="bn">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>দলিল ড্রাফট তথ্য সংগ্রহ [নমুনা - যাচাই বাকি]</title>
  <style>{COMMON_CSS}
    .checklist {{
      background: var(--primary-light);
      border: 1px solid #a7f3d0;
      border-radius: 0.5rem;
      padding: 0.75rem 1rem;
      margin-top: 0.5rem;
      font-size: 0.85rem;
    }}
    .checklist-item {{ display: flex; align-items: center; gap: 0.4rem; margin-bottom: 0.25rem; }}
  </style>
</head>
<body>
  <header>
    <div class="brand">⚖️ আইন-AI</div>
    <div style="font-size: 0.85rem; color: var(--primary); font-weight: 600;">আবাসিক বাড়িভাড়া চুক্তিপত্র</div>
  </header>
  <main>
    <div class="chat-bubble chat-user">
      আমি ফ্ল্যাট ভাড়ার একটি চুক্তিপত্র করতে চাই।
    </div>
    <div class="chat-bubble chat-ai">
      <div class="ai-badge">🤖 আইন-AI সহকারী | অনুমোদিত টেমপ্লেট T-RENT-01</div>
      <p>নিশ্চয়ই। আবাসিক বাড়িভাড়া চুক্তি প্রস্তুত করতে আমাদের নিম্নের ৫টি তথ্য প্রয়োজন হবে:</p>
      <div class="checklist">
        <div class="checklist-item"><span>⏳</span><span>১. বাড়িওয়ালার নাম ও পিতা/স্বামীর নাম</span></div>
        <div class="checklist-item"><span>⏳</span><span>২. ভাড়াটিয়ার নাম ও পরিচয়</span></div>
        <div class="checklist-item"><span>⏳</span><span>৩. ভাড়াকৃত ফ্ল্যাট ও বাড়ির সঠিক ঠিকানা</span></div>
        <div class="checklist-item"><span>⏳</span><span>৪. মাসিক ভাড়া ও অগ্রিম জামানত (টাকায়)</span></div>
        <div class="checklist-item"><span>⏳</span><span>৫. চুক্তির মেয়াদ (কত মাস বা বছর)</span></div>
      </div>
      <p style="margin-top: 0.75rem;">প্রথমে বলুন: <strong>বাড়িওয়ালার পুরো নাম ও পিতা/স্বামীর নাম কী?</strong></p>
      <div class="dual-path">
        <button class="btn btn-outline" style="font-size: 0.8rem;">🛠️ নিজে ফর্ম পূরণ করি</button>
        <button class="btn btn-primary" style="font-size: 0.8rem;">🤖 চ্যাটে বলে যাই</button>
      </div>
    </div>
  </main>
  <nav class="bottom-nav">
    <a href="#" class="nav-item active"><span>💬</span><span>সহায়িকা</span></a>
    <a href="#" class="nav-item"><span>📁</span><span>ফোল্ডার</span></a>
    <a href="#" class="nav-item"><span>➕</span><span>যোগ</span></a>
    <a href="#" class="nav-item"><span>📖</span><span>সাহায্য</span></a>
    <a href="#" class="nav-item"><span>👤</span><span>আমার</span></a>
  </nav>
</body>
</html>
""",

    # 3. Understood Confirmation (HR-14)
    "03_understood_confirmation.html": f"""<!DOCTYPE html>
<html lang="bn">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>আমি যা বুঝলাম কনফার্মেশন [নমুনা - যাচাই বাকি]</title>
  <style>{COMMON_CSS}
    .summary-card {{
      background: #f1f5f9;
      border: 1px solid var(--border);
      border-radius: 0.5rem;
      padding: 0.75rem 1rem;
      margin: 0.75rem 0;
    }}
    .summary-row {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 0.4rem 0;
      border-bottom: 1px dashed var(--border);
      font-size: 0.85rem;
    }}
    .edit-link {{ color: var(--primary); text-decoration: underline; cursor: pointer; font-size: 0.8rem; }}
  </style>
</head>
<body>
  <header>
    <div class="brand">⚖️ আইন-AI</div>
    <div style="font-size: 0.85rem;">তথ্য নিশ্চিতকরণ</div>
  </header>
  <main>
    <div class="chat-bubble chat-ai" style="max-width: 100%;">
      <div class="ai-badge">🤖 আইন-AI সহকারী | তথ্য পরীক্ষণ (HR-14)</div>
      <p>আপনার দেওয়া বক্তব্য থেকে <strong>আমি যা বুঝলাম</strong>:</p>
      <div class="summary-card">
        <div class="summary-row">
          <span><strong>বাড়িওয়ালা:</strong> মোঃ রফিকুল ইসলাম</span>
          <span class="edit-link">[সম্পাদনা]</span>
        </div>
        <div class="summary-row">
          <span><strong>ভাড়াটিয়া:</strong> তানভীর আহমেদ</span>
          <span class="edit-link">[সম্পাদনা]</span>
        </div>
        <div class="summary-row">
          <span><strong>ঠিকানা:</strong> ফ্ল্যাট ৪/বি, বাড়ি ১২, রোড ৫, ধানমন্ডি, ঢাকা</span>
          <span class="edit-link">[সম্পাদনা]</span>
        </div>
        <div class="summary-row">
          <span><strong>মাসিক ভাড়া:</strong> ২৫,০০০ টাকা (পঁচিশ হাজার টাকা)</span>
          <span class="edit-link">[সম্পাদনা]</span>
        </div>
        <div class="summary-row" style="border-bottom: none;">
          <span><strong>জামানত:</strong> ৫০,০০০ টাকা (পঞ্চাশ হাজার টাকা)</span>
          <span class="edit-link">[সম্পাদনা]</span>
        </div>
      </div>
      <p style="font-size: 0.85rem; color: var(--text-muted);">দলিল চূড়ান্ত করার আগে উপরের তথ্যগুলো ভালো করে দেখে নিন।</p>
      <div class="action-buttons">
        <button class="btn btn-primary">সব ঠিক আছে, এগিয়ে যান ✓</button>
        <button class="btn btn-outline">তথ্য সংশোধন করুন</button>
      </div>
    </div>
  </main>
  <nav class="bottom-nav">
    <a href="#" class="nav-item active"><span>💬</span><span>সহায়িকা</span></a>
    <a href="#" class="nav-item"><span>📁</span><span>ফোল্ডার</span></a>
    <a href="#" class="nav-item"><span>➕</span><span>যোগ</span></a>
    <a href="#" class="nav-item"><span>📖</span><span>সাহায্য</span></a>
    <a href="#" class="nav-item"><span>👤</span><span>আমার</span></a>
  </nav>
</body>
</html>
""",

    # 4. Missing Information Prompt
    "04_missing_info_prompt.html": f"""<!DOCTYPE html>
<html lang="bn">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>অনুপস্থিত তথ্য তাগিদ [নমুনা - যাচাই বাকি]</title>
  <style>{COMMON_CSS}</style>
</head>
<body>
  <header>
    <div class="brand">⚖️ আইন-AI</div>
    <div style="font-size: 0.85rem;">অনুপস্থিত তথ্য</div>
  </header>
  <main>
    <div class="chat-bubble chat-ai">
      <div class="ai-badge">🤖 আইন-AI সহকারী | টেমপ্লেট ভ্যালিডেশন</div>
      <p>ধন্যবাদ! প্রায় সব তথ্য পাওয়া গেছে, তবে <strong>১টি আবশ্যক তথ্য এখনো বাকি আছে:</strong></p>
      <div style="background: #fef2f2; border: 1px solid #fecaca; padding: 0.75rem; border-radius: 0.5rem; margin: 0.5rem 0; color: #991b1b; font-size: 0.85rem;">
        ⚠️ <strong>চুক্তির মেয়াদ উল্লেখ করা হয়নি।</strong> ভাড়াচুক্তি সাধারণত ১১ মাস, ১ বছর বা ২ বছরের জন্য হয়ে থাকে।
      </div>
      <p>দয়া করে জানান: এই চুক্তিটি কত দিনের বা কত মাসের জন্য কার্যকর থাকবে?</p>
      <div class="action-buttons">
        <button class="btn btn-secondary" style="font-size: 0.85rem;">১১ মাস</button>
        <button class="btn btn-secondary" style="font-size: 0.85rem;">১ বছর (১২ মাস)</button>
        <button class="btn btn-secondary" style="font-size: 0.85rem;">২ বছর</button>
      </div>
    </div>
  </main>
  <nav class="bottom-nav">
    <a href="#" class="nav-item active"><span>💬</span><span>সহায়িকা</span></a>
    <a href="#" class="nav-item"><span>📁</span><span>ফোল্ডার</span></a>
    <a href="#" class="nav-item"><span>➕</span><span>যোগ</span></a>
    <a href="#" class="nav-item"><span>📖</span><span>সাহায্য</span></a>
    <a href="#" class="nav-item"><span>👤</span><span>আমার</span></a>
  </nav>
</body>
</html>
""",

    # 5. Draft Ready with Folder Created
    "05_draft_ready_folder.html": f"""<!DOCTYPE html>
<html lang="bn">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>খসড়া প্রস্তুত ও ফোল্ডার সংরক্ষণ [নমুনা - যাচাই বাকি]</title>
  <style>{COMMON_CSS}
    .folder-alert {{
      background: var(--primary-light);
      border: 1px solid #6ee7b7;
      padding: 0.85rem 1rem;
      border-radius: 0.75rem;
      margin: 0.75rem 0;
      display: flex;
      align-items: center;
      justify-content: space-between;
    }}
  </style>
</head>
<body>
  <header>
    <div class="brand">⚖️ আইন-AI</div>
    <div style="font-size: 0.85rem; color: var(--primary);">খসড়া সম্পন্ন ✓</div>
  </header>
  <main>
    <div class="chat-bubble chat-ai" style="max-width: 100%;">
      <div class="ai-badge">🤖 আইন-AI সহকারী | দলিল প্রস্তুত সম্পন্ন</div>
      <p>🎉 আপনার <strong>আবাসিক বাড়িভাড়া চুক্তিপত্র (খসড়া)</strong> সফলভাবে তৈরি হয়েছে!</p>

      <div class="folder-alert">
        <div>
          <div style="font-size: 0.85rem; color: var(--primary-dark); font-weight: 700;">📁 স্বয়ংক্রিয় ফোল্ডার তৈরি হয়েছে:</div>
          <div style="font-size: 0.95rem; font-weight: 600;">ধানমন্ডি ফ্ল্যাট ভাড়াচুক্তি (২০২৬)</div>
        </div>
        <button class="btn btn-outline" style="font-size: 0.8rem;">নাম পরিবর্তন</button>
      </div>

      <p style="font-size: 0.85rem; color: var(--text-muted); margin-bottom: 0.5rem;">
        দলিলটিতে জলছাপ যুক্ত রয়েছে। আপনি এখনই পিডিএফ ডাউনলোড করতে পারেন অথবা ফোল্ডারে দেখতে পারেন।
      </p>

      <div class="action-buttons">
        <button class="btn btn-primary">📄 পিডিএফ ডাউনলোড করুন</button>
        <button class="btn btn-outline">📁 ফোল্ডারে খুলুন</button>
        <button class="btn btn-outline">⚖️ আইনজীবীকে দেখান</button>
      </div>
    </div>
  </main>
  <nav class="bottom-nav">
    <a href="#" class="nav-item active"><span>💬</span><span>সহায়িকা</span></a>
    <a href="#" class="nav-item"><span>📁</span><span>ফোল্ডার</span></a>
    <a href="#" class="nav-item"><span>➕</span><span>যোগ</span></a>
    <a href="#" class="nav-item"><span>📖</span><span>সাহায্য</span></a>
    <a href="#" class="nav-item"><span>👤</span><span>আমার</span></a>
  </nav>
</body>
</html>
""",

    # 6. Folders View with Left File Panel
    "06_folders_view_left_panel.html": f"""<!DOCTYPE html>
<html lang="bn">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>ফোল্ডার ও ফাইল প্যানেল [নমুনা - যাচাই বাকি]</title>
  <style>{COMMON_CSS}
    .layout-split {{
      display: grid;
      grid-template-columns: 280px 1fr;
      gap: 1.5rem;
      width: 100%;
    }}
    @media (max-width: 768px) {{
      .layout-split {{ grid-template-columns: 1fr; }}
    }}
    .sidebar-panel {{
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 0.75rem;
      padding: 1rem;
    }}
    .folder-item {{
      padding: 0.6rem 0.75rem;
      border-radius: 0.5rem;
      margin-bottom: 0.35rem;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 0.5rem;
      font-size: 0.85rem;
    }}
    .folder-item.active {{
      background: var(--primary-light);
      color: var(--primary-dark);
      font-weight: 700;
    }}
    .file-card {{
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 0.5rem;
      padding: 0.75rem 1rem;
      margin-bottom: 0.5rem;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }}
  </style>
</head>
<body>
  <header>
    <div class="brand">⚖️ আইন-AI</div>
    <div style="font-size: 0.85rem;">আমার ফোল্ডারসমূহ</div>
  </header>
  <main style="max-width: 1100px;">
    <div class="layout-split">
      <div class="sidebar-panel">
        <h3 style="font-size: 0.9rem; margin-bottom: 0.75rem; color: var(--text-muted);">কেস ফোল্ডার তালিকা</h3>
        <div class="folder-item active">📁 ধানমন্ডি ফ্ল্যাট ভাড়াচুক্তি</div>
        <div class="folder-item">📁 মিরপুর জমি বিরোধ [নমুনা - যাচাই বাকি]</div>
        <div class="folder-item">📁 চেক ডিজঅনার নোটিশ [নমুনা - যাচাই বাকি]</div>
      </div>
      <div>
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
          <h2>ধানমন্ডি ফ্ল্যাট ভাড়াচুক্তি (২০২৬)</h2>
          <button class="btn btn-outline" style="font-size: 0.8rem;">+ নথি যোগ করুন</button>
        </div>
        <div class="file-card">
          <div>
            <div style="font-weight: 600; font-size: 0.9rem;">📄 ভাড়াচুক্তি_খসড়া_v1.pdf</div>
            <div style="font-size: 0.75rem; color: var(--text-muted);">তৈরি: ১০ অক্টোবর ২০২৬ | অবস্থা: খসড়া</div>
          </div>
          <button class="btn btn-primary" style="font-size: 0.8rem;">ডাউনলোড</button>
        </div>
        <div class="file-card">
          <div>
            <div style="font-weight: 600; font-size: 0.9rem;">🖼️ এনআইডি_ফটোকপি.jpg</div>
            <div style="font-size: 0.75rem; color: var(--text-muted);">আপলোড: ১০ অক্টোবর ২০২৬ | ১.২ মেগাবাইট</div>
          </div>
          <button class="btn btn-outline" style="font-size: 0.8rem;">দেখুন</button>
        </div>
      </div>
    </div>
  </main>
  <nav class="bottom-nav">
    <a href="#" class="nav-item"><span>💬</span><span>সহায়িকা</span></a>
    <a href="#" class="nav-item active"><span>📁</span><span>ফোল্ডার</span></a>
    <a href="#" class="nav-item"><span>➕</span><span>যোগ</span></a>
    <a href="#" class="nav-item"><span>📖</span><span>সাহায্য</span></a>
    <a href="#" class="nav-item"><span>👤</span><span>আমার</span></a>
  </nav>
</body>
</html>
""",

    # 7. Notice Mode
    "07_notice_mode.html": f"""<!DOCTYPE html>
<html lang="bn">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>নোটিশ মোড বিশ্লেষণ [নমুনা - যাচাই বাকি]</title>
  <style>{COMMON_CSS}
    .deadline-badge {{
      background: #fef2f2;
      border: 1px solid #f87171;
      color: #991b1b;
      padding: 0.6rem 0.85rem;
      border-radius: 0.5rem;
      font-weight: 700;
      font-size: 0.85rem;
      margin: 0.5rem 0;
    }}
  </style>
</head>
<body>
  <header>
    <div class="brand">⚖️ আইন-AI</div>
    <div style="font-size: 0.85rem;">নোটিশ বিশ্লেষণ মোড</div>
  </header>
  <main>
    <div class="chat-bubble chat-user">
      [ছবি আপলোড: আইনি_নোটিশ_চেক_ডিজঅনার.jpg]
      আমাকে একজন উকিল চিঠি পাঠিয়েছে, এর অর্থ কী?
    </div>
    <div class="chat-bubble chat-ai">
      <div class="ai-badge">🤖 আইন-AI সহকারী | নথি বিশ্লেষণ পাইপলাইন</div>
      <p>আপনার আপলোডকৃত চিঠিটি পড়ে বিশ্লেষণ করা হয়েছে:</p>

      <div class="deadline-badge">
        ⏰ সময়সীমা: নোটিশ প্রাপ্তির ৩০ দিনের মধ্যে জবাব বা টাকা পরিশোধ করতে বলা হয়েছে।
      </div>

      <div style="background: var(--surface); border: 1px solid var(--border); padding: 0.75rem; border-radius: 0.5rem; font-size: 0.85rem; margin: 0.5rem 0;">
        <p><strong>দাবির বিষয়:</strong> এনআই অ্যাক্ট ১৩৮ ধারা মোতাবেক ৫,০০,০০০ টাকার চেক ডিজঅনার।</p>
        <p style="margin-top: 0.35rem; color: var(--text-muted);">
          সতর্কতা: এটি একটি সংবেদনশীল আইনি বিষয়। নোটিশের মেয়াদ পার হওয়ার পূর্বে জবাব দেওয়া বা আইনজীবীর শরণাপন্ন হওয়া প্রয়োজন।
        </p>
      </div>

      <div class="action-buttons">
        <button class="btn btn-primary">⚖️ আইনজীবীর জন্য কেস ব্রিফ তৈরি করুন</button>
        <button class="btn btn-outline">📝 নোটিশের জবাব খসড়া করুন</button>
      </div>
    </div>
  </main>
  <nav class="bottom-nav">
    <a href="#" class="nav-item active"><span>💬</span><span>সহায়িকা</span></a>
    <a href="#" class="nav-item"><span>📁</span><span>ফোল্ডার</span></a>
    <a href="#" class="nav-item"><span>➕</span><span>যোগ</span></a>
    <a href="#" class="nav-item"><span>📖</span><span>সাহায্য</span></a>
    <a href="#" class="nav-item"><span>👤</span><span>আমার</span></a>
  </nav>
</body>
</html>
""",

    # 8. Urgent Message Showing Help First (HR-16)
    "08_urgent_help_first.html": f"""<!DOCTYPE html>
<html lang="bn">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>জরুরি ট্রায়াজ ও হেল্পলাইন [নমুনা - যাচাই বাকি]</title>
  <style>{COMMON_CSS}
    .urgent-banner {{
      background: #7f1d1d;
      color: #ffffff;
      padding: 1rem;
      border-radius: 0.75rem;
      margin-bottom: 0.75rem;
    }}
    .helpline-box {{
      background: #ffffff;
      color: #0f172a;
      padding: 0.75rem;
      border-radius: 0.5rem;
      margin-top: 0.5rem;
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 0.5rem;
      font-size: 0.85rem;
    }}
  </style>
</head>
<body>
  <header>
    <div class="brand">⚖️ আইন-AI</div>
    <div style="font-size: 0.85rem; color: var(--danger); font-weight: 700;">জরুরি নিরাপত্তা মোড</div>
  </header>
  <main>
    <div class="chat-bubble chat-user">
      আমার ছোট ভাইকে পুলিশ ধরে নিয়ে গেছে, থানায় গেলে বলতেছে গ্রেপ্তার দেখাবে, মারধর করতে পারে!
    </div>
    <div class="chat-bubble chat-ai" style="max-width: 100%;">
      <div class="ai-badge">🤖 আইন-AI সহকারী | তাৎক্ষণিক জরুরি সুরক্ষা (HR-16)</div>

      <div class="urgent-banner">
        <h3 style="font-size: 1rem; margin-bottom: 0.25rem;">🚨 জরুরি সুরক্ষা ও সহায়তা সবার আগে</h3>
        <p style="font-size: 0.85rem; opacity: 0.9;">গ্রেপ্তার বা বলপ্রয়োগের ঝুঁকিতে অ্যাপের ভেতর দলিল লেখার সময় নষ্ট করবেন না। অবিলম্বে সরকারি সহায়তা নিন:</p>

        <div class="helpline-box">
          <div>
            <strong>জাতীয় জরুরি সেবা:</strong><br>
            <span style="font-size: 1.1rem; color: var(--danger); font-weight: 700;">৯৯৯</span>
            <div style="font-size: 0.75rem; color: var(--amber-text); margin-top: 0.2rem;">
              <span class="badge">[নমুনা - যাচাই বাকি]</span> (HR-16: অ্যাডমিন যাচাই বাকি)
            </div>
          </div>
          <div>
            <strong>সরকারি আইনি সহায়তা:</strong><br>
            <span style="font-size: 1.1rem; color: var(--primary); font-weight: 700;">১৬৪৩০</span>
            <div style="font-size: 0.75rem; color: var(--amber-text); margin-top: 0.2rem;">
              <span class="badge">[নমুনা - যাচাই বাকি]</span> (HR-16: অ্যাডমিন যাচাই বাকি)
            </div>
          </div>
        </div>
      </div>

      <p style="font-size: 0.85rem;">আইনি অধিকার নির্দেশিকা: ২৪ ঘণ্টার মধ্যে ম্যাজিস্ট্রেট আদালতে হাজির করার সাংবিধানিক অধিকার রয়েছে।</p>

      <div class="action-buttons">
        <button class="btn btn-primary">⚖️ বারের অন-ডিউটি আইনজীবীর তথ্য দেখুন</button>
        <button class="btn btn-outline">জিডি বা অভিযোগ তথ্য নোট রাখুন</button>
      </div>
    </div>
  </main>
  <nav class="bottom-nav">
    <a href="#" class="nav-item active"><span>💬</span><span>সহায়িকা</span></a>
    <a href="#" class="nav-item"><span>📁</span><span>ফোল্ডার</span></a>
    <a href="#" class="nav-item"><span>➕</span><span>যোগ</span></a>
    <a href="#" class="nav-item"><span>📖</span><span>সাহায্য</span></a>
    <a href="#" class="nav-item"><span>👤</span><span>আমার</span></a>
  </nav>
</body>
</html>
""",

    # 9. Messy Input Options (U0.4)
    "09_messy_input_options.html": f"""<!DOCTYPE html>
<html lang="bn">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>অগোছালো ইনপুট অপশন নির্বাচন [নমুনা - যাচাই বাকি]</title>
  <style>{COMMON_CSS}</style>
</head>
<body>
  <header>
    <div class="brand">⚖️ আইন-AI</div>
    <div style="font-size: 0.85rem;">সহায়িকা মোড</div>
  </header>
  <main>
    <div class="chat-bubble chat-user">
      ভাই, আমার বাড়িওয়ালা বলছে আগামী মাসে বাসা ছাড়তে হবে, ৩ বছর আছি, চুক্তি করা নাই
    </div>
    <div class="chat-bubble chat-ai">
      <div class="ai-badge">🤖 আইন-AI সহকারী | তথ্য ও পরবর্তী ধাপ</div>
      <p>আপনার কথা শুনে বুঝলাম <strong>বাড়িভাড়া ও বাসা ছাড়ার নোটিশ সংক্রান্ত সমস্যা</strong> হচ্ছে।</p>
      <p style="margin-top: 0.35rem; font-size: 0.85rem; color: var(--text-muted);">
        বাড়িভাড়া নিয়ন্ত্রণ আইনে সাধারণত যুক্তিসঙ্গত সময় ও নোটিশ প্রদানের নিয়ম রয়েছে। আপনি কী পদক্ষেপ নিতে চান?
      </p>

      <div style="display: flex; flex-direction: column; gap: 0.5rem; margin-top: 0.75rem;">
        <button class="btn btn-outline" style="text-align: left; padding: 0.75rem;">
          📄 <strong>বাড়িভাড়ার আইন ও নোটিশের নিয়ম দেখুন</strong><br>
          <small style="color: var(--text-muted);">আইন অনুযায়ী বাসা ছাড়ার জন্য কতদিন সময় পাবেন</small>
        </button>
        <button class="btn btn-outline" style="text-align: left; padding: 0.75rem;">
          📝 <strong>বাড়িওয়ালাকে জানানোর জন্য একটি পত্র ড্রাফট করুন</strong><br>
          <small style="color: var(--text-muted);">সময় চেয়ে বিনীত আবেদনপত্র প্রস্তুত করুন</small>
        </button>
        <button class="btn btn-outline" style="text-align: left; padding: 0.75rem;">
          ⚖️ <strong>আইনজীবীকে দেখানোর জন্য একটি ব্রিফ তৈরি করুন</strong><br>
          <small style="color: var(--text-muted);">ঘটনার সারসংক্ষেপ সাজিয়ে আইনজীবীর পরামর্শ নিন</small>
        </button>
        <button class="btn btn-secondary" style="text-align: left; padding: 0.6rem;">
          💬 <strong>আমাকে আরও বিস্তারিত বলুন</strong>
        </button>
      </div>
    </div>
  </main>
  <nav class="bottom-nav">
    <a href="#" class="nav-item active"><span>💬</span><span>সহায়িকা</span></a>
    <a href="#" class="nav-item"><span>📁</span><span>ফোল্ডার</span></a>
    <a href="#" class="nav-item"><span>➕</span><span>যোগ</span></a>
    <a href="#" class="nav-item"><span>📖</span><span>সাহায্য</span></a>
    <a href="#" class="nav-item"><span>👤</span><span>আমার</span></a>
  </nav>
</body>
</html>
""",

    # 10. Folder View after Draft with Manual Menus (U0.4)
    "10_folder_view_after_draft_manual.html": f"""<!DOCTYPE html>
<html lang="bn">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>ফোল্ডার ভিউ ও ম্যানুয়াল মেনু [নমুনা - যাচাই বাকি]</title>
  <style>{COMMON_CSS}
    .action-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(130px, 1fr));
      gap: 0.5rem;
      margin-top: 1rem;
    }}
    .action-tile {{
      background: var(--surface);
      border: 1px solid var(--border);
      padding: 0.75rem;
      border-radius: 0.5rem;
      text-align: center;
      font-size: 0.8rem;
      cursor: pointer;
    }}
  </style>
</head>
<body>
  <header>
    <div class="brand">⚖️ আইন-AI</div>
    <div style="font-size: 0.85rem;">কেস ফোল্ডার ভিউ</div>
  </header>
  <main>
    <div style="background: var(--surface); border: 1px solid var(--border); border-radius: 0.75rem; padding: 1.25rem;">
      <div style="display: flex; justify-content: space-between; align-items: flex-start;">
        <div>
          <span style="font-size: 0.75rem; background: var(--primary-light); color: var(--primary-dark); padding: 0.2rem 0.5rem; border-radius: 0.25rem; font-weight: 700;">সক্রিয় ফোল্ডার</span>
          <h2 style="font-size: 1.2rem; margin-top: 0.35rem;">ধানমন্ডি বাসাভাড়া বিরোধ (২০২৬)</h2>
          <p style="font-size: 0.85rem; color: var(--text-muted); margin-top: 0.2rem;">চ্যাট থেকে স্বয়ংক্রিয় তৈরি | ক্লায়েন্ট: তানভীর আহমেদ [নমুনা - যাচাই বাকি]</p>
        </div>
        <button class="btn btn-outline" style="font-size: 0.8rem;">⚙️ ফোল্ডার সেটিংস</button>
      </div>

      <hr style="border: 0; border-top: 1px solid var(--border); margin: 1rem 0;" />

      <h3 style="font-size: 0.9rem; margin-bottom: 0.5rem;">📁 ফোল্ডারের ফাইলসমূহ:</h3>
      <div style="background: var(--bg); border: 1px solid var(--border); border-radius: 0.5rem; padding: 0.75rem; display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
        <div>
          <div style="font-weight: 600; font-size: 0.85rem;">📄 বাড়িওয়ালাকে_দেওয়া_আবেদনপত্র.pdf</div>
          <div style="font-size: 0.75rem; color: var(--text-muted);">খসড়া তৈরি: ১০ অক্টোবর ২০২৬ | অবস্থা: পরীক্ষাধীন</div>
        </div>
        <button class="btn btn-primary" style="font-size: 0.75rem;">ডাউনলোড</button>
      </div>

      <h3 style="font-size: 0.9rem; margin-top: 1rem;">🛠️ পরবর্তী ম্যানুয়াল পদক্ষেপসমূহ:</h3>
      <div class="action-grid">
        <div class="action-tile">📄 নতুন খসড়া যোগ</div>
        <div class="action-tile">📷 নোটিশ বা রসিদ আপলোড</div>
        <div class="action-tile">⏰ সময়সীমা সেট করুন</div>
        <div class="action-tile">⚖️ আইনজীবীর জন্য ব্রিফ</div>
      </div>
    </div>
  </main>
  <nav class="bottom-nav">
    <a href="#" class="nav-item"><span>💬</span><span>সহায়িকা</span></a>
    <a href="#" class="nav-item active"><span>📁</span><span>ফোল্ডার</span></a>
    <a href="#" class="nav-item"><span>➕</span><span>যোগ</span></a>
    <a href="#" class="nav-item"><span>📖</span><span>সাহায্য</span></a>
    <a href="#" class="nav-item"><span>👤</span><span>আমার</span></a>
  </nav>
</body>
</html>
"""
}

def generate_mockups():
    print("Generating HTML mockups...")
    for filename, content in MOCKUP_TEMPLATES.items():
        filepath = MOCKUPS_DIR / filename
        filepath.write_text(content, encoding="utf-8")
        print(f"  Wrote {filepath}")

def capture_screenshots():
    print("Capturing screenshots at 360, 768, and 1280 px...")
    viewports = [
        {"name": "mobile_360", "width": 360, "height": 640},
        {"name": "tablet_768", "width": 768, "height": 1024},
        {"name": "desktop_1280", "width": 1280, "height": 800},
    ]

    records = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        for filename in MOCKUP_TEMPLATES.keys():
            html_path = MOCKUPS_DIR / filename
            base_name = filename.replace(".html", "")

            for vp in viewports:
                context = browser.new_context(viewport={"width": vp["width"], "height": vp["height"]})
                page = context.new_page()
                page.goto(f"file:///{html_path.resolve().as_posix()}")
                page.wait_for_load_state("networkidle")

                shot_filename = f"{base_name}_{vp['name']}.png"
                shot_path = SCREENSHOTS_DIR / shot_filename
                page.screenshot(path=str(shot_path), full_page=True)
                context.close()

                # Calculate hash and size
                file_bytes = shot_path.read_bytes()
                sha256 = hashlib.sha256(file_bytes).hexdigest()
                size = len(file_bytes)

                records.append({
                    "mockup_file": filename,
                    "viewport": vp["name"],
                    "width": vp["width"],
                    "height": vp["height"],
                    "screenshot_path": str(shot_path.relative_to(REPO_ROOT)).replace("\\", "/"),
                    "sha256": sha256,
                    "byte_size": size
                })
                print(f"  Captured {shot_filename} ({size:,} bytes)")

        browser.close()

    hashes_file = REPORTS_DIR / "mockup_hashes.json"
    with open(hashes_file, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)
    print(f"\nWrote machine digest: {hashes_file} ({len(records)} screenshot records)")

if __name__ == "__main__":
    generate_mockups()
    capture_screenshots()
