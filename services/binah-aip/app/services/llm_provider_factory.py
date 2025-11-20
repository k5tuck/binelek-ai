"""LLM Provider Factory - Creates LLM provider instances"""

import logging
from typing import Literal
from app.config import settings
from app.services.llm_provider import ILLMProvider
from app.services.providers import OpenAIProvider, AnthropicProvider, OllamaProvider

logger = logging.getLogger(__name__)


class LLMProviderFactory:
    """Factory for creating LLM provider instances"""

    @staticmethod
    def create_provider(
        provider: Literal["openai", "anthropic", "ollama"] | None = None,
        **kwargs
    ) -> ILLMProvider:
        """
        Create an LLM provider instance

        Args:
            provider: Provider type. If None, uses settings.llm_provider
            **kwargs: Additional arguments to pass to provider constructor

        Returns:
            ILLMProvider instance

        Raises:
            ValueError: If provider is not supported or required config is missing
        """
        provider_type = provider or settings.llm_provider
        logger.info(f"Creating LLM provider: {provider_type}")

        if provider_type == "openai":
            api_key = kwargs.get("api_key") or settings.openai_api_key
            if not api_key:
                raise ValueError(
                    "OpenAI API key not provided. Set OPENAI_API_KEY env var or pass api_key parameter"
                )
            default_model = kwargs.get("default_model") or settings.llm_model
            return OpenAIProvider(api_key=api_key, default_model=default_model)

        elif provider_type == "anthropic":
            api_key = kwargs.get("api_key") or settings.anthropic_api_key
            if not api_key:
                raise ValueError(
                    "Anthropic API key not provided. Set ANTHROPIC_API_KEY env var or pass api_key parameter"
                )
            default_model = kwargs.get("default_model") or settings.llm_model
            return AnthropicProvider(api_key=api_key, default_model=default_model)

        elif provider_type == "ollama":
            base_url = kwargs.get("base_url") or settings.ollama_base_url
            default_model = kwargs.get("default_model") or settings.llm_model
            return OllamaProvider(base_url=base_url, default_model=default_model)

        else:
            raise ValueError(f"Unsupported LLM provider: {provider_type}")

    @staticmethod
    def get_provider(
        provider: Literal["openai", "anthropic", "ollama"] | None = None
    ) -> ILLMProvider:
        """
        Get or create an LLM provider instance (alias for create_provider)

        Args:
            provider: Provider type. If None, uses settings.llm_provider

        Returns:
            ILLMProvider instance
        """
        return LLMProviderFactory.create_provider(provider)
