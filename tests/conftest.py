"""
Global pytest configuration and environment bootstrapping.
Ensures tests run in complete isolation from the real development database and storage,
and enforces a fail-fast safeguard against touching production/development files.
"""

import os
import shutil
import tempfile
from pathlib import Path

import pytest
from dotenv import load_dotenv

# Load .env if present
load_dotenv()

# Bootstrap test secrets in environment if not already set by shell
if "PHONE_BLOCKLIST_SALT" not in os.environ:
    os.environ["PHONE_BLOCKLIST_SALT"] = "ain-ai-test-environment-salt-2026-isolated"
if "JWT_SECRET" not in os.environ:
    os.environ["JWT_SECRET"] = "ain-ai-development-signing-key-bangladesh-legal-os-s1"

# ---------------------------------------------------------------------------
# Test Isolation Setup: Use temporary database & temporary storage folder
# ---------------------------------------------------------------------------
_TEST_ROOT = Path(tempfile.mkdtemp(prefix="ain_ai_pytest_isolated_"))
_TEST_DB_PATH = _TEST_ROOT / "isolated_test_ain_ai.db"
_TEST_STORAGE_PATH = _TEST_ROOT / "storage"
_TEST_STORAGE_PATH.mkdir(parents=True, exist_ok=True)

# Seed isolated test DB from current ain_ai.db so baseline tables & migrations exist
_PROD_DB = Path("ain_ai.db").resolve()
if _PROD_DB.exists():
    shutil.copy2(_PROD_DB, _TEST_DB_PATH)

os.environ["DATABASE_URL"] = f"sqlite:///{_TEST_DB_PATH.resolve()}"
os.environ["STORAGE_DIR"] = str(_TEST_STORAGE_PATH.resolve())

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from packages.trust_kernel.db import db_manager  # noqa: E402

test_engine = create_engine(
    f"sqlite:///{_TEST_DB_PATH.resolve()}",
    connect_args={"check_same_thread": False},
    echo=False,
)
db_manager.url = f"sqlite:///{_TEST_DB_PATH.resolve()}"
db_manager.engine = test_engine
db_manager.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

from packages.trust_kernel.document_engine import document_service  # noqa: E402

document_service.db = db_manager


@pytest.fixture(autouse=True)
def safeguard_production_database_and_storage(request):
    """
    Safeguard (SRS / Sprint S4 Definition of Done):
    Fails immediately if any test attempts to run against the real development database (ain_ai.db)
    or the real development storage folder.
    (Exception: test_legacy_data_integrity_and_migration is allowed to perform read-only inspection).
    """
    if request.node.name == "test_legacy_data_integrity_and_migration":
        return

    # 1. Database URL safeguard
    current_db_url = os.environ.get("DATABASE_URL", "")
    if current_db_url.startswith("sqlite:///"):
        target_file = Path(current_db_url.replace("sqlite:///", "")).resolve()
        if target_file == _PROD_DB:
            pytest.fail(
                f"SAFEGUARD ERROR: Test '{request.node.name}' is pointed directly at real development database: {current_db_url}"
            )

    # 2. Storage directory safeguard
    current_storage = os.environ.get("STORAGE_DIR", "")
    real_storage_path = Path("storage").resolve()
    if current_storage:
        target_storage = Path(current_storage).resolve()
        if target_storage == real_storage_path:
            pytest.fail(
                f"SAFEGUARD ERROR: Test '{request.node.name}' is pointed directly at real development storage folder: {current_storage}"
            )


@pytest.fixture
def isolated_db_manager():
    return db_manager


@pytest.fixture
def test_citizen_user(isolated_db_manager):
    user_data = {
        "id": "citizen-user-test-s5",
        "phone": "+8801711000111",
        "name": "মো: তানভীর হোসেন",
        "role": "citizen",
        "roles": ["citizen"],
        "preferred_lang": "bn",
        "numeral_style": "bn",
        "status": "active",
        "is_onboarded": True,
    }
    isolated_db_manager.save_user(user_data)
    return user_data

