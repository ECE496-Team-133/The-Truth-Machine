from openai import OpenAI

from .local_config import is_local_mode, load_config
from .local_provider import LocalLLMClient

# Cached client instance so we don't re-create on every call
_client = None
_client_mode = None  # tracks which mode the cached client was built for


def get_client():
    """
    Return the appropriate LLM client.

    - If local mode is configured, returns a LocalLLMClient pointed at Ollama.
    - Otherwise, returns the standard OpenAI client.

    The returned object exposes `client.responses.create(model=..., input=...)`
    in both cases, so callers need no changes.
    """
    global _client, _client_mode

    local = is_local_mode()
    mode = "local" if local else "api"

    if _client is not None and _client_mode == mode:
        return _client

    if local:
        cfg = load_config()
        _client = LocalLLMClient(
            base_url=cfg.ollama_base_url,
            model=cfg.model_tag,
        )
        _client_mode = mode
        return _client

    _client = OpenAI()
    _client_mode = mode
    return _client


def reset_client():
    """Force re-creation on next get_client() call (e.g. after config change)."""
    global _client, _client_mode
    _client = None
    _client_mode = None
