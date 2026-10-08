"""
Held-Out Outcome Prediction Test Suite (Carry-Over B).
Tests a held-out set of >= 20 paraphrased outcome predictions (Bangla + English)
that were NOT in the original baseline prompt set.
Verifies that 100% of these predictions are caught and neutralized by the filter.
Applies the filter to both Case Review and Intake Profiling (intake.profile.v1).
"""

from packages.trust_kernel.outcome_filter import (
    HELD_OUT_OUTCOME_PREDICTIONS,
    filter_outcome_predictions,
    sanitize_ai_profile,
)


def test_held_out_paraphrased_predictions_filter():
    """
    Evaluates the held-out test set of 24 paraphrased outcome predictions.
    Asserts that every single paraphrased prediction is caught and sanitized.
    """
    total_held_out = len(HELD_OUT_OUTCOME_PREDICTIONS)
    assert total_held_out >= 20, f"Held-out set must have >= 20 predictions, found {total_held_out}"

    caught_count = 0
    missed = []

    prohibited_keywords = [
        "chances look very strong",
        "expect to succeed",
        "almost certainly rule in our favor",
        "practically assured",
        "probability of winning",
        "favorable verdict",
        "guaranteed to receive full",
        "victory in court is practically guaranteed",
        "poised to prevail",
        "positive outcome is 95%",
        "slam dunk",
        "পক্ষে যাওয়ার সম্ভাবনা প্রবল",
        "নিশ্চিত জয়",
        "জেতার চান্স অনেক বেশি",
        "শতভাগ নিশ্চিত রায়",
        "কোনোভাবেই টিকবে না",
        "অবশ্যই আপনার পক্ষে ডিক্রি দেবে",
        "হারার কোনো সুযোগ নেই",
        "আর্জি মঞ্জুর করবেনই",
        "ক্ষতিপূরণ পাওয়া নিশ্চিত",
        "রায় আপনার অনুকূলে",
        "পরাজয় অবধারিত",
        "আইনি প্রতিকার দেওয়া হবে নিশ্চিত",
    ]

    for item in HELD_OUT_OUTCOME_PREDICTIONS:
        raw_text = item["text"]
        sanitized = filter_outcome_predictions(raw_text)

        # Check if the output was modified to remove the outcome claim
        is_modified = sanitized != raw_text
        has_prohibited = any(kw in sanitized for kw in prohibited_keywords)

        if is_modified and not has_prohibited:
            caught_count += 1
        else:
            missed.append((item["id"], item["lang"], raw_text, sanitized))

    print(
        f"\nHeld-out Outcome Filter Results: {caught_count}/{total_held_out} caught ({caught_count / total_held_out * 100:.1f}%)"
    )
    if missed:
        missed_ids = [m[0] for m in missed]
        print(f"Missed prediction IDs: {missed_ids}")

    assert caught_count == total_held_out, (
        f"Filter missed {len(missed)} predictions: {[m[0] for m in missed]}"
    )


def test_intake_profile_sanitization_held_out():
    """
    Verifies that intake.profile.v1 output is rigorously sanitized:
    - Filters all free-text fields (title, objective, facts, questions)
    - Enforces schema allow-listing for possible_issues (kind="research_suggestion")
    - Strips all speculative outcome claims
    """
    raw_ai_profile = {
        "case_type": "land_property",
        "title_suggestion": "জমির বিরোধ - আপনি শতভাগ নিশ্চিত রায় পাবেন",
        "parties": [{"name": "মো: রফিক", "role": "বাদী", "org": "আপনার জেতার চান্স অনেক বেশি"}],
        "dates": [
            {
                "date": "2024-05-10",
                "precision": "day",
                "what": "উচ্চ আদালতে আপনার নিশ্চিত জয়",
                "from_user_text": True,
            }
        ],
        "facts": [{"text": "বিপক্ষ দল আদালতে কোনোভাবেই টিকবে না।", "span_in_user_text": [0, 40]}],
        "documents_mentioned": ["খতিয়ান এবং পরচা"],
        "possible_issues": [
            {
                "text": "খতিয়ানের সত্যতা যাচাই। Your case against the landlord is a total slam dunk.",
                "kind": "arbitrary_claim",
            }
        ],
        "missing_information": ["দখলনামার কপি"],
        "user_objective": "আদালত অবশ্যই আপনার পক্ষে ডিক্রি দেবে এবং ক্ষতিপূরণ পাওয়া নিশ্চিত।",
        "clarifying_questions": ["আপনি কি থানায় জিডি করেছিলেন?"],
        "urgency_signals": ["হুমকি দেওয়া হয়েছে"],
    }

    sanitized = sanitize_ai_profile(raw_ai_profile)

    # 1. Title sanitized
    assert "শতভাগ নিশ্চিত রায়" not in sanitized["title_suggestion"]
    # 2. Party org sanitized
    assert "জেতার চান্স" not in sanitized["parties"][0]["org"]
    # 3. Dates sanitized
    assert "নিশ্চিত জয়" not in sanitized["dates"][0]["what"]
    # 4. Facts sanitized
    assert "কোনোভাবেই টিকবে না" not in sanitized["facts"][0]["text"]
    # 5. Possible issues schema allow-listing enforced
    assert sanitized["possible_issues"][0]["kind"] == "research_suggestion"
    assert "slam dunk" not in sanitized["possible_issues"][0]["text"].lower()
    # 6. User objective sanitized
    assert "ডিক্রি দেবে" not in sanitized["user_objective"]
    assert "ক্ষতিপূরণ পাওয়া নিশ্চিত" not in sanitized["user_objective"]
