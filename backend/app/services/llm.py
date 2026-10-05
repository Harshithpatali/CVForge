import json

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
            "additionalProperties": {
                "type": "array", "items": {"type": "string"}
            },
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


def _extract_json(text: str) -> dict:
    text = text.strip()
    try:
        value = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError("Groq did not return valid JSON.") from exc
    if not isinstance(value, dict):
        raise ValueError("Groq resume response must be a JSON object.")
    return value


def generate_resume(prompt: str) -> dict:
    if not settings.groq_api_key:
        raise RuntimeError("GROQ_API_KEY is not configured.")

    client = OpenAI(
        api_key=settings.groq_api_key,
        base_url=settings.groq_base_url,
    )
    response = client.chat.completions.create(
        model=settings.groq_model,
        messages=[
            {
                "role": "system",
                "content": (
                    "Return the complete CVForge resume schema. Every required field "
                    "must be present, including empty arrays when there is no evidence. "
                    "Never invent facts or URLs.",
                ),
            },
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
    return _extract_json(response.choices[0].message.content or "")