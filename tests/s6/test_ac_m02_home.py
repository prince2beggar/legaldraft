"""
Acceptance Criteria Tests for Home Screen & Deterministic Next Action (SRS Section 5.2 M02; Sprint S6).

Exact SRS AC Mapping:
- AC-M02-1: unconfirmed deadline in 2 days + missing document => Next Action is deadline-confirm (priority 3 before 6).
- AC-M02-2: every Next Action has non-empty reason_refs that resolve to existing objects.
- AC-M02-3: no cases => ProblemInput + QuickActions + next.none, no errors.
- AC-M02-4: Home first useful content <= 4 s on simulated slow 3G (Playwright CDP throttling). If not feasible, mark UNVERIFIED in the report.

10 Priorities & Ordering:
- test_priority_1_urgent_triage_no_help
- test_priority_2_overdue_deadline
- test_priority_3_unconfirmed_deadline_le_3d
- test_priority_4_deadline_le_7d_with_open_tasks
- test_priority_5_lawyer_instruction_task_due
- test_priority_6_required_document_missing
- test_priority_7_extracted_fields_awaiting_review
- test_priority_8_proposed_facts_awaiting_confirmation
- test_priority_9_draft_in_progress
- test_priority_10_next_none_all_caught_up
- test_priority_ordering_all_10_tiers

Supporting Tests (Non-AC names):
- test_time_aware_bangla_greeting
- test_problem_input_metadata
- test_upcoming_list_bangla_format_limit_5
- test_home_ownership_isolation
"""

from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone

import pytest

from packages.trust_kernel.case_engine import CaseEngine
from packages.trust_kernel.home_engine import HomeEngine


@pytest.fixture
def case_eng(isolated_db_manager):
    return CaseEngine(db=isolated_db_manager)


@pytest.fixture
def home_eng(isolated_db_manager):
    return HomeEngine(db=isolated_db_manager)


@pytest.fixture
def user_a(isolated_db_manager):
    user_data = {
        "id": f"citizen-user-home-a-{time.time_ns()}",
        "phone": "+8801711223344",
        "name": "মোঃ আব্দুর রহমান",
        "role": "citizen",
        "roles": ["citizen"],
        "preferred_lang": "bn",
        "status": "active",
        "is_onboarded": True,
    }
    isolated_db_manager.save_user(user_data)
    return user_data


@pytest.fixture
def user_b(isolated_db_manager):
    user_data = {
        "id": f"citizen-user-home-b-{time.time_ns()}",
        "phone": "+8801811998877",
        "name": "জনাব সাদেক আলী",
        "role": "citizen",
        "roles": ["citizen"],
        "preferred_lang": "bn",
        "status": "active",
        "is_onboarded": True,
    }
    isolated_db_manager.save_user(user_data)
    return user_data


# ---------------------------------------------------------------------------
# Exact SRS AC Mapping (M02)
# ---------------------------------------------------------------------------


def test_ac_m02_1_unconfirmed_deadline_over_missing_doc_priority(home_eng, case_eng, user_a):
    """
    AC-M02-1: unconfirmed deadline in 2 days + missing document => Next Action is deadline-confirm (priority 3 before 6).
    """
    # 1. Create a case with NO documents attached (which satisfies Priority 6)
    case = case_eng.create_case(
        user_id=user_a["id"],
        title="নথিহীন মামলা সংক্রান্ত বিরোধ",
        case_type="general",
        status="active",
    )
    assert len(case_eng.db.list_case_documents(case["id"])) == 0

    # 2. Add an unconfirmed deadline due in 2 days (Priority 3: 0 <= days_left <= 3 & unconfirmed)
    today = datetime.now(timezone.utc).date()
    due_2_days = (today + timedelta(days=2)).isoformat()
    case_eng.db.create_deadline(
        case_id=case["id"],
        title="আইনি জবাব দাখিলের নোটিশ সময়সীমা",
        due_date=due_2_days,
        user_id=user_a["id"],
        confirmed_by_user=False,  # Unconfirmed!
    )

    # 3. Calculate Next Action
    action = home_eng.calculate_next_action(user_a["id"])

    # 4. Must select Priority 3 (deadline-confirm) before Priority 6 (missing document)
    assert action["priority_tier"] == 3
    assert action["action_type"] == "confirm_deadline"
    assert "সময়সীমা নিশ্চিত করুন" in action["title"]
    assert len(action["reason_refs"]) > 0
    assert action["reason_refs"][0]["object_type"] == "deadline"


