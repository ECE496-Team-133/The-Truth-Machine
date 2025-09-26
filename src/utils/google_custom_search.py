import requests
from typing import List, Optional
from .config import SETTINGS

GOOGLE_CSE_ENDPOINT = "https://www.googleapis.com/customsearch/v1"


def get_first_n_results_urls(query: str, n: int = 1) -> Optional[List[str]]:
    params = {
        "key": SETTINGS.custom_search_api_key,
        "cx": SETTINGS.custom_search_engine_id,
        "q": query,
    }
    try:
        resp = requests.get(GOOGLE_CSE_ENDPOINT, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        items = data.get("items", [])
        urls = [item.get("link") for item in items if item.get("link")]
        return urls[:n] if urls else None
    except Exception as e:
        print(f"[ERROR] Google Custom Search failed: {e}")
        return None
