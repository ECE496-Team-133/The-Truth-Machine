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
    ".mw-editsection",
    ".mw-jump-link",
    ".toc",
    ".catlinks",
    ".mw-cite-backlink",
]

# Selectors for reference elements that should be converted to text markers
REFERENCE_SELECTORS = [
    ".reference",
    "sup.reference",
    "span.reference",
]

# Shared session with retries and a compliant User-Agent
_session = requests.Session()
_adapter = requests.adapters.HTTPAdapter(max_retries=3)
_session.mount("https://", _adapter)
_session.headers.update({"User-Agent": WIKI_USER_AGENT, "Accept": "text/html,*/*"})


def extract_title_from_wiki_url(url: str) -> Optional[str]:
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


def _preserve_reference_markers(soup):
    """
    Preserve Wikipedia reference markers like [1] before removing reference elements.
    Converts reference elements to plain text markers so they appear in extracted text.
    """
    import re
    from bs4 import NavigableString
    
    for selector in REFERENCE_SELECTORS:
        for ref_el in soup.select(selector):
            # Extract the text content (should be like [1], [2], etc.)
            ref_text = ref_el.get_text(strip=True)
            
            # If it looks like a reference marker (starts with [ and ends with ])
            # or if it's empty but the element has an id that looks like a reference
            if not ref_text:
                # Try to get the reference number from the element's id or class
                ref_id = ref_el.get('id', '')
                if 'ref-' in ref_id:
                    # Extract number from id like "cite_ref-1" -> "1"
                    match = re.search(r'(\d+)', ref_id)
                    if match:
                        ref_text = f"[{match.group(1)}]"
                elif ref_el.get('class') and any('ref' in str(c) for c in ref_el.get('class', [])):
                    # Try to extract from parent or sibling
                    parent = ref_el.parent
                    if parent:
                        parent_text = parent.get_text(strip=True)
                        # Look for [number] pattern in parent
                        match = re.search(r'\[(\d+)\]', parent_text)
                        if match:
                            ref_text = f"[{match.group(1)}]"
            
            # If we found reference text, replace the element with a text node
            if ref_text and ref_text.startswith('[') and ref_text.endswith(']'):
                # Replace the element with a text node containing just the marker
                ref_el.replace_with(NavigableString(ref_text))
            elif ref_text:
                # If it has text but not in [number] format, try to extract the number
                match = re.search(r'\[(\d+)\]', ref_text)
                if match:
                    ref_el.replace_with(NavigableString(f"[{match.group(1)}]"))
                else:
                    # If we can't determine the reference, just remove it
                    ref_el.decompose()
            else:
                # If we can't determine the reference, just remove it
                ref_el.decompose()


def _extract_text_preserving_spacing(element) -> str:
    """
    Extract text from an element while preserving spacing exactly as it appears.
    Uses empty separator to avoid adding spaces between elements, preserving original spacing.
    """
    if element is None:
        return ""
    
    import re
    
    # Use separator='' to NOT add spaces between elements - preserve original spacing exactly
    # This prevents BeautifulSoup from adding unwanted spaces between inline elements
    text = element.get_text(separator='', strip=False)
    
    # Normalize all whitespace (tabs, newlines, multiple spaces) to single spaces
    # This preserves actual spaces in the content but normalizes formatting whitespace
    text = re.sub(r'\s+', ' ', text)
    
    # Only fix one thing: remove spaces before reference markers like [1], [2], etc.
    # Reference markers should be directly attached to the preceding text
    text = re.sub(r' (\[[0-9]+\])', r'\1', text)
    
    # Clean up any double spaces that might have been created
    text = re.sub(r'  +', ' ', text)
    
    # Strip leading/trailing whitespace
    text = text.strip()
    
    return text


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

    # Preserve reference markers before removing other elements
    _preserve_reference_markers(soup)

    # Remove non-content elements
    for sel in REMOVE_SELECTORS:
        for el in soup.select(sel):
            el.decompose()

    blocks = []
    for el in soup.select("h1,h2,h3,h4,h5,h6,p,li"):
        text = _extract_text_preserving_spacing(el)
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
    
    # Preserve reference markers before removing other elements
    _preserve_reference_markers(content)

    for sel in REMOVE_SELECTORS:
        for el in content.select(sel):
            el.decompose()

    blocks = []
    for el in content.select("h1,h2,h3,h4,h5,h6,p,li"):
        text = _extract_text_preserving_spacing(el)
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
    title = extract_title_from_wiki_url(url)
    if title:
        # 1) Plain-text API
        try:
            txt = _wiki_rest_plain_text(title)
            if txt:
                print("Plain Text API")
                return txt
        except requests.HTTPError:
            pass
        except Exception:
            pass

        # 2) Mobile HTML API
        try:
            txt = _wiki_rest_mobile_html(title)
            if txt:
                print("Mobile HTML API")
                return txt
        except requests.HTTPError:
            pass
        except Exception:
            pass

        # Small backoff before generic try
        time.sleep(0.4)

    # 3) Generic scrape (works for non-Wikipedia or as last resort)
    try:
        print("Generic scrape")
        return _generic_html_scrape(url)
    except requests.HTTPError as e:
        # Surface a clean error line like your original
        print(f"[ERROR] Wikipedia scraping failed: {e}")
        return None
    except Exception as e:
        print(f"[ERROR] Wikipedia scraping failed: {e}")
        return None
