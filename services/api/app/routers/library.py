"""
Citizen Library API Router (SRS Section 5.9 M09, 9.3 S2).
Endpoints:
- GET /api/v1/library/categories
- GET /api/v1/library/search
- GET /api/v1/library/sources/{id}
- GET /api/v1/library/versions/{id}
- GET /api/v1/library/passages/{id}
- POST /api/v1/library/passages/{id}/explain
"""

from __future__ import annotations

from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from packages.trust_kernel.db import db_manager
from packages.trust_kernel.retrieval import retrieval_service
from services.api.app.routers.auth import get_current_user

router = APIRouter(prefix="/library", tags=["Citizen Library"])

LIFE_SITUATION_CATEGORIES = [
    {
        "id": "tenancy",
        "name_en": "Tenancy & Rent",
        "name_bn": "ভাড়া ও বাড়িওয়ালা-ভাড়াটিয়া",
        "icon": "home",
        "description_bn": "বাড়িভাড়া নিয়ন্ত্রণ, উচ্ছেদ নোটিশ, জামানত ও চুক্তি সম্পর্কিত আইন।",
    },
    {
        "id": "land",
        "name_en": "Land & Property",
        "name_bn": "জমি ও সম্পত্তি বিরোধ",
        "icon": "landscape",
        "description_bn": "নামজারি, খতিয়ান, বণ্টন, হেবা এবং জমি রেজিস্ট্রেশন সংক্রান্ত বিধান।",
    },
    {
        "id": "family",
        "name_en": "Family & Marriage",
        "name_bn": "পারিবারিক ও উত্তরাধিকার",
        "icon": "people",
        "description_bn": "বিবাহ, দেনমোহর, তালাক, সন্তানের হেফাজত ও উত্তরাধিকার বণ্টন।",
    },
    {
        "id": "labour",
        "name_en": "Labour & Employment",
        "name_bn": "শ্রম ও কর্মসংস্থান অধিকার",
        "icon": "work",
        "description_bn": "শ্রমিক অধিকার, মজুরি, প্রভিডেন্ট ফান্ড, বরখাস্ত ও ছাঁটাইয়ের ক্ষতিপূরণ।",
    },
    {
        "id": "business",
        "name_en": "Business & Commercial",
        "name_bn": "ব্যবসা ও চুক্তি আইন",
        "icon": "business",
        "description_bn": "ট্রেড লাইসেন্স, কোম্পানি আইন, চুক্তিভঙ্গ ও চেক ডিজঅনার।",
    },
    {
        "id": "civil",
        "name_en": "Fundamental Rights & Civil",
        "name_bn": "মৌলিক অধিকার ও সংবিধান",
        "icon": "gavel",
        "description_bn": "সংবিধান স্বীকৃত মৌলিক অধিকার, গ্রেফতার ও জামিনের আইনি সুরক্ষা।",
    },
]


class ExplainRequest(BaseModel):
    as_of_date: str | None = Field(default=None, description="As-of date (YYYY-MM-DD)")


@router.get("/categories")
def get_categories(user: dict[str, Any] = Depends(get_current_user)):
    """Returns the 6 primary citizen life situations (SRS 5.9)."""
    return {"categories": LIFE_SITUATION_CATEGORIES}


@router.get("/search")
def search_library(
    q: str = Query(default="", description="Search keywords"),
    as_of: str | None = Query(default=None, description="As-of date YYYY-MM-DD"),
    category: str | None = Query(default=None, description="Filter by life situation"),
    k: int = Query(default=10, ge=1, le=50),
    user: dict[str, Any] = Depends(get_current_user),
):
    """
    Searches the approved legal knowledge base as-of a specific date.
    Enforces AC-M09-1 (as-of date window) and AC-M09-2 (only approved).
    """
    target_date = as_of or date.today().isoformat()
    filters = {}
    if category:
        filters["category"] = category

    results = retrieval_service.search(
        query=q,
        as_of_date=target_date,
        filters=filters,
        k=k,
    )
    return {
        "query": q,
        "as_of_date": target_date,
        "count": len(results),
        "results": results,
    }


@router.get("/sources/{source_id}")
def get_source_details(
    source_id: str,
    as_of: str | None = Query(default=None),
    user: dict[str, Any] = Depends(get_current_user),
):
    """Returns source metadata and the currently effective approved version."""
    source = db_manager.get_source(source_id)
    if not source:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source not found")

    target_date = as_of or date.today().isoformat()
    versions = db_manager.list_source_versions(source_id=source_id, status="approved")

    effective_version = None
    for v in versions:
        if v["effective_from"] <= target_date:
            if v.get("effective_to") is None or v["effective_to"] >= target_date:
                effective_version = v
                break

    return {
        "source": source,
        "as_of_date": target_date,
        "effective_version": effective_version,
    }


