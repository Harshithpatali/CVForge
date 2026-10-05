from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.db import get_db
from app.core.auth import current_user
from app.models.entities import Application, CandidateProfileRecord, GenerationJob
from app.services.document_parser import extract_text, parse_candidate
from app.services.jd_parser import analyze_jd
from app.services.questionnaire import missing_questions
from app.services.generation_service import generate_for_application
from app.schemas.cv import JobProfile, CandidateProfile

router = APIRouter(prefix='/api/v1/jobs', tags=['jobs'])


@router.post('/analyze')
async def analyze(
    jd: str = Form(...),
    cv: UploadFile | None = File(None),
    u=Depends(current_user),
    db: Session = Depends(get_db),
):
    if cv:
        data = await cv.read()
        text = extract_text(data, cv.filename or '')
        candidate = parse_candidate(text, cv.filename or 'txt')
    else:
        candidate = parse_candidate('', 'txt')

    job = analyze_jd(jd)
    questions = missing_questions(candidate, job)

    return {
        'candidate': candidate.model_dump(exclude={'raw_text'}),
        'job': job.model_dump(exclude={'raw_text'}),
        'questions': [x.model_dump() for x in questions],
    }


@router.post('/applications')
def create_application(
    job: JobProfile,
    candidate: CandidateProfile | None = None,
    candidate_profile_id: int | None = None,
    u=Depends(current_user),
    db: Session = Depends(get_db),
):
    if candidate_profile_id and not db.query(CandidateProfileRecord).filter_by(
        id=candidate_profile_id, user_id=u.id
    ).first():
        raise HTTPException(404, 'Profile not found')

    a = Application(
        user_id=u.id,
        candidate_profile_id=candidate_profile_id,
        candidate_json=candidate.model_dump(exclude={'raw_text'}) if candidate else None,
        job_title=job.title,
        company=job.company,
        job_json=job.model_dump(),
        status='draft',
    )
    db.add(a)
    db.commit()
    db.refresh(a)
    return {'id': a.id, 'status': a.status}


@router.post('/applications/{application_id}/generate')
def generate(
    application_id: int,
    answers: dict[str, str] | None = None,
    u=Depends(current_user),
    db: Session = Depends(get_db),
):
    a = db.query(Application).filter_by(id=application_id, user_id=u.id).first()
    if not a:
        raise HTTPException(404, 'Application not found')

    try:
        job, resume = generate_for_application(db, a, answers or {})
        db.commit()
        return {
            'generation_id': job.id,
            'resume_id': resume.id,
            'status': job.status,
            'resume': resume.resume_json,
            'ats': resume.ats_json,
            'template': resume.template_key,
        }
    except Exception as exc:
        db.commit()
        raise HTTPException(502, f'Resume generation failed: {exc}')


@router.post('/enqueue')
def enqueue(
    application_id: int,
    answers: dict[str, str] | None = None,
    u=Depends(current_user),
    db: Session = Depends(get_db),
):
    a = db.query(Application).filter_by(id=application_id, user_id=u.id).first()
    if not a:
        raise HTTPException(404, 'Application not found')

    j = GenerationJob(
        application_id=a.id,
        status='queued',
        input_json={'answers': answers or {}},
    )
    db.add(j)
    a.status = 'queued'
    db.commit()
    db.refresh(j)
    return {'generation_id': j.id, 'status': j.status}


@router.get('/generations/{generation_id}')
def status(
    generation_id: int,
    u=Depends(current_user),
    db: Session = Depends(get_db),
):
    j = db.get(GenerationJob, generation_id)
    a = db.get(Application, j.application_id) if j else None
    if not j or not a or a.user_id != u.id:
        raise HTTPException(404, 'Generation job not found')
    return {
        'id': j.id,
        'status': j.status,
        'error': j.error,
        'application_id': j.application_id,
    }
