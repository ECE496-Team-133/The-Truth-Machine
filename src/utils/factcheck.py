from typing import Optional
from urllib.parse import quote
from .openai_client import get_client
from .constants import MODEL_FACTCHECK, PROMPT_FACTCHECK
from .models import ClaimResult


def find_answer_in_article(scraped_content: str, claim: str) -> Optional[ClaimResult]:
    client = get_client()
    prompt = PROMPT_FACTCHECK.format(claim=claim, scraped=scraped_content)
    try:
        resp = client.responses.create(model=MODEL_FACTCHECK, input=prompt)
        text = getattr(resp, "output_text", None)
        if not text:
            return None
        try:
            return ClaimResult.model_validate_json(text)
        except Exception:
            # fallback: wrap raw text in evidence, mark label False
            return ClaimResult(label="False", evidence=text)
    except Exception as e:
        print(f"[ERROR] find_answer_in_article failed: {e}")
        return None


def build_text_fragment_link(url: str, evidence: Optional[str]) -> str:
    if not evidence:
        return url
    return f"{url}#:~:text={quote(evidence)}"
