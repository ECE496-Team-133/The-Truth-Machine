from .openai_client import get_client
from .constants import (
    MODEL_CLAIM_EXTRACTION,
    MODEL_CLAIM_OPTIMIZATION,
    MODEL_WIKI_TARGET,
    PROMPT_EXTRACT_CLAIMS,
    PROMPT_OPTIMIZE_CLAIM,
    PROMPT_WIKI_ARTICLE_NAME,
)
from .models import ExtractedClaims


def extract_claims_from_query(query: str) -> list[str]:
    client = get_client()
    prompt = PROMPT_EXTRACT_CLAIMS.format(query=query)
    try:
        resp = client.responses.create(model=MODEL_CLAIM_EXTRACTION, input=prompt)
        raw = getattr(resp, "output_text", None)
        if not raw:
            return []
        # v2 RootModel: use `.root` to access the underlying list
        return ExtractedClaims.model_validate_json(raw).root
    except Exception as e:
        print(f"[ERROR] extract_claims_from_query failed: {e}")
        return []


def optimize_claim(claim: str) -> str:
    client = get_client()
    prompt = PROMPT_OPTIMIZE_CLAIM.format(claim=claim)
    try:
        resp = client.responses.create(model=MODEL_CLAIM_OPTIMIZATION, input=prompt)
        return getattr(resp, "output_text", None) or ""
    except Exception as e:
        print(f"[ERROR] optimize_claim failed: {e}")
        return claim


def get_query_for_wiki_article(claim: str) -> str:
    client = get_client()
    prompt = PROMPT_WIKI_ARTICLE_NAME.format(claim=claim)
    try:
        resp = client.responses.create(model=MODEL_WIKI_TARGET, input=prompt)
        return getattr(resp, "output_text", None) or ""
    except Exception as e:
        print(f"[ERROR] get_query_for_wiki_article failed: {e}")
        return ""
