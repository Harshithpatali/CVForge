from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import Response
from sqlalchemy.orm import Session
from app.core.db import get_db
from app.core.auth import current_user
from app.models.entities import ResumeArtifact, Application
from app.services.document_renderer import render_pdf, render_docx

router=APIRouter(prefix='/api/v1/resumes',tags=['resumes'])

@router.get('/{resume_id}/download')
def download(
    resume_id: int,
    format: str = "pdf",
    pages: int | None = None,
    style: str | None = None,
    u=Depends(current_user),
    db: Session = Depends(get_db),
):
    art=db.get(ResumeArtifact,resume_id); a=db.get(Application,art.application_id) if art else None
    if not art or not a or a.user_id!=u.id: raise HTTPException(404,'Resume not found')
    saved_options = art.resume_json.get("_render_options", {}) if isinstance(art.resume_json, dict) else {}
    page_target = int(pages or saved_options.get("page_target") or 1)
    page_target = 2 if page_target == 2 else 1
    layout_style = (style or saved_options.get("style") or "reference").strip().lower()
    if layout_style not in {"reference", "compact"}:
        layout_style = "reference"

    if format == "pdf":
        payload = render_pdf(
            art.resume_json,
            page_target=page_target,
            style=layout_style,
        )
        return Response(
            payload,
            media_type="application/pdf",
            headers={
                "Content-Disposition": (
                    f"attachment; filename=cvforge_resume_{resume_id}_"
                    f"{page_target}p.pdf"
                )
            },
        )

    if format == "docx":
        payload = render_docx(
            art.resume_json,
            page_target=page_target,
            style=layout_style,
        )
        return Response(
            payload,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={
                "Content-Disposition": (
                    f"attachment; filename=cvforge_resume_{resume_id}_"
                    f"{page_target}p.docx"
                )
            },
        )
    raise HTTPException(400,'format must be pdf or docx')
