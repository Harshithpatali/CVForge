from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', extra='ignore')
    database_url: str
    xai_api_key: str = ''
    xai_model: str = 'grok-4.7'
    xai_base_url: str = 'https://api.x.ai/v1'
    jwt_secret: str = 'change-me-in-production'
    jwt_expire_minutes: int = 1440
    cors_origins: str = '*'
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
