import json

from google import genai
from google.genai import types

from app.core.config import settings
from app.schemas.cv import CandidateProfile, Contact, Education, Experience, JobProfile, Project, ProjectLink
from app.services.jd_parser import normalize_job_title


JOB_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "title": {"type": "string"},
        "company": {"type": "string"},
        "role_family": {"type": "string"},
        "seniority": {"type": "string"},
        "domain": {"type": "string"},
        "location": {"type": "string"},
        "employment_type": {"type": "string"},
        "must_have_skills": {"type": "array", "items": {"type": "string"}},
        "preferred_skills": {"type": "array", "items": {"type": "string"}},
        "responsibilities": {"type": "array", "items": {"type": "string"}},
        "qualifications": {"type": "array", "items": {"type": "string"}},
        "certifications": {"type": "array", "items": {"type": "string"}},
        "keywords": {"type": "array", "items": {"type": "string"}},
    },
    "required": [
        "title",
        "company",
        "role_family",
        "seniority",
        "domain",
        "location",
        "employment_type",
        "must_have_skills",
        "preferred_skills",
        "responsibilities",
        "qualifications",
        "certifications",
        "keywords",
    ],
}

CANDIDATE_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "contact": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "name": {"type": "string"},
                "email": {"type": "string"},
                "phone": {"type": "string"},
                "location": {"type": "string"},
                "linkedin": {"type": "string"},
                "github": {"type": "string"},
                "portfolio": {"type": "string"},
            },
            "required": [
                "name",
                "email",
                "phone",
                "location",
                "linkedin",
                "github",
                "portfolio",
            ],
        },
        "headline": {"type": "string"},
        "summary": {"type": "string"},
        "skills": {"type": "array", "items": {"type": "string"}},
        "experience": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "company": {"type": "string"},
                    "title": {"type": "string"},
                    "location": {"type": "string"},
                    "start_date": {"type": "string"},
                    "end_date": {"type": "string"},
                    "bullets": {"type": "array", "items": {"type": "string"}},
                },
                "required": [
                    "company",
                    "title",
                    "location",
                    "start_date",
                    "end_date",
                    "bullets",
                ],
            },
        },
        "education": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "institution": {"type": "string"},
                    "degree": {"type": "string"},
                    "field": {"type": "string"},
                    "location": {"type": "string"},
                    "start_date": {"type": "string"},
                    "end_date": {"type": "string"},
                },
                "required": [
                    "institution",
                    "degree",
                    "field",
                    "location",
                    "start_date",
                    "end_date",
                ],
            },
        },
        "projects": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "name": {"type": "string"},
                    "description": {"type": "string"},
                    "technologies": {"type": "array", "items": {"type": "string"}},
                    "bullets": {"type": "array", "items": {"type": "string"}},
                    "url": {"type": "string"},
                    "links": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "additionalProperties": False,
                            "properties": {
                                "label": {"type": "string"},
                                "url": {"type": "string"},
                            },
                            "required": ["label", "url"],
                        },
                    },
                },
                "required": [
                    "name",
                    "description",
                    "technologies",
                    "bullets",
                    "url",
                    "links",
                ],
            },
        },
        "certifications": {"type": "array", "items": {"type": "string"}},
    },
    "required": [
        "contact",
        "headline",
        "summary",
        "skills",
        "experience",
        "education",
        "projects",
        "certifications",
    ],
}


def _client() -> genai.Client:
    return genai.Client(
        api_key=settings.gemini_api_key,
        http_options=types.HttpOptions(
            retry_options=types.HttpRetryOptions(
                attempts=2,
                initial_delay=0.6,
                max_delay=2.5,
                exp_base=2.0,
                jitter=0.5,
                http_status_codes=[408, 429, 500, 502, 503, 504],
            )
        ),
    )


def _json(text: str) -> dict:
    return json.loads((text or "").strip())


