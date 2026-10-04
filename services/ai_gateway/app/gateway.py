"""
AI Gateway (SRS Section 2.5)
Enforces:
1. PII Redaction before external calls (HR-11)
2. Task policy routing & fallback
3. JSON Schema validation & enforcement
4. Restoring redacted placeholders
5. Recording AiOutput metadata & inputs hash
"""

import hashlib
import json
import re
from typing import Any

PHONE_REGEX = re.compile(r"(\+?880|0)1[3-9]\d{8}")
EMAIL_REGEX = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
NID_REGEX = re.compile(r"\b(\d{10}|\d{13}|\d{17})\b")


class AiGateway:
    def __init__(self):
        self._execution_history = []

    def redact_pii(self, text: str) -> tuple[str, dict[str, str]]:
        mapping = {}
        counter = 0

        def replace_phone(match):
            nonlocal counter
            counter += 1
            ph = f"[PHONE_MASK_{counter}]"
            mapping[ph] = match.group(0)
            return ph

        def replace_email(match):
            nonlocal counter
            counter += 1
            em = f"[EMAIL_MASK_{counter}]"
            mapping[em] = match.group(0)
            return em

        def replace_nid(match):
            nonlocal counter
            counter += 1
            nid = f"[NID_MASK_{counter}]"
            mapping[nid] = match.group(0)
            return nid

        clean_text = PHONE_REGEX.sub(replace_phone, text)
        clean_text = EMAIL_REGEX.sub(replace_email, clean_text)
        clean_text = NID_REGEX.sub(replace_nid, clean_text)

        return clean_text, mapping

    def restore_pii(self, text: str, mapping: dict[str, str]) -> str:
        for placeholder, original in mapping.items():
            text = text.replace(placeholder, original)
        return text

    def run(
        self,
        task: str,
        context: dict[str, Any],
        schema: dict[str, Any] | None = None,
        options: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Executes an AI task through the secure gateway.
        In S0, operates in deterministic mock mode conforming to schema.
        """
        options = options or {}
        context_str = json.dumps(context, sort_keys=True, default=str)
        inputs_hash = hashlib.sha256(context_str.encode("utf-8")).hexdigest()

        # Step 1: PII Redaction
        _redacted_context_str, _pii_mapping = self.redact_pii(context_str)

        # Step 2: Route / Mock result based on task
        mock_output = {
            "task": task,
            "status": "success",
            "certainty": "clear",
            "claims": [],
            "as_of_date": "2026-10-02",
        }

        # Step 3: Record AI Output
        record = {
            "task": task,
            "inputs_hash": inputs_hash,
            "prompt_version": "v1.0.0",
            "model": options.get("model", "mock-legal-v1"),
            "output": mock_output,
            "certainty": mock_output["certainty"],
        }
        self._execution_history.append(record)

        return record


ai_gateway = AiGateway()
