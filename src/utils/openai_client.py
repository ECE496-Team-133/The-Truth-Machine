from openai import OpenAI


# A thin wrapper so other modules don't import OpenAI directly
def get_client() -> OpenAI:
    # The OpenAI SDK will read OPENAI_API_KEY from env automatically,
    # but we ensure it's present via config.validate_settings() in main.
    return OpenAI()
