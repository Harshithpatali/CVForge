# CVForge

Production-grade, evidence-first resume tailoring.

## Architecture

```text
Streamlit Community Cloud
        |
        | HTTPS
        v
FastAPI on Render
   |            |
   |            +--> Groq GPT-OSS 120B
   |            |       (CV generation)
   |            |
   |            +--> Google Gemini 3.8 Flash
   |                    (ATS evaluation)
   |
   v
Neon PostgreSQL
```

The current deployment uses one synchronous FastAPI service. This is appropriate for a Render Free portfolio deployment. Generation is isolated in `generation_service.py`. `llm.py` separates the two model responsibilities: Groq generates the CV, and Gemini evaluates the generated CV against the user's job description.

## CV input and ATS project planning

CVForge accepts an existing CV in two ways during job analysis:

- upload a PDF, DOCX, TXT, or Markdown file
- paste the CV text directly

When both are supplied, the pasted CV takes precedence so the candidate evidence stays deterministic.

After Groq generates the tailored CV, Gemini independently evaluates the exact CV against the job description. In addition to ATS scoring, Gemini can identify important capability gaps and propose up to three portfolio project ideas. Each suggestion is stored with its rationale, skills to demonstrate, project scope, implementation plan, and the resume signal the completed project could provide. Suggested projects are explicitly treated as future work and are never added to the candidate's current experience or projects automatically.

## Evidence-first pipeline

1. Parse the CV into structured candidate evidence.
2. Parse the JD into role family, seniority, domain, skills, and keywords.
3. Inspect public GitHub repositories supplied by the candidate and use bounded repository evidence.
4. Ask targeted evidence questions when requirements lack evidence.
5. Select a versioned prompt template based on role, seniority, and domain.
6. Generate the tailored CV with Groq using only candidate evidence.
7. Send the generated CV and the user's job description to Gemini for an independent ATS/job-match evaluation.
8. Store the Gemini ATS report with the resume revision.
9. Render PDF/DOCX on demand.

## Repository

```text
CVForge/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   ├── models/
│   │   ├── schemas/
│   │   └── services/
│   ├── alembic/
│   ├── Dockerfile
│   └── requirements.txt
└── streamlit_app/
    ├── app.py
    ├── api_client.py
    └── requirements.txt
```

## Backend environment

DATABASE_URL=postgresql://...

# Groq builds the CV
GROQ_API_KEY=...
GROQ_MODEL=openai/gpt-oss-120b
GROQ_BASE_URL=https://api.groq.com/openai/v1

# Gemini evaluates ATS/job match
GEMINI_API_KEY=...
GEMINI_MODEL=gemini-3.8-flash

JWT_SECRET=<strong-random-secret>
CORS_ORIGINS=*
```

Groq uses the OpenAI-compatible Python client for structured resume generation. Gemini uses the official Google GenAI Python SDK for structured ATS evaluation.

## Streamlit environment

Set a Streamlit secret/environment variable:

```text
CVFORGE_API_URL=https://<your-render-backend>.onrender.com
```

## Render backend

Runtime: Docker  
Root directory: `backend`  
Dockerfile: `Dockerfile`  
Plan: Free  
Health check: `/health`

The Dockerfile runs Alembic migrations before starting Uvicorn and uses Render's `$PORT`.

For the production workflow, add these Render environment variables:

```text
GROQ_API_KEY=<your-groq-key>
GROQ_MODEL=openai/gpt-oss-120b
GEMINI_API_KEY=<your-gemini-key>
GEMINI_MODEL=gemini-3.8-flash
```

Do not commit either key to GitHub.

## Frontend deployment fingerprint

The Streamlit frontend entrypoint is:
```text
streamlit_app/app.py
```

The current production UI build displays:
```text
studio-ui-2026.10.06
```

The sidebar should show:
```text
Dashboard
CV Studio
Applications
Profiles
```

If Streamlit still shows `New Application`, it is serving an older deployment/commit or a different main-file path.

## Streamlit Community Cloud

Repository: `Harshithpatali/CVForge`  
Main file: `streamlit_app/app.py`

Secret:

```toml
CVFORGE_API_URL = "https://<your-render-backend>.onrender.com"
```

## Streamlit Community Cloud

The Streamlit frontend is isolated in the `frontend/` directory.

**Main file:** `frontend/app.py`

**Dependencies:** `frontend/requirements.txt`

**Configuration:** `.streamlit/config.toml` at the repository root.

This follows Streamlit Community Cloud's supported subdirectory layout: an
entrypoint may live in a subdirectory, its dependency file may live beside it,
and the single Streamlit configuration file stays at the repository root.

The production sidebar is:

```text
Dashboard
CV Studio
Applications
Profiles
```

The current UI build fingerprint shown in the sidebar is:

```text
studio-ui-2026.10.06
```


## Security

- Never commit API keys or database passwords.
- Use a strong `JWT_SECRET` in production.
- Candidate CV text is treated as evidence and unsupported claims are prohibited.
- The ATS score is generated by Gemini from the supplied job description and generated CV; the evaluator is separate from the Groq generation step.
- GitHub repository inspection is limited to public repositories.

## LLM responsibilities

### Groq — CV generation
Groq receives the parsed JD, candidate evidence, project evidence, and GitHub repository evidence. It generates the tailored CV in the strict CVForge resume schema.

### Gemini — ATS evaluation
After Groq generates the CV, Gemini receives the parsed job signals plus the generated CV and returns a structured 0–100 ATS/job-match report containing keyword coverage, required-skill coverage, title alignment, responsibility alignment, strengths, gaps, missing keywords, and recommendations.
