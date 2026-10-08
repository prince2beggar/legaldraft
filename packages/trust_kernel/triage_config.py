"""
Triage Keywords and Urgency Rules Config (SRS M11 / S7).
Lawyer-reviewed keyword triggers and triage categories.
Enforces that rule-based classifier can ONLY RAISE urgency, never lower user-selected urgency.
"""

from __future__ import annotations

import re
from typing import Any

# ---------------------------------------------------------------------------
# 1. Triage Chips Configuration (First Screen)
# ---------------------------------------------------------------------------
TRIAGE_CHIPS_CONFIG: list[dict[str, Any]] = [
    {
        "id": "arrested_detained",
        "title_bn": "কাউকে গ্রেফতার বা আটক করা হয়েছে",
        "title_en": "Someone was arrested or detained",
        "is_urgent": True,
        "category": "police_custody",
    },
    {
        "id": "violence_threat",
        "title_bn": "শারীরিক ক্ষতি বা প্রাণনাশের হুমকি রয়েছে",
        "title_en": "I or someone is being hurt or threatened",
        "is_urgent": True,
        "category": "personal_safety",
    },
    {
        "id": "child_at_risk",
        "title_bn": "একটি শিশু তাৎক্ষণিক ঝুঁকিতে রয়েছে",
        "title_en": "A child is at risk",
        "is_urgent": True,
        "category": "child_protection",
    },
    {
        "id": "lose_home_soon",
        "title_bn": "বাড়ি বা জমি থেকে জোরপূর্বক উচ্ছেদের ঝুঁকিতে",
        "title_en": "I may lose my home soon",
        "is_urgent": True,
        "category": "housing_eviction",
    },
    {
        "id": "deadline_hearing_soon",
        "title_bn": "আগামী কয়েকদিনের মধ্যে কোর্ট শুনানি বা জরুরি সময়সীমা",
        "title_en": "I have a deadline or hearing in the next few days",
        "is_urgent": True,
        "category": "imminent_deadline",
    },
    {
        "id": "none_of_these",
        "title_bn": "এর কোনোটিই নয় (সাধারণ সমস্যা)",
        "title_en": "None of these (General legal matter)",
        "is_urgent": False,
        "category": "general",
    },
]

# ---------------------------------------------------------------------------
# 2. Lawyer-Reviewed Keyword List Config
# ---------------------------------------------------------------------------
TRIAGE_KEYWORDS_CONFIG: dict[str, list[str]] = {
    "arrest_custody": [
        "arrest",
        "arrested",
        "detain",
        "detained",
        "police custody",
        "remand",
        "custody",
        "warrant",
        "arrest warrant",
        "গ্রেফতার",
        "গ্রেপ্তার",
        "আটক",
        "হেফাজত",
        "থানা হেফাজতে",
        "রিমান্ড",
        "পুলিশ আটক",
        "পরোয়ানা",
        "পরোয়ানা",
        "গ্রেপ্তারি পরোয়ানা",
        "থানায় নিয়ে গেছে",
        "তুলে নিয়ে গেছে",
        "তুলে নিয়ে গেছে",
        "হাজতে",
        "জেল হবে",
        "জেল",
    ],
    "violence_threat": [
        "threat",
        "threatened",
        "beating",
        "beaten",
        "violence",
        "assault",
        "attack",
        "kill",
        "murder",
        "life threat",
        "domestic violence",
        "hurt",
        "মারধর",
        "হুমকি",
        "মারপিট",
        "হত্যা",
        "খুন",
        "জখম",
        "শারীরিক নির্যাতন",
        "প্রাণনাশের হুমকি",
        "মারতে এসেছে",
        "মারধর করছে",
        "মারার হুমকি",
        "হামলা",
        "তাড়িয়ে দিয়েছে",
        "তাড়িয়ে দিয়েছে",
        "নিরাপত্তা প্রয়োজন",
        "নিরাপত্তা প্রয়োজন",
        "জীবন সংশয়",
        "জীবন সংশয়",
    ],
    "child_protection": [
        "child abuse",
        "minor child",
        "child custody",
        "kidnapped",
        "abduction",
        "child threat",
        "child labor",
        "শিশু নির্যাতন",
        "শিশু পাচার",
        "বাচ্চা কেড়ে নেওয়া",
        "শিশু অপহরণ",
        "বাচ্চা আটকে রেখেছে",
        "বাচ্চা আটকাইয়া",
        "শিশু অধিকার",
        "সন্তান কেড়ে নেওয়া",
        "বাচ্চার জীবন",
    ],
    "eviction_shelter": [
        "eviction",
        "evict",
        "evicted",
        "lose home",
        "homeless",
        "thrown out",
        "bulldozed",
        "land grabbing",
        "dispossessed",
        "উচ্ছেদ",
        "উচছেদ",
        "বাড়ি থেকে বের",
        "দখলচ্যুত",
        "ঘরবাড়ি ভাঙচুর",
        "ভাঙচুর",
        "ভাংচুর",
        "জমি দখল",
        "বাড়ি দখল",
        "বাড়ি দখল",
        "দখল করছে",
        "মাস্তান",
        "উচ্ছেদ নোটিশ",
        "জোরপূর্বক উচ্ছেদ",
        "তালা মেরে",
        "রাস্তায় বসে",
        "রাস্তায় বসে",
    ],
    "imminent_court": [
        "hearing tomorrow",
        "deadline tomorrow",
        "hearing in 2 days",
        "hearing in 3 days",
        "court date tomorrow",
        "urgent stay order",
        "আগামীকাল শুনানি",
        "কালকে শুনানি",
        "কাল শুনানি",
        "পরশু শুনানি",
        "কোর্ট তারিখ কাল",
        "জরুরি স্থগিতাদেশ",
        "৩ দিনের মধ্যে শুনানি",
        "২ দিনের মধ্যে শুনানি",
        "স্থগিত না করলে",
        "স্থগিতাদেশ",
        "সমন এসেছে",
    ],
}

# Compile regex patterns for fast, robust word-boundary matching
TRIAGE_KEYWORD_PATTERNS: list[tuple[re.Pattern, str]] = []
for category, keywords in TRIAGE_KEYWORDS_CONFIG.items():
    for kw in keywords:
        # Use simple substring / word-boundary pattern
        escaped = re.escape(kw)
        pattern = re.compile(rf"{escaped}", re.IGNORECASE)
        TRIAGE_KEYWORD_PATTERNS.append((pattern, category))
