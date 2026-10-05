from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.core.db import get_db
from app.core.auth import current_user
from app.models.entities import Application, CandidateProfileRecord, ResumeArtifact
from app.schemas.resume import GeneratedResume
from app.schemas.cv import CandidateProfile, JobProfile
from app.services.ats_validator import validate

router=APIRouter(prefix='/api/v1/resumes',tags=['editor'])
class ResumeUpdate(BaseModel): resume:dict

@router.get('/{resume_id}')
def get_resume(resume_id:int,u=Depends(current_user),db:Session=Depends(get_db)):
    r=db.get(ResumeArtifact,resume_id); a=db.get(Application,r.application_id) if r else None
    if not r or not a or a.user_id!=u.id: raise HTTPException(404,'Resume not found')
    return {'id':r.id,'version':r.version,'resume':r.resume_json,'ats':r.ats_json,'template':r.template_key}

@router.put('/{resume_id}')
def update_resume(resume_id:int,x:ResumeUpdate,u=Depends(current_user),db:Session=Depends(get_db)):
    r=db.get(ResumeArtifact,resume_id); a=db.get(Application,r.application_id) if r else None
    if not r or not a or a.user_id!=u.id: raise HTTPException(404,'Resume not found')
    resume=GeneratedResume.model_validate(x.resume)
    job=JobProfile.model_validate(a.job_json)
    candidate_data=a.candidate_json
    if not candidate_data and a.candidate_profile_id:
        profile=db.query(CandidateProfileRecord).filter_by(id=a.candidate_profile_id,user_id=u.id).first()
        candidate_data=profile.profile_json if profile else {}
    candidate=CandidateProfile.model_validate(candidate_data or {})
    ats=validate(resume,job,candidate)
    new=ResumeArtifact(application_id=r.application_id,version=r.version+1,resume_json=resume.model_dump(),ats_json=ats,prompt_version_id=r.prompt_version_id,template_key=r.template_key)
    db.add(new);db.commit();db.refresh(new)
    return {'id':new.id,'version':new.version,'resume':new.resume_json,'ats':new.ats_json}