@router.get("/versions/{version_id}")
def get_version_details(
    version_id: str,
    user: dict[str, Any] = Depends(get_current_user),
):
    """
    Returns version details and its passages.
    Enforces AC-M09-2 / AC-M10-3: Citizens can ONLY view 'approved' versions.
    """
    version = db_manager.get_source_version(version_id)
    if not version:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Version not found")

    user_role = user.get("role", "citizen")
    if user_role not in ("admin", "reviewer") and version["status"] != "approved":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Version not found or not yet approved for public viewing (AC-M10-3).",
        )

    passages = db_manager.get_source_passages(version_id)
    source = db_manager.get_source(version["source_id"])

    # Rights check
    if source and source.get("rights") == "unlicensed" and user_role not in ("admin", "reviewer"):
        for p in passages:
            p["text"] = "[পাঠ্য লাইসেন্স সীমাবদ্ধতার কারণে দৃশ্যমান নয় / Text unavailable due to licensing]"

    return {
        "version": version,
        "source": source,
        "passage_count": len(passages),
        "passages": passages,
    }


@router.get("/passages/{passage_id}")
def get_passage_detail(
    passage_id: str,
    user: dict[str, Any] = Depends(get_current_user),
):
    passage = db_manager.get_passage(passage_id)
    if not passage:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Passage not found")

    version = db_manager.get_source_version(passage["source_version_id"])
    user_role = user.get("role", "citizen")
    if not version or (user_role not in ("admin", "reviewer") and version["status"] != "approved"):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Passage not found")

    return {"passage": passage, "version": version}


@router.post("/passages/{passage_id}/explain")
def explain_passage(
    passage_id: str,
    req: ExplainRequest,
    user: dict[str, Any] = Depends(get_current_user),
):
    """
    Generates plain Bangla explanation for a legal passage (task source.explain.v1).
    Enforces AC-M09-4: Always includes AI label, source chip, and as-of date.
    """
    passage = db_manager.get_passage(passage_id)
    if not passage:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Passage not found")

    version = db_manager.get_source_version(passage["source_version_id"])
    if not version:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Version not found")

    source = db_manager.get_source(version["source_id"])
    source_title = source["title"] if source else "Legal Document"
    source_chip = f"{source_title} ({passage.get('section_ref', 'ধারা')})"
    target_date = req.as_of_date or date.today().isoformat()

    # Plain citizen-facing guidance: Clear, accessible Bangla with zero developer jargon
    explanation_bn = (
        "ধারাটির সংবিধিবদ্ধ মূল পাঠ্য উপরে উল্লেখ করা হয়েছে। "
        "সাধারণ নাগরিকের বোধগম্য ভাষায় ধারাটির সহজ সারসংক্ষেপ ও বিস্তারিত নির্দেশিকা শীঘ্রই যুক্ত করা হবে। [DRAFT_NOT_REVIEWED]"
    )
    key_terms = [
        {"term_bn": "আইনি বিধান", "definition_bn": "সংবিধিবদ্ধ আইনের মূল ধারা অনুযায়ী অনুসরণীয়"},
        {"term_bn": "কার্যকারিতা", "definition_bn": f"ধারাটি {version['effective_from']} তারিখ হতে কার্যকর"},
    ]
    what_not_said = "এই অনুচ্ছেদটি কোনো নির্দিষ্ট মামলার আইনি সিদ্ধান্ত বা আইনি প্রতিনিধিত্বের বিকল্প নয়।"

    return {
        "ai_label": "সহজ পাঠিকা [STATIC_PLACEHOLDER_NO_AI]",
        "is_ai_generated": False,
        "source_chip": source_chip,
        "as_of_date": target_date,
        "passage_id": passage_id,
        "heading": passage.get("heading"),
        "plain_explanation_bn": explanation_bn,
        "key_terms": key_terms,
        "what_not_said": what_not_said,
        "disclaimer_bn": "সতর্কতা: এটি একটি পরীক্ষামূলক সহায়ক তথ্য। বাস্তব আইনি পদক্ষেপে সর্বদা একজন নিবন্ধিত আইনজীবীর পরামর্শ নিন।",
    }
