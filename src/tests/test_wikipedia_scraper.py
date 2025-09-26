from src.utils import wikipedia_scraper as ws


def test_scraper_prefers_rest_plain(monkeypatch):
    monkeypatch.setattr(ws, "_extract_title_from_wiki_url", lambda url: "Ada_Lovelace")
    monkeypatch.setattr(ws, "_wiki_rest_plain_text", lambda title: "Plain text")
    monkeypatch.setattr(ws, "_wiki_rest_mobile_html", lambda title: None)
    monkeypatch.setattr(ws, "_generic_html_scrape", lambda url: None)
    out = ws.scrape_wikipedia_content("https://en.wikipedia.org/wiki/Ada_Lovelace")
    assert out == "Plain text"


def test_scraper_falls_back_to_mobile_html(monkeypatch):
    monkeypatch.setattr(ws, "_extract_title_from_wiki_url", lambda url: "Ada_Lovelace")
    monkeypatch.setattr(ws, "_wiki_rest_plain_text", lambda title: None)
    monkeypatch.setattr(ws, "_wiki_rest_mobile_html", lambda title: "HTML content")
    monkeypatch.setattr(ws, "_generic_html_scrape", lambda url: None)
    out = ws.scrape_wikipedia_content("https://en.wikipedia.org/wiki/Ada_Lovelace")
    assert "HTML" in out


def test_scraper_generic(monkeypatch):
    monkeypatch.setattr(ws, "_extract_title_from_wiki_url", lambda url: None)
    monkeypatch.setattr(ws, "_generic_html_scrape", lambda url: "Generic")
    out = ws.scrape_wikipedia_content("https://example.com/page")
    assert out == "Generic"
