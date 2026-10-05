import re
from app.schemas.resume import GeneratedResume
from app.schemas.cv import JobProfile, CandidateProfile

def norm(s): return re.sub(r"[^a-z0-9+#.-]+"," ",s.lower()).strip()

def validate(resume: GeneratedResume, job: JobProfile, candidate: CandidateProfile):
    text=norm(resume.model_dump_json())
    required=set(norm(x) for x in job.must_have_skills)
    covered={x for x in required if x in text}
    keyword_score=len(covered)/len(required) if required else 1.0
    sections=[bool(resume.name),bool(resume.contact_line),bool(resume.summary),bool(resume.skills),bool(resume.experience or resume.projects),bool(resume.education)]
    section_score=sum(sections)/len(sections)
    title_score=1.0 if norm(job.title) and any(tok in norm(resume.headline) for tok in norm(job.title).split() if len(tok)>2) else 0.5
    warnings=[]
    if len(resume.summary.split())>100: warnings.append("Summary is longer than recommended.")
    if len(resume.skills)>35: warnings.append("Skills section is too large; remove low-relevance skills.")
    if not resume.experience and not resume.projects: warnings.append("No experience or projects section has evidence.")
    score=round(100*(0.55*keyword_score+0.30*section_score+0.15*title_score),1)
    return {"score":score,"keyword_coverage":round(keyword_score*100,1),"required_keywords":sorted(required),"covered_keywords":sorted(covered),"section_score":round(section_score*100,1),"warnings":warnings}
