from app.schemas.cv import CandidateProfile, JobProfile, QuestionnaireItem

def missing_questions(candidate: CandidateProfile, job: JobProfile):
    q=[]
    if not candidate.contact.name: q.append(QuestionnaireItem(key="name",question="What is your full name?",reason="Required for the resume header."))
    if not candidate.contact.email: q.append(QuestionnaireItem(key="email",question="What email address should appear on the resume?",reason="Required contact field."))
    if not candidate.education: q.append(QuestionnaireItem(key="education",question="List your highest education: institution, degree, field, dates.",reason="Education is missing."))
    if not candidate.experience and not candidate.projects: q.append(QuestionnaireItem(key="experience_or_projects",question="List your most relevant experience or 2–4 projects with measurable results.",reason="There is no usable evidence section."))
    missing=[s for s in job.must_have_skills if s.lower() not in {x.lower() for x in candidate.skills}]
    for skill in missing[:8]:
        q.append(QuestionnaireItem(key=f"skill_{skill.replace(' ','_')}",question=f"Do you have hands-on experience with {skill}? If yes, where and what did you build/do?",reason="The JD marks this as a relevant requirement; we need evidence before including it."))
    return q
