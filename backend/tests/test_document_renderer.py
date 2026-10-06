from io import BytesIO

from pypdf import PdfReader

from app.services.document_renderer import render_pdf


def _sample_resume():
    return {
        "name": "Candidate Name",
        "contact_line": "Mysuru, India | +91 9000000000 | candidate@example.com",
        "headline": "Data Scientist | Machine Learning | Statistical Analysis",
        "summary": "Applied mathematician and data scientist with experience in statistics, machine learning, analytics, and production data workflows.",
        "skill_groups": {
            "Languages": ["Python", "SQL", "R"],
            "Data & ML": ["Pandas", "Scikit-learn", "XGBoost"],
            "Statistics": ["Regression", "Hypothesis Testing"],
            "Analytics": ["Experimentation", "Forecasting"],
            "Databases & Tools": ["PostgreSQL", "Git"],
            "Deployment": ["Docker", "FastAPI"],
            "Visualization": ["Power BI", "Tableau"],
        },
        "professional_links": [],
        "experience": [
            {
                "company": "Example Co",
                "title": "Data Scientist",
                "dates": "2024 - Present",
                "location": "India",
                "bullets": [
                    "Built forecasting models and automated analytics workflows.",
                    "Evaluated models using statistical and machine-learning metrics.",
                ],
            }
        ],
        "projects": [
            {
                "name": "Customer Analytics Platform",
                "bullets": [
                    "Built a reproducible customer analytics pipeline using Python and SQL.",
                    "Developed predictive features and model evaluation workflows.",
                ],
                "technologies": ["Python", "SQL", "XGBoost"],
                "url": "",
                "links": [],
            }
        ],
        "education": [
            {
                "institution": "Example University",
                "degree": "M.Sc.",
                "field": "Applied Mathematics and Computing",
                "dates": "2022 - 2024",
            }
        ],
        "certifications": ["Machine Learning Professional Certificate"],
    }


def _page_count(payload: bytes) -> int:
    return len(PdfReader(BytesIO(payload)).pages)


def test_reference_pdf_is_one_page_for_compact_resume():
    payload = render_pdf(_sample_resume(), page_target=1, style="reference")
    assert _page_count(payload) <= 1


def test_two_page_request_can_expand_short_resume():
    payload = render_pdf(_sample_resume(), page_target=2, style="reference")
    assert 1 <= _page_count(payload) <= 2


def test_compact_style_is_supported():
    payload = render_pdf(_sample_resume(), page_target=1, style="compact")
    assert _page_count(payload) <= 1
