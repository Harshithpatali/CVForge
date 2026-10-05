import copy
import re

import streamlit as st
from api_client import API_URL, APIError, auth, get, post, put, request

st.set_page_config(page_title='CVForge', page_icon='📄', layout='wide')

st.markdown('''
<style>
.block-container{max-width:1200px;padding-top:2rem}
.cv-card{padding:1.2rem 1.4rem;border:1px solid #e5e7eb;border-radius:14px;background:#fff;margin-bottom:1rem}
.badge{display:inline-block;padding:.3rem .6rem;border-radius:999px;background:#f1f5f9;margin-right:.4rem;font-size:.85rem}
.metric{font-size:2rem;font-weight:700}
.small{color:#64748b;font-size:.9rem}
</style>
''', unsafe_allow_html=True)

if 'token' not in st.session_state: st.session_state.token=None
if 'user' not in st.session_state: st.session_state.user=None
if 'analysis' not in st.session_state: st.session_state.analysis=None
if 'application' not in st.session_state: st.session_state.application=None
if 'resume' not in st.session_state: st.session_state.resume=None


def logout():
    st.session_state.token=None; st.session_state.user=None; st.session_state.analysis=None; st.session_state.application=None; st.session_state.resume=None


def login_screen():
    st.title('CVForge')
    st.caption('Production-grade, evidence-first resume tailoring')
    tab1,tab2=st.tabs(['Sign in','Create account'])
    with tab1:
        email=st.text_input('Email',key='login_email')
        password=st.text_input('Password',type='password',key='login_password')
        if st.button('Sign in',type='primary',use_container_width=True):
            try:
                data=auth('/api/v1/auth/login',{'email':email,'password':password})
                st.session_state.token=data['token']; st.session_state.user=data['user']; st.rerun()
            except APIError as e: st.error(str(e))
    with tab2:
        name=st.text_input('Name',key='reg_name')
        email=st.text_input('Email',key='reg_email')
        password=st.text_input('Password (8+ characters)',type='password',key='reg_password')
        if st.button('Create account',type='primary',use_container_width=True):
            try:
                data=auth('/api/v1/auth/register',{'name':name,'email':email,'password':password})
                st.session_state.token=data['token']; st.session_state.user=data['user']; st.rerun()
            except APIError as e: st.error(str(e))


def profile_dict_from_analysis(candidate):
    return candidate




def _normalise_url(value: str) -> str:
    value = (value or "").strip()
    if value and value.startswith("www."):
        return "https://" + value
    return value


def _md_linkify(text: str) -> str:
    def repl(match):
        url = match.group(0).rstrip(".,;)")
        return f"[{url}]({url})"

    return re.sub(r"https?://[^\s|]+", repl, text or "")


def collect_link_evidence(candidate: dict) -> dict:
    contact = candidate.get("contact") or {}
    projects = candidate.get("projects") or []
    answers = {}

    st.subheader("Links & project proof")
    st.caption(
        "Only provide links you actually own or can show as evidence. "
        "CVForge will preserve them and make them clickable in PDF/DOCX exports."
    )

    with st.expander("Professional links", expanded=True):
        c1, c2, c3 = st.columns(3)
        linkedin = c1.text_input(
            "LinkedIn URL",
            value=contact.get("linkedin", ""),
            placeholder="https://linkedin.com/in/your-profile",
            key="link_linkedin",
        )
        portfolio = c2.text_input(
            "Portfolio URL",
            value=contact.get("portfolio", ""),
            placeholder="https://yourportfolio.com",
            key="link_portfolio",
        )
        github = c3.text_input(
            "GitHub URL",
            value=contact.get("github", ""),
            placeholder="https://github.com/username",
            key="link_github",
        )

        if linkedin.strip():
            answers["linkedin_url"] = _normalise_url(linkedin)
        if portfolio.strip():
            answers["portfolio_url"] = _normalise_url(portfolio)
        if github.strip():
            answers["github_url"] = _normalise_url(github)

    with st.expander("Project links", expanded=True):
        for idx, project in enumerate(projects):
            c1, c2 = st.columns([1, 2])
            name = c1.text_input(
                f"Project {idx + 1} name",
                value=project.get("name", "") or f"Project {idx + 1}",
                key=f"project_name_{idx}",
            )
            url = c2.text_input(
                "Project / demo / GitHub link",
                value=project.get("url", ""),
                placeholder="https://github.com/... or live demo URL",
                key=f"project_url_{idx}",
            )
            if name.strip():
                answers[f"project_name_{idx}"] = name.strip()
            if url.strip():
                answers[f"project_url_{idx}"] = _normalise_url(url)

        st.markdown("**Additional projects**")
        for idx in (1, 2):
            c1, c2 = st.columns([1, 2])
            name = c1.text_input(
                f"Additional project {idx} name",
                key=f"additional_project_{idx}_name",
                placeholder="Project name",
            )
            url = c2.text_input(
                f"Additional project {idx} link",
                key=f"additional_project_{idx}_url",
                placeholder="https://...",
            )
            if name.strip():
                answers[f"additional_project_{idx}_name"] = name.strip()
            if url.strip():
                answers[f"additional_project_{idx}_url"] = _normalise_url(url)

    st.session_state.link_answers = answers
    return answers


