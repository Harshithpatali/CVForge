from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.db import Base
from app.models.entities import Application, GenerationEvent, GenerationJob, User
from app.services.generation_service import generate_for_application
from app.services.document_renderer import render_pdf


def make_db():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    return Session()


def base_application(db):
    user = User(
        email="test@example.com",
        password_hash="hash",
        name="Test User",
    )
    db.add(user)
    db.flush()

    application = Application(
        user_id=user.id,
        candidate_json={},
        job_title="Data Scientist",
        company="Example",
        job_json={
            "title": "Data Scientist",
            "company": "Example",
            "role_family": "data_science",
            "seniority": "entry",
            "domain": "general",
        },
        status="draft",
    )
    db.add(application)
    db.flush()
    return application


def test_current_model_contains_schema_alignment_fields():
    assert "candidate_json" in Application.__table__.columns
    from app.models.entities import ResumeArtifact

    assert "updated_at" in ResumeArtifact.__table__.columns


def test_generation_failure_is_persisted(monkeypatch):
    db = make_db()
    application = base_application(db)

    def fail_generation(_prompt):
        raise RuntimeError("simulated Groq failure")

    monkeypatch.setattr(
        "app.services.generation_service.generate_resume",
        fail_generation,
    )

    try:
        generate_for_application(db, application, {})
    except RuntimeError as exc:
        assert "simulated Groq failure" in str(exc)
    else:
        raise AssertionError("Generation should have failed")

    db.commit()

    failed_job = (
        db.query(GenerationJob)
        .filter_by(application_id=application.id)
        .order_by(GenerationJob.id.desc())
        .first()
    )
    assert failed_job is not None
    assert failed_job.status == "failed"
    assert "simulated Groq failure" in failed_job.error

    db.refresh(application)
    assert application.status == "failed"

    event = (
        db.query(GenerationEvent)
        .filter_by(
            generation_job_id=failed_job.id,
            event_type="generation_failed",
        )
        .first()
    )
    assert event is not None


def test_pdf_renderer_escapes_resume_text():
    payload = {
        "name": "Test & Candidate",
        "contact_line": "email@example.com",
        "headline": "Data Scientist",
        "summary": "Built an API with <5ms latency & reliable output.\nSecond line.",
        "skills": ["Python", "SQL & Statistics"],
        "experience": [
            {
                "company": "Example",
                "title": "Analyst",
                "dates": "2025-2026",
                "bullets": ["Improved <metric> by 20% & documented the result."],
            }
        ],
    }

    pdf = render_pdf(payload)
    assert pdf.startswith(b"%PDF")
    assert len(pdf) > 1000
