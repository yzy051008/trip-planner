from app.config import Settings, get_settings


def test_settings_loads_defaults_without_sensitive_values(monkeypatch):
    for name in (
        "AMAP_API_KEY",
        "LLM_API_KEY",
        "OPENAI_API_KEY",
        "DASHSCOPE_API_KEY",
        "LLM_MODEL_ID",
        "LLM_MODEL",
        "OPENAI_MODEL",
        "OPENAI_MODEL_NAME",
        "LLM_BASE_URL",
        "OPENAI_BASE_URL",
        "LLM_TEMPERATURE",
        "LLM_TIMEOUT",
    ):
        monkeypatch.delenv(name, raising=False)

    settings = Settings(_env_file=None)

    assert settings.app_name == "LangChain智能旅行助手"
    assert settings.port == 8000
    assert settings.amap_api_key == ""
    assert settings.llm_api_key == ""
    assert settings.llm_model == "gpt-4o"
    assert not hasattr(settings, "log_level")


def test_cors_origins_are_split_into_a_list():
    settings = Settings(cors_origins="http://localhost:5173, http://localhost:3000")

    assert settings.get_cors_origins_list() == [
        "http://localhost:5173",
        "http://localhost:3000",
    ]