def ai_analyze_job(jd_text: str, fallback: JobProfile) -> JobProfile:
    if not settings.gemini_api_key or not jd_text.strip():
        return fallback

    prompt = f"""
You are CVForge's job intelligence engine.

Analyze the job description below for resume tailoring.

Rules:
- Extract what the employer actually asks for.
- Separate must-have requirements from preferred/nice-to-have requirements.
- Convert responsibilities into concise action-oriented responsibilities.
- Normalize role family, seniority and domain.
- Extract important technical and business keywords.
- Never invent requirements that are not supported by the posting.
- Return only JSON matching the supplied schema.

JOB DESCRIPTION:
{jd_text[:30000]}
"""

    try:
        response = _client().models.generate_content(
            model=settings.gemini_fast_model,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_json_schema=JOB_SCHEMA,
                temperature=0.1,
                max_output_tokens=2500,
            ),
        )
        data = _json(getattr(response, "text", "") or "")
        data["raw_text"] = jd_text
        job = JobProfile.model_validate(data)
        job.title = normalize_job_title(job.title, jd_text)
        if job.company:
            job.company = " ".join(job.company.strip().split())[:255]
        return job
    except Exception:
        return fallback


def _merge_links(ai_projects: list[Project], parsed_projects: list[Project]) -> list[Project]:
    parsed_by_key = {
        " ".join(p.name.lower().split()): p
        for p in parsed_projects
        if p.name
    }

    merged: list[Project] = []
    used: set[str] = set()

    for project in ai_projects:
        key = " ".join(project.name.lower().split())
        source = parsed_by_key.get(key)

        if source:
            if not project.links:
                project.links = list(source.links)
            if not project.url:
                project.url = source.url
            if not project.technologies:
                project.technologies = list(source.technologies)
            if not project.bullets:
                project.bullets = list(source.bullets)
            used.add(key)

        merged.append(project)

    for project in parsed_projects:
        key = " ".join(project.name.lower().split())
        if key and key not in used and key not in {"projects", "selected projects"}:
            merged.append(project)

    return merged[:10]


def ai_extract_candidate(
    raw_text: str,
    filename: str,
    fallback: CandidateProfile,
) -> CandidateProfile:
    if not settings.gemini_api_key or not raw_text.strip():
        return fallback

    prompt = f"""
You are CVForge's evidence extraction engine.

Extract the candidate's existing CV into structured evidence.

Hard rules:
- Only extract facts present in the source.
- Never invent employers, dates, skills, metrics, credentials or project URLs.
- Preserve URLs exactly.
- Distinguish personal LinkedIn/GitHub/Portfolio from project GitHub/Demo links.
- Preserve real project names instead of collapsing everything into one Projects entry.
- Preserve project technologies and bullets.
- Keep missing fields empty.
- Do not rewrite achievements; extraction only.
- Return only JSON matching the supplied schema.

SOURCE FILE: {filename}

CV TEXT:
{raw_text[:50000]}
"""

    try:
        response = _client().models.generate_content(
            model=settings.gemini_fast_model,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_json_schema=CANDIDATE_SCHEMA,
                temperature=0.0,
                max_output_tokens=7000,
            ),
        )
        data = _json(getattr(response, "text", "") or "")
        candidate = CandidateProfile.model_validate(data)

        # Deterministic parser remains the source of truth for raw text/format
        # and preserves PDF hyperlink annotations that may not appear in text.
        candidate.raw_text = fallback.raw_text or raw_text
        candidate.source_format = fallback.source_format or filename.rsplit(".", 1)[-1]

        if not candidate.contact.email:
            candidate.contact.email = fallback.contact.email
        if not candidate.contact.phone:
            candidate.contact.phone = fallback.contact.phone
        if not candidate.contact.location:
            candidate.contact.location = fallback.contact.location
        if not candidate.contact.linkedin:
            candidate.contact.linkedin = fallback.contact.linkedin
        if not candidate.contact.github:
            candidate.contact.github = fallback.contact.github
        if not candidate.contact.portfolio:
            candidate.contact.portfolio = fallback.contact.portfolio
        if not candidate.skills:
            candidate.skills = list(fallback.skills)
        if not candidate.experience:
            candidate.experience = list(fallback.experience)
        if not candidate.education:
            candidate.education = list(fallback.education)
        if not candidate.certifications:
            candidate.certifications = list(fallback.certifications)

        candidate.projects = _merge_links(candidate.projects, fallback.projects)

        return candidate
    except Exception:
        return fallback
