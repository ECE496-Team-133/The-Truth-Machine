def test_get_first_n_results_urls(monkeypatch):
    from src.utils import google_custom_search as gcs

    def fake_get(url, params=None, timeout=None):
        class Resp:
            def json(self):
                return {"items": [{"link": "http://a"}, {"link": "http://b"}]}

            def raise_for_status(self):
                pass

        return Resp()

    monkeypatch.setattr(gcs.requests, "get", fake_get)
    urls = gcs.get_first_n_results_urls("Ada", n=1)
    assert urls == ["http://a"]
