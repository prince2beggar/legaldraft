/**
 * AIN-AI Frontend Shared Formatter & Enum Dictionary (Directive V2, V4, V5, V6, W2, W3, W4)
 *
 * Provides:
 * 1. UI constants (all user-facing labels touched in V1–V8, centralized)
 * 2. Bangla date & time formatting in Asia/Dhaka (+06:00) with Bangla digits
 * 3. Relative days formatting ("৪ দিন অতিবাহিত", "আজই শেষ দিন", "১ দিন বাকি")
 * 4. Strict enum-to-Bangla translation map (throws in dev/tests, safe neutral fallback in production)
 * 5. Deadline basis & confirmation state formatters with [নমুনা] statutory tag
 */

const UI_CONSTANTS = {
  // Navigation & Actions
  BTN_SUBMIT_PROBLEM: 'সমস্যা জানান',
  NEXT_ACTION_HEADER: 'পরবর্তী শীর্ষ পদক্ষেপ',
  WHY_AM_I_SEEING_THIS: 'কেন এটি দেখানো হচ্ছে?',
  VERIFY_RULE: 'যাচাই করুন',
  RULE_SAMPLE_TAG: '[নমুনা - যাচাই বাকি]',
  PROPOSAL_VERIFY_NOTE: 'তারিখটি একটি প্রস্তাব — আইনজীবীর সাথে যাচাই করুন',

  // Status & Confirmation
  CONFIRMED_BY_YOU: 'আপনি নিশ্চিত করেছেন',
  PROPOSED_CONFIRM: 'প্রস্তাবিত — নিশ্চিত করুন',
  DEMO_BANNER_TEXT: 'এটি একটি সক্রিয় ডেমো মোড — টেস্ট ডেটা ব্যবহার করা হচ্ছে',
  DEMO_BADGE: 'ডেমো মোড',

  // Filters & Headers
  FILTER_ALL: 'সব',
  FILTER_PENDING: 'অপেক্ষমাণ',
  FILTER_RESOLVED: 'নিষ্পত্তি',
  ACTIVE_CASES_TITLE: 'সক্রিয় সমস্যা ও মামলা',

  // Date & Counter Strings
  DAYS_OVERDUE: 'দিন অতিবাহিত',
  TODAY_LAST_DAY: 'আজই শেষ দিন',
  DAYS_REMAINING: 'দিন বাকি',
  DATE_NOT_AVAILABLE: '—',
  UNKNOWN_VALUE: 'অজানা',

  // Provenance Bases
  STATED_DATE: 'নোটিশে উল্লেখিত তারিখ',
  USER_ENTERED_DATE: 'ব্যবহারকারীর নির্ধারিত তারিখ',
  RULE_BASED_DATE: 'নিয়ম অনুযায়ী',

  // Empty State Fallbacks
  EMPTY_NOTES: 'কোনো নোট সংরক্ষিত নেই।',
  EMPTY_DEADLINES: 'কোনো জরুরি সময়সীমা নেই।',
  EMPTY_CASES: 'কোনো সমস্যা বা মামলা নেই।',
};

const BANGLA_DIGITS = ['০', '১', '২', '৩', '৪', '৫', '৬', '৭', '৮', '৯'];
const BANGLA_MONTHS = [
  'জানুয়ারি', 'ফেব্রুয়ারি', 'মার্চ', 'এপ্রিল', 'মে', 'জুন',
  'জুলাই', 'আগস্ট', 'সেপ্টেম্বর', 'অক্টোবর', 'নভেম্বর', 'ডিসেম্বর'
];

function toBanglaDigits(val) {
  if (val === null || val === undefined) return '';
  return String(val).replace(/[0-9]/g, d => BANGLA_DIGITS[Number(d)]);
}

function toAsciiDigits(str) {
  if (str === null || str === undefined) return '';
  const bnToAscii = {'০':'0', '১':'1', '২':'2', '৩':'3', '৪':'4', '৫':'5', '৬':'6', '৭':'7', '৮':'8', '৯':'9'};
  return String(str).replace(/[০-৯]/g, d => bnToAscii[d]);
}

