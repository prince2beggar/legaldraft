"""
AI Gateway & LLM Orchestration Layer (SRS Section 4.4, 8.5, 9.3 S3).
Provides secure, governed LLM access with:
1. Pre-provider PII redaction and post-response un-redaction.
2. Model routing with graceful fallback.
3. Strict JSON-schema output validation.
4. Prompt registry with versioning.
5. Cost guard / token quotas.
6. Provider slots: FakeLLMProvider (test/offline) and RealLlmAdapterSlot (disabled by default).
7. Persistence in ai_outputs and claim_links tables.
"""

import hashlib
import json
import os
import re
import uuid
from typing import Any

import jsonschema

from packages.trust_kernel.audit import audit_service
from packages.trust_kernel.db import DatabaseManager, db_manager

BN_DIGITS = "০১২৩৪৫৬৭৮৯"
_EN_TO_BN = str.maketrans("0123456789", BN_DIGITS)
_BN_TO_EN = str.maketrans(BN_DIGITS, "0123456789")


def to_bangla_digits(val: Any) -> str:
    return str(val).translate(_EN_TO_BN)


def to_ascii_digits(val: Any) -> str:
    return str(val).translate(_BN_TO_EN)


class CostLimitExceededError(ValueError):
    """Raised when token quota or cost limit is exceeded."""

    pass


class SchemaValidationError(ValueError):
    """Raised when model output fails JSON schema validation."""

    pass


class PIIRedactor:
    """Detects and redacts sensitive PII (phones, NID, emails) with reversible tokens."""

    PHONE_REGEX = re.compile(r"(?:\+8801|01)[3-9]\d{8}\b")
    NID_REGEX = re.compile(r"\b(?:\d{10}|\d{13}|\d{17})\b")
    EMAIL_REGEX = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")

    def redact(self, text: str) -> tuple[str, dict[str, str]]:
        redactions: dict[str, str] = {}
        redacted = text

        # 1. Redact Emails
        for idx, match in enumerate(self.EMAIL_REGEX.finditer(text), 1):
            val = match.group(0)
            token = f"<PII_EMAIL_{idx}>"
            redactions[token] = val
            redacted = redacted.replace(val, token)

        # 2. Redact Phone numbers
        for idx, match in enumerate(self.PHONE_REGEX.finditer(text), 1):
            val = match.group(0)
            token = f"<PII_PHONE_{idx}>"
            redactions[token] = val
            redacted = redacted.replace(val, token)

        # 3. Redact NID numbers
        for idx, match in enumerate(self.NID_REGEX.finditer(text), 1):
            val = match.group(0)
            token = f"<PII_NID_{idx}>"
            redactions[token] = val
            redacted = redacted.replace(val, token)

        return redacted, redactions

    def unredact(self, text: str, redactions: dict[str, str]) -> str:
        restored = text
        for token, original_val in redactions.items():
            restored = restored.replace(token, original_val)
        return restored


