"""
News scrapers for AP, Reuters, The Guardian, BBC, NYT, Washington Post,
CNN, Bloomberg, FT, Al Jazeera, CNBC, WSJ, Politico, and The Economist.
"""
from typing import Optional
import requests
from bs4 import BeautifulSoup

# Shared session with retries
_session = requests.Session()
_adapter = requests.adapters.HTTPAdapter(max_retries=3)
_session.mount("https://", _adapter)
_session.headers.update({
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
})


def _generic_scrape(url: str, source_name: str, primary_selectors: list, strip_selectors: Optional[list] = None) -> Optional[str]:
    """
    Generic article scraper. Tries primary_selectors in order; falls back to all <p> in <body>.
    strip_selectors: elements to remove before extracting text (ads, bylines, etc.)
    """
    default_strip = [".advertisement", ".ad-slot", ".related", ".social", "script",
                     "style", ".newsletter", ".share", ".byline", ".timestamp"]
    if strip_selectors is None:
        strip_selectors = default_strip
    else:
        strip_selectors = default_strip + strip_selectors

    try:
        r = _session.get(url, timeout=30)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")

        article = None
        for sel in primary_selectors:
            article = soup.select_one(sel)
            if article:
                print(f"[DEBUG] {source_name}: Found content with selector: {sel}")
                break

        if article:
            for sel in strip_selectors:
                for el in article.select(sel):
                    el.decompose()
            blocks = [p.get_text(strip=True) for p in article.select("p") if len(p.get_text(strip=True)) > 20]
            if blocks:
                content = "\n\n".join(blocks)
                print(f"[DEBUG] {source_name}: Extracted {len(blocks)} paragraphs, {len(content)} chars")
                return content

        # Fallback: all <p> in <body>
        body = soup.find("body")
        if body:
            blocks = [p.get_text(strip=True) for p in body.select("p") if len(p.get_text(strip=True)) > 50]
            if len(blocks) >= 3:
                content = "\n\n".join(blocks[:10])
                print(f"[DEBUG] {source_name}: Fallback extracted {len(blocks)} paragraphs")
                return content

        print(f"[WARNING] {source_name}: Could not find article content in {url}")
        return None
    except Exception as e:
        print(f"[ERROR] {source_name} scraping failed for {url}: {e}")
        return None


def scrape_ap_content(url: str) -> Optional[str]:
    return _generic_scrape(url, "AP", [
        "article",
        ".Article",
        ".ArticleBody",
        ".article-body",
        "[data-module='ArticleBody']",
        ".RichTextStoryBody",
        "div[class*='Article']",
        "div[class*='article']",
        "main article",
        "main .article-body",
        "[role='article']",
    ])


def scrape_reuters_content(url: str) -> Optional[str]:
    return _generic_scrape(url, "Reuters", [
        "article",
        ".ArticleBodyWrapper",
        ".StandardArticleBody_body",
        '[data-module="ArticleBody"]',
        ".article-body",
        "div[class*='ArticleBody']",
        "div[class*='article-body']",
        "main article",
        "[role='article']",
        ".article-body__content",
    ], [".article-info"])


def scrape_guardian_content(url: str) -> Optional[str]:
    return _generic_scrape(url, "Guardian", [
        "article",
        ".article-body-commercial-selector",
        '[data-module="ArticleBody"]',
        ".content__article-body",
        ".article-body",
        "div[class*='article-body']",
        "div[class*='ArticleBody']",
        "main article",
        "[role='article']",
        ".dcr-1b2qy6v",
    ], [".ad-slot", ".submeta"])


def scrape_bbc_content(url: str) -> Optional[str]:
    return _generic_scrape(url, "BBC", [
        "[data-testid='article-body']",
        "[data-component='text-block']",
        ".article__body-content",
        ".story-body__inner",
        ".article-body-component",
        "article",
        "main article",
        "[role='article']",
        "div[class*='ArticleBody']",
        "div[class*='article-body']",
    ])


def scrape_nytimes_content(url: str) -> Optional[str]:
    return _generic_scrape(url, "NYT", [
        "section[name='articleBody']",
        "[data-testid='article-body']",
        ".article-content",
        ".StoryBodyCompanionColumn",
        "article",
        "main article",
        "[role='article']",
        "div[class*='StoryBody']",
        "div[class*='article-body']",
    ])


def scrape_washingtonpost_content(url: str) -> Optional[str]:
    return _generic_scrape(url, "WashPost", [
        "article",
        ".article-body",
        "[data-qa='article-body']",
        ".teaser-content",
        "div[class*='article']",
        "main article",
        "[role='article']",
        ".pb-feed-article",
    ])