def new_application():
    st.header('New application')
    st.write('Upload your existing CV and paste the target job description. CVForge analyzes both before generation.')
    jd=st.text_area('Job description',height=320,placeholder='Paste the complete job description here...')
    cv=st.file_uploader('Existing CV (optional)',type=['pdf','docx','txt','md'])
    if st.button('Analyze JD + CV',type='primary',disabled=not jd.strip()):
        try:
            files={'cv':(cv.name,cv.getvalue())} if cv else None
            data={'jd':jd}
            st.session_state.analysis=request('POST','/api/v1/jobs/analyze',token=st.session_state.token,data=data,files=files).json()
            st.session_state.application=None; st.session_state.resume=None
        except APIError as e: st.error(str(e))
    a=st.session_state.analysis
    if not a: return
    job=a['job']; candidate=a['candidate']
    st.divider(); st.subheader('Job intelligence')
    c1,c2,c3,c4=st.columns(4)
    c1.metric('Role',job.get('role_family','general').replace('_',' ').title())
    c2.metric('Seniority',job.get('seniority','entry').title())
    c3.metric('Domain',job.get('domain','general').title())
    c4.metric('Required skills',len(job.get('must_have_skills',[])))
    if job.get('must_have_skills'):
        st.write(' '.join(f"`{x}`" for x in job['must_have_skills']))
    with st.expander('Extracted candidate evidence',expanded=True):
        st.json(candidate)
    questions=a.get('questions',[])
    answers={}
    if questions:
        st.subheader('Evidence questions')
        st.caption('Answer only what is true. These answers become additional evidence for generation.')
        for q in questions:
            answers[q['key']]=st.text_area(q['question'],help=q.get('reason',''),key='q_'+q['key'])

    link_answers = collect_link_evidence(candidate)
    answers.update(link_answers)

    if st.button('Create application and generate CV',type='primary'):
        try:
            payload={'job':job,'candidate':candidate}
            created=post('/api/v1/jobs/applications',st.session_state.token,json=payload)
            st.session_state.application=created
            with st.spinner('Groq is tailoring your resume, preserving evidence, and running ATS validation...'):
                result=post(f"/api/v1/jobs/applications/{created['id']}/generate",st.session_state.token,json=answers)
            st.session_state.resume=result
            st.success('Resume generated successfully.')
        except APIError as e: st.error(str(e))
    if st.session_state.resume:
        render_resume(st.session_state.resume)


def render_resume(result):
    resume=result.get('resume',{}); ats=result.get('ats',{})
    st.divider(); st.header('Resume result')
    m1,m2,m3=st.columns(3)
    m1.metric('ATS score',f"{ats.get('score',0):.1f}")
    m2.metric('Keyword coverage',f"{ats.get('keyword_coverage',0):.1f}%")
    m3.metric('Section score',f"{ats.get('section_score',0):.1f}%")
    st.subheader(resume.get('name','Resume'))
    if resume.get('contact_line'):
        st.markdown(_md_linkify(resume.get('contact_line','')))
    st.markdown(f"**{resume.get('headline','')}**")
    if resume.get('summary'): st.write(resume['summary'])
    for title,key in [('Skills','skills'),('Experience','experience'),('Projects','projects'),('Education','education'),('Certifications','certifications')]:
        values=resume.get(key) or []
        if not values: continue
        st.subheader(title)
        if key in {'skills','certifications'}: st.write(', '.join(values))
        elif key=='experience':
            for x in values:
                st.markdown(f"**{x.get('title','')} — {x.get('company','')}**  ")
                st.caption(x.get('dates',''))
                for b in x.get('bullets',[]): st.markdown(f'- {b}')
        elif key=='projects':
            for x in values:
                st.markdown(f"**_{x.get('name','')}_**")
                if x.get('url'):
                    st.markdown(f"[Project link]({_normalise_url(x['url'])})")
                if x.get('technologies'): st.caption(', '.join(x['technologies']))
                for b in x.get('bullets',[]): st.markdown(f'- {b}')
        elif key=='education':
            for x in values: st.markdown(f"**{x.get('degree','')} {x.get('field','')}** — {x.get('institution','')} {x.get('dates','')}")
    if ats.get('warnings'): st.warning('\n'.join(ats['warnings']))
    st.subheader('Edit resume')
    edited=copy.deepcopy(resume)

    edited['contact_line']=st.text_input('Contact line',value=resume.get('contact_line',''))

    edited['headline']=st.text_input('Headline',value=resume.get('headline',''))
    edited['summary']=st.text_area('Summary',value=resume.get('summary',''),height=150)
    edited['skills']=[x.strip() for x in st.text_input('Skills (comma separated)',value=', '.join(resume.get('skills',[]))).split(',') if x.strip()]

    if edited.get('projects'):
        st.caption('Project links')
        for idx,project in enumerate(edited['projects']):
            edited['projects'][idx]['url']=st.text_input(
                f"{project.get('name','Project')} link",
                value=project.get('url',''),
                key=f"edit_project_url_{result.get('resume_id')}_{idx}"
            )

    if st.button('Save new resume revision'):
        rid=result.get('resume_id')
        if rid:
            try:
                saved=put(f'/api/v1/resumes/{rid}',st.session_state.token,json={'resume':edited})
                st.session_state.resume={**result,'resume_id':saved['id'],'resume':saved['resume'],'ats':saved['ats']}
                st.success(f"Saved revision v{saved['version']}.")
            except APIError as e: st.error(str(e))
    rid=result.get('resume_id')
    if rid:
        st.subheader('Download')
        b1,b2=st.columns(2)
        for col,fmt,label,mime in [(b1,'pdf','Download PDF','application/pdf'),(b2,'docx','Download DOCX','application/vnd.openxmlformats-officedocument.wordprocessingml.document')]:
            try:
                rr=request('GET',f'/api/v1/resumes/{rid}/download',token=st.session_state.token,params={'format':fmt})
                col.download_button(label,rr.content,file_name=f'cvforge_resume_{rid}.{fmt}',mime=mime,use_container_width=True)
            except APIError as e: col.error(str(e))


