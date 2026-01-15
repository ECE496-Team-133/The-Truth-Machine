"""
News scrapers for AP, Reuters, and The Guardian
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


def scrape_ap_content(url: str) -> Optional[str]:
    """Scrape content from Associated Press articles."""
    try:
        r = _session.get(url, timeout=30)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        
        # AP article content - try multiple selectors
        article = None
        selectors = [
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
            "[role='article']"
        ]
        
        for selector in selectors:
            article = soup.select_one(selector)
            if article:
                print(f"[DEBUG] AP: Found content with selector: {selector}")
                break
        
        if article:
            # Remove unwanted elements
            for selector in [".advertisement", ".related", ".social", "script", "style", ".newsletter", ".share", ".byline", ".timestamp"]:
                for el in article.select(selector):
                    el.decompose()
            
            # Extract text from paragraphs
            blocks = []
            for p in article.select("p"):
                text = p.get_text(strip=True)
                if text and len(text) > 20:
                    blocks.append(text)
            
            if blocks:
                content = "\n\n".join(blocks)
                print(f"[DEBUG] AP: Extracted {len(blocks)} paragraphs, {len(content)} characters")
                return content
        
        # Fallback: try to get all paragraphs from body
        body = soup.find("body")
        if body:
            blocks = []
            for p in body.select("p"):
                text = p.get_text(strip=True)
                if text and len(text) > 50:  # Longer threshold for fallback
                    blocks.append(text)
            if len(blocks) >= 3:  # Need at least 3 paragraphs
                content = "\n\n".join(blocks[:10])  # Limit to first 10 paragraphs
                print(f"[DEBUG] AP: Fallback extracted {len(blocks)} paragraphs")
                return content
        
        print(f"[WARNING] AP: Could not find article content in {url}")
        print(f"[DEBUG] AP: Page title: {soup.title.string if soup.title else 'No title'}")
        return None
    except Exception as e:
        print(f"[ERROR] AP scraping failed for {url}: {e}")
        import traceback
        traceback.print_exc()
        return None


def scrape_reuters_content(url: str) -> Optional[str]:
    """Scrape content from Reuters articles."""
    try:
        r = _session.get(url, timeout=30)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        
        # Reuters article content - try multiple selectors
        article = None
        selectors = [
            "article",
            ".ArticleBodyWrapper",
            ".StandardArticleBody_body",
            '[data-module="ArticleBody"]',
            ".article-body",
            "div[class*='ArticleBody']",
            "div[class*='article-body']",
            "main article",
            "[role='article']",
            ".article-body__content"
        ]
        
        for selector in selectors:
            article = soup.select_one(selector)
            if article:
                print(f"[DEBUG] Reuters: Found content with selector: {selector}")
                break
        
        if article:
            # Remove unwanted elements
            for selector in [".advertisement", ".related", ".social", "script", "style", ".article-info", ".newsletter", ".byline"]:
                for el in article.select(selector):
                    el.decompose()
            
            # Extract text
            blocks = []
            for p in article.select("p"):
                text = p.get_text(strip=True)
                if text and len(text) > 20:
                    blocks.append(text)
            
            if blocks:
                content = "\n\n".join(blocks)
                print(f"[DEBUG] Reuters: Extracted {len(blocks)} paragraphs, {len(content)} characters")
                return content
        
        # Fallback: try to get all paragraphs from body
        body = soup.find("body")
        if body:
            blocks = []
            for p in body.select("p"):
                text = p.get_text(strip=True)
                if text and len(text) > 50:  # Longer threshold for fallback
                    blocks.append(text)
            if len(blocks) >= 3:  # Need at least 3 paragraphs
                content = "\n\n".join(blocks[:10])  # Limit to first 10 paragraphs
                print(f"[DEBUG] Reuters: Fallback extracted {len(blocks)} paragraphs")
                return content
        
        print(f"[WARNING] Reuters: Could not find article content in {url}")
        print(f"[DEBUG] Reuters: Page title: {soup.title.string if soup.title else 'No title'}")
        return None
    except Exception as e:
        print(f"[ERROR] Reuters scraping failed for {url}: {e}")
        import traceback
        traceback.print_exc()
        return None


def scrape_guardian_content(url: str) -> Optional[str]:
    """Scrape content from The Guardian articles."""
    try:
        r = _session.get(url, timeout=30)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        
        # Guardian article content - try multiple selectors
        article = None
        selectors = [
            "article",
            ".article-body-commercial-selector",
            '[data-module="ArticleBody"]',
            ".content__article-body",
            ".article-body",
            "div[class*='article-body']",
            "div[class*='ArticleBody']",
            "main article",
            "[role='article']",
            ".dcr-1b2qy6v"  # Guardian's article body class
        ]
        
        for selector in selectors:
            article = soup.select_one(selector)
            if article:
                print(f"[DEBUG] Guardian: Found content with selector: {selector}")
                break
        
        if article:
            # Remove unwanted elements
            for selector in [".ad-slot", ".related", ".social", "script", "style", ".submeta", ".newsletter", ".byline"]:
                for el in article.select(selector):
                    el.decompose()
            
            # Extract text
            blocks = []
            for p in article.select("p"):
                text = p.get_text(strip=True)
                if text and len(text) > 20:
                    blocks.append(text)
            
            if blocks:
                content = "\n\n".join(blocks)
                print(f"[DEBUG] Guardian: Extracted {len(blocks)} paragraphs, {len(content)} characters")
                return content
        
        # Fallback: try to get all paragraphs from body
        body = soup.find("body")
        if body:
            blocks = []
            for p in body.select("p"):
                text = p.get_text(strip=True)
                if text and len(text) > 50:  # Longer threshold for fallback
                    blocks.append(text)
            if len(blocks) >= 3:  # Need at least 3 paragraphs
                content = "\n\n".join(blocks[:10])  # Limit to first 10 paragraphs
                print(f"[DEBUG] Guardian: Fallback extracted {len(blocks)} paragraphs")
                return content
        
        print(f"[WARNING] Guardian: Could not find article content in {url}")
        print(f"[DEBUG] Guardian: Page title: {soup.title.string if soup.title else 'No title'}")
        return None
    except Exception as e:
        print(f"[ERROR] Guardian scraping failed for {url}: {e}")
        import traceback
        traceback.print_exc()
        return None


def scrape_news_content(url: str, source: str) -> Optional[str]:
    """
    Route to appropriate scraper based on source.
    
    Args:
        url: The article URL
        source: One of 'wikipedia', 'ap', 'reuters', 'guardian'
    
    Returns:
        Scraped content or None
    """
    if source == 'ap':
        return scrape_ap_content(url)
    elif source == 'reuters':
        return scrape_reuters_content(url)
    elif source == 'guardian':
        return scrape_guardian_content(url)
    elif source == 'wikipedia':
        # Import here to avoid circular imports
        from .wikipedia_scraper import scrape_wikipedia_content
        return scrape_wikipedia_content(url)
    else:
        print(f"[ERROR] Unknown source: {source}")
        return None


def build_source_query(query: str, source: str) -> str:
    """
    Build a search query optimized for a specific source.
    
    Args:
        query: The base query
        source: One of 'wikipedia', 'ap', 'reuters', 'guardian'
    
    Returns:
        Optimized query string
    """
    if source == 'wikipedia':
        return query  # Wikipedia queries are already optimized
    elif source == 'ap':
        return f"{query} site:apnews.com"
    elif source == 'reuters':
        return f"{query} site:reuters.com"
    elif source == 'guardian':
        return f"{query} site:theguardian.com"
    else:
        return query
