# Render Free Deployment

## Backend

Create one Render Web Service:

- Environment: Docker
- Dockerfile path: `backend/Dockerfile`
- Health check: `/health`
- Port: 8000

Required environment variables:

```env
DATABASE_URL=postgresql+psycopg://...
XAI_API_KEY=...
XAI_MODEL=grok-4.5
CORS_ORIGINS=https://your-frontend-url
STORAGE_BACKEND=local
```

Do not depend on the container filesystem for permanent resume storage. For a free demo, return generated files directly. Add external object storage later if persistent artifact downloads are required.

## Frontend

Deploy the Next.js frontend separately and set its API base URL to the Render backend URL.

## Free-tier guidance

Do not deploy a separate worker, Redis, Kubernetes cluster, or database service on Render for the initial free deployment. The API performs generation synchronously and the generation service is kept modular for a future queue-based deployment.
