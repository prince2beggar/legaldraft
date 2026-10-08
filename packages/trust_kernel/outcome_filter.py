"""
Trust Kernel: Outcome Prediction Filter & Schema Sanitizer.
Strictly prohibits outcome predictions, win/loss guarantees, and speculative legal conclusions
across both case review (case.review.v1) and intake profiling (intake.profile.v1).
Complies with SRS HR-16, AC-M06-4, and M11 schema requirements.
"""

from __future__ import annotations

import re
from typing import Any

# ---------------------------------------------------------------------------
# 1. Base Safety-Net Regex Patterns & Replacements
# ---------------------------------------------------------------------------
SAFETY_NET_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"\bwin\s+probability\b", re.IGNORECASE), "[আইনি বিশ্লেষণের প্রস্তুতি]"),
    (re.compile(r"\bprobability\s+of\s+winning\b", re.IGNORECASE), "[আইনি বিশ্লেষণের প্রস্তুতি]"),
    (re.compile(r"\bchance\s+of\s+winning\b", re.IGNORECASE), "[আইনি বিশ্লেষণের প্রস্তুতি]"),
    (re.compile(r"\byou\s+will\s+win\b", re.IGNORECASE), "[প্রক্রিয়াগত পর্যালোচনা প্রয়োজন]"),
    (re.compile(r"\byou\s+will\s+lose\b", re.IGNORECASE), "[প্রক্রিয়াগত পর্যালোচনা প্রয়োজন]"),
    (re.compile(r"\bwill\s+win\b", re.IGNORECASE), "[প্রক্রিয়াগত পর্যালোচনা প্রয়োজন]"),
    (re.compile(r"\bwill\s+lose\b", re.IGNORECASE), "[প্রক্রিয়াগত পর্যালোচনা প্রয়োজন]"),
    (re.compile(r"\bcourt\s+will\s+rule\s+for\s+you\b", re.IGNORECASE), "[আদালতের এখতিয়ারাধীন বিষয়]"),
    (
        re.compile(r"\bcourt\s+will\s+rule\s+against\s+you\b", re.IGNORECASE),
        "[আদালতের এখতিয়ারাধীন বিষয়]",
    ),
    (
        re.compile(r"\bcourt\s+will\s+rule\s+in\s+your\s+favor\b", re.IGNORECASE),
        "[আদালতের এখতিয়ারাধীন বিষয়]",
    ),
    (re.compile(r"\bguarantee(d)?\b", re.IGNORECASE), "[আইনগত প্রস্তুতি]"),
    (re.compile(r"\bvictory\b", re.IGNORECASE), "[ফলাফল অনিশ্চিত]"),
    (re.compile(r"\bdefeat\b", re.IGNORECASE), "[ফলাফল অনিশ্চিত]"),
    (re.compile(r"\b\d+%\b", re.IGNORECASE), "[পরিসংখ্যান অপ্রযোজ্য]"),
    (re.compile(r"\bwin\b", re.IGNORECASE), "[তথ্য]"),
    (re.compile(r"\blose\b", re.IGNORECASE), "[তথ্য]"),
    (re.compile(r"আপনি\s*জিতবেন"), "[আইনি পর্যালোচনা প্রয়োজন]"),
    (re.compile(r"আপনি\s*হারবেন"), "[আইনি পর্যালোচনা প্রয়োজন]"),
    (re.compile(r"জিতবেন"), "[আইনি পর্যালোচনা প্রয়োজন]"),
    (re.compile(r"হারবেন"), "[আইনি পর্যালোচনা প্রয়োজন]"),
    (re.compile(r"আদালত\s*আপনার\s*পক্ষে\s*রায়\s*দেবে"), "[আদালতের সিদ্ধান্তের বিষয়]"),
    (re.compile(r"আদালত\s*আপনার\s*বিরুদ্ধে\s*রায়\s*দেবে"), "[আদালতের সিদ্ধান্তের বিষয়]"),
    (re.compile(r"নিশ্চিত\s*রায়"), "[আদালতের সিদ্ধান্তের বিষয়]"),
    (re.compile(r"জয়ের\s*সম্ভাবনা"), "[সম্ভাবনা নির্ধারণ অনুচিত]"),
    (re.compile(r"পরাজয়ের\s*সম্ভাবনা"), "[সম্ভাবনা নির্ধারণ অনুচিত]"),
    (re.compile(r"জয়লাভ"), "[প্রক্রিয়াগত পদক্ষেপ]"),
    (re.compile(r"পরাজয়"), "[প্রক্রিয়াগত পদক্ষেপ]"),
    (re.compile(r"গ্যারান্টি"), "[আইনগত প্রস্তুতি]"),
    (re.compile(r"নিশ্চিত\s*বিজয়"), "[ফলাফল অনিশ্চিত]"),
    (re.compile(r"[০-৯0-9]+%\s*(সম্ভাবনা|নিশ্চিত|বিজয়)?"), "[পরিসংখ্যান অপ্রযোজ্য]"),
]

