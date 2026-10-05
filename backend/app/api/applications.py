from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.core.db import get_db
from app.core.auth import current_user
from app.models.entities import Application, CandidateProfileRecord, GenerationJob, ResumeArtifact
from app.schemas.cv import JobProfile

router=APIRouter(prefix="/api/v1/applications",tags=["applications"])
class CreateApplication(BaseModel): job:JobProfile; candidate_profile_id:int|None=None; answers:dict[str,str]={}; template:str="auto"
@router.post("")
def create(x:CreateApplication,u=Depends(current_user),db:Session=Depends(get_db)):
    if x.candidate_profile_id and not db.query(CandidateProfileRecord).filter_by(id=x.candidate_profile_id,user_id=u.id).first(): raise HTTPException(404,"Profile not found")
    a=Application(user_id=u.id,candidate_profile_id=x.candidate_profile_id,job_title=x.job.title,company=x.job.company,job_json=x.job.model_dump())
    db.add(a);db.commit();db.refresh(a)
    return {"id":a.id,"status":a.status}
@router.get("")
def list_apps(u=Depends(current_user),db:Session=Depends(get_db)):
    rows=db.query(Application).filter_by(user_id=u.id).order_by(Application.updated_at.desc()).all()
    return [{"id":a.id,"job_title":a.job_title,"company":a.company,"status":a.status,"created_at":a.created_at,"updated_at":a.updated_at} for a in rows]
@router.get("/{application_id}")
def get_app(application_id:int,u=Depends(current_user),db:Session=Depends(get_db)):
    a=db.query(Application).filter_by(id=application_id,user_id=u.id).first()
    if not a: raise HTTPException(404,"Application not found")
    jobs=db.query(GenerationJob).filter_by(application_id=a.id).order_by(GenerationJob.created_at.desc()).all()
    resumes=db.query(ResumeArtifact).filter_by(application_id=a.id).order_by(ResumeArtifact.version.desc()).all()
    return {"application":{"id":a.id,"job":a.job_json,"status":a.status},"generations":[{"id":j.id,"status":j.status,"error":j.error} for j in jobs],"resumes":[{"id":r.id,"version":r.version,"resume":r.resume_json,"ats":r.ats_json,"template":r.template_key} for r in resumes]}
