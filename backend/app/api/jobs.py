from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.db import get_db
from app.core.auth import current_user
from app.models.entities import Application, CandidateProfileRecord, GenerationJob
from app.services.document_parser import extract_text, parse_candidate
from app.services.jd_parser import analyze_jd
from app.services.questionnaire import missing_questions
from app.schemas.cv import JobProfile

router=APIRouter(prefix="/api/v1/jobs",tags=["jobs"])
@router.post("/analyze")
async def analyze(jd:str=Form(...),cv:UploadFile|None=File(None),u=Depends(current_user),db:Session=Depends(get_db)):
    candidate=parse_candidate(extract_text(await cv.read(),cv.filename),cv.filename) if cv else parse_candidate("","txt")
    job=analyze_jd(jd); questions=missing_questions(candidate,job)
    return {"candidate":candidate.model_dump(exclude={"raw_text"}),"job":job.model_dump(exclude={"raw_text"}),"questions":[x.model_dump() for x in questions]}
@router.post("/enqueue")
def enqueue(application_id:int,answers:dict[str,str]|None=None,u=Depends(current_user),db:Session=Depends(get_db)):
    a=db.query(Application).filter_by(id=application_id,user_id=u.id).first()
    if not a: raise HTTPException(404,"Application not found")
    j=GenerationJob(application_id=a.id,status="queued",input_json={"answers":answers or {}}); db.add(j); a.status="generating"; db.commit(); db.refresh(j)
    return {"generation_id":j.id,"status":j.status}
@router.get("/{generation_id}")
def status(generation_id:int,u=Depends(current_user),db:Session=Depends(get_db)):
    j=db.get(GenerationJob,generation_id); a=db.get(Application,j.application_id) if j else None
    if not j or not a or a.user_id!=u.id: raise HTTPException(404,"Generation job not found")
    return {"id":j.id,"status":j.status,"error":j.error,"application_id":j.application_id}
