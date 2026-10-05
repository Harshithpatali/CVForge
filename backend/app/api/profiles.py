from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from sqlalchemy.orm import Session
from app.core.db import get_db
from app.core.auth import current_user
from app.models.entities import CandidateProfileRecord
from app.services.document_parser import extract_text, parse_candidate
from app.schemas.cv import CandidateProfile

router=APIRouter(prefix="/api/v1/profiles",tags=["profiles"])
@router.get("")
def list_profiles(u=Depends(current_user),db:Session=Depends(get_db)):
    rows=db.query(CandidateProfileRecord).filter_by(user_id=u.id).order_by(CandidateProfileRecord.updated_at.desc()).all()
    return [{"id":r.id,"name":r.name,"profile":r.profile_json,"is_default":r.is_default,"updated_at":r.updated_at} for r in rows]
@router.post("")
async def create_profile(name:str=Form(...),cv:UploadFile|None=File(None),u=Depends(current_user),db:Session=Depends(get_db)):
    text=extract_text(await cv.read(),cv.filename) if cv else ""
    p=parse_candidate(text,cv.filename if cv else "txt")
    r=CandidateProfileRecord(user_id=u.id,name=name,profile_json=p.model_dump(exclude={"raw_text"}),source_text=text)
    db.add(r);db.commit();db.refresh(r)
    return {"id":r.id,"name":r.name,"profile":r.profile_json}
@router.put("/{profile_id}")
def update_profile(profile_id:int,p:CandidateProfile,u=Depends(current_user),db:Session=Depends(get_db)):
    r=db.query(CandidateProfileRecord).filter_by(id=profile_id,user_id=u.id).first()
    if not r: raise HTTPException(404,"Profile not found")
    r.profile_json=p.model_dump(exclude={"raw_text"}); db.commit(); return {"id":r.id,"profile":r.profile_json}
@router.delete("/{profile_id}")
def delete_profile(profile_id:int,u=Depends(current_user),db:Session=Depends(get_db)):
    r=db.query(CandidateProfileRecord).filter_by(id=profile_id,user_id=u.id).first()
    if not r: raise HTTPException(404,"Profile not found")
    db.delete(r);db.commit();return {"deleted":True}
