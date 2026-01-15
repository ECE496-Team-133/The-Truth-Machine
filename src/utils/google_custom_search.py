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
        
        # Log API response details for debugging
        search_info = data.get("searchInformation", {})
        total_results = search_info.get("totalResults", "0")
        print(f"[DEBUG] Google Custom Search API response: totalResults={total_results}, query='{query}'")
        
        items = data.get("items", [])
        urls = [item.get("link") for item in items if item.get("link")]
        
        if urls:
            print(f"[DEBUG] Found {len(urls)} URLs from Google Custom Search")
            return urls[:n]
        else:
            # Log why no results were found
            if "error" in data:
                print(f"[WARNING] Google Custom Search API error: {data['error']}")
            elif total_results == "0":
                print(f"[WARNING] Google Custom Search returned 0 results for query: '{query}'")
            else:
                print(f"[WARNING] Google Custom Search returned {len(items)} items but no valid URLs")
            return None
    except requests.exceptions.HTTPError as e:
        print(f"[ERROR] Google Custom Search HTTP error: {e}")
        if hasattr(e.response, 'text'):
            print(f"[ERROR] Response body: {e.response.text[:500]}")
        return None
    except Exception as e:
        print(f"[ERROR] Google Custom Search failed: {e}")
        import traceback
        traceback.print_exc()
        return None
