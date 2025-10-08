"""
Local model version of claims processing that replaces OpenAI calls.
"""

from .local_openai_client import get_local_openai_client


def extract_claims_from_query(query: str) -> list[str]:
    """Extract claims from query using local model."""
    client = get_local_openai_client()
    return client.extract_claims(query)


def optimize_claim(claim: str) -> str:
    """Optimize claim using local model."""
    client = get_local_openai_client()
    return client.optimize_claim(claim)


def get_query_for_wiki_article(claim: str) -> str:
    """Get Wikipedia article query using local model."""
    client = get_local_openai_client()
    return client.get_wiki_article_name(claim)
