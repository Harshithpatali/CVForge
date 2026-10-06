from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', extra='ignore')

    database_url: str

    # Groq builds the tailored resume.
    groq_api_key: str = ''
    groq_model: str = 'openai/gpt-oss-120b'
    groq_base_url: str = 'https://api.groq.com/openai/v1'

    # Gemini evaluates ATS/job-match quality after generation.
    gemini_api_key: str = ''
    gemini_model: str = 'gemini-3.8-flash'
    # Comma-separated fallback models used when Gemini returns transient 429/5xx errors.
    gemini_fallback_models: str = 'gemini-3.6-flash,gemini-3.5-flash-lite'
    gemini_retry_attempts: int = 2
    gemini_fast_model: str = 'gemini-3.5-flash-lite'
    gemini_embedding_model: str = 'gemini-embedding-2'
    gemini_embedding_dimension: int = 768

    # Authentication
    jwt_secret: str = 'change-me-in-production'
    jwt_expire_minutes: int = 1440

    # FastAPI CORS
    cors_origins: str = '*'

    # Artifact storage
    storage_backend: str = 'local'
    s3_bucket: str = ''
    s3_region: str = 'ap-south-1'
    s3_prefix: str = 'cvforge'
    s3_presign_seconds: int = 900

    @property
    def cors_list(self):
        if self.cors_origins.strip() == '*':
            return ['*']
        return [x.strip() for x in self.cors_origins.split(',') if x.strip()]


settings = Settings()
