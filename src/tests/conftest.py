import importlib
import pathlib
import pytest


class StubOpenAIResponse:
    def __init__(self, output_text: str | None):
        self.output_text = output_text


class StubOpenAIClient:
    def __init__(self, output_text: str | None):
        self._output_text = output_text

        class _Responses:
            def __init__(self, parent):
                self._parent = parent

            def create(self, **kwargs):
                return StubOpenAIResponse(self._parent._output_text)

        self.responses = _Responses(self)


@pytest.fixture
def stub_openai_client_factory(monkeypatch):
    def _factory(output_text: str | None):
        from src.utils import openai_client

        monkeypatch.setattr(
            openai_client, "get_client", lambda: StubOpenAIClient(output_text)
        )

    return _factory


@pytest.fixture
def tmp_env(monkeypatch, tmp_path):
    class _Env:
        def __init__(self, tmp_path: pathlib.Path):
            self.root = tmp_path
            self.path = tmp_path / ".env"

        def write(self, mapping: dict[str, str]):
            self.path.write_text(
                "\n".join(f"{k}={v}" for k, v in mapping.items()), encoding="utf-8"
            )

        def reload(self):
            import src.utils.config as cfg

            monkeypatch.setattr(cfg, "ENV_PATH", self.path, raising=True)
            importlib.reload(cfg)

    return _Env(tmp_path)
