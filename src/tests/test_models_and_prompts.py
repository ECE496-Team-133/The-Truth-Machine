def test_rootmodel_parsing():
    from src.utils.models import ExtractedClaims

    raw = '["A", "B"]'
    parsed = ExtractedClaims.model_validate_json(raw)
    assert parsed.root == ["A", "B"]


def test_prompt_factcheck_safe():
    from src.utils.constants import PROMPT_FACTCHECK

    s = PROMPT_FACTCHECK.format(claim="Ada", scraped="Scraped text")
    assert '{"label": "True" or "False"' in s
    assert "Ada" in s
    assert "Scraped text" in s
