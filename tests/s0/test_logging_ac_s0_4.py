"""
Test AC-S0-4: Structured Logging and Automated PII Redaction
"""

from services.api.app.logging_config import redact_data, redact_string


def test_redact_phone_numbers():
    text = "User phone is 01712345678 and international +8801812345678."
    redacted = redact_string(text)
    assert "01712345678" not in redacted
    assert "+8801812345678" not in redacted
    assert "[REDACTED_PHONE]" in redacted


def test_redact_emails():
    text = "Contact advocate at lawyer.firm@court.gov.bd for details."
    redacted = redact_string(text)
    assert "lawyer.firm@court.gov.bd" not in redacted
    assert "[REDACTED_EMAIL]" in redacted


def test_redact_nids():
    text = "Citizen national id is 19902691234567890."
    redacted = redact_string(text)
    assert "19902691234567890" not in redacted
    assert "[REDACTED_NID]" in redacted


def test_redact_dictionary_keys():
    payload = {
        "user_id": "u-123",
        "phone": "01711000000",
        "password": "supersecretpassword",
        "otp": "123456",
        "details": {"nid": "5500123456", "safe_field": "public_case_title"},
    }
    cleaned = redact_data(payload)
    assert cleaned["phone"] == "[REDACTED]"
    assert cleaned["password"] == "[REDACTED]"
    assert cleaned["otp"] == "[REDACTED]"
    assert cleaned["details"]["nid"] == "[REDACTED]"
    assert cleaned["details"]["safe_field"] == "public_case_title"
