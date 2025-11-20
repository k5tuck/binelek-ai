"""LLM Service - High-level interface for LLM operations"""

import logging
from typing import AsyncIterator, Optional
from app.services.llm_provider import ILLMProvider, LLMRequest, LLMResponse
from app.services.llm_provider_factory import LLMProviderFactory
from app.config import settings

logger = logging.getLogger(__name__)


class LLMService:
    """High-level service for LLM operations"""

    def __init__(self, provider: Optional[ILLMProvider] = None):
        """
        Initialize LLM Service

        Args:
            provider: LLMProvider instance. If None, creates one from settings
        """
        self.provider = provider or LLMProviderFactory.get_provider()
        logger.info(f"LLM Service initialized with provider: {self.provider.provider_name}")

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        tenant_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> LLMResponse:
        """
        Generate a response from the LLM

        Args:
            prompt: The prompt to send to the LLM
            system_prompt: System context/instructions
            model: Model to use (overrides default)
            temperature: Temperature for sampling
            max_tokens: Maximum tokens in response
            tenant_id: Tenant ID for multi-tenancy tracking
            user_id: User ID for tracking

        Returns:
            LLMResponse with the generated content
        """
        request = LLMRequest(
            prompt=prompt,
            system_prompt=system_prompt,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            tenant_id=tenant_id,
            user_id=user_id,
        )

        return await self.provider.generate_response(request)

    async def generate_stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        tenant_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> AsyncIterator[str]:
        """
        Generate a streaming response from the LLM

        Args:
            prompt: The prompt to send to the LLM
            system_prompt: System context/instructions
            model: Model to use (overrides default)
            temperature: Temperature for sampling
            max_tokens: Maximum tokens in response
            tenant_id: Tenant ID for multi-tenancy tracking
            user_id: User ID for tracking

        Yields:
            Chunks of the generated response
        """
        request = LLMRequest(
            prompt=prompt,
            system_prompt=system_prompt,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            tenant_id=tenant_id,
            user_id=user_id,
        )

        async for chunk in self.provider.generate_streaming_response(request):
            yield chunk

    async def health_check(self) -> bool:
        """
        Check if the LLM provider is healthy

        Returns:
            True if healthy, False otherwise
        """
        return await self.provider.health_check()

    async def list_models(self) -> list[str]:
        """
        List available models

        Returns:
            List of available model names
        """
        return await self.provider.list_models()

    async def switch_provider(self, provider_type: str):
        """
        Switch to a different LLM provider

        Args:
            provider_type: Type of provider ("openai", "anthropic", "ollama")

        Raises:
            ValueError: If provider type is not supported
        """
        self.provider = LLMProviderFactory.get_provider(provider_type)
        logger.info(f"Switched LLM provider to: {provider_type}")
