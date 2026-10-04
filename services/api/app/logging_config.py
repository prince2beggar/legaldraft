"""
Structured Logging with Automated PII Redaction (SRS Section 2.3, 8.2, B15)
Ensures zero personal data or secrets enter stdout / log files.
"""

import json
import logging
import re
from datetime import datetime, timezone
from typing import Any

SENSITIVE_KEYS = {
    "phone",
    "mobile",
    "email",
    "nid",
    "passport",
    "password",
    "token",
    "otp",
    "access_token",
    "refresh_token",
    "secret",
    "authorization",
    "account_number",
    "card_number",
    "pin",
}

PHONE_REGEX = re.compile(r"(\+?880|0)1[3-9]\d{8}")
EMAIL_REGEX = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
NID_REGEX = re.compile(r"\b(\d{10}|\d{13}|\d{17})\b")


def redact_string(val: str) -> str:
    val = PHONE_REGEX.sub("[REDACTED_PHONE]", val)
    val = EMAIL_REGEX.sub("[REDACTED_EMAIL]", val)
    val = NID_REGEX.sub("[REDACTED_NID]", val)
    return val


def redact_data(data: Any) -> Any:
    if isinstance(data, dict):
        sanitized = {}
        for k, v in data.items():
            if str(k).lower() in SENSITIVE_KEYS:
                sanitized[k] = "[REDACTED]"
            else:
                sanitized[k] = redact_data(v)
        return sanitized
    elif isinstance(data, list):
        return [redact_data(item) for item in data]
    elif isinstance(data, str):
        return redact_string(data)
    return data


class StructuredJsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_obj: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": redact_string(record.getMessage()),
        }
        if hasattr(record, "props") and isinstance(record.props, dict):
            log_obj["props"] = redact_data(record.props)

        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_obj, ensure_ascii=False)


def setup_logging(level: int = logging.INFO) -> logging.Logger:
    logger = logging.getLogger("ain_ai")
    logger.setLevel(level)
    logger.handlers.clear()

    handler = logging.StreamHandler()
    handler.setFormatter(StructuredJsonFormatter())
    logger.addHandler(handler)
    return logger


logger = setup_logging()
