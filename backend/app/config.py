"""应用配置。"""

from pathlib import Path

from dotenv import load_dotenv
from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_DIR = Path(__file__).resolve().parents[1]
ENV_FILE = BACKEND_DIR / ".env"
load_dotenv(ENV_FILE)


_LLM_DEFAULTS = {
    "llm_model": "gpt-4o",
    "llm_temperature": 0.7,
    "llm_timeout": 60,
}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "LangChain智能旅行助手"
    app_version: str = "1.0.0"
    debug: bool = False
    host: str = "0.0.0.0"
    port: int = 8000
    cors_origins: str = (
        "http://localhost:5173,http://localhost:3000,"
        "http://127.0.0.1:5173,http://127.0.0.1:3000"
    )

    amap_api_key: str = ""
    llm_api_key: str = Field(
        default="",
        validation_alias=AliasChoices("LLM_API_KEY", "OPENAI_API_KEY"),
    )
    llm_base_url: str = Field(
        default="",
        validation_alias=AliasChoices("LLM_BASE_URL", "OPENAI_BASE_URL"),
    )
    llm_model: str = Field(
        default="gpt-4o",
        validation_alias=AliasChoices(
            "LLM_MODEL_ID", "LLM_MODEL", "OPENAI_MODEL", "OPENAI_MODEL_NAME"
        ),
    )
    llm_temperature: float = 0.7
    llm_timeout: int = 60

    amap_connect_timeout: float = 3.0
    amap_read_timeout: float = 10.0
    amap_write_timeout: float = 3.0
    amap_pool_timeout: float = 3.0
    amap_max_retries: int = 2

    embedding_provider: str = "local"
    local_embedding_model: str = "BAAI/bge-small-zh-v1.5"
    dashscope_api_key: str = ""
    embedding_model: str = "text-embedding-v4"

    # 临时规划会话默认使用内存，生产环境建议在 .env 中显式切换为 Redis。
    planning_session_store: str = "memory"
    redis_url: str = "redis://localhost:6379/0"
    planning_session_ttl_seconds: int = 7200

    @field_validator("llm_model", "llm_temperature", "llm_timeout", mode="before")
    @classmethod
    def empty_llm_value_to_default(cls, value, info):
        if value == "" or value is None:
            return _LLM_DEFAULTS[info.field_name]
        return value

    def get_cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",")]


settings = Settings()


def get_settings() -> Settings:
    return settings


def validate_config() -> bool:
    if not settings.amap_api_key:
        raise ValueError("AMAP_API_KEY 未配置")
    return True
