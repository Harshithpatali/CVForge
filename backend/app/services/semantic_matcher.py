import math

from google import genai
from google.genai import types

from app.core.config import settings


def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return max(-1.0, min(1.0, dot / (na * nb)))


def _to_score(similarity: float) -> float:
    # Cosine similarity generally clusters in a narrower positive range for
    # job/resume text than the full [-1,1] interval.
    return round(max(0.0, min(100.0, ((similarity + 1.0) / 2.0) * 100.0)), 1)


def _embed_texts(client: genai.Client, texts: list[str]) -> list[list[float]]:
    response = client.models.embed_content(
        model=settings.gemini_embedding_model,
        contents=texts,
        config=types.EmbedContentConfig(
            output_dimensionality=settings.gemini_embedding_dimension,
        ),
    )
    return [
        [float(value) for value in (embedding.values or [])]
        for embedding in (response.embeddings or [])
    ]


def semantic_job_match(job: dict, resume: dict) -> dict | None:
    if not settings.gemini_api_key:
        return None

    responsibilities = [str(x) for x in job.get("responsibilities", []) if str(x).strip()]
    must = [str(x) for x in job.get("must_have_skills", []) if str(x).strip()]
    preferred = [str(x) for x in job.get("preferred_skills", []) if str(x).strip()]
    title = str(job.get("title", "")).strip()

    resume_skills = resume.get("skills") or []
    grouped = resume.get("skill_groups") or {}
    grouped_values = [
        item
        for values in grouped.values()
        for item in (values or [])
    ]

    experience = [
        f"{item.get('title', '')} {item.get('company', '')} "
        + " ".join(item.get("bullets") or [])
        for item in (resume.get("experience") or [])
    ]
    projects = [
        f"{item.get('name', '')} {' '.join(item.get('technologies') or [])} "
        + " ".join(item.get("bullets") or [])
        for item in (resume.get("projects") or [])
    ]

    resume_text = " ".join(
        [
            str(resume.get("headline", "")),
            str(resume.get("summary", "")),
            " ".join(str(x) for x in resume_skills),
            " ".join(str(x) for x in grouped_values),
            " ".join(experience),
            " ".join(projects),
        ]
    ).strip()

    if not resume_text:
        return None

    job_text = " ".join(
        [
            title,
            " ".join(must),
            " ".join(preferred),
            " ".join(responsibilities),
            " ".join(str(x) for x in (job.get("qualifications") or [])),
        ]
    ).strip()

    responsibility_text = " ".join(responsibilities).strip() or job_text
    skill_text = " ".join(must + preferred).strip() or job_text

    client = genai.Client(api_key=settings.gemini_api_key)
    vectors = _embed_texts(
        client,
        [job_text, skill_text, responsibility_text, resume_text],
    )

    return {
        "overall": _to_score(_cosine(vectors[0], vectors[3])),
        "skills": _to_score(_cosine(vectors[1], vectors[3])),
        "responsibilities": _to_score(_cosine(vectors[2], vectors[3])),
    }
