from .openai_client import get_client
from .constants import (
    MODEL_CLAIM_EXTRACTION,
    MODEL_CLAIM_OPTIMIZATION,
    MODEL_WIKI_TARGET,
    MODEL_NEWS_QUERY,
    MODEL_PREREQUISITE,
    MODEL_CLARIFYING_QUESTION,
    MODEL_EXTRACT_ANSWER,
    MODEL_GENERATE_FINAL_CLAIM,
    MODEL_PLAN,
    PROMPT_EXTRACT_CLAIMS,
    PROMPT_OPTIMIZE_CLAIM,
    PROMPT_WIKI_ARTICLE_NAME,
    PROMPT_NEWS_QUERY,
    PROMPT_PREREQUISITE,
    PROMPT_CLARIFYING_QUESTION,
    PROMPT_EXTRACT_ANSWER,
    PROMPT_GENERATE_FINAL_CLAIM,
    PROMPT_PLAN,
)
from .models import ExtractedClaims, FactCheckPlan


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


def get_query_for_news(claim: str) -> str:
    """Convert a claim into an optimized search query for news sources."""
    client = get_client()
    prompt = PROMPT_NEWS_QUERY.format(claim=claim)
    try:
        resp = client.responses.create(model=MODEL_NEWS_QUERY, input=prompt)
        optimized = getattr(resp, "output_text", None)
        if optimized and optimized.strip():
            # Clean up the response (remove quotes, extra whitespace)
            optimized = optimized.strip().strip('"').strip("'")
            print(f"[DEBUG] News query optimization: '{claim}' → '{optimized}'")
            return optimized
        else:
            print(f"[WARNING] News query optimization returned empty, using original claim")
            return claim
    except Exception as e:
        print(f"[ERROR] get_query_for_news failed: {e}")
        # Fallback: extract key terms from claim
        import re
        # Remove common words and extract key terms
        words = re.findall(r'\b[A-Z][a-z]+\b|\b[A-Z]{2,}\b', claim)
        if words:
            fallback = ' '.join(words[:5])  # Take first 5 capitalized words/abbreviations
            print(f"[INFO] Using fallback news query: '{fallback}'")
            return fallback
        return claim


def generate_prerequisite(query: str) -> str:
    """Generate a prerequisite statement that must be validated before checking the query."""
    client = get_client()
    prompt = PROMPT_PREREQUISITE.format(query=query)
    try:
        resp = client.responses.create(model=MODEL_PREREQUISITE, input=prompt)
        return getattr(resp, "output_text", None) or ""
    except Exception as e:
        print(f"[ERROR] generate_prerequisite failed: {e}")
        return ""


def generate_clarifying_question(query: str, prerequisite: str) -> str:
    """Generate a clarifying question to extract missing information."""
    client = get_client()
    prompt = PROMPT_CLARIFYING_QUESTION.format(query=query, prerequisite=prerequisite)
    try:
        resp = client.responses.create(model=MODEL_CLARIFYING_QUESTION, input=prompt)
        return getattr(resp, "output_text", None) or ""
    except Exception as e:
        print(f"[ERROR] generate_clarifying_question failed: {e}")
        return ""


def extract_answer_from_article(question: str, scraped_content: str) -> str:
    """Extract an answer from scraped article content based on a question."""
    client = get_client()
    prompt = PROMPT_EXTRACT_ANSWER.format(question=question, scraped=scraped_content)
    try:
        resp = client.responses.create(model=MODEL_EXTRACT_ANSWER, input=prompt)
        answer = getattr(resp, "output_text", None) or ""
        return answer.strip()
    except Exception as e:
        print(f"[ERROR] extract_answer_from_article failed: {e}")
        return "NOT_FOUND"


def generate_plan(query: str) -> FactCheckPlan:
    """Generate a fact-checking plan for the query."""
    client = get_client()
    prompt = PROMPT_PLAN.format(query=query)
    try:
        resp = client.responses.create(model=MODEL_PLAN, input=prompt)
        raw = getattr(resp, "output_text", None)
        if not raw:
            # Return empty plan if generation fails
            return FactCheckPlan(prerequisites=[], additional_info_needed=[], final_claim_template="")
        try:
            return FactCheckPlan.model_validate_json(raw)
        except Exception as e:
            print(f"[ERROR] Failed to parse plan JSON: {e}")
            print(f"Raw response: {raw}")
            return FactCheckPlan(prerequisites=[], additional_info_needed=[], final_claim_template="")
    except Exception as e:
        print(f"[ERROR] generate_plan failed: {e}")
        return FactCheckPlan(prerequisites=[], additional_info_needed=[], final_claim_template="")


def generate_final_claim(query: str, template: str, extracted_info: dict) -> str:
    """Generate a final claim from the query, template, and extracted information."""
    # If no placeholders need replacement and no extracted_info, just return the template
    if not extracted_info and "[" not in template:
        return template
    
    # If we have extracted_info, use it to replace placeholders
    if extracted_info:
        # Use extracted_info to replace placeholders
        result = template
        for key, value in extracted_info.items():
            # Try different placeholder formats
            placeholders = [
                f"[{key}]",
                f"[{key.title()}]",
                f"[{key.replace('_', ' ')}]",
                f"[{key.replace('_', ' ').title()}]",
            ]
            for placeholder in placeholders:
                if placeholder in result:
                    result = result.replace(placeholder, str(value))
        # If we replaced all placeholders, return the result
        if "[" not in result:
            return result.strip()
    
    # If no extracted_info and we have placeholders, try to extract values from query
    # This is a simple fallback that tries to match placeholders to query words
    if not extracted_info and "[" in template:
        # For simple cases like "[Place] is in [Region]", try to extract from query
        # This is a heuristic - if the template structure matches query structure
        import re
        placeholders = re.findall(r'\[([^\]]+)\]', template)
        if len(placeholders) == 2 and template.count("[") == 2:
            # Try to match template structure to query
            # For "[Place] is in [Region]" and "Oman is in Africa"
            # Split query by common separators
            query_words = query.split()
            template_words = template.split()
            
            # Simple heuristic: if template has "[X] is in [Y]" pattern
            # and query has "X is in Y" pattern, extract X and Y from query
            if "is in" in query.lower() and "is in" in template.lower():
                parts = re.split(r'\s+is\s+in\s+', query, flags=re.IGNORECASE)
                if len(parts) == 2:
                    place = parts[0].strip()
                    region = parts[1].strip()
                    result = template.replace(f"[{placeholders[0]}]", place).replace(f"[{placeholders[1]}]", region)
                    if "[" not in result:
                        return result.strip()
    
    # Fallback to LLM if we can't do simple replacement
    client = get_client()
    # Format extracted info as a readable string (or "None" if empty)
    if extracted_info:
        info_str = "\n".join([f"{key}: {value}" for key, value in extracted_info.items()])
    else:
        info_str = "None"
    
    prompt = PROMPT_GENERATE_FINAL_CLAIM.format(query=query, template=template, extracted_info=info_str)
    try:
        resp = client.responses.create(model=MODEL_GENERATE_FINAL_CLAIM, input=prompt)
        result = getattr(resp, "output_text", None) or ""
        # Strip any extra whitespace
        return result.strip()
    except Exception as e:
        print(f"[ERROR] generate_final_claim failed: {e}")
        return ""
