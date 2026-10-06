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
                        '"warnings": [], "project_suggestions": [{"title": "Streaming Analytics Control Tower", '
                        '"priority": "High", "why_missing": "The JD requires streaming systems.", '
                        '"skills_to_demonstrate": ["Kafka", "Spark Streaming"], '
                        '"project_scope": "Build a small event-driven analytics platform.", '
                        '"plan": ["Ingest events", "Process streams", "Expose a dashboard"], '
                        '"resume_signal": "Demonstrates event-driven data engineering."}]}'
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



def test_evaluate_ats_falls_back_after_transient_503(monkeypatch):
    monkeypatch.setattr(settings, "gemini_api_key", "test-key")
    monkeypatch.setattr(settings, "gemini_model", "gemini-3.8-flash")
    monkeypatch.setattr(
        settings,
        "gemini_fallback_models",
        "gemini-3.6-flash,gemini-3.5-flash-lite",
    )

    class FakeAPIError(Exception):
        def __init__(self, code, message):
            self.code = code
            self.message = message
            super().__init__(message)

    monkeypatch.setattr(llm.errors, "APIError", FakeAPIError)

    class FakeModels:
        calls = []

        def generate_content(self, *, model, contents, config):
            self.calls.append(model)
            if model == "gemini-3.8-flash":
                raise FakeAPIError(503, "high demand")
            return type(
                "Response",
                (),
                {
                    "text": (
                        '{"score": 81, "keyword_coverage": 80, '
                        '"required_skill_coverage": 84, "title_alignment": 82, '
                        '"responsibility_alignment": 79, "formatting_score": 90, '
                        '"matched_keywords": ["Python"], "missing_keywords": ["Spark"], '
                        '"strengths": ["Strong match"], "gaps": ["Spark missing"], '
                        '"recommendations": ["Add Spark only if evidenced"], '
                        '"warnings": []}'
                    )
                },
            )()

    class FakeClient:
        def __init__(self):
            self.models = FakeModels()

    fake_client = FakeClient()
    monkeypatch.setattr(llm, "_gemini_client", lambda: fake_client)

    result = llm.evaluate_ats(
        {"title": "Data Scientist"},
        {"headline": "Data Scientist"},
    )

    assert result["score"] == 81
    assert fake_client.models.calls == ["gemini-3.8-flash", "gemini-3.6-flash"]


def test_evaluate_ats_rejects_non_transient_error(monkeypatch):
    monkeypatch.setattr(settings, "gemini_api_key", "test-key")

    class FakeAPIError(Exception):
        def __init__(self, code, message):
            self.code = code
            self.message = message
            super().__init__(message)

    monkeypatch.setattr(llm.errors, "APIError", FakeAPIError)

    class FakeModels:
        def generate_content(self, *, model, contents, config):
            raise FakeAPIError(400, "bad request")

    class FakeClient:
        def __init__(self):
            self.models = FakeModels()

    monkeypatch.setattr(llm, "_gemini_client", lambda: FakeClient())

    try:
        llm.evaluate_ats({}, {})
    except FakeAPIError as exc:
        assert exc.code == 400
    else:
        raise AssertionError("Non-transient Gemini errors should not be retried")