class FakeLLMProvider:
    """Mock LLM provider for deterministic testing and offline local execution."""

    def __init__(self, name: str = "fake-llm-primary"):
        self.name = name
        self.custom_responses: dict[str, str] = {}

    def set_mock_response(self, match_key: str, response_json: str):
        self.custom_responses[match_key] = response_json

    def clear_mock_responses(self):
        self.custom_responses.clear()

    def generate(
        self, system_prompt: str, user_prompt: str, schema: dict[str, Any] | None = None
    ) -> tuple[str, int]:
        # Estimate token cost: 1 token ~ 4 chars
        cost_tokens = len(system_prompt + user_prompt) // 4 + 50

        # Check custom mock overrides first
        for key, resp in self.custom_responses.items():
            if key in user_prompt or key in system_prompt:
                return resp, cost_tokens

        # Check if this is the notice explanation task
        if schema and "summary_one_line" in schema.get("properties", {}):
            return self._generate_notice_explanation(user_prompt), cost_tokens

        # Check if this is the simpler explanation task
        if schema and "simpler_summary" in schema.get("properties", {}):
            return self._generate_simpler_explanation(user_prompt), cost_tokens

        # Check if this is the intake profile task (M11)
        if schema and "title_suggestion" in schema.get("properties", {}):
            return self._generate_intake_profile(user_prompt), cost_tokens

        # Check if this is the drafting helper task (M05)
        if schema and "rephrased_question" in schema.get("properties", {}):
            return self._generate_draft_helper(user_prompt), cost_tokens

        # Check if this is the case review task
        if schema and "possible_issues" in schema.get("properties", {}):
            return self._generate_case_review(user_prompt), cost_tokens

        # If schema requires specific keys, generate compliant dummy response
        if schema and "properties" in schema:
            response_dict: dict[str, Any] = {}
            for prop, details in schema["properties"].items():
                p_type = details.get("type", "string")
                if p_type == "string":
                    response_dict[prop] = f"[নমুনা বিশ্লেষণ] {prop} এর ফলাফল"
                elif p_type == "number" or p_type == "integer":
                    response_dict[prop] = 1
                elif p_type == "boolean":
                    response_dict[prop] = True
                elif p_type == "array":
                    response_dict[prop] = ["[নমুনা এন্ট্রি]"]
                else:
                    response_dict[prop] = {}
            return json.dumps(response_dict, ensure_ascii=False), cost_tokens

        # Generic compliant response
        generic = {
            "summary": "[নমুনা আইনি পরামর্শ] উপস্থাপিত তথ্যের ভিত্তিতে আইনি বিশ্লেষণ।",
            "statutory_basis": "বাড়িভাড়া নিয়ন্ত্রণ আইন ১৯৯১",
            "section": "ধারা ৭",
            "confidence": 0.95,
        }
        return json.dumps(generic, ensure_ascii=False), cost_tokens

    def _generate_notice_explanation(self, user_prompt: str) -> str:
        prompt_lower = user_prompt.lower()

        # Check edge cases
        is_blurry = (
            "blurry" in prompt_lower or "অস্পষ্ট" in prompt_lower or len(user_prompt.strip()) < 30
        )
        is_non_notice = (
            "non_notice" in prompt_lower
            or "চালান" in user_prompt
            or (
                "দলিল" in user_prompt
                and "নোটিশ" not in user_prompt
                and "notice" not in prompt_lower
            )
        )
        has_handwriting = "handwriting" in prompt_lower or "হাতের লেখা" in user_prompt
        multiple_notices = (
            "multiple_notices" in prompt_lower
            or "একাধিক নোটিশ" in user_prompt
            or "দুটি নোটিশ" in user_prompt
            or "২টি নোটিশ" in user_prompt
            or "প্রথম নোটিশ" in user_prompt
            or "multiple notices" in prompt_lower
            or "two notices" in prompt_lower
        )

        certainty = (
            "not_sure"
            if is_blurry
            else ("check" if has_handwriting or multiple_notices else "clear")
        )

        # Determine consequences
        has_explicit_consequence = (
            "মামলা" in user_prompt
            or "case" in prompt_lower
            or "আদালত" in user_prompt
            or "ডিজঅনার" in user_prompt
            or "জরিমানা" in user_prompt
            or "demolition" in prompt_lower
            or "উচ্ছেদ" in user_prompt
            or "বরখাস্ত" in user_prompt
            or "আইনি ব্যবস্থা" in user_prompt
            or "legal proceedings" in prompt_lower
        )

        # Dates extraction
        important_dates = []
        rel_match = (
            re.search(r"(\d+|[০-৯]+)\s*(?:কর্ম)?দিনের?\s*মধ্যে", user_prompt)
            or re.search(r"আগামী\s*(\d+|[০-৯]+)\s*দিনের", user_prompt)
            or re.search(r"within\s*(\d+)\s*days", user_prompt, re.IGNORECASE)
            or re.search(r"(\d+|[০-৯]+)\s*দিন\s*সময়", user_prompt)
            or re.search(r"(\d+|[০-৯]+)\s*দিন\s*পর", user_prompt)
        )
        if rel_match:
            rel_raw = rel_match.group(1)
            rel_val = int(to_ascii_digits(rel_raw))
            rel_bn_val = to_bangla_digits(rel_val)
            matched_span = rel_match.group(0)
            important_dates.append(
                {
                    "label": "নোটিশে লেখা সময়সীমা",
                    "stated_text": f"নোটিশ প্রাপ্তির {rel_bn_val} দিনের মধ্যে"
                    if "মধ্যে" in matched_span
                    else f"নোটিশ প্রাপ্তির {rel_bn_val} দিন",
                    "stated_date": None,
                    "relative": {
                        "period_value": rel_val,
                        "period_unit": "days",
                        "from_event": "receipt",
                        "from_text": f"নোটিশ প্রাপ্তির {rel_bn_val} দিন",
                    },
                    "claims": [
                        {"text": matched_span, "span_ref": {"page": 1, "start": 0, "end": 60}}
                    ],
                }
            )
        elif (
            "১৫ অক্টোবর ২০২৬" in user_prompt
            or "2026-10-15" in user_prompt
            or "২০২৬-১০-১৫" in user_prompt
        ):
            stated_txt = (
                "১৫ অক্টোবর ২০২৬"
                if ("১৫ অক্টোবর ২০২৬" in user_prompt or "2026-10-15" in user_prompt)
                else "২০২৬-১০-১৫"
            )
            important_dates.append(
                {
                    "label": "হাজিরার তারিখ",
                    "stated_text": stated_txt,
                    "stated_date": "2026-10-15",
                    "relative": None,
                    "claims": [
                        {"text": stated_txt, "span_ref": {"page": 1, "start": 0, "end": 40}}
                    ],
                }
            )
        else:
            important_dates.append(
                {
                    "label": "নোটিশে উল্লেখিত তারিখ",
                    "stated_text": "নোটিশে সুনির্দিষ্ট কোনো সময়সীমা বা তারিখ উল্লেখ নেই",
                    "stated_date": None,
                    "relative": None,
                    "claims": [],
                }
            )

        if has_explicit_consequence:
            if_ignored = {
                "text": "নোটিশ অনুযায়ী নির্ধারিত সময়ের মধ্যে পদক্ষেপ না নিলে আপনার বিরুদ্ধে আদালতে মামলা বা আইনি কার্যধারা শুরু করা হতে পারে।",
                "claims": [
                    {"text": "মামলা দায়ের করা হবে", "span_ref": {"page": 1, "start": 0, "end": 80}}
                ],
                "stated_in_notice": True,
                "not_stated": False,
            }
        else:
            if_ignored = {
                "text": "নথিতে এমন কিছু উল্লেখ নেই। একজন আইনজীবীর পরামর্শ নিন।",
                "claims": [],
                "stated_in_notice": False,
                "not_stated": True,
            }

        resp = {
            "language": "bn",
            "certainty": certainty,
            "is_notice": not is_non_notice,
            "notice_category": "demand_notice",
            "has_handwriting": has_handwriting,
            "multiple_notices_detected": multiple_notices,
            "summary_one_line": "[নমুনা] আইনি দাবি নোটিশ: নির্দিষ্ট সময়ের মধ্যে দাবিকৃত পদক্ষেপ গ্রহণ বা জবাব দাখিল করার নির্দেশ।",
            "summary_chips": [
                {"label": "[আইনি নোটিশ]", "section_ref": "আইনি নোটিশ", "passage_id": None}
            ],
            "what_is_this": {
                "text": "এটি একটি আনুষ্ঠানিক আইনি নোটিশ (Legal Notice)।",
                "claims": [{"text": "আইনি নোটিশ", "span_ref": {"page": 1, "start": 0, "end": 30}}],
            },
            "sender": {
                "text": "নোটিশ প্রেরণকারী পক্ষ বা তাদের নিযুক্ত আইনজীবী।",
                "claims": [{"text": "প্রেরক পক্ষ", "span_ref": {"page": 1, "start": 0, "end": 30}}],
            },
            "why_received": {
                "text": "প্রেরক পক্ষের সাথে কোনো চুক্তি, পাওনা বা আইনি বিরোধের পরিপ্রেক্ষিতে এই নোটিশটি পাঠানো হয়েছে।",
                "claims": [
                    {"text": "বিরোধের পরিপ্রেক্ষিতে", "span_ref": {"page": 1, "start": 0, "end": 40}}
                ],
            },
            "what_it_says": [
                {
                    "text": "প্রেরকের দাবিকৃত দাবি অবিলম্বে বিবেচনা ও সমাধান করার জন্য বলা হয়েছে।",
                    "claims": [
                        {"text": "দাবি বিবেচনা", "span_ref": {"page": 1, "start": 0, "end": 30}}
                    ],
                },
                {
                    "text": "নির্ধারিত সময়সীমার মধ্যে সন্তোষজনক জবাব প্রদান করতে বলা হয়েছে।",
                    "claims": [
                        {"text": "জবাব প্রদান", "span_ref": {"page": 1, "start": 0, "end": 30}}
                    ],
                },
            ],
            "action_required": [
                {
                    "text": "নোটিশের দাবির সত্যতা যাচাই করে একজন আইনজীবীর মাধ্যমে আনুষ্ঠানিক জবাব দিন।",
                    "claims": [{"text": "জবাব দিন", "span_ref": {"page": 1, "start": 0, "end": 30}}],
                    "task_suggestion": {"title": "আইনজীবীর মাধ্যমে নোটিশের জবাব দাখিল করুন"},
                },
                {
                    "text": "নোটিশে দাবিকৃত প্রাসঙ্গিক সকল কাগজপত্র ও প্রমাণাদি সংগ্রহ করুন।",
                    "claims": [
                        {"text": "কাগজপত্র সংগ্রহ", "span_ref": {"page": 1, "start": 0, "end": 30}}
                    ],
                    "task_suggestion": {"title": "প্রাসঙ্গিক প্রমাণাদি ও রসিদ সংগ্রহ করুন"},
                },
            ],
            "important_dates": important_dates,
            "documents_needed": [
                {
                    "text": "প্রেরক পক্ষের সাথে বিগত দিনের চুক্তিপত্র বা লেনদেনের রসিদ।",
                    "claims": [
                        {"text": "লেনদেনের রসিদ", "span_ref": {"page": 1, "start": 0, "end": 30}}
                    ],
                },
                {
                    "text": "নোটিশ পৌঁছানোর খাম ও প্রাপ্তি স্বীকারপত্র (A/D কার্ড)।",
                    "claims": [
                        {"text": "প্রাপ্তি স্বীকারপত্র", "span_ref": {"page": 1, "start": 0, "end": 30}}
                    ],
                },
            ],
            "if_ignored": if_ignored,
            "questions_for_lawyer": [
                "এই নোটিশের কি নির্দিষ্ট মেয়াদের মধ্যে আনুষ্ঠানিক লিখিত জবাব দেওয়া বাধ্যতামূলক?",
                "প্রেরকের দাবির আইনি ভিত্তি কতটুকু শক্তিশালী?",
                "আমার কি এই পরিস্থিতিতে আগাম কোনো আইনি পদক্ষেপ বা জিডি করা উচিত?",
            ],
            "not_found": [],
            "cited_laws_in_notice": [],
        }
        return json.dumps(resp, ensure_ascii=False)

    def _generate_simpler_explanation(self, user_prompt: str) -> str:
        resp = {
            "language": "bn",
            "simpler_summary": "[সহজ ভাষায়] আপনাকে একটি আইনি নোটিশ দেওয়া হয়েছে। নির্ধারিত সময়ের মধ্যে এর জবাব দিতে হবে।",
            "simpler_what_it_says": [
                "অন্য পক্ষ আপনার কাছে পাওনা বা কোনো দাবি করছেন।",
                "নির্দিষ্ট সময়ের মধ্যে আপনি টাকা পরিশোধ বা লিখিত জবাব না দিলে তারা আদালতে যেতে পারেন।",
            ],
            "simpler_actions": [
                "নোটিশের খাম এবং প্রাপ্তির তারিখ লিখে রাখুন।",
                "দেরি না করে দ্রুত একজন আইনজীবীর পরামর্শ নিন এবং জবাব দিন।",
            ],
            "simpler_warning": "নোটিশটি অবহেলা করবেন না। সময় পার হয়ে গেলে পরবর্তীতে আপনার অধিকার রক্ষা করা কঠিন হতে পারে।",
        }
        return json.dumps(resp, ensure_ascii=False)

    def _generate_case_review(self, user_prompt: str) -> str:
        # Strictly ensure zero outcome statements, probabilities, or win/lose claims (AC-M06-5, Red-team)
        resp = {
            "possible_issues": [
                "নোটিশের দাবিকৃত অর্থ ও ব্যাংক হিসাবের বিবরণের মধ্যে মিল যাচাই করা প্রয়োজন।",
                "নোটিশ প্রাপ্তির নির্দিষ্ট তারিখ ও আইনি জবাবের সময়সীমার বাধ্যবাধকতা।",
            ],
            "missing_information": [
                "ব্যাংকের চেক ডিজঅনার মেমোর মূল কপি ও তারিখ।",
                "নোটিশ গ্রহণের আনুষ্ঠানিক পোস্টাল রসিদ বা কুরিয়ার স্লিপ।",
            ],
            "required_documents": [
                "মূল ব্যাংক চেক এবং ব্যাংক রিটার্ন মেমো।",
                "সংশ্লিষ্ট ব্যবসায়িক চুক্তি, ইনভয়েস বা লেনদেনের রসিদ।",
            ],
            "possible_processes": [
                {
                    "process_name": "এনআই অ্যাক্ট ১৩৮ ধারার আনুষ্ঠানিক জবাব দাখিল",
                    "statute_ref": "নেগোশিয়েবল ইনস্ট্রুমেন্টস অ্যাক্ট ১৮৮১, ধারা ১৩৮",
                    "status": "APPROVED",
                },
                {
                    "process_name": "আইনি বিরোধ নিষ্পত্তিকল্পে আপস-মীমাংসার উদ্যোগ",
                    "statute_ref": "সালিশ আইন ২০০১",
                    "status": "APPROVED",
                },
            ],
            "questions_for_lawyer": [
                "নোটিশের মেয়াদ উত্তীর্ণ হওয়ার পূর্বে জবাব পাঠানো কি বাধ্যতামূলক?",
                "চেক ডিজঅনারের বিপরীতে কি দেওয়ানি আদালতে কোনো প্রতিকার চাওয়া যায়?",
            ],
            "options_to_discuss": [
                "অভিজ্ঞ আইনজীবীর মাধ্যমে আনুষ্ঠানিক লিখিত জবাব দাখিল করা।",
                "ব্যাংকের নথিপত্র ও হিসাব বিবরণী সংগ্রহ করে আইনি অবস্থান প্রস্তুত করা।",
            ],
            "ai_disclaimer": "AI বিশ্লেষণ, আইনি পরামর্শ নয়",
        }
        return json.dumps(resp, ensure_ascii=False)

    def _generate_intake_profile(self, user_prompt: str) -> str:
        prompt_lower = user_prompt.lower()
        if "জমি" in user_prompt or "land" in prompt_lower or "দখল" in user_prompt:
            ctype = "land_property"
            title = "জমির মালিকানা ও স্বত্ব সংক্রান্ত বিরোধ"
        elif "ভাড়া" in user_prompt or "rent" in prompt_lower or "বাড়িওয়ালা" in user_prompt:
            ctype = "rent_tenancy"
            title = "বাড়িভাড়া ও উচ্ছেদ সংক্রান্ত আইনি সহায়তা"
        elif "চুক্তি" in user_prompt or "contract" in prompt_lower:
            ctype = "contract"
            title = "চুক্তিভঙ্গ ও ক্ষতিপূরণ সংক্রান্ত বিরোধ"
        elif (
            "মারধর" in user_prompt
            or "হামলা" in user_prompt
            or "হুমকি" in user_prompt
            or "assault" in prompt_lower
        ):
            ctype = "criminal_complaint"
            title = "শারীরিক আঘাত ও হুমকির প্রেক্ষিতে আইনি নালিশ"
        else:
            ctype = "other"
            title = "নাগরিক আইনি সহায়তা আবেদন"

        # Ground facts from user's actual intake text
        narrative_snippet = ""
        try:
            if "User Intake Answers:\n" in user_prompt:
                ans_str = user_prompt.split("User Intake Answers:\n", 1)[1].split(
                    "\nTriage Chips:", 1
                )[0]
                ans_dict = json.loads(ans_str)
                for k in ["what_happened", "narrative", "where_happened", "who_involved"]:
                    v = ans_dict.get(k)
                    if v and isinstance(v, str) and v.strip():
                        narrative_snippet = v.strip()
                        break
        except Exception:
            pass

        if not narrative_snippet:
            for line in user_prompt.splitlines():
                if len(line.strip()) > 10 and not line.startswith(
                    ("User Intake Answers", "Triage Chips", "Urgency")
                ):
                    narrative_snippet = line.strip()
                    break

        if narrative_snippet:
            fact_text = narrative_snippet[:100]
            facts_list = [{"text": fact_text, "span_in_user_text": [0, len(fact_text)]}]
        else:
            facts_list = []

        resp = {
            "case_type": ctype,
            "title_suggestion": title,
            "parties": [
                {"name": "আবেদনকারী নাগরিক", "role": "বাদী / আবেদনকারী", "org": ""},
                {"name": "বিপক্ষ ব্যক্তি বা প্রতিষ্ঠান", "role": "বিবাদী", "org": ""},
            ],
            "dates": [
                {
                    "date": "2026-10-01",
                    "precision": "day",
                    "what": "ঘটনার প্রাথমিক সূচনা",
                    "from_user_text": True,
                }
            ],
            "facts": facts_list,
            "documents_mentioned": ["জাতীয় পরিচয়পত্র", "প্রাসঙ্গিক প্রমাণাদি"],
            "possible_issues": [
                {
                    "text": "ঘটনার সত্যতা ও প্রাসঙ্গিক কাগজপত্রের আইনি বৈধতা যাচাই।",
                    "kind": "research_suggestion",
                }
            ],
            "missing_information": ["ঘটনার প্রত্যক্ষদর্শীদের বিবরণ", "আনুষ্ঠানিক লিখিত প্রমাণাদি"],
            "user_objective": "আইনসঙ্গত উপায়ে বিরোধ নিষ্পত্তি ও প্রতিকার লাভ।",
            "clarifying_questions": ["এই বিষয়ে কি ইতিমধ্যে থানায় কোনো জিডি বা অভিযোগ করা হয়েছে?"],
            "urgency_signals": [],
        }
        return json.dumps(resp, ensure_ascii=False)

    def _generate_draft_helper(self, user_prompt: str) -> str:
        q_match = re.search(r"Question Text:\s*(.+)", user_prompt)
        q_text = q_match.group(1).strip() if q_match else "প্রশ্নের বিবরণ"

        c_match = re.search(r"Approved Optional Clause IDs:\s*(.+)", user_prompt)
        approved_ids: list[str] = []
        if c_match:
            raw_ids = c_match.group(1).strip()
            approved_ids = [i.strip(" '\"[]") for i in raw_ids.split(",") if i.strip(" '\"[]")]

        t_match = re.search(r"User Query / Term:\s*(.+)", user_prompt)
        term_text = t_match.group(1).strip() if t_match else ""

        rephrased = f"সহজ বাংলায়: {q_text} (দয়া করে সঠিক তথ্য প্রদান করুন)।"
        suggested_ids = [approved_ids[0]] if approved_ids else []

        explanation: dict[str, Any] = {
            "term": term_text or "আইনি পরিভাষা",
            "explanation_bn": "চুক্তির শর্তাবলী স্পষ্টভাবে পালনের আইনি বাধ্যবাধকতা রয়েছে।",
            "source_chip": "The Contract Act, 1872",
        }

        resp = {
            "rephrased_question": rephrased,
            "suggested_clause_ids": suggested_ids,
            "term_explanation": explanation,
        }
        return json.dumps(resp, ensure_ascii=False)


