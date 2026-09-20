"""LangChain ChatOpenAI 服务工厂。"""

from langchain_openai import ChatOpenAI

from ..config import get_settings


_llm_instance = None
_LLM_MAX_RETRIES = 2


def get_llm() -> ChatOpenAI:
    """获取全局 LLM 实例。"""
    global _llm_instance

    if _llm_instance is None:
        settings = get_settings()
        _llm_instance = ChatOpenAI(
            model=settings.llm_model,
            api_key=settings.llm_api_key or None,
            base_url=settings.llm_base_url or None,
            temperature=settings.llm_temperature,
            timeout=settings.llm_timeout,
            max_retries=_LLM_MAX_RETRIES,
        )

    return _llm_instance


def reset_llm() -> None:
    """重置全局 LLM 实例。"""
    global _llm_instance
    _llm_instance = None
