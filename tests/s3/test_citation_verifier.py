"""
Unit and Integration Tests for Citation Verifier (SRS Section 4.3, 8.4, 9.3 S3).
Proves:
1. Exact verbatim citation match returns status VERIFIED, match_score 1.0, is_verbatim True.
2. Normalized citation match handles whitespace and punctuation differences.
3. Contradicted citation detects significant distortion or negation.
4. Unverified status returned when claim text cannot be found.
5. Draft / unapproved source versions are rejected.
6. Superseded versions are rejected when evaluated against an as-of date after their validity period.
"""

import pytest

from packages.trust_kernel.citation_verifier import CitationVerifier
from packages.trust_kernel.source_registry import SourceRegistryService


@pytest.fixture
def mock_registry():
    registry = SourceRegistryService()
    # Ensure test source exists
    source_id = registry.create_source(
        {
            "title": "বাড়িভাড়া নিয়ন্ত্রণ আইন ১৯৯১",
            "title_bn": "বাড়িভাড়া নিয়ন্ত্রণ আইন ১৯৯১",
            "source_type": "statute",
            "authority": "সংসদ",
            "source_label": "FAKE_TEST_DATA",
        }
    )
    v1_id = registry.add_version(
        source_id=source_id,
        file_content="ধারা ৭: কোনো ব্যক্তি বাড়িভাড়া বাবদ এক মাসের ভাড়ার অধিক জামানত দাবি করতে পারবেন না।",
        effective_from="1991-01-01",
        effective_to="2020-12-31",
        version_label="1.0",
        uploader_id="usr-uploader-1",
    )
    registry.approve(
        version_id=v1_id,
        reviewer_id="usr-reviewer-2",
        approval_notes="Approved for test verification.",
    )

    # v2 superseding v1 from 2021-01-01 onwards
    v2_id = registry.add_version(
        source_id=source_id,
        file_content="ধারা ৭: কোনো ব্যক্তি বাড়িভাড়া বাবদ দুই মাসের ভাড়ার অধিক জামানত দাবি করতে পারবেন না।",
        effective_from="2021-01-01",
        effective_to=None,
        version_label="2.0",
        uploader_id="usr-uploader-1",
    )
    registry.approve(
        version_id=v2_id, reviewer_id="usr-reviewer-2", approval_notes="Approved amendment."
    )

    # Draft unapproved version
    v_draft_id = registry.add_version(
        source_id=source_id,
        file_content="ধারা ৭: খসড়া প্রস্তাবনা",
        effective_from="2027-01-01",
        version_label="3.0-draft",
        uploader_id="usr-uploader-1",
    )

    return {
        "registry": registry,
        "source_id": source_id,
        "v1_id": v1_id,
        "v2_id": v2_id,
        "v_draft_id": v_draft_id,
    }


def test_verbatim_citation_match(mock_registry):
    """Verbatim exact quote returns status VERIFIED with score 1.0 and is_verbatim True."""
    verifier = CitationVerifier(registry=mock_registry["registry"])
    report = verifier.verify(
        claim_text="কোনো ব্যক্তি বাড়িভাড়া বাবদ দুই মাসের ভাড়ার অধিক জামানত দাবি করতে পারবেন না।",
        source_id=mock_registry["source_id"],
        source_version_id=mock_registry["v2_id"],
        as_of_date="2026-10-02",
    )
    assert report.status == "VERIFIED"
    assert report.match_score == 1.0
    assert report.is_verbatim is True
    assert report.verified_span is not None


def test_normalized_citation_match(mock_registry):
    """Slight whitespace and quote variation still verifies successfully."""
    verifier = CitationVerifier(registry=mock_registry["registry"])
    report = verifier.verify(
        claim_text="  কোনো  ব্যক্তি  বাড়িভাড়া   বাবদ দুই মাসের ভাড়ার অধিক জামানত দাবি করতে পারবেন না।  ",
        source_id=mock_registry["source_id"],
        source_version_id=mock_registry["v2_id"],
        as_of_date="2026-10-02",
    )
    assert report.status == "VERIFIED"
    assert report.match_score >= 0.95


def test_contradicted_citation_mismatch(mock_registry):
    """Distorted claim (e.g. claim saying 1 month when law says 2 months) is flagged."""
    verifier = CitationVerifier(registry=mock_registry["registry"])
    report = verifier.verify(
        claim_text="কোনো ব্যক্তি বাড়িভাড়া বাবদ পাঁচ মাসের ভাড়ার জামানত নিতে পারবেন।",
        source_id=mock_registry["source_id"],
        source_version_id=mock_registry["v2_id"],
        as_of_date="2026-10-02",
    )
    assert report.status in ("CONTRADICTED", "UNVERIFIED")
    assert report.match_score < 0.85


