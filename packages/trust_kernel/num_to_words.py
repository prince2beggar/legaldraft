"""
Number-to-Words Converter & Numeral Consistency Engine for Bangladesh Legal Context (SRS M05, AC-M05-5).
Provides deterministic conversion of numerals to words in Bengali and English,
and validates numeral-vs-word consistency to prevent legal drafting discrepancies.
"""

from __future__ import annotations

import re
from typing import Tuple

BN_DIGITS = "০১২৩৪৫৬৭৮৯"
_EN_TO_BN_TRANS = str.maketrans("0123456789", BN_DIGITS)
_BN_TO_EN_TRANS = str.maketrans(BN_DIGITS, "0123456789")

# Bengali Number Words
_BN_ONES = [
    "শূন্য",
    "এক",
    "দুই",
    "তিন",
    "চার",
    "পাঁচ",
    "ছয়",
    "সাত",
    "আট",
    "নয়",
    "দশ",
    "এগারো",
    "বারো",
    "তেরো",
    "চৌদ্দ",
    "পনেরো",
    "ষোলো",
    "সতেরো",
    "আঠারো",
    "উনিশ",
    "বিশ",
    "একুশ",
    "বাইশ",
    "তেইশ",
    "চব্বিশ",
    "পঁচিশ",
    "ছাব্বিশ",
    "সাতাশ",
    "আঠাশ",
    "ঊনত্রিশ",
    "ত্রিশ",
    "একত্রিশ",
    "বত্রিশ",
    "তেত্রিশ",
    "চৌত্রিশ",
    "পঁয়ত্রিশ",
    "ছত্রিশ",
    "সাঁইত্রিশ",
    "আটত্রিশ",
    "ঊনচল্লিশ",
    "চল্লিশ",
    "একচল্লিশ",
    "বিয়াল্লিশ",
    "তেতাল্লিশ",
    "চুয়াল্লিশ",
    "পঁয়তাল্লিশ",
    "ছেচল্লিশ",
    "সাতচল্লিশ",
    "আটচল্লিশ",
    "ঊনপঞ্চাশ",
    "পঞ্চাশ",
    "একান্ন",
    "বায়ান্ন",
    "তিপ্পান্ন",
    "চুয়ান্ন",
    "পঞ্চান্ন",
    "ছাপ্পান্ন",
    "সাতান্ন",
    "আটান্ন",
    "ঊনষাট",
    "ষাট",
    "একষট্টি",
    "বাষট্টি",
    "তেষট্টি",
    "চৌষট্টি",
    "পঁয়ষট্টি",
    "ছেষট্টি",
    "সাতষট্টি",
    "আটষট্টি",
    "ঊনসত্তর",
    "সত্তর",
    "একাত্তর",
    "বাহাত্তর",
    "তিয়াত্তর",
    "চুয়াত্তর",
    "পঁচাত্তর",
    "ছিয়াত্তর",
    "সাতাত্তর",
    "আটাত্তর",
    "ঊনআশি",
    "আশি",
    "একাশি",
    "বিরাশি",
    "তিরাশি",
    "চুরাশি",
    "পঁচাশি",
    "ছিয়াশি",
    "সাতাশি",
    "আটাশি",
    "ঊননব্বই",
    "নব্বই",
    "একানব্বই",
    "বানব্বই",
    "তিরানব্বই",
    "চুরানব্বই",
    "পঁচানব্বই",
    "ছিয়ানব্বই",
    "সাতানব্বই",
    "আটানব্বই",
    "নিরানব্বই",
]

