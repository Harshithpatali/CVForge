import json

from google import genai
from google.genai import types
from openai import OpenAI

from app.core.config import settings


REQUIRED_RESUME_FIELDS = [
    "name", "contact_line", "headline", "summary", "skills",
    "skill_groups", "professional_links", "experience", "projects",
    "education", "certifications",
]

RESUME_JSON_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "name": {"type": "string"},
        "contact_line": {"type": "string"},
        "headline": {"type": "string"},
        "summary": {"type": "string"},
        "skills": {"type": "array", "items": {"type": "string"}},
        "skill_groups": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "Languages": {"type": "array", "items": {"type": "string"}},
                "Data & ML": {"type": "array", "items": {"type": "string"}},
                "Statistics": {"type": "array", "items": {"type": "string"}},
                "Analytics": {"type": "array", "items": {"type": "string"}},
                "Databases & Tools": {"type": "array", "items": {"type": "string"}},
                "Deployment": {"type": "array", "items": {"type": "string"}},
                "Visualization": {"type": "array", "items": {"type": "string"}},
            },
            "required": [
                "Languages",
                "Data & ML",
                "Statistics",
                "Analytics",
                "Databases & Tools",
                "Deployment",
                "Visualization",
            ],
        },
        "professional_links": {
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
        "experience": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "company": {"type": "string"},
                    "title": {"type": "string"},
                    "dates": {"type": "string"},
                    "location": {"type": "string"},
                    "bullets": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["company", "title", "dates", "location", "bullets"],
            },
        },
        "projects": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "name": {"type": "string"},
                    "bullets": {"type": "array", "items": {"type": "string"}},
                    "technologies": {"type": "array", "items": {"type": "string"}},
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
                "required": ["name", "bullets", "technologies", "url", "links"],
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
                    "dates": {"type": "string"},
                },
                "required": ["institution", "degree", "field", "dates"],
            },
        },
        "certifications": {"type": "array", "items": {"type": "string"}},
    },
    "required": REQUIRED_RESUME_FIELDS,
}

ATS_JSON_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "score": {"type": "number", "minimum": 0, "maximum": 100},
        "keyword_coverage": {"type": "number", "minimum": 0, "maximum": 100},
        "required_skill_coverage": {"type": "number", "minimum": 0, "maximum": 100},
        "title_alignment": {"type": "number", "minimum": 0, "maximum": 100},
        "responsibility_alignment": {"type": "number", "minimum": 0, "maximum": 100},
        "formatting_score": {"type": "number", "minimum": 0, "maximum": 100},
        "matched_keywords": {"type": "array", "items": {"type": "string"}},
        "missing_keywords": {"type": "array", "items": {"type": "string"}},
        "strengths": {"type": "array", "items": {"type": "string"}},
        "gaps": {"type": "array", "items": {"type": "string"}},
        "recommendations": {"type": "array", "items": {"type": "string"}},
        "warnings": {"type": "array", "items": {"type": "string"}},
    },
    "required": [
        "score",
        "keyword_coverage",
        "required_skill_coverage",
        "title_alignment",
        "responsibility_alignment",
        "formatting_score",
        "matched_keywords",
        "missing_keywords",
        "strengths",
        "gaps",
        "recommendations",
        "warnings",
    ],
}

CV_SYSTEM_PROMPT = (
    "You are CVForge's resume generation engine. Return the complete CVForge "
    "resume schema. Every required field must be present, including empty arrays "
    "when there is no evidence. Never invent facts, metrics, credentials, or URLs."
)

ATS_SYSTEM_PROMPT = (
    "You are CVForge's ATS evaluation engine. Evaluate the generated resume "
    "strictly against the provided job description. Score the resume from 0 to 100 "
    "for likely ATS/job-match strength. Do not reward skills that are absent from "
    "the resume. Do not penalize the resume for refusing to invent unsupported facts. "
    "Consider exact and close keyword matches, required-skill coverage, title alignment, "
    "responsibility alignment, and machine-readable formatting. Return only the "
    "requested JSON schema."
)


def _extract_json(text: str, label: str) -> dict:
    text = (text or "").strip()
    try:
        value = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{label} did not return valid JSON.") from exc
    if not isinstance(value, dict):
        raise ValueError(f"{label} response must be a JSON object.")
    return value


def _generate_with_groq(prompt: str) -> dict:
    if not settings.groq_api_key:
        raise RuntimeError("GROQ_API_KEY is not configured.")

    client = OpenAI(
        api_key=settings.groq_api_key,
        base_url=settings.groq_base_url,
    )
    response = client.chat.completions.create(
        model=settings.groq_model,
        messages=[
            {"role": "system", "content": CV_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
        max_completion_tokens=5000,
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "cvforge_resume",
                "strict": True,
                "schema": RESUME_JSON_SCHEMA,
            },
        },
    )
    return _extract_json(response.choices[0].message.content or "", "Groq")


def generate_resume(prompt: str) -> dict:
    # Groq is intentionally the only resume-generation provider.
    return _generate_with_groq(prompt)


def evaluate_ats(job: dict, resume: dict) -> dict:
    if not settings.gemini_api_key:
        raise RuntimeError("GEMINI_API_KEY is not configured.")

    client = genai.Client(api_key=settings.gemini_api_key)
    prompt = (
        "JOB DESCRIPTION AND PARSED JOB SIGNALS:\n"
        f"{json.dumps(job, ensure_ascii=False)}\n\n"
        "GENERATED RESUME:\n"
        f"{json.dumps(resume, ensure_ascii=False)}\n\n"
        "Evaluate the generated resume as an ATS/job-match artifact. "
        "The overall score must reflect how strongly this exact resume matches "
        "this exact job. Identify matched and missing keywords from the job data "
        "and explain the highest-impact gaps. Do not invent candidate experience."
    )

    response = client.models.generate_content(
        model=settings.gemini_model,
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=ATS_SYSTEM_PROMPT,
            response_mime_type="application/json",
            response_json_schema=ATS_JSON_SCHEMA,
            max_output_tokens=4000,
        ),
    )
    return _extract_json(getattr(response, "text", "") or "", "Gemini ATS evaluator")
