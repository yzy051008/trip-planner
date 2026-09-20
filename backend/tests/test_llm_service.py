from types import SimpleNamespace


def test_get_llm_builds_one_configured_chat_model(monkeypatch):
    from app.services import llm_service

    created = []

    class FakeChatOpenAI:
        def __init__(self, **kwargs):
            created.append(kwargs)

    monkeypatch.setattr(llm_service, "ChatOpenAI", FakeChatOpenAI)
    monkeypatch.setattr(
        llm_service,
        "get_settings",
        lambda: SimpleNamespace(
            llm_model="test-model",
            llm_api_key="test-key",
            llm_base_url="https://example.com/v1",
            llm_temperature=0.5,
            llm_timeout=30,
        ),
    )
    llm_service.reset_llm()

    first = llm_service.get_llm()
    second = llm_service.get_llm()

    assert first is second
    assert created == [
        {
            "model": "test-model",
            "api_key": "test-key",
            "base_url": "https://example.com/v1",
            "temperature": 0.5,
            "timeout": 30,
            "max_retries": 2,
        }
    ]


def test_reset_llm_allows_rebuilding_the_singleton(monkeypatch):
    from app.services import llm_service

    instances = []

    class FakeChatOpenAI:
        def __init__(self, **kwargs):
            instances.append(self)

    monkeypatch.setattr(llm_service, "ChatOpenAI", FakeChatOpenAI)
    monkeypatch.setattr(
        llm_service,
        "get_settings",
        lambda: SimpleNamespace(
            llm_model="test-model",
            llm_api_key="",
            llm_base_url="",
            llm_temperature=0.7,
            llm_timeout=60,
        ),
    )
    llm_service.reset_llm()
    first = llm_service.get_llm()
    llm_service.reset_llm()
    second = llm_service.get_llm()

    assert first is not second
    assert len(instances) == 2
