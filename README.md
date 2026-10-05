# CVForge — Render Free + Neon

CVForge is an ATS-focused CV tailoring SaaS built around deterministic document extraction, structured job-description analysis, role/seniority/domain-specific prompts, Grok structured generation, ATS validation, resume editing, and DOCX/PDF rendering.

## Free-tier deployment architecture

- Render Web Service: FastAPI backend in Docker
- Render Static Site or Web Service: Next.js frontend
- Neon PostgreSQL: persistent application data
- Grok/xAI API: generation
- No Kubernetes
- No Redis
- No separate Render worker on the free plan
- No Render persistent disk dependency

Generation is synchronous on the free-tier deployment. The generation service remains isolated so it can later be moved behind a queue/worker without rewriting the core resume-generation logic.

## Local backend

```bash
cd backend
python -m venv .venv
# activate the environment
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

## Environment

Copy `.env.example` to `.env` and set your Neon and xAI credentials.

## Render backend

Create a Render **Web Service** pointing at the repository root with:

- Runtime: Docker
- Dockerfile: `backend/Dockerfile`
- Health check path: `/health`
- No worker service required for the free deployment

Set environment variables in Render instead of committing secrets.
