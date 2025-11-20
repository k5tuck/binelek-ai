"""Anthropic LLM Provider Implementation"""

from typing import AsyncIterator, Optional
import logging
import time
from anthropic import AsyncAnthropic, APIError
from app.services.llm_provider import ILLMProvider, LLMRequest, LLMResponse

logger = logging.getLogger(__name__)


class AnthropicProvider(ILLMProvider):
    """Anthropic LLM Provider using Claude API"""

    def __init__(self, api_key: str, default_model: str = "claude-3-sonnet-20240229"):
        """
        Initialize Anthropic provider

        Args:
            api_key: Anthropic API key
            default_model: Default model to use if not specified
        """
        if not api_key:
            raise ValueError("Anthropic API key is required")

        self.api_key = api_key
        self.default_model = default_model
        self.client = AsyncAnthropic(api_key=api_key)
        self.provider_name = "anthropic"

    async def generate_response(self, request: LLMRequest) -> LLMResponse:
        """
        Generate a response from Claude

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

            # Build system and user messages
            system_prompt = request.system_prompt or ""
            user_message = request.prompt

            # Call Anthropic API
            response = await self.client.messages.create(
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system_prompt if system_prompt else None,
                messages=[
                    {"role": "user", "content": user_message}
                ],
            )

            # Extract content
            content = response.content[0].text if response.content else ""
            finish_reason = response.stop_reason or "end_turn"

            processing_time = (time.time() - start_time) * 1000

            return LLMResponse(
                content=content,
                model=model,
                tokens_used=response.usage.input_tokens + response.usage.output_tokens,
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
                finish_reason=finish_reason,
                processing_time_ms=processing_time,
                provider=self.provider_name,
                request_id=getattr(response, "id", None),
            )

        except APIError as e:
            logger.error(f"Anthropic API error: {e}")
            raise
        except Exception as e:
            logger.error(f"Error generating Anthropic response: {e}")
            raise

    async def generate_streaming_response(
        self, request: LLMRequest
    ) -> AsyncIterator[str]:
        """
        Generate a streaming response from Claude

        Args:
            request: LLMRequest with prompt and configuration

        Yields:
            Chunks of the generated response
        """
        try:
            model = request.model or self.default_model
            temperature = request.temperature if request.temperature is not None else 0.7
            max_tokens = request.max_tokens or 2048

            system_prompt = request.system_prompt or ""
            user_message = request.prompt

            # Stream from Anthropic
            with await self.client.messages.stream(
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system_prompt if system_prompt else None,
                messages=[
                    {"role": "user", "content": user_message}
                ],
            ) as stream:
                async for text in stream.text_stream:
                    yield text

        except APIError as e:
            logger.error(f"Anthropic streaming API error: {e}")
            raise
        except Exception as e:
            logger.error(f"Error in Anthropic streaming response: {e}")
            raise

    async def health_check(self) -> bool:
        """
        Check if Anthropic API is accessible

        Returns:
            True if API is accessible, False otherwise
        """
        try:
            # Make a simple call to verify API key and connectivity
            response = await self.client.messages.create(
                model=self.default_model,
                max_tokens=10,
                messages=[
                    {"role": "user", "content": "ok"}
                ],
            )
            return response.id is not None
        except Exception as e:
            logger.warning(f"Anthropic health check failed: {e}")
            return False

    async def list_models(self) -> list[str]:
        """
        List available Anthropic models

        Returns:
            List of available model names
        """
        # Anthropic doesn't provide a models list API, return known models
        return [
            "claude-3-opus-20240229",
            "claude-3-sonnet-20240229",
            "claude-3-haiku-20240307",
            "claude-2.1",
            "claude-2",
            "claude-instant-1.2",
        ]