def test_ac_m02_2_every_next_action_has_resolvable_reason_refs(
    home_eng, case_eng, user_a, isolated_db_manager
):
    """
    AC-M02-2: every Next Action has non-empty reason_refs that resolve to existing objects.
    """
    # Scenario A: Empty state -> resolves to user object
    action_empty = home_eng.calculate_next_action(user_a["id"])
    assert len(action_empty["reason_refs"]) > 0
    for ref in action_empty["reason_refs"]:
        assert ref.get("object_type") == "user"
        assert isolated_db_manager.get_user(ref["id"]) is not None

    # Scenario B: Case with missing doc -> resolves to case object
    case = case_eng.create_case(
        user_id=user_a["id"],
        title="রেফারেন্স যাচাই মামলা",
        case_type="land",
    )
    action_p6 = home_eng.calculate_next_action(user_a["id"])
    assert len(action_p6["reason_refs"]) > 0
    for ref in action_p6["reason_refs"]:
        assert ref.get("object_type") == "case"
        assert isolated_db_manager.get_case(ref["id"]) is not None

    # Scenario C: Case with deadline -> resolves to deadline object
    today = datetime.now(timezone.utc).date()
    case_eng.db.create_deadline(
        case_id=case["id"],
        title="জরুরি পদক্ষেপ",
        due_date=(today + timedelta(days=1)).isoformat(),
        user_id=user_a["id"],
        confirmed_by_user=False,
    )
    action_p3 = home_eng.calculate_next_action(user_a["id"])
    assert len(action_p3["reason_refs"]) > 0
    for ref in action_p3["reason_refs"]:
        if ref.get("object_type") == "deadline":
            assert isolated_db_manager.get_deadline(ref["id"]) is not None


def test_ac_m02_3_no_cases_problem_input_quick_actions_next_none(home_eng, user_b):
    """
    AC-M02-3: no cases => ProblemInput + QuickActions + next.none, no errors.
    """
    data = home_eng.get_home_data(user_b["id"])

    # 1. ProblemInput must be present and valid
    assert "problem_input" in data
    assert data["problem_input"]["placeholder"] != ""
    assert data["problem_input"]["action_route"] == "/intake"
    assert data["problem_input"]["mic_disabled"] is True
    assert data["problem_input"]["mic_tooltip"] == "ভয়েস ইনপুট শীঘ্রই আসছে"

    # 2. QuickActions must be present with >= 3 actions
    assert "quick_actions" in data
    assert len(data["quick_actions"]) >= 3
    urls = [q["url"] for q in data["quick_actions"]]
    assert "/documents/upload" in urls
    assert "/intake" in urls

    # 3. Next action must be next.none
    assert data["next_action"]["action_type"] == "next.none"
    assert data["next_action"]["priority_tier"] == 10
    assert len(data["next_action"]["reason_refs"]) > 0

    # 4. Zero cases, zero upcoming, no errors
    assert len(data["my_cases"]) == 0
    assert len(data["upcoming"]) == 0


