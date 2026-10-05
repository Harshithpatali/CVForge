from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import FileResponse, RedirectResponse
from sqlalchemy.orm import Session
from app.core.db import get_db
from app.core.auth import current_user
from app.models.entities import ResumeArtifact, Application
from app.services.artifact_storage import ArtifactStorage
router=APIRouter(prefix="/api/v1/resumes",tags=["resumes"])
@router.get("/{resume_id}/download")
def download(resume_id:int,format:str="pdf",u=Depends(current_user),db:Session=Depends(get_db)):
    art=db.get(ResumeArtifact,resume_id); a=db.get(Application,art.application_id) if art else None
    if not art or not a or a.user_id!=u.id: raise HTTPException(404,"Resume not found")
    if format not in {"pdf","docx"}: raise HTTPException(400,"format must be pdf or docx")
    key=art.pdf_path if format=="pdf" else art.docx_path
    if not key: raise HTTPException(404,"Artifact not rendered")
    storage=ArtifactStorage(); url=storage.presigned_url(key)
    if url: return RedirectResponse(url)
    return FileResponse(key,filename=f"tailored_resume_{resume_id}.{format}")
