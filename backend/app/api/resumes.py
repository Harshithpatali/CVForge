from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import Response
from sqlalchemy.orm import Session
from app.core.db import get_db
from app.core.auth import current_user
from app.models.entities import ResumeArtifact, Application
from app.services.document_renderer import render_pdf, render_docx

router=APIRouter(prefix='/api/v1/resumes',tags=['resumes'])

@router.get('/{resume_id}/download')
def download(resume_id:int,format:str='pdf',u=Depends(current_user),db:Session=Depends(get_db)):
    art=db.get(ResumeArtifact,resume_id); a=db.get(Application,art.application_id) if art else None
    if not art or not a or a.user_id!=u.id: raise HTTPException(404,'Resume not found')
    if format == 'pdf':
        return Response(render_pdf(art.resume_json), media_type='application/pdf', headers={'Content-Disposition': f'attachment; filename=cvforge_resume_{resume_id}.pdf'})
    if format == 'docx':
        return Response(render_docx(art.resume_json), media_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document', headers={'Content-Disposition': f'attachment; filename=cvforge_resume_{resume_id}.docx'})
    raise HTTPException(400,'format must be pdf or docx')
