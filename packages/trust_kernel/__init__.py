"""
Trust Kernel Package - Shared Foundation for AIN-AI
"""

from packages.trust_kernel.ai_gateway import AIGateway, ai_gateway
from packages.trust_kernel.audit import audit_service
from packages.trust_kernel.citation_verifier import CitationVerifier, citation_verifier
from packages.trust_kernel.eval_harness import EvalHarness, eval_harness
from packages.trust_kernel.feature_flags import feature_flags
from packages.trust_kernel.i18n import i18n
from packages.trust_kernel.interfaces import (
    AuditInterface,
    CitationVerifierInterface,
    EmbedderInterface,
    PolicyConsentInterface,
    RetrievalInterface,
    ReviewQueueInterface,
    RulesEngineInterface,
    SourceRegistryInterface,
)
from packages.trust_kernel.policy_consent import policy_consent
from packages.trust_kernel.retrieval import (
    DeterministicEmbedder,
    HybridRetriever,
    PgvectorEmbedder,
    retrieval_service,
)
from packages.trust_kernel.rules_engine import RulesEngine, rules_engine
from packages.trust_kernel.source_registry import SourceRegistryService, source_registry

__all__ = [
    "AIGateway",
    "AuditInterface",
    "CitationVerifier",
    "CitationVerifierInterface",
    "DeterministicEmbedder",
    "EmbedderInterface",
    "EvalHarness",
    "HybridRetriever",
    "PgvectorEmbedder",
    "PolicyConsentInterface",
    "RetrievalInterface",
    "ReviewQueueInterface",
    "RulesEngine",
    "RulesEngineInterface",
    "SourceRegistryInterface",
    "SourceRegistryService",
    "ai_gateway",
    "audit_service",
    "citation_verifier",
    "eval_harness",
    "feature_flags",
    "i18n",
    "policy_consent",
    "retrieval_service",
    "rules_engine",
    "source_registry",
]
