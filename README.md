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
   |            |
   |            +--> Google Gemini 3.8 Flash
   |
   v
Neon PostgreSQL
```

The current deployment uses one synchronous FastAPI service. This is appropriate for a Render Free portfolio deployment. Generation is isolated in `generation_service.py`, while `llm.py` provides a provider switch so the same resume pipeline can run through Groq or Gemini without changing application logic.

Set `LLM_PROVIDER=groq` or `LLM_PROVIDER=gemini` in the backend environment.

## Evidence-first pipeline

1. Parse the CV into structured candidate evidence.
2. Parse the JD into role family, seniority, domain, skills, and keywords.
3. Inspect public GitHub repositories supplied by the candidate and use bounded repository evidence.
4. Ask targeted evidence questions when requirements lack evidence.
5. Select a versioned prompt template based on role, seniority, and domain.
6. Generate a structured resume through the configured LLM provider.
7. Validate ATS alignment deterministically.
8. Store applications, prompt versions, generation jobs, and immutable resume revisions in PostgreSQL.
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

Use one provider at a time:

```env
DATABASE_URL=postgresql://...
LLM_PROVIDER=gemini

# Google AI Studio / Gemini
GEMINI_API_KEY=...
GEMINI_MODEL=gemini-3.8-flash

# Optional Groq provider
GROQ_API_KEY=...
GROQ_MODEL=openai/gpt-oss-120b
GROQ_BASE_URL=https://api.groq.com/openai/v1

JWT_SECRET=<strong-random-secret>
CORS_ORIGINS=*
```

Google's official GenAI Python SDK is used for Gemini structured JSON output. Groq continues to use the OpenAI-compatible Python client.

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

For Gemini, add these Render environment variables:

```text
LLM_PROVIDER=gemini
GEMINI_API_KEY=<your-key>
GEMINI_MODEL=gemini-3.8-flash
```

Do not commit the key to GitHub.

## Streamlit Community Cloud

Repository: `Harshithpatali/CVForge`  
Main file: `streamlit_app/app.py`

Secret:

```toml
CVFORGE_API_URL = "https://<your-render-backend>.onrender.com"
```

## Security

- Never commit API keys or database passwords.
- Use a strong `JWT_SECRET` in production.
- Candidate CV text is treated as evidence and unsupported claims are prohibited.
- The ATS score is deterministic and independent of the LLM's self-evaluation.
- GitHub repository inspection is limited to public repositories.

## Gemini

CVForge uses the official Google GenAI Python SDK with Gemini structured output. The current default model is `gemini-3.8-flash`, and the resume response is constrained to the CVForge JSON schema before Pydantic validation.

## Groq

CVForge uses Groq's OpenAI-compatible API through the official Python OpenAI client with `https://api.groq.com/openai/v1` and the `openai/gpt-oss-120b` model.
