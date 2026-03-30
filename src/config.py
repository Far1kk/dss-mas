from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from typing import Optional


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # GigaChat (основной провайдер)
    gigachat_api_key: Optional[str] = Field(None, alias="GIGACHAT_API_KEY")
    gigachat_client_id: Optional[str] = Field(None, alias="GIGACHAT_CLIENT_ID")
    gigachat_client_secret: Optional[str] = Field(None, alias="GIGACHAT_CLIENT_SECRET")

    # Альтернативные провайдеры
    claude_api_key: Optional[str] = Field(None, alias="CLAUDE_API_KEY")
    openai_api_key: Optional[str] = Field(None, alias="OPENAI_API_KEY")
    deepseek_api_key: Optional[str] = Field(None, alias="DEEPSEEK_API_KEY")
    ollama_base_url: str = Field("http://localhost:11434", alias="OLLAMA_BASE_URL")

    # База данных PostgreSQL
    database_url: str = Field(
        "postgresql+asyncpg://postgres:postgres@localhost:5432/dss",
        alias="DATABASE_URL",
    )

    # Синхронный URL для seed-скрипта (psycopg2)
    database_url_sync: str = Field(
        "postgresql://postgres:postgres@localhost:5432/dss",
        alias="DATABASE_URL_SYNC",
    )

    # Приложение
    app_host: str = Field("192.168.0.17", alias="APP_HOST")
    app_port: int = Field(5000, alias="APP_PORT")
    default_llm_provider: str = Field("gigachat", alias="DEFAULT_LLM_PROVIDER")

    # LightAutoML (отключено по умолчанию — не устанавливается на Windows)
    use_lightautoml: bool = Field(False, alias="USE_LIGHTAUTOML")


settings = Settings()

