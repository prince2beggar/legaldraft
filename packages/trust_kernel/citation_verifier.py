"""
Citation Verifier & Deterministic Passage Matcher (SRS Section 4.3, 8.4, 9.3 S3).
Performs deterministic, reproducible verification of citations and claims against
approved statutory source versions and passages.

Safety Guarantees:
1. Rejects unapproved / draft source versions.
2. Rejects superseded versions when checked against an as-of date after their validity period.
3. Produces a structured CitationVerificationReport with match scores, discrepancies, and status.
"""

import difflib
import re
import unicodedata
from dataclasses import asdict, dataclass, field
from typing import Any

from packages.trust_kernel.db import DatabaseManager, db_manager
from packages.trust_kernel.source_registry import SourceRegistryService, source_registry

# Digit mapping: Bangla numerals to ASCII digits
BANGLA_TO_ASCII_DIGITS = str.maketrans("০১২৩৪৫৬৭৮৯", "0123456789")


def canonicalize_digits(text: str) -> str:
    """Maps Bengali numerals to standard ASCII digits 0-9 for semantic digit equivalence."""
    if not text:
        return ""
    return text.translate(BANGLA_TO_ASCII_DIGITS)


def extract_numbers(text: str) -> list[str]:
    """Extracts all numeric sequences (converting Bengali to ASCII) from text."""
    canon = canonicalize_digits(text)
    return re.findall(r"\d+", canon)


def normalize_legal_text(text: str, map_digits: bool = True) -> str:
    """
    Applies exact, deterministic legal text normalization:
    1. Unicode normalization: NFKC canonical decomposition & composition.
    2. Whitespace normalization: Stripping leading/trailing whitespace, converting runs of spaces, tabs,
       newlines, non-breaking spaces (\u00a0), and zero-width spaces (\u200b) to a single ASCII space ' '.
    3. Punctuation standardization: Normalizing quotation marks (“ ” ‘ ’ -> " '), dashes (– — -> -).
       Preserves Bengali danda (।) and periods/commas.
    4. Digit Canonicalization: Maps Bengali digits (০-৯) to ASCII digits (0-9)
       to allow cross-script equivalence (e.g. 'ধারা ৭' == 'ধারা 7').

    SAFETY RULE: Normalization NEVER blurs distinct numbers. 7 is never equal to 8.
    """
    if not text:
        return ""
    # 1. Unicode NFKC normalization
    norm = unicodedata.normalize("NFKC", text)
    # 2. Whitespace normalization
    norm = re.sub(r"[\s\u200b\u00a0]+", " ", norm).strip()
    # 3. Punctuation standardization
    norm = (
        norm.replace("“", '"')
        .replace("”", '"')
        .replace("‘", "'")
        .replace("’", "'")
        .replace("–", "-")
        .replace("—", "-")
    )
    # 4. Canonicalize numerals
    if map_digits:
        norm = norm.translate(BANGLA_TO_ASCII_DIGITS)
    return norm


