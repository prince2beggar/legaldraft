"""
i18n Translation Resolver (SRS Section 0.3 B9, 10.6)
Provides string localisation with Bangla (bn) as default.
"""

import json
from pathlib import Path

CONTENT_DIR = Path(__file__).resolve().parent.parent.parent / "content" / "i18n"


class I18nService:
    def __init__(self):
        self._catalogs: dict[str, dict[str, str]] = {}
        self._default_locale = "bn"
        self._load_catalogs()

    def _load_catalogs(self):
        for locale in ["bn", "en"]:
            path = CONTENT_DIR / f"{locale}.json"
            if path.exists():
                with open(path, "r", encoding="utf-8") as f:
                    self._catalogs[locale] = json.load(f)
            else:
                self._catalogs[locale] = {}

    def t(self, key: str, locale: str | None = None, **kwargs) -> str:
        loc = locale or self._default_locale
        catalog = self._catalogs.get(loc, {})
        # Fallback to bn if key not found in requested locale
        text = catalog.get(key)
        if text is None:
            text = self._catalogs.get(self._default_locale, {}).get(key, key)

        if kwargs:
            for k, v in kwargs.items():
                text = text.replace(f"{{{k}}}", str(v))
        return text

    def get_catalog(self, locale: str = "bn") -> dict[str, str]:
        return dict(self._catalogs.get(locale, {}))


i18n = I18nService()
