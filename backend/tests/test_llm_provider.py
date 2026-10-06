from app.core.config import settings
from app.services import llm


def test_generate_resume_routes_to_groq(monkeypatch):
    monkeypatch.setattr(settings, "llm_provider", "groq")
    monkeypatch.setattr(
        llm,
        "_generate_with_groq",
        lambda prompt: {"provider": "groq", "prompt": prompt},
    )

    result = llm.generate_resume("test prompt")

    assert result["provider"] == "groq"


def test_generate_resume_routes_to_gemini(monkeypatch):
    monkeypatch.setattr(settings, "llm_provider", "gemini")
    monkeypatch.setattr(
        llm,
        "_generate_with_gemini",
        lambda prompt: {"provider": "gemini", "prompt": prompt},
    )

    result = llm.generate_resume("test prompt")

    assert result["provider"] == "gemini"


def test_generate_resume_rejects_unknown_provider(monkeypatch):
    monkeypatch.setattr(settings, "llm_provider", "unknown")

    try:
        llm.generate_resume("test prompt")
    except RuntimeError as exc:
        assert "Unsupported LLM_PROVIDER" in str(exc)
    else:
        raise AssertionError("Unknown provider should raise RuntimeError")
