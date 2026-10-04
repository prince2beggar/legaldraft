"""
Trust Kernel Interfaces (SRS Section 2.4)
The shared contracts that enforce correctness across all legal AI operations.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any


class SourceRegistryInterface(ABC):
    @abstractmethod
    def create_source(self, meta: dict[str, Any]) -> str:
        pass

    @abstractmethod
    def add_version(
        self,
        source_id: str,
        file_content: bytes,
        effective_from: datetime,
        effective_to: datetime | None = None,
    ) -> str:
        pass

    @abstractmethod
    def submit_for_review(self, version_id: str) -> bool:
        pass

    @abstractmethod
    def approve(self, version_id: str, reviewer_id: str) -> bool:
        pass

    @abstractmethod
    def get_effective(self, source_id: str, as_of_date: datetime) -> dict[str, Any] | None:
        pass


class EmbedderInterface(ABC):
    @abstractmethod
    def embed_text(self, text: str) -> list[float]:
        pass

    @abstractmethod
    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        pass


class RetrievalInterface(ABC):
    @abstractmethod
    def search(
        self,
        query: str,
        as_of_date: datetime,
        jurisdiction: str = "BD",
        filters: dict[str, Any] | None = None,
        k: int = 5,
    ) -> list[dict[str, Any]]:
        pass


class CitationVerifierInterface(ABC):
    @abstractmethod
    def verify(self, ai_output: dict[str, Any], as_of_date: datetime) -> dict[str, Any]:
        pass

    @abstractmethod
    def enforce(self, ai_output: dict[str, Any]) -> dict[str, Any]:
        pass


class RulesEngineInterface(ABC):
    @abstractmethod
    def compute(
        self, rule_key: str, inputs: dict[str, Any], as_of_date: datetime
    ) -> dict[str, Any]:
        pass


class ReviewQueueInterface(ABC):
    @abstractmethod
    def enqueue(self, object_type: str, object_id: str, tier: str, reason: str) -> str:
        pass

    @abstractmethod
    def decide(
        self, item_id: str, decision: str, reviewer_id: str, note: str | None = None
    ) -> bool:
        pass


class PolicyConsentInterface(ABC):
    @abstractmethod
    def can(self, actor: dict[str, Any], action: str, obj: dict[str, Any]) -> bool:
        pass

    @abstractmethod
    def grant(
        self,
        grantor_id: str,
        grantee_id: str,
        scope: str,
        permissions: list[str],
        expires_at: datetime,
    ) -> str:
        pass

    @abstractmethod
    def revoke(self, consent_id: str) -> bool:
        pass


class AuditInterface(ABC):
    @abstractmethod
    def log(
        self,
        actor_id: str,
        actor_role: str,
        action: str,
        object_type: str,
        object_id: str,
        ip: str | None = None,
        meta: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        pass

    @abstractmethod
    def verify_integrity(self) -> bool:
        pass