def scrape_cnn_content(url: str) -> Optional[str]:
    return _generic_scrape(url, "CNN", [
        "article",
        ".article__content",
        ".l-container",
        "[class*='article-content']",
        "[class*='ArticleContent']",
        "div[class*='Article']",
        "main article",
        "[role='article']",
    ])


def scrape_bloomberg_content(url: str) -> Optional[str]:
    return _generic_scrape(url, "Bloomberg", [
        "article",
        "[class*='article-body']",
        "[class*='Body__content']",
        ".fence-body",
        ".article-body__content",
        "div[class*='body-content']",
        "main article",
        "[role='article']",
    ])


def scrape_ft_content(url: str) -> Optional[str]:
    return _generic_scrape(url, "FT", [
        "article",
        ".article__content-body",
        ".article-content",
        "[class*='article-content']",
        ".n-content-body",
        "main article",
        "[role='article']",
    ])


def scrape_aljazeera_content(url: str) -> Optional[str]:
    return _generic_scrape(url, "Al Jazeera", [
        "article",
        ".wysiwyg",
        "[class*='article-p-wrapper']",
        ".article-body",
        "[class*='Article']",
        "main article",
        "[role='article']",
    ])


def scrape_cnbc_content(url: str) -> Optional[str]:
    return _generic_scrape(url, "CNBC", [
        "article",
        ".ArticleBody-articleBody",
        ".ArticleBody-subtitle",
        "[data-module='body-text']",
        "[class*='ArticleBody']",
        "[class*='article-body']",
        "main article",
        "[role='article']",
    ])


def scrape_wsj_content(url: str) -> Optional[str]:
    return _generic_scrape(url, "WSJ", [
        "article",
        ".article-content",
        "[class*='article-content']",
        ".wsj-article-body",
        "[class*='ArticleBody']",
        "main article",
        "[role='article']",
    ])


def scrape_politico_content(url: str) -> Optional[str]:
    return _generic_scrape(url, "Politico", [
        "article",
        ".article-body",
        ".story-text",
        "[class*='article-body']",
        "[class*='story-text']",
        "main article",
        "[role='article']",
    ])


def scrape_economist_content(url: str) -> Optional[str]:
    return _generic_scrape(url, "Economist", [
        "article",
        ".article__body",
        "[class*='article-body']",
        "[class*='ArticleBody']",
        "main article",
        "[role='article']",
    ])


def scrape_news_content(url: str, source: str) -> Optional[str]:
    """Route to appropriate scraper based on source key."""
    if source == "wikipedia":
        from .wikipedia_scraper import scrape_wikipedia_content
        return scrape_wikipedia_content(url)

    dispatch = {
        "ap":              scrape_ap_content,
        "reuters":         scrape_reuters_content,
        "guardian":        scrape_guardian_content,
        "bbc":             scrape_bbc_content,
        "nytimes":         scrape_nytimes_content,
        "washingtonpost":  scrape_washingtonpost_content,
        "cnn":             scrape_cnn_content,
        "bloomberg":       scrape_bloomberg_content,
        "ft":              scrape_ft_content,
        "aljazeera":       scrape_aljazeera_content,
        "cnbc":            scrape_cnbc_content,
        "wsj":             scrape_wsj_content,
        "politico":        scrape_politico_content,
        "economist":       scrape_economist_content,
    }
    fn = dispatch.get(source)
    if fn:
        return fn(url)
    print(f"[ERROR] Unknown source: {source}")
    return None


# Canonical site: restrictions per source key
_SOURCE_SITES: dict[str, str] = {
    "ap":             "site:apnews.com",
    "reuters":        "site:reuters.com",
    "guardian":       "site:theguardian.com",
    "bbc":            "site:bbc.com",
    "nytimes":        "site:nytimes.com",
    "washingtonpost": "site:washingtonpost.com",
    "cnn":            "site:cnn.com",
    "bloomberg":      "site:bloomberg.com",
    "ft":             "site:ft.com",
    "aljazeera":      "site:aljazeera.com",
    "cnbc":           "site:cnbc.com",
    "wsj":            "site:wsj.com",
    "politico":       "site:politico.com",
    "economist":      "site:economist.com",
}


def build_source_query(query: str, source: str) -> str:
    """Build a Google search query restricted to the given source domain."""
    if source == "wikipedia":
        return query  # Wikipedia queries are handled separately
    site = _SOURCE_SITES.get(source)
    return f"{query} {site}" if site else query
