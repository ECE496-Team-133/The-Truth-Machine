# -------------------------
# String constants & prompts
# -------------------------

MODEL_CLAIM_EXTRACTION = "gpt-5-nano"
MODEL_CLAIM_OPTIMIZATION = "gpt-5-mini"
MODEL_FACTCHECK = "gpt-5-nano"
MODEL_WIKI_TARGET = "gpt-5-nano"
MODEL_NEWS_QUERY = "gpt-5-nano"
MODEL_PREREQUISITE = "gpt-5-nano"
MODEL_CLARIFYING_QUESTION = "gpt-5-nano"
MODEL_EXTRACT_ANSWER = "gpt-5-nano"
MODEL_GENERATE_FINAL_CLAIM = "gpt-5-nano"
MODEL_PLAN = "gpt-5-nano"

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

PROMPT_WIKI_ARTICLE_NAME = (
    'Return the name of the wikipedia article that contains the answer to the claim/question. '
    'If context is provided, use it to resolve any references (e.g., "the actor" should be replaced with the actual name from context). '
    'Return only the article name, nothing else.\n\n'
    'Claim/Question: "{claim}"'
)

PROMPT_NEWS_QUERY = (
    'Convert the following claim into a concise news search query with key terms that would appear in news articles. '
    'Extract the main entities, topics, and keywords. Use common news terminology and abbreviations where appropriate. '
    'Return only the search query, nothing else.\n\n'
    'Examples:\n'
    '- "The United Kingdom is a member of the European Union" → "United Kingdom EU membership Brexit"\n'
    '- "The actor who played Gus in Better Call Saul is American" → "Gus Better Call Saul actor nationality"\n'
    '- "Oman is located in Africa" → "Oman location Africa"\n\n'
    'Claim: "{claim}"'
)


PROMPT_FACTCHECK = (
    "Based on the following scraped content from a web page, please analyze the claim and provide:\n"
    '1. A label of either "True" or "False" based on whether the claim is supported by the content\n'
    "2. A clear, complete sentence or paragraph from the article that verifies or disproves the claim\n\n"
    "IMPORTANT: The evidence should be a meaningful, complete sentence or sentences that directly address the claim. "
    "It should be clear enough for a reader to understand why the claim is true or false. "
    "Extract a single contiguous block of text from the scraped content that provides proper context and evidence. "
    "The evidence should be informative and self-contained, not just a few words.\n\n"
    "Return your response in this exact JSON format:\n"
    '{{"label": "True" or "False", "evidence": "complete sentence or paragraph from the article"}}\n\n'
    'Claim: "{claim}"\n\n'
    "Scraped Content:\n"
    "{scraped}"
)

PROMPT_PLAN = (
    "Given the following query, create a simple plan to fact-check it using Wikipedia. "
    "Keep it minimal - only include what's absolutely necessary.\n\n"
    "CRITICAL: Do NOT use any external knowledge or information you already know. "
    "You must ONLY work with what is explicitly stated in the query itself. "
    "Do NOT resolve any references or fill in any names - that will be done by extracting information from Wikipedia articles.\n\n"
    "Break down the query into:\n"
    "1. Prerequisites: Basic facts mentioned in the query that must be verified first. "
    "   These should ONLY validate what's explicitly stated in the query, not add new information. "
    "   Example: For 'The actor playing Gus in Better Call Saul is American', prerequisites would be "
    "   'There is a character named Gus in Better Call Saul' and 'An actor plays the character Gus in Better Call Saul'.\n"
    "2. Additional info needed: ONLY information needed to RESOLVE VAGUE REFERENCES in the query. "
    "   This is ONLY used when the query contains vague references (like 'the actor', 'the president', 'the company', 'that person', 'he', 'she', 'it') "
    "   that need to be replaced with actual names. "
    "   If the query already contains explicit names, places, or entities (like 'Oman', 'Africa', 'Giancarlo Esposito', 'Breaking Bad', 'Canada', 'United States'), "
    "   then NO additional info is needed - return an empty array []. "
    "   Do NOT create additional info items for entities that are already explicitly named in the query. "
    "   Do NOT include the actual claim being verified here. "
    "   Example: For 'The actor playing Gus in Better Call Saul is American', the additional info would be "
    "   only the actor's name (to resolve 'the actor'), NOT their nationality (the nationality IS the claim being verified). "
    "   Example: For 'Is Oman in Africa?', NO additional info is needed because both 'Oman' and 'Africa' are already explicit place names - return []. "
    "   Example: For 'Was the actor who played Gus Fring born in Canada?', additional info would be needed to resolve 'the actor' - return one item. "
    "   Example: For 'Was Giancarlo Esposito born in Canada?', NO additional info is needed - return [].\n"
    "3. Final claim template: The actual factual claim that will be fact-checked. "
    "   This should include the assertion from the original query, with PLACEHOLDERS for the resolved references. "
    "   Use placeholders like [Actor name], [The actor], [Actor], etc. - DO NOT fill in actual names or information. "
    "   Example: For 'The actor playing Gus in Better Call Saul is American', the final claim template should be "
    "   '[Actor name] is American' or '[The actor] is American' - NOT 'Giancarlo Esposito is American' (that name must come from Wikipedia).\n\n"
    "IMPORTANT DISTINCTION:\n"
    "- Additional info = resolves references (who/what is being referred to) - extracted from Wikipedia\n"
    "- Final claim template = the actual assertion being verified (the fact that will be checked) - uses PLACEHOLDERS, not actual names\n"
    "- Do NOT put the verification itself (like 'is American') in additional info - that belongs in the final claim template\n"
    "- Do NOT use any names, dates, or specific information you know - use placeholders that will be filled from Wikipedia\n\n"
    "Return your response as JSON with this exact structure:\n"
    '{{\n'
    '  "prerequisites": ["prerequisite 1", "prerequisite 2", ...],\n'
    '  "additional_info_needed": [\n'
    '    {{"question": "simple direct question", "purpose": "brief purpose description"}},\n'
    '    ...\n'
    '  ],\n'
    '  "final_claim_template": "template with PLACEHOLDERS like [Actor name] or [The actor]"\n'
    '}}\n\n'
    "Query: {query}"
)

