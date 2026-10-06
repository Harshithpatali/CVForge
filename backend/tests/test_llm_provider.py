from app.core.config import settings
from app.services import llm


def test_generate_resume_uses_groq(monkeypatch):
    monkeypatch.setattr(settings, "groq_api_key", "test-key")
    monkeypatch.setattr(
        llm,
        "_generate_with_groq",
        lambda prompt: {"provider": "groq", "prompt": prompt},
    )

    result = llm.generate_resume("test prompt")

    assert result["provider"] == "groq"


def test_evaluate_ats_uses_gemini(monkeypatch):
    monkeypatch.setattr(settings, "gemini_api_key", "test-key")
    monkeypatch.setattr(
        llm.genai,
        "Client",
        lambda api_key: object(),
    )

    class FakeClient:
        pass

    fake_client = FakeClient()
    fake_client.models = type(
        "Models",
        (),
        {
            "generate_content": lambda self, **kwargs: type(
                "Response",
                (),
                {
                    "text": (
                        '{"score": 84, "keyword_coverage": 80, '
                        '"required_skill_coverage": 90, "title_alignment": 85, '
                        '"responsibility_alignment": 82, "formatting_score": 95, '
                        '"matched_keywords": ["Python"], "missing_keywords": ["Spark"], '
                        '"strengths": ["Strong Python alignment"], '
                        '"gaps": ["Spark missing"], '
                        '"recommendations": ["Add Spark only if evidenced"], '
                        '"warnings": []}'
                    )
                },
            )(),
        },
    )()

    monkeypatch.setattr(llm.genai, "Client", lambda api_key: fake_client)

    result = llm.evaluate_ats(
        {"title": "Data Scientist", "must_have_skills": ["Python"]},
        {"headline": "Data Scientist", "skills": ["Python"]},
    )

    assert result["score"] == 84
    assert result["missing_keywords"] == ["Spark"]


def test_gemini_ats_requires_api_key(monkeypatch):
    monkeypatch.setattr(settings, "gemini_api_key", "")

    try:
        llm.evaluate_ats({}, {})
    except RuntimeError as exc:
        assert "GEMINI_API_KEY" in str(exc)
    else:
        raise AssertionError("Missing Gemini key should raise RuntimeError")
