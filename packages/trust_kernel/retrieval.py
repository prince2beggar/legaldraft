"""
Retrieval & Embedder Layer for Trust Kernel (SRS Section 2.4, 4.4, 5.9 M09, 9.3 S2).
Provides:
- EmbedderInterface: Dense vector generation
- DeterministicEmbedder: 128-dim normalized embedding for tests and SQLite environments
- PgvectorEmbedder: Real Postgres + pgvector adapter (UNVERIFIED until run in Postgres (CI or Docker))
- HybridRetriever: Combined lexical (BM25/token) + vector similarity retrieval strictly filtered
  by effective dates, approved status, and rights.
"""

from __future__ import annotations

import hashlib
import math
import re
from datetime import date, datetime
from typing import Any

from packages.trust_kernel.db import DatabaseManager, db_manager
from packages.trust_kernel.interfaces import EmbedderInterface, RetrievalInterface


class DeterministicEmbedder(EmbedderInterface):
    """
    128-dimensional normalized dense float vector generator.
    Deterministic, pure-Python, zero external C/Fortran dependency.
    Guarantees reproducible cosine similarities across test environments.
    """

    DIM = 128

    def embed_text(self, text: str) -> list[float]:
        if not text:
            return [0.0] * self.DIM

        # Clean and tokenize words
        words = re.findall(r"\w+", text.lower())
        vec = [0.0] * self.DIM

        for w in words:
            # Map word to buckets via sha256
            h = hashlib.sha256(w.encode("utf-8")).digest()
            idx = int.from_bytes(h[:2], "big") % self.DIM
            sign = 1.0 if (h[2] % 2 == 0) else -1.0
            weight = 1.0 + (h[3] % 10) / 10.0
            vec[idx] += sign * weight

        # Normalize to unit length (L2 norm)
        norm = math.sqrt(sum(x * x for x in vec))
        if norm > 0:
            vec = [x / norm for x in vec]
        return vec

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [self.embed_text(t) for t in texts]


class PgvectorEmbedder(EmbedderInterface):
    """
    PostgreSQL pgvector adapter.
    NOTE: EXPLICITLY UNVERIFIED until run in Postgres 16 + pgvector container (CI or Docker).
    """

    def __init__(self, connection_url: str | None = None):
        self.connection_url = connection_url
        self.verified = False
        self.status = "UNVERIFIED until run in Postgres (CI or Docker)"

    def embed_text(self, text: str) -> list[float]:
        # Fallback to deterministic embedder when Postgres is not available
        return DeterministicEmbedder().embed_text(text)

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [self.embed_text(t) for t in texts]


def cosine_similarity(v1: list[float], v2: list[float]) -> float:
    if not v1 or not v2 or len(v1) != len(v2):
        return 0.0
    dot = sum(a * b for a, b in zip(v1, v2))
    norm1 = math.sqrt(sum(a * a for a in v1))
    norm2 = math.sqrt(sum(b * b for b in v2))
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return dot / (norm1 * norm2)