PROMPT_PREREQUISITE = (
    "Given the following query, generate a prerequisite statement that must be true for the query to be checkable. "
    "The prerequisite should ONLY validate basic facts explicitly mentioned in the query, not add new information. "
    "Return only the prerequisite statement, nothing else.\n\n"
    "Query: {query}"
)

PROMPT_CLARIFYING_QUESTION = (
    "Given the following query and the prerequisite statement that has been validated, "
    "generate a clarifying question that extracts the missing information needed to verify the query. "
    "The question should be answerable from a Wikipedia article. "
    "Return only the clarifying question, nothing else.\n\n"
    "Query: {query}\n"
    "Prerequisite: {prerequisite}"
)

PROMPT_EXTRACT_ANSWER = (
    "Based on the following scraped content from a Wikipedia article, answer the question. "
    "IMPORTANT: You must extract the answer DIRECTLY from the scraped content provided. "
    "Do NOT use any external knowledge or information you already know. "
    "The answer must be found in the scraped content text below.\n\n"
    "Provide a clear, informative response extracted from the article. "
    "If the question asks for a name or specific fact, include relevant context from the article when appropriate. "
    "Return only the answer extracted from the scraped content, nothing else. "
    "If the answer is not found in the scraped content, return 'NOT_FOUND'.\n\n"
    "Question: {question}\n\n"
    "Scraped Content:\n"
    "{scraped}"
)

PROMPT_GENERATE_FINAL_CLAIM = (
    "Given the original query, the extracted information, and the final claim template, "
    "generate the final concise factual claim by replacing placeholders in the template.\n\n"
    "CRITICAL RULES:\n"
    "1. If the template contains placeholders like [Place], [Region], [Actor name], etc., you MUST replace them "
    "   with values from the ORIGINAL QUERY, NOT from extracted_info or your own knowledge.\n"
    "2. If extracted_info is provided, use it to replace placeholders that match the extracted_info keys.\n"
    "3. For any placeholders that don't have a match in extracted_info, replace them with the corresponding "
    "   explicit values from the ORIGINAL QUERY.\n"
    "4. DO NOT use any external knowledge or information you already know. ONLY use values from the query or extracted_info.\n"
    "5. If the template is '[Place] is in [Region]' and the query is 'Oman is in Africa', "
    "   replace [Place] with 'Oman' and [Region] with 'Africa' from the query - return 'Oman is in Africa'.\n"
    "6. DO NOT change or correct the values - use them exactly as they appear in the query.\n\n"
    "Original Query: {query}\n"
    "Template: {template}\n"
    "Extracted Information: {extracted_info}\n\n"
    "Replace placeholders with values from the query or extracted_info. Return only the final claim statement, nothing else.\n\n"
    "Example: Template '[Actor name] is American' with query 'The actor playing Gus is American' and extracted_info 'actor_name: Giancarlo Esposito' "
    "→ return 'Giancarlo Esposito is American' (using extracted_info).\n"
    "Example: Template '[Place] is in [Region]' with query 'Oman is in Africa' and no extracted_info "
    "→ return 'Oman is in Africa' (using values from query)."
)

WIKI_USER_AGENT = (
    "factcheck-wiki-py/0.1 (+https://your-site-or-repo; your-email@example.com)"
)
