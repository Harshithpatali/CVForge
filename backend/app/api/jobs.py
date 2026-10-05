from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.auth import current_user
from app.core.db import get_db
from app.models.entities import Application, CandidateProfileRecord, GenerationJob
from app.schemas.cv import CandidateProfile, JobProfile
from app.services.document_parser import extract_text, parse_candidate
from app.services.generation_service import generate_for_application
from app.services.jd_parser import analyze_jd
from app.services.questionnaire import missing_questions


router = APIRouter(prefix="/api/v1/jobs", tags=["jobs"])


@router.post("/analyze")
async def analyze(
    jd: str = Form(...),
    cv: UploadFile | None = File(None),
    u=Depends(current_user),
    db: Session = Depends(get_db),
):
    if cv:
        data = await cv.read()
        text = extract_text(data, cv.filename or "")
        candidate = parse_candidate(text, cv.filename or "txt")
    else:
        candidate = parse_candidate("", "txt")

    job = analyze_jd(jd)
    questions = missing_questions(candidate, job)

    return {
        "candidate": candidate.model_dump(exclude={"raw_text"}),
        "job": job.model_dump(exclude={"raw_text"}),
        "questions": [x.model_dump() for x in questions],
    }


@router.post("/applications")
def create_application(
    job: JobProfile,
    candidate: CandidateProfile | None = None,
    candidate_profile_id: int | None = None,
    u=Depends(current_user),
    db: Session = Depends(get_db),
):
    if candidate_profile_id and not db.query(CandidateProfileRecord).filter_by(
        id=candidate_profile_id,
        user_id=u.id,
    ).first():
        raise HTTPException(404, "Profile not found")

    application = Application(
        user_id=u.id,
        candidate_profile_id=candidate_profile_id,
        candidate_json=(
            candidate.model_dump(exclude={"raw_text"})
            if candidate
            else None
        ),
        job_title=job.title,
        company=job.company,
        job_json=job.model_dump(),
        status="draft",
    )
    db.add(application)
    db.commit()
    db.refresh(application)
    return {"id": application.id, "status": application.status}


@router.post("/applications/{application_id}/generate")
def generate(
    application_id: int,
    answers: dict[str, str] | None = None,
    u=Depends(current_user),
    db: Session = Depends(get_db),
):
    application = (
        db.query(Application)
        .filter_by(id=application_id, user_id=u.id)
        .first()
    )
    if not application:
        raise HTTPException(404, "Application not found")

    try:
        generation_job, resume = generate_for_application(
            db,
            application,
            answers or {},
        )
        db.commit()
        return {
            "generation_id": generation_job.id,
            "resume_id": resume.id,
            "status": generation_job.status,
            "resume": resume.resume_json,
            "ats": resume.ats_json,
            "template": resume.template_key,
        }
    except Exception as exc:
        # generation_for_application records a failed generation when the
        # transaction remains usable. If the final commit itself fails,
        # rollback cleanly instead of issuing a second commit on an aborted
        # PostgreSQL transaction.
        try:
            db.commit()
        except Exception:
            db.rollback()

        raise HTTPException(
            502,
            f"Resume generation failed: {exc}",
        )


@router.post("/enqueue")
def enqueue(
    application_id: int,
    answers: dict[str, str] | None = None,
    u=Depends(current_user),
    db: Session = Depends(get_db),
):
    application = (
        db.query(Application)
        .filter_by(id=application_id, user_id=u.id)
        .first()
    )
    if not application:
        raise HTTPException(404, "Application not found")

    generation_job = GenerationJob(
        application_id=application.id,
        status="queued",
        input_json={"answers": answers or {}},
    )
    db.add(generation_job)
    application.status = "queued"
    db.commit()
    db.refresh(generation_job)
    return {"generation_id": generation_job.id, "status": generation_job.status}


@router.get("/generations/{generation_id}")
def status(
    generation_id: int,
    u=Depends(current_user),
    db: Session = Depends(get_db),
):
    generation_job = db.get(GenerationJob, generation_id)
    application = (
        db.get(Application, generation_job.application_id)
        if generation_job
        else None
    )
    if (
        not generation_job
        or not application
        or application.user_id != u.id
    ):
        raise HTTPException(404, "Generation job not found")

    return {
        "id": generation_job.id,
        "status": generation_job.status,
        "error": generation_job.error,
        "application_id": generation_job.application_id,
    }
