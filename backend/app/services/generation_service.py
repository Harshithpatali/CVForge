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
from app.schemas.cv import CandidateProfile, JobProfile, Project, ProjectLink
from app.schemas.resume import GeneratedResume, ResumeLink, ResumeProject
from app.services.llm import evaluate_ats, generate_resume
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
    if not value:
        return ""
    if not value.startswith(("http://", "https://")):
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
        github_url = _normalise_url(answers.get(f"project_github_url_{idx}"))
        demo_url = _normalise_url(answers.get(f"project_demo_url_{idx}"))
        legacy_url = _normalise_url(answers.get(f"project_url_{idx}"))

        if name:
            project.name = name

        links = []
        if github_url:
            links.append(ProjectLink(label="GitHub", url=github_url))
        if demo_url:
            links.append(ProjectLink(label="Live Demo", url=demo_url))
        if links:
            project.links = links
        elif legacy_url:
            project.url = legacy_url
            project.links = [ProjectLink(label="Project", url=legacy_url)]

    for idx in (1, 2):
        name = (answers.get(f"additional_project_{idx}_name") or "").strip()
        github_url = _normalise_url(answers.get(f"additional_project_{idx}_github_url"))
        demo_url = _normalise_url(answers.get(f"additional_project_{idx}_demo_url"))

        links = []
        if github_url:
            links.append(ProjectLink(label="GitHub", url=github_url))
        if demo_url:
            links.append(ProjectLink(label="Live Demo", url=demo_url))

        if name and links:
            candidate.projects.append(
                Project(
                    name=name,
                    links=links,
                )
            )


def _apply_github_repository_evidence(candidate: CandidateProfile) -> None:
    existing = {_project_key(project.name): project for project in candidate.projects if project.name}

    for repo in candidate.github_repositories:
        name = str(repo.get("name") or repo.get("full_name") or "").strip()
        if not name:
            continue

        technologies = [str(x) for x in repo.get("technologies", []) if str(x).strip()]
        description = str(repo.get("description") or repo.get("evidence_summary") or "").strip()
        repo_url = _normalise_url(str(repo.get("url") or ""))

        project = existing.get(_project_key(name))
        if project is None:
            project = Project(name=name)
            candidate.projects.append(project)
            existing[_project_key(name)] = project

        if description and not project.description:
            project.description = description
        for technology in technologies:
            if technology not in project.technologies:
                project.technologies.append(technology)

        if repo_url:
            project.links = [
                ProjectLink(label="GitHub", url=repo_url),
                *[link for link in project.links if link.url != repo_url],
            ]


def _contact_line_from_evidence(candidate: CandidateProfile, fallback: str) -> str:
    contact = candidate.contact
    parts: list[str] = []

    for value in (contact.location, contact.phone, contact.email):
        value = (value or "").strip()
        if value and value not in parts:
            parts.append(value)

    return " | ".join(parts) if parts else fallback


def _project_key(name: str) -> str:
    return " ".join((name or "").lower().split())


def _restore_project_links(resume: GeneratedResume, candidate: CandidateProfile) -> None:
    allowed_urls = {
        link.url.strip()
        for project in candidate.projects
        for link in project.links
        if link.url and link.url.strip()
    }
    allowed_urls.update(
        project.url.strip()
        for project in candidate.projects
        if project.url and project.url.strip()
    )

    candidate_by_name = {
        _project_key(project.name): project
        for project in candidate.projects
        if project.links or project.url
    }

    generated_keys = set()

    for project in resume.projects:
        project_links = []
        for link in project.links:
            url = _normalise_url(link.url)
            if url in allowed_urls:
                project_links.append(
                    ResumeLink(label=link.label or "Project", url=url)
                )
        if project.url:
            url = _normalise_url(project.url)
            if url in allowed_urls and not any(x.url == url for x in project_links):
                project_links.append(ResumeLink(label="Project", url=url))

        exact = candidate_by_name.get(_project_key(project.name))
        if exact:
            for link in exact.links:
                if not any(x.url == link.url for x in project_links):
                    project_links.append(
                        ResumeLink(label=link.label, url=link.url)
                    )
            if exact.url and not any(x.url == exact.url for x in project_links):
                project_links.append(
                    ResumeLink(label="Project", url=exact.url)
                )

        project.links = project_links
        project.url = project_links[0].url if project_links else ""
        generated_keys.add(_project_key(project.name))

    for project in candidate.projects:
        if project.name and project.links and _project_key(project.name) not in generated_keys:
            resume.projects.append(
                ResumeProject(
                    name=project.name,
                    url=project.links[0].url,
                    links=[
                        ResumeLink(label=link.label, url=link.url)
                        for link in project.links
                    ],
                )
            )
            generated_keys.add(_project_key(project.name))


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
        _apply_github_repository_evidence(candidate)

        template = select_template(job.role_family, job.seniority, job.domain)

        candidate_payload = candidate.model_dump(exclude={"raw_text"})
        compact_repositories = []
        for repo in candidate_payload.get("github_repositories", [])[:5]:
            compact = dict(repo)
            compact["readme"] = str(repo.get("readme", ""))[:7000]
            compact["important_files"] = list(repo.get("important_files", []))[:20]
            compact["code_samples"] = [
                {
                    "path": sample.get("path", ""),
                    "content": str(sample.get("content", ""))[:2000],
                }
                for sample in repo.get("code_samples", [])[:6]
            ]
            compact_repositories.append(compact)
        candidate_payload["github_repositories"] = compact_repositories

        prompt = build_generation_prompt(
            job.model_dump(),
            candidate_payload,
            answers,
            template,
        )
        prompt_version = _prompt_version(db, template, template.instructions)

        # Step 1: Groq builds the tailored CV.
        raw = generate_resume(prompt)
        resume = GeneratedResume.model_validate(raw)
        resume.contact_line = _contact_line_from_evidence(
            candidate,
            resume.contact_line,
        )
        _restore_project_links(resume, candidate)
        resume.professional_links = [
            ResumeLink(label="LinkedIn", url=candidate.contact.linkedin),
            ResumeLink(label="GitHub", url=candidate.contact.github),
            ResumeLink(label="Portfolio", url=candidate.contact.portfolio),
        ]
        resume.professional_links = [x for x in resume.professional_links if x.url]

        # Step 2: Gemini independently evaluates the generated CV against the JD.
        ats = evaluate_ats(
            job.model_dump(),
            resume.model_dump(),
            candidate.model_dump(exclude={"raw_text"}),
        )

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
