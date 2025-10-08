"""
Local OpenAI-compatible client that replaces OpenAI API calls with local model calls.
This allows the original system to work with local models instead of OpenAI.
"""

import json
import requests
from typing import Optional, Dict, Any


class LocalOpenAIClient:
    """Local OpenAI-compatible client that uses local models."""
    
    def __init__(self, base_url: str = "http://localhost:1234", model: str = "local-model"):
        self.base_url = base_url.rstrip('/')
        self.model = model
    
    def _make_request(self, prompt: str, max_tokens: int = 1000, temperature: float = 0.1) -> Optional[str]:
        """Make a request to the local model."""
        try:
            url = f"{self.base_url}/v1/chat/completions"
            payload = {
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": temperature,
                "max_tokens": max_tokens
            }
            
            response = requests.post(url, json=payload, timeout=60)
            response.raise_for_status()
            
            data = response.json()
            if "choices" in data and len(data["choices"]) > 0:
                return data["choices"][0]["message"]["content"]
        except Exception as e:
            print(f"[ERROR] Local model request failed: {e}")
        
        return None
    
    def extract_claims(self, query: str) -> list[str]:
        """Extract claims from a query using local model."""
        prompt = f"""Strictly extract claims and facts that could be fact-checked from the following query. 
Return the claims as a JSON array of strings. If no claims are present, such as strict questions, 
return an empty array: "{query}"

Respond with only the JSON array, no other text."""
        
        response = self._make_request(prompt, max_tokens=500)
        if not response:
            return []
        
        try:
            # Try to parse JSON from response
            import re
            json_match = re.search(r'\[.*?\]', response)
            if json_match:
                claims = json.loads(json_match.group())
                return claims if isinstance(claims, list) else []
        except Exception:
            pass
        
        return []
    
    def optimize_claim(self, claim: str) -> str:
        """Optimize a claim using local model."""
        prompt = f"""Rewrite the following claim such that the core assertion of the claim can be easily 
fact checked in a relevant article without requiring additional context. 
Return a single optimized claim. Claim: {claim}

Respond with only the optimized claim, no other text."""
        
        response = self._make_request(prompt, max_tokens=200)
        return response if response else claim
    
    def get_wiki_article_name(self, claim: str) -> str:
        """Get Wikipedia article name for a claim using local model."""
        prompt = f'Return the name of the wikipedia article that contains the answer to the claim "{claim}"\n\nRespond with only the article name, no other text.'
        
        response = self._make_request(prompt, max_tokens=100)
        return response if response else claim
    
    def _select_relevant_content(self, claim: str, content: str, max_length: int = 8000) -> str:
        """Select the most relevant content for fact-checking."""
        if len(content) <= max_length:
            return content
        
        # Extract key terms from the claim
        claim_lower = claim.lower()
        key_terms = []
        
        # Look for important terms (dates, names, etc.)
        import re
        dates = re.findall(r'\b\d{4}\b', claim)  # Years like 1943, 1912
        key_terms.extend(dates)
        
        # Extract potential key words (capitalized words, important nouns)
        words = claim.split()
        for word in words:
            if len(word) > 3 and word[0].isupper():  # Capitalized words
                key_terms.append(word.lower())
        
        # Find sections that contain key terms
        content_lower = content.lower()
        relevant_sections = []
        
        # Split content into paragraphs
        paragraphs = content.split('\n\n')
        
        for paragraph in paragraphs:
            paragraph_lower = paragraph.lower()
            relevance_score = 0
            
            # Score based on key terms found
            for term in key_terms:
                if term in paragraph_lower:
                    relevance_score += 1
            
            if relevance_score > 0:
                relevant_sections.append((relevance_score, paragraph))
        
        # Sort by relevance and take the most relevant sections
        relevant_sections.sort(key=lambda x: x[0], reverse=True)
        
        selected_content = ""
        for score, paragraph in relevant_sections:
            if len(selected_content) + len(paragraph) <= max_length:
                selected_content += paragraph + "\n\n"
            else:
                break
        
        # If we still have space, add the beginning of the article
        if len(selected_content) < max_length:
            remaining_space = max_length - len(selected_content)
            beginning = content[:remaining_space]
            selected_content = beginning + "\n\n" + selected_content
        
        return selected_content[:max_length]
    
    def factcheck_claim(self, claim: str, scraped_content: str) -> Optional[Dict[str, Any]]:
        """Fact-check a claim against scraped content using local model."""
        # Smart content selection: find relevant sections instead of just truncating
        truncated_content = self._select_relevant_content(claim, scraped_content)
        
        prompt = f"""Based on the following scraped content from a web page, please analyze the claim and provide:
1. A label of either "True" or "False" based on whether the claim is supported by the content
2. A single contiguous block of text from the article that verifies or disproves the claim

IMPORTANT: The evidence must be a concise, single, unbroken string of text directly copied from the scraped content. 
Do not combine multiple separate sentences or paragraphs. Find the most relevant and concise single block of text that 
directly verifies or disproves the claim.

Return your response in this exact JSON format:
{{"label": "True" or "False", "evidence": "single contiguous block of text from the article"}}

Claim: "{claim}"

Scraped Content:
{truncated_content}"""
        
        response = self._make_request(prompt, max_tokens=1000)
        if not response:
            return None
        
        try:
            # Try to parse JSON from response
            import re
            json_match = re.search(r'\{[^}]*"label"[^}]*"evidence"[^}]*\}', response)
            if json_match:
                return json.loads(json_match.group())
        except Exception:
            pass
        
        # Fallback: try to extract True/False and evidence
        try:
            if "true" in response.lower():
                label = "True"
            elif "false" in response.lower():
                label = "False"
            else:
                label = "False"
            
            # Extract evidence (everything after "evidence":)
            evidence_match = re.search(r'"evidence":\s*"([^"]*)"', response)
            evidence = evidence_match.group(1) if evidence_match else response[:200]
            
            return {"label": label, "evidence": evidence}
        except Exception:
            return {"label": "False", "evidence": response[:200]}


# Global client instance
_local_client: Optional[LocalOpenAIClient] = None


def get_local_openai_client() -> LocalOpenAIClient:
    """Get the global local OpenAI client."""
    global _local_client
    if _local_client is None:
        _local_client = LocalOpenAIClient()
    return _local_client


def set_local_openai_client(client: LocalOpenAIClient):
    """Set the global local OpenAI client."""
    global _local_client
    _local_client = client