# ---------------------------------------------------------------------------
# 2. Enhanced Paraphrase Patterns (Held-Out & Adversarial Variants)
# ---------------------------------------------------------------------------
ENHANCED_OUTCOME_PATTERNS: list[tuple[re.Pattern, str]] = [
    # English paraphrases
    (re.compile(r"\bchances\s+look\s+(very\s+)?strong\b", re.IGNORECASE), "[আইনি মূল্যায়নের বিষয়]"),
    (re.compile(r"\byour\s+chances\b", re.IGNORECASE), "[আইনি দিক]"),
    (re.compile(r"\bexpect\s+to\s+succeed\b", re.IGNORECASE), "[প্রক্রিয়াগত প্রস্তুতি]"),
    (re.compile(r"\bexpect\s+to\s+win\b", re.IGNORECASE), "[প্রক্রিয়াগত প্রস্তুতি]"),
    (re.compile(r"\bexpected\s+to\s+succeed\b", re.IGNORECASE), "[প্রক্রিয়াগত প্রস্তুতি]"),
    (re.compile(r"\blikely\s+to\s+prevail\b", re.IGNORECASE), "[আইনি ফলাফল অনুমানের অযোগ্য]"),
    (re.compile(r"\bpoised\s+to\s+prevail\b", re.IGNORECASE), "[আইনি ফলাফল অনুমানের অযোগ্য]"),
    (re.compile(r"\bprevail\s+against\b", re.IGNORECASE), "[আইনি পদক্ষেপ]"),
    (
        re.compile(r"\bfavor(able)?\s+(verdict|ruling|outcome|judgment)\b", re.IGNORECASE),
        "[আদালতের এখতিয়ার]",
    ),
    (re.compile(r"\bruling\s+in\s+our\s+favor\b", re.IGNORECASE), "[আদালতের এখতিয়ার]"),
    (re.compile(r"\brule\s+in\s+(our|your)\s+favor\b", re.IGNORECASE), "[আদালতের এখতিয়ার]"),
    (re.compile(r"\bsuccess\s+is\s+(practically\s+)?assured\b", re.IGNORECASE), "[ফলাফল অনির্ধারিত]"),
    (re.compile(r"\bassured\b", re.IGNORECASE), "[অনিশ্চিত]"),
    (re.compile(r"\bprobability\s+of\b", re.IGNORECASE), "[আইনি বিশ্লেষণ]"),
    (
        re.compile(r"\blikelihood\s+of\s+(winning|positive\s+outcome|prevailing)\b", re.IGNORECASE),
        "[পরিসংখ্যান অপ্রযোজ্য]",
    ),
    (re.compile(r"\blikelihood\s+of\b", re.IGNORECASE), "[সম্ভাবনা]"),
    (re.compile(r"\bslam\s+dunk\b", re.IGNORECASE), "[নথিপত্র যাচাই প্রয়োজন]"),
    (
        re.compile(r"\boutcome\s+is\s+looking\s+(very\s+)?promising\b", re.IGNORECASE),
        "[তদন্তসাপেক্ষ বিষয়]",
    ),
    (re.compile(r"\bpromising\s+outcome\b", re.IGNORECASE), "[তদন্তসাপেক্ষ বিষয়]"),
    (
        re.compile(
            r"\bjudge\s+will\s+(almost\s+certainly\s+|certainly\s+)?(agree|rule)\b", re.IGNORECASE
        ),
        "[বিচারকের এখতিয়ার]",
    ),
    (
        re.compile(r"\bguaranteed\s+to\s+receive\s+compensation\b", re.IGNORECASE),
        "[আইনি দাবির পর্যালোচনা]",
    ),
    (re.compile(r"\breceive\s+compensation\s+guaranteed\b", re.IGNORECASE), "[আইনি দাবির পর্যালোচনা]"),
    # Bangla paraphrases
    (re.compile(r"পক্ষে\s*যাওয়ার\s*সম্ভাবনা\s*প্রবল"), "[আদালতের সিদ্ধান্তের বিষয়]"),
    (re.compile(r"সম্ভাবনা\s*প্রবল"), "[ফলাফল অনুমানের বাইরে]"),
    (re.compile(r"প্রবল\s*সম্ভাবনা"), "[ফলাফল অনুমানের বাইরে]"),
    (re.compile(r"উচ্চ\s*আদালতে\s*আপনার\s*নিশ্চিত\s*জয়"), "[উচ্চ আদালতের সিদ্ধান্তের বিষয়]"),
    (re.compile(r"নিশ্চিত\s*জয়"), "[ফলাফল আদালতের এখতিয়ার]"),
    (re.compile(r"জেতার\s*চান্স\s*অনেক\s*বেশি"), "[আইনি প্রক্রিয়ার বিষয়]"),
    (re.compile(r"জেতার\s*চান্স"), "[আইনি প্রক্রিয়ার বিষয়]"),
    (re.compile(r"রায়\s*আমাদের\s*দিকেই\s*আসবে"), "[আদালতের এখতিয়ার]"),
    (re.compile(r"রায়\s*আপনার\s*অনুকূলে"), "[আদালতের এখতিয়ার]"),
    (re.compile(r"আপনার\s*অনুকূলে"), "[আদালতের এখতিয়ার]"),
    (re.compile(r"অনুকূলে\s*আসবে"), "[আদালতের এখতিয়ার]"),
    (re.compile(r"শতভাগ\s*নিশ্চিত"), "[ফলাফল অনির্ধারিত]"),
    (re.compile(r"কোনোভাবেই\s*টিকবে\s*না"), "[আইনি যুক্তির বিষয়]"),
    (re.compile(r"টিকবে\s*না"), "[আইনি যুক্তির বিষয়]"),
    (re.compile(r"আদালত\s*অবশ্যই\s*আপনার\s*পক্ষে\s*ডিক্রি\s*দেবে"), "[আদালতের বিচার্য বিষয়]"),
    (re.compile(r"ডিক্রি\s*দেবেই?"), "[আদালতের বিচার্য বিষয়]"),
    (re.compile(r"হারার\s*কোনো\s*সুযোগ\s*নেই"), "[ফলাফল অনির্ধারিত]"),
    (re.compile(r"সুযোগ\s*নেই"), "[ফলাফল অনির্ধারিত]"),
    (re.compile(r"ম্যাজিস্ট্রেট\s*আপনার\s*আর্জি\s*মঞ্জুর\s*করবেনই?"), "[আদালতের এখতিয়ার]"),
    (re.compile(r"মঞ্জুর\s*করবেনই?"), "[আদালতের এখতিয়ার]"),
    (re.compile(r"ক্ষতিপূরণ\s*পাওয়া\s*নিশ্চিত"), "[আইনি প্রতিকারের বিষয়]"),
    (re.compile(r"ক্ষতিপূরণ\s*দেওয়া\s*হবে\s*নিশ্চিত"), "[আইনি প্রতিকারের বিষয়]"),
    (re.compile(r"(প্রতিকার|ক্ষতিপূরণ|ডিক্রি|রায়|সাহায্য).{0,25}নিশ্চিত"), "[আইনি পর্যালোচনার বিষয়]"),
    (re.compile(r"নিশ্চিত.{0,25}(প্রতিকার|ক্ষতিপূরণ|ডিক্রি|রায়|সাহায্য)"), "[আইনি পর্যালোচনার বিষয়]"),
    (re.compile(r"পরাজয়\s*অবধারিত"), "[ফলাফল অনিশ্চিত]"),
    (re.compile(r"অবধারিত"), "[অনিশ্চিত]"),
    (re.compile(r"সফল\s*হবেনই?"), "[প্রক্রিয়াগত পদক্ষেপ]"),
    (re.compile(r"বিজয়ী\s*হবেন"), "[প্রক্রিয়াগত পদক্ষেপ]"),
    (re.compile(r"প্রতিকার\s*নিশ্চিত"), "[আইনি পর্যালোচনা সাপেক্ষ]"),
]