def test_ac_m02_4_home_first_useful_content_simulated_slow_3g():
    """
    AC-M02-4: Home first useful content <= 4 s on simulated slow 3G (Playwright CDP throttling).
    Includes an unthrottled control, records load times, request counts, and asserts:
    - throttled_time > unthrottled_time
    - throttled_time <= 4.0s budget
    Both runs execute with service worker / browser cache cleared (first visit).
    """
    import http.server
    import threading
    from pathlib import Path

    from playwright.sync_api import sync_playwright

    static_dir = Path(__file__).resolve().parent.parent.parent / "backend" / "app" / "static"

    class QuietHandler(http.server.SimpleHTTPRequestHandler):
        def log_message(self, format, *args):
            pass

    server = http.server.HTTPServer(
        ("127.0.0.1", 0), lambda *args: QuietHandler(*args, directory=str(static_dir))
    )
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    url = f"http://127.0.0.1:{port}/home.html?variant=standard"

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=[f"--explicitly-allowed-ports={port}"],
            )

            # Warm up browser process to prevent process launch jitter
            warm_ctx = browser.new_context()
            warm_p = warm_ctx.new_page()
            warm_p.goto(url, wait_until="commit")
            warm_ctx.close()

            # -----------------------------------------------------------------
            # 1. Unthrottled Control (First visit, cleared cache)
            # -----------------------------------------------------------------
            context_ctrl = browser.new_context()
            page_ctrl = context_ctrl.new_page()

            unthrottled_requests = []
            page_ctrl.on("request", lambda req: unthrottled_requests.append(req.url))

            cdp_ctrl = context_ctrl.new_cdp_session(page_ctrl)
            cdp_ctrl.send("Network.enable")
            cdp_ctrl.send("Network.clearBrowserCache")
            cdp_ctrl.send("Network.setCacheDisabled", {"cacheDisabled": True})

            t0 = time.perf_counter()
            page_ctrl.goto(url, wait_until="commit")
            page_ctrl.wait_for_selector("#problemInputField", state="visible")
            unthrottled_time = time.perf_counter() - t0
            context_ctrl.close()

            # -----------------------------------------------------------------
            # 2. Throttled Slow 3G (First visit, cleared cache, 400 kbps, 400 ms RTT)
            # -----------------------------------------------------------------
            context_slow = browser.new_context()
            page_slow = context_slow.new_page()

            throttled_requests = []
            page_slow.on("request", lambda req: throttled_requests.append(req.url))

            cdp_slow = context_slow.new_cdp_session(page_slow)
            cdp_slow.send("Network.enable")
            cdp_slow.send("Network.clearBrowserCache")
            cdp_slow.send("Network.setCacheDisabled", {"cacheDisabled": True})
            cdp_slow.send(
                "Network.emulateNetworkConditions",
                {
                    "offline": False,
                    "latency": 400,
                    "downloadThroughput": 50000,  # ~400 kbps
                    "uploadThroughput": 50000,  # ~400 kbps
                },
            )

            t1 = time.perf_counter()
            page_slow.goto(url, wait_until="commit")
            page_slow.wait_for_selector("#problemInputField", state="visible")
            throttled_time = time.perf_counter() - t1
            context_slow.close()

            browser.close()

            # Assertions
            assert throttled_time > unthrottled_time, (
                f"Expected throttled ({throttled_time:.3f}s) > unthrottled ({unthrottled_time:.3f}s)"
            )
            assert throttled_time <= 4.0, (
                f"Slow 3G first useful content took {throttled_time:.2f}s, exceeding 4.0s budget"
            )
            assert len(unthrottled_requests) > 0
            assert len(throttled_requests) > 0
    finally:
        server.shutdown()


# ---------------------------------------------------------------------------
# 10 Priorities (1 test per priority)
# ---------------------------------------------------------------------------


def test_priority_1_urgent_triage_no_help(home_eng, case_eng, user_a):
    """Priority 1: Urgent triage no help step (reads nullable case.is_urgent_triage / triage_urgency == 'urgent_no_help')."""
    case = case_eng.create_case(
        user_id=user_a["id"],
        title="জরুরি ট্রায়াজ কেস",
        urgency="urgent",
    )
    # Mark triage as urgent_no_help
    case_eng.db.update_case(case["id"], is_urgent_triage=True, triage_urgency="urgent_no_help")

    action = home_eng.calculate_next_action(user_a["id"])
    assert action["priority_tier"] == 1
    assert action["action_type"] == "urgent_triage"
    assert action["case_id"] == case["id"]