def test_negative_draft_unapproved_version_citation_rejected(mock_registry):
    """Citations pointing to draft or unapproved source versions are rejected."""
    verifier = CitationVerifier(registry=mock_registry["registry"])
    report = verifier.verify(
        claim_text="ধারা ৭: খসড়া প্রস্তাবনা",
        source_id=mock_registry["source_id"],
        source_version_id=mock_registry["v_draft_id"],
    )
    assert report.status == "UNVERIFIED"
    assert report.as_of_valid is False
    assert any("not approved" in d for d in report.discrepancies)


def test_negative_superseded_version_citation_rejected_for_as_of_date(mock_registry):
    """Citing an old version with an as-of date after its effective_to returns SUPERSEDED."""
    verifier = CitationVerifier(registry=mock_registry["registry"])
    report = verifier.verify(
        claim_text="কোনো ব্যক্তি বাড়িভাড়া বাবদ এক মাসের ভাড়ার অধিক জামানত দাবি করতে পারবেন না।",
        source_id=mock_registry["source_id"],
        source_version_id=mock_registry["v1_id"],
        as_of_date="2026-10-02",  # v1 expired on 2020-12-31
    )
    assert report.status == "SUPERSEDED"
    assert report.as_of_valid is False
    assert any("superseded" in d for d in report.discrepancies)


def test_rule_b03_citation_nonexistent_source_or_passage_rejected(mock_registry):
    """
    Rule B3: Citation verifier rejects citations to non-existent sources or passages.
    """
    verifier = CitationVerifier(registry=mock_registry["registry"])

    # 1. Non-existent source
    rep1 = verifier.verify(
        claim_text="ধারা ১: সংক্ষিপ্ত শিরোনাম",
        source_id="nonexistent-src-999",
        source_version_id=mock_registry["v1_id"],
    )
    assert rep1.status == "UNVERIFIED"
    assert rep1.as_of_valid is False
    assert any("does not exist" in d for d in rep1.discrepancies)

    # 2. Non-existent source version
    rep2 = verifier.verify(
        claim_text="ধারা ১: সংক্ষিপ্ত শিরোনাম",
        source_id=mock_registry["source_id"],
        source_version_id="nonexistent-ver-999",
    )
    assert rep2.status == "UNVERIFIED"
    assert rep2.as_of_valid is False
    assert any("does not exist" in d for d in rep2.discrepancies)

    # 3. Non-existent passage section reference
    rep3 = verifier.verify(
        claim_text="ধারা ৯৯: কোনো অধিকার নেই",
        source_id=mock_registry["source_id"],
        source_version_id=mock_registry["v1_id"],
        section_ref="ধারা ৯৯",
    )
    assert rep3.status == "UNVERIFIED"
    assert any("does not exist" in d for d in rep3.discrepancies)


def test_rule_b03_citation_digits_normalization_and_number_mismatch_rejected(mock_registry):
    """
    Rule B3:
    1. Bangla vs English digits equivalence: 'ধারা ৭' and 'ধারা 7' match canonically.
    2. Changed number rejection: If a statutory number or date is altered (e.g. 60 vs 70),
       it is strictly rejected as CONTRADICTED.
    """
    verifier = CitationVerifier(registry=mock_registry["registry"])

    # Statutory text in mock source v2 contains:
    # "ধারা ৭: কোনো ব্যক্তি বাড়িভাড়া বাবদ দুই মাসের ভাড়ার অধিক জামানত দাবি করতে পারবেন না।"
    # 1. Test digit equivalence: English digit "7" matches Bengali digit "৭"
    rep_digits = verifier.verify(
        claim_text="ধারা 7: কোনো ব্যক্তি বাড়িভাড়া বাবদ দুই মাসের ভাড়ার অধিক জামানত দাবি করতে পারবেন না।",
        source_id=mock_registry["source_id"],
        source_version_id=mock_registry["v2_id"],
        as_of_date="2026-10-02",
    )
    assert rep_digits.status == "VERIFIED"
    assert rep_digits.match_score >= 0.95

    # 2. Test altered number: passage has 60 bigha, claim changes to 70 bigha
    passage_text = "কোনো ব্যক্তি বা পরিবার ৬০ বিঘার অতিরিক্ত কৃষি জমি দখলে রাখতে পারিবেন না।"
    rep_number_changed = verifier.verify(
        claim_text="কোনো ব্যক্তি বা পরিবার ৭০ বিঘার অতিরিক্ত কৃষি জমি দখলে রাখতে পারিবেন না।",
        source_id=mock_registry["source_id"],
        source_version_id=mock_registry["v2_id"],
        passage_text=passage_text,
        as_of_date="2026-10-02",
    )
    assert rep_number_changed.status == "CONTRADICTED"
    assert rep_number_changed.match_score == 0.0
    assert any("Numeric mismatch" in d for d in rep_number_changed.discrepancies)