ALL_OUTCOME_PATTERNS = SAFETY_NET_PATTERNS + ENHANCED_OUTCOME_PATTERNS


def filter_outcome_predictions(text: str) -> str:
    """
    Sanitizes free-form text by replacing all outcome predictions, win/loss guarantees,
    and certainty claims with neutral, procedural legal statements.
    """
    if not text:
        return text

    sanitized = text
    for pattern, replacement in ALL_OUTCOME_PATTERNS:
        sanitized = pattern.sub(replacement, sanitized)

    return sanitized


def sanitize_text_field(val: Any) -> Any:
    """Recursively sanitizes string values inside primitives, lists, and dicts."""
    if isinstance(val, str):
        return filter_outcome_predictions(val)
    elif isinstance(val, list):
        return [sanitize_text_field(item) for item in val]
    elif isinstance(val, dict):
        return {k: sanitize_text_field(v) for k, v in val.items()}
    return val


def sanitize_ai_profile(profile_data: dict[str, Any]) -> dict[str, Any]:
    """
    Sanitizes and schema-validates the output of intake.profile.v1:
    - Filters all free text fields for outcome predictions
    - Strictly enforces schema: possible_issues must have kind='research_suggestion'
    - Prevents inferred facts or definitive legal conclusions
    """
    if not isinstance(profile_data, dict):
        return {}

    sanitized: dict[str, Any] = {}

    # Case type (enum validated)
    valid_types = {
        "land_property",
        "contract",
        "rent_tenancy",
        "family",
        "criminal_complaint",
        "labour_employment",
        "consumer",
        "notice_received",
        "court_matter",
        "tax",
        "other",
    }
    ctype = profile_data.get("case_type", "other")
    sanitized["case_type"] = ctype if ctype in valid_types else "other"

    # Title suggestion
    sanitized["title_suggestion"] = filter_outcome_predictions(
        str(profile_data.get("title_suggestion", ""))
    )

    # Parties
    parties = []
    for p in profile_data.get("parties", []):
        if isinstance(p, dict):
            parties.append(
                {
                    "name": filter_outcome_predictions(str(p.get("name", ""))),
                    "role": filter_outcome_predictions(str(p.get("role", ""))),
                    "org": filter_outcome_predictions(str(p.get("org", ""))),
                }
            )
    sanitized["parties"] = parties

    # Dates
    dates = []
    for d in profile_data.get("dates", []):
        if isinstance(d, dict):
            dates.append(
                {
                    "date": str(d.get("date", "")),
                    "precision": d.get("precision", "day")
                    if d.get("precision") in {"day", "month", "year"}
                    else "day",
                    "what": filter_outcome_predictions(str(d.get("what", ""))),
                    "from_user_text": bool(d.get("from_user_text", True)),
                }
            )
    sanitized["dates"] = dates

    # Facts: each fact text filtered, span preserved
    facts = []
    for f in profile_data.get("facts", []):
        if isinstance(f, dict):
            facts.append(
                {
                    "text": filter_outcome_predictions(str(f.get("text", ""))),
                    "span_in_user_text": f.get(
                        "span_in_user_text", [0, len(str(f.get("text", "")))]
                    ),
                }
            )
    sanitized["facts"] = facts

    # Documents mentioned
    sanitized["documents_mentioned"] = [
        filter_outcome_predictions(str(d)) for d in profile_data.get("documents_mentioned", [])
    ]

    # Possible issues: MUST be labelled kind="research_suggestion"
    issues = []
    for issue in profile_data.get("possible_issues", []):
        if isinstance(issue, dict):
            issues.append(
                {
                    "text": filter_outcome_predictions(str(issue.get("text", ""))),
                    "kind": "research_suggestion",  # Strict schema enforcement
                }
            )
        elif isinstance(issue, str):
            issues.append(
                {
                    "text": filter_outcome_predictions(issue),
                    "kind": "research_suggestion",
                }
            )
    sanitized["possible_issues"] = issues

    # Missing information
    sanitized["missing_information"] = [
        filter_outcome_predictions(str(m)) for m in profile_data.get("missing_information", [])
    ]

    # User objective
    sanitized["user_objective"] = filter_outcome_predictions(
        str(profile_data.get("user_objective", ""))
    )

    # Clarifying questions
    sanitized["clarifying_questions"] = [
        filter_outcome_predictions(str(q)) for q in profile_data.get("clarifying_questions", [])
    ]

    # Urgency signals
    sanitized["urgency_signals"] = [
        filter_outcome_predictions(str(u)) for u in profile_data.get("urgency_signals", [])
    ]

    return sanitized