def applications():
    st.header('Applications')
    try: rows=get('/api/v1/applications',st.session_state.token)
    except APIError as e: st.error(str(e)); return
    if not rows: st.info('No applications yet. Start a new application.')
    for a in rows:
        with st.container(border=True):
            c1,c2,c3=st.columns([3,2,1])
            c1.markdown(f"**{a['job_title'] or 'Untitled role'}**")
            c1.caption(a.get('company',''))
            c2.write(a.get('status','draft').title())
            if c3.button('Open',key=f"open_{a['id']}"):
                try:
                    detail=get(f"/api/v1/applications/{a['id']}",st.session_state.token)
                    resumes=detail.get('resumes',[])
                    if resumes:
                        r=resumes[0]; st.session_state.resume={'resume_id':r['id'],'resume':r['resume'],'ats':r['ats']}; st.session_state.page='New Application'; st.rerun()
                    else: st.info('No generated resume yet.')
                except APIError as e: st.error(str(e))


def profiles():
    st.header('Candidate profiles')
    st.caption('Save reusable evidence profiles so you do not have to upload the same CV for every application.')
    try: rows=get('/api/v1/profiles',st.session_state.token)
    except APIError as e: st.error(str(e)); return
    for p in rows:
        with st.container(border=True):
            st.markdown(f"**{p['name']}**")
            st.json(p['profile'])
    st.subheader('Save a profile from the current analysis')
    a=st.session_state.analysis
    if a:
        name=st.text_input('Profile name',value='My CV',key='profile_name')
        if st.button('Save current candidate profile'):
            try:
                result=post('/api/v1/profiles/manual',st.session_state.token,params={'name':name},json=a['candidate'])
                st.success(f"Saved profile #{result['id']}")
            except APIError as e: st.error(str(e))
    else: st.info('Analyze a CV first, then save the extracted candidate evidence here.')


def dashboard():
    st.header('Overview')
    try:
        apps=get('/api/v1/applications',st.session_state.token)
        profs=get('/api/v1/profiles',st.session_state.token)
    except APIError as e: st.error(str(e)); return
    c1,c2,c3=st.columns(3)
    c1.metric('Applications',len(apps)); c2.metric('Saved profiles',len(profs)); c3.metric('Completed',sum(x.get('status')=='completed' for x in apps))
    st.markdown('''<div class="cv-card"><h3>Evidence-first workflow</h3><p>CVForge separates job intelligence, candidate evidence, prompt selection, generation, and deterministic ATS validation. Grok rewrites evidence; it does not invent it.</p></div>''',unsafe_allow_html=True)

if not st.session_state.token:
    login_screen(); st.stop()

with st.sidebar:
    st.title('CVForge')
    st.caption(st.session_state.user.get('email',''))
    page=st.radio('Workspace',['Overview','New Application','Applications','Profiles'],index=['Overview','New Application','Applications','Profiles'].index(st.session_state.get('page','Overview')))
    st.session_state.page=page
    if st.button('Sign out'): logout(); st.rerun()

if page=='Overview': dashboard()
elif page=='New Application': new_application()
elif page=='Applications': applications()
elif page=='Profiles': profiles()
