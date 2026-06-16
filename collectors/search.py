"""
Pencarian topik di internet menggunakan Tavily Search API dengan fallback
ke Brave Search bila Tavily tidak tersedia atau melebihi limit.

Tambahan: hasil Tavily dibersihkan (HTML strip, whitespace normalize,
truncation) dan didedup berdasarkan URL untuk mengurangi noise sebelum
dikembalikan ke pipeline.
"""

import logging
import re
from typing import Iterable

import requests
from bs4 import BeautifulSoup
from tavily import TavilyClient

from config.settings import BRAVE_API_KEY, MAX_RESULTS_PER_TOPIC, TAVILY_API_KEY

logger = logging.getLogger("collectors.search")

_tavily_client = None


def get_tavily_client():
    global _tavily_client
    if _tavily_client is None:
        if not TAVILY_API_KEY:
            raise ValueError("TAVILY_API_KEY not set. Add on file .env")
        _tavily_client = TavilyClient(api_key=TAVILY_API_KEY)
    return _tavily_client


def _clean_html(text: str) -> str:
    if not text:
        return ""
    # Use BeautifulSoup to remove tags and collapse whitespace
    soup = BeautifulSoup(text, "html.parser")
    cleaned = " ".join(soup.get_text(separator=" ").split())
    return cleaned.strip()


def _truncate_sentence_safe(text: str, max_chars: int = 500) -> str:
    if not text:
        return ""
    text = _clean_html(text)
    if len(text) <= max_chars:
        return text
    cut = text[: max_chars]
    # try to cut at sentence boundary
    pos = max(cut.rfind('. '), cut.rfind('! '), cut.rfind('? '))
    if pos and pos > int(max_chars * 0.6):
        return cut[: pos + 1].strip() + "..."
    return cut.strip() + "..."


def _normalize_title(title: str) -> str:
    if not title:
        return ""
    return re.sub(r"\s+", " ", title).strip()


def _iter_unique_by_url(items: Iterable[dict]) -> Iterable[dict]:
    seen = set()
    for it in items:
        url = (it.get("url") or it.get("source_url") or "").strip()
        if not url or url in seen:
            continue
        seen.add(url)
        yield it


def _search_tavily(topic: str, max_results: int) -> list[dict]:
    client = get_tavily_client()
    response = client.search(
        query=topic,
        max_results=max_results,
        include_raw_content=True,
    )
    results = response.get("results", [])
    cleaned = []
    for r in _iter_unique_by_url(results):
        url = r.get("url") or r.get("link") or ""
        title = _normalize_title(r.get("title") or r.get("name") or url)
        raw = r.get("raw_content") or r.get("content") or ""
        snippet = r.get("content") or raw

        raw_clean = _truncate_sentence_safe(raw, max_chars=2000)
        snippet_clean = _truncate_sentence_safe(snippet, max_chars=500)

        # prefer raw_clean if substantial, else snippet_clean
        content_choice = raw_clean if len(raw_clean) > 120 else snippet_clean
        if not content_choice:
            # skip entries with no useful text
            continue

        cleaned.append(
            {
                "url": url,
                "title": title,
                "content": snippet_clean,
                "raw_content": raw_clean,
            }
        )
    if not cleaned:
        raise ValueError("Tavily returned no usable results.")
    return cleaned


def _search_brave(topic: str, max_results: int) -> list[dict]:
    if not BRAVE_API_KEY:
        raise ValueError("BRAVE_API_KEY not set. Add on file .env")

    headers = {
        "Accept": "application/json",
        "X-Subscription-Token": BRAVE_API_KEY,
    }
    params = {"q": topic, "count": max_results}

    response = requests.get(
        "https://api.search.brave.com/res/v1/web/search",
        headers=headers,
        params=params,
        timeout=20,
    )
    response.raise_for_status()

    data = response.json()
    items = data.get("web", {}).get("results", [])

    results = []
    for item in items:
        snippet = item.get("description") or item.get("snippet") or ""
        results.append(
            {
                "url": item.get("url"),
                "title": item.get("title") or item.get("url"),
                "content": _truncate_sentence_safe(snippet, max_chars=500),
                "raw_content": _truncate_sentence_safe(snippet, max_chars=2000),
            }
        )
    return list(_iter_unique_by_url(results))


def search_topic(topic: str, max_results: int = MAX_RESULTS_PER_TOPIC) -> list[dict]:
    """
    Mencari informasi topik dengan Tavily, lalu fallback ke Brave jika
    Tavily tidak tersedia, melebihi limit, atau gagal.

    Returns:
        List of dict, masing-masing berisi:
        - url
        - title
        - content (snippet)
        - raw_content (isi halaman yang lebih lengkap, jika tersedia)
    """
    try:
        return _search_tavily(topic, max_results)
    except Exception as exc:
        logger.warning(
            "Tavily search failed for %r: %s. Trying Brave Search fallback.",
            topic,
            exc,
        )

    try:
        return _search_brave(topic, max_results)
    except Exception as fallback_exc:
        logger.exception(
            "Brave Search fallback also failed for %r: %s",
            topic,
            fallback_exc,
        )
        raise RuntimeError(
            "Search unavailable: Tavily failed and Brave fallback is not configured or failed."
        ) from fallback_exc