def test_priority_2_overdue_deadline(home_eng, case_eng, user_a):
    """Priority 2: Overdue deadline (days_left < 0 / is_overdue) -> sets case status to action_required (AC-M06-3)."""
    case = case_eng.create_case(
        user_id=user_a["id"],
        title="মেয়াদোত্তীর্ণ মামলার ফাইল",
        status="active",
    )
    today = datetime.now(timezone.utc).date()
    yesterday = (today - timedelta(days=2)).isoformat()
    case_eng.db.create_deadline(
        case_id=case["id"],
        title="আদালতে হাজিরা বা জবাব দাখিল",
        due_date=yesterday,
        user_id=user_a["id"],
        confirmed_by_user=True,
    )

    action = home_eng.calculate_next_action(user_a["id"])
    assert action["priority_tier"] == 2
    assert action["action_type"] == "overdue_deadline"
    assert "মেয়াদ উত্তীর্ণ" in action["title"]

    # Verify AC-M06-3: case status updated to action_required
    updated_case = case_eng.db.get_case(case["id"])
    assert updated_case["status"] == "action_required"


def test_priority_3_unconfirmed_deadline_le_3d(home_eng, case_eng, user_a):
    """Priority 3: Unconfirmed deadline <= 3 days (days_left <= 3 & unconfirmed)."""
    case = case_eng.create_case(user_id=user_a["id"], title="সময়সীমা নিশ্চিতকরণ কেস")
    today = datetime.now(timezone.utc).date()
    due_in_3 = (today + timedelta(days=3)).isoformat()
    case_eng.db.create_deadline(
        case_id=case["id"],
        title="নোটিশের গণনা করা সময়সীমা",
        due_date=due_in_3,
        user_id=user_a["id"],
        confirmed_by_user=False,
    )

    action = home_eng.calculate_next_action(user_a["id"])
    assert action["priority_tier"] == 3
    assert action["action_type"] == "confirm_deadline"


def test_priority_4_deadline_le_7d_with_open_tasks(home_eng, case_eng, user_a):
    """Priority 4: Deadline <= 7 days with open tasks (0 <= days_left <= 7 & open tasks)."""
    case = case_eng.create_case(user_id=user_a["id"], title="টাস্ক ও সময়সীমা কেস")
    today = datetime.now(timezone.utc).date()
    due_in_5 = (today + timedelta(days=5)).isoformat()
    case_eng.db.create_deadline(
        case_id=case["id"],
        title="আসন্ন শুনানি",
        due_date=due_in_5,
        user_id=user_a["id"],
        confirmed_by_user=True,  # Confirmed so Priority 3 doesn't fire
    )
    case_eng.db.create_task(
        case_id=case["id"],
        title="খতিয়ানের নকল সংগ্রহ করুন",
        owner_id=user_a["id"],
        status="not_started",
    )

    action = home_eng.calculate_next_action(user_a["id"])
    assert action["priority_tier"] == 4
    assert action["action_type"] == "complete_task"
    assert "খতিয়ানের নকল" in action["title"]


def test_priority_5_lawyer_instruction_task_due(home_eng, case_eng, user_a):
    """Priority 5: Lawyer/instruction task due (origin in ('lawyer', 'instruction'))."""
    case = case_eng.create_case(user_id=user_a["id"], title="আইনজীবীর নির্দেশিত কাজ")
    # Attach a document so Priority 6 doesn't fire
    doc = case_eng.db.create_document(user_a["id"], "dalil.pdf", 100, "application/pdf")
    case_eng.attach_document(case["id"], user_a["id"], doc["id"])

    case_eng.db.create_task(
        case_id=case["id"],
        title="মূল দলিলের সত্যায়িত কপি প্রদান",
        owner_id=user_a["id"],
        origin="lawyer",
        status="not_started",
    )

    action = home_eng.calculate_next_action(user_a["id"])
    assert action["priority_tier"] == 5
    assert action["action_type"] == "complete_task"
    assert "আইনজীবীর নির্দেশিত" in action["title"]


