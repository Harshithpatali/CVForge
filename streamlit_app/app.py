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
if 'github_repos' not in st.session_state: st.session_state.github_repos=[]


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
    if not value:
        return ""
    if not value.startswith(("http://", "https://")):
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
            "GitHub profile",
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
        st.caption(
            "For each project, provide a project name plus up to two links. "
            "Typical pair: GitHub + Live Demo."
        )

        for idx, project in enumerate(projects):
            name = st.text_input(
                f"Project {idx + 1} name",
                value=project.get("name", "") or f"Project {idx + 1}",
                key=f"project_name_{idx}",
            )
            project_links = project.get("links") or []
            github_default = next(
                (
                    x.get("url", "")
                    for x in project_links
                    if x.get("label") == "GitHub"
                ),
                "",
            )
            demo_default = next(
                (
                    x.get("url", "")
                    for x in project_links
                    if x.get("label") in {"Live Demo", "Project"}
                ),
                "",
            )

            c1, c2 = st.columns(2)
            github_url = c1.text_input(
                "GitHub",
                value=github_default,
                placeholder="https://github.com/...",
                key=f"project_github_url_{idx}",
            )
            demo_url = c2.text_input(
                "Live Demo / Portfolio",
                value=demo_default,
                placeholder="https://...",
                key=f"project_demo_url_{idx}",
            )

            if name.strip():
                answers[f"project_name_{idx}"] = name.strip()
            if github_url.strip():
                answers[f"project_github_url_{idx}"] = _normalise_url(github_url)
            if demo_url.strip():
                answers[f"project_demo_url_{idx}"] = _normalise_url(demo_url)

        st.markdown("**Additional projects**")
        for idx in (1, 2):
            name = st.text_input(
                f"Additional project {idx} name",
                key=f"additional_project_{idx}_name",
                placeholder="Project name",
            )
            c1, c2 = st.columns(2)
            github_url = c1.text_input(
                "GitHub",
                placeholder="https://github.com/...",
                key=f"additional_project_{idx}_github_url",
            )
            demo_url = c2.text_input(
                "Live Demo / Portfolio",
                placeholder="https://...",
                key=f"additional_project_{idx}_demo_url",
            )
            if name.strip():
                answers[f"additional_project_{idx}_name"] = name.strip()
            if github_url.strip():
                answers[f"additional_project_{idx}_github_url"] = _normalise_url(github_url)
            if demo_url.strip():
                answers[f"additional_project_{idx}_demo_url"] = _normalise_url(demo_url)

    st.session_state.link_answers = answers
    return answers

