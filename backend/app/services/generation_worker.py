import time
from datetime import datetime
from sqlalchemy import select, update
from sqlalchemy.orm import Session
from app.core.db import SessionLocal
from app.core.config import settings
from app.models.entities import GenerationJob, Application, CandidateProfileRecord, ResumeArtifact, PromptVersion, GenerationEvent
from app.services.prompt_registry import select_prompt
from app.services.grok_client import GrokClient
from app.services.ats_validator import validate
from app.services.renderer import render_docx, render_pdf
from app.services.template_registry import select_template
from app.services.artifact_storage import ArtifactStorage

def event(db,jid,typ,payload=None): db.add(GenerationEvent(generation_job_id=jid,event_type=typ,payload=payload)); db.commit()

def claim(db):
    j=db.execute(select(GenerationJob).where(GenerationJob.status=="queued", GenerationJob.attempts < settings.worker_max_attempts).order_by(GenerationJob.created_at).with_for_update(skip_locked=True).limit(1)).scalar_one_or_none()
    if not j:return None
    j.status="running";j.started_at=datetime.utcnow();j.attempts+=1;db.commit();return j

def process(j):
    db=SessionLocal()
    try:
        a=db.get(Application,j.application_id); p=db.get(CandidateProfileRecord,a.candidate_profile_id) if a.candidate_profile_id else None
        candidate=p.profile_json if p else {}
        job=type("Job",(),a.job_json)()
        # Pydantic-like namespace for existing services
        from app.schemas.cv import JobProfile,CandidateProfile
        jp=JobProfile.model_validate(a.job_json); cp=CandidateProfile.model_validate(candidate)
        key,prompt=select_prompt(jp)
        existing=db.query(PromptVersion).filter_by(prompt_key=key,prompt_text=prompt).order_by(PromptVersion.version.desc()).first()
        if existing: pv=existing; version=existing.version
        else:
            latest=db.query(PromptVersion).filter_by(prompt_key=key).order_by(PromptVersion.version.desc()).first(); version=(latest.version+1 if latest else 1); pv=PromptVersion(prompt_key=key,version=version,prompt_text=prompt,role_family=jp.role_family,seniority=jp.seniority,domain=jp.domain,active=True);db.add(pv);db.commit();db.refresh(pv)
        event(db,j.id,"prompt_selected",{"prompt_key":key,"prompt_version":version})
        answers=(j.input_json or {}).get("answers", {})
        resume=GrokClient().generate(prompt,cp.model_dump(),jp.model_dump(),answers)
        ats=validate(resume,jp,cp); template_key,_=select_template(jp.role_family,"auto")
        old=db.query(ResumeArtifact).filter_by(application_id=a.id).order_by(ResumeArtifact.version.desc()).first(); ver=(old.version+1 if old else 1)
        art=ResumeArtifact(job_id=j.id,application_id=a.id,version=ver,resume_json=resume.model_dump(),ats_json=ats,prompt_version_id=pv.id,template_key=template_key);db.add(art);db.commit();db.refresh(art)
        docx=render_docx(art.resume_json,art.id);pdf=render_pdf(art.resume_json,art.id);storage=ArtifactStorage()
        art.docx_path=storage.save(docx,f"{settings.s3_prefix}/resumes/{art.id}/resume.docx");art.pdf_path=storage.save(pdf,f"{settings.s3_prefix}/resumes/{art.id}/resume.pdf")
        j.status="completed";j.finished_at=datetime.utcnow();a.status="completed";db.commit();event(db,j.id,"completed",{"resume_id":art.id,"ats_score":ats["score"]})
    except Exception as e:
        db.rollback();j=db.get(GenerationJob,j.id);j.status="failed";j.error=str(e);j.finished_at=datetime.utcnow();db.commit();event(db,j.id,"failed",{"error":str(e)})
    finally: db.close()

def run_forever():
    while True:
        db=SessionLocal();j=claim(db);db.close()
        if j: process(j)
        else: time.sleep(settings.worker_poll_seconds)
