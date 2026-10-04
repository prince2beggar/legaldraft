"""
Feature Flags System (SRS Section 2.6, 5.P1 X-007)
Controls gradual module enablement across Phase 1 MVP to Phase 4.
"""

import os

DEFAULT_FLAGS: dict[str, bool] = {
    # Phase 1: MVP (Enabled in P1)
    "M01_AUTH": True,
    "M02_HOME": True,
    "M03_DOCUMENTS": True,
    "M04_NOTICE_INTERPRETER": True,
    "M05_DRAFTING": True,
    "M06_CASE_FOLDER": True,
    "M07_NOTIFICATIONS": True,
    "M08_SHARING_CONSENT": True,
    "M09_SOURCE_LIBRARY": True,
    "M10_ADMIN_KNOWLEDGE": True,
    "M11_INTAKE_TRIAGE": True,
    # Phase 2: Research & Collaboration (Disabled in P1)
    "M12_RESEARCH_WORKSPACE": False,
    "M13_RELATED_CASE_FINDER": False,
    "M14_CITATIONS_BIBLIOGRAPHY": False,
    "M15_RESEARCH_QC": False,
    "M16_LAWYER_PORTAL": False,
    "M17_APPOINTMENTS": False,
    "M25_VOICE_INPUT": False,
    # Phase 3: Land & Scale (Disabled in P1)
    "M18_HANDWRITTEN_DEED": False,
    "M19_DOC_COMPARISON": False,
    "M20_LAW_FIRM_PORTAL": False,
    "M21_BILLING_PAYMENTS": False,
    # Phase 4: Ecosystem (Disabled in P1)
    "M22_LAWYER_MARKETPLACE": False,
    "M23_TAX_COMPLIANCE": False,
    "M24_OFFICIAL_INTEGRATIONS": False,
}


class FeatureFlagManager:
    def __init__(self):
        self._flags = dict(DEFAULT_FLAGS)
        for key in self._flags:
            env_val = os.getenv(f"FEATURE_{key}")
            if env_val is not None:
                self._flags[key] = env_val.lower() in ("true", "1", "yes")

    def is_enabled(self, flag_name: str) -> bool:
        return self._flags.get(flag_name, False)

    def set_flag(self, flag_name: str, enabled: bool) -> None:
        self._flags[flag_name] = enabled

    def get_all(self) -> dict[str, bool]:
        return dict(self._flags)


feature_flags = FeatureFlagManager()
