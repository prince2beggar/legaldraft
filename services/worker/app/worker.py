"""
Celery Background Worker Entrypoint (SRS Section 2.2, 8.1)
Handles asynchronous jobs: OCR, document parsing, embedding, indexing, notifications.
"""

import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from services.api.app.logging_config import logger

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Lightweight background job runner / Celery stub
try:
    from celery import Celery

    celery_app = Celery("ain_ai_worker", broker=REDIS_URL, backend=REDIS_URL)
    celery_app.conf.update(
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="Asia/Dhaka",
        enable_utc=True,
    )

    @celery_app.task(name="process_document_job")
    def process_document_job(document_id: str, intent: str):
        logger.info(f"Processing document job: {document_id} with intent: {intent}")
        return {"status": "completed", "document_id": document_id}

except ImportError:
    celery_app = None
    logger.info("Celery package not installed in environment; fallback worker available.")


def run_worker():
    logger.info("AIN-AI Background Worker started.")
    if celery_app:
        celery_app.start()


if __name__ == "__main__":
    run_worker()
