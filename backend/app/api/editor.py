from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.auth import current_user
from app.core.db import get_db
from app.models.entities import Application, CandidateProfileRecord, ResumeArtifact
from app.schemas.cv import CandidateProfile, JobProfile
from app.schemas.resume import GeneratedResume
from app.services.llm import evaluate_ats

router = APIRouter(prefix="/api/v1/resumes", tags=["editor"])


class ResumeUpdate(BaseModel):
    resume: dict


@router.get("/{resume_id}")
def get_resume(resume_id: int, u=Depends(current_user), db: Session = Depends(get_db)):
    resume = db.get(ResumeArtifact, resume_id)
    application = db.get(Application, resume.application_id) if resume else None
    if not resume or not application or application.user_id != u.id:
        raise HTTPException(404, "Resume not found")
    return {
        "id": resume.id,
        "version": resume.version,
        "resume": resume.resume_json,
        "ats": resume.ats_json,
        "template": resume.template_key,
    }


@router.put("/{resume_id}")
def update_resume(
    resume_id: int,
    x: ResumeUpdate,
    u=Depends(current_user),
    db: Session = Depends(get_db),
):
    resume_artifact = db.get(ResumeArtifact, resume_id)
    application = (
        db.get(Application, resume_artifact.application_id)
        if resume_artifact
        else None
    )
    if not resume_artifact or not application or application.user_id != u.id:
        raise HTTPException(404, "Resume not found")

    try:
        resume = GeneratedResume.model_validate(x.resume)
        job = JobProfile.model_validate(application.job_json)

        candidate_data = application.candidate_json
        if not candidate_data and application.candidate_profile_id:
            profile = (
                db.query(CandidateProfileRecord)
                .filter_by(
                    id=application.candidate_profile_id,
                    user_id=u.id,
                )
                .first()
            )
            candidate_data = profile.profile_json if profile else {}

        CandidateProfile.model_validate(candidate_data or {})

        ats = evaluate_ats(job.model_dump(), resume.model_dump())

        new_artifact = ResumeArtifact(
            application_id=resume_artifact.application_id,
            version=resume_artifact.version + 1,
            resume_json=resume.model_dump(),
            ats_json=ats,
            prompt_version_id=resume_artifact.prompt_version_id,
            prompt_key=resume_artifact.prompt_key,
            template_key=resume_artifact.template_key,
        )
        db.add(new_artifact)
        db.commit()
        db.refresh(new_artifact)

        return {
            "id": new_artifact.id,
            "version": new_artifact.version,
            "resume": new_artifact.resume_json,
            "ats": new_artifact.ats_json,
        }
    except HTTPException:
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            502,
            f"Resume revision evaluation failed: {exc}",
        ) from exc
