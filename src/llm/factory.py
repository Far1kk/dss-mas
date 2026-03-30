from langchain_core.language_models import BaseChatModel
from src.llm.providers import LLMProvider
from src.config import settings
from src.logger import log


class LLMFactory:
    @staticmethod
    def get_llm(provider: LLMProvider | str, **kwargs) -> BaseChatModel:
        if isinstance(provider, str):
            provider = LLMProvider.from_str(provider)

        log.debug(f"Создание LLM: {provider.value}")

        if provider == LLMProvider.GIGACHAT:
            from langchain_gigachat import GigaChat
            return GigaChat(
                credentials=settings.gigachat_api_key,
                verify_ssl_certs=False,
                scope="GIGACHAT_API_PERS",
                **kwargs,
            )

        if provider == LLMProvider.CLAUDE:
            from langchain_anthropic import ChatAnthropic
            return ChatAnthropic(
                api_key=settings.claude_api_key,
                model=kwargs.pop("model", "claude-sonnet-4-6"),
                **kwargs,
            )

        if provider == LLMProvider.OPENAI:
            from langchain_openai import ChatOpenAI
            return ChatOpenAI(
                api_key=settings.openai_api_key,
                model=kwargs.pop("model", "gpt-4o-mini"),
                **kwargs,
            )

        if provider == LLMProvider.DEEPSEEK:
            from langchain_deepseek import ChatDeepSeek
            return ChatDeepSeek(
                api_key=settings.deepseek_api_key,
                model=kwargs.pop("model", "deepseek-chat"),
                **kwargs,
            )

        if provider == LLMProvider.OLLAMA:
            from langchain_ollama import ChatOllama
            return ChatOllama(
                base_url=settings.ollama_base_url,
                model=kwargs.pop("model", "llama3"),
                **kwargs,
            )

        raise ValueError(f"Неизвестный провайдер: {provider}")
