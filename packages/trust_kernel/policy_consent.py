"""
Policy and Consent Engine (SRS Section 2.4, 3.2, 3.4)
Controls data access, role-based checks, and expiring consent grants.
"""

from datetime import datetime, timezone
from typing import Any

from packages.trust_kernel.db import db_manager
from packages.trust_kernel.interfaces import PolicyConsentInterface


class PolicyConsentService(PolicyConsentInterface):
    def __init__(self):
        self._consents: dict[str, dict[str, Any]] = {}
        self.load_from_db()

    def load_from_db(self) -> None:
        """Hydrates consents from persistent database layer."""
        persisted = db_manager.load_all_consents()
        for c in persisted:
            self._consents[c["id"]] = c

    def can(self, actor: dict[str, Any], action: str, obj: dict[str, Any]) -> bool:
        """
        Determines if actor is authorized to perform action on object.
        Follows Section 3.2 Permission Matrix.
        """
        if not actor:
            return False

        actor_role = actor.get("role", "citizen")
        actor_id = actor.get("id")

        # Admin can view platform metadata, but never raw user document content without break-glass
        if actor_role == "admin":
            if action in ["view_platform_audit", "manage_users", "manage_system"]:
                return True
            if action in ["read_document_content", "view_user_cases"]:
                return actor.get("break_glass_active", False) is True
            return False

        # Reviewer permissions
        if actor_role == "reviewer":
            return action in [
                "review_source",
                "review_template",
                "review_rule",
                "view_review_queue",
            ]

        # Citizen / Lawyer on own object
        owner_id = obj.get("owner_id")
        if owner_id and owner_id == actor_id:
            return True

        # Public approved resources are readable by all authenticated users
        if (
            obj.get("object_type") == "source"
            and obj.get("status") == "approved"
            and action == "read"
        ):
            return True

        # Check explicit consent grants
        obj_id = obj.get("id")
        scope_type = obj.get("object_type", "case")
        if not actor_id or not obj_id:
            return False
        return self._has_active_consent(actor_id, scope_type, obj_id, action)

    def grant(
        self,
        grantor_id: str,
        grantee_id: str,
        scope: str,
        permissions: list[str],
        expires_at: datetime,
    ) -> str:
        consent_id = f"cst-{len(self._consents) + 1:05d}"
        self._consents[consent_id] = {
            "id": consent_id,
            "grantor_id": grantor_id,
            "grantee_id": grantee_id,
            "scope": scope,
            "permissions": permissions,
            "starts_at": datetime.now(timezone.utc),
            "expires_at": expires_at,
            "revoked_at": None,
        }
        db_manager.save_consent(self._consents[consent_id])
        return consent_id

    def revoke(self, consent_id: str) -> bool:
        if consent_id in self._consents:
            self._consents[consent_id]["revoked_at"] = datetime.now(timezone.utc)
            db_manager.save_consent(self._consents[consent_id])
            return True
        return False

    def _has_active_consent(
        self, grantee_id: str, scope_type: str, scope_id: str, action: str
    ) -> bool:
        now = datetime.now(timezone.utc)
        for c in self._consents.values():
            if (
                c["grantee_id"] == grantee_id
                and not c["revoked_at"]
                and c["expires_at"] > now
                and action in c.get("permissions", ["view"])
            ):
                return True
        return False

    def record_versioned_consent(
        self, user_id: str, consent_type: str, version: str
    ) -> dict[str, Any]:
        """Record an explicit versioned user consent (SRS Section 5, M01)."""
        c_id = f"cst-ver-{len(self._consents) + 1:05d}"
        record = {
            "id": c_id,
            "grantor_id": user_id,
            "grantee_id": "platform",
            "scope": consent_type,
            "version": version,
            "permissions": ["accepted"],
            "starts_at": datetime.now(timezone.utc),
            "expires_at": datetime.max.replace(tzinfo=timezone.utc),
            "revoked_at": None,
        }
        self._consents[c_id] = record
        db_manager.save_consent(record)
        return record

    def get_user_consents(self, user_id: str) -> list[dict[str, Any]]:
        """Return all active and historical consents for a given user."""
        return [c for c in self._consents.values() if c.get("grantor_id") == user_id]

    def can_access_route(
        self, actor: dict[str, Any] | None, path: str, method: str
    ) -> tuple[bool, str]:
        """
        Evaluates route-level access control for X-001 sweep and security enforcement.
        Returns (is_allowed, reason).
        """
        clean_path = path.rstrip("/") or "/"

        # 1. Public whitelist (health, docs, static, auth handshake)
        public_exact = {
            "/health",
            "/health/ready",
            "/health/flags",
            "/auth/otp/request",
            "/auth/otp/verify",
            "/auth/refresh",
            "/api/v1/auth/otp/request",
            "/api/v1/auth/otp/verify",
            "/api/v1/auth/refresh",
            "/welcome",
            "/signin",
            "/otp",
            "/onboarding",
            "/docs",
            "/openapi.json",
        }
        if clean_path in public_exact or clean_path.startswith("/static"):
            return True, "public_route"

        # 2. If actor is unauthenticated, deny access immediately
        if not actor:
            return False, "unauthenticated"

        actor_role = actor.get("role", "citizen")

        # 3. Admin / Reviewer restricted surfaces
        if clean_path == "/admin" or clean_path.startswith("/api/v1/admin"):
            if actor_role in ("admin", "reviewer"):
                return True, "admin_role_granted"
            return False, "forbidden_requires_admin_role"

        # 4. Protected authenticated surfaces (Citizen, Advocate, Admin)
        return True, "authenticated_access_granted"

    def clear(self) -> None:
        """Reset consent store for clean testing."""
        self._consents.clear()


policy_consent = PolicyConsentService()