/**
 * Formats ISO date or timestamp into Asia/Dhaka date: "৯ অক্টোবর ২০২৬"
 */
function formatBanglaDate(dateInput) {
  if (!dateInput) return UI_CONSTANTS.DATE_NOT_AVAILABLE;
  try {
    const s = toAsciiDigits(String(dateInput).trim());
    // Match YYYY-MM-DD
    const match = s.match(/^(\d{4})-(\d{2})-(\d{2})/);
    if (match) {
      const year = match[1];
      const monthIdx = parseInt(match[2], 10) - 1;
      const day = parseInt(match[3], 10);
      const bnDay = toBanglaDigits(day);
      const bnMonth = BANGLA_MONTHS[monthIdx] || match[2];
      const bnYear = toBanglaDigits(year);
      return `${bnDay} ${bnMonth} ${bnYear}`;
    }

    const d = new Date(dateInput);
    if (isNaN(d.getTime())) return String(dateInput);
    // Offset +6 for Asia/Dhaka
    const utc = d.getTime() + (d.getTimezoneOffset() * 60000);
    const dhakaDate = new Date(utc + (3600000 * 6));
    const day = toBanglaDigits(dhakaDate.getDate());
    const month = BANGLA_MONTHS[dhakaDate.getMonth()];
    const year = toBanglaDigits(dhakaDate.getFullYear());
    return `${day} ${month} ${year}`;
  } catch (e) {
    return UI_CONSTANTS.DATE_NOT_AVAILABLE;
  }
}

/**
 * Formats time into Asia/Dhaka: "রাত ১০:৩০"
 */
function formatBanglaTime(dateInput) {
  if (!dateInput) return '';
  try {
    const d = new Date(dateInput);
    if (isNaN(d.getTime())) return '';
    const utc = d.getTime() + (d.getTimezoneOffset() * 60000);
    const dhakaDate = new Date(utc + (3600000 * 6));
    const hours = dhakaDate.getHours();
    const mins = dhakaDate.getMinutes();

    let period = 'সকাল';
    let h12 = hours;
    if (hours >= 20 || hours < 4) {
      period = 'রাত';
      h12 = hours >= 20 ? hours - 12 : (hours === 0 ? 12 : hours);
    } else if (hours >= 4 && hours < 12) {
      period = 'সকাল';
      h12 = hours === 0 ? 12 : hours;
    } else if (hours >= 12 && hours < 16) {
      period = 'দুপুর';
      h12 = hours === 12 ? 12 : hours - 12;
    } else if (hours >= 16 && hours < 18) {
      period = 'বিকাল';
      h12 = hours - 12;
    } else {
      period = 'সন্ধ্যা';
      h12 = hours - 12;
    }

    const padM = mins < 10 ? '০' + toBanglaDigits(mins) : toBanglaDigits(mins);
    return `${period} ${toBanglaDigits(h12)}:${padM}`;
  } catch (e) {
    return '';
  }
}

/**
 * Formats datetime: "৯ অক্টোবর ২০২৬, রাত ১০:৩০"
 */
function formatBanglaDateTime(dateInput) {
  if (!dateInput) return UI_CONSTANTS.DATE_NOT_AVAILABLE;
  const s = String(dateInput).trim();
  const datePart = formatBanglaDate(s);
  if (s.includes('T') || s.includes(':')) {
    const timePart = formatBanglaTime(s);
    if (timePart) return `${datePart}, ${timePart}`;
  }
  return datePart;
}

/**
 * Formats days left according to V4:
 * "-৪ দিন বাকি" -> "৪ দিন অতিবাহিত" (overdue)
 * "০" -> "আজই শেষ দিন"
 * "১ দিন বাকি" -> "১ দিন বাকি"
 */
