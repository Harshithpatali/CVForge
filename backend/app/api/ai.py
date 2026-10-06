from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.auth import current_user
from app.core.db import get_db
from app.models.entities import Application, ResumeArtifact
from app.services.optimizer import optimize_resume


router = APIRouter(prefix="/api/v1/ai", tags=["ai"])


class OptimizeRequest(BaseModel):
    target_score: float = Field(default=85.0, ge=60.0, le=95.0)
    max_iterations: int = Field(default=2, ge=1, le=2)


@router.post("/resumes/{resume_id}/optimize")
def optimize(
    resume_id: int,
    payload: OptimizeRequest,
    u=Depends(current_user),
    db: Session = Depends(get_db),
):
    artifact = db.get(ResumeArtifact, resume_id)
    application = db.get(Application, artifact.application_id) if artifact else None

    if not artifact or not application or application.user_id != u.id:
        raise HTTPException(404, "Resume not found")

    try:
        optimized_artifact, meta = optimize_resume(
            db,
            application,
            artifact,
            target_score=payload.target_score,
            max_iterations=payload.max_iterations,
        )
        db.commit()
        db.refresh(optimized_artifact)

        return {
            "resume_id": optimized_artifact.id,
            "version": optimized_artifact.version,
            "resume": optimized_artifact.resume_json,
            "ats": optimized_artifact.ats_json,
            "optimization": meta,
        }
    except Exception as exc:
        db.rollback()
        raise HTTPException(502, f"AI optimization failed: {exc}") from exc