def _candidate_editor(candidate: dict) -> dict:
    candidate = copy.deepcopy(candidate or {})
    contact = candidate.setdefault("contact", {})
    candidate.setdefault("experience", [])
    candidate.setdefault("education", [])
    candidate.setdefault("projects", [])
    candidate.setdefault("skills", [])
    candidate.setdefault("certifications", [])
    candidate.setdefault("github_repositories", [])

    st.subheader("Build / enhance your CV")
    st.caption(
        "Upload a CV when you have one, then correct or complete the extracted information below. "
        "When no CV is uploaded, fill the same fields from scratch."
    )

    with st.expander("Personal information", expanded=True):
        c1, c2 = st.columns(2)
        contact["name"] = c1.text_input("Full name", value=contact.get("name", ""))
        candidate["headline"] = c2.text_input(
            "Professional headline",
            value=candidate.get("headline", ""),
            placeholder="Data Scientist | Machine Learning | Statistical Analysis",
        )
        c1, c2, c3 = st.columns(3)
        contact["email"] = c1.text_input("Email", value=contact.get("email", ""))
        contact["phone"] = c2.text_input("Phone", value=contact.get("phone", ""))
        contact["location"] = c3.text_input(
            "Location",
            value=contact.get("location", ""),
            placeholder="Karnataka, India",
        )
        c1, c2, c3 = st.columns(3)
        contact["linkedin"] = c1.text_input(
            "LinkedIn",
            value=contact.get("linkedin", ""),
            placeholder="https://linkedin.com/in/...",
        )
        contact["github"] = c2.text_input(
            "GitHub profile",
            value=contact.get("github", ""),
            placeholder="https://github.com/...",
        )
        contact["portfolio"] = c3.text_input(
            "Portfolio",
            value=contact.get("portfolio", ""),
            placeholder="https://...",
        )

    with st.expander("Professional summary", expanded=True):
        candidate["summary"] = st.text_area(
            "Summary",
            value=candidate.get("summary", ""),
            height=130,
        )

    with st.expander("Skills", expanded=True):
        candidate["skills"] = [
            x.strip()
            for x in st.text_area(
                "Skills — one per line or comma separated",
                value="\n".join(candidate.get("skills", [])),
                height=110,
            ).replace(",", "\n").splitlines()
            if x.strip()
        ]

    with st.expander("Professional experience", expanded=True):
        experiences = list(candidate.get("experience") or [])
        while len(experiences) < 3:
            experiences.append({})
        edited_experience = []

        for idx in range(3):
            exp = experiences[idx] or {}
            with st.container(border=True):
                st.markdown(f"**Experience {idx + 1}**")
                c1, c2 = st.columns(2)
                company = c1.text_input(
                    "Company",
                    value=exp.get("company", ""),
                    key=f"exp_company_{idx}",
                )
                title = c2.text_input(
                    "Job title",
                    value=exp.get("title", ""),
                    key=f"exp_title_{idx}",
                )
                c1, c2, c3 = st.columns(3)
                start = c1.text_input(
                    "Start",
                    value=exp.get("start_date", ""),
                    key=f"exp_start_{idx}",
                )
                end = c2.text_input(
                    "End",
                    value=exp.get("end_date", ""),
                    key=f"exp_end_{idx}",
                )
                location = c3.text_input(
                    "Location",
                    value=exp.get("location", ""),
                    key=f"exp_location_{idx}",
                )
                bullets = st.text_area(
                    "Achievements / responsibilities — one per line",
                    value="\n".join(exp.get("bullets", [])),
                    key=f"exp_bullets_{idx}",
                    height=110,
                )
                if company or title or bullets.strip():
                    edited_experience.append({
                        "company": company,
                        "title": title,
                        "location": location,
                        "start_date": start,
                        "end_date": end,
                        "bullets": [x.strip(" -") for x in bullets.splitlines() if x.strip()],
                    })
        candidate["experience"] = edited_experience

    with st.expander("Projects", expanded=True):
        projects = list(candidate.get("projects") or [])
        while len(projects) < 4:
            projects.append({})
        edited_projects = []

        for idx in range(4):
            project = projects[idx] or {}
            with st.container(border=True):
                st.markdown(f"**Project {idx + 1}**")
                name = st.text_input(
                    "Project name",
                    value=project.get("name", ""),
                    key=f"manual_project_name_{idx}",
                )
                technologies = st.text_input(
                    "Technologies",
                    value=", ".join(project.get("technologies", [])),
                    key=f"manual_project_tech_{idx}",
                )
                c1, c2 = st.columns(2)
                github = c1.text_input(
                    "GitHub repository",
                    value=next(
                        (
                            x.get("url", "")
                            for x in project.get("links", [])
                            if x.get("label") == "GitHub"
                        ),
                        "",
                    ),
                    key=f"manual_project_github_{idx}",
                )
                demo = c2.text_input(
                    "Live demo / project link",
                    value=next(
                        (
                            x.get("url", "")
                            for x in project.get("links", [])
                            if x.get("label") in {"Live Demo", "Project"}
                        ),
                        "",
                    ),
                    key=f"manual_project_demo_{idx}",
                )
                bullets = st.text_area(
                    "Project contributions — one per line",
                    value="\n".join(project.get("bullets", [])),
                    key=f"manual_project_bullets_{idx}",
                    height=100,
                )

                if name or bullets.strip() or github.strip() or demo.strip():
                    links = []
                    if github.strip():
                        links.append({"label": "GitHub", "url": _normalise_url(github)})
                    if demo.strip():
                        links.append({"label": "Live Demo", "url": _normalise_url(demo)})
                    edited_projects.append({
                        "name": name,
                        "technologies": [x.strip() for x in technologies.split(",") if x.strip()],
                        "bullets": [x.strip(" -") for x in bullets.splitlines() if x.strip()],
                        "links": links,
                        "url": links[0]["url"] if links else "",
                    })
        candidate["projects"] = edited_projects

    with st.expander("Education", expanded=True):
        educations = list(candidate.get("education") or [])
        while len(educations) < 2:
            educations.append({})
        edited_education = []
        for idx in range(2):
            edu = educations[idx] or {}
            c1, c2 = st.columns(2)
            institution = c1.text_input(
                f"Institution {idx + 1}",
                value=edu.get("institution", ""),
                key=f"edu_inst_{idx}",
            )
            degree = c2.text_input(
                "Degree",
                value=edu.get("degree", ""),
                key=f"edu_degree_{idx}",
            )
            c1, c2, c3 = st.columns(3)
            field = c1.text_input(
                "Field",
                value=edu.get("field", ""),
                key=f"edu_field_{idx}",
            )
            start = c2.text_input(
                "Start",
                value=edu.get("start_date", ""),
                key=f"edu_start_{idx}",
            )
            end = c3.text_input(
                "End",
                value=edu.get("end_date", ""),
                key=f"edu_end_{idx}",
            )
            if institution or degree or field:
                edited_education.append({
                    "institution": institution,
                    "degree": degree,
                    "field": field,
                    "location": edu.get("location", ""),
                    "start_date": start,
                    "end_date": end,
                })
        candidate["education"] = edited_education

    with st.expander("Certifications"):
        candidate["certifications"] = [
            x.strip()
            for x in st.text_area(
                "One certification per line",
                value="\n".join(candidate.get("certifications", [])),
                height=90,
            ).splitlines()
            if x.strip()
        ]

    candidate["github_repositories"] = st.session_state.github_repos
    return candidate


