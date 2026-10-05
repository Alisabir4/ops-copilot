from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "sqlite:///./copilot.db"
    jwt_secret: str = "development-secret-change-before-deployment"
    jwt_expire_minutes: int = 720
    groq_api_key: str = ""
    groq_model: str = ""
    groq_base_url: str = "https://api.groq.com/openai/v1"
    n8n_webhook_url: str = ""
    n8n_api_key: str = ""
    demo_mode: bool = True
    max_upload_mb: int = 10
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)


settings = Settings()
