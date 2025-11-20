"""OpenAI LLM Provider Implementation"""

from typing import AsyncIterator, Optional
import logging
import time
import httpx
from openai import AsyncOpenAI, APIError
from app.services.llm_provider import ILLMProvider, LLMRequest, LLMResponse

logger = logging.getLogger(__name__)


class OpenAIProvider(ILLMProvider):
    """OpenAI LLM Provider using OpenAI API"""

    def __init__(self, api_key: str, default_model: str = "gpt-4-turbo-preview"):
        """
        Initialize OpenAI provider

        Args:
            api_key: OpenAI API key
            default_model: Default model to use if not specified
        """
        if not api_key:
            raise ValueError("OpenAI API key is required")

        self.api_key = api_key
        self.default_model = default_model
        self.client = AsyncOpenAI(api_key=api_key)
        self.provider_name = "openai"

    async def generate_response(self, request: LLMRequest) -> LLMResponse:
        """
        Generate a response from OpenAI

        Args:
            request: LLMRequest with prompt and configuration

        Returns:
            LLMResponse with the generated content
        """
        try:
            start_time = time.time()
            model = request.model or self.default_model
            temperature = request.temperature if request.temperature is not None else 0.7
            max_tokens = request.max_tokens or 2048

            # Build messages
            messages = []
            if request.system_prompt:
                messages.append({"role": "system", "content": request.system_prompt})

            messages.append({"role": "user", "content": request.prompt})

            # Call OpenAI API
            response = await self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )

            # Extract content
            content = response.choices[0].message.content or ""
            finish_reason = response.choices[0].finish_reason or "stop"

            processing_time = (time.time() - start_time) * 1000

            return LLMResponse(
                content=content,
                model=model,
                tokens_used=response.usage.total_tokens if response.usage else 0,
                input_tokens=response.usage.prompt_tokens if response.usage else 0,
                output_tokens=response.usage.completion_tokens if response.usage else 0,
                finish_reason=finish_reason,
                processing_time_ms=processing_time,
                provider=self.provider_name,
                request_id=getattr(response, "id", None),
            )

        except APIError as e:
            logger.error(f"OpenAI API error: {e}")
            raise
        except Exception as e:
            logger.error(f"Error generating OpenAI response: {e}")
            raise

    async def generate_streaming_response(
        self, request: LLMRequest
    ) -> AsyncIterator[str]:
        """
        Generate a streaming response from OpenAI

        Args:
            request: LLMRequest with prompt and configuration

        Yields:
            Chunks of the generated response
        """
        try:
            model = request.model or self.default_model
            temperature = request.temperature if request.temperature is not None else 0.7
            max_tokens = request.max_tokens or 2048

            # Build messages
            messages = []
            if request.system_prompt:
                messages.append({"role": "system", "content": request.system_prompt})

            messages.append({"role": "user", "content": request.prompt})

            # Stream from OpenAI
            stream = await self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
            )

            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

        except APIError as e:
            logger.error(f"OpenAI streaming API error: {e}")
            raise
        except Exception as e:
            logger.error(f"Error in OpenAI streaming response: {e}")
            raise

    async def health_check(self) -> bool:
        """
        Check if OpenAI API is accessible

        Returns:
            True if API is accessible, False otherwise
        """
        try:
            # Make a simple call to verify API key and connectivity
            response = await self.client.models.list()
            return bool(response.data)
        except Exception as e:
            logger.warning(f"OpenAI health check failed: {e}")
            return False

    async def list_models(self) -> list[str]:
        """
        List available OpenAI models

        Returns:
            List of available model names
        """
        try:
            models_response = await self.client.models.list()
            return [model.id for model in models_response.data]
        except Exception as e:
            logger.error(f"Error listing OpenAI models: {e}")
            return []