def test_rule_b03_citation_negation_added_or_removed_not_verified(mock_registry):
    """
    Rule B3: Negation added or removed ('পারবেন না' vs 'পারবেন') must strictly NOT be VERIFIED.
    Case (a1): Negation removed from claim (statute says 'পারবেন না', claim says 'পারবেন').
    Case (a2): Negation added to claim (statute says 'পারবেন', claim says 'পারবেন না').
    Both must be flagged as CONTRADICTED and NEVER VERIFIED.
    """
    verifier = CitationVerifier(registry=mock_registry["registry"])
    passage = "ধারা ৭: কোনো ব্যক্তি বাড়িভাড়া বাবদ দুই মাসের ভাড়ার অধিক জামানত দাবি করতে পারবেন না।"

    # Case a1: Negation removed ('পারবেন না' -> 'পারবেন')
    rep_neg_removed = verifier.verify(
        claim_text="কোনো ব্যক্তি বাড়িভাড়া বাবদ দুই মাসের ভাড়ার অধিক জামানত দাবি করতে পারবেন।",
        source_id=mock_registry["source_id"],
        source_version_id=mock_registry["v2_id"],
        passage_text=passage,
        as_of_date="2026-10-02",
    )
    assert rep_neg_removed.status != "VERIFIED"
    assert rep_neg_removed.status == "CONTRADICTED"
    assert rep_neg_removed.is_verbatim is False

    # Case a2: Negation added ('পারবেন' -> 'পারবেন না')
    passage_affirmative = "ধারা ৮: সকল নাগরিক যথাযথ প্রতিকার দাবি করতে পারবেন।"
    rep_neg_added = verifier.verify(
        claim_text="সকল নাগরিক যথাযথ প্রতিকার দাবি করতে পারবেন না।",
        source_id=mock_registry["source_id"],
        source_version_id=mock_registry["v2_id"],
        passage_text=passage_affirmative,
        as_of_date="2026-10-02",
    )
    assert rep_neg_added.status != "VERIFIED"
    assert rep_neg_added.status == "CONTRADICTED"
    assert rep_neg_added.is_verbatim is False


def test_rule_b03_citation_opposite_keyword_swapped_not_verified(mock_registry):
    """
    Rule B3: Swapping a key word for its opposite (e.g. 'নিষিদ্ধ' vs 'অনুমোদিত')
    must strictly NOT be VERIFIED (must be CONTRADICTED).
    """
    verifier = CitationVerifier(registry=mock_registry["registry"])
    passage = "ধারা ১২: আবাসিক এলাকায় বাণিজ্যিক স্থাপনা নির্মাণ সম্পূর্ণ নিষিদ্ধ।"

    rep_opposite = verifier.verify(
        claim_text="আবাসিক এলাকায় বাণিজ্যিক স্থাপনা নির্মাণ সম্পূর্ণ অনুমোদিত।",
        source_id=mock_registry["source_id"],
        source_version_id=mock_registry["v2_id"],
        passage_text=passage,
        as_of_date="2026-10-02",
    )
    assert rep_opposite.status != "VERIFIED"
    assert rep_opposite.status == "CONTRADICTED"
    assert any("Semantic contradiction" in d for d in rep_opposite.discrepancies)


def test_rule_b03_citation_dropped_word_fuzzy_score_not_verified(mock_registry):
    """
    Rule B3: A match score >= 0.95 due to a dropped word must NOT make a citation VERIFIED on its own.
    Only exact normalized match counts as VERIFIED. Anything fuzzy is 'NEEDS_REVIEW'.
    """
    verifier = CitationVerifier(registry=mock_registry["registry"])
    # Target: "ধারা ৭: কোনো ব্যক্তি বাড়িভাড়া বাবদ দুই মাসের ভাড়ার অধিক জামানত দাবি করতে পারবেন না।"
    # Claim drops one single word "ভাড়ার":
    claim_with_dropped_word = "কোনো ব্যক্তি বাড়িভাড়া বাবদ দুই মাসের অধিক জামানত দাবি করতে পারবেন না।"

    rep_dropped = verifier.verify(
        claim_text=claim_with_dropped_word,
        source_id=mock_registry["source_id"],
        source_version_id=mock_registry["v2_id"],
        as_of_date="2026-10-02",
    )
    assert rep_dropped.status != "VERIFIED"
    assert rep_dropped.status == "NEEDS_REVIEW"
    assert rep_dropped.match_score >= 0.60
    assert any(
        "fuzzy" in d.lower() or "human review" in d.lower() for d in rep_dropped.discrepancies
    )
