from datetime import datetime
from sqlalchemy.orm import Session
from app.models.entities import Application, CandidateProfileRecord, GenerationJob, PromptVersion, ResumeArtifact, GenerationEvent
from app.schemas.cv import CandidateProfile, JobProfile
from app.schemas.resume import GeneratedResume
from app.services.ats_validator import validate
from app.services.llm import generate_resume
from app.services.prompt_engine import select_template, build_generation_prompt

def _prompt_version(db: Session, template, prompt_text: str) -> PromptVersion:
    row = db.query(PromptVersion).filter(PromptVersion.prompt_key == template.key, PromptVersion.version == template.version).first()
    if row:
        return row
    row = PromptVersion(prompt_key=template.key, version=template.version, prompt_text=prompt_text, role_family=template.role_family, seniority=template.seniority, domain=template.domain, active=True)
    db.add(row)
    db.flush()
    return row

def generate_for_application(db: Session, application: Application, answers: dict[str, str] | None = None):
    answers = answers or {}
    job = JobProfile.model_validate(application.job_json)
    if application.candidate_profile_id:
        profile = db.query(CandidateProfileRecord).filter_by(id=application.candidate_profile_id, user_id=application.user_id).first()
        if not profile:
            raise ValueError('Candidate profile not found.')
        candidate = CandidateProfile.model_validate(profile.profile_json)
    else:
        candidate = CandidateProfile.model_validate(application.candidate_json or {})

    gen = GenerationJob(application_id=application.id, status='running', input_json={'answers': answers}, attempts=1, started_at=datetime.utcnow())
    db.add(gen)
    db.flush()
    db.add(GenerationEvent(generation_job_id=gen.id, event_type='generation_started', payload={}))
    template = select_template(job.role_family, job.seniority, job.domain)
    prompt = build_generation_prompt(job.model_dump(), candidate.model_dump(exclude={'raw_text'}), answers, template)
    pv = _prompt_version(db, template, template.instructions)
    try:
        raw = generate_resume(prompt)
        resume = GeneratedResume.model_validate(raw)
        ats = validate(resume, job, candidate)
        latest = db.query(ResumeArtifact).filter_by(application_id=application.id).order_by(ResumeArtifact.version.desc()).first()
        version = latest.version + 1 if latest else 1
        artifact = ResumeArtifact(application_id=application.id, version=version, resume_json=resume.model_dump(), ats_json=ats, prompt_version_id=pv.id, template_key=template.key)
        db.add(artifact)
        gen.status = 'completed'
        gen.finished_at = datetime.utcnow()
        application.status = 'completed'
        db.add(GenerationEvent(generation_job_id=gen.id, event_type='generation_completed', payload={'resume_id': artifact.id, 'ats_score': ats.get('score')}))
        db.flush()
        return gen, artifact
    except Exception as exc:
        gen.status = 'failed'
        gen.error = str(exc)
        gen.finished_at = datetime.utcnow()
        application.status = 'failed'
        db.add(GenerationEvent(generation_job_id=gen.id, event_type='generation_failed', payload={'error': str(exc)[:1000]}))
        db.flush()
        raise
