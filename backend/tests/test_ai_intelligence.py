from app.core.config import settings
from app.schemas.cv import Contact, CandidateProfile, Project, ProjectLink


def test_ai_job_analysis_falls_back_without_gemini(monkeypatch):
    from app.services import ai_intelligence

    fallback = ai_intelligence.JobProfile(
        title="Data Scientist",
        role_family="data_science",
        seniority="entry",
        domain="general",
        must_have_skills=["Python"],
    )
    monkeypatch.setattr(settings, "gemini_api_key", "")

    result = ai_intelligence.ai_analyze_job(
        "Data Scientist with Python",
        fallback,
    )

    assert result.title == "Data Scientist"
    assert result.must_have_skills == ["Python"]


def test_ai_candidate_extraction_falls_back_without_gemini(monkeypatch):
    from app.services import ai_intelligence

    fallback = CandidateProfile(
        contact=Contact(
            name="Candidate",
            email="candidate@example.com",
            github="https://github.com/candidate",
        ),
        projects=[
            Project(
                name="Fraud Detection",
                links=[
                    ProjectLink(
                        label="GitHub",
                        url="https://github.com/candidate/fraud",
                    )
                ],
            )
        ],
        raw_text="Candidate\nFraud Detection",
        source_format="pdf",
    )
    monkeypatch.setattr(settings, "gemini_api_key", "")

    result = ai_intelligence.ai_extract_candidate(
        fallback.raw_text,
        "resume.pdf",
        fallback,
    )

    assert result.contact.email == "candidate@example.com"
    assert result.projects[0].links[0].url == "https://github.com/candidate/fraud"
