"""
Local model version of fact-checking that replaces OpenAI calls.
"""

from typing import Optional
from urllib.parse import quote
from .local_openai_client import get_local_openai_client
from .models import ClaimResult


def find_answer_in_article(scraped_content: str, claim: str) -> Optional[ClaimResult]:
    """Find answer in article using local model instead of OpenAI."""
    client = get_local_openai_client()
    result = client.factcheck_claim(claim, scraped_content)
    
    if result:
        try:
            return ClaimResult(
                label=result["label"],
                evidence=result["evidence"]
            )
        except Exception as e:
            print(f"[ERROR] Failed to create ClaimResult: {e}")
            return ClaimResult(label="False", evidence=result.get("evidence", ""))
    
    return None


def build_text_fragment_link(url: str, evidence: Optional[str]) -> str:
    """Build a text fragment link for the evidence."""
    if not evidence:
        return url
    return f"{url}#:~:text={quote(evidence)}"
