from __future__ import annotations

import time
from typing import Optional
from urllib.parse import urlparse, unquote

import requests
from bs4 import BeautifulSoup

from .constants import WIKI_USER_AGENT

REMOVE_SELECTORS = [
    ".navbox",
    ".infobox",
    ".sidebar",
    ".reference",
    ".mw-editsection",
    ".mw-jump-link",
    ".toc",
    ".catlinks",
    ".mw-cite-backlink",
]

# Shared session with retries and a compliant User-Agent
_session = requests.Session()
_adapter = requests.adapters.HTTPAdapter(max_retries=3)
_session.mount("https://", _adapter)
_session.headers.update({"User-Agent": WIKI_USER_AGENT, "Accept": "text/html,*/*"})


def _extract_title_from_wiki_url(url: str) -> Optional[str]:
    """
    Convert https://en.wikipedia.org/wiki/Ada_Lovelace  -> Ada_Lovelace
    Handles anchors and querystrings gracefully.
    """
    try:
        parsed = urlparse(url)
        if "wikipedia.org" not in parsed.netloc:
            return None
        parts = parsed.path.split("/")
        if len(parts) >= 3 and parts[1] == "wiki":
            return unquote(parts[2])
    except Exception:
        return None
    return None


def _wiki_rest_plain_text(title: str) -> Optional[str]:
    """
    Wikipedia REST: plain text of a page.
    Docs: https://en.wikipedia.org/api/rest_v1/#/Page%20content/get_page_plain_title
    """
    rest_url = f"https://en.wikipedia.org/api/rest_v1/page/plain/{title}"
    r = _session.get(rest_url, timeout=30)
    if r.status_code == 200 and r.text.strip():
        # The plain endpoint already returns readable text
        return r.text
    return None


def _wiki_rest_mobile_html(title: str) -> Optional[str]:
    """
    Wikipedia REST: mobile-html, then strip out boilerplate.
    Docs: https://en.wikipedia.org/api/rest_v1/#/Page%20content/get_page_mobile_html_title
    """
    rest_url = f"https://en.wikipedia.org/api/rest_v1/page/mobile-html/{title}"
    r = _session.get(rest_url, timeout=30, headers={"Accept": "text/html"})
    if r.status_code != 200:
        return None
    soup = BeautifulSoup(r.text, "html.parser")

    # Remove non-content elements similar to desktop selectors
    for sel in REMOVE_SELECTORS:
        for el in soup.select(sel):
            el.decompose()

    blocks = []
    for el in soup.select("h1,h2,h3,h4,h5,h6,p,li"):
        text = el.get_text(strip=True)
        if text and len(text) > 10:
            blocks.append(text)
    return "\n\n".join(blocks) if blocks else None


def _generic_html_scrape(url: str) -> Optional[str]:
    """
    Fallback: generic HTML scrape with proper headers.
    Some sites reject non-browser UAs — we comply with Wikipedia’s UA policy above.
    """
    r = _session.get(url, timeout=30)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")

    content = soup.select_one("#mw-content-text .mw-parser-output") or soup
    for sel in REMOVE_SELECTORS:
        for el in content.select(sel):
            el.decompose()

    blocks = []
    for el in content.select("h1,h2,h3,h4,h5,h6,p,li"):
        text = el.get_text(strip=True)
        if text and len(text) > 10:
            blocks.append(text)
    return "\n\n".join(blocks) if blocks else None


def scrape_wikipedia_content(url: str) -> Optional[str]:
    """
    Robust scraper:
      • If URL is Wikipedia, prefer REST API (plain → mobile-html) to avoid 403s.
      • Otherwise, fall back to generic HTML scraping.
      • Always send a proper User-Agent and retry gently.
    """
    # Try Wikipedia-specific strategies if applicable
    title = _extract_title_from_wiki_url(url)
    if title:
        # 1) Plain-text API
        try:
            txt = _wiki_rest_plain_text(title)
            if txt:
                return txt
        except requests.HTTPError:
            pass
        except Exception:
            pass

        # 2) Mobile HTML API
        try:
            txt = _wiki_rest_mobile_html(title)
            if txt:
                return txt
        except requests.HTTPError:
            pass
        except Exception:
            pass

        # Small backoff before generic try
        time.sleep(0.4)

    # 3) Generic scrape (works for non-Wikipedia or as last resort)
    try:
        return _generic_html_scrape(url)
    except requests.HTTPError as e:
        # Surface a clean error line like your original
        print(f"[ERROR] Wikipedia scraping failed: {e}")
        return None
    except Exception as e:
        print(f"[ERROR] Wikipedia scraping failed: {e}")
        return None
