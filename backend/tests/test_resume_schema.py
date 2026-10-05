from app.schemas.resume import GeneratedResume
from app.services.llm import RESUME_JSON_SCHEMA


def test_generated_resume_accepts_missing_optional_sections():
    resume = GeneratedResume.model_validate(
        {
            "name": "Candidate",
            "contact_line": "India | +91 1234567890 | candidate@example.com",
            "headline": "Data Scientist",
            "summary": "Summary",
            "skills": ["Python"],
        }
    )

    assert resume.experience == []
    assert resume.projects == []
    assert resume.education == []


def test_strict_llm_schema_requires_all_resume_sections():
    assert set(RESUME_JSON_SCHEMA["required"]) == set(
        RESUME_JSON_SCHEMA["properties"]
    )
    assert RESUME_JSON_SCHEMA["additionalProperties"] is False