@dataclass
class CitationVerificationReport:
    claim: str
    source_id: str
    source_version_id: str
    section_ref: str | None
    status: str  # "VERIFIED", "UNVERIFIED", "CONTRADICTED", "SUPERSEDED"
    match_score: float
    verified_span: str | None
    discrepancies: list[str] = field(default_factory=list)
    is_verbatim: bool = False
    as_of_valid: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class CitationVerifier:
    def __init__(
        self,
        db: DatabaseManager | None = None,
        registry: SourceRegistryService | None = None,
    ):
        self.db = db or db_manager
        self.registry = registry or source_registry

    def verify(
        self,
        claim_text: str,
        source_id: str,
        source_version_id: str,
        section_ref: str | None = None,
        passage_text: str | None = None,
        as_of_date: str | None = None,
    ) -> CitationVerificationReport:
        """
        Verifies a cited legal statement or quote against the source passage.
        """
        discrepancies: list[str] = []
        claim_clean = claim_text.strip()
        if not claim_clean:
            return CitationVerificationReport(
                claim=claim_text,
                source_id=source_id,
                source_version_id=source_version_id,
                section_ref=section_ref,
                status="UNVERIFIED",
                match_score=0.0,
                verified_span=None,
                discrepancies=["Empty claim provided."],
                is_verbatim=False,
            )

        # 1. Fetch source and version records and check approval / temporal validity
        source_record = self.db.get_source(source_id)
        if not source_record:
            return CitationVerificationReport(
                claim=claim_text,
                source_id=source_id,
                source_version_id=source_version_id,
                section_ref=section_ref,
                status="UNVERIFIED",
                match_score=0.0,
                verified_span=None,
                discrepancies=[f"Source '{source_id}' does not exist."],
                is_verbatim=False,
                as_of_valid=False,
            )

        version_record = self.db.get_source_version(source_version_id)
        if not version_record:
            return CitationVerificationReport(
                claim=claim_text,
                source_id=source_id,
                source_version_id=source_version_id,
                section_ref=section_ref,
                status="UNVERIFIED",
                match_score=0.0,
                verified_span=None,
                discrepancies=[f"Source version '{source_version_id}' does not exist."],
                is_verbatim=False,
                as_of_valid=False,
            )

        if version_record.get("status") != "approved":
            return CitationVerificationReport(
                claim=claim_text,
                source_id=source_id,
                source_version_id=source_version_id,
                section_ref=section_ref,
                status="UNVERIFIED",
                match_score=0.0,
                verified_span=None,
                discrepancies=[
                    f"Source version status is '{version_record.get('status')}', not approved."
                ],
                is_verbatim=False,
                as_of_valid=False,
            )

        # Check temporal applicability if as_of_date provided
        if as_of_date:
            eff_from = version_record.get("effective_from", "")
            eff_to = version_record.get("effective_to")
            if as_of_date < eff_from:
                return CitationVerificationReport(
                    claim=claim_text,
                    source_id=source_id,
                    source_version_id=source_version_id,
                    section_ref=section_ref,
                    status="UNVERIFIED",
                    match_score=0.0,
                    verified_span=None,
                    discrepancies=[f"As-of date {as_of_date} precedes effective_from {eff_from}."],
                    is_verbatim=False,
                    as_of_valid=False,
                )
            if eff_to and as_of_date > eff_to:
                return CitationVerificationReport(
                    claim=claim_text,
                    source_id=source_id,
                    source_version_id=source_version_id,
                    section_ref=section_ref,
                    status="SUPERSEDED",
                    match_score=0.0,
                    verified_span=None,
                    discrepancies=[
                        f"Version superseded on {eff_to}; as-of date {as_of_date} is later."
                    ],
                    is_verbatim=False,
                    as_of_valid=False,
                )

        # 2. Obtain passage text
        target_text = passage_text
        if not target_text:
            passages = self.db.get_source_passages(source_version_id)
            if section_ref:
                matched_p = [p for p in passages if p.get("section_ref") == section_ref]
                if matched_p:
                    target_text = " ".join([p["text"] for p in matched_p])
                else:
                    return CitationVerificationReport(
                        claim=claim_text,
                        source_id=source_id,
                        source_version_id=source_version_id,
                        section_ref=section_ref,
                        status="UNVERIFIED",
                        match_score=0.0,
                        verified_span=None,
                        discrepancies=[
                            f"Passage for section '{section_ref}' does not exist in version '{source_version_id}'."
                        ],
                        is_verbatim=False,
                        as_of_valid=True,
                    )
            elif passages:
                target_text = " ".join([p["text"] for p in passages])

        if not target_text:
            return CitationVerificationReport(
                claim=claim_text,
                source_id=source_id,
                source_version_id=source_version_id,
                section_ref=section_ref,
                status="UNVERIFIED",
                match_score=0.0,
                verified_span=None,
                discrepancies=["No passage text found for specified source and section."],
                is_verbatim=False,
            )

        # Numeric mismatch check:
        # If claim contains numbers not present in target text, reject as CONTRADICTED immediately.
        claim_nums = extract_numbers(claim_clean)
        target_nums = extract_numbers(target_text)
        missing_nums = [n for n in claim_nums if n not in target_nums]
        if missing_nums:
            return CitationVerificationReport(
                claim=claim_text,
                source_id=source_id,
                source_version_id=source_version_id,
                section_ref=section_ref,
                status="CONTRADICTED",
                match_score=0.0,
                verified_span=None,
                discrepancies=[
                    f"Numeric mismatch: claim contains number(s) {missing_nums} not found in cited passage. "
                    f"Changing statutory numbers or dates is strictly rejected."
                ],
                is_verbatim=False,
                as_of_valid=True,
            )

        # Test 3: Deterministic & Semantic Matching

        # 3a. Unicode-safe Bengali and English tokenization
        def tokenize_words(text: str) -> set[str]:
            tokens = set()
            for w in text.split():
                clean = w.strip("।,.:;!?'\"()[]{}–-— \t\r\n")
                if clean:
                    tokens.add(clean)
            return tokens

        negation_tokens = {"না", "নয়", "নহে", "নাই", "নাহ", "not", "no", "never", "cannot"}
        antonym_pairs = [
            ("নিষিদ্ধ", "অনুমোদিত"),
            ("অনুমোদিত", "নিষিদ্ধ"),
            ("বৈধ", "অবৈধ"),
            ("অবৈধ", "বৈধ"),
            ("বাধ্যতামূলক", "ঐচ্ছিক"),
            ("ঐচ্ছিক", "বাধ্যতামূলক"),
            ("দণ্ডনীয়", "অদণ্ডনীয়"),
            ("অদণ্ডনীয়", "দণ্ডনীয়"),
            ("শাস্তিযোগ্য", "অশাস্তিযোগ্য"),
            ("অশাস্তিযোগ্য", "শাস্তিযোগ্য"),
            ("দায়বদ্ধ", "দায়মুক্ত"),
            ("দায়মুক্ত", "দায়বদ্ধ"),
            ("অধিকার", "অনধিকার"),
            ("অনধিকার", "অধিকার"),
            ("prohibited", "permitted"),
            ("permitted", "prohibited"),
            ("lawful", "unlawful"),
            ("unlawful", "lawful"),
            ("mandatory", "optional"),
            ("optional", "mandatory"),
        ]

        norm_claim = normalize_legal_text(claim_clean)
        norm_target = normalize_legal_text(target_text)

        claim_words = tokenize_words(norm_claim)
        target_words = tokenize_words(norm_target)

        # Check for antonym/opposite keyword swap across passage
        for w1, w2 in antonym_pairs:
            if w1 in claim_words and w2 in target_words:
                return CitationVerificationReport(
                    claim=claim_text,
                    source_id=source_id,
                    source_version_id=source_version_id,
                    section_ref=section_ref,
                    status="CONTRADICTED",
                    match_score=0.0,
                    verified_span=None,
                    discrepancies=[
                        f"Semantic contradiction: claim contains '{w1}' whereas statutory passage contains '{w2}'."
                    ],
                    is_verbatim=False,
                    as_of_valid=True,
                )

        claim_has_neg = any(w in negation_tokens for w in claim_words)
        target_has_neg = any(w in negation_tokens for w in target_words)

        # Helper to check if a substring occurrence in target is immediately followed or preceded by a negation
        def is_negated_in_context(target: str, sub: str) -> bool:
            pattern_after = re.escape(sub) + r"\s+(না|নয়|নহে|নাই|নাহ)\b"
            pattern_before = r"\b(না|নয়|নহে|নাই|নাহ)\s+" + re.escape(sub)
            return bool(re.search(pattern_after, target) or re.search(pattern_before, target))

        # Test 3b: Exact Verbatim Match
        if claim_clean in target_text:
            if not claim_has_neg and is_negated_in_context(target_text, claim_clean):
                return CitationVerificationReport(
                    claim=claim_text,
                    source_id=source_id,
                    source_version_id=source_version_id,
                    section_ref=section_ref,
                    status="CONTRADICTED",
                    match_score=0.0,
                    verified_span=None,
                    discrepancies=[
                        "Negation mismatch: claim dropped the negation present in the statutory context."
                    ],
                    is_verbatim=False,
                    as_of_valid=True,
                )
            return CitationVerificationReport(
                claim=claim_text,
                source_id=source_id,
                source_version_id=source_version_id,
                section_ref=section_ref,
                status="VERIFIED",
                match_score=1.0,
                verified_span=claim_clean,
                discrepancies=[],
                is_verbatim=True,
                as_of_valid=True,
            )

        # Test 3c: Normalized Substring Match
        if norm_claim in norm_target:
            if not claim_has_neg and is_negated_in_context(norm_target, norm_claim):
                return CitationVerificationReport(
                    claim=claim_text,
                    source_id=source_id,
                    source_version_id=source_version_id,
                    section_ref=section_ref,
                    status="CONTRADICTED",
                    match_score=0.0,
                    verified_span=None,
                    discrepancies=[
                        "Negation mismatch: claim dropped the negation present in the statutory context."
                    ],
                    is_verbatim=False,
                    as_of_valid=True,
                )
            return CitationVerificationReport(
                claim=claim_text,
                source_id=source_id,
                source_version_id=source_version_id,
                section_ref=section_ref,
                status="VERIFIED",
                match_score=1.0,
                verified_span=norm_claim,
                discrepancies=["Minor whitespace or punctuation differences."],
                is_verbatim=False,
                as_of_valid=True,
            )

        # Test 3d: Fuzzy Sequence Matcher across full text
        seq_matcher = difflib.SequenceMatcher(None, norm_claim, norm_target)
        matching_blocks = [m for m in seq_matcher.get_matching_blocks() if m.size > 0]

        if matching_blocks:
            first_b = matching_blocks[0].b
            last_b = matching_blocks[-1].b + matching_blocks[-1].size
            matched_span = norm_target[first_b:last_b]
            total_matching_chars = sum(m.size for m in matching_blocks)
            score = round(min(1.0, total_matching_chars / len(norm_claim)), 2)
        else:
            matched_span = None
            score = 0.0

        # If negation differs between claim and target passage, flag as CONTRADICTED
        if claim_has_neg != target_has_neg and score >= 0.50:
            return CitationVerificationReport(
                claim=claim_text,
                source_id=source_id,
                source_version_id=source_version_id,
                section_ref=section_ref,
                status="CONTRADICTED",
                match_score=0.0,
                verified_span=matched_span,
                discrepancies=[
                    "Negation mismatch: negation was added or removed between claim and statutory passage."
                ],
                is_verbatim=False,
                as_of_valid=True,
            )

        # STRICT RULE: A match score >= 0.95 must NOT make a citation "VERIFIED" on its own.
        # Only an exact match after documented normalisation counts as VERIFIED.
        # Anything fuzzy is "NEEDS_REVIEW".
        if score >= 0.60:
            status = "NEEDS_REVIEW"
            discrepancies.append(
                f"Fuzzy match detected with {int(score * 100)}% span overlap. "
                f"Requires human review (fuzzy matches are never auto-verified)."
            )
        elif score >= 0.35:
            status = "CONTRADICTED"
            discrepancies.append(
                f"Significant difference: only {int(score * 100)}% span overlap with cited text."
            )
        else:
            status = "UNVERIFIED"
            discrepancies.append("Claim text was not found in the referenced statutory passage.")

        return CitationVerificationReport(
            claim=claim_text,
            source_id=source_id,
            source_version_id=source_version_id,
            section_ref=section_ref,
            status=status,
            match_score=score,
            verified_span=matched_span,
            discrepancies=discrepancies,
            is_verbatim=False,
            as_of_valid=True,
        )

    def verify_span(
        self,
        claim_text: str,
        document_text: str,
        span_ref: dict[str, Any] | None = None,
    ) -> CitationVerificationReport:
        """
        Verifies a claim directly against an OCR text span from the document (SRS M04).
        """
        norm_claim = normalize_legal_text(claim_text)
        norm_doc = normalize_legal_text(document_text)

        if not norm_claim:
            return CitationVerificationReport(
                claim=claim_text,
                source_id="document",
                source_version_id="ocr",
                section_ref=None,
                status="UNVERIFIED",
                match_score=0.0,
                verified_span=None,
                discrepancies=["Empty claim."],
            )

        # Check exact substring in document
        if norm_claim in norm_doc:
            return CitationVerificationReport(
                claim=claim_text,
                source_id="document",
                source_version_id="ocr",
                section_ref=None,
                status="VERIFIED",
                match_score=1.0,
                verified_span=claim_text,
                is_verbatim=True,
                as_of_valid=True,
            )

        # If span_ref with start and end is provided, check the specific span
        if span_ref and "start" in span_ref and "end" in span_ref:
            start = int(span_ref["start"])
            end = int(span_ref["end"])
            if 0 <= start < end <= len(document_text):
                target_span = document_text[start:end]
                norm_target = normalize_legal_text(target_span)
                if norm_claim == norm_target or norm_claim in norm_target:
                    return CitationVerificationReport(
                        claim=claim_text,
                        source_id="document",
                        source_version_id="ocr",
                        section_ref=None,
                        status="VERIFIED",
                        match_score=1.0,
                        verified_span=target_span,
                        is_verbatim=True,
                        as_of_valid=True,
                    )

        # Check token / keyword coverage
        claim_words = set(re.findall(r"\w+", norm_claim))
        doc_words = set(re.findall(r"\w+", norm_doc))
        if claim_words and claim_words.issubset(doc_words):
            return CitationVerificationReport(
                claim=claim_text,
                source_id="document",
                source_version_id="ocr",
                section_ref=None,
                status="VERIFIED",
                match_score=0.98,
                verified_span=claim_text,
                is_verbatim=False,
                as_of_valid=True,
            )

        # Fallback to difflib matcher
        matcher = difflib.SequenceMatcher(None, norm_claim, norm_doc)
        match = matcher.find_longest_match(0, len(norm_claim), 0, len(norm_doc))
        if match.size >= len(norm_claim) * 0.7:
            return CitationVerificationReport(
                claim=claim_text,
                source_id="document",
                source_version_id="ocr",
                section_ref=None,
                status="NEEDS_REVIEW",
                match_score=match.size / len(norm_claim),
                verified_span=document_text[match.b : match.b + match.size],
                discrepancies=["Fuzzy match in document text."],
            )

        return CitationVerificationReport(
            claim=claim_text,
            source_id="document",
            source_version_id="ocr",
            section_ref=None,
            status="UNVERIFIED",
            match_score=0.0,
            verified_span=None,
            discrepancies=["Claim not found in document text."],
        )


citation_verifier = CitationVerifier()
