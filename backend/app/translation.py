"""Query translation for multilingual search.

Most 3D-model catalogs (Printables, Thingiverse) are indexed in English. So a
Ukrainian user typing "ваза" finds nothing. We detect non-Latin script in the
query, translate to English via a free translation service, cache the result
in Redis (translations don't change often), and feed the English form to
source adapters.

Provider abstraction lets us swap MyMemory for DeepL/Google later without
touching callers.
"""

from __future__ import annotations

import hashlib
import logging
import unicodedata
from typing import TYPE_CHECKING

import httpx
from langdetect import DetectorFactory, LangDetectException, detect

from app.core.cache import get_redis

if TYPE_CHECKING:
    from app.core.cache import InMemoryCache

# langdetect is non-deterministic by default — seed it for stable results.
DetectorFactory.seed = 0

log = logging.getLogger(__name__)

_CACHE_TTL_SECONDS = 7 * 24 * 60 * 60  # 7 days
_MYMEMORY_URL = "https://api.mymemory.translated.net/get"
_HTTP_TIMEOUT = 5.0


_SCRIPT_DEFAULT_LANG = {
    "CYRILLIC": "ru",
    "GREEK": "el",
    "ARABIC": "ar",
    "HEBREW": "he",
    "HIRAGANA": "ja",
    "KATAKANA": "ja",
    "HANGUL": "ko",
    "CJK": "zh-CN",
    "DEVANAGARI": "hi",
    "THAI": "th",
}


def needs_translation(query: str) -> bool:
    """True if the query contains alphabetic chars outside the Latin block."""
    for c in query:
        if not c.isalpha():
            continue
        try:
            name = unicodedata.name(c)
        except ValueError:
            continue
        if "LATIN" not in name:
            return True
    return False


def _detect_source_lang(query: str) -> str | None:
    """Best-effort source language code, suitable for MyMemory's `langpair` source slot."""
    try:
        code = detect(query)
        if code and code != "en":
            return code
    except LangDetectException:
        pass

    # langdetect often misfires on short queries (1-2 words). Fall back to
    # script-based defaults: Cyrillic chars in our context are typically
    # Ukrainian or Russian, etc.
    for c in query:
        if not c.isalpha():
            continue
        try:
            name = unicodedata.name(c)
        except ValueError:
            continue
        for script, lang in _SCRIPT_DEFAULT_LANG.items():
            if script in name:
                return lang
    return None


def _cache_key(text: str) -> str:
    return "tr:en:" + hashlib.sha1(text.lower().strip().encode()).hexdigest()


async def _fetch_translation(
    client: httpx.AsyncClient, text: str, source_lang: str
) -> str | None:
    try:
        resp = await client.get(
            _MYMEMORY_URL,
            params={"q": text, "langpair": f"{source_lang}|en"},
            timeout=_HTTP_TIMEOUT,
        )
        resp.raise_for_status()
        body = resp.json()
    except (httpx.HTTPError, ValueError):
        log.exception("translation request failed")
        return None

    data = body.get("responseData") or {}
    translated = data.get("translatedText")
    if not isinstance(translated, str) or not translated.strip():
        return None
    if translated.strip().lower() == text.strip().lower():
        return None  # passthrough means no translation actually happened
    return translated.strip()


async def translate_to_english(
    text: str,
    *,
    redis: "InMemoryCache | None" = None,
    client: httpx.AsyncClient | None = None,
) -> str | None:
    """Return English translation of `text`, or None when no translation needed/available."""
    text = text.strip()
    if not text:
        return None
    if not needs_translation(text):
        log.info("translate: skip (latin) %r", text)
        return None

    redis = redis or get_redis()
    key = _cache_key(text)
    try:
        cached = await redis.get(key)
    except Exception:
        log.exception("cache get failed for translation; continuing")
        cached = None
    if cached:
        log.info("translate: cache hit %r → %r", text, cached)
        return cached if cached != text else None

    source_lang = _detect_source_lang(text)
    if not source_lang:
        log.info("translate: no source lang detected for %r", text)
        return None

    log.info("translate: %r (%s) → en …", text, source_lang)

    own_client = client is None
    client = client or httpx.AsyncClient()
    try:
        translated = await _fetch_translation(client, text, source_lang)
    finally:
        if own_client:
            await client.aclose()

    if translated:
        log.info("translate: %r (%s) → %r", text, source_lang, translated)
        try:
            await redis.set(key, translated, ex=_CACHE_TTL_SECONDS)
        except Exception:
            log.exception("cache set failed for translation; continuing")
    else:
        log.info("translate: no result for %r (%s)", text, source_lang)
    return translated