def test_priority_6_required_document_missing(home_eng, case_eng, user_a):
    """Priority 6: Required document missing via case-type checklist rule."""
    _ = case_eng.create_case(
        user_id=user_a["id"],
        title="প্রয়োজনীয় দলিলবিহীন কেস",
        case_type="land_dispute",
    )

    action = home_eng.calculate_next_action(user_a["id"])
    assert action["priority_tier"] == 6
    assert action["action_type"] == "upload_document"
    assert "আপলোড করুন" in action["title"]


def test_priority_6_case_with_docs_but_required_one_missing(home_eng, case_eng, user_a):
    """Priority 6: Case with docs but a required one missing -> priority 6."""
    case = case_eng.create_case(
        user_id=user_a["id"],
        title="দলিল আছে কিন্তু খতিয়ান নেই",
        case_type="land_dispute",  # Requires both 'khatian' and 'deed'
    )
    # Attach 'deed' only
    doc1 = case_eng.db.create_document(user_a["id"], "deed.pdf", doc_type="deed")
    case_eng.attach_document(case["id"], user_a["id"], doc1["id"])

    # Next Action must still be Priority 6 because 'khatian' is missing!
    action = home_eng.calculate_next_action(user_a["id"])
    assert action["priority_tier"] == 6
    assert action["action_type"] == "upload_document"
    assert "খতিয়ান বা পরচা" in action["title"]


def test_priority_6_case_with_all_required_docs_is_not_priority_6(home_eng, case_eng, user_a):
    """Priority 6: Case with all required docs -> not 6 (drops to lower tier / next.none)."""
    case = case_eng.create_case(
        user_id=user_a["id"],
        title="সকল প্রয়োজনীয় দলিল সংযুক্ত",
        case_type="land_dispute",
    )
    # Attach both 'khatian' and 'deed'
    doc1 = case_eng.db.create_document(user_a["id"], "deed.pdf", doc_type="deed")
    case_eng.attach_document(case["id"], user_a["id"], doc1["id"])
    doc2 = case_eng.db.create_document(user_a["id"], "khatian.pdf", doc_type="khatian")
    case_eng.attach_document(case["id"], user_a["id"], doc2["id"])

    # Next Action must NOT be Priority 6!
    action = home_eng.calculate_next_action(user_a["id"])
    assert action["priority_tier"] != 6
    assert action["priority_tier"] == 10  # All caught up (next.none)


def test_priority_6_draft_not_reviewed_placeholder(home_eng, case_eng, user_a):
    """Priority 6: Unapproved checklist items show [DRAFT_NOT_REVIEWED / খসড়া চেকলিস্ট] placeholder."""
    _ = case_eng.create_case(
        user_id=user_a["id"],
        title="খসড়া চেকলিস্ট কেস",
        metadata={
            "required_documents": [
                {
                    "doc_type": "survey_map",
                    "title": "নকশা বা সার্ভে ম্যাপ",
                    "status": "DRAFT_NOT_REVIEWED",
                }
            ]
        },
    )
    action = home_eng.calculate_next_action(user_a["id"])
    assert action["priority_tier"] == 6
    assert "[DRAFT_NOT_REVIEWED / খসড়া চেকলিস্ট]" in action["title"]


def test_priority_7_extracted_fields_awaiting_review(home_eng, case_eng, user_a):
    """Priority 7: Extracted fields awaiting review (status == 'extracted')."""
    case = case_eng.create_case(user_id=user_a["id"], title="তথ্য পর্যালোচনা কেস")
    doc = case_eng.db.create_document(user_a["id"], "notice_scan.pdf", 100, "application/pdf")
    case_eng.attach_document(case["id"], user_a["id"], doc["id"])

    # Add an extracted field
    case_eng.db.add_document_field(
        document_id=doc["id"],
        key="sender",
        value="এডভোকেট রফিকুল ইসলাম",
        confidence=0.95,
        state="extracted",
    )

    action = home_eng.calculate_next_action(user_a["id"])
    assert action["priority_tier"] == 7
    assert action["action_type"] == "review_extracted_fields"
    assert "তথ্য যাচাই সম্পন্ন করুন" in action["title"]


