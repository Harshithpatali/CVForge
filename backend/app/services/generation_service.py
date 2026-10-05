from datetime import datetime

from sqlalchemy.orm import Session

from app.models.entities import (
    Application,
    CandidateProfileRecord,
    GenerationEvent,
    GenerationJob,
    PromptVersion,
    ResumeArtifact,
)
from app.schemas.cv import CandidateProfile, JobProfile, Project
from app.schemas.resume import GeneratedResume
from app.services.ats_validator import validate
from app.services.llm import generate_resume
from app.services.prompt_engine import build_generation_prompt, select_template


def _prompt_version(db: Session, template, prompt_text: str) -> PromptVersion:
    row = (
        db.query(PromptVersion)
        .filter(
            PromptVersion.prompt_key == template.key,
            PromptVersion.version == template.version,
        )
        .first()
    )
    if row:
        return row

    row = PromptVersion(
        prompt_key=template.key,
        version=template.version,
        prompt_text=prompt_text,
        role_family=template.role_family,
        seniority=template.seniority,
        domain=template.domain,
        active=True,
    )
    db.add(row)
    db.flush()
    return row


def _normalise_url(value: str | None) -> str:
    value = (value or "").strip()
    if value.startswith("www."):
        return f"https://{value}"
    return value


def _apply_link_evidence(candidate: CandidateProfile, answers: dict[str, str]) -> None:
    contact = candidate.contact

    for key, attr in (
        ("linkedin_url", "linkedin"),
        ("portfolio_url", "portfolio"),
        ("github_url", "github"),
    ):
        value = _normalise_url(answers.get(key))
        if value:
            setattr(contact, attr, value)

    for idx, project in enumerate(candidate.projects):
        name = (answers.get(f"project_name_{idx}") or "").strip()
        url = _normalise_url(answers.get(f"project_url_{idx}"))

        if name:
            project.name = name
        if url:
            project.url = url

    for idx in (1, 2):
        name = (answers.get(f"additional_project_{idx}_name") or "").strip()
        url = _normalise_url(answers.get(f"additional_project_{idx}_url"))

        if name and url:
            candidate.projects.append(Project(name=name, url=url))


def _contact_line_from_evidence(candidate: CandidateProfile, fallback: str) -> str:
    contact = candidate.contact
    parts: list[str] = []

    for value in (contact.email, contact.phone, contact.location):
        value = (value or "").strip()
        if value and value not in parts:
            parts.append(value)

    for label, value in (
        ("LinkedIn", contact.linkedin),
        ("Portfolio", contact.portfolio),
        ("GitHub", contact.github),
    ):
        value = (value or "").strip()
        if value:
            parts.append(f"{label}: {value}")

    return " | ".join(parts) if parts else fallback


def _project_key(name: str) -> str:
    return " ".join((name or "").lower().split())


def _restore_project_links(resume: GeneratedResume, candidate: CandidateProfile) -> None:
    candidate_by_name = {
        _project_key(project.name): project.url
        for project in candidate.projects
        if project.url
    }

    for idx, project in enumerate(resume.projects):
        if project.url:
            continue

        exact = candidate_by_name.get(_project_key(project.name))
        if exact:
            project.url = exact
        elif idx < len(candidate.projects) and candidate.projects[idx].url:
            project.url = candidate.projects[idx].url


def _record_failure(
    db: Session,
    application_id: int,
    generation_job: GenerationJob | None,
    answers: dict[str, str],
    exc: Exception,
) -> None:
    error_text = str(exc)[:4000]

    try:
        application = db.get(Application, application_id)
        if application:
            application.status = "failed"

        if generation_job is not None and generation_job.id is not None:
            generation_job.status = "failed"
            generation_job.error = error_text
            generation_job.finished_at = datetime.utcnow()
            db.add(
                GenerationEvent(
                    generation_job_id=generation_job.id,
                    event_type="generation_failed",
                    payload={"error": error_text[:1000]},
                )
            )
            db.flush()
            return
    except Exception:
        db.rollback()

    try:
        application = db.get(Application, application_id)
        if application:
            application.status = "failed"

        failed_job = GenerationJob(
            application_id=application_id,
            status="failed",
            input_json={"answers": answers},
            attempts=1,
            started_at=datetime.utcnow(),
            finished_at=datetime.utcnow(),
            error=error_text,
        )
        db.add(failed_job)
        db.flush()

        db.add(
            GenerationEvent(
                generation_job_id=failed_job.id,
                event_type="generation_failed",
                payload={"error": error_text[:1000]},
            )
        )
        db.flush()
    except Exception:
        db.rollback()


def generate_for_application(
    db: Session,
    application: Application,
    answers: dict[str, str] | None = None,
):
    answers = answers or {}
    generation_job: GenerationJob | None = None

    try:
        generation_job = GenerationJob(
            application_id=application.id,
            status="running",
            input_json={"answers": answers},
            attempts=1,
            started_at=datetime.utcnow(),
        )
        db.add(generation_job)
        db.flush()

        application.status = "generating"

        db.add(
            GenerationEvent(
                generation_job_id=generation_job.id,
                event_type="generation_started",
                payload={},
            )
        )

        job = JobProfile.model_validate(application.job_json)

        if application.candidate_profile_id:
            profile = (
                db.query(CandidateProfileRecord)
                .filter_by(
                    id=application.candidate_profile_id,
                    user_id=application.user_id,
                )
                .first()
            )
            if not profile:
                raise ValueError("Candidate profile not found.")
            candidate = CandidateProfile.model_validate(profile.profile_json)
        else:
            candidate = CandidateProfile.model_validate(
                application.candidate_json or {}
            )

        _apply_link_evidence(candidate, answers)

        template = select_template(job.role_family, job.seniority, job.domain)
        prompt = build_generation_prompt(
            job.model_dump(),
            candidate.model_dump(exclude={"raw_text"}),
            answers,
            template,
        )
        prompt_version = _prompt_version(db, template, template.instructions)

        raw = generate_resume(prompt)
        resume = GeneratedResume.model_validate(raw)
        resume.contact_line = _contact_line_from_evidence(
            candidate,
            resume.contact_line,
        )
        _restore_project_links(resume, candidate)

        ats = validate(resume, job, candidate)

        latest = (
            db.query(ResumeArtifact)
            .filter_by(application_id=application.id)
            .order_by(ResumeArtifact.version.desc())
            .first()
        )
        version = latest.version + 1 if latest else 1

        artifact = ResumeArtifact(
            application_id=application.id,
            version=version,
            resume_json=resume.model_dump(),
            ats_json=ats,
            prompt_version_id=prompt_version.id,
            prompt_key=template.key,
            template_key=template.key,
        )
        db.add(artifact)
        db.flush()

        generation_job.status = "completed"
        generation_job.finished_at = datetime.utcnow()
        application.status = "completed"

        db.add(
            GenerationEvent(
                generation_job_id=generation_job.id,
                event_type="generation_completed",
                payload={
                    "resume_id": artifact.id,
                    "ats_score": ats.get("score"),
                },
            )
        )
        db.flush()

        return generation_job, artifact

    except Exception as exc:
        _record_failure(
            db=db,
            application_id=application.id,
            generation_job=generation_job,
            answers=answers,
            exc=exc,
        )
        raise