function formatDaysLeft(days) {
  if (days === null || days === undefined) return '';
  const num = parseInt(days, 10);
  if (isNaN(num)) return '';
  if (num < 0) {
    return `${toBanglaDigits(Math.abs(num))} ${UI_CONSTANTS.DAYS_OVERDUE}`;
  } else if (num === 0) {
    return UI_CONSTANTS.TODAY_LAST_DAY;
  } else {
    return `${toBanglaDigits(num)} ${UI_CONSTANTS.DAYS_REMAINING}`;
  }
}

/**
 * Comprehensive Strict Bangla Enum Translation Table
 */
const ENUM_MAPS = {
  case_type: {
    land_dispute: 'জমিজমা ও সম্পত্তি',
    land_property: 'জমি ও সম্পত্তি',
    notice_response: 'আইনি নোটিশের জবাব',
    legal_notice: 'আইনি নোটিশ',
    cheque_dishonor: 'চেক ডিজঅনার',
    eviction: 'উচ্ছেদ সংক্রান্ত',
    money_claim: 'টাকা লেনদেন ও অর্থ দাবি',
    civil: 'দেওয়ানি বিরোধ',
    criminal: 'ফৌজদারি বা এনআই অ্যাক্ট',
    criminal_complaint: 'ফৌজদারি নালিশ',
    criminal_defense: 'ফৌজদারি আত্মরক্ষা',
    family: 'পারিবারিক বিরোধ',
    family_dispute: 'পারিবারিক বিরোধ',
    rent_dispute: 'ভাড়া বিরোধ',
    rent_tenancy: 'বাড়িভাড়া ও উচ্ছেদ',
    contract: 'চুক্তি ও লেনদেন',
    contract_breach: 'চুক্তি লঙ্ঘন',
    inheritance: 'উত্তরাধিকার বিরোধ',
    labour_employment: 'শ্রম ও কর্মসংস্থান',
    consumer: 'ভোক্তা অধিকার',
    notice_received: 'আইনি নোটিশ প্রাপ্তি',
    court_matter: 'আদালতের মামলা',
    tax: 'কর ও রাজস্ব',
    general: 'সাধারণ আইনি বিষয়',
    legacy_civil: 'দেওয়ানি বিরোধ',
    other: 'অন্যান্য আইনি বিষয়',
  },
  status: {
    active: 'সক্রিয়',
    action_required: 'পদক্ষেপ প্রয়োজন',
    completed: 'সম্পন্ন',
    archived: 'আর্কাইভকৃত',
    pending: 'অপেক্ষমাণ',
    in_progress: 'চলমান',
    draft: 'খসড়া',
    drafting: 'খসড়া প্রস্তুতকরণ',
    new: 'নতুন',
    reviewed: 'পর্যালোচিত',
    unconfirmed: 'অনিশ্চিত',
    confirmed: 'নিশ্চিত',
    overdue: 'অতিবাহিত',
    cancelled: 'বাতিল',
    not_started: 'শুরু হয়নি',
    extracted: 'চিহ্নিত তথ্য',
    proposed: 'প্রস্তাবিত',
    waiting: 'অপেক্ষমাণ',
    in_review: 'পর্যালোচনাধীন',
    closed: 'বন্ধ',
    dismissed: 'খারিজ',
  },
  urgency: {
    urgent: 'জরুরি',
    critical: 'জরুরি',
    high: 'উচ্চ',
    normal: 'নিয়মিত',
    medium: 'নিয়মিত',
    low: 'সাধারণ',
    urgent_no_help: 'জরুরি ট্রায়াজ',
    urgent_triage: 'জরুরি ট্রায়াজ',
    action_required: 'পদক্ষেপ প্রয়োজন',
  },
  priority: {
    urgent: 'জরুরি',
    critical: 'জরুরি',
    high: 'উচ্চ',
    normal: 'নিয়মিত',
    medium: 'নিয়মিত',
    low: 'সাধারণ',
  },
  deadline_kind: {
    court_hearing: 'আদালত শুনানি',
    notice_response: 'নোটিশের লিখিত জবাব',
    statute_of_limitations: 'তামাদির মেয়াদ',
    document_submission: 'নথিপত্র দাখিল',
    appeal_window: 'আপিলের সময়সীমা',
    payment_due: 'পরিশোধের মেয়াদ',
    filing_deadline: 'মামলা দায়েরের শেষ তারিখ',
    gd_submission: 'জিডি কপি দাখিল',
    general_deadline: 'সাধারণ সময়সীমা',
  },
  doc_type: {
    khatian: 'খতিয়ান বা পরচা',
    deed: 'মালিকানা দলিল',
    cheque_copy: 'ডিসঅনারকৃত চেক',
    bank_memo: 'ব্যাংক রিটার্ন মেমো',
    tenancy_agreement: 'ভাড়া চুক্তিপত্র',
    eviction_notice: 'উচ্ছেদ নোটিশ',
    money_receipt: 'টাকা লেনদেনের প্রমাণ',
    received_notice: 'প্রাপ্ত আইনি নোটিশ',
    general_document: 'সাধারণ দলিল',
    court_order: 'আদালতের আদেশ',
    petition: 'আবেদনপত্র বা আরজি',
    nid: 'জাতীয় পরিচয়পত্র',
    notice_legal: 'আইনি নোটিশ',
    notice_court: 'আদালতের নোটিশ বা সমন',
    notice_government: 'সরকারি নোটিশ',
    agreement_rent: 'ভাড়া চুক্তিপত্র',
    agreement_service: 'সেবা চুক্তিপত্র',
    agreement_sale: 'বায়না বা বিক্রয় চুক্তিপত্র',
    deed_printed: 'মুদ্রিত দলিল',
    power_of_attorney: 'আমমোক্তারনামা (পাওয়ার অব অ্যাটর্নি)',
    affidavit: 'হলফনামা (অ্যাফিডেভিট)',
    application: 'দরখাস্ত বা আবেদন',
    receipt: 'টাকা প্রাপ্তি রসিদ',
    other: 'অন্যান্য নথি',
  },
  deadline_basis: {
    stated_date: 'নোটিশে উল্লেখিত তারিখ',
    notice_stated: 'নোটিশে উল্লেখিত তারিখ',
    rule_based: 'নিয়ম অনুযায়ী',
    user_entered: 'ব্যবহারকারীর নির্ধারিত তারিখ',
    user_set: 'ব্যবহারকারীর নির্ধারিত তারিখ',
  },
  deadline_state: {
    confirmed: 'আপনি নিশ্চিত করেছেন',
    unconfirmed: 'প্রস্তাবিত — নিশ্চিত করুন',
    proposed: 'প্রস্তাবিত — নিশ্চিত করুন',
  },
  system_tags: {
    sample_limit: '[নমুনা - যাচাই বাকি]',
  },
};
ENUM_MAPS.document_type = ENUM_MAPS.doc_type;

