from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.jobs import router as jobs_router
from app.api.resumes import router as legacy_resumes_router
from app.api.auth import router as auth_router
from app.api.profiles import router as profiles_router
from app.api.applications import router as applications_router
from app.api.editor import router as editor_router

app=FastAPI(title='CVForge API',version='3.0.0',description='Evidence-first resume tailoring API')
app.add_middleware(CORSMiddleware,allow_origins=settings.cors_list,allow_credentials=settings.cors_origins.strip() != '*',allow_methods=['*'],allow_headers=['*'])
for r in [auth_router,profiles_router,applications_router,jobs_router,editor_router,legacy_resumes_router]: app.include_router(r)

@app.get('/')
def root():
    return {'service':'CVForge API','version':'3.0.0','docs':'/docs','health':'/health'}

@app.get('/health')
def health():
    return {'status':'ok','service':'cvforge-api','storage_backend':settings.storage_backend}
