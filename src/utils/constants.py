# -------------------------
# String constants & prompts
# -------------------------

MODEL_CLAIM_EXTRACTION = "gpt-5-nano"
MODEL_CLAIM_OPTIMIZATION = "gpt-5-mini"
MODEL_FACTCHECK = "gpt-5-nano"
MODEL_WIKI_TARGET = "gpt-5-nano"

PROMPT_EXTRACT_CLAIMS = (
    "Strictly extract claims and facts that could be fact-checked from the following query. "
    "Return the claims as a JSON array of strings. If no claims are present, such as strict questions, "
    'return an empty array: "{query}"'
)

PROMPT_OPTIMIZE_CLAIM = (
    "Rewrite the following claim such that the core assertion of the claim can be easily "
    "fact checked in a relevant article without requiring addtional context. "
    "Return a single optimized claim. Claim: {claim}"
)

PROMPT_WIKI_ARTICLE_NAME = 'Return the name of the wikipedia article that contains the answer to the claim "{claim}"'


PROMPT_FACTCHECK = (
    "Based on the following scraped content from a web page, please analyze the claim and provide:\n"
    '1. A label of either "True" or "False" based on whether the claim is supported by the content\n'
    "2. A single contiguous block of text from the article that verifies or disproves the claim\n\n"
    "IMPORTANT: The evidence must be a concise, single, unbroken string of text directly copied from the scraped content. "
    "Do not combine multiple separate sentences or paragraphs. Find the most relevant and concise single block of text that "
    "directly verifies or disproves the claim.\n\n"
    "Return your response in this exact JSON format:\n"
    '{{"label": "True" or "False", "evidence": "single contiguous block of text from the article"}}\n\n'
    'Claim: "{claim}"\n\n'
    "Scraped Content:\n"
    "{scraped}"
)

WIKI_USER_AGENT = (
    "factcheck-wiki-py/0.1 (+https://your-site-or-repo; your-email@example.com)"
)