/**
 * Dev Mode State Management (Directive W2)
 * In Dev Mode / Tests: throws Error on unmapped enum.
 * In Production: returns neutral fallback "—" and emits console.warn.
 */
let _devMode = (typeof window !== 'undefined' && typeof window.DEV_MODE !== 'undefined')
  ? Boolean(window.DEV_MODE)
  : true;

function setDevMode(val) {
  _devMode = Boolean(val);
  if (typeof window !== 'undefined') {
    window.DEV_MODE = _devMode;
  }
}

function isDevMode() {
  if (typeof window !== 'undefined' && typeof window.DEV_MODE !== 'undefined') {
    return Boolean(window.DEV_MODE);
  }
  return _devMode;
}

/**
 * Production-Safe Enum Translator (Directive W2)
 */
function formatEnum(category, key) {
  if (key === null || key === undefined || key === '') return '';
  const cleanKey = String(key).trim().toLowerCase();
  const catTable = ENUM_MAPS[category];

  if (!catTable) {
    if (isDevMode()) {
      throw new Error(`[EnumTranslationError] Unknown enum category: "${category}"`);
    } else {
      console.warn(`[EnumWarning] Unknown enum category: "${category}"`);
      return UI_CONSTANTS.DATE_NOT_AVAILABLE; // neutral fallback "—"
    }
  }

  const translated = catTable[cleanKey];
  if (!translated) {
    if (isDevMode()) {
      throw new Error(`[EnumTranslationError] Missing Bangla translation for enum [${category}].[${cleanKey}]`);
    } else {
      console.warn(`[EnumWarning] Missing Bangla translation for enum [${category}].[${cleanKey}], rendering fallback`);
      return UI_CONSTANTS.DATE_NOT_AVAILABLE; // neutral fallback "—"
    }
  }

  return translated;
}

