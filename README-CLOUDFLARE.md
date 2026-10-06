# CVForge — Cloudflare React Deployment

CVForge now includes a React/Vite frontend in `frontend-react/` while preserving the existing FastAPI AI/CV engine.

## Cloudflare Pages settings

- Root directory: `/`
- Build command: `npm --prefix frontend-react install && npm --prefix frontend-react run build`
- Build output directory: `frontend-react/dist`

Add this **Production** secret:

`CVFORGE_API_URL=https://YOUR-BACKEND.example.com`

Do not put Groq or Gemini API keys in the React app. Those stay on the FastAPI backend.

## Architecture

Browser -> Cloudflare Pages React -> Pages Function /api/* -> FastAPI -> PostgreSQL + Groq + Gemini.

The Pages Function in `functions/[[path]].js` keeps browser requests on the Cloudflare origin and forwards them to the backend.

## Local React

```bash
cd frontend-react
npm install
npm run dev
```

Optional local API base:

```text
VITE_API_BASE=http://localhost:8000/api
```

## Product workflow

1. Paste or upload a CV.
2. Paste a target job description.
3. Run the existing CVForge analysis/generation pipeline.
4. Review the generated CV.
5. Review ATS score, strengths, gaps, missing keywords and recommendations.

The backend remains responsible for authentication, persistence, AI generation, ATS evaluation, document parsing and PDF/DOCX rendering.