class RealLlmAdapterSlot:
    """
    Neutral adapter slot for real upstream LLM providers (e.g., Anthropic, OpenAI, Gemini).
    Disabled by default via ENABLE_REAL_LLM environment variable.
    """

    def __init__(self):
        self.enabled = os.environ.get("ENABLE_REAL_LLM", "false").lower() in ("true", "1", "yes")
        self.api_key = os.environ.get("REAL_LLM_API_KEY")

    def generate(
        self, system_prompt: str, user_prompt: str, schema: dict[str, Any] | None = None
    ) -> tuple[str, int]:
        if not self.enabled or not self.api_key:
            raise RuntimeError(
                "RealLlmAdapterSlot is disabled or missing REAL_LLM_API_KEY. "
                "Falling back to configured secondary or test provider."
            )
        # Placeholder for upstream API call when configured
        raise NotImplementedError(
            "Real upstream LLM calls are disabled in test/offline environment."
        )


class AIGateway:
    def __init__(self, db: DatabaseManager | None = None, max_token_limit: int = 4096):
        self.db = db or db_manager
        self.max_token_limit = max_token_limit
        self.redactor = PIIRedactor()
        self.primary_provider = FakeLLMProvider("mock-primary-v1")
        self.secondary_provider = FakeLLMProvider("mock-fallback-v1")
        self.real_slot = RealLlmAdapterSlot()
        self._ensure_default_prompts_seeded()

    def _ensure_default_prompts_seeded(self):
        default_prompts = [
            {
                "id": "legal_advisory.v1",
                "name": "Legal Problem Advisory Prompt",
                "version": "1.0.0",
                "system_prompt": "You are a Bangladesh Legal OS legal assistant. Analyze the user query with statutory references. Output strict JSON.",
                "user_template": "Query: {query}\nRelevant Sources: {sources}",
                "schema": {
                    "type": "object",
                    "properties": {
                        "summary": {"type": "string"},
                        "statutory_basis": {"type": "string"},
                        "section": {"type": "string"},
                        "confidence": {"type": "number"},
                    },
                    "required": ["summary", "statutory_basis"],
                },
            },
            {
                "id": "clause_summarizer.v1",
                "name": "Citizen Plain Language Summarizer",
                "version": "1.0.0",
                "system_prompt": "Explain the statutory clause in plain, calm Bangla for citizens. Output strict JSON.",
                "user_template": "Clause text: {clause_text}",
                "schema": {
                    "type": "object",
                    "properties": {
                        "plain_explanation_bn": {"type": "string"},
                        "key_rights": {"type": "array"},
                    },
                    "required": ["plain_explanation_bn"],
                },
            },
            {
                "id": "notice.explain.v1",
                "name": "Legal Notice Interpreter (M04)",
                "version": "1.0.0",
                "system_prompt": (
                    "You are the Bangladesh Legal Notice Interpreter (AIN-AI Module M04). "
                    "Analyze the given official notice or legal document text in simple, calm, citizen-friendly Bangla. "
                    "Output strictly conforming to the requested JSON schema. "
                    "Never invent unmentioned dates or unverified consequences."
                ),
                "user_template": "Document Text:\n{document_text}\n\nAs of Date: {as_of_date}",
                "schema": {
                    "type": "object",
                    "properties": {
                        "language": {"type": "string"},
                        "certainty": {"type": "string"},
                        "is_notice": {"type": "boolean"},
                        "notice_category": {"type": "string"},
                        "has_handwriting": {"type": "boolean"},
                        "multiple_notices_detected": {"type": "boolean"},
                        "summary_one_line": {"type": "string"},
                        "summary_chips": {"type": "array"},
                        "what_is_this": {
                            "type": "object",
                            "properties": {"text": {"type": "string"}},
                            "required": ["text"],
                        },
                        "sender": {
                            "type": "object",
                            "properties": {"text": {"type": "string"}},
                            "required": ["text"],
                        },
                        "why_received": {
                            "type": "object",
                            "properties": {"text": {"type": "string"}},
                            "required": ["text"],
                        },
                        "what_it_says": {"type": "array"},
                        "action_required": {"type": "array"},
                        "important_dates": {"type": "array"},
                        "documents_needed": {"type": "array"},
                        "if_ignored": {"type": "object"},
                        "questions_for_lawyer": {"type": "array"},
                        "not_found": {"type": "array"},
                        "cited_laws_in_notice": {"type": "array"},
                    },
                    "required": [
                        "language",
                        "certainty",
                        "summary_one_line",
                        "what_is_this",
                        "sender",
                        "why_received",
                        "what_it_says",
                        "action_required",
                        "important_dates",
                        "documents_needed",
                        "questions_for_lawyer",
                    ],
                },
            },
            {
                "id": "notice.explain_simpler.v1",
                "name": "Simpler Plain Bangla Notice Explainer (M04)",
                "version": "1.0.0",
                "system_prompt": (
                    "Rewrite the verified legal notice explanation in even simpler, everyday Bangla for a non-lawyer citizen. "
                    "Do not add any unverified legal consequences. Output strict JSON."
                ),
                "user_template": "Notice Analysis:\n{analysis_json}",
                "schema": {
                    "type": "object",
                    "properties": {
                        "language": {"type": "string"},
                        "simpler_summary": {"type": "string"},
                        "simpler_what_it_says": {"type": "array"},
                        "simpler_actions": {"type": "array"},
                        "simpler_warning": {"type": "string"},
                    },
                    "required": [
                        "language",
                        "simpler_summary",
                        "simpler_what_it_says",
                        "simpler_actions",
                    ],
                },
            },
            {
                "id": "case.review.v1",
                "name": "Case Folder Review & Issue Spotting (M06)",
                "version": "1.0.0",
                "system_prompt": (
                    "Analyze citizen legal case details in Bangladesh to identify possible issues, "
                    "missing information, required documents, approved legal processes, questions for a lawyer, "
                    "and options to discuss. STRICT PROHIBITION: You must NEVER state or predict the outcome of "
                    "the case, provide win/loss probabilities, or tell the user they will win or lose. "
                    "Always include the mandatory disclaimer 'AI বিশ্লেষণ, আইনি পরামর্শ নয়'. Output strict JSON in Bengali."
                ),
                "user_template": "Case Title: {case_title}\nCase Type: {case_type}\nParties: {parties}\nFacts: {facts}\nDocuments: {documents}\nTasks: {tasks}\nNotes: {notes}",
                "schema": {
                    "type": "object",
                    "properties": {
                        "possible_issues": {"type": "array"},
                        "missing_information": {"type": "array"},
                        "required_documents": {"type": "array"},
                        "possible_processes": {"type": "array"},
                        "questions_for_lawyer": {"type": "array"},
                        "options_to_discuss": {"type": "array"},
                        "ai_disclaimer": {"type": "string"},
                    },
                    "required": [
                        "possible_issues",
                        "missing_information",
                        "required_documents",
                        "possible_processes",
                        "questions_for_lawyer",
                        "options_to_discuss",
                        "ai_disclaimer",
                    ],
                },
            },
            {
                "id": "intake.profile.v1",
                "name": "Citizen Intake & Triage Case Profiler (M11)",
                "version": "1.0.0",
                "system_prompt": (
                    "You are the Bangladesh Legal Intake and Case Profiling Agent (AIN-AI Module M11). "
                    "Extract structured facts, parties, dates, and issues from the user's answers. "
                    "Rules: do not infer facts the user did not state; possible_issues are labelled research suggestions; "
                    "no legal conclusions; no outcome statements or predictions. Output strict JSON."
                ),
                "user_template": "User Intake Answers:\n{answers_json}\nTriage Chips: {triage_chips}\nUrgency: {urgency}",
                "schema": {
                    "type": "object",
                    "properties": {
                        "case_type": {"type": "string"},
                        "title_suggestion": {"type": "string"},
                        "parties": {"type": "array"},
                        "dates": {"type": "array"},
                        "facts": {"type": "array"},
                        "documents_mentioned": {"type": "array"},
                        "possible_issues": {"type": "array"},
                        "missing_information": {"type": "array"},
                        "user_objective": {"type": "string"},
                        "clarifying_questions": {"type": "array"},
                        "urgency_signals": {"type": "array"},
                    },
                    "required": [
                        "case_type",
                        "title_suggestion",
                        "parties",
                        "dates",
                        "facts",
                        "documents_mentioned",
                        "possible_issues",
                        "missing_information",
                        "user_objective",
                        "clarifying_questions",
                    ],
                },
            },
            {
                "id": "draft.helper.v1",
                "name": "Drafting Question & Clause Helper (M05)",
                "version": "1.0.0",
                "system_prompt": (
                    "You are the Bangladesh Legal Drafting Assistant (AIN-AI Module M05). "
                    "Your role is strictly limited to: (1) rephrasing questions into simpler Bangla, "
                    "(2) suggesting optional clauses strictly from the template's approved clause list, "
                    "and (3) explaining legal terms with library source citations. "
                    "You MUST NOT generate free clauses, predict dispute outcomes, or advise whether an agreement is fair or favourable. "
                    "Output strict JSON conforming to the allow-list schema only."
                ),
                "user_template": (
                    "Template Code: {template_code}\n"
                    "Question ID: {question_id}\n"
                    "Question Text: {question_text}\n"
                    "Approved Optional Clause IDs: {approved_clause_ids}\n"
                    "User Query / Term: {user_query}"
                ),
                "schema": {
                    "type": "object",
                    "properties": {
                        "rephrased_question": {"type": "string"},
                        "suggested_clause_ids": {"type": "array", "items": {"type": "string"}},
                        "term_explanation": {
                            "type": "object",
                            "properties": {
                                "term": {"type": "string"},
                                "explanation_bn": {"type": "string"},
                                "source_chip": {"type": "string"},
                            },
                            "required": ["term", "explanation_bn"],
                        },
                    },
                    "additionalProperties": False,
                },
            },
        ]
        for p in default_prompts:
            self.db.save_prompt(p)

    def execute_prompt(
        self,
        prompt_id: str,
        variables: dict[str, Any],
        prompt_version: str | None = None,
        user_id: str = "system",
        model_preference: str = "primary",
    ) -> dict[str, Any]:
        """
        Executes a prompt through the governed AI Gateway pipeline:
        1. Refuses unregistered prompts; verifies version.
        2. Prompt injection scanning (flags and defends against prompt hijacking).
        3. PII Redaction
        4. Cost Guard verification
        5. Model execution with fallback
        6. Schema validation & anti-hallucination guard (never produces deadline)
        7. Unredaction
        8. Audit & Output Persistence (records prompt id, version, security flags)
        """
        prompt = self.db.get_prompt(prompt_id)
        if not prompt:
            raise ValueError(f"Unregistered prompt '{prompt_id}' refused.")

        registered_ver = prompt.get("version", "1.0.0")
        if prompt_version is not None and registered_ver != prompt_version:
            raise ValueError(
                f"Prompt '{prompt_id}' version mismatch: requested '{prompt_version}', registered is '{registered_ver}'."
            )

        system_prompt = prompt["system_prompt"]
        user_template = prompt["user_template"]
        schema = prompt.get("schema")

        # Prompt injection detection
        injection_patterns = [
            re.compile(r"ignore\s+(?:all\s+|prior\s+|previous\s+)?instructions", re.IGNORECASE),
            re.compile(r"output\s+(?:a\s+)?deadline", re.IGNORECASE),
            re.compile(r"reveal\s+(?:the\s+)?system\s+prompt", re.IGNORECASE),
            re.compile(r"disregard\s+(?:all\s+)?prior", re.IGNORECASE),
            re.compile(r"system\s+override", re.IGNORECASE),
        ]
        security_flags: list[str] = []
        injection_flagged = False
        for k, v in variables.items():
            if isinstance(v, str):
                for p in injection_patterns:
                    if p.search(v):
                        injection_flagged = True
                        security_flags.append(f"prompt_injection_pattern:{p.pattern}")

        if injection_flagged:
            security_flags.append("PROMPT_INJECTION_FLAGGED")

        # 1. Render variables into user template
        try:
            rendered_user = user_template.format(**variables)
        except KeyError as e:
            raise ValueError(f"Missing required prompt variable: {e}") from e

        # If injection detected, encapsulate untrusted content
        if injection_flagged:
            rendered_user = f"<untrusted_document>\n{rendered_user}\n</untrusted_document>"

        # 2. PII Redaction
        redacted_user, redactions = self.redactor.redact(rendered_user)

        # 3. Cost Guard check
        estimated_input_tokens = len(system_prompt + redacted_user) // 4
        if estimated_input_tokens > self.max_token_limit:
            raise CostLimitExceededError(
                f"Request token length ({estimated_input_tokens}) exceeds maximum limit ({self.max_token_limit})."
            )

        # 4. Model execution with fallback
        model_name = self.primary_provider.name
        raw_output = ""
        cost_tokens = 0

        # Try real slot if explicitly preferred and enabled
        executed = False
        if model_preference == "real":
            try:
                raw_output, cost_tokens = self.real_slot.generate(
                    system_prompt, redacted_user, schema
                )
                model_name = "real-llm-adapter"
                executed = True
            except Exception:
                executed = False

        if not executed:
            try:
                raw_output, cost_tokens = self.primary_provider.generate(
                    system_prompt, redacted_user, schema
                )
                model_name = self.primary_provider.name
            except Exception:
                # Fallback to secondary provider
                raw_output, cost_tokens = self.secondary_provider.generate(
                    system_prompt, redacted_user, schema
                )
                model_name = self.secondary_provider.name

        # 5. Schema validation & anti-deadline enforcement
        try:
            parsed_json = json.loads(raw_output)
            if prompt_id == "draft.helper.v1" and isinstance(parsed_json, dict):
                from packages.trust_kernel.outcome_filter import filter_outcome_predictions

                # 1. Drop free clauses and any keys outside allowed schema
                allowed_keys = {"rephrased_question", "suggested_clause_ids", "term_explanation"}
                parsed_json = {k: v for k, v in parsed_json.items() if k in allowed_keys}

                # 2. Filter suggested_clause_ids strictly against approved list
                raw_approved = variables.get("approved_clause_ids", "")
                if isinstance(raw_approved, list):
                    approved_set = set(raw_approved)
                else:
                    approved_set = {
                        x.strip(" '\"[]") for x in str(raw_approved).split(",") if x.strip(" '\"[]")
                    }

                if "suggested_clause_ids" in parsed_json and isinstance(
                    parsed_json["suggested_clause_ids"], list
                ):
                    parsed_json["suggested_clause_ids"] = [
                        cid for cid in parsed_json["suggested_clause_ids"] if cid in approved_set
                    ]

                # 3. Filter any outcome predictions from text fields
                if "rephrased_question" in parsed_json and isinstance(
                    parsed_json["rephrased_question"], str
                ):
                    parsed_json["rephrased_question"] = filter_outcome_predictions(
                        parsed_json["rephrased_question"]
                    )

                if "term_explanation" in parsed_json and isinstance(
                    parsed_json["term_explanation"], dict
                ):
                    exp = parsed_json["term_explanation"]
                    if "explanation_bn" in exp and isinstance(exp.get("explanation_bn"), str):
                        exp["explanation_bn"] = filter_outcome_predictions(exp["explanation_bn"])

                raw_output = json.dumps(parsed_json, ensure_ascii=False)

            if schema:
                jsonschema.validate(instance=parsed_json, schema=schema)
                # Anti-deadline defense: Ensure prompt injection did not force an unapproved deadline field
                if "deadline" in parsed_json and "deadline" not in schema.get("properties", {}):
                    del parsed_json["deadline"]
                    raw_output = json.dumps(parsed_json, ensure_ascii=False)
        except (json.JSONDecodeError, jsonschema.ValidationError) as e:
            # Record failed output for transparency
            out_id = f"out-{uuid.uuid4().hex[:12]}"
            self.db.save_ai_output(
                {
                    "id": out_id,
                    "prompt_id": prompt_id,
                    "prompt_version": registered_ver,
                    "model": model_name,
                    "raw_input": rendered_user,
                    "redacted_input": redacted_user,
                    "raw_output": raw_output,
                    "unredacted_output": raw_output,
                    "cost_tokens": cost_tokens,
                    "status": "schema_error",
                    "security_flags": security_flags,
                }
            )
            raise SchemaValidationError(f"Output failed schema validation: {e}") from e

        # 6. Unredaction
        unredacted_output_str = self.redactor.unredact(raw_output, redactions)
        final_data = json.loads(unredacted_output_str)

        # 7. Persistence
        output_id = f"out-{uuid.uuid4().hex[:12]}"
        self.db.save_ai_output(
            {
                "id": output_id,
                "prompt_id": prompt_id,
                "prompt_version": registered_ver,
                "model": model_name,
                "raw_input": rendered_user,
                "redacted_input": redacted_user,
                "raw_output": raw_output,
                "unredacted_output": unredacted_output_str,
                "cost_tokens": cost_tokens,
                "status": "success",
                "security_flags": security_flags,
            }
        )

        return {
            "output_id": output_id,
            "prompt_id": prompt_id,
            "prompt_version": registered_ver,
            "model": model_name,
            "provider": "real" if (executed and model_name == "real-llm-adapter") else "fake",
            "data": final_data,
            "cost_tokens": cost_tokens,
            "redactions_applied": len(redactions),
            "status": "success",
            "injection_flagged": injection_flagged,
            "security_flags": security_flags,
        }

    def store_claim_links(
        self,
        output_id: str,
        claims: list[dict[str, Any]],
        as_of_date: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Stores claims associated with an AI output.
        Every claim in an AI output is stored with its source-passage link;
        a claim without a verified link is flagged and never shown as verified.
        """
        from packages.trust_kernel.citation_verifier import citation_verifier

        stored_links = []
        for c in claims:
            cid = c.get("id") or f"clm-{uuid.uuid4().hex[:12]}"
            claim_text = c.get("claim_text", "").strip()
            source_id = c.get("source_id")
            source_version_id = c.get("source_version_id")
            section_ref = c.get("section_ref")
            passage_text = c.get("passage_text")

            is_verified = False
            is_flagged = False
            verification_status = "UNVERIFIED"
            score = 0.0
            details: dict[str, Any] = {}

            if not source_id or not source_version_id:
                is_flagged = True
                verification_status = "UNVERIFIED"
                details = {"flagged": True, "reason": "No valid source passage link provided"}
            else:
                report = citation_verifier.verify(
                    claim_text=claim_text,
                    source_id=source_id,
                    source_version_id=source_version_id,
                    section_ref=section_ref,
                    passage_text=passage_text,
                    as_of_date=as_of_date,
                )
                score = report.match_score
                if report.status == "VERIFIED" and report.as_of_valid:
                    is_verified = True
                    is_flagged = False
                    verification_status = "VERIFIED"
                    details = {"flagged": False, "verified_span": report.verified_span}
                else:
                    is_verified = False
                    is_flagged = True
                    verification_status = report.status
                    details = {"flagged": True, "discrepancies": report.discrepancies}

            claim_record = {
                "id": cid,
                "output_id": output_id,
                "claim_text": claim_text,
                "source_id": source_id or "unlinked",
                "source_version_id": source_version_id or "unlinked",
                "section_ref": section_ref,
                "verification_status": verification_status,
                "verification_score": score,
                "details": details,
                "is_verified": is_verified,
                "is_flagged": is_flagged,
            }
            self.db.save_claim_link(claim_record)
            stored_links.append(claim_record)

        return stored_links

    def get_output_claims(self, output_id: str) -> list[dict[str, Any]]:
        """
        Retrieves claim links for an output.
        Guarantees that a claim without a verified link is flagged and NEVER shown as verified.
        """
        raw_links = self.db.list_claim_links(output_id)
        results = []
        for link in raw_links:
            status = link.get("verification_status")
            is_verified = status == "VERIFIED"
            is_flagged = not is_verified or link.get("details", {}).get("flagged", False)
            results.append(
                {
                    **link,
                    "is_verified": is_verified,
                    "is_flagged": is_flagged,
                }
            )
        return results

    def execute(self, task: str, input_data: dict[str, Any]) -> dict[str, Any]:
        """Convenience execution method for AI tasks like intake.profile.v1."""
        return self.execute_prompt(
            prompt_id=task,
            variables={
                "answers_json": json.dumps(input_data.get("answers", {}), ensure_ascii=False),
                "triage_chips": json.dumps(input_data.get("triage_chips", []), ensure_ascii=False),
                "urgency": input_data.get("urgency", "normal"),
            },
        )
    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        schema: dict[str, Any] | None = None,
        user_id: str = "system",
    ) -> dict[str, Any]:
        """Direct generation method complying with X-004 audit requirements."""
        redacted_user, redactions = self.redactor.redact(user_prompt)
        content, tokens = self.primary_provider.generate(system_prompt, redacted_user, schema)
        unredacted_content = self.redactor.unredact(content, redactions)

        out_id = f"out-{uuid.uuid4().hex[:12]}"
        prompt_hash = hashlib.sha256((system_prompt + user_prompt).encode("utf-8")).hexdigest()

        # Save AI output
        self.db.save_ai_output(
            {
                "id": out_id,
                "prompt_id": "direct_generate",
                "prompt_version": "1.0.0",
                "model": self.primary_provider.name,
                "provider": self.primary_provider.name,
                "user_id": user_id,
                "prompt_hash": prompt_hash,
                "raw_input": user_prompt,
                "redacted_input": redacted_user,
                "raw_output": content,
                "unredacted_output": unredacted_content,
                "cost_tokens": tokens,
            }
        )

        # Log into audit service
        audit_service.log(
            actor_id=user_id,
            actor_role="system",
            action="AI_GATEWAY_GENERATE",
            object_type="ai_output",
            object_id=out_id,
            meta={"prompt_hash": prompt_hash, "provider": self.primary_provider.name},
        )
        return {
            "id": out_id,
            "content": unredacted_content,
            "tokens_used": tokens,
            "prompt_hash": prompt_hash,
        }


ai_gateway = AIGateway()