/**
 * Formats deadline provenance basis string with statutory badge and verification notice (Directives V6, W4)
 * For ni_act_138_response_window and any statutory rule: labelled [নমুনা] with proposal verification notice.
 */
function formatDeadlineProvenance(basisType, ruleKey) {
  let basis = basisType;
  let rule = ruleKey;

  if (typeof basisType === 'object' && basisType !== null) {
    basis = basisType.calculation_basis || basisType.basis;
    rule = basisType.rule_key || basisType.rule_id;
  }

  if (basis === 'rule_based' || rule) {
    const ruleLabel = (rule === 'demo_sample_period' || rule === 'ni_act_138_response_window')
      ? '১০ দিন (নমুনা)'
      : (rule ? `${rule} [নমুনা]` : '১০ দিন (নমুনা)');

    const sampleBadge = `<span class="badge-sample" style="display:inline-block; font-size:11px; padding:1px 6px; background:#fef3c7; color:#92400e; border:1px solid #fde68a; border-radius:4px; font-weight:600; margin-left:4px;">${UI_CONSTANTS.RULE_SAMPLE_TAG}</span>`;
    const verifyProposalText = `<div style="font-size:12px; color:var(--text-muted, #64748b); margin-top:2px;">${UI_CONSTANTS.PROPOSAL_VERIFY_NOTE}</div>`;

    return `<span>${UI_CONSTANTS.RULE_BASED_DATE}: ${ruleLabel} ${sampleBadge}</span> <a href="/admin/rules#${encodeURIComponent(rule || '')}" class="verify-rule-link" style="color:var(--color-primary, #1e3a8a); text-decoration:underline; font-size:12px; margin-left:4px;">(${UI_CONSTANTS.VERIFY_RULE})</a>${verifyProposalText}`;
  }

  if (basis === 'user_entered' || basis === 'user_set') {
    return UI_CONSTANTS.USER_ENTERED_DATE;
  }

  return UI_CONSTANTS.STATED_DATE;
}

/**
 * Formats deadline confirmation state
 */
function formatDeadlineState(isConfirmed) {
  return isConfirmed ? UI_CONSTANTS.CONFIRMED_BY_YOU : UI_CONSTANTS.PROPOSED_CONFIRM;
}

// Export to window
if (typeof window !== 'undefined') {
  window.UI_CONSTANTS = UI_CONSTANTS;
  window.toBanglaDigits = toBanglaDigits;
  window.formatBanglaDate = formatBanglaDate;
  window.formatBanglaTime = formatBanglaTime;
  window.formatBanglaDateTime = formatBanglaDateTime;
  window.formatDaysLeft = formatDaysLeft;
  window.ENUM_MAPS = ENUM_MAPS;
  window.formatEnum = formatEnum;
  window.setDevMode = setDevMode;
  window.isDevMode = isDevMode;
  window.formatDeadlineProvenance = formatDeadlineProvenance;
  window.formatDeadlineState = formatDeadlineState;
}

if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    UI_CONSTANTS,
    toBanglaDigits,
    toAsciiDigits,
    formatBanglaDate,
    formatBanglaTime,
    formatBanglaDateTime,
    formatDaysLeft,
    ENUM_MAPS,
    formatEnum,
    setDevMode,
    isDevMode,
    formatDeadlineProvenance,
    formatDeadlineState,
  };
}
