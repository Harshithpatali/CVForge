import json

from fastapi import APIRouter, Depends, HTTPException
from google import genai
from google.genai import types
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.auth import current_user
from app.core.db import get_db
from app.models.entities import Application, ResumeArtifact
from app.core.config import settings
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


class CopilotRequest(BaseModel):
    question: str = Field(min_length=3, max_length=2000)


def _copilot_client() -> genai.Client:
    return genai.Client(
        api_key=settings.gemini_api_key,
        http_options=types.HttpOptions(
            retry_options=types.HttpRetryOptions(
                attempts=2,
                initial_delay=0.6,
                max_delay=2.5,
                exp_base=2.0,
                jitter=0.5,
                http_status_codes=[408, 429, 500, 502, 503, 504],
            )
        ),
    )


@router.post("/resumes/{resume_id}/copilot")
def copilot(
    resume_id: int,
    payload: CopilotRequest,
    u=Depends(current_user),
    db: Session = Depends(get_db),
):
    artifact = db.get(ResumeArtifact, resume_id)
    application = db.get(Application, artifact.application_id) if artifact else None

    if not artifact or not application or application.user_id != u.id:
        raise HTTPException(404, "Resume not found")

    if not settings.gemini_api_key:
        raise HTTPException(503, "Gemini is not configured.")

    prompt = f"""
You are CVForge Copilot.

Answer the user's question using ONLY the supplied target job, generated resume,
and ATS evaluation.

Do not invent candidate facts, employers, metrics, skills, credentials, or project history.
You may recommend future actions, future portfolio projects, or truthful rewrites, but label them
as recommendations rather than completed experience.

TARGET JOB:
{json.dumps(application.job_json, ensure_ascii=False)}

CURRENT RESUME:
{json.dumps(artifact.resume_json, ensure_ascii=False)}

ATS / AI REVIEW:
{json.dumps(artifact.ats_json, ensure_ascii=False)}

USER QUESTION:
{payload.question}

Give a concise, practical answer. Use headings and bullet points where helpful.
"""

    try:
        response = _copilot_client().models.generate_content(
            model=settings.gemini_fast_model,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.2,
                max_output_tokens=2200,
            ),
        )
        return {"answer": (response.text or "").strip()}
    except Exception as exc:
        raise HTTPException(
            503,
            "AI Copilot is temporarily unavailable. Please retry shortly.",
        ) from exc
