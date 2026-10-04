"""
Database Layer & Persistence for Trust Kernel (SRS Section 2.2, 4.1, 8.6, 9.3 S1 Fixes).
Provides real database storage for Users, Devices, Consents, Audit Ledger, and Blocklist.
"""

import hashlib
import json
import os
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import (
    Boolean,
    Column,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    create_engine,
    text,
)
from sqlalchemy.orm import DeclarativeBase, sessionmaker


def get_db_url() -> str:
    return os.getenv("DATABASE_URL", "sqlite:///./ain_ai.db")


class Base(DeclarativeBase):
    pass


class UserDB(Base):
    __tablename__ = "trust_users"

    id = Column(String(64), primary_key=True)
    phone = Column(String(32), index=True, nullable=False)
    name = Column(String(255), nullable=True)
    role = Column(String(32), default="citizen", nullable=False)
    roles_json = Column(Text, default='["citizen"]', nullable=False)
    preferred_lang = Column(String(16), default="bn", nullable=False)
    numeral_style = Column(String(16), default="bn", nullable=False)
    status = Column(String(32), default="active", nullable=False)
    is_onboarded = Column(Boolean, default=False, nullable=False)
    created_at = Column(String(64), nullable=False)
    deleted_at = Column(String(64), nullable=True)


class DeviceDB(Base):
    __tablename__ = "trust_devices"

    id = Column(String(64), primary_key=True)
    user_id = Column(String(64), index=True, nullable=False)
    label = Column(String(128), nullable=False)
    last_seen_at = Column(String(64), nullable=True)
    revoked_at = Column(String(64), nullable=True)
    created_at = Column(String(64), nullable=False)


class ConsentDB(Base):
    __tablename__ = "trust_consents"

    id = Column(String(64), primary_key=True)
    grantor_id = Column(String(64), index=True, nullable=False)
    grantee_id = Column(String(64), index=True, nullable=False)
    scope = Column(String(64), nullable=False)
    permissions_json = Column(Text, nullable=False)
    starts_at = Column(String(64), nullable=False)
    expires_at = Column(String(64), nullable=False)
    revoked_at = Column(String(64), nullable=True)
    created_at = Column(String(64), nullable=False)


class AuditLogDB(Base):
    __tablename__ = "trust_audit_logs"

    id = Column(String(64), primary_key=True)
    at = Column(String(64), nullable=False)
    actor_id = Column(String(64), index=True, nullable=False)
    actor_role = Column(String(32), nullable=False)
    action = Column(String(64), nullable=False)
    object_type = Column(String(64), nullable=False)
    object_id = Column(String(64), nullable=False)
    ip = Column(String(64), nullable=True)
    meta_json = Column(Text, nullable=True)
    prev_hash = Column(String(64), nullable=False)
    hash = Column(String(64), nullable=False)


class BlockedPhoneHashDB(Base):
    __tablename__ = "trust_blocked_phone_hashes"

    phone_hash = Column(String(64), primary_key=True)
    created_at = Column(String(64), nullable=False)


class SourceDB(Base):
    __tablename__ = "sources"

    id = Column(String(36), primary_key=True)
    source_type = Column(String(32), nullable=False)
    title = Column(String(255), nullable=False)
    title_bn = Column(String(255), nullable=True)
    authority = Column(String(128), nullable=False)
    jurisdiction = Column(String(8), default="BD", nullable=False)
    language = Column(String(8), default="bn", nullable=False)
    official = Column(Boolean, default=True, nullable=False)
    rights = Column(String(32), default="official", nullable=False)
    url = Column(String(512), nullable=True)
    created_by = Column(String(36), nullable=True)
    created_at = Column(String(64), nullable=False)
    source_label = Column(String(64), default="FAKE_TEST_DATA", nullable=False)


class SourceVersionDB(Base):
    __tablename__ = "source_versions"

    id = Column(String(36), primary_key=True)
    source_id = Column(String(36), ForeignKey("sources.id"), nullable=False)
    version_label = Column(String(32), nullable=False)
    publication_date = Column(String(32), nullable=True)
    effective_from = Column(String(32), nullable=False)
    effective_to = Column(String(32), nullable=True)
    status = Column(String(32), default="draft", nullable=False)
    file_key = Column(String(255), nullable=True)
    reviewer_id = Column(String(36), nullable=True)
    reviewed_at = Column(String(64), nullable=True)
    approved_at = Column(String(64), nullable=True)
    uploader_id = Column(String(64), nullable=True)
    superseded_by_version_id = Column(String(64), nullable=True)
    approval_notes = Column(Text, nullable=True)


class SourcePassageDB(Base):
    __tablename__ = "source_passages"

    id = Column(String(36), primary_key=True)
    source_version_id = Column(String(36), ForeignKey("source_versions.id"), nullable=False)
    section_ref = Column(String(64), nullable=True)
    heading = Column(String(255), nullable=True)
    page_no = Column(Integer, nullable=True)
    text = Column(Text, nullable=False)
    tokens = Column(Integer, nullable=True)
    embedding_json = Column(Text, nullable=True)


class IngestionJobDB(Base):
    __tablename__ = "ingestion_jobs"

    id = Column(String(64), primary_key=True)
    source_id = Column(String(64), nullable=False)
    source_version_id = Column(String(64), nullable=False)
    step = Column(String(32), default="uploaded", nullable=False)
    status = Column(String(32), default="pending", nullable=False)
    details_json = Column(Text, default="{}", nullable=False)
    error_message = Column(Text, nullable=True)
    created_at = Column(String(64), nullable=False)
    updated_at = Column(String(64), nullable=False)


class RuleDB(Base):
    __tablename__ = "rules"

    id = Column(String(64), primary_key=True)
    rule_key = Column(String(64), nullable=True)
    title = Column(String(255), nullable=True)
    domain = Column(String(64), nullable=True)
    name = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    category = Column(String(64), nullable=True)
    created_at = Column(String(64), nullable=True)


class RuleVersionDB(Base):
    __tablename__ = "rule_versions"

    id = Column(String(64), primary_key=True)
    rule_id = Column(String(64), ForeignKey("rules.id"), nullable=False)
    version = Column(String(32), nullable=False)
    effective_from = Column(String(32), nullable=True)
    effective_to = Column(String(32), nullable=True)
    definition = Column(Text, nullable=True)
    status = Column(String(32), default="draft", nullable=True)
    parameters_schema_json = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=True)
    created_at = Column(String(64), nullable=True)


class RuleTestDB(Base):
    __tablename__ = "rule_tests"

    id = Column(String(64), primary_key=True)
    rule_id = Column(String(64), ForeignKey("rules.id"), nullable=False)
    version = Column(String(32), nullable=False)
    test_name = Column(String(255), nullable=False)
    input_json = Column(Text, nullable=False)
    expected_output_json = Column(Text, nullable=False)
    created_at = Column(String(64), nullable=False)


class PromptDB(Base):
    __tablename__ = "prompts"

    id = Column(String(64), primary_key=True)
    name = Column(String(128), nullable=False)
    version = Column(String(32), nullable=False)
    system_prompt = Column(Text, nullable=False)
    user_template = Column(Text, nullable=False)
    schema_json = Column(Text, nullable=False)
    created_at = Column(String(64), nullable=False)


class AIOutputDB(Base):
    __tablename__ = "ai_outputs"

    id = Column(String(64), primary_key=True)
    prompt_id = Column(String(64), nullable=True)
    prompt_version = Column(String(32), nullable=True)
    model = Column(String(64), nullable=False)
    raw_input = Column(Text, nullable=False)
    redacted_input = Column(Text, nullable=False)
    raw_output = Column(Text, nullable=False)
    unredacted_output = Column(Text, nullable=False)
    cost_tokens = Column(Integer, default=0, nullable=False)
    status = Column(String(32), default="success", nullable=False)
    security_flags = Column(Text, default="[]", nullable=True)
    created_at = Column(String(64), nullable=False)


class ClaimLinkDB(Base):
    __tablename__ = "claim_links"

    id = Column(String(64), primary_key=True)
    output_id = Column(String(64), ForeignKey("ai_outputs.id"), nullable=True)
    claim_text = Column(Text, nullable=False)
    source_id = Column(String(64), nullable=False)
    source_version_id = Column(String(64), nullable=False)
    section_ref = Column(String(64), nullable=True)
    verification_status = Column(String(32), default="UNVERIFIED", nullable=False)
    verification_score = Column(Float, default=0.0, nullable=False)
    details_json = Column(Text, default="{}", nullable=False)
    created_at = Column(String(64), nullable=False)


class EvalRunDB(Base):
    __tablename__ = "eval_runs"

    id = Column(String(64), primary_key=True)
    suite_name = Column(String(128), nullable=False)
    total_cases = Column(Integer, default=0, nullable=False)
    passed_cases = Column(Integer, default=0, nullable=False)
    failed_cases = Column(Integer, default=0, nullable=False)
    accuracy_rate = Column(Float, default=0.0, nullable=False)
    gate_passed = Column(Boolean, default=False, nullable=False)
    created_at = Column(String(64), nullable=False)


class EvalResultDB(Base):
    __tablename__ = "eval_results"

    id = Column(String(64), primary_key=True)
    run_id = Column(String(64), ForeignKey("eval_runs.id"), nullable=False)
    case_id = Column(String(64), nullable=False)
    input_summary = Column(Text, nullable=False)
    expected_output = Column(Text, nullable=False)
    actual_output = Column(Text, nullable=False)
    score = Column(Float, default=0.0, nullable=False)
    passed = Column(Boolean, default=False, nullable=False)
    latency_ms = Column(Float, default=0.0, nullable=False)
    created_at = Column(String(64), nullable=False)


class DocumentDB(Base):
    __tablename__ = "documents"

    id = Column(String(36), primary_key=True)
    owner_id = Column(String(36), nullable=False)
    case_id = Column(String(36), nullable=True)
    filename = Column(String(255), nullable=False)
    mime = Column(String(64), nullable=False)
    size_bytes = Column(Integer, nullable=False)
    sha256 = Column(String(64), index=True, nullable=False)
    storage_key = Column(String(255), nullable=False)
    doc_type = Column(String(64), nullable=True)
    language = Column(String(16), default="bn", nullable=True)
    processing_status = Column(String(32), default="uploaded", nullable=False)
    intent = Column(String(32), default="understand", nullable=False)
    uploaded_at = Column(String(64), nullable=False)
    deleted_at = Column(String(64), nullable=True)
    retry_count = Column(Integer, default=0, nullable=True)
    error_message = Column(Text, nullable=True)
    page_count = Column(Integer, default=1, nullable=True)


class DocumentPageDB(Base):
    __tablename__ = "document_pages"

    id = Column(String(36), primary_key=True)
    document_id = Column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    page_no = Column(Integer, nullable=False)
    image_key = Column(String(255), nullable=True)
    ocr_text = Column(Text, nullable=True)
    ocr_confidence = Column(Float, nullable=True)
    engine = Column(String(32), nullable=True)
    engine_version = Column(String(32), nullable=True)


class DocumentFieldDB(Base):
    __tablename__ = "document_fields"

    id = Column(String(36), primary_key=True)
    document_id = Column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    key = Column(String(64), nullable=False)
    value = Column(Text, nullable=True)
    confidence = Column(Float, nullable=True)
    confidence_word = Column(String(16), nullable=True)  # clear, check, not sure
    page_no = Column(Integer, nullable=True)
    bbox = Column(Text, nullable=True)
    crop_key = Column(String(255), nullable=True)
    state = Column(String(16), default="extracted", nullable=False)  # extracted -> reviewed -> verified
    reviewed_by = Column(String(36), nullable=True)
    reviewed_at = Column(String(64), nullable=True)
    verified_by = Column(String(36), nullable=True)
    verified_at = Column(String(64), nullable=True)


class DocumentUploadResumableDB(Base):
    __tablename__ = "document_uploads_resumable"

    upload_id = Column(String(64), primary_key=True)
    owner_id = Column(String(64), nullable=False)
    filename = Column(String(255), nullable=False)
    total_size = Column(Integer, nullable=False)
    total_chunks = Column(Integer, nullable=False)
    uploaded_chunks_json = Column(Text, nullable=False)
    sha256_hash = Column(String(64), nullable=False)
    temp_file_path = Column(String(255), nullable=False)
    created_at = Column(String(64), nullable=False)
    expires_at = Column(String(64), nullable=False)


class CaseDB(Base):
    __tablename__ = "cases"

    id = Column(String(36), primary_key=True)
    owner_id = Column(String(36), nullable=False)
    title = Column(String(255), nullable=False)
    case_type = Column(String(64), nullable=False)
    description = Column(Text, nullable=True)
    objective = Column(Text, nullable=True)
    urgency = Column(String(16), default="normal", nullable=False)
    status = Column(String(32), default="new", nullable=False)
    next_action_id = Column(String(36), nullable=True)
    closed_at = Column(String(64), nullable=True)
    created_at = Column(String(64), nullable=False)
    updated_at = Column(String(64), nullable=True)
    deleted_at = Column(String(64), nullable=True)
    legacy_matter_id = Column(String(64), nullable=True)
    metadata_json = Column(Text, nullable=True)
    triage_urgency = Column(String(32), nullable=True)
    is_urgent_triage = Column(Boolean, default=False, nullable=True)