def inspect_github_repositories():
    st.subheader("GitHub project inspection")
    st.caption(
        "Enter public GitHub repository URLs, one per line. CVForge inspects repository metadata, "
        "README, languages, selected project files, and technologies. Private repositories are not accessed."
    )
    raw = st.text_area(
        "Public GitHub repositories",
        value="\n".join(x.get("url", "") for x in st.session_state.github_repos),
        placeholder="https://github.com/owner/project-one\nhttps://github.com/owner/project-two",
        height=100,
        key="github_repo_input",
    )

    if st.button("Inspect public repositories"):
        urls = [x.strip() for x in raw.splitlines() if x.strip()]
        inspected = []
        for url in urls:
            try:
                with st.spinner(f"Inspecting {url}..."):
                    data = post(
                        "/api/v1/github/inspect",
                        st.session_state.token,
                        json={"url": url},
                    )
                inspected.append(data)
                st.success(
                    f"Inspected {data.get('full_name', url)} — "
                    f"{len(data.get('technologies', []))} technologies detected."
                )
            except APIError as exc:
                st.error(f"{url}: {exc}")
        st.session_state.github_repos = inspected

    if st.session_state.github_repos:
        for repo in st.session_state.github_repos:
            with st.container(border=True):
                st.markdown(
                    f"**{repo.get('full_name', repo.get('name', 'Repository'))}**"
                )
                if repo.get("description"):
                    st.write(repo["description"])
                st.caption(
                    " | ".join(
                        x
                        for x in (
                            repo.get("language"),
                            ", ".join(repo.get("technologies", [])),
                            repo.get("default_branch"),
                        )
                        if x
                    )
                )
                if repo.get("readme"):
                    with st.expander("Repository evidence"):
                        st.text(repo["readme"][:4000])