# English Number Words
_EN_ONES = [
    "zero",
    "one",
    "two",
    "three",
    "four",
    "five",
    "six",
    "seven",
    "eight",
    "nine",
    "ten",
    "eleven",
    "twelve",
    "thirteen",
    "fourteen",
    "fifteen",
    "sixteen",
    "seventeen",
    "eighteen",
    "nineteen",
]
_EN_TENS = ["", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety"]


def to_bangla_digits(val: int | float | str) -> str:
    """Converts ASCII digits to Bengali digits."""
    return str(val).translate(_EN_TO_BN_TRANS)


def to_ascii_digits(val: int | float | str) -> str:
    """Converts Bengali digits to ASCII digits."""
    return str(val).translate(_BN_TO_EN_TRANS)


def parse_numeric_amount(val: int | float | str) -> int:
    """Extracts integer value from various string formats (supports commas, currency symbols, BN/EN digits)."""
    if isinstance(val, (int, float)):
        return int(val)
    raw = str(val).strip()
    raw = to_ascii_digits(raw)
    cleaned = re.sub(r"[^\d.]", "", raw)
    if not cleaned:
        return 0
    return int(float(cleaned))


def number_to_bangla_words(number: int) -> str:
    """Converts integer number up to 99,99,99,999 to Bengali words (Indian numbering system)."""
    if number == 0:
        return "শূন্য"
    if number < 0:
        return "মাইনাস " + number_to_bangla_words(abs(number))

    parts: list[str] = []

    # কোটি (Crore) - 10,000,000
    crore = number // 10000000
    remainder = number % 10000000
    if crore > 0:
        parts.append(f"{number_to_bangla_words(crore)} কোটি")

    # লাখ (Lakh) - 100,000
    lakh = remainder // 100000
    remainder = remainder % 100000
    if lakh > 0:
        parts.append(f"{_BN_ONES[lakh]} লাখ")

    # হাজার (Thousand) - 1,000
    thousand = remainder // 1000
    remainder = remainder % 1000
    if thousand > 0:
        parts.append(f"{_BN_ONES[thousand]} হাজার")

    # শত (Hundred) - 100
    hundred = remainder // 100
    remainder = remainder % 100
    if hundred > 0:
        parts.append(f"{_BN_ONES[hundred]} শত")

    # অবশিষ্ট (1-99)
    if remainder > 0:
        parts.append(_BN_ONES[remainder])

    return " ".join(parts)


def number_to_english_words(number: int) -> str:
    """Converts integer number up to 999,999,999 to English words."""
    if number == 0:
        return "zero"
    if number < 0:
        return "minus " + number_to_english_words(abs(number))

    def _convert_hundred(n: int) -> str:
        res = []
        if n >= 100:
            res.append(_EN_ONES[n // 100] + " hundred")
            n %= 100
        if n >= 20:
            tens_word = _EN_TENS[n // 10]
            ones = n % 10
            if ones > 0:
                res.append(f"{tens_word}-{_EN_ONES[ones]}")
            else:
                res.append(tens_word)
        elif n > 0:
            res.append(_EN_ONES[n])
        return " and ".join(res) if len(res) > 1 and "hundred" in res[0] else " ".join(res)

    parts: list[str] = []
    billions = number // 1000000000
    remainder = number % 1000000000
    if billions > 0:
        parts.append(f"{_convert_hundred(billions)} billion")

    millions = remainder // 1000000
    remainder = remainder % 1000000
    if millions > 0:
        parts.append(f"{_convert_hundred(millions)} million")

    thousands = remainder // 1000
    remainder = remainder % 1000
    if thousands > 0:
        parts.append(f"{_convert_hundred(thousands)} thousand")

    if remainder > 0:
        parts.append(_convert_hundred(remainder))

    return " ".join(parts)


def normalize_words_text(text: str) -> str:
    """Normalizes word string by stripping punctuation, extra spaces, and common currency words."""
    cleaned = text.lower().strip()
    cleaned = re.sub(r"[,\-./()।]", " ", cleaned)
    # Remove currency words
    cleaned = re.sub(r"\b(টাকা|টাকায়|taka|bdt|only|মাত্র)\b", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def verify_numeral_word_consistency(
    numeric_amount: int | float | str, words_input: str
) -> Tuple[bool, str]:
    """
    Validates whether the words description matches the numeric amount (AC-M05-5).
    Supports both Bengali and English descriptions.
    Returns (is_valid, message).
    """
    amt = parse_numeric_amount(numeric_amount)
    if amt <= 0 and not words_input:
        return True, ""

    if not words_input or not words_input.strip():
        return False, "টাকার পরিমাণ কথায় লেখা আবশ্যক।"

    bn_expected = number_to_bangla_words(amt)
    en_expected = number_to_english_words(amt)

    norm_input = normalize_words_text(words_input)
    norm_bn = normalize_words_text(bn_expected)
    norm_en = normalize_words_text(en_expected)

    # Alternative spellings in Bengali (লাখ vs লক্ষ, বিশ vs কুড়ি, শত vs একশত)
    norm_bn_alt = norm_bn.replace("লাখ", "লক্ষ").replace("শত", "একশত")
    norm_input_alt = norm_input.replace("লাখ", "লক্ষ").replace("শত", "একশত")

    # Check match against Bengali expected
    if norm_input == norm_bn or norm_input_alt == norm_bn_alt:
        return True, ""

    # Check match against English expected
    if norm_input == norm_en or norm_input.replace("-", " ") == norm_en.replace("-", " "):
        return True, ""

    # If the words input contains the major components (e.g. "পঞ্চাশ হাজার")
    if all(part in norm_input for part in norm_bn.split() if part not in ("এক",)):
        return True, ""
    if all(part in norm_input for part in norm_en.split() if part not in ("and", "one")):
        return True, ""

    # Check for direct discrepancy/mismatch
    return False, (
        f"সংখ্যার সাথে কথায় লেখার অমিল রয়েছে: {numeric_amount} (কথায় প্রত্যাশিত: "
        f"'{bn_expected} টাকা' অথবা '{en_expected.title()} Taka', প্রদত্ত: '{words_input}')"
    )
