"""
Test JWT Security: Vetted PyJWT, pinned algorithm HS256, exp/nbf validation,
and rejection of tampered, expired, and alg=none tokens (SRS Section 9.3 S1 Fixes).
"""

import time

import jwt
import pytest

from packages.trust_kernel.auth import AuthException, TokenService


def test_jwt_valid_lifecycle():
    """Valid token encodes and decodes claims properly."""
    payload = {
        "sub": "usr-test-123",
        "phone": "01711223344",
        "role": "citizen",
        "device_id": "dev-001",
        "type": "access",
        "exp": int(time.time()) + 3600,
    }
    token = TokenService.encode_token(payload)
    decoded = TokenService.decode_token(token)
    assert decoded["sub"] == "usr-test-123"
    assert decoded["phone"] == "01711223344"
    assert decoded["type"] == "access"


def test_jwt_reject_tampered_signature():
    """Any modification to the token payload or signature is rejected (constant-time check)."""
    payload = {
        "sub": "usr-test-123",
        "phone": "01711223344",
        "role": "citizen",
        "type": "access",
        "exp": int(time.time()) + 3600,
    }
    token = TokenService.encode_token(payload)
    # Tamper with the last 4 characters of signature
    tampered = token[:-4] + ("AAAA" if token[-4:] != "AAAA" else "BBBB")

    with pytest.raises(AuthException) as exc_info:
        TokenService.decode_token(tampered)
    assert exc_info.value.status_code == 401
    assert (
        "signature" in exc_info.value.message.lower()
        or "validation" in exc_info.value.message.lower()
    )


def test_jwt_reject_expired_token():
    """Tokens with exp timestamp in the past must be rejected with 401."""
    secret = TokenService.get_secret()
    past_payload = {
        "sub": "usr-expired-123",
        "type": "access",
        "exp": int(time.time()) - 100,  # Expired 100 seconds ago
    }
    expired_token = jwt.encode(past_payload, secret, algorithm="HS256")

    with pytest.raises(AuthException) as exc_info:
        TokenService.decode_token(expired_token)
    assert exc_info.value.status_code == 401
    assert "expired" in exc_info.value.message.lower()


def test_jwt_reject_alg_none_attack():
    """Unsigned tokens using alg=none or alternative algorithms must be rejected."""
    payload = {
        "sub": "usr-attacker-000",
        "type": "access",
        "role": "admin",
        "exp": int(time.time()) + 3600,
    }
    # Craft an unsigned token with alg=none
    none_token = jwt.encode(payload, key="", algorithm="none")

    with pytest.raises(AuthException) as exc_info:
        TokenService.decode_token(none_token)
    assert exc_info.value.status_code == 401


def test_jwt_secret_from_env(monkeypatch):
    """Secret is loaded from JWT_SECRET environment variable."""
    monkeypatch.setenv("JWT_SECRET", "custom-isolated-secret-key-1234567890-secure-32b")
    payload = {
        "sub": "usr-env-test",
        "type": "access",
        "exp": int(time.time()) + 3600,
    }
    token = TokenService.encode_token(payload)
    decoded = TokenService.decode_token(token)
    assert decoded["sub"] == "usr-env-test"

    # Verifying with wrong secret fails
    monkeypatch.setenv("JWT_SECRET", "different-secret-key-0987654321-secure-32b")
    with pytest.raises(AuthException) as exc_info:
        TokenService.decode_token(token)
    assert exc_info.value.status_code == 401