def new_application():
    st.header("CV Enhance")
    st.write(
        "Paste the target JD, optionally upload your existing CV, complete the missing information, "
        "and let CVForge use verified public GitHub project evidence."
    )

    mode = st.radio(
        "CV workflow",
        ["Enhance existing CV", "Build CV from scratch"],
        horizontal=True,
    )

    jd = st.text_area(
        "Target job description",
        height=280,
        placeholder="Paste the complete job description here...",
    )

    cv = st.file_uploader(
        "Upload existing CV (optional)",
        type=["pdf", "docx", "txt", "md"],
        help="Upload your current CV when you have one. You can still edit every extracted field below.",
    )

    c1, c2 = st.columns([1, 1])
    with c1:
        analyze = st.button(
            "Analyze JD + CV",
            type="primary",
            disabled=not jd.strip(),
            use_container_width=True,
        )
    with c2:
        if mode == "Build CV from scratch":
            st.caption("No upload is required. Complete the CV fields after analysis.")

    if analyze:
        try:
            files = {"cv": (cv.name, cv.getvalue())} if cv else None
            data = {"jd": jd}
            result = request(
                "POST",
                "/api/v1/jobs/analyze",
                token=st.session_state.token,
                data=data,
                files=files,
            ).json()
            st.session_state.analysis = result
            st.session_state.application = None
            st.session_state.resume = None
            st.session_state.github_repos = []
        except APIError as exc:
            st.error(str(exc))

    analysis = st.session_state.analysis
    if not analysis:
        return

    job = analysis["job"]
    candidate = _candidate_editor(analysis["candidate"])

    st.divider()
    st.subheader("Job intelligence")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Role", job.get("role_family", "general").replace("_", " ").title())
    c2.metric("Seniority", job.get("seniority", "entry").title())
    c3.metric("Domain", job.get("domain", "general").title())
    c4.metric("Required skills", len(job.get("must_have_skills", [])))

    if job.get("must_have_skills"):
        st.write(" ".join(f"`{x}`" for x in job["must_have_skills"]))

    inspect_github_repositories()

    questions = analysis.get("questions", [])
    answers = {}
    if questions:
        st.subheader("Evidence questions")
        st.caption(
            "Answer only what is true. These answers become additional evidence for generation."
        )
        for q in questions:
            answers[q["key"]] = st.text_area(
                q["question"],
                help=q.get("reason", ""),
                key="q_" + q["key"],
            )

    link_answers = collect_link_evidence(candidate)
    answers.update(link_answers)

    candidate["github_repositories"] = st.session_state.github_repos

    if st.button("Create application and generate CV", type="primary", use_container_width=True):
        try:
            payload = {"job": job, "candidate": candidate}
            created = post(
                "/api/v1/jobs/applications",
                st.session_state.token,
                json=payload,
            )
            st.session_state.application = created

            with st.spinner(
                "Inspecting evidence, building the CV with Groq, and evaluating ATS match with Gemini..."
            ):
                result = post(
                    f"/api/v1/jobs/applications/{created['id']}/generate",
                    st.session_state.token,
                    json=answers,
                )

            st.session_state.resume = result
            st.success("CV generated successfully.")
        except APIError as exc:
            st.error(str(exc))

    if st.session_state.resume:
        render_resume(st.session_state.resume)