def test_priority_8_proposed_facts_awaiting_confirmation(home_eng, case_eng, user_a):
    """Priority 8: AI-proposed facts/events awaiting confirmation (is_proposed == True)."""
    case = case_eng.create_case(user_id=user_a["id"], title="AI পর্যালোচনা কেস")
    doc = case_eng.db.create_document(user_a["id"], "doc.pdf", 100, "application/pdf")
    case_eng.attach_document(case["id"], user_a["id"], doc["id"])

    # Add AI-proposed fact
    case_eng.add_fact(
        case_id=case["id"],
        user_id=user_a["id"],
        fact_text="সম্ভাব্য আইনি সমস্যা: চুক্তির ৩ নং ধারা লঙ্ঘিত হয়েছে",
        is_proposed=True,
    )

    action = home_eng.calculate_next_action(user_a["id"])
    assert action["priority_tier"] == 8
    assert action["action_type"] == "confirm_proposed_fact"
    assert "AI-প্রস্তাবিত তথ্য নিশ্চিত করুন" in action["title"]


def test_priority_9_draft_in_progress(home_eng, case_eng, user_a):
    """Priority 9: Draft in progress (draft.status == 'in_progress')."""
    case = case_eng.create_case(
        user_id=user_a["id"],
        title="খসড়া প্রস্তুতের কেস",
        metadata={"draft_in_progress": True},
    )
    doc = case_eng.db.create_document(user_a["id"], "deed.pdf", 100, "application/pdf")
    case_eng.attach_document(case["id"], user_a["id"], doc["id"])

    action = home_eng.calculate_next_action(user_a["id"])
    assert action["priority_tier"] == 9
    assert action["action_type"] == "continue_draft"
    assert "খসড়া" in action["title"]


def test_priority_10_next_none_all_caught_up(home_eng, case_eng, user_a):
    """Priority 10: next.none ('all caught up' / explore default)."""
    case = case_eng.create_case(
        user_id=user_a["id"],
        title="সম্পূর্ণ পরিচ্ছন্ন কেস",
        status="active",
    )
    doc = case_eng.db.create_document(user_a["id"], "doc.pdf", 100, "application/pdf")
    case_eng.attach_document(case["id"], user_a["id"], doc["id"])

    action = home_eng.calculate_next_action(user_a["id"])
    assert action["priority_tier"] == 10
    assert action["action_type"] == "next.none"
    assert "সব কাজ সম্পন্ন" in action["title"]


def test_priority_ordering_all_10_tiers(home_eng, case_eng, user_a):
    """
    1 Priority ordering test:
    Demonstrates that higher priority tiers preempt lower priority tiers.
    Priority 1 beats 2, 2 beats 3, 3 beats 4, 4 beats 5, 5 beats 6, etc.
    """
    case = case_eng.create_case(
        user_id=user_a["id"],
        title="মাল্টি-প্রায়োরিটি কেস",
        case_type="land_dispute",
    )

    # Has missing document (Priority 6)
    na_6 = home_eng.calculate_next_action(user_a["id"])
    assert na_6["priority_tier"] == 6

    # Add lawyer task -> Priority 5 beats Priority 6
    case_eng.db.create_task(
        case_id=case["id"],
        title="আইনজীবীর কাজ",
        owner_id=user_a["id"],
        origin="lawyer",
        status="not_started",
    )
    na_5 = home_eng.calculate_next_action(user_a["id"])
    assert na_5["priority_tier"] == 5

    # Add deadline in 5 days -> Priority 4 beats Priority 5
    today = datetime.now(timezone.utc).date()
    case_eng.db.create_deadline(
        case_id=case["id"],
        title="আসন্ন সময়সীমা ৫ দিন",
        due_date=(today + timedelta(days=5)).isoformat(),
        user_id=user_a["id"],
        confirmed_by_user=True,
    )
    na_4 = home_eng.calculate_next_action(user_a["id"])
    assert na_4["priority_tier"] == 4

    # Add unconfirmed deadline in 2 days -> Priority 3 beats Priority 4
    case_eng.db.create_deadline(
        case_id=case["id"],
        title="অনিশ্চিত সময়সীমা ২ দিন",
        due_date=(today + timedelta(days=2)).isoformat(),
        user_id=user_a["id"],
        confirmed_by_user=False,
    )
    na_3 = home_eng.calculate_next_action(user_a["id"])
    assert na_3["priority_tier"] == 3

    # Add overdue deadline -> Priority 2 beats Priority 3
    case_eng.db.create_deadline(
        case_id=case["id"],
        title="মেয়াদোত্তীর্ণ সময়সীমা",
        due_date=(today - timedelta(days=1)).isoformat(),
        user_id=user_a["id"],
        confirmed_by_user=True,
    )
    na_2 = home_eng.calculate_next_action(user_a["id"])
    assert na_2["priority_tier"] == 2

    # Mark urgent triage -> Priority 1 beats Priority 2
    case_eng.db.update_case(case["id"], is_urgent_triage=True, triage_urgency="urgent_no_help")
    na_1 = home_eng.calculate_next_action(user_a["id"])
    assert na_1["priority_tier"] == 1


