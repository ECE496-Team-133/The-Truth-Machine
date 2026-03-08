"""
Local LLM provider that mimics the OpenAI client interface.

Wraps Ollama's OpenAI-compatible API so that existing code using
`client.responses.create(model=..., input=...)` works without modification.
"""

import requests
from typing import Optional


class _ResponseObject:
    """Mimics the OpenAI response object with an `output_text` attribute."""

    def __init__(self, text: Optional[str]):
        self.output_text = text


class _ResponsesNamespace:
    """
    Mimics `client.responses` so that `client.responses.create(...)` works.
    Routes calls to Ollama's OpenAI-compatible chat/completions endpoint.
    """

    def __init__(self, base_url: str, model: str, timeout: int = 120):
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._timeout = timeout

    def create(
        self,
        *,
        model: Optional[str] = None,
        input: str = "",  # noqa: A002 – matches OpenAI kwarg name
        temperature: float = 0.1,
        max_tokens: int = 4096,
        **kwargs,
    ) -> _ResponseObject:
        """
        Drop-in replacement for `openai.Client().responses.create(...)`.

        The `model` argument from existing code is intentionally ignored --
        all calls go to the single locally-installed model.
        """
        url = f"{self._base_url}/v1/chat/completions"
        payload = {
            "model": self._model,
            "messages": [{"role": "user", "content": input}],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        try:
            r = requests.post(url, json=payload, timeout=self._timeout)
            r.raise_for_status()
            data = r.json()
            if "choices" in data and data["choices"]:
                text = data["choices"][0]["message"]["content"]
                return _ResponseObject(text)
        except requests.exceptions.Timeout:
            print(f"[ERROR] Local model request timed out after {self._timeout}s")
        except requests.exceptions.ConnectionError:
            print(
                f"[ERROR] Cannot connect to local model at {self._base_url}. "
                "Is Ollama running? Start it with: ollama serve"
            )
        except Exception as e:
            print(f"[ERROR] Local model request failed: {e}")

        return _ResponseObject(None)


class LocalLLMClient:
    """
    Drop-in replacement for `openai.OpenAI()` that routes all inference
    to a locally-running Ollama instance.

    Usage is identical to the OpenAI client:

        client = LocalLLMClient(base_url="http://localhost:11434", model="llama3.1:8b")
        resp = client.responses.create(model="gpt-5-nano", input="Hello")
        print(resp.output_text)
    """

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "llama3.1:8b",
        timeout: int = 120,
    ):
        self.base_url = base_url
        self.model = model
        self.responses = _ResponsesNamespace(base_url, model, timeout)

    def __repr__(self):
        return f"LocalLLMClient(base_url={self.base_url!r}, model={self.model!r})"
