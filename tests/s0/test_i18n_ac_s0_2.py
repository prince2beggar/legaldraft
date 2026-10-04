"""
Test AC-S0-2: i18n Translation and Microcopy Completeness
"""

from packages.trust_kernel.i18n import i18n


def test_default_locale_is_bangla():
    assert i18n._default_locale == "bn"
    text = i18n.t("home.prompt")
    assert text == "আপনার সমস্যাটি বলুন"


def test_english_translation():
    text = i18n.t("home.prompt", locale="en")
    assert text == "Tell us what happened"


def test_parameter_substitution():
    text = i18n.t("next.deadline.overdue", locale="bn", title="শুনানি", days_overdue=3)
    assert "শুনানি" in text
    assert "3 দিন পার হয়েছে" in text


def test_core_microcopy_keys_present():
    core_keys = [
        "home.prompt",
        "next.title",
        "action.scan",
        "action.upload",
        "action.draft",
        "label.ai_not_checked",
        "legal.disclaimer.short",
        "field.extracted",
        "field.reviewed",
        "field.verified",
        "notfound",
        "nosource",
        "lawyer.ask",
        "share.sheet.title",
        "deadline.confirm",
        "deadline.how",
        "if_ignored.not_stated",
        "urgent.title",
        "citation.incomplete",
    ]
    for key in core_keys:
        bn_val = i18n.t(key, locale="bn")
        en_val = i18n.t(key, locale="en")
        assert bn_val != key, f"Missing Bengali key: {key}"
        assert en_val != key, f"Missing English key: {key}"
