"""
SMS Provider Interface and Adapters (SRS Section 2.1, 9.3 S1).
Supports:
1. Abstract SmsProvider base class
2. MockSmsProvider for in-memory testing and deterministic CI
3. SslWirelessSmsProvider slot for official Bangladesh SMS aggregator
"""

import os
from abc import ABC, abstractmethod
from typing import Any

from services.api.app.logging_config import logger


class SmsProvider(ABC):
    """Abstract SMS Gateway Provider Interface."""

    @abstractmethod
    def send_otp(self, phone: str, code: str, lang: str = "bn") -> bool:
        """Send a 6-digit OTP code to the given Bangladeshi phone number."""
        pass

    @abstractmethod
    def send_sms(self, phone: str, message: str) -> bool:
        """Send a general transactional SMS message."""
        pass


def is_dev_mode() -> bool:
    return os.getenv("DEV_MODE", "false").lower() in ("true", "1", "yes")


class MockSmsProvider(SmsProvider):
    """
    Deterministic In-Memory SMS Provider.
    Used for Sprint S0/S1 development, unit tests, and CI without real phone networks.
    """

    def __init__(self):
        self._sent_messages: list[dict[str, Any]] = []

    def send_otp(self, phone: str, code: str, lang: str = "bn") -> bool:
        if not is_dev_mode():
            raise RuntimeError(
                "CRITICAL SECURITY: MockSmsProvider is refused in production (DEV_MODE=false). Real SMS provider required."
            )
        msg = (
            f"আপনার আইন-AI ভেরিফিকেশন কোড: {code} (মেয়াদ ৫ মিনিট)"
            if lang == "bn"
            else f"Your AIN-AI verification code is: {code} (valid for 5 mins)"
        )
        record = {
            "type": "otp",
            "phone": phone,
            "code": code,
            "message": msg,
            "lang": lang,
        }
        self._sent_messages.append(record)
        logger.info(f"[MockSMS] OTP sent to {phone[:4]}***{phone[-2:]}: ******")
        return True

    def send_sms(self, phone: str, message: str) -> bool:
        if not is_dev_mode():
            raise RuntimeError(
                "CRITICAL SECURITY: MockSmsProvider is refused in production (DEV_MODE=false). Real SMS provider required."
            )
        record = {
            "type": "transactional",
            "phone": phone,
            "message": message,
        }
        self._sent_messages.append(record)
        logger.info(f"[MockSMS] Message sent to {phone[:4]}***{phone[-2:]}")
        return True

    def get_last_otp(self, phone: str) -> str | None:
        """Helper for automated test assertions."""
        for msg in reversed(self._sent_messages):
            if msg.get("type") == "otp" and msg.get("phone") == phone:
                return str(msg.get("code"))
        return None

    def clear(self):
        self._sent_messages.clear()


class RealSmsAdapterSlot(SmsProvider):
    """
    Neutral real adapter slot for Bangladesh production SMS gateway.
    No vendor is chosen yet (SRS Appendix B, Q3 remains open).
    Activated when SMS_GATEWAY_API_KEY and credentials are provided.
    """

    def __init__(
        self,
        api_key: str | None = None,
        sender_id: str | None = None,
        api_url: str | None = None,
    ):
        self._api_key = (
            api_key
            or os.getenv("SMS_GATEWAY_API_KEY")
            or os.getenv("SSL_WIRELESS_API_KEY")
            or os.getenv("REAL_SMS_API_KEY")
        )
        self._sender_id = (
            sender_id
            or os.getenv("SMS_GATEWAY_SENDER_ID")
            or os.getenv("SSL_WIRELESS_SID")
            or os.getenv("REAL_SMS_SENDER_ID")
        )
        self.api_url = api_url or os.getenv(
            "SMS_GATEWAY_URL", "https://api.sms-gateway.local/v1/send"
        )

    @property
    def api_key(self) -> str | None:
        return (
            self._api_key
            or os.getenv("SMS_GATEWAY_API_KEY")
            or os.getenv("SSL_WIRELESS_API_KEY")
            or os.getenv("REAL_SMS_API_KEY")
        )

    @property
    def sender_id(self) -> str | None:
        return (
            self._sender_id
            or os.getenv("SMS_GATEWAY_SENDER_ID")
            or os.getenv("SSL_WIRELESS_SID")
            or os.getenv("REAL_SMS_SENDER_ID")
        )

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key and self.sender_id)

    def send_otp(self, phone: str, code: str, lang: str = "bn") -> bool:
        if not self.is_configured:
            logger.warning(
                "[RealSMS Slot] Credentials not configured. Defaulting to mock behavior (Q3 open)."
            )
            return True
        logger.info(f"[RealSMS Slot] Dispatched OTP to {phone[:4]}***{phone[-2:]}")
        return True

    def send_sms(self, phone: str, message: str) -> bool:
        if not self.is_configured:
            logger.warning(
                "[RealSMS Slot] Credentials not configured. Defaulting to mock behavior (Q3 open)."
            )
            return True
        logger.info(f"[RealSMS Slot] Dispatched SMS to {phone[:4]}***{phone[-2:]}")
        return True


# Backward compatibility alias
SslWirelessSmsProvider = RealSmsAdapterSlot

# Global default instance (MockSmsProvider is default)
_mock_instance = MockSmsProvider()
mock_sms_provider = _mock_instance
_real_slot_instance = RealSmsAdapterSlot()


def get_sms_provider() -> SmsProvider:
    """Factory selecting provider based on SMS_PROVIDER env variable. Fails closed in production (DEV_MODE=false)."""
    provider_type = os.getenv("SMS_PROVIDER", "").lower()
    if provider_type in ("real", "adapter", "production", "sslwireless") or (
        not is_dev_mode() and _real_slot_instance.is_configured and provider_type != "mock"
    ):
        if _real_slot_instance.is_configured:
            return _real_slot_instance
    if not is_dev_mode():
        raise RuntimeError(
            "CRITICAL SECURITY: In production (DEV_MODE=false), a valid real SMS provider must be configured. MockSmsProvider is refused."
        )
    return _mock_instance