def render_resume(result):
    resume=result.get('resume',{}); ats=result.get('ats',{})
    st.divider(); st.header('Resume result')
    m1,m2,m3,m4=st.columns(4)
    m1.metric('Gemini ATS score',f"{ats.get('score',0):.1f}/100")
    m2.metric('Keyword coverage',f"{ats.get('keyword_coverage',0):.1f}%")
    m3.metric('Required skills',f"{ats.get('required_skill_coverage',0):.1f}%")
    m4.metric('Responsibility match',f"{ats.get('responsibility_alignment',0):.1f}%")
    st.subheader(resume.get('name','Resume'))
    if resume.get('contact_line'):
        st.markdown(_md_linkify(resume.get('contact_line','')))

    professional_links = resume.get('professional_links') or []
    if professional_links:
        st.markdown(
            " | ".join(
                f"[{x.get('label', 'Link')}]({_normalise_url(x.get('url', ''))})"
                for x in professional_links
                if x.get('url')
            )
        )

    if resume.get('headline'):
        st.markdown(f"**{resume.get('headline','')}**")
    if resume.get('summary'): st.write(resume['summary'])
    for title,key in [('Skills','skills'),('Experience','experience'),('Projects','projects'),('Education','education'),('Certifications','certifications')]:
        values=resume.get(key) or []
        if not values: continue
        st.subheader(title)
        if key == 'skills':
            groups = resume.get('skill_groups') or {}
            if groups:
                for group, group_values in groups.items():
                    if group_values:
                        st.markdown(f"**{group}:** " + ", ".join(group_values))
            else:
                st.write(', '.join(values))
        elif key=='certifications': st.write(', '.join(values))
        elif key=='experience':
            for x in values:
                st.markdown(f"**{x.get('title','')} — {x.get('company','')}**  ")
                st.caption(x.get('dates',''))
                for b in x.get('bullets',[]): st.markdown(f'- {b}')
        elif key=='projects':
            for x in values:
                st.markdown(f"**_{x.get('name','')}_**")
                links = x.get('links') or []
                if links:
                    st.markdown(
                        " | ".join(
                            f"[{link.get('label', 'Project')}]({_normalise_url(link.get('url', ''))})"
                            for link in links
                            if link.get('url')
                        )
                    )
                elif x.get('url'):
                    st.markdown(f"[Project link]({_normalise_url(x['url'])})")
                if x.get('technologies'): st.caption(', '.join(x['technologies']))
                for b in x.get('bullets',[]): st.markdown(f'- {b}')
        elif key=='education':
            for x in values: st.markdown(f"**{x.get('degree','')} {x.get('field','')}** — {x.get('institution','')} {x.get('dates','')}")
    if ats.get('strengths'):
        with st.expander('Why this CV matches the JD', expanded=True):
            for item in ats.get('strengths', []):
                st.markdown(f"- {item}")

    if ats.get('gaps'):
        with st.expander('ATS gaps to fix'):
            for item in ats.get('gaps', []):
                st.markdown(f"- {item}")

    if ats.get('missing_keywords'):
        with st.expander('Missing or weak keywords'):
            st.write(", ".join(ats.get('missing_keywords', [])))

    if ats.get('recommendations'):
        with st.expander('Gemini recommendations'):
            for item in ats.get('recommendations', []):
                st.markdown(f"- {item}")

    if ats.get('warnings'):
        st.warning('\n'.join(ats['warnings']))
    st.subheader('Edit resume')
    edited=copy.deepcopy(resume)

    edited['contact_line']=st.text_input('Contact line',value=resume.get('contact_line',''))

    edited['headline']=st.text_input('Headline',value=resume.get('headline',''))
    edited['summary']=st.text_area('Summary',value=resume.get('summary',''),height=150)
    edited['skills']=[x.strip() for x in st.text_input('Skills (comma separated)',value=', '.join(resume.get('skills',[]))).split(',') if x.strip()]

    if edited.get('projects'):
        st.caption('Project links')
        for idx,project in enumerate(edited['projects']):
            links = project.get('links') or []
            github_default = next(
                (link.get('url','') for link in links if link.get('label') == 'GitHub'),
                ''
            )
            demo_default = next(
                (link.get('url','') for link in links if link.get('label') in {'Live Demo','Project'}),
                ''
            )
            c1,c2 = st.columns(2)
            github = c1.text_input(
                f"{project.get('name','Project')} — GitHub",
                value=github_default,
                key=f"edit_project_github_{result.get('resume_id')}_{idx}"
            )
            demo = c2.text_input(
                f"{project.get('name','Project')} — Live Demo",
                value=demo_default,
                key=f"edit_project_demo_{result.get('resume_id')}_{idx}"
            )
            edited['projects'][idx]['links'] = [
                {'label':'GitHub','url':_normalise_url(github)}
            ] if github.strip() else []
            if demo.strip():
                edited['projects'][idx]['links'].append(
                    {'label':'Live Demo','url':_normalise_url(demo)}
                )
            edited['projects'][idx]['url'] = (
                edited['projects'][idx]['links'][0]['url']
                if edited['projects'][idx]['links'] else ''
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
    st.markdown('''<div class="cv-card"><h3>Evidence-first workflow</h3><p>CVForge separates job intelligence, candidate evidence, prompt selection, CV generation, and ATS evaluation. Groq builds the resume from evidence; Gemini independently evaluates the generated resume against the user's job description.</p></div>''',unsafe_allow_html=True)

if not st.session_state.token:
    login_screen(); st.stop()

with st.sidebar:
    st.title('CVForge')
    st.caption(st.session_state.user.get('email',''))
    pages=['Overview','CV Enhance','Applications','Profiles']
    current_page=st.session_state.get('page','Overview')
    if current_page not in pages:
        current_page='Overview'
    page=st.radio('Workspace',pages,index=pages.index(current_page))
    st.session_state.page=page
    if st.button('Sign out'): logout(); st.rerun()

if page=='Overview': dashboard()
elif page=='CV Enhance': new_application()
elif page=='Applications': applications()
elif page=='Profiles': profiles()