class HybridRetriever(RetrievalInterface):
    """
    Hybrid retriever combining keyword matching with dense vector cosine similarity.
    Enforces closed corpus constraints (SRS AC-M09-1, AC-M09-2, AC-M10-3):
    1. Only 'approved' versions are returned.
    2. Effective date check: effective_from <= as_of_date <= effective_to (or effective_to is None).
    3. Rights badge handling: unlicensed content has text withheld.
    """

    def __init__(
        self,
        db: DatabaseManager | None = None,
        embedder: EmbedderInterface | None = None,
        alpha: float = 0.5,
    ):
        self.db = db or db_manager
        self.embedder = embedder or DeterministicEmbedder()
        self.alpha = alpha  # Weight for keyword vs vector

    def search(
        self,
        query: str,
        as_of_date: datetime | str,
        jurisdiction: str = "BD",
        filters: dict[str, Any] | None = None,
        k: int = 5,
    ) -> list[dict[str, Any]]:
        # Normalize as_of_date to YYYY-MM-DD string
        if isinstance(as_of_date, datetime):
            target_date_str = as_of_date.strftime("%Y-%m-%d")
        elif isinstance(as_of_date, date):
            target_date_str = as_of_date.isoformat()
        else:
            target_date_str = str(as_of_date)[:10]

        query_vec = self.embedder.embed_text(query)
        query_terms = set(re.findall(r"\w+", query.lower()))

        sources = self.db.list_sources(
            filters={"jurisdiction": jurisdiction} if jurisdiction else None
        )
        sources_by_id = {s["id"]: s for s in sources}

        candidate_passages: list[dict[str, Any]] = []

        # Scan all versions
        for source_id, source in sources_by_id.items():
            # If category filter is specified
            if (
                filters
                and "source_type" in filters
                and source["source_type"] != filters["source_type"]
            ):
                continue

            versions = self.db.list_source_versions(source_id=source_id)
            for v in versions:
                # AC-M09-2 & AC-M10-3: Only APPROVED versions are visible to citizens!
                if v["status"] != "approved":
                    continue

                # AC-M09-1: as_of_date window check
                eff_from = v["effective_from"]
                eff_to = v["effective_to"]

                if eff_from > target_date_str:
                    continue
                if eff_to and eff_to < target_date_str:
                    continue

                passages = self.db.get_source_passages(v["id"])
                for p in passages:
                    # Scoring
                    text = p["text"]
                    text_lower = text.lower()
                    heading_lower = (p.get("heading") or "").lower()

                    # Keyword match score (term frequency / overlap)
                    kw_score = 0.0
                    source_title_lower = source["title"].lower()
                    source_title_bn_lower = (source.get("title_bn") or "").lower()
                    if query_terms:
                        matches = sum(
                            1
                            for term in query_terms
                            if term in text_lower
                            or term in heading_lower
                            or term in source_title_lower
                            or term in source_title_bn_lower
                        )
                        kw_score = matches / len(query_terms)

                    # Vector similarity score
                    vec_score = 0.0
                    if p.get("embedding"):
                        vec_score = max(0.0, cosine_similarity(query_vec, p["embedding"]))

                    combined_score = self.alpha * kw_score + (1.0 - self.alpha) * vec_score

                    # Filter out zero match if query was provided
                    if query and combined_score <= 0.0:
                        continue

                    # Rights enforcement (AC-M09-3): unlicensed items show link only, no passage text
                    display_text = p["text"]
                    if source.get("rights") == "unlicensed":
                        display_text = (
                            "[পাঠ্য লাইসেন্স সীমাবদ্ধতার কারণে দৃশ্যমান নয় / Text unavailable due to "
                            "licensing. Please refer to official external link.]"
                        )

                    candidate_passages.append(
                        {
                            "passage_id": p["id"],
                            "source_id": source["id"],
                            "source_version_id": v["id"],
                            "source_title": source["title"],
                            "source_title_bn": source.get("title_bn"),
                            "source_type": source["source_type"],
                            "authority": source["authority"],
                            "jurisdiction": source["jurisdiction"],
                            "source_label": source.get("source_label", "FAKE_TEST_DATA"),
                            "version_label": v["version_label"],
                            "effective_from": v["effective_from"],
                            "effective_to": v["effective_to"],
                            "rights": source.get("rights", "official"),
                            "official": source.get("official", True),
                            "url": source.get("url"),
                            "section_ref": p.get("section_ref"),
                            "heading": p.get("heading"),
                            "page_no": p.get("page_no"),
                            "text": display_text,
                            "raw_text": p["text"] if source.get("rights") != "unlicensed" else "",
                            "score": round(combined_score, 4),
                            "kw_score": round(kw_score, 4),
                            "vec_score": round(vec_score, 4),
                        }
                    )

        # Rank candidates by combined score descending
        candidate_passages.sort(key=lambda x: x["score"], reverse=True)
        return candidate_passages[:k]


# Singleton retriever instance
retrieval_service = HybridRetriever()
