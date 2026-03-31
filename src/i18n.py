"""
Internationalization (i18n) support for WebVM.

Provides a lightweight JSON-based translation system with:
- Language detection (URL param → cookie → Accept-Language → default)
- Jinja2 template filter `t()` for translating strings
- Language switcher via URL parameter `?lang=zh_CN`
- Session-based language preference persistence
- Fallback to English for missing translations

Translation files are stored in web/i18n/{lang}.json
e.g. web/i18n/zh_CN.json, web/i18n/en.json
"""

import json
import os
from pathlib import Path
from functools import lru_cache
from flask import session, request, make_response


# Available languages
LANGUAGES = {
    "zh_CN": "中文",
    "en":    "English",
}
DEFAULT_LANGUAGE = "en"


def _i18n_dir():
    return Path(__file__).parent.parent / "web" / "i18n"


@lru_cache(maxsize=2)
def _load_translations(lang: str) -> dict:
    """Load and cache a translation JSON file."""
    path = _i18n_dir() / f"{lang}.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    # Fallback to English
    if lang != DEFAULT_LANGUAGE:
        return _load_translations(DEFAULT_LANGUAGE)
    return {}


def get_translations(lang: str) -> dict:
    """Get the full translations dict for a language."""
    return _load_translations(lang)


def get_browser_language() -> str:
    """
    Detect the best matching language from the browser's Accept-Language header.
    Returns the first supported language found, or DEFAULT_LANGUAGE.
    """
    header = request.headers.get("Accept-Language", "")
    for part in header.split(","):
        lang = part.split(";")[0].strip().replace("-", "_")
        if lang in LANGUAGES:
            return lang
        # Try just the base part (e.g. "zh" from "zh-CN")
        base = lang.split("_")[0]
        for supported in LANGUAGES:
            if supported.startswith(base):
                return supported
    return DEFAULT_LANGUAGE


def get_current_language() -> str:
    """
    Determine the current language for the request.
    Priority: URL param ?lang= > session > cookie > Accept-Language > default
    """
    # 1. URL parameter (e.g. /?lang=zh_CN)
    lang = request.args.get("lang")
    if lang in LANGUAGES:
        return lang

    # 2. Session stored preference
    lang = session.get("lang")
    if lang in LANGUAGES:
        return lang

    # 3. Browser preference
    return get_browser_language()


def set_language(lang: str) -> str:
    """
    Persist language preference in session and cookie.
    Returns the language that was set.
    """
    if lang not in LANGUAGES:
        lang = DEFAULT_LANGUAGE
    session["lang"] = lang
    # Set a cookie for persistence (30 days)
    response = make_response()
    response.set_cookie(
        "webvm_lang", lang,
        max_age=60 * 60 * 24 * 30,
        samesite="Lax"
    )
    return lang


def t(key: str, lang: str = None, **kwargs) -> str:
    """
    Translate a dotted-key string and optionally format with kwargs.

    Usage in Python:
        t("nav.dashboard")                    → "仪表盘"
        t("dashboard.meta", lang="zh_CN", os_cat="Linux", os_ver="Ubuntu 24.04")
                                                        → "Linux / Ubuntu 24.04 · 4096MB RAM ..."

    Usage in Jinja2 templates (via filter):
        {{ "nav.dashboard" | t }}
        {{ "dashboard.meta" | t(os_cat=vm.os_category, os_ver=vm.os_version, ...) }}

    Args:
        key: Dot-separated translation key, e.g. "nav.dashboard"
        lang: Language code (defaults to current request language)
        **kwargs: Format arguments for placeholders like {name}

    Returns:
        Translated string, or the key itself if not found.
    """
    if lang is None:
        lang = get_current_language()

    translations = _load_translations(lang)

    # Navigate nested dict by dot-separated key
    parts = key.split(".")
    value = translations
    for part in parts:
        if isinstance(value, dict) and part in value:
            value = value[part]
        else:
            return key  # Not found, return key as-is

    # Format with provided kwargs
    if kwargs:
        try:
            return value.format(**kwargs)
        except (KeyError, ValueError):
            return value

    return value


def lang_select_options(current_lang: str) -> list[dict]:
    """Return list of {id, name, selected} dicts for language selector."""
    return [
        {"id": code, "name": name, "selected": code == current_lang}
        for code, name in LANGUAGES.items()
    ]
