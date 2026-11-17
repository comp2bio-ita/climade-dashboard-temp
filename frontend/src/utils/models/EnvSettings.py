from pydantic_settings import BaseSettings

class EnvSettings(BaseSettings):
    DASH_HOST: str = None
    DASH_PORT: int = None
    DASH_USER: str = None
    DASH_PASSWORD: str = None
    DASH_DATABASE: str = None