from dataclasses import dataclass


@dataclass(frozen=True)
class PromptTemplate:
    key: str
    role_family: str
    seniority: str
    domain: str
    version: int
    instructions: str


BASE = """You are CVForge, an evidence-first resume tailoring engine.
You must tailor a resume to the target job without inventing facts.

HARD RULES:
1. Use only evidence present in the candidate profile or explicit user answers.
2. Never invent employers, dates, degrees, technologies, certifications, metrics, job titles, achievements, or URLs.
3. Rewrite wording only for relevance, clarity, ATS alignment, and impact.
4. Do not add a skill merely because it appears in the job description.
5. If evidence for a required skill is absent, omit it from the resume.
6. Prefer quantified achievements only when the source contains a real number.
7. Preserve candidate-provided LinkedIn, portfolio, GitHub, and project URLs exactly.
8. Project links must use the provided label, such as GitHub or Live Demo.
9. Never output a placeholder link or invent a URL.
10. Keep the resume concise, one-column, ATS-readable, and visually close to a professional LaTeX CV.
11. Use categorized technical skills where the evidence supports categories such as Languages, Data & ML, Statistics, Analytics, Databases & Tools, Deployment, and Visualization.
12. Return ONLY valid JSON matching the requested schema.
"""


ROLE_GUIDANCE = {
    "data_science": "Prioritize statistical reasoning, experimentation, ML modeling, business impact, Python/SQL, evaluation metrics, and end-to-end analytical work.",
    "data_analytics": "Prioritize SQL, BI, dashboards, KPI analysis, experimentation, stakeholder communication, and measurable business outcomes.",
    "machine_learning": "Prioritize production ML, feature engineering, model evaluation, APIs, deployment, monitoring, and software/data engineering evidence.",
    "data_engineering": "Prioritize data pipelines, SQL, Spark, orchestration, warehouses, data quality, reliability, and scalable systems evidence.",
    "finance": "Prioritize quantitative analysis, risk, financial modeling, controls, statistics, and domain-relevant evidence.",
    "software": "Prioritize software engineering, APIs, testing, architecture, databases, deployment, and engineering impact.",
    "general": "Prioritize the strongest evidence that directly maps to the target role.",
}


DOMAIN_GUIDANCE = {
    "fintech": "Use precise risk/finance terminology only when supported by candidate evidence.",
    "healthcare": "Prioritize accuracy, validation, governance, and domain-relevant analytical evidence when supported.",
    "retail": "Prioritize customer, revenue, conversion, forecasting, experimentation, and operational evidence when supported.",
    "energy": "Prioritize process optimization, reliability, analytics, forecasting, and engineering evidence when supported.",
    "consulting": "Prioritize client impact, structured problem solving, communication, and cross-functional delivery when supported.",
    "general": "",
}


def select_template(role_family: str, seniority: str, domain: str) -> PromptTemplate:
    role = role_family if role_family in ROLE_GUIDANCE else "general"
    senior = (
        seniority
        if seniority in {"intern", "entry", "mid", "senior", "staff"}
        else "entry"
    )
    dom = domain if domain in DOMAIN_GUIDANCE else "general"

    key = f"resume.{role}.{senior}.{dom}"
    instructions = (
        f"{BASE}\n"
        f"ROLE GUIDANCE: {ROLE_GUIDANCE[role]}\n"
        f"DOMAIN GUIDANCE: {DOMAIN_GUIDANCE[dom]}"
    )

    if senior in {"intern", "entry"}:
        instructions += (
            "\nSENIORITY GUIDANCE: Emphasize projects, education, internships, "
            "practical evidence, and demonstrated skills."
        )
    elif senior == "mid":
        instructions += (
            "\nSENIORITY GUIDANCE: Emphasize ownership, measurable outcomes, "
            "and breadth of delivery."
        )
    else:
        instructions += (
            "\nSENIORITY GUIDANCE: Emphasize leadership, architecture, scope, "
            "and business impact only where evidenced."
        )

    return PromptTemplate(
        key,
        role,
        senior,
        dom,
        1,
        instructions,
    )


def build_generation_prompt(
    job: dict,
    candidate: dict,
    answers: dict,
    template: PromptTemplate,
) -> str:
    import json

    schema = {
        "name": "string",
        "contact_line": "string",
        "headline": "string",
        "summary": "string",
        "skills": ["string"],
        "skill_groups": {
            "Languages": ["string"],
            "Data & ML": ["string"],
            "Statistics": ["string"],
            "Analytics": ["string"],
            "Databases & Tools": ["string"],
            "Deployment": ["string"],
            "Visualization": ["string"],
        },
        "professional_links": [
            {"label": "LinkedIn", "url": "https://..."}
        ],
        "experience": [
            {
                "company": "string",
                "title": "string",
                "dates": "string",
                "location": "string",
                "bullets": ["string"],
            }
        ],
        "projects": [
            {
                "name": "string",
                "bullets": ["string"],
                "technologies": ["string"],
                "url": "string",
                "links": [
                    {"label": "GitHub", "url": "https://..."},
                    {"label": "Live Demo", "url": "https://..."}
                ],
            }
        ],
        "education": [
            {
                "institution": "string",
                "degree": "string",
                "field": "string",
                "dates": "string",
            }
        ],
        "certifications": ["string"],
    }

    return f"""{template.instructions}

TARGET JOB:
{json.dumps(job, ensure_ascii=False)}

CANDIDATE EVIDENCE:
{json.dumps(candidate, ensure_ascii=False)}

ADDITIONAL USER ANSWERS:
{json.dumps(answers or {}, ensure_ascii=False)}

OUTPUT JSON SCHEMA:
{json.dumps(schema, ensure_ascii=False)}

Create the strongest truthful ATS-friendly resume for this exact job.
Use the visual hierarchy of the supplied LaTeX reference:
name and target headline centered, compact contact row, professional links row,
then blue-accent section headings with horizontal rules.
Keep experience and projects concise with strong bullets.
For projects, use the exact project names supplied by the candidate where possible
and include GitHub / Live Demo links when provided.
For skills, group evidence into useful categories rather than one giant comma-separated list.
Never invent links, metrics, dates, employers, or credentials.
"""
