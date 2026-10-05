import re

from app.schemas.cv import CandidateProfile, JobProfile
from app.schemas.resume import GeneratedResume


def norm(s):
    return re.sub(r"[^a-z0-9+#.-]+", " ", s.lower()).strip()


def validate(resume: GeneratedResume, job: JobProfile, candidate: CandidateProfile):
    text = norm(resume.model_dump_json())

    required = {norm(x) for x in job.must_have_skills}
    covered = {x for x in required if x in text}
    keyword_score = len(covered) / len(required) if required else 1.0

    sections = [
        bool(resume.name),
        bool(resume.contact_line),
        bool(resume.summary),
        bool(resume.skills),
        bool(resume.experience or resume.projects),
        bool(resume.education),
    ]
    section_score = sum(sections) / len(sections)

    title_score = (
        1.0
        if norm(job.title)
        and any(
            tok in norm(resume.headline)
            for tok in norm(job.title).split()
            if len(tok) > 2
        )
        else 0.5
    )

    expected_links = []
    if candidate.contact.linkedin:
        expected_links.append(("LinkedIn", candidate.contact.linkedin))
    if candidate.contact.portfolio:
        expected_links.append(("Portfolio", candidate.contact.portfolio))
    if candidate.contact.github:
        expected_links.append(("GitHub", candidate.contact.github))

    for project in candidate.projects:
        for link in project.links:
            if link.url:
                expected_links.append((f"{project.name or 'Project'} - {link.label}", link.url))
        if project.url:
            expected_links.append((project.name or "Project", project.url))

    resume_text = resume.model_dump_json()
    covered_links = [
        (label, url)
        for label, url in expected_links
        if url in resume_text
    ]
    link_coverage = (
        len(covered_links) / len(expected_links)
        if expected_links
        else 1.0
    )

    warnings = []
    if len(resume.summary.split()) > 100:
        warnings.append("Summary is longer than recommended.")
    if len(resume.skills) > 35:
        warnings.append("Skills section is too large; remove low-relevance skills.")
    if not resume.experience and not resume.projects:
        warnings.append("No experience or projects section has evidence.")

    missing_links = [
        label
        for label, _ in expected_links
        if label not in {x[0] for x in covered_links}
    ]
    if missing_links:
        warnings.append(
            "Missing provided links: " + ", ".join(missing_links)
        )

    score = round(
        100
        * (
            0.55 * keyword_score
            + 0.30 * section_score
            + 0.15 * title_score
        ),
        1,
    )

    return {
        "score": score,
        "keyword_coverage": round(keyword_score * 100, 1),
        "required_keywords": sorted(required),
        "covered_keywords": sorted(covered),
        "section_score": round(section_score * 100, 1),
        "link_coverage": round(link_coverage * 100, 1),
        "expected_links": len(expected_links),
        "covered_links": len(covered_links),
        "warnings": warnings,
    }