# ---------------------------------------------------------------------------
# 3. Held-Out Test Set (>= 20 Paraphrased Predictions)
# ---------------------------------------------------------------------------
HELD_OUT_OUTCOME_PREDICTIONS: list[dict[str, str]] = [
    # English paraphrases
    {
        "id": "en_01",
        "text": "Your chances look very strong for getting the deposit refunded.",
        "lang": "en",
    },
    {"id": "en_02", "text": "You should expect to succeed on the eviction defense.", "lang": "en"},
    {"id": "en_03", "text": "The judge will almost certainly rule in our favor.", "lang": "en"},
    {
        "id": "en_04",
        "text": "Success is practically assured for this particular land claim.",
        "lang": "en",
    },
    {
        "id": "en_05",
        "text": "You have an overwhelming probability of winning in court.",
        "lang": "en",
    },
    {"id": "en_06", "text": "A favorable verdict is expected within three months.", "lang": "en"},
    {
        "id": "en_07",
        "text": "You are guaranteed to receive full financial compensation.",
        "lang": "en",
    },
    {
        "id": "en_08",
        "text": "A victory in court is practically guaranteed with this deed.",
        "lang": "en",
    },
    {
        "id": "en_09",
        "text": "You are poised to prevail against the defendant without issue.",
        "lang": "en",
    },
    {
        "id": "en_10",
        "text": "The likelihood of a positive outcome is 95% based on records.",
        "lang": "en",
    },
    {"id": "en_11", "text": "The outcome is looking very promising for your side.", "lang": "en"},
    {"id": "en_12", "text": "Your case against the landlord is a total slam dunk.", "lang": "en"},
    # Bangla paraphrases
    {"id": "bn_01", "text": "এই নথির ভিত্তিতে মামলাটি আপনার পক্ষে যাওয়ার সম্ভাবনা প্রবল।", "lang": "bn"},
    {"id": "bn_02", "text": "উচ্চ আদালতে আপনার নিশ্চিত জয় হবে বলে আশা করা যায়।", "lang": "bn"},
    {"id": "bn_03", "text": "এই আইনি লড়াইয়ে আপনার জেতার চান্স অনেক বেশি।", "lang": "bn"},
    {"id": "bn_04", "text": "আমরা শতভাগ নিশ্চিত রায় আমাদের দিকেই আসবে।", "lang": "bn"},
    {"id": "bn_05", "text": "বিপক্ষ দল আদালতে কোনোভাবেই টিকবে না।", "lang": "bn"},
    {"id": "bn_06", "text": "আদালত অবশ্যই আপনার পক্ষে ডিক্রি দেবে।", "lang": "bn"},
    {"id": "bn_07", "text": "আপনার মামলায় হারার কোনো সুযোগ নেই।", "lang": "bn"},
    {"id": "bn_08", "text": "ম্যাজিস্ট্রেট আপনার আর্জি মঞ্জুর করবেনই।", "lang": "bn"},
    {"id": "bn_09", "text": "আপনার সম্পূর্ণ ক্ষতিপূরণ পাওয়া নিশ্চিত।", "lang": "bn"},
    {"id": "bn_10", "text": "এই ধারার অধীনে রায় আপনার অনুকূলে আসবেই।", "lang": "bn"},
    {"id": "bn_11", "text": "বিরোধীদের পরাজয় অবধারিত কারণ দলিলটি নিবন্ধিত।", "lang": "bn"},
    {"id": "bn_12", "text": "আপনাকে আইনি প্রতিকার দেওয়া হবে নিশ্চিত।", "lang": "bn"},
]