class CasePartyDB(Base):
    __tablename__ = "case_parties"

    id = Column(String(64), primary_key=True)
    case_id = Column(String(64), ForeignKey("cases.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    role = Column(String(64), nullable=False)
    contact_info = Column(String(255), nullable=True)


class CaseEventDB(Base):
    __tablename__ = "case_events"

    id = Column(String(64), primary_key=True)
    case_id = Column(String(64), ForeignKey("cases.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(255), nullable=False)
    event_date = Column(String(32), nullable=False)
    date_precision = Column(String(16), default="day", nullable=False)
    description = Column(Text, nullable=True)
    event_type = Column(String(64), nullable=False)
    created_at = Column(String(64), nullable=False)


class CaseFactDB(Base):
    __tablename__ = "case_facts"

    id = Column(String(64), primary_key=True)
    case_id = Column(String(64), ForeignKey("cases.id", ondelete="CASCADE"), nullable=False)
    text = Column(Text, nullable=True)
    fact_text = Column(Text, nullable=True)
    source_ref = Column(String(64), nullable=True)
    source_doc_id = Column(String(64), nullable=True)
    state = Column(String(32), default="active", nullable=True)
    status = Column(String(32), default="active", nullable=False)
    is_proposed = Column(Boolean, default=False, nullable=False)
    created_at = Column(String(64), nullable=False)


class CaseNoteDB(Base):
    __tablename__ = "case_notes"

    id = Column(String(64), primary_key=True)
    case_id = Column(String(64), ForeignKey("cases.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(String(64), nullable=False)
    note_text = Column(Text, nullable=False)
    is_private = Column(Boolean, default=True, nullable=False)
    include_in_analysis = Column(Boolean, default=False, nullable=False)
    include_in_brief = Column(Boolean, default=False, nullable=False)
    created_at = Column(String(64), nullable=False)
    updated_at = Column(String(64), nullable=False)


class CaseDocumentDB(Base):
    __tablename__ = "case_documents"

    case_id = Column(String(64), ForeignKey("cases.id", ondelete="CASCADE"), primary_key=True, nullable=False)
    document_id = Column(String(64), ForeignKey("documents.id", ondelete="CASCADE"), primary_key=True, nullable=False)
    attached_at = Column(String(64), nullable=False)


class NotificationDB(Base):
    __tablename__ = "notifications"

    id = Column(String(64), primary_key=True)
    user_id = Column(String(64), nullable=False)
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    channel = Column(String(32), default="in_app", nullable=False)
    category = Column(String(64), nullable=False)
    deadline_id = Column(String(64), nullable=True)
    case_id = Column(String(64), nullable=True)
    scheduled_at = Column(String(64), nullable=False)
    sent_at = Column(String(64), nullable=True)
    status = Column(String(32), default="pending", nullable=False)
    retry_count = Column(Integer, default=0, nullable=False)
    error_message = Column(Text, nullable=True)
    created_at = Column(String(64), nullable=False)
    is_read = Column(Boolean, default=False, nullable=True)
    read_at = Column(String(64), nullable=True)
    kind = Column(String(32), default="system", nullable=True)
    title_key = Column(String(64), default="", nullable=True)
    body_key = Column(String(64), default="", nullable=True)


class NotificationPreferenceDB(Base):
    __tablename__ = "notification_preferences"

    user_id = Column(String(64), primary_key=True)
    enable_in_app = Column(Boolean, default=True, nullable=False)
    enable_sms = Column(Boolean, default=False, nullable=False)
    quiet_hours_enabled = Column(Boolean, default=True, nullable=False)
    quiet_hours_start = Column(String(8), default="22:00", nullable=False)
    quiet_hours_end = Column(String(8), default="07:00", nullable=False)
    language = Column(String(8), default="bn", nullable=False)
    updated_at = Column(String(64), nullable=False)


class TaskDB(Base):
    __tablename__ = "tasks"

    id = Column(String(36), primary_key=True)
    case_id = Column(String(36), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    owner_id = Column(String(36), nullable=False)
    assignee_id = Column(String(36), nullable=True)
    due_at = Column(String(64), nullable=True)
    priority = Column(String(16), default="normal", nullable=False)
    status = Column(String(32), default="not_started", nullable=False)
    origin = Column(String(16), default="user", nullable=False)
    related_document_id = Column(String(36), nullable=True)
    document_id = Column(String(64), nullable=True)
    created_at = Column(String(64), nullable=False)


class DeadlineDB(Base):
    __tablename__ = "deadlines"

    id = Column(String(36), primary_key=True)
    case_id = Column(String(36), nullable=False)
    title = Column(String(255), nullable=False)
    due_date = Column(String(32), nullable=False)
    rule_key = Column(String(64), nullable=True)
    rule_version = Column(String(16), nullable=True)
    calc_steps = Column(Text, nullable=True)
    assumptions = Column(Text, nullable=True)
    confirmed_by_user = Column(Boolean, default=False, nullable=False)
    confirmed_at = Column(String(64), nullable=True)
    status = Column(String(32), default="upcoming", nullable=False)
    source_ref = Column(Text, nullable=True)
    document_id = Column(String(64), nullable=True)
    user_id = Column(String(64), nullable=True)
    calculation_basis = Column(Text, nullable=True)
    is_user_set = Column(Boolean, default=False, nullable=False)
    created_at = Column(String(64), nullable=False)


class ReminderScheduleDB(Base):
    __tablename__ = "reminder_schedules"

    id = Column(String(64), primary_key=True)
    deadline_id = Column(String(64), ForeignKey("deadlines.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(String(64), nullable=False)
    offset_days = Column(Integer, nullable=False)
    scheduled_at = Column(String(64), nullable=False)
    channel = Column(String(32), default="in_app", nullable=False)
    status = Column(String(32), default="pending", nullable=False)
    created_at = Column(String(64), nullable=False)


class NoticeAnalysisDB(Base):
    __tablename__ = "notice_analyses"

    id = Column(String(64), primary_key=True)
    document_id = Column(String(64), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, unique=True)
    user_id = Column(String(64), nullable=False)
    analysis_json = Column(Text, nullable=False)
    simpler_json = Column(Text, nullable=True)
    certainty = Column(String(32), nullable=False)
    as_of_date = Column(String(32), nullable=False)
    created_at = Column(String(64), nullable=False)
    updated_at = Column(String(64), nullable=False)


class DatabaseManager:
    _clock_fn: Any = None

    @classmethod
    def set_clock(cls, clock: Any = None) -> None:
        cls._clock_fn = clock

    @classmethod
    def reset_clock(cls) -> None:
        cls._clock_fn = None

    @classmethod
    def get_current_time(cls) -> datetime:
        if cls._clock_fn is not None:
            if callable(cls._clock_fn):
                return cls._clock_fn()
            return cls._clock_fn
        return datetime.now(timezone.utc)

    def __init__(self, db_url: str | None = None):
        self.url = db_url or get_db_url()
        connect_args = {}
        if self.url.startswith("sqlite"):
            connect_args = {"check_same_thread": False}
        self.engine = create_engine(self.url, connect_args=connect_args, echo=False)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        self.init_schema()

    def init_schema(self):
        Base.metadata.create_all(bind=self.engine)
        # Ensure added columns in existing tables are present for SQLite
        with self.engine.connect() as conn:
            for col_def in [
                ("rules", "name", "TEXT"),
                ("rules", "description", "TEXT"),
                ("rules", "category", "VARCHAR(64)"),
                ("rules", "created_at", "VARCHAR(64)"),
                ("rule_versions", "parameters_schema_json", "TEXT"),
                ("rule_versions", "is_active", "BOOLEAN DEFAULT 1"),
                ("rule_versions", "created_at", "VARCHAR(64)"),
                ("ai_outputs", "prompt_version", "VARCHAR(32)"),
                ("ai_outputs", "security_flags", "TEXT DEFAULT '[]'"),
                ("documents", "retry_count", "INTEGER DEFAULT 0"),
                ("documents", "error_message", "TEXT"),
                ("documents", "page_count", "INTEGER DEFAULT 1"),
                ("document_fields", "confidence_word", "VARCHAR(16)"),
                ("deadlines", "document_id", "VARCHAR(64)"),
                ("deadlines", "user_id", "VARCHAR(64)"),
                ("deadlines", "calculation_basis", "TEXT"),
                ("deadlines", "is_user_set", "BOOLEAN DEFAULT 0"),
                ("tasks", "document_id", "VARCHAR(64)"),
                ("cases", "legacy_matter_id", "VARCHAR(64)"),
                ("cases", "metadata_json", "TEXT"),
                ("case_parties", "contact_info", "VARCHAR(255)"),
                ("case_events", "date_precision", "VARCHAR(16) DEFAULT 'day'"),
                ("case_events", "event_type", "VARCHAR(64) DEFAULT 'other'"),
                ("case_facts", "fact_text", "TEXT"),
                ("case_facts", "source_doc_id", "VARCHAR(64)"),
                ("case_facts", "status", "VARCHAR(32) DEFAULT 'active'"),
                ("case_facts", "is_proposed", "BOOLEAN DEFAULT 0"),
                ("notifications", "title", "VARCHAR(255)"),
                ("notifications", "message", "TEXT"),
                ("notifications", "channel", "VARCHAR(32) DEFAULT 'in_app'"),
                ("notifications", "category", "VARCHAR(64) DEFAULT 'general'"),
                ("notifications", "deadline_id", "VARCHAR(64)"),
                ("notifications", "case_id", "VARCHAR(64)"),
                ("notifications", "scheduled_at", "VARCHAR(64)"),
                ("notifications", "sent_at", "VARCHAR(64)"),
                ("notifications", "status", "VARCHAR(32) DEFAULT 'pending'"),
                ("notifications", "retry_count", "INTEGER DEFAULT 0"),
                ("notifications", "error_message", "TEXT"),
                ("notifications", "is_read", "BOOLEAN DEFAULT 0"),
                ("notifications", "read_at", "VARCHAR(64)"),
                ("case_notes", "include_in_brief", "BOOLEAN DEFAULT 0"),
                ("cases", "triage_urgency", "VARCHAR(32)"),
                ("cases", "is_urgent_triage", "BOOLEAN DEFAULT 0"),
            ]:
                table, col, col_type = col_def
                try:
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {col} {col_type}"))
                    conn.commit()
                except Exception:
                    pass

    def get_session(self):
        return self.SessionLocal()

    # User operations
    def save_user(self, user: dict[str, Any]):
        with self.get_session() as session:
            record = session.query(UserDB).filter(UserDB.id == user["id"]).first()
            if not record:
                record = UserDB(id=user["id"])
                session.add(record)
            record.phone = user.get("phone", "")
            record.name = user.get("name")
            record.role = user.get("role", "citizen")
            record.roles_json = json.dumps(user.get("roles", [record.role]))
            record.preferred_lang = user.get("preferred_lang", "bn")
            record.numeral_style = user.get("numeral_style", "bn")
            record.status = user.get("status", "active")
            record.is_onboarded = bool(user.get("is_onboarded", False))
            record.created_at = str(user.get("created_at", datetime.now(timezone.utc).isoformat()))
            record.deleted_at = user.get("deleted_at")
            session.commit()

    def load_all_users(self) -> list[dict[str, Any]]:
        with self.get_session() as session:
            rows = session.query(UserDB).all()
            return [
                {
                    "id": r.id,
                    "phone": r.phone,
                    "name": r.name,
                    "role": r.role,
                    "roles": json.loads(r.roles_json) if r.roles_json else [r.role],
                    "preferred_lang": r.preferred_lang,
                    "numeral_style": r.numeral_style,
                    "status": r.status,
                    "is_onboarded": r.is_onboarded,
                    "created_at": r.created_at,
                    "deleted_at": r.deleted_at,
                }
                for r in rows
            ]

    def get_user(self, user_id: str) -> dict[str, Any] | None:
        with self.get_session() as session:
            r = session.query(UserDB).filter(UserDB.id == user_id).first()
            if not r:
                return None
            return {
                "id": r.id,
                "phone": r.phone,
                "name": r.name,
                "role": r.role,
                "roles": json.loads(r.roles_json) if r.roles_json else [r.role],
                "preferred_lang": r.preferred_lang,
                "numeral_style": r.numeral_style,
                "status": r.status,
                "is_onboarded": r.is_onboarded,
                "created_at": r.created_at,
                "deleted_at": r.deleted_at,
            }

    # Device operations
    def save_device(self, dev: dict[str, Any]):
        with self.get_session() as session:
            record = session.query(DeviceDB).filter(DeviceDB.id == dev["id"]).first()
            if not record:
                record = DeviceDB(id=dev["id"])
                session.add(record)
            record.user_id = dev.get("user_id", "")
            record.label = dev.get("label", "Default Device")
            record.last_seen_at = dev.get("last_seen_at")
            record.revoked_at = dev.get("revoked_at")
            record.created_at = str(dev.get("created_at", datetime.now(timezone.utc).isoformat()))
            session.commit()

    def load_all_devices(self) -> list[dict[str, Any]]:
        with self.get_session() as session:
            rows = session.query(DeviceDB).all()
            return [
                {
                    "id": r.id,
                    "user_id": r.user_id,
                    "label": r.label,
                    "last_seen_at": r.last_seen_at,
                    "revoked_at": r.revoked_at,
                    "created_at": r.created_at,
                }
                for r in rows
            ]

    # Consent operations
    def save_consent(self, consent: dict[str, Any]):
        with self.get_session() as session:
            record = session.query(ConsentDB).filter(ConsentDB.id == consent["id"]).first()
            if not record:
                record = ConsentDB(id=consent["id"])
                session.add(record)
            record.grantor_id = consent.get("grantor_id", "")
            record.grantee_id = consent.get("grantee_id", "")
            record.scope = consent.get("scope", "")
            record.permissions_json = json.dumps(consent.get("permissions", []))
            record.starts_at = str(consent.get("starts_at", ""))
            record.expires_at = str(consent.get("expires_at", ""))
            record.revoked_at = str(consent["revoked_at"]) if consent.get("revoked_at") else None
            record.created_at = str(
                consent.get("created_at", datetime.now(timezone.utc).isoformat())
            )
            session.commit()

    def load_all_consents(self) -> list[dict[str, Any]]:
        with self.get_session() as session:
            rows = session.query(ConsentDB).all()
            return [
                {
                    "id": r.id,
                    "grantor_id": r.grantor_id,
                    "grantee_id": r.grantee_id,
                    "scope": r.scope,
                    "permissions": json.loads(r.permissions_json) if r.permissions_json else [],
                    "starts_at": r.starts_at,
                    "expires_at": r.expires_at,
                    "revoked_at": r.revoked_at,
                    "created_at": r.created_at,
                }
                for r in rows
            ]

    def has_active_consent(self, grantor_id: str, grantee_id: str, scope: str) -> bool:
        with self.get_session() as session:
            row = (
                session.query(ConsentDB)
                .filter(
                    ConsentDB.grantor_id == grantor_id,
                    ConsentDB.grantee_id == grantee_id,
                    ConsentDB.scope == scope,
                )
                .first()
            )
            if not row:
                return False
            if row.revoked_at:
                return False
            if row.expires_at:
                try:
                    exp = datetime.fromisoformat(row.expires_at)
                    if datetime.now(timezone.utc) > exp:
                        return False
                except Exception:
                    pass
            return True

    # Audit operations
    def save_audit_entry(self, entry: dict[str, Any]):
        with self.get_session() as session:
            record = session.query(AuditLogDB).filter(AuditLogDB.id == entry["id"]).first()
            if not record:
                record = AuditLogDB(id=entry["id"])
                session.add(record)
            record.at = str(entry.get("at", datetime.now(timezone.utc).isoformat()))
            record.actor_id = str(entry.get("actor_id", ""))
            record.actor_role = str(entry.get("actor_role", "user"))
            record.action = str(entry.get("action", ""))
            record.object_type = str(entry.get("object_type", ""))
            record.object_id = str(entry.get("object_id", ""))
            record.ip = entry.get("ip", "127.0.0.1")
            record.meta_json = json.dumps(entry.get("meta", {}))
            record.prev_hash = str(entry.get("prev_hash", ""))
            record.hash = str(entry.get("hash", ""))
            session.commit()

    def load_all_audit_entries(self) -> list[dict[str, Any]]:
        with self.get_session() as session:
            rows = session.query(AuditLogDB).order_by(AuditLogDB.id.asc()).all()
            return [
                {
                    "id": r.id,
                    "at": r.at,
                    "actor_id": r.actor_id,
                    "actor_role": r.actor_role,
                    "action": r.action,
                    "object_type": r.object_type,
                    "object_id": r.object_id,
                    "ip": r.ip,
                    "meta": json.loads(r.meta_json) if r.meta_json else {},
                    "prev_hash": r.prev_hash,
                    "hash": r.hash,
                }
                for r in rows
            ]

    def record_audit_event(
        self,
        actor_id: str,
        actor_type: str,
        action: str,
        object_type: str,
        object_id: str,
        details: dict[str, Any] | None = None,
    ):
        entry_id = f"aud-{uuid.uuid4().hex[:12]}"
        self.save_audit_entry({
            "id": entry_id,
            "actor_id": actor_id,
            "actor_role": actor_type,
            "action": action,
            "object_type": object_type,
            "object_id": object_id,
            "meta": details or {},
        })

    def get_audit_logs(self, object_id: str | None = None) -> list[dict[str, Any]]:
        entries = self.load_all_audit_entries()
        if object_id:
            entries = [e for e in entries if e.get("object_id") == object_id]
        return entries

    # Blocked phone hashes
    def save_blocked_phone_hash(self, phone_hash: str):
        with self.get_session() as session:
            record = (
                session.query(BlockedPhoneHashDB)
                .filter(BlockedPhoneHashDB.phone_hash == phone_hash)
                .first()
            )
            if not record:
                record = BlockedPhoneHashDB(
                    phone_hash=phone_hash, created_at=datetime.now(timezone.utc).isoformat()
                )
                session.add(record)
                session.commit()

    def load_all_blocked_phone_hashes(self) -> set[str]:
        with self.get_session() as session:
            rows = session.query(BlockedPhoneHashDB).all()
            return {r.phone_hash for r in rows}

    # Sources operations
    def save_source(self, data: dict[str, Any]):
        with self.get_session() as session:
            record = session.query(SourceDB).filter(SourceDB.id == data["id"]).first()
            if not record:
                record = SourceDB(id=data["id"])
                session.add(record)
            record.source_type = data.get("source_type", "statute")
            record.title = data.get("title", "")
            record.title_bn = data.get("title_bn")
            record.authority = data.get("authority", "Parliament of Bangladesh")
            record.jurisdiction = data.get("jurisdiction", "BD")
            record.language = data.get("language", "bn")
            record.official = bool(data.get("official", True))
            record.rights = data.get("rights", "official")
            record.url = data.get("url")
            record.created_by = data.get("created_by")
            record.created_at = str(data.get("created_at", datetime.now(timezone.utc).isoformat()))
            record.source_label = data.get("source_label", "FAKE_TEST_DATA")
            session.commit()

    def get_source(self, source_id: str) -> dict[str, Any] | None:
        with self.get_session() as session:
            r = session.query(SourceDB).filter(SourceDB.id == source_id).first()
            if not r:
                return None
            return {
                "id": r.id,
                "source_type": r.source_type,
                "title": r.title,
                "title_bn": r.title_bn,
                "authority": r.authority,
                "jurisdiction": r.jurisdiction,
                "language": r.language,
                "official": r.official,
                "rights": r.rights,
                "url": r.url,
                "created_by": r.created_by,
                "created_at": r.created_at,
                "source_label": r.source_label,
            }

    def list_sources(self, filters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        with self.get_session() as session:
            q = session.query(SourceDB)
            if filters:
                if "source_type" in filters:
                    q = q.filter(SourceDB.source_type == filters["source_type"])
                if "jurisdiction" in filters:
                    q = q.filter(SourceDB.jurisdiction == filters["jurisdiction"])
                if "rights" in filters:
                    q = q.filter(SourceDB.rights == filters["rights"])
            rows = q.order_by(SourceDB.created_at.desc()).all()
            return [
                {
                    "id": r.id,
                    "source_type": r.source_type,
                    "title": r.title,
                    "title_bn": r.title_bn,
                    "authority": r.authority,
                    "jurisdiction": r.jurisdiction,
                    "language": r.language,
                    "official": r.official,
                    "rights": r.rights,
                    "url": r.url,
                    "created_by": r.created_by,
                    "created_at": r.created_at,
                    "source_label": r.source_label,
                }
                for r in rows
            ]

    # Source versions operations
    def save_source_version(self, data: dict[str, Any]):
        with self.get_session() as session:
            record = session.query(SourceVersionDB).filter(SourceVersionDB.id == data["id"]).first()
            if not record:
                record = SourceVersionDB(id=data["id"])
                session.add(record)
            record.source_id = data.get("source_id", "")
            record.version_label = data.get("version_label", "1.0")
            record.publication_date = data.get("publication_date")
            record.effective_from = str(data.get("effective_from", ""))
            record.effective_to = str(data["effective_to"]) if data.get("effective_to") else None
            record.status = data.get("status", "draft")
            record.file_key = data.get("file_key")
            record.reviewer_id = data.get("reviewer_id")
            record.reviewed_at = data.get("reviewed_at")
            record.approved_at = data.get("approved_at")
            record.uploader_id = data.get("uploader_id")
            record.superseded_by_version_id = data.get("superseded_by_version_id")
            record.approval_notes = data.get("approval_notes")
            session.commit()

    def get_source_version(self, version_id: str) -> dict[str, Any] | None:
        with self.get_session() as session:
            r = session.query(SourceVersionDB).filter(SourceVersionDB.id == version_id).first()
            if not r:
                return None
            return {
                "id": r.id,
                "source_id": r.source_id,
                "version_label": r.version_label,
                "publication_date": r.publication_date,
                "effective_from": r.effective_from,
                "effective_to": r.effective_to,
                "status": r.status,
                "file_key": r.file_key,
                "reviewer_id": r.reviewer_id,
                "reviewed_at": r.reviewed_at,
                "approved_at": r.approved_at,
                "uploader_id": r.uploader_id,
                "superseded_by_version_id": r.superseded_by_version_id,
                "approval_notes": r.approval_notes,
            }

    def list_source_versions(
        self, source_id: str | None = None, status: str | None = None
    ) -> list[dict[str, Any]]:
        with self.get_session() as session:
            q = session.query(SourceVersionDB)
            if source_id:
                q = q.filter(SourceVersionDB.source_id == source_id)
            if status:
                q = q.filter(SourceVersionDB.status == status)
            rows = q.order_by(SourceVersionDB.effective_from.asc()).all()
            return [
                {
                    "id": r.id,
                    "source_id": r.source_id,
                    "version_label": r.version_label,
                    "publication_date": r.publication_date,
                    "effective_from": r.effective_from,
                    "effective_to": r.effective_to,
                    "status": r.status,
                    "file_key": r.file_key,
                    "reviewer_id": r.reviewer_id,
                    "reviewed_at": r.reviewed_at,
                    "approved_at": r.approved_at,
                    "uploader_id": r.uploader_id,
                    "superseded_by_version_id": r.superseded_by_version_id,
                    "approval_notes": r.approval_notes,
                }
                for r in rows
            ]

    # Source Passages operations
    def save_source_passages(self, passages: list[dict[str, Any]]):
        with self.get_session() as session:
            for p in passages:
                record = (
                    session.query(SourcePassageDB).filter(SourcePassageDB.id == p["id"]).first()
                )
                if not record:
                    record = SourcePassageDB(id=p["id"])
                    session.add(record)
                record.source_version_id = p.get("source_version_id", "")
                record.section_ref = p.get("section_ref")
                record.heading = p.get("heading")
                record.page_no = p.get("page_no")
                record.text = p.get("text", "")
                record.tokens = p.get("tokens", len(record.text.split()))
                if "embedding" in p and p["embedding"]:
                    record.embedding_json = json.dumps(p["embedding"])
                elif "embedding_json" in p:
                    record.embedding_json = p["embedding_json"]
            session.commit()

    def get_source_passages(self, version_id: str) -> list[dict[str, Any]]:
        with self.get_session() as session:
            rows = (
                session.query(SourcePassageDB)
                .filter(SourcePassageDB.source_version_id == version_id)
                .all()
            )
            return [
                {
                    "id": r.id,
                    "source_version_id": r.source_version_id,
                    "section_ref": r.section_ref,
                    "heading": r.heading,
                    "page_no": r.page_no,
                    "text": r.text,
                    "tokens": r.tokens,
                    "embedding": json.loads(r.embedding_json) if r.embedding_json else None,
                }
                for r in rows
            ]

    def get_passage(self, passage_id: str) -> dict[str, Any] | None:
        with self.get_session() as session:
            r = session.query(SourcePassageDB).filter(SourcePassageDB.id == passage_id).first()
            if not r:
                return None
            return {
                "id": r.id,
                "source_version_id": r.source_version_id,
                "section_ref": r.section_ref,
                "heading": r.heading,
                "page_no": r.page_no,
                "text": r.text,
                "tokens": r.tokens,
                "embedding": json.loads(r.embedding_json) if r.embedding_json else None,
            }

    # Ingestion Jobs operations
    def save_ingestion_job(self, job: dict[str, Any]):
        with self.get_session() as session:
            record = session.query(IngestionJobDB).filter(IngestionJobDB.id == job["id"]).first()
            if not record:
                record = IngestionJobDB(id=job["id"])
                session.add(record)
            record.source_id = job.get("source_id", "")
            record.source_version_id = job.get("source_version_id", "")
            record.step = job.get("step", "uploaded")
            record.status = job.get("status", "pending")
            record.details_json = json.dumps(job.get("details", {}))
            record.error_message = job.get("error_message")
            record.created_at = str(job.get("created_at", datetime.now(timezone.utc).isoformat()))
            record.updated_at = str(job.get("updated_at", datetime.now(timezone.utc).isoformat()))
            session.commit()

    def get_ingestion_job(self, job_id: str) -> dict[str, Any] | None:
        with self.get_session() as session:
            r = session.query(IngestionJobDB).filter(IngestionJobDB.id == job_id).first()
            if not r:
                return None
            return {
                "id": r.id,
                "source_id": r.source_id,
                "source_version_id": r.source_version_id,
                "step": r.step,
                "status": r.status,
                "details": json.loads(r.details_json) if r.details_json else {},
                "error_message": r.error_message,
                "created_at": r.created_at,
                "updated_at": r.updated_at,
            }

    def list_ingestion_jobs(self, source_id: str | None = None) -> list[dict[str, Any]]:
        with self.get_session() as session:
            q = session.query(IngestionJobDB)
            if source_id:
                q = q.filter(IngestionJobDB.source_id == source_id)
            rows = q.order_by(IngestionJobDB.created_at.desc()).all()
            return [
                {
                    "id": r.id,
                    "source_id": r.source_id,
                    "source_version_id": r.source_version_id,
                    "step": r.step,
                    "status": r.status,
                    "details": json.loads(r.details_json) if r.details_json else {},
                    "error_message": r.error_message,
                    "created_at": r.created_at,
                    "updated_at": r.updated_at,
                }
                for r in rows
            ]

    # Rules Engine Persistence
    def save_rule(self, rule: dict[str, Any]):
        with self.get_session() as session:
            record = session.query(RuleDB).filter(RuleDB.id == rule["id"]).first()
            if not record:
                record = RuleDB(id=rule["id"])
                session.add(record)
            record.rule_key = rule.get("rule_key", rule["id"])
            record.title = rule.get("title", rule["name"])
            record.domain = rule.get("domain", rule.get("category", "statutory"))
            record.name = rule["name"]
            record.description = rule["description"]
            record.category = rule.get("category", "statutory")
            record.created_at = str(rule.get("created_at", datetime.now(timezone.utc).isoformat()))
            session.commit()

    def get_rule(self, rule_id: str) -> dict[str, Any] | None:
        with self.get_session() as session:
            r = session.query(RuleDB).filter(RuleDB.id == rule_id).first()
            if not r:
                return None
            return {
                "id": r.id,
                "name": r.name or r.title,
                "description": r.description,
                "category": r.category or r.domain,
                "created_at": r.created_at,
            }

    def list_rules(self) -> list[dict[str, Any]]:
        with self.get_session() as session:
            rows = session.query(RuleDB).order_by(RuleDB.id.desc()).all()
            return [
                {
                    "id": r.id,
                    "name": r.name or r.title,
                    "description": r.description,
                    "category": r.category or r.domain,
                    "created_at": r.created_at,
                }
                for r in rows
            ]

    def save_rule_version(self, rv: dict[str, Any]):
        with self.get_session() as session:
            record = session.query(RuleVersionDB).filter(RuleVersionDB.id == rv["id"]).first()
            if not record:
                record = RuleVersionDB(id=rv["id"])
                session.add(record)
            record.rule_id = rv["rule_id"]
            record.version = rv["version"]
            record.effective_from = rv.get("effective_from", "1971-01-01")
            record.effective_to = rv.get("effective_to")
            record.definition = json.dumps(rv.get("definition", rv.get("parameters_schema", {}))) if isinstance(rv.get("definition", rv.get("parameters_schema")), (dict, list)) else "{}"
            record.status = rv.get("status", "approved" if rv.get("is_active", True) else "draft")
            record.parameters_schema_json = json.dumps(rv.get("parameters_schema", {})) if isinstance(rv.get("parameters_schema"), (dict, list)) else rv.get("parameters_schema_json", "{}")
            record.is_active = bool(rv.get("is_active", True))
            record.created_at = str(rv.get("created_at", datetime.now(timezone.utc).isoformat()))
            session.commit()

    def list_rule_versions(self, rule_id: str) -> list[dict[str, Any]]:
        with self.get_session() as session:
            rows = session.query(RuleVersionDB).filter(RuleVersionDB.rule_id == rule_id).all()
            return [
                {
                    "id": r.id,
                    "rule_id": r.rule_id,
                    "version": r.version,
                    "parameters_schema": json.loads(r.parameters_schema_json) if r.parameters_schema_json else {},
                    "is_active": r.is_active,
                    "created_at": r.created_at,
                }
                for r in rows
            ]

    def save_rule_test(self, test: dict[str, Any]):
        with self.get_session() as session:
            record = session.query(RuleTestDB).filter(RuleTestDB.id == test["id"]).first()
            if not record:
                record = RuleTestDB(id=test["id"])
                session.add(record)
            record.rule_id = test["rule_id"]
            record.version = test["version"]
            record.test_name = test["test_name"]
            record.input_json = json.dumps(test.get("input_data", {})) if isinstance(test.get("input_data"), (dict, list)) else test.get("input_json", "{}")
            record.expected_output_json = json.dumps(test.get("expected_output", {})) if isinstance(test.get("expected_output"), (dict, list)) else test.get("expected_output_json", "{}")
            record.created_at = str(test.get("created_at", datetime.now(timezone.utc).isoformat()))
            session.commit()

    def list_rule_tests(self, rule_id: str, version: str | None = None) -> list[dict[str, Any]]:
        with self.get_session() as session:
            q = session.query(RuleTestDB).filter(RuleTestDB.rule_id == rule_id)
            if version:
                q = q.filter(RuleTestDB.version == version)
            rows = q.all()
            return [
                {
                    "id": r.id,
                    "rule_id": r.rule_id,
                    "version": r.version,
                    "test_name": r.test_name,
                    "input_data": json.loads(r.input_json) if r.input_json else {},
                    "expected_output": json.loads(r.expected_output_json) if r.expected_output_json else {},
                    "created_at": r.created_at,
                }
                for r in rows
            ]

    # AI Gateway Persistence
    def save_prompt(self, prompt: dict[str, Any]):
        with self.get_session() as session:
            record = session.query(PromptDB).filter(PromptDB.id == prompt["id"]).first()
            if not record:
                record = PromptDB(id=prompt["id"])
                session.add(record)
            record.name = prompt["name"]
            record.version = prompt["version"]
            record.system_prompt = prompt["system_prompt"]
            record.user_template = prompt["user_template"]
            record.schema_json = json.dumps(prompt.get("schema", {})) if isinstance(prompt.get("schema"), (dict, list)) else prompt.get("schema_json", "{}")
            record.created_at = str(prompt.get("created_at", datetime.now(timezone.utc).isoformat()))
            session.commit()

    def get_prompt(self, prompt_id: str) -> dict[str, Any] | None:
        with self.get_session() as session:
            r = session.query(PromptDB).filter(PromptDB.id == prompt_id).first()
            if not r:
                return None
            return {
                "id": r.id,
                "name": r.name,
                "version": r.version,
                "system_prompt": r.system_prompt,
                "user_template": r.user_template,
                "schema": json.loads(r.schema_json) if r.schema_json else {},
                "created_at": r.created_at,
            }

    def save_ai_output(self, output: dict[str, Any]):
        with self.get_session() as session:
            record = session.query(AIOutputDB).filter(AIOutputDB.id == output["id"]).first()
            if not record:
                record = AIOutputDB(id=output["id"])
                session.add(record)
            record.prompt_id = output.get("prompt_id")
            record.prompt_version = output.get("prompt_version")
            record.model = output["model"]
            record.raw_input = output["raw_input"]
            record.redacted_input = output["redacted_input"]
            record.raw_output = output["raw_output"]
            record.unredacted_output = output["unredacted_output"]
            record.cost_tokens = int(output.get("cost_tokens", 0))
            record.status = output.get("status", "success")
            sec_flags = output.get("security_flags", [])
            record.security_flags = json.dumps(sec_flags) if isinstance(sec_flags, list) else str(sec_flags)
            record.created_at = str(output.get("created_at", datetime.now(timezone.utc).isoformat()))
            session.commit()

    def get_ai_output(self, output_id: str) -> dict[str, Any] | None:
        with self.get_session() as session:
            r = session.query(AIOutputDB).filter(AIOutputDB.id == output_id).first()
            if not r:
                return None
            return {
                "id": r.id,
                "prompt_id": r.prompt_id,
                "prompt_version": r.prompt_version,
                "model": r.model,
                "raw_input": r.raw_input,
                "redacted_input": r.redacted_input,
                "raw_output": r.raw_output,
                "unredacted_output": r.unredacted_output,
                "cost_tokens": r.cost_tokens,
                "status": r.status,
                "security_flags": json.loads(r.security_flags) if r.security_flags else [],
                "created_at": r.created_at,
            }

    def get_last_ai_output(self) -> dict[str, Any] | None:
        with self.get_session() as session:
            r = session.query(AIOutputDB).order_by(AIOutputDB.created_at.desc()).first()
            if not r:
                return None
            return {
                "id": r.id,
                "prompt_id": r.prompt_id,
                "prompt_version": r.prompt_version,
                "model": r.model,
                "raw_input": r.raw_input,
                "redacted_input": r.redacted_input,
                "raw_output": r.raw_output,
                "unredacted_output": r.unredacted_output,
                "cost_tokens": r.cost_tokens,
                "status": r.status,
                "security_flags": json.loads(r.security_flags) if r.security_flags else [],
                "created_at": r.created_at,
            }

    def save_claim_link(self, claim: dict[str, Any]):
        with self.get_session() as session:
            record = session.query(ClaimLinkDB).filter(ClaimLinkDB.id == claim["id"]).first()
            if not record:
                record = ClaimLinkDB(id=claim["id"])
                session.add(record)
            record.output_id = claim.get("output_id")
            record.claim_text = claim["claim_text"]
            record.source_id = claim["source_id"]
            record.source_version_id = claim["source_version_id"]
            record.section_ref = claim.get("section_ref")
            record.verification_status = claim.get("verification_status", "UNVERIFIED")
            record.verification_score = float(claim.get("verification_score", 0.0))
            record.details_json = json.dumps(claim.get("details", {})) if isinstance(claim.get("details"), (dict, list)) else claim.get("details_json", "{}")
            record.created_at = str(claim.get("created_at", datetime.now(timezone.utc).isoformat()))
            session.commit()

    def list_claim_links(self, output_id: str | None = None) -> list[dict[str, Any]]:
        with self.get_session() as session:
            q = session.query(ClaimLinkDB)
            if output_id:
                q = q.filter(ClaimLinkDB.output_id == output_id)
            rows = q.all()
            return [
                {
                    "id": r.id,
                    "output_id": r.output_id,
                    "claim_text": r.claim_text,
                    "source_id": r.source_id,
                    "source_version_id": r.source_version_id,
                    "section_ref": r.section_ref,
                    "verification_status": r.verification_status,
                    "verification_score": r.verification_score,
                    "details": json.loads(r.details_json) if r.details_json else {},
                    "created_at": r.created_at,
                }
                for r in rows
            ]

    # Eval Harness Persistence
    def save_eval_run(self, run: dict[str, Any]):
        with self.get_session() as session:
            record = session.query(EvalRunDB).filter(EvalRunDB.id == run["id"]).first()
            if not record:
                record = EvalRunDB(id=run["id"])
                session.add(record)
            record.suite_name = run["suite_name"]
            record.total_cases = int(run.get("total_cases", 0))
            record.passed_cases = int(run.get("passed_cases", 0))
            record.failed_cases = int(run.get("failed_cases", 0))
            record.accuracy_rate = float(run.get("accuracy_rate", 0.0))
            record.gate_passed = bool(run.get("gate_passed", False))
            record.created_at = str(run.get("created_at", datetime.now(timezone.utc).isoformat()))
            session.commit()

    def get_eval_run(self, run_id: str) -> dict[str, Any] | None:
        with self.get_session() as session:
            r = session.query(EvalRunDB).filter(EvalRunDB.id == run_id).first()
            if not r:
                return None
            return {
                "id": r.id,
                "suite_name": r.suite_name,
                "total_cases": r.total_cases,
                "passed_cases": r.passed_cases,
                "failed_cases": r.failed_cases,
                "accuracy_rate": r.accuracy_rate,
                "gate_passed": r.gate_passed,
                "created_at": r.created_at,
            }

    def list_eval_runs(self) -> list[dict[str, Any]]:
        with self.get_session() as session:
            rows = session.query(EvalRunDB).order_by(EvalRunDB.created_at.desc()).all()
            return [
                {
                    "id": r.id,
                    "suite_name": r.suite_name,
                    "total_cases": r.total_cases,
                    "passed_cases": r.passed_cases,
                    "failed_cases": r.failed_cases,
                    "accuracy_rate": r.accuracy_rate,
                    "gate_passed": r.gate_passed,
                    "created_at": r.created_at,
                }
                for r in rows
            ]

    def save_eval_result(self, res: dict[str, Any]):
        with self.get_session() as session:
            record = session.query(EvalResultDB).filter(EvalResultDB.id == res["id"]).first()
            if not record:
                record = EvalResultDB(id=res["id"])
                session.add(record)
            record.run_id = res["run_id"]
            record.case_id = res["case_id"]
            record.input_summary = res["input_summary"]
            record.expected_output = res["expected_output"]
            record.actual_output = res["actual_output"]
            record.score = float(res.get("score", 0.0))
            record.passed = bool(res.get("passed", False))
            record.latency_ms = float(res.get("latency_ms", 0.0))
            record.created_at = str(res.get("created_at", datetime.now(timezone.utc).isoformat()))
            session.commit()

    def list_eval_results(self, run_id: str) -> list[dict[str, Any]]:
        with self.get_session() as session:
            rows = session.query(EvalResultDB).filter(EvalResultDB.run_id == run_id).all()
            return [
                {
                    "id": r.id,
                    "run_id": r.run_id,
                    "case_id": r.case_id,
                    "input_summary": r.input_summary,
                    "expected_output": r.expected_output,
                    "actual_output": r.actual_output,
                    "score": r.score,
                    "passed": r.passed,
                    "latency_ms": r.latency_ms,
                    "created_at": r.created_at,
                }
                for r in rows
            ]

    # Document operations (Sprint S4 M03)
    def create_document(
        self,
        owner_id: str,
        filename: str,
        size_bytes: int = 100,
        mime: str = "application/pdf",
        sha256: str | None = None,
        case_id: str | None = None,
        doc_type: str = "other",
        processing_status: str = "completed",
    ) -> dict[str, Any]:
        doc_id = f"doc-{uuid.uuid4().hex[:12]}"
        sha = sha256 or hashlib.sha256(f"{doc_id}-{filename}".encode()).hexdigest()
        doc_data = {
            "id": doc_id,
            "owner_id": owner_id,
            "filename": filename,
            "size_bytes": size_bytes,
            "mime": mime,
            "sha256": sha,
            "storage_key": f"docs/{owner_id}/{doc_id}.pdf",
            "case_id": case_id,
            "doc_type": doc_type,
            "processing_status": processing_status,
            "uploaded_at": datetime.now(timezone.utc).isoformat(),
        }
        self.save_document(doc_data)
        if case_id:
            self.attach_document_to_case(case_id, doc_id)
        res = self.get_document(doc_id)
        return res if res is not None else doc_data

    def save_document(self, doc_data: dict[str, Any]) -> str:
        with self.get_session() as session:
            doc_id = doc_data.get("id") or f"doc-{uuid.uuid4().hex[:12]}"
            record = session.query(DocumentDB).filter(DocumentDB.id == doc_id).first()
            if not record:
                record = DocumentDB(id=doc_id)
                session.add(record)
            record.owner_id = doc_data["owner_id"]
            record.case_id = doc_data.get("case_id")
            record.filename = doc_data["filename"]
            record.mime = doc_data.get("mime", "application/pdf")
            record.size_bytes = int(doc_data.get("size_bytes", 0))
            record.sha256 = doc_data["sha256"]
            record.storage_key = doc_data["storage_key"]
            record.doc_type = doc_data.get("doc_type", "other")
            record.language = doc_data.get("language", "bn")
            record.processing_status = doc_data.get("processing_status", "uploaded")
            record.intent = doc_data.get("intent", "understand")
            record.uploaded_at = str(doc_data.get("uploaded_at", datetime.now(timezone.utc).isoformat()))
            record.deleted_at = doc_data.get("deleted_at")
            record.retry_count = int(doc_data.get("retry_count", 0))
            record.error_message = doc_data.get("error_message")
            record.page_count = int(doc_data.get("page_count", 1))
            session.commit()
            return doc_id

    def get_document(self, doc_id: str) -> dict[str, Any] | None:
        with self.get_session() as session:
            r = session.query(DocumentDB).filter(DocumentDB.id == doc_id).first()
            if not r or r.deleted_at is not None:
                return None
            return {
                "id": r.id,
                "owner_id": r.owner_id,
                "case_id": r.case_id,
                "filename": r.filename,
                "mime": r.mime,
                "size_bytes": r.size_bytes,
                "sha256": r.sha256,
                "storage_key": r.storage_key,
                "doc_type": r.doc_type,
                "language": r.language,
                "processing_status": r.processing_status,
                "intent": r.intent,
                "uploaded_at": r.uploaded_at,
                "deleted_at": r.deleted_at,
                "retry_count": r.retry_count,
                "error_message": r.error_message,
                "page_count": r.page_count,
            }

    def find_document_by_hash(self, owner_id: str, sha256_hash: str) -> dict[str, Any] | None:
        with self.get_session() as session:
            r = session.query(DocumentDB).filter(
                DocumentDB.owner_id == owner_id,
                DocumentDB.sha256 == sha256_hash,
                DocumentDB.deleted_at.is_(None)
            ).first()
            if not r:
                return None
            return {
                "id": r.id,
                "owner_id": r.owner_id,
                "filename": r.filename,
                "sha256": r.sha256,
                "processing_status": r.processing_status,
                "intent": r.intent,
            }

    def list_documents(self, owner_id: str | None = None, include_deleted: bool = False) -> list[dict[str, Any]]:
        with self.get_session() as session:
            query = session.query(DocumentDB)
            if owner_id:
                query = query.filter(DocumentDB.owner_id == owner_id)
            if not include_deleted:
                query = query.filter(DocumentDB.deleted_at.is_(None))
            rows = query.order_by(DocumentDB.uploaded_at.desc()).all()
            return [
                {
                    "id": r.id,
                    "owner_id": r.owner_id,
                    "filename": r.filename,
                    "size_bytes": r.size_bytes,
                    "sha256": r.sha256,
                    "doc_type": r.doc_type,
                    "processing_status": r.processing_status,
                    "intent": r.intent,
                    "uploaded_at": r.uploaded_at,
                    "page_count": r.page_count,
                    "retry_count": r.retry_count,
                    "error_message": r.error_message,
                }
                for r in rows
            ]

    def update_document_status(self, doc_id: str, status: str, error_message: str | None = None, retry_count: int | None = None):
        with self.get_session() as session:
            record = session.query(DocumentDB).filter(DocumentDB.id == doc_id).first()
            if record:
                record.processing_status = status
                if error_message is not None:
                    record.error_message = error_message
                if retry_count is not None:
                    record.retry_count = retry_count
                session.commit()

    def set_document_intent(self, doc_id: str, intent: str):
        with self.get_session() as session:
            record = session.query(DocumentDB).filter(DocumentDB.id == doc_id).first()
            if record:
                record.intent = intent
                session.commit()

    def update_document_case(self, doc_id: str, case_id: str):
        with self.get_session() as session:
            record = session.query(DocumentDB).filter(DocumentDB.id == doc_id).first()
            if record:
                record.case_id = case_id
                session.commit()

    def delete_document(self, doc_id: str):
        with self.get_session() as session:
            record = session.query(DocumentDB).filter(DocumentDB.id == doc_id).first()
            if record:
                record.deleted_at = datetime.now(timezone.utc).isoformat()
                session.commit()

    def purge_document(self, doc_id: str):
        with self.get_session() as session:
            session.query(DocumentFieldDB).filter(DocumentFieldDB.document_id == doc_id).delete()
            session.query(DocumentPageDB).filter(DocumentPageDB.document_id == doc_id).delete()
            session.query(DocumentDB).filter(DocumentDB.id == doc_id).delete()
            session.commit()

    # Document Page Operations
    def save_document_page(self, page_data: dict[str, Any]) -> str:
        with self.get_session() as session:
            page_id = page_data.get("id") or f"page-{uuid.uuid4().hex[:12]}"
            record = session.query(DocumentPageDB).filter(DocumentPageDB.id == page_id).first()
            if not record:
                record = DocumentPageDB(id=page_id)
                session.add(record)
            record.document_id = page_data["document_id"]
            record.page_no = int(page_data["page_no"])
            record.image_key = page_data.get("image_key")
            record.ocr_text = page_data.get("ocr_text", "")
            record.ocr_confidence = float(page_data.get("ocr_confidence", 1.0))
            record.engine = page_data.get("engine", "FakeOcr")
            record.engine_version = page_data.get("engine_version", "1.0")
            session.commit()
            return page_id

    def list_document_pages(self, doc_id: str) -> list[dict[str, Any]]:
        with self.get_session() as session:
            rows = session.query(DocumentPageDB).filter(DocumentPageDB.document_id == doc_id).order_by(DocumentPageDB.page_no.asc()).all()
            return [
                {
                    "id": r.id,
                    "document_id": r.document_id,
                    "page_no": r.page_no,
                    "image_key": r.image_key,
                    "ocr_text": r.ocr_text,
                    "ocr_confidence": r.ocr_confidence,
                    "engine": r.engine,
                }
                for r in rows
            ]

    get_document_pages = list_document_pages

    # Document Field Operations
    def add_document_field(
        self,
        document_id: str,
        key: str,
        value: Any,
        confidence: float = 0.9,
        state: str = "extracted",
        page_no: int = 1,
    ) -> dict[str, Any]:
        fld_id = f"fld-{uuid.uuid4().hex[:12]}"
        field_data = {
            "id": fld_id,
            "document_id": document_id,
            "key": key,
            "value": value,
            "confidence": confidence,
            "state": state,
            "page_no": page_no,
        }
        self.save_document_field(field_data)
        res = self.get_document_field(fld_id)
        return res if res is not None else field_data

    def save_document_field(self, field_data: dict[str, Any]) -> str:
        with self.get_session() as session:
            fld_id = field_data.get("id") or f"fld-{uuid.uuid4().hex[:12]}"
            record = session.query(DocumentFieldDB).filter(DocumentFieldDB.id == fld_id).first()
            if not record:
                record = DocumentFieldDB(id=fld_id)
                session.add(record)
            record.document_id = field_data["document_id"]
            record.key = field_data["key"]
            record.value = field_data.get("value")
            record.confidence = float(field_data.get("confidence", 0.9))
            record.confidence_word = field_data.get("confidence_word", "clear")
            record.page_no = int(field_data.get("page_no", 1))
            if field_data.get("bbox") is None:
                record.bbox = None
            elif isinstance(field_data.get("bbox"), (list, dict)):
                record.bbox = json.dumps(field_data["bbox"])
            else:
                record.bbox = str(field_data.get("bbox", "[]"))
            record.crop_key = field_data.get("crop_key")
            record.state = field_data.get("state", "extracted")
            session.commit()
            return fld_id

    @staticmethod
    def _safe_load_bbox(val: str | None) -> list[Any] | dict[str, Any]:
        if not val or val in ("None", "null", "[]"):
            return []
        try:
            return json.loads(val)
        except Exception:
            return []

    def get_document_field(self, field_id: str) -> dict[str, Any] | None:
        with self.get_session() as session:
            r = session.query(DocumentFieldDB).filter(DocumentFieldDB.id == field_id).first()
            if not r:
                return None
            return {
                "id": r.id,
                "document_id": r.document_id,
                "key": r.key,
                "value": r.value,
                "confidence": r.confidence,
                "confidence_word": r.confidence_word,
                "page_no": r.page_no,
                "bbox": self._safe_load_bbox(r.bbox),
                "crop_key": r.crop_key,
                "state": r.state,
                "reviewed_by": r.reviewed_by,
                "reviewed_at": r.reviewed_at,
                "verified_by": r.verified_by,
                "verified_at": r.verified_at,
            }

    def update_document_field(self, field_id: str, new_value: str, user_id: str) -> dict[str, Any] | None:
        with self.get_session() as session:
            r = session.query(DocumentFieldDB).filter(DocumentFieldDB.id == field_id).first()
            if not r:
                return None
            r.value = new_value
            r.state = "reviewed"
            r.reviewed_by = user_id
            r.reviewed_at = datetime.now(timezone.utc).isoformat()
            session.commit()
            return self.get_document_field(field_id)

    def verify_document_field(self, field_id: str, user_id: str) -> dict[str, Any] | None:
        with self.get_session() as session:
            r = session.query(DocumentFieldDB).filter(DocumentFieldDB.id == field_id).first()
            if not r:
                return None
            r.state = "verified"
            r.verified_by = user_id
            r.verified_at = datetime.now(timezone.utc).isoformat()
            session.commit()
            return self.get_document_field(field_id)

    def list_document_fields(self, doc_id: str) -> list[dict[str, Any]]:
        with self.get_session() as session:
            rows = session.query(DocumentFieldDB).filter(DocumentFieldDB.document_id == doc_id).all()
            return [
                {
                    "id": r.id,
                    "document_id": r.document_id,
                    "key": r.key,
                    "value": r.value,
                    "confidence": r.confidence,
                    "confidence_word": r.confidence_word,
                    "page_no": r.page_no,
                    "bbox": self._safe_load_bbox(r.bbox),
                    "crop_key": r.crop_key,
                    "state": r.state,
                    "reviewed_by": r.reviewed_by,
                    "reviewed_at": r.reviewed_at,
                    "verified_by": r.verified_by,
                    "verified_at": r.verified_at,
                }
                for r in rows
            ]

    # Resumable upload operations
    def save_resumable_upload(self, upload_data: dict[str, Any]):
        with self.get_session() as session:
            r = session.query(DocumentUploadResumableDB).filter(DocumentUploadResumableDB.upload_id == upload_data["upload_id"]).first()
            if not r:
                r = DocumentUploadResumableDB(upload_id=upload_data["upload_id"])
                session.add(r)
            r.owner_id = upload_data["owner_id"]
            r.filename = upload_data["filename"]
            r.total_size = int(upload_data["total_size"])
            r.total_chunks = int(upload_data["total_chunks"])
            r.uploaded_chunks_json = json.dumps(upload_data.get("uploaded_chunks", []))
            r.sha256_hash = upload_data.get("sha256_hash", "")
            r.temp_file_path = upload_data["temp_file_path"]
            r.created_at = str(upload_data.get("created_at", datetime.now(timezone.utc).isoformat()))
            r.expires_at = str(upload_data.get("expires_at", ""))
            session.commit()

    def get_resumable_upload(self, upload_id: str) -> dict[str, Any] | None:
        with self.get_session() as session:
            r = session.query(DocumentUploadResumableDB).filter(DocumentUploadResumableDB.upload_id == upload_id).first()
            if not r:
                return None
            return {
                "upload_id": r.upload_id,
                "owner_id": r.owner_id,
                "filename": r.filename,
                "total_size": r.total_size,
                "total_chunks": r.total_chunks,
                "uploaded_chunks": json.loads(r.uploaded_chunks_json) if r.uploaded_chunks_json else [],
                "sha256_hash": r.sha256_hash,
                "temp_file_path": r.temp_file_path,
                "created_at": r.created_at,
                "expires_at": r.expires_at,
            }

    def update_resumable_chunks(self, upload_id: str, chunk_index: int):
        with self.get_session() as session:
            r = session.query(DocumentUploadResumableDB).filter(DocumentUploadResumableDB.upload_id == upload_id).first()
            if r:
                chunks = json.loads(r.uploaded_chunks_json) if r.uploaded_chunks_json else []
                if chunk_index not in chunks:
                    chunks.append(chunk_index)
                r.uploaded_chunks_json = json.dumps(sorted(chunks))
                session.commit()

    def delete_resumable_upload(self, upload_id: str):
        with self.get_session() as session:
            session.query(DocumentUploadResumableDB).filter(DocumentUploadResumableDB.upload_id == upload_id).delete()
            session.commit()

    # ---------------------------------------------------------------------------
    # Sprint S5: Cases, Tasks, Deadlines, Reminders & Notice Analyses
    # ---------------------------------------------------------------------------

    def create_case(
        self,
        owner_id: str,
        title: str,
        case_type: str = "general",
        description: str | None = None,
        objective: str | None = None,
        urgency: str = "normal",
        status: str = "new",
        legacy_matter_id: str | None = None,
        metadata_json: str | None = None,
        triage_urgency: str | None = None,
        is_urgent_triage: bool = False,
    ) -> dict[str, Any]:
        with self.get_session() as session:
            case_id = str(uuid.uuid4())
            now_iso = datetime.now(timezone.utc).isoformat()
            case = CaseDB(
                id=case_id,
                owner_id=owner_id,
                title=title,
                case_type=case_type,
                description=description,
                objective=objective,
                urgency=urgency,
                status=status,
                legacy_matter_id=legacy_matter_id,
                metadata_json=metadata_json,
                triage_urgency=triage_urgency,
                is_urgent_triage=is_urgent_triage,
                created_at=now_iso,
                updated_at=now_iso,
            )
            session.add(case)
            session.commit()
            return {
                "id": case.id,
                "owner_id": case.owner_id,
                "title": case.title,
                "case_type": case.case_type,
                "description": case.description,
                "objective": case.objective,
                "urgency": case.urgency,
                "status": case.status,
                "legacy_matter_id": case.legacy_matter_id,
                "metadata_json": case.metadata_json,
                "triage_urgency": case.triage_urgency,
                "is_urgent_triage": case.is_urgent_triage,
                "created_at": case.created_at,
                "updated_at": case.updated_at,
            }

    def get_case(self, case_id: str) -> dict[str, Any] | None:
        with self.get_session() as session:
            case = session.query(CaseDB).filter(CaseDB.id == case_id).first()
            if not case:
                return None
            return {
                "id": case.id,
                "owner_id": case.owner_id,
                "title": case.title,
                "case_type": case.case_type,
                "description": case.description,
                "objective": case.objective,
                "urgency": case.urgency,
                "status": case.status,
                "next_action_id": case.next_action_id,
                "legacy_matter_id": case.legacy_matter_id,
                "metadata_json": case.metadata_json,
                "triage_urgency": case.triage_urgency,
                "is_urgent_triage": case.is_urgent_triage,
                "closed_at": case.closed_at,
                "created_at": case.created_at,
                "updated_at": case.updated_at,
                "deleted_at": case.deleted_at,
            }

    def list_cases(self, owner_id: str | None = None) -> list[dict[str, Any]]:
        with self.get_session() as session:
            q = session.query(CaseDB).filter(CaseDB.deleted_at.is_(None))
            if owner_id:
                q = q.filter(CaseDB.owner_id == owner_id)
            rows = q.order_by(CaseDB.created_at.desc()).all()
            return [
                {
                    "id": c.id,
                    "owner_id": c.owner_id,
                    "title": c.title,
                    "case_type": c.case_type,
                    "urgency": c.urgency,
                    "status": c.status,
                    "legacy_matter_id": c.legacy_matter_id,
                    "metadata_json": c.metadata_json,
                    "triage_urgency": c.triage_urgency,
                    "is_urgent_triage": c.is_urgent_triage,
                    "created_at": c.created_at,
                    "updated_at": c.updated_at,
                }
                for c in rows
            ]

    def create_task(
        self,
        case_id: str,
        title: str,
        description: str | None = None,
        owner_id: str = "system",
        document_id: str | None = None,
        due_at: str | None = None,
        priority: str = "normal",
        status: str = "not_started",
        origin: str = "user",
    ) -> dict[str, Any]:
        with self.get_session() as session:
            task_id = str(uuid.uuid4())
            now_iso = datetime.now(timezone.utc).isoformat()
            task = TaskDB(
                id=task_id,
                case_id=case_id,
                title=title,
                description=description,
                owner_id=owner_id,
                due_at=due_at,
                priority=priority,
                status=status,
                origin=origin,
                related_document_id=document_id,
                document_id=document_id,
                created_at=now_iso,
            )
            session.add(task)
            session.commit()
            return {
                "id": task.id,
                "case_id": task.case_id,
                "title": task.title,
                "description": task.description,
                "owner_id": task.owner_id,
                "due_at": task.due_at,
                "priority": task.priority,
                "status": task.status,
                "origin": task.origin,
                "document_id": task.document_id,
                "created_at": task.created_at,
            }

    def get_task(self, task_id: str) -> dict[str, Any] | None:
        with self.get_session() as session:
            t = session.query(TaskDB).filter(TaskDB.id == task_id).first()
            if not t:
                return None
            return {
                "id": t.id,
                "case_id": t.case_id,
                "title": t.title,
                "description": t.description,
                "owner_id": t.owner_id,
                "due_at": t.due_at,
                "priority": t.priority,
                "status": t.status,
                "origin": t.origin,
                "document_id": t.document_id,
                "created_at": t.created_at,
            }

    def list_tasks(self, case_id: str | None = None, document_id: str | None = None) -> list[dict[str, Any]]:
        with self.get_session() as session:
            q = session.query(TaskDB)
            if case_id:
                q = q.filter(TaskDB.case_id == case_id)
            if document_id:
                q = q.filter((TaskDB.document_id == document_id) | (TaskDB.related_document_id == document_id))
            return [
                {
                    "id": t.id,
                    "case_id": t.case_id,
                    "title": t.title,
                    "description": t.description,
                    "owner_id": t.owner_id,
                    "due_at": t.due_at,
                    "priority": t.priority,
                    "status": t.status,
                    "origin": t.origin,
                    "document_id": t.document_id,
                    "created_at": t.created_at,
                }
                for t in q.all()
            ]

    def update_task_status(self, task_id: str, status: str) -> dict[str, Any] | None:
        with self.get_session() as session:
            t = session.query(TaskDB).filter(TaskDB.id == task_id).first()
            if not t:
                return None
            t.status = status
            session.commit()
            return {
                "id": t.id,
                "case_id": t.case_id,
                "title": t.title,
                "status": t.status,
            }

    def create_deadline(
        self,
        case_id: str,
        title: str,
        due_date: str,
        user_id: str | None = None,
        document_id: str | None = None,
        rule_key: str | None = None,
        rule_version: str | None = None,
        calc_steps: list[Any] | None = None,
        assumptions: list[Any] | None = None,
        calculation_basis: str | None = None,
        is_user_set: bool = False,
        confirmed_by_user: bool = False,
    ) -> dict[str, Any]:
        with self.get_session() as session:
            dl_id = str(uuid.uuid4())
            now_iso = datetime.now(timezone.utc).isoformat()
            dl = DeadlineDB(
                id=dl_id,
                case_id=case_id,
                title=title,
                due_date=due_date,
                user_id=user_id,
                document_id=document_id,
                rule_key=rule_key,
                rule_version=rule_version,
                calc_steps=json.dumps(calc_steps, ensure_ascii=False) if calc_steps is not None else None,
                assumptions=json.dumps(assumptions, ensure_ascii=False) if assumptions is not None else None,
                calculation_basis=calculation_basis,
                is_user_set=is_user_set,
                confirmed_by_user=confirmed_by_user,
                confirmed_at=now_iso if confirmed_by_user else None,
                status="upcoming",
                created_at=now_iso,
            )
            session.add(dl)
            session.commit()

            res = {
                "id": dl.id,
                "case_id": dl.case_id,
                "title": dl.title,
                "due_date": dl.due_date,
                "user_id": dl.user_id,
                "document_id": dl.document_id,
                "rule_key": dl.rule_key,
                "rule_version": dl.rule_version,
                "calc_steps": calc_steps or [],
                "assumptions": assumptions or [],
                "calculation_basis": dl.calculation_basis,
                "is_user_set": dl.is_user_set,
                "confirmed_by_user": dl.confirmed_by_user,
                "confirmed_at": dl.confirmed_at,
                "status": dl.status,
                "created_at": dl.created_at,
            }

            if confirmed_by_user and user_id:
                # AC-M07-1: Automatically create reminder schedule on confirmation
                self._create_default_reminders_for_deadline(session, str(dl.id), str(user_id), due_date)

            return res

    def _create_default_reminders_for_deadline(self, session, deadline_id: str, user_id: str, due_date_str: str):
        from datetime import datetime, timedelta, timezone
        dhaka_tz = timezone(timedelta(hours=6))
        try:
            due_dt = datetime.strptime(due_date_str[:10], "%Y-%m-%d").date()
        except Exception:
            return

        current_time = self.get_current_time().astimezone(dhaka_tz)
        now_iso = current_time.isoformat()

        # Default offsets per SRS M07: T-7, T-3, T-1, morning of (offset 0 at 08:00 Asia/Dhaka)
        offsets = [-7, -3, -1, 0]
        for offset in offsets:
            sched_date = due_dt + timedelta(days=offset)
            sched_dt = datetime(sched_date.year, sched_date.month, sched_date.day, 8, 0, 0, tzinfo=dhaka_tz)

            # Rule 6: Never create a reminder whose time is already in the past
            if sched_dt <= current_time:
                continue

            r_id = str(uuid.uuid4())
            rem = ReminderScheduleDB(
                id=r_id,
                deadline_id=deadline_id,
                user_id=user_id,
                offset_days=offset,
                scheduled_at=sched_dt.isoformat(),
                channel="in_app",
                status="pending",
                created_at=now_iso,
            )
            session.add(rem)
        session.commit()

    def get_deadline(self, deadline_id: str) -> dict[str, Any] | None:
        with self.get_session() as session:
            dl = session.query(DeadlineDB).filter(DeadlineDB.id == deadline_id).first()
            if not dl:
                return None
            return {
                "id": dl.id,
                "case_id": dl.case_id,
                "title": dl.title,
                "due_date": dl.due_date,
                "user_id": dl.user_id,
                "document_id": dl.document_id,
                "rule_key": dl.rule_key,
                "rule_version": dl.rule_version,
                "calc_steps": json.loads(dl.calc_steps) if dl.calc_steps else [],
                "assumptions": json.loads(dl.assumptions) if dl.assumptions else [],
                "calculation_basis": dl.calculation_basis,
                "is_user_set": dl.is_user_set,
                "confirmed_by_user": dl.confirmed_by_user,
                "confirmed_at": dl.confirmed_at,
                "status": dl.status,
                "created_at": dl.created_at,
            }

    def list_deadlines(self, case_id: str | None = None, document_id: str | None = None) -> list[dict[str, Any]]:
        with self.get_session() as session:
            q = session.query(DeadlineDB)
            if case_id:
                q = q.filter(DeadlineDB.case_id == case_id)
            if document_id:
                q = q.filter(DeadlineDB.document_id == document_id)
            return [
                {
                    "id": dl.id,
                    "case_id": dl.case_id,
                    "title": dl.title,
                    "due_date": dl.due_date,
                    "user_id": dl.user_id,
                    "document_id": dl.document_id,
                    "rule_key": dl.rule_key,
                    "rule_version": dl.rule_version,
                    "calc_steps": json.loads(dl.calc_steps) if dl.calc_steps else [],
                    "assumptions": json.loads(dl.assumptions) if dl.assumptions else [],
                    "calculation_basis": dl.calculation_basis,
                    "is_user_set": dl.is_user_set,
                    "confirmed_by_user": dl.confirmed_by_user,
                    "confirmed_at": dl.confirmed_at,
                    "status": dl.status,
                    "created_at": dl.created_at,
                }
                for dl in q.all()
            ]

    def confirm_deadline(self, deadline_id: str, user_id: str | None = None) -> dict[str, Any] | None:
        """
        Confirms a deadline (AC-M04-2, AC-M07-1):
        1. Updates confirmed_by_user = True, confirmed_at = now_iso, status = 'upcoming'.
        2. Automatically generates default reminder schedules (T-7, T-3, T-1, 0).
        """
        with self.get_session() as session:
            dl = session.query(DeadlineDB).filter(DeadlineDB.id == deadline_id).first()
            if not dl:
                return None
            dl.confirmed_by_user = True
            now_iso = datetime.now(timezone.utc).isoformat()
            dl.confirmed_at = now_iso
            dl.status = "upcoming"
            if user_id:
                dl.user_id = user_id
            session.commit()

            # Schedule reminders
            eff_user = dl.user_id or user_id or "system"
            self._create_default_reminders_for_deadline(session, dl.id, eff_user, dl.due_date)

            return {
                "id": dl.id,
                "confirmed_by_user": dl.confirmed_by_user,
                "confirmed_at": dl.confirmed_at,
                "status": dl.status,
                "due_date": dl.due_date,
            }

    def dismiss_or_meet_deadline(self, deadline_id: str, status: str = "completed") -> dict[str, Any] | None:
        """
        Dismisses or meets a deadline (AC-M07-1):
        1. Sets deadline status to completed or dismissed.
        2. Automatically cancels all pending reminder schedules.
        """
        with self.get_session() as session:
            dl = session.query(DeadlineDB).filter(DeadlineDB.id == deadline_id).first()
            if not dl:
                return None
            dl.status = status
            # Cancel pending reminders
            session.query(ReminderScheduleDB).filter(
                ReminderScheduleDB.deadline_id == deadline_id,
                ReminderScheduleDB.status == "pending",
            ).update({"status": "cancelled"})
            session.query(NotificationDB).filter(
                NotificationDB.deadline_id == deadline_id,
                NotificationDB.status == "pending",
            ).update({"status": "cancelled"})
            session.commit()
            return {
                "id": dl.id,
                "status": dl.status,
                "reminders_cancelled": True,
            }

    def get_reminders_for_deadline(self, deadline_id: str) -> list[dict[str, Any]]:
        with self.get_session() as session:
            rows = session.query(ReminderScheduleDB).filter(ReminderScheduleDB.deadline_id == deadline_id).all()
            return [
                {
                    "id": r.id,
                    "deadline_id": r.deadline_id,
                    "user_id": r.user_id,
                    "offset_days": r.offset_days,
                    "scheduled_at": r.scheduled_at,
                    "channel": r.channel,
                    "status": r.status,
                    "created_at": r.created_at,
                }
                for r in rows
            ]

    def cancel_reminders_for_deadline(self, deadline_id: str) -> int:
        with self.get_session() as session:
            cnt = session.query(ReminderScheduleDB).filter(
                ReminderScheduleDB.deadline_id == deadline_id,
                ReminderScheduleDB.status == "pending",
            ).update({"status": "cancelled"})
            session.commit()
            return cnt

    def save_notice_analysis(
        self,
        document_id: str,
        user_id: str,
        analysis: dict[str, Any],
        certainty: str,
        as_of_date: str,
    ) -> dict[str, Any]:
        with self.get_session() as session:
            now_iso = datetime.now(timezone.utc).isoformat()
            rec = session.query(NoticeAnalysisDB).filter(NoticeAnalysisDB.document_id == document_id).first()
            if not rec:
                rec = NoticeAnalysisDB(
                    id=str(uuid.uuid4()),
                    document_id=document_id,
                    user_id=user_id,
                    analysis_json=json.dumps(analysis, ensure_ascii=False),
                    certainty=certainty,
                    as_of_date=as_of_date,
                    created_at=now_iso,
                    updated_at=now_iso,
                )
                session.add(rec)
            else:
                rec.analysis_json = json.dumps(analysis, ensure_ascii=False)
                rec.certainty = certainty
                rec.as_of_date = as_of_date
                rec.updated_at = now_iso
            session.commit()
            return {
                "id": rec.id,
                "document_id": rec.document_id,
                "certainty": rec.certainty,
                "as_of_date": rec.as_of_date,
            }

    def get_notice_analysis(self, document_id: str) -> dict[str, Any] | None:
        with self.get_session() as session:
            rec = session.query(NoticeAnalysisDB).filter(NoticeAnalysisDB.document_id == document_id).first()
            if not rec:
                return None
            return {
                "id": rec.id,
                "document_id": rec.document_id,
                "user_id": rec.user_id,
                "analysis": json.loads(rec.analysis_json) if rec.analysis_json else {},
                "simpler": json.loads(rec.simpler_json) if rec.simpler_json else None,
                "certainty": rec.certainty,
                "as_of_date": rec.as_of_date,
                "created_at": rec.created_at,
                "updated_at": rec.updated_at,
            }

    def update_notice_simpler(self, document_id: str, simpler: dict[str, Any]) -> dict[str, Any] | None:
        with self.get_session() as session:
            rec = session.query(NoticeAnalysisDB).filter(NoticeAnalysisDB.document_id == document_id).first()
            if not rec:
                return None
            now_iso = datetime.now(timezone.utc).isoformat()
            rec.simpler_json = json.dumps(simpler, ensure_ascii=False)
            rec.updated_at = now_iso
            session.commit()
            return {
                "id": rec.id,
                "document_id": rec.document_id,
                "simpler": simpler,
            }

    # ---------------------------------------------------------------------------
    # Sprint S6: Case Details (Parties, Events, Facts, Notes, Docs) & Notifications
    # ---------------------------------------------------------------------------

    def update_case(self, case_id: str, **kwargs) -> dict[str, Any] | None:
        with self.get_session() as session:
            case = session.query(CaseDB).filter(CaseDB.id == case_id).first()
            if not case:
                return None
            for k, v in kwargs.items():
                if hasattr(case, k):
                    setattr(case, k, v)
            case.updated_at = datetime.now(timezone.utc).isoformat()
            session.commit()
            return self.get_case(case_id)

    def delete_case(self, case_id: str, document_action: str = "keep") -> bool:
        """
        Deletes a case with document handling:
        - "keep": unlinks documents from case, preserving document records and storage files.
        - "unlink": removes associations, sets document.case_id to None.
        - "delete": removes associated document records and unlinks.
        """
        with self.get_session() as session:
            case = session.query(CaseDB).filter(CaseDB.id == case_id).first()
            if not case:
                return False

            now_iso = datetime.now(timezone.utc).isoformat()
            case.deleted_at = now_iso
            case.status = "archived"

            # Handle associated documents
            if document_action == "delete":
                doc_links = session.query(CaseDocumentDB).filter(CaseDocumentDB.case_id == case_id).all()
                for dl in doc_links:
                    d = session.query(DocumentDB).filter(DocumentDB.id == dl.document_id).first()
                    if d:
                        d.deleted_at = now_iso
                session.query(DocumentDB).filter(DocumentDB.case_id == case_id).update({"deleted_at": now_iso})
            elif document_action in ("unlink", "keep"):
                session.query(DocumentDB).filter(DocumentDB.case_id == case_id).update({"case_id": None})
                session.query(CaseDocumentDB).filter(CaseDocumentDB.case_id == case_id).delete()

            # Clean tasks and deadlines
            session.query(TaskDB).filter(TaskDB.case_id == case_id).delete()
            session.query(DeadlineDB).filter(DeadlineDB.case_id == case_id).delete()

            session.commit()
            return True

    # Parties
    def add_case_party(self, case_id: str, name: str, role: str, contact_info: str | None = None) -> dict[str, Any]:
        with self.get_session() as session:
            party_id = str(uuid.uuid4())
            party = CasePartyDB(id=party_id, case_id=case_id, name=name, role=role, contact_info=contact_info)
            session.add(party)
            session.commit()
            return {"id": party.id, "case_id": party.case_id, "name": party.name, "role": party.role, "contact_info": party.contact_info}

    def list_case_parties(self, case_id: str) -> list[dict[str, Any]]:
        with self.get_session() as session:
            rows = session.query(CasePartyDB).filter(CasePartyDB.case_id == case_id).all()
            return [{"id": r.id, "case_id": r.case_id, "name": r.name, "role": r.role, "contact_info": r.contact_info} for r in rows]

    def delete_case_party(self, party_id: str) -> bool:
        with self.get_session() as session:
            cnt = session.query(CasePartyDB).filter(CasePartyDB.id == party_id).delete()
            session.commit()
            return cnt > 0

    # Events
    def add_case_event(
        self,
        case_id: str,
        title: str,
        event_date: str,
        date_precision: str = "day",
        description: str | None = None,
        event_type: str = "other",
    ) -> dict[str, Any]:
        with self.get_session() as session:
            evt_id = str(uuid.uuid4())
            now_iso = datetime.now(timezone.utc).isoformat()
            evt = CaseEventDB(
                id=evt_id,
                case_id=case_id,
                title=title,
                event_date=event_date,
                date_precision=date_precision,
                description=description,
                event_type=event_type,
                created_at=now_iso,
            )
            session.add(evt)
            session.commit()
            return {
                "id": evt.id,
                "case_id": evt.case_id,
                "title": evt.title,
                "event_date": evt.event_date,
                "date_precision": evt.date_precision,
                "description": evt.description,
                "event_type": evt.event_type,
                "created_at": evt.created_at,
            }

    def list_case_events(self, case_id: str) -> list[dict[str, Any]]:
        with self.get_session() as session:
            rows = session.query(CaseEventDB).filter(CaseEventDB.case_id == case_id).order_by(CaseEventDB.event_date.asc()).all()
            return [
                {
                    "id": r.id,
                    "case_id": r.case_id,
                    "title": r.title,
                    "event_date": r.event_date,
                    "date_precision": r.date_precision,
                    "description": r.description,
                    "event_type": r.event_type,
                    "created_at": r.created_at,
                }
                for r in rows
            ]

    # Facts
    def add_case_fact(
        self,
        case_id: str,
        fact_text: str,
        source_doc_id: str | None = None,
        status: str = "active",
        is_proposed: bool = False,
    ) -> dict[str, Any]:
        with self.get_session() as session:
            fact_id = str(uuid.uuid4())
            now_iso = datetime.now(timezone.utc).isoformat()
            fact = CaseFactDB(
                id=fact_id,
                case_id=case_id,
                text=fact_text,
                fact_text=fact_text,
                source_ref=source_doc_id,
                source_doc_id=source_doc_id,
                state=status,
                status=status,
                is_proposed=is_proposed,
                created_at=now_iso,
            )
            session.add(fact)
            session.commit()
            return {
                "id": fact.id,
                "case_id": fact.case_id,
                "fact_text": fact.fact_text,
                "source_doc_id": fact.source_doc_id,
                "status": fact.status,
                "is_proposed": fact.is_proposed,
                "created_at": fact.created_at,
            }

    def list_case_facts(self, case_id: str, include_proposed: bool = True) -> list[dict[str, Any]]:
        with self.get_session() as session:
            q = session.query(CaseFactDB).filter(CaseFactDB.case_id == case_id)
            if not include_proposed:
                q = q.filter(CaseFactDB.is_proposed == False)  # noqa: E712
            rows = q.order_by(CaseFactDB.created_at.asc()).all()
            return [
                {
                    "id": r.id,
                    "case_id": r.case_id,
                    "fact_text": r.fact_text,
                    "source_doc_id": r.source_doc_id,
                    "status": r.status,
                    "is_proposed": r.is_proposed,
                    "created_at": r.created_at,
                }
                for r in rows
            ]

    def accept_case_fact(self, fact_id: str) -> dict[str, Any] | None:
        with self.get_session() as session:
            fact = session.query(CaseFactDB).filter(CaseFactDB.id == fact_id).first()
            if not fact:
                return None
            fact.is_proposed = False
            fact.status = "accepted"
            session.commit()
            return {
                "id": fact.id,
                "case_id": fact.case_id,
                "fact_text": fact.fact_text,
                "status": fact.status,
                "is_proposed": fact.is_proposed,
            }

    def dismiss_case_fact(self, fact_id: str) -> dict[str, Any] | None:
        with self.get_session() as session:
            fact = session.query(CaseFactDB).filter(CaseFactDB.id == fact_id).first()
            if not fact:
                return None
            fact.status = "rejected"
            session.commit()
            return {
                "id": fact.id,
                "case_id": fact.case_id,
                "status": fact.status,
            }

    # Notes
    def add_case_note(
        self,
        case_id: str,
        user_id: str,
        note_text: str,
        is_private: bool = True,
        include_in_analysis: bool = False,
        include_in_brief: bool = False,
    ) -> dict[str, Any]:
        with self.get_session() as session:
            note_id = str(uuid.uuid4())
            now_iso = datetime.now(timezone.utc).isoformat()
            note = CaseNoteDB(
                id=note_id,
                case_id=case_id,
                user_id=user_id,
                note_text=note_text,
                is_private=is_private,
                include_in_analysis=include_in_analysis,
                include_in_brief=include_in_brief,
                created_at=now_iso,
                updated_at=now_iso,
            )
            session.add(note)
            session.commit()
            return {
                "id": note.id,
                "case_id": note.case_id,
                "user_id": note.user_id,
                "note_text": note.note_text,
                "is_private": note.is_private,
                "include_in_analysis": note.include_in_analysis,
                "include_in_brief": note.include_in_brief,
                "created_at": note.created_at,
                "updated_at": note.updated_at,
            }

    def list_case_notes(self, case_id: str, user_id: str | None = None) -> list[dict[str, Any]]:
        with self.get_session() as session:
            q = session.query(CaseNoteDB).filter(CaseNoteDB.case_id == case_id)
            if user_id:
                q = q.filter((CaseNoteDB.user_id == user_id) | (CaseNoteDB.is_private == False))  # noqa: E712
            rows = q.order_by(CaseNoteDB.created_at.desc()).all()
            return [
                {
                    "id": r.id,
                    "case_id": r.case_id,
                    "user_id": r.user_id,
                    "note_text": r.note_text,
                    "is_private": r.is_private,
                    "include_in_analysis": r.include_in_analysis,
                    "include_in_brief": bool(r.include_in_brief),
                    "created_at": r.created_at,
                    "updated_at": r.updated_at,
                }
                for r in rows
            ]

    def get_notes_for_brief(self, case_id: str) -> list[dict[str, Any]]:
        with self.get_session() as session:
            rows = (
                session.query(CaseNoteDB)
                .filter(CaseNoteDB.case_id == case_id, CaseNoteDB.include_in_brief == True)  # noqa: E712
                .order_by(CaseNoteDB.created_at.asc())
                .all()
            )
            return [
                {
                    "id": r.id,
                    "case_id": r.case_id,
                    "user_id": r.user_id,
                    "note_text": r.note_text,
                    "is_private": r.is_private,
                    "include_in_analysis": r.include_in_analysis,
                    "include_in_brief": True,
                    "created_at": r.created_at,
                    "updated_at": r.updated_at,
                }
                for r in rows
            ]

    def delete_case_note(self, note_id: str) -> bool:
        with self.get_session() as session:
            cnt = session.query(CaseNoteDB).filter(CaseNoteDB.id == note_id).delete()
            session.commit()
            return cnt > 0

    # Documents link
    def attach_document_to_case(self, case_id: str, document_id: str) -> dict[str, Any]:
        with self.get_session() as session:
            now_iso = datetime.now(timezone.utc).isoformat()
            link = session.query(CaseDocumentDB).filter(
                CaseDocumentDB.case_id == case_id,
                CaseDocumentDB.document_id == document_id,
            ).first()
            if not link:
                link = CaseDocumentDB(case_id=case_id, document_id=document_id, attached_at=now_iso)
                session.add(link)
            doc = session.query(DocumentDB).filter(DocumentDB.id == document_id).first()
            if doc:
                doc.case_id = case_id
            session.commit()
            return {"case_id": case_id, "document_id": document_id, "attached_at": now_iso}

    def list_case_documents(self, case_id: str) -> list[dict[str, Any]]:
        with self.get_session() as session:
            links = session.query(CaseDocumentDB).filter(CaseDocumentDB.case_id == case_id).all()
            doc_ids = [lnk.document_id for lnk in links]
            direct_docs = session.query(DocumentDB).filter(DocumentDB.case_id == case_id).all()
            all_doc_ids = list(set(doc_ids + [d.id for d in direct_docs]))

            if not all_doc_ids:
                return []
            docs = session.query(DocumentDB).filter(DocumentDB.id.in_(all_doc_ids), DocumentDB.deleted_at.is_(None)).all()
            return [
                {
                    "id": d.id,
                    "filename": d.filename,
                    "mime": d.mime,
                    "size_bytes": d.size_bytes,
                    "doc_type": d.doc_type,
                    "processing_status": d.processing_status,
                    "uploaded_at": d.uploaded_at,
                }
                for d in docs
            ]

    def detach_document_from_case(self, case_id: str, document_id: str) -> bool:
        with self.get_session() as session:
            session.query(CaseDocumentDB).filter(
                CaseDocumentDB.case_id == case_id,
                CaseDocumentDB.document_id == document_id,
            ).delete()
            doc = session.query(DocumentDB).filter(DocumentDB.id == document_id).first()
            if doc and doc.case_id == case_id:
                doc.case_id = None
            session.commit()
            return True

    # Notifications
    def create_notification(
        self,
        user_id: str,
        title: str,
        message: str,
        channel: str = "in_app",
        category: str = "deadline_reminder",
        deadline_id: str | None = None,
        case_id: str | None = None,
        scheduled_at: str | None = None,
        status: str = "pending",
    ) -> dict[str, Any]:
        with self.get_session() as session:
            nid = str(uuid.uuid4())
            now_iso = self.get_current_time().isoformat()
            sched = scheduled_at or now_iso
            notif = NotificationDB(
                id=nid,
                user_id=user_id,
                title=title,
                message=message,
                channel=channel,
                category=category,
                deadline_id=deadline_id,
                case_id=case_id,
                scheduled_at=sched,
                status=status,
                retry_count=0,
                created_at=now_iso,
                is_read=False,
                read_at=None,
                kind="system",
                title_key=title[:64] if title else "",
                body_key=message[:64] if message else "",
            )
            session.add(notif)
            session.commit()
            return {
                "id": notif.id,
                "user_id": notif.user_id,
                "title": notif.title,
                "message": notif.message,
                "channel": notif.channel,
                "category": notif.category,
                "deadline_id": notif.deadline_id,
                "case_id": notif.case_id,
                "scheduled_at": notif.scheduled_at,
                "status": notif.status,
                "retry_count": notif.retry_count,
                "is_read": bool(notif.is_read),
                "read_at": notif.read_at,
                "created_at": notif.created_at,
            }

    def get_notification(self, notification_id: str) -> dict[str, Any] | None:
        with self.get_session() as session:
            r = session.query(NotificationDB).filter(NotificationDB.id == notification_id).first()
            if not r:
                return None
            return {
                "id": r.id,
                "user_id": r.user_id,
                "title": r.title,
                "message": r.message,
                "channel": r.channel,
                "category": r.category,
                "deadline_id": r.deadline_id,
                "case_id": r.case_id,
                "scheduled_at": r.scheduled_at,
                "sent_at": r.sent_at,
                "status": r.status,
                "retry_count": r.retry_count,
                "error_message": r.error_message,
                "is_read": bool(r.is_read),
                "read_at": r.read_at,
                "created_at": r.created_at,
            }

    def list_notifications(self, user_id: str, status: str | None = None) -> list[dict[str, Any]]:
        with self.get_session() as session:
            q = session.query(NotificationDB).filter(NotificationDB.user_id == user_id)
            if status:
                q = q.filter(NotificationDB.status == status)
            rows = q.order_by(NotificationDB.created_at.desc()).all()
            return [
                {
                    "id": r.id,
                    "user_id": r.user_id,
                    "title": r.title,
                    "message": r.message,
                    "channel": r.channel,
                    "category": r.category,
                    "deadline_id": r.deadline_id,
                    "case_id": r.case_id,
                    "scheduled_at": r.scheduled_at,
                    "sent_at": r.sent_at,
                    "status": r.status,
                    "retry_count": r.retry_count,
                    "error_message": r.error_message,
                    "is_read": bool(r.is_read),
                    "read_at": r.read_at,
                    "created_at": r.created_at,
                }
                for r in rows
            ]

    def mark_notification_read(self, notification_id: str) -> dict[str, Any] | None:
        with self.get_session() as session:
            notif = session.query(NotificationDB).filter(NotificationDB.id == notification_id).first()
            if not notif:
                return None
            now_iso = self.get_current_time().isoformat()
            notif.is_read = True
            notif.read_at = now_iso
            session.commit()
            return {
                "id": notif.id,
                "is_read": notif.is_read,
                "read_at": notif.read_at,
            }

    def update_notification(self, notification_id: str, **kwargs) -> dict[str, Any] | None:
        with self.get_session() as session:
            notif = session.query(NotificationDB).filter(NotificationDB.id == notification_id).first()
            if not notif:
                return None
            for k, v in kwargs.items():
                if hasattr(notif, k):
                    setattr(notif, k, v)
            session.commit()
            return {
                "id": notif.id,
                "status": notif.status,
                "retry_count": notif.retry_count,
                "sent_at": notif.sent_at,
                "error_message": notif.error_message,
            }

    def get_notification_preferences(self, user_id: str) -> dict[str, Any]:
        with self.get_session() as session:
            prefs = session.query(NotificationPreferenceDB).filter(NotificationPreferenceDB.user_id == user_id).first()
            if not prefs:
                return {
                    "user_id": user_id,
                    "enable_in_app": True,
                    "enable_sms": False,
                    "quiet_hours_enabled": True,
                    "quiet_hours_start": "22:00",
                    "quiet_hours_end": "07:00",
                    "language": "bn",
                }
            return {
                "user_id": prefs.user_id,
                "enable_in_app": prefs.enable_in_app,
                "enable_sms": prefs.enable_sms,
                "quiet_hours_enabled": prefs.quiet_hours_enabled,
                "quiet_hours_start": prefs.quiet_hours_start,
                "quiet_hours_end": prefs.quiet_hours_end,
                "language": prefs.language,
            }

    def save_notification_preferences(self, user_id: str, prefs: dict[str, Any]) -> dict[str, Any]:
        with self.get_session() as session:
            rec = session.query(NotificationPreferenceDB).filter(NotificationPreferenceDB.user_id == user_id).first()
            now_iso = datetime.now(timezone.utc).isoformat()
            if not rec:
                rec = NotificationPreferenceDB(
                    user_id=user_id,
                    enable_in_app=prefs.get("enable_in_app", True),
                    enable_sms=prefs.get("enable_sms", False),
                    quiet_hours_enabled=prefs.get("quiet_hours_enabled", True),
                    quiet_hours_start=prefs.get("quiet_hours_start", "22:00"),
                    quiet_hours_end=prefs.get("quiet_hours_end", "07:00"),
                    language=prefs.get("language", "bn"),
                    updated_at=now_iso,
                )
                session.add(rec)
            else:
                if "enable_in_app" in prefs:
                    rec.enable_in_app = prefs["enable_in_app"]
                if "enable_sms" in prefs:
                    rec.enable_sms = prefs["enable_sms"]
                if "quiet_hours_enabled" in prefs:
                    rec.quiet_hours_enabled = prefs["quiet_hours_enabled"]
                if "quiet_hours_start" in prefs:
                    rec.quiet_hours_start = prefs["quiet_hours_start"]
                if "quiet_hours_end" in prefs:
                    rec.quiet_hours_end = prefs["quiet_hours_end"]
                if "language" in prefs:
                    rec.language = prefs["language"]
                rec.updated_at = now_iso
            session.commit()
            return self.get_notification_preferences(user_id)

    def get_legacy_matter(self, matter_id: str) -> dict[str, Any] | None:
        with self.get_session() as session:
            try:
                res = session.execute(
                    text("SELECT id, user_id, title, matter_type, client_name, status, created_at FROM matters WHERE id = :mid"),
                    {"mid": matter_id},
                ).mappings().first()
                if res:
                    return dict(res)
            except Exception:
                pass
            return None

    def list_legacy_matters(self) -> list[dict[str, Any]]:
        with self.get_session() as session:
            try:
                rows = session.execute(
                    text("SELECT id, user_id, title, matter_type, client_name, status, created_at FROM matters")
                ).mappings().all()
                return [dict(r) for r in rows]
            except Exception:
                return []

    def clear_all_data(self):
        """Used in test fixtures to cleanly wipe test databases."""
        with self.get_session() as session:
            session.query(NotificationPreferenceDB).delete()
            session.query(NotificationDB).delete()
            session.query(CaseDocumentDB).delete()
            session.query(CaseNoteDB).delete()
            session.query(CaseFactDB).delete()
            session.query(CaseEventDB).delete()
            session.query(CasePartyDB).delete()
            session.query(NoticeAnalysisDB).delete()
            session.query(ReminderScheduleDB).delete()
            session.query(DeadlineDB).delete()
            session.query(TaskDB).delete()
            session.query(CaseDB).delete()
            session.query(DocumentFieldDB).delete()
            session.query(DocumentPageDB).delete()
            session.query(DocumentUploadResumableDB).delete()
            # Only wipe ingested S4 documents, preserving migrated legacy records
            session.query(DocumentDB).filter(
                (DocumentDB.storage_key.isnot(None)) | (DocumentDB.owner_id.isnot(None))
            ).delete()
            session.query(EvalResultDB).delete()
            session.query(EvalRunDB).delete()
            session.query(ClaimLinkDB).delete()
            session.query(AIOutputDB).delete()
            session.query(PromptDB).delete()
            session.query(RuleTestDB).delete()
            session.query(RuleVersionDB).delete()
            session.query(RuleDB).delete()
            session.query(AuditLogDB).delete()
            session.query(ConsentDB).delete()
            session.query(DeviceDB).delete()
            session.query(UserDB).delete()
            session.query(BlockedPhoneHashDB).delete()
            session.query(SourcePassageDB).delete()
            session.query(IngestionJobDB).delete()
            session.query(SourceVersionDB).delete()
            session.query(SourceDB).delete()
            session.commit()


# Singleton database manager instance
db_manager = DatabaseManager()
