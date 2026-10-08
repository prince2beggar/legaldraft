"""
Append-only Hash-chained Audit Logger (SRS Section 4.5, 8.6)
Guarantees integrity of every state-changing action.
"""

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from packages.trust_kernel.db import db_manager
from packages.trust_kernel.interfaces import AuditInterface

GENESIS_HASH = "0000000000000000000000000000000000000000000000000000000000000000"


class InMemoryAuditService(AuditInterface):
    def __init__(self, load_db: bool = False):
        self._entries: list[dict[str, Any]] = []
        self._last_hash: str = GENESIS_HASH
        if load_db:
            self.load_from_db()

    def load_from_db(self) -> None:
        """Hydrates audit ledger from persistent database layer."""
        persisted = db_manager.load_all_audit_entries()
        if persisted:
            self._entries = persisted
            self._last_hash = persisted[-1]["hash"]
        else:
            self._entries = []
            self._last_hash = GENESIS_HASH

    def _compute_hash(self, entry_data: dict[str, Any], prev_hash: str) -> str:
        payload = json.dumps(entry_data, sort_keys=True, default=str) + prev_hash
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

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
        timestamp = datetime.now(timezone.utc).isoformat()
        entry_data = {
            "actor_id": actor_id,
            "actor_role": actor_role,
            "action": action,
            "object_type": object_type,
            "object_id": object_id,
            "ip": ip or "127.0.0.1",
            "meta": meta or {},
            "at": timestamp,
        }
        current_hash = self._compute_hash(entry_data, self._last_hash)
        full_record = {
            "id": f"audit-{len(self._entries) + 1:06d}",
            **entry_data,
            "prev_hash": self._last_hash,
            "hash": current_hash,
        }
        self._entries.append(full_record)
        self._last_hash = current_hash
        db_manager.save_audit_entry(full_record)
        return full_record

    def record_event(
        self,
        actor_id: str,
        action: str,
        object_type: str,
        object_id: str,
        description: str = "",
        metadata: dict[str, Any] | None = None,
        actor_role: str = "citizen",
        **kwargs: Any,
    ) -> dict[str, Any]:
        meta = dict(metadata or {})
        if description:
            meta["description"] = description
        meta.update(kwargs)
        return self.log(
            actor_id=actor_id,
            actor_role=actor_role,
            action=action,
            object_type=object_type,
            object_id=object_id,
            meta=meta,
        )

    def get_entries(
        self, actor_id: str | None = None, limit: int | None = None
    ) -> list[dict[str, Any]]:
        if actor_id:
            entries = [e for e in self._entries if e["actor_id"] == actor_id]
        else:
            entries = list(self._entries)
        if limit is not None and limit > 0:
            return entries[-limit:]
        return entries

    def verify_integrity(self) -> bool:
        prev = GENESIS_HASH
        for entry in self._entries:
            entry_data = {
                "actor_id": entry["actor_id"],
                "actor_role": entry["actor_role"],
                "action": entry["action"],
                "object_type": entry["object_type"],
                "object_id": entry["object_id"],
                "ip": entry["ip"],
                "meta": entry["meta"],
                "at": entry["at"],
            }
            computed = self._compute_hash(entry_data, entry["prev_hash"])
            if entry["prev_hash"] != prev or entry["hash"] != computed:
                return False
            prev = entry["hash"]
        return True

    verify_chain = verify_integrity

    def get_user_audit_extract(self, user_id: str) -> list[dict[str, Any]]:
        """Extract all audit log events involving the user (actor or target object) for GDPR/PDPO export."""
        return [
            e
            for e in self._entries
            if e.get("actor_id") == user_id
            or (e.get("object_type") == "user" and e.get("object_id") == user_id)
        ]

    def tamper_with_record(self, index: int, field: str, new_value: Any) -> None:
        """Simulates an unauthorized modification to test hash-chain tamper detection."""
        if 0 <= index < len(self._entries):
            self._entries[index][field] = new_value

    def clear(self) -> None:
        """Resets the audit ledger for clean testing."""
        self._entries.clear()
        self._last_hash = GENESIS_HASH

    append = log

    def get_recent_logs(self, limit: int = 10) -> list[dict[str, Any]]:
        """Returns the most recent audit log entries up to limit."""
        return list(reversed(self._entries[-limit:]))


audit_service = InMemoryAuditService(load_db=True)
audit_logger = audit_service
