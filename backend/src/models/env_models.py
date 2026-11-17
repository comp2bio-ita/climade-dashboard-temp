from pydantic_settings import BaseSettings, SettingsConfigDict

class EnvSettings(BaseSettings):
    DASH_HOST: str = None
    DASH_PORT: int = None
    DASH_USER: str = None
    DASH_PASSWORD: str = None
    DASH_DATABASE: str = None
    NCBI_EMAIL: str = None
    NCBI_API_KEY: str = None

    # Instructs Pydantic to read system env vars first, falling back to .env if needed
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')