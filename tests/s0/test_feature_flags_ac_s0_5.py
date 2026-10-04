"""
Test AC-S0-5: Modular Feature Flags and Phase Gating
"""

from packages.trust_kernel.feature_flags import FeatureFlagManager


def test_phase1_mvp_flags_enabled_by_default():
    mgr = FeatureFlagManager()
    assert mgr.is_enabled("M01_AUTH") is True
    assert mgr.is_enabled("M02_HOME") is True
    assert mgr.is_enabled("M03_DOCUMENTS") is True
    assert mgr.is_enabled("M04_NOTICE_INTERPRETER") is True
    assert mgr.is_enabled("M05_DRAFTING") is True
    assert mgr.is_enabled("M06_CASE_FOLDER") is True
    assert mgr.is_enabled("M07_NOTIFICATIONS") is True
    assert mgr.is_enabled("M08_SHARING_CONSENT") is True
    assert mgr.is_enabled("M09_SOURCE_LIBRARY") is True
    assert mgr.is_enabled("M10_ADMIN_KNOWLEDGE") is True
    assert mgr.is_enabled("M11_INTAKE_TRIAGE") is True


def test_later_phase_modules_disabled():
    mgr = FeatureFlagManager()
    assert mgr.is_enabled("M12_RESEARCH_WORKSPACE") is False
    assert mgr.is_enabled("M16_LAWYER_PORTAL") is False
    assert mgr.is_enabled("M18_HANDWRITTEN_DEED") is False
    assert mgr.is_enabled("M22_LAWYER_MARKETPLACE") is False
    assert mgr.is_enabled("M24_OFFICIAL_INTEGRATIONS") is False


def test_flag_override():
    mgr = FeatureFlagManager()
    assert mgr.is_enabled("M12_RESEARCH_WORKSPACE") is False
    mgr.set_flag("M12_RESEARCH_WORKSPACE", True)
    assert mgr.is_enabled("M12_RESEARCH_WORKSPACE") is True