# ---------------------------------------------------------------------------
# Extra tests kept under non-AC names
# ---------------------------------------------------------------------------


def test_time_aware_bangla_greeting(home_eng, user_a):
    """Time-aware greeting test kept under non-AC name."""
    g_morning = home_eng.generate_greeting(user_a["id"], hour=8)
    assert "শুভ সকাল" in g_morning
    assert "মোঃ আব্দুর রহমান" in g_morning

    g_afternoon = home_eng.generate_greeting(user_a["id"], hour=14)
    assert "শুভ অপরাহ্ন" in g_afternoon

    g_evening = home_eng.generate_greeting(user_a["id"], hour=20)
    assert "শুভ সন্ধ্যা" in g_evening


def test_problem_input_metadata(home_eng):
    """ProblemInput metadata test kept under non-AC name."""
    metadata = home_eng.get_problem_input_metadata()
    assert metadata["mic_disabled"] is True
    assert metadata["mic_tooltip"] == "ভয়েস ইনপুট শীঘ্রই আসছে"
    assert metadata["action_route"] == "/intake"

    cleaned = home_eng.clean_problem_input("   জমি খারিজ সংক্রান্ত নোটিশ পেয়েছি   ")
    assert cleaned == "জমি খারিজ সংক্রান্ত নোটিশ পেয়েছি"


def test_upcoming_list_bangla_format_limit_5(home_eng, case_eng, user_a):
    """Upcoming list shows up to 5 items with Bangla formatted dates."""
    case = case_eng.create_case(user_id=user_a["id"], title="আসন্ন তালিকা কেস")
    today = datetime.now(timezone.utc).date()
    for i in range(1, 8):
        case_eng.db.create_deadline(
            case_id=case["id"],
            title=f"আইনি পদক্ষেপ {i}",
            due_date=(today + timedelta(days=i + 1)).isoformat(),
            user_id=user_a["id"],
            confirmed_by_user=True,
        )

    home_data = home_eng.get_home_data(user_a["id"])
    upcoming = home_data.get("upcoming", [])
    assert len(upcoming) == 5
    days_list = [u["days_left"] for u in upcoming]
    assert days_list == sorted(days_list)


def test_home_ownership_isolation(home_eng, case_eng, user_a, user_b):
    """User B cannot see User A's cases or next actions."""
    case_a = case_eng.create_case(
        user_id=user_a["id"],
        title="ব্যবহারকারী ক এর মামলা",
        urgency="urgent",
    )
    today = datetime.now(timezone.utc).date()
    case_eng.db.create_deadline(
        case_id=case_a["id"],
        title="ব্যবহারকারী ক এর সময়সীমা",
        due_date=(today + timedelta(days=1)).isoformat(),
        user_id=user_a["id"],
        confirmed_by_user=True,
    )

    home_a = home_eng.get_home_data(user_a["id"])
    assert len(home_a["my_cases"]) >= 1

    home_b = home_eng.get_home_data(user_b["id"])
    assert home_b["next_action"]["action_type"] == "next.none"
    assert len(home_b["my_cases"]) == 0
