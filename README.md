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
   v            v
Neon PostgreSQL  xAI Grok
```

The current deployment uses one synchronous FastAPI service. This is appropriate for a Render Free portfolio deployment. Generation is isolated in `generation_service.py`, so a queue/worker can be introduced later without redesigning the product.

## Evidence-first pipeline

1. Parse the CV into structured candidate evidence.
2. Parse the JD into role family, seniority, domain, skills, and keywords.
3. Ask targeted evidence questions when requirements lack evidence.
4. Select a versioned prompt template based on role, seniority, and domain.
5. Generate with Grok using only candidate evidence and explicit answers.
6. Validate ATS alignment deterministically.
7. Store applications, prompt versions, generation jobs, and immutable resume revisions in PostgreSQL.
8. Render PDF/DOCX on demand.

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

```env
DATABASE_URL=postgresql://...
XAI_API_KEY=xai-...
XAI_MODEL=grok-4.7
XAI_BASE_URL=https://api.x.ai/v1
JWT_SECRET=<strong-random-secret>
CORS_ORIGINS=*
```

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

## xAI

CVForge uses xAI's OpenAI-compatible API through the official Python OpenAI client with `https://api.x.ai/v1` as the base URL.
